"""Generate synthetic consultation audio from docs/consultation_scripts.md.

Tooling: edge-tts (Microsoft Edge's free neural TTS, no API key) - chosen over local
candidates like Piper after finding Piper's pt_BR voice catalog is all-male, which
conflicts with the scripts' feminine-agreement patient dialogue.

Severity-tier prosody: only the patient's lines vary by tier (rate/pitch slow down as
severity increases, simulating fatigue) - the doctor's delivery stays neutral.
Inter-turn silence also lengthens with severity.

Outputs, per participant:
  dataset/synthetic/audio/OAWXX_consultation.wav   concatenated doctor+patient dialogue
  dataset/synthetic/audio/OAWXX_transcript.json    ground-truth {speaker, text, severity}
                                                    per line - dev-only.
"""

import argparse
import asyncio
import json
import re
from pathlib import Path

import edge_tts
from pydub import AudioSegment

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPTS_PATH = REPO_ROOT / "docs" / "consultation_scripts.md"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dataset" / "synthetic" / "audio"

DOCTOR_VOICE = "pt-BR-AntonioNeural"
PATIENT_VOICE = "pt-BR-FranciscaNeural"

TIER_LABELS = {"Baixo": "low", "Moderado": "moderate", "Alto": "high"}

# Patient-only prosody by tier - doctor's voice never varies.
PATIENT_PROSODY_BY_TIER = {
    "low": {"rate": "+0%", "pitch": "+0Hz"},
    "moderate": {"rate": "-10%", "pitch": "-1Hz"},
    "high": {"rate": "-20%", "pitch": "-3Hz"},
}
DOCTOR_PROSODY = {"rate": "+0%", "pitch": "+0Hz"}

# Inter-turn silence scales with tier. Raised from 400/600ms after diarization testing
# showed pyannote's speaker-change detection missed boundaries at shorter gaps.
INTER_TURN_SILENCE_MS_BY_TIER = {"low": 700, "moderate": 800, "high": 900}

HEADER_RE = re.compile(r"^## (OAW\d+)\s*[—\-–]\s*(\w+)(?:\s*\((.+?)\))?\s*$")
LINE_RE = re.compile(r"^(Médico|Paciente):\s*(.+)$")
SPEAKER_KEY = {"Médico": "doctor", "Paciente": "patient"}


def parse_consultation_scripts(md_path=DEFAULT_SCRIPTS_PATH):
    """Parse the markdown script file into {participant_id: {tier, scenario_label, lines}}."""
    text = Path(md_path).read_text(encoding="utf-8")
    blocks = text.split("## ")[1:]  # first split chunk is the file preamble/table, not a script

    participants = {}
    for block in blocks:
        header_line, _, rest = block.partition("\n")
        match = HEADER_RE.match(f"## {header_line}")
        if not match:
            continue
        participant_id, tier_pt, scenario_label = match.groups()
        tier = TIER_LABELS.get(tier_pt, tier_pt.lower())

        fence_start = rest.find("```")
        fence_end = rest.find("```", fence_start + 3)
        code_block = rest[fence_start + 3:fence_end] if fence_start != -1 else ""

        lines = []
        for raw_line in code_block.splitlines():
            line_match = LINE_RE.match(raw_line.strip())
            if line_match:
                speaker_pt, line_text = line_match.groups()
                lines.append({"speaker": SPEAKER_KEY[speaker_pt], "text": line_text.strip()})

        if lines:
            participants[participant_id] = {
                "tier": tier,
                "scenario_label": scenario_label or "",
                "lines": lines,
            }

    return participants


async def synthesize_line(text, speaker, tier, output_path):
    voice = DOCTOR_VOICE if speaker == "doctor" else PATIENT_VOICE
    prosody = DOCTOR_PROSODY if speaker == "doctor" else PATIENT_PROSODY_BY_TIER[tier]
    communicate = edge_tts.Communicate(text, voice, rate=prosody["rate"], pitch=prosody["pitch"])
    await communicate.save(str(output_path))


async def synthesize_participant(participant_id, meta, tmp_dir):
    """Synthesize each line to a temp mp3, returning the list of file paths in order."""
    tmp_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for i, line in enumerate(meta["lines"]):
        path = tmp_dir / f"{participant_id}_line{i:02d}_{line['speaker']}.mp3"
        await synthesize_line(line["text"], line["speaker"], meta["tier"], path)
        paths.append(path)
    return paths


def assemble_consultation_audio(line_paths, tier, output_path):
    silence = AudioSegment.silent(duration=INTER_TURN_SILENCE_MS_BY_TIER[tier])
    combined = AudioSegment.empty()
    for path in line_paths:
        combined += AudioSegment.from_mp3(path)
        # Silence after every line, including the last - without it, the closing line
        # had no trailing context for pyannote's segmentation to place that boundary.
        combined += silence
    output_path.parent.mkdir(parents=True, exist_ok=True)
    combined.export(output_path, format="wav")
    return len(combined) / 1000.0  # duration in seconds


def save_transcript_log(participant_id, meta, output_path):
    log = [
        {"speaker": line["speaker"], "text": line["text"], "severity": meta["tier"]}
        for line in meta["lines"]
    ]
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(log, ensure_ascii=False, indent=2), encoding="utf-8")


def process_participant(participant_id, meta, output_dir, tmp_dir):
    line_paths = asyncio.run(synthesize_participant(participant_id, meta, tmp_dir))
    duration_s = assemble_consultation_audio(
        line_paths, meta["tier"], output_dir / f"{participant_id}_consultation.wav"
    )
    save_transcript_log(participant_id, meta, output_dir / f"{participant_id}_transcript.json")
    for path in line_paths:
        path.unlink(missing_ok=True)
    return {
        "participant_id": participant_id,
        "tier": meta["tier"],
        "scenario_label": meta["scenario_label"],
        "num_lines": len(meta["lines"]),
        "duration_s": round(duration_s, 1),
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--scripts-path", type=Path, default=DEFAULT_SCRIPTS_PATH)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--skip-existing", action="store_true",
                         help="Skip participants whose _consultation.wav already exists")
    args = parser.parse_args()

    participants = parse_consultation_scripts(args.scripts_path)
    if not participants:
        print(f"No scripts parsed from {args.scripts_path}")
        return

    tmp_dir = args.output_dir / "_tmp_lines"
    for participant_id, meta in sorted(participants.items()):
        wav_path = args.output_dir / f"{participant_id}_consultation.wav"
        if args.skip_existing and wav_path.exists():
            print(f"skip (already exists): {participant_id}")
            continue
        summary = process_participant(participant_id, meta, args.output_dir, tmp_dir)
        print(summary)

    tmp_dir.rmdir() if tmp_dir.exists() and not any(tmp_dir.iterdir()) else None
    print(f"processed {len(participants)} participants -> {args.output_dir}")


if __name__ == "__main__":
    main()
