from generate_tts import parse_consultation_scripts


def test_parses_all_14_participants():
    participants = parse_consultation_scripts()
    assert len(participants) == 14
    assert set(participants.keys()) == {f"OAW{i:02d}" for i in range(1, 15)}


def test_tier_mapping_matches_scenario_plan_table():
    participants = parse_consultation_scripts()
    low = {"OAW02", "OAW08", "OAW09", "OAW11"}
    high = {"OAW04", "OAW12"}
    for pid, meta in participants.items():
        if pid in low:
            assert meta["tier"] == "low"
        elif pid in high:
            assert meta["tier"] == "high"
        else:
            assert meta["tier"] == "moderate"


def test_lines_alternate_speakers_starting_with_doctor():
    participants = parse_consultation_scripts()
    for pid, meta in participants.items():
        speakers = [line["speaker"] for line in meta["lines"]]
        assert speakers[0] == "doctor", pid
        assert all(a != b for a, b in zip(speakers, speakers[1:])), pid


def test_lines_are_non_empty_text():
    participants = parse_consultation_scripts()
    for meta in participants.values():
        for line in meta["lines"]:
            assert line["text"].strip()
