"""Combine the three modalities' latest 0-100 scores into one aggregated risk assessment.

Gait has multiple rows per patient (one per video segment), so run.py passes in a
per-patient median gait score rather than a single row's score, unlike audio/anomaly
which have exactly one row per patient.

Aggregation rule (v1_equal_weight_2of3_escalation):
1. combined_risk_score = equal-weighted average of the three 0-100 scores.
2. Escalation override: if >=2 of the 3 individual scores are >= HIGH_SCORE_THRESHOLD,
   force combined_risk_level = HIGH regardless of the average.
3. Otherwise, map combined_risk_score to LOW/MODERATE/HIGH via fixed terciles of the
   0-100 scale.
"""

AGGREGATION_RULE_VERSION = "v1_equal_weight_2of3_escalation"

WEIGHTS = {"gait": 1 / 3, "audio": 1 / 3, "anomaly": 1 / 3}

HIGH_SCORE_THRESHOLD = 65  # individual-score threshold for the 2-of-3 escalation rule
ESCALATION_MIN_HIGH_COUNT = 2

# Fixed terciles of the 0-100 scale.
LOW_MODERATE_CUTOFF = 33.34
MODERATE_HIGH_CUTOFF = 66.67


def _risk_level_from_score(combined_risk_score):
    if combined_risk_score >= MODERATE_HIGH_CUTOFF:
        return "HIGH"
    if combined_risk_score >= LOW_MODERATE_CUTOFF:
        return "MODERATE"
    return "LOW"


def aggregate(gait_score, audio_score, anomaly_score):
    """Combine three 0-100 scores into one aggregated result.

    Returns dict: combined_risk_score (float, 0-100), combined_risk_level
    (LOW/MODERATE/HIGH), escalated (bool - whether the 2-of-3 override fired),
    aggregation_rule_version.
    """
    scores = {"gait": gait_score, "audio": audio_score, "anomaly": anomaly_score}
    combined_risk_score = sum(scores[k] * WEIGHTS[k] for k in scores)

    high_count = sum(1 for v in scores.values() if v >= HIGH_SCORE_THRESHOLD)
    escalated = high_count >= ESCALATION_MIN_HIGH_COUNT

    combined_risk_level = "HIGH" if escalated else _risk_level_from_score(combined_risk_score)

    return {
        "combined_risk_score": combined_risk_score,
        "combined_risk_level": combined_risk_level,
        "escalated": escalated,
        "aggregation_rule_version": AGGREGATION_RULE_VERSION,
    }
