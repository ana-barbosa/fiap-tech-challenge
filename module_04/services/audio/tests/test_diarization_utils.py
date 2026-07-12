from diarization_utils import collapse_consecutive, map_speakers_to_roles, validate_diarization


def test_collapse_consecutive_removes_adjacent_duplicates():
    assert collapse_consecutive(["a", "a", "b", "b", "b", "a"]) == ["a", "b", "a"]


def test_collapse_consecutive_empty():
    assert collapse_consecutive([]) == []


def test_map_speakers_to_roles_first_speaker_is_doctor():
    segments = [
        {"speaker": "SPEAKER_01", "text": "Como você tem se sentido?"},
        {"speaker": "SPEAKER_00", "text": "Um pouco cansada."},
        {"speaker": "SPEAKER_01", "text": "Entendido."},
    ]
    result = map_speakers_to_roles(segments)
    assert result[0]["role"] == "doctor"
    assert result[1]["role"] == "patient"
    assert result[2]["role"] == "doctor"


def test_map_speakers_to_roles_unknown_speaker_stays_unknown():
    segments = [{"speaker": None, "text": "..."}]
    result = map_speakers_to_roles(segments)
    assert result[0]["role"] == "unknown"


def test_validate_diarization_perfect_match():
    segments = [
        {"role": "doctor", "text": "..."},
        {"role": "patient", "text": "..."},
        {"role": "doctor", "text": "..."},
    ]
    ground_truth = [
        {"speaker": "doctor", "text": "...", "severity": "low"},
        {"speaker": "patient", "text": "...", "severity": "low"},
        {"speaker": "doctor", "text": "...", "severity": "low"},
    ]
    result = validate_diarization(segments, ground_truth)
    assert result["turn_sequence_accuracy"] == 1.0
    assert result["num_diarized_turns"] == 3
    assert result["num_ground_truth_turns"] == 3


def test_validate_diarization_handles_split_segments_via_collapsing():
    # WhisperX splits one "doctor" ground-truth line into two segments - should still
    # collapse to the same turn sequence and match perfectly.
    segments = [
        {"role": "doctor", "text": "Como você"},
        {"role": "doctor", "text": "tem se sentido?"},
        {"role": "patient", "text": "Bem."},
    ]
    ground_truth = [
        {"speaker": "doctor", "text": "Como você tem se sentido?", "severity": "low"},
        {"speaker": "patient", "text": "Bem.", "severity": "low"},
    ]
    result = validate_diarization(segments, ground_truth)
    assert result["turn_sequence_accuracy"] == 1.0


def test_validate_diarization_mismatch_scores_below_one():
    segments = [{"role": "patient", "text": "..."}, {"role": "doctor", "text": "..."}]
    ground_truth = [
        {"speaker": "doctor", "text": "...", "severity": "low"},
        {"speaker": "patient", "text": "...", "severity": "low"},
    ]
    result = validate_diarization(segments, ground_truth)
    assert result["turn_sequence_accuracy"] < 1.0
