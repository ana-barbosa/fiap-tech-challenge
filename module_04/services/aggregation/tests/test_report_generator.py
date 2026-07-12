import json

import aggregate_scores
import report_generator

GAIT_ROW_ABNORMAL = {
    "cadence_steps_per_min": 90.5, "step_time_s_mean": 0.65, "flag_abnormal_gait": 1,
}
GAIT_ROW_NORMAL = {
    "cadence_steps_per_min": 120.0, "step_time_s_mean": 0.5, "flag_abnormal_gait": 0,
}
AUDIO_ROW = {
    "fatigue_mentions": 2, "pain_mentions": 1,
    "flags": json.dumps({"fatigue_mentioned": True, "pain_mentioned": True, "anxiety_mentioned": True}),
}
ANOMALY_ROW_DECLINING = {
    "t_score_trend": "declining (+0.85 FNT points over the visit history)",
    "prescription_flag": 1,
}
ANOMALY_ROW_STABLE = {
    "t_score_trend": "stable (+0.02 FNT points over the visit history)",
    "prescription_flag": 0,
}


def test_build_report_high_risk_includes_alert_line():
    aggregation_result = aggregate_scores.aggregate(gait_score=90, audio_score=90, anomaly_score=90)
    report = report_generator.build_report(
        "OAW04", GAIT_ROW_ABNORMAL, AUDIO_ROW, ANOMALY_ROW_DECLINING, aggregation_result
    )
    assert "Patient ID: OAW04" in report
    assert "abnormal gait detected" in report
    assert "2 fatigue mention(s), 1 pain mention(s), anxiety mentioned" in report
    assert "prescription discontinued unexpectedly" in report
    assert "Combined risk: HIGH" in report
    assert "Alert sent to medical team" in report


def test_build_report_low_risk_has_no_alert_line():
    aggregation_result = aggregate_scores.aggregate(gait_score=10, audio_score=10, anomaly_score=10)
    report = report_generator.build_report(
        "OAW02", GAIT_ROW_NORMAL, AUDIO_ROW, ANOMALY_ROW_STABLE, aggregation_result
    )
    assert "gait within normal range" in report
    assert "medication regimen stable" in report
    assert "Combined risk: LOW" in report
    assert "Alert sent" not in report


def test_build_alert_message_mentions_escalation():
    aggregation_result = aggregate_scores.aggregate(gait_score=70, audio_score=70, anomaly_score=0)
    message = report_generator.build_alert_message("OAW12", aggregation_result)
    assert "OAW12" in message
    assert "escalated by 2-of-3 agreement" in message


def test_build_alert_message_without_escalation():
    aggregation_result = aggregate_scores.aggregate(gait_score=90, audio_score=10, anomaly_score=10)
    assert aggregation_result["escalated"] is False
    message = report_generator.build_alert_message("OAW12", aggregation_result)
    assert "escalated" not in message
