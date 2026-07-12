"""Distress/fatigue scoring from diarized consultation transcripts.

Local keyword-stem detection for fatigue, pain, and anxiety mentions on **patient-only**
lines, with a small negation check so denials ("sem dor", "dor não") aren't miscounted
as the thing they're denying. The 0-100 distress score is a disclosed, fixed-weight
heuristic, not a calibrated clinical measure.

Keyword stems match at word-start only (not substring-anywhere) and are
accent-insensitive (NFKD-normalized with combining marks stripped, so "incômoda" and
"incomoda" both match the "incomod" stem). Word-start anchoring matters: a plain
substring check on "dor" (pain) would also match inside "dormido"/"dormir" (sleep-
related words); see PAIN_KEYWORDS' negative lookahead for the fix.
"""

import json
import re
import unicodedata
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"

# Stem patterns (word-start anchored, see _count_mentions), not whole words, so
# inflections/diminutives match too (e.g. "dor" also matches "dorzinha", "dores";
# "cansa" matches "cansada", "cansaço", "cansado"). "dor" excludes a following "m" so it
# doesn't match sleep-related words (dormir, dormido, dorme).
FATIGUE_KEYWORDS = [re.compile(r"cansa"), re.compile(r"fadiga")]
PAIN_KEYWORDS = [re.compile(r"dor(?!m)"), re.compile(r"incomod"), re.compile(r"desconfort")]
ANXIETY_KEYWORDS = [re.compile(r"ansios"), re.compile(r"medo"), re.compile(r"insegur"), re.compile(r"preocupad")]

# Words that negate a keyword mention if they appear immediately before or after it
# (see _count_mentions), e.g. "sem dor", "nenhuma dor", "dor não".
NEGATION_WORDS = {"nao", "sem", "nenhum", "nenhuma", "nunca"}
# Immediate neighbor only, not a wider window - avoids over-triggering on negation
# words in unrelated nearby clauses.
NEGATION_LOOKAROUND = 1

DISTRESS_WEIGHTS = {"fatigue": 20, "pain": 20, "anxiety": 15}
HIGH_DISTRESS_THRESHOLD = 50


def _tokenize(text):
    """Lowercase, strip accents, and split into word tokens with punctuation dropped.

    Punctuation must be dropped (not just accents stripped) for the negation check in
    _count_mentions to work: without it, "Não, dor não." tokenizes to "nao," and "nao."
    (trailing comma/period attached), which never exactly matches the bare "nao" in
    NEGATION_WORDS.
    """
    decomposed = unicodedata.normalize("NFKD", text.lower())
    stripped = "".join(c for c in decomposed if not unicodedata.combining(c))
    return re.findall(r"\w+", stripped)


def _count_mentions(text, keywords):
    """Count keyword-stem occurrences in text, excluding ones immediately negated
    (checked on both sides, since negation can precede or follow the keyword).
    """
    words = _tokenize(text)
    count = 0
    for i, word in enumerate(words):
        if not any(kw.match(word) for kw in keywords):
            continue
        nearby = (
            words[max(0, i - NEGATION_LOOKAROUND):i]
            + words[i + 1:i + 1 + NEGATION_LOOKAROUND]
        )
        if any(neg in nearby for neg in NEGATION_WORDS):
            continue
        count += 1
    return count


def score_patient_text(segments):
    """Score one participant's patient-only text for fatigue/pain/anxiety mentions.

    segments: list of {"role": "doctor"|"patient"|"unknown", "text": str, ...} - only
    role == "patient" contributes.
    """
    patient_text = " ".join(seg["text"] for seg in segments if seg.get("role") == "patient")

    fatigue_mentions = _count_mentions(patient_text, FATIGUE_KEYWORDS)
    pain_mentions = _count_mentions(patient_text, PAIN_KEYWORDS)
    anxiety_mentions = _count_mentions(patient_text, ANXIETY_KEYWORDS)

    distress_score = min(100, (
        fatigue_mentions * DISTRESS_WEIGHTS["fatigue"]
        + pain_mentions * DISTRESS_WEIGHTS["pain"]
        + anxiety_mentions * DISTRESS_WEIGHTS["anxiety"]
    ))

    flags = {
        "fatigue_mentioned": fatigue_mentions > 0,
        "pain_mentioned": pain_mentions > 0,
        "anxiety_mentioned": anxiety_mentions > 0,
        "high_distress": distress_score >= HIGH_DISTRESS_THRESHOLD,
    }

    return {
        "fatigue_mentions": fatigue_mentions,
        "pain_mentions": pain_mentions,
        "distress_score": distress_score,
        "flags": flags,
    }


def score_participant(participant_id, blob_store_dir=DEFAULT_BLOB_STORE_DIR):
    transcript_path = blob_store_dir / participant_id / "diarized_transcript.json"
    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    result = score_patient_text(data["segments"])
    result["participant_id"] = participant_id
    return result


def score_segment_text(text):
    """Per-line fatigue/pain/anxiety flags for one segment's text, for UI highlighting.

    Does not feed the aggregate distress_score/fatigue_mentions/pain_mentions written
    to the audio_scores table - those stay based on score_patient_text's whole-text counts.
    """
    return {
        "fatigue_mentioned": _count_mentions(text, FATIGUE_KEYWORDS) > 0,
        "pain_mentioned": _count_mentions(text, PAIN_KEYWORDS) > 0,
        "anxiety_mentioned": _count_mentions(text, ANXIETY_KEYWORDS) > 0,
    }


def add_segment_flags(segments):
    """Return a copy of segments with per-line fatigue/pain/anxiety flags added to
    every segment - explicit True/False on every segment (not left absent), so
    downstream consumers never see a missing/NaN cell for these columns.

    Only patient-role segments are actually scored; doctor/unknown segments get
    explicit False (e.g. a doctor's line mentioning "dor" while asking about pain
    shouldn't be flagged as if the patient reported it).
    """
    augmented = []
    for seg in segments:
        seg = dict(seg)
        if seg.get("role") == "patient":
            seg.update(score_segment_text(seg["text"]))
        else:
            seg.update({"fatigue_mentioned": False, "pain_mentioned": False, "anxiety_mentioned": False})
        augmented.append(seg)
    return augmented


def annotate_transcript_with_flags(participant_id, blob_store_dir=DEFAULT_BLOB_STORE_DIR):
    """Add per-line fatigue/pain/anxiety flags to participant_id's diarized transcript
    and rewrite it back to db/blob_store/{participant_id}/diarized_transcript.json.
    """
    transcript_path = blob_store_dir / participant_id / "diarized_transcript.json"
    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    data["segments"] = add_segment_flags(data["segments"])
    transcript_path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    return transcript_path
