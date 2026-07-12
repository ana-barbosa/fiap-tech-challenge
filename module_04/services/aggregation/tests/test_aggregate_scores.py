import aggregate_scores


def test_all_low_scores_yield_low_risk():
    result = aggregate_scores.aggregate(gait_score=10, audio_score=10, anomaly_score=10)
    assert result["combined_risk_level"] == "LOW"
    assert result["escalated"] is False
    assert result["combined_risk_score"] == 10


def test_all_moderate_scores_yield_moderate_risk():
    result = aggregate_scores.aggregate(gait_score=50, audio_score=50, anomaly_score=50)
    assert result["combined_risk_level"] == "MODERATE"
    assert result["escalated"] is False


def test_all_high_scores_yield_high_risk():
    result = aggregate_scores.aggregate(gait_score=90, audio_score=90, anomaly_score=90)
    assert result["combined_risk_level"] == "HIGH"
    assert result["escalated"] is True


def test_two_of_three_high_escalates_even_with_moderate_average():
    # average = (70 + 70 + 0) / 3 = 46.67, which alone would be MODERATE - the 2-of-3
    # escalation override should still force HIGH.
    result = aggregate_scores.aggregate(gait_score=70, audio_score=70, anomaly_score=0)
    assert result["escalated"] is True
    assert result["combined_risk_level"] == "HIGH"


def test_one_of_three_high_does_not_escalate():
    result = aggregate_scores.aggregate(gait_score=90, audio_score=10, anomaly_score=10)
    assert result["escalated"] is False
    # average = (90 + 10 + 10) / 3 = 36.67 -> MODERATE
    assert result["combined_risk_level"] == "MODERATE"


def test_tercile_boundaries():
    assert aggregate_scores._risk_level_from_score(0) == "LOW"
    assert aggregate_scores._risk_level_from_score(33.0) == "LOW"
    assert aggregate_scores._risk_level_from_score(33.34) == "MODERATE"
    assert aggregate_scores._risk_level_from_score(66.67) == "HIGH"
    assert aggregate_scores._risk_level_from_score(100) == "HIGH"


def test_aggregation_rule_version_is_stamped():
    result = aggregate_scores.aggregate(gait_score=10, audio_score=10, anomaly_score=10)
    assert result["aggregation_rule_version"] == aggregate_scores.AGGREGATION_RULE_VERSION
