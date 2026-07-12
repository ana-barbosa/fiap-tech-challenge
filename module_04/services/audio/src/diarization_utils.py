"""Pure-logic helpers for diarization output, shared by transcription.py and its tests.

Kept dependency-free (stdlib only) so tests don't have to import whisperx (torch,
pyannote.audio - heavy, and gated behind a HuggingFace token) just for this.
"""


def collapse_consecutive(sequence):
    return [item for i, item in enumerate(sequence) if i == 0 or item != sequence[i - 1]]


def map_speakers_to_roles(segments):
    """Map pyannote's arbitrary speaker IDs to doctor/patient by turn order.

    Every consultation dialogue starts with the doctor, so the first speaker ID to
    appear is the doctor and the second is the patient. This only holds because we
    control script authorship; a real deployment would need role classification
    instead of turn order.
    """
    seen_order = []
    for seg in segments:
        if seg["speaker"] and seg["speaker"] not in seen_order:
            seen_order.append(seg["speaker"])

    role_by_speaker = {}
    if len(seen_order) >= 1:
        role_by_speaker[seen_order[0]] = "doctor"
    if len(seen_order) >= 2:
        role_by_speaker[seen_order[1]] = "patient"

    for seg in segments:
        seg["role"] = role_by_speaker.get(seg["speaker"], "unknown")
    return segments


def validate_diarization(segments, ground_truth_log):
    """Compare diarized role sequence against the known ground-truth speaker sequence.

    WhisperX segments rarely line up 1:1 with our original script lines (ASR may split
    or merge differently), so this compares role SEQUENCES after collapsing consecutive
    duplicates on both sides, rather than exact segment boundaries - sequence order is
    what matters for downstream sentiment scoring, since we just need to know which
    spans of text are the patient's.
    """
    diarized_roles = collapse_consecutive([seg["role"] for seg in segments if seg["role"] != "unknown"])
    ground_truth_roles = collapse_consecutive([line["speaker"] for line in ground_truth_log])

    matches = sum(1 for a, b in zip(diarized_roles, ground_truth_roles) if a == b)
    total = max(len(diarized_roles), len(ground_truth_roles))

    return {
        "num_diarized_turns": len(diarized_roles),
        "num_ground_truth_turns": len(ground_truth_roles),
        "turn_sequence_accuracy": matches / total if total else None,
        "diarized_sequence": diarized_roles,
        "ground_truth_sequence": ground_truth_roles,
    }
