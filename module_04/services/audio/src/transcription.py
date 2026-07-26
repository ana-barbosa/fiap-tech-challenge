"""Transcription + speaker diarization for synthetic consultation audio.

Uses WhisperX (Whisper ASR + forced alignment + pyannote.audio diarization) to produce a
diarized, timestamped transcript per participant. Diarization uses
pyannote/speaker-diarization-community-1, a gated model - a token alone is not enough.
You must first visit https://huggingface.co/pyannote/speaker-diarization-community-1
while logged in and click "Agree and access repository", THEN create a token, then:

    cp .env.example .env   # fill in HF_TOKEN
"""

import json
import os
from pathlib import Path

import whisperx
from dotenv import load_dotenv
from whisperx.diarize import DiarizationPipeline

from diarization_utils import map_speakers_to_roles

REPO_ROOT = Path(__file__).resolve().parents[3]
load_dotenv(REPO_ROOT / ".env")

WHISPER_MODEL_SIZE = "medium"  # multilingual; pt-BR needs more than "base" for reliable ASR
WHISPER_LANGUAGE = "pt"
DEVICE = "cpu"
COMPUTE_TYPE = "int8"  # cpu-friendly

HF_TOKEN_ENV_VAR = "HF_TOKEN"


def _require_hf_token():
    token = os.environ.get(HF_TOKEN_ENV_VAR)
    if not token:
        raise RuntimeError(
            f"{HF_TOKEN_ENV_VAR} is not set. Diarization needs a HuggingFace token for "
            "the gated pyannote/speaker-diarization-community-1 model - visit "
            "https://huggingface.co/pyannote/speaker-diarization-community-1 while "
            "logged in and click \"Agree and access repository\" (a token alone isn't "
            f"enough), then create a token and set {HF_TOKEN_ENV_VAR} in .env "
            "(see .env.example)."
        )
    return token


def load_models(device=DEVICE, compute_type=COMPUTE_TYPE):
    """Load the Whisper ASR model, alignment model, and diarization pipeline once."""
    hf_token = _require_hf_token()
    asr_model = whisperx.load_model(WHISPER_MODEL_SIZE, device, compute_type=compute_type,
                                     language=WHISPER_LANGUAGE)
    align_model, align_metadata = whisperx.load_align_model(language_code=WHISPER_LANGUAGE, device=device)
    diarize_model = DiarizationPipeline(token=hf_token, device=device)
    return asr_model, align_model, align_metadata, diarize_model


EXPECTED_NUM_SPEAKERS = 2  # every consultation_scripts.md dialogue is doctor + patient only


def transcribe_and_diarize(audio_path, asr_model, align_model, align_metadata, diarize_model, device=DEVICE):
    """Run ASR -> forced alignment -> diarization on one audio file.

    Returns a list of {start, end, speaker, text} segments. Speaker labels are
    pyannote's own arbitrary IDs (SPEAKER_00, SPEAKER_01, ...) - see
    map_speakers_to_roles for mapping those to doctor/patient.
    """
    audio = whisperx.load_audio(str(audio_path))
    result = asr_model.transcribe(audio, batch_size=8)
    result = whisperx.align(result["segments"], align_model, align_metadata, audio, device)
    # num_speakers=2 pinned rather than left to auto-detection: pyannote's clustering
    # unreliably estimates speaker count on these short clips (observed misdetecting a
    # single speaker for one participant). Every recording here is a fixed 2-party
    # dialogue by construction, so we pass the known count directly.
    diarize_segments = diarize_model(audio, num_speakers=EXPECTED_NUM_SPEAKERS)
    result = whisperx.assign_word_speakers(diarize_segments, result)

    return [
        {"start": seg.get("start"), "end": seg.get("end"),
         "speaker": seg.get("speaker"), "text": seg.get("text", "").strip()}
        for seg in result["segments"]
    ]


def process_participant(participant_id, blob_store_dir, models):
    audio_path = blob_store_dir / participant_id / "consultation.wav"

    segments = transcribe_and_diarize(audio_path, *models)
    segments = map_speakers_to_roles(segments)

    patient_dir = blob_store_dir / participant_id
    patient_dir.mkdir(parents=True, exist_ok=True)
    output_path = patient_dir / "diarized_transcript.json"
    output_path.write_text(
        json.dumps({"segments": segments}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return {"participant_id": participant_id, "num_segments": len(segments)}
