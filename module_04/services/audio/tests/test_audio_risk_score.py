import json

import audio_risk_score as ars


def test_score_segment_text_detects_fatigue():
    # real line, docs/consultation_scripts.md OAW01
    result = ars.score_segment_text("Ando um pouco mais cansada que o normal, principalmente no fim da tarde.")
    assert result == {"fatigue_mentioned": True, "pain_mentioned": False, "anxiety_mentioned": False}


def test_score_segment_text_negated_pain_not_flagged():
    # real line, docs/consultation_scripts.md OAW01 - "dor" is denied right next to it
    # ("dor nao"), while "cansaco" (fatigue) is a genuine, unnegated mention.
    result = ars.score_segment_text("Nao, dor nao. So mesmo esse cansaco.")
    assert result["pain_mentioned"] is False
    assert result["fatigue_mentioned"] is True


def test_score_segment_text_no_mentions():
    result = ars.score_segment_text("Bom dia, como voce esta se sentindo hoje?")
    assert result == {"fatigue_mentioned": False, "pain_mentioned": False, "anxiety_mentioned": False}


def test_add_segment_flags_only_scores_patient_role():
    segments = [
        {"role": "doctor", "text": "Notou alguma dor ao caminhar ou se movimentar?"},
        {"role": "patient", "text": "Estou com muita dor no joelho."},
        {"role": "unknown", "text": "dor"},
    ]
    doctor_seg, patient_seg, unknown_seg = ars.add_segment_flags(segments)

    assert doctor_seg["pain_mentioned"] is False  # doctor's line never scored, even though it says "dor"
    assert patient_seg["pain_mentioned"] is True
    assert unknown_seg["pain_mentioned"] is False  # only "patient" role is scored


def test_add_segment_flags_sets_explicit_false_not_missing_key():
    segments = [{"role": "doctor", "text": "Ola."}]
    augmented = ars.add_segment_flags(segments)
    assert augmented[0]["fatigue_mentioned"] is False
    assert augmented[0]["pain_mentioned"] is False
    assert augmented[0]["anxiety_mentioned"] is False


def test_add_segment_flags_does_not_mutate_input():
    segments = [{"role": "patient", "text": "Sinto dor."}]
    ars.add_segment_flags(segments)
    assert "pain_mentioned" not in segments[0]


def test_annotate_transcript_with_flags_round_trip(tmp_path):
    patient_dir = tmp_path / "OAWTEST"
    patient_dir.mkdir()
    transcript_path = patient_dir / "diarized_transcript.json"
    transcript_path.write_text(
        json.dumps({"segments": [
            {"role": "doctor", "text": "Como voce esta?"},
            {"role": "patient", "text": "Estou cansada e com dor."},
        ]}),
        encoding="utf-8",
    )

    ars.annotate_transcript_with_flags("OAWTEST", tmp_path)

    data = json.loads(transcript_path.read_text(encoding="utf-8"))
    assert data["segments"][0]["fatigue_mentioned"] is False
    assert data["segments"][1]["fatigue_mentioned"] is True
    assert data["segments"][1]["pain_mentioned"] is True
