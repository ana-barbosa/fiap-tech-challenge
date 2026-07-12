"""Build the doctor-facing report text combining all three modalities' findings.

Example output:

    Patient ID: SYN001
    Video: abnormal gait detected (90.5 steps/min, 0.65s step time)
    Audio: 2 fatigue mention(s), 1 pain mention(s)
    Bone density: declining (+0.85 FNT points over the visit history); prescription discontinued unexpectedly
    Combined risk: HIGH (78.3/100)
    Alert sent to medical team for fall/fracture risk reassessment.
"""

import json


def _video_finding(gait_row):
    cadence = gait_row.get("cadence_steps_per_min")
    step_time = gait_row.get("step_time_s_mean")
    cadence_str = f"{cadence:.1f} steps/min" if cadence is not None else "cadence unavailable"
    step_time_str = f"{step_time:.2f}s step time" if step_time is not None else "step time unavailable"

    if gait_row.get("flag_abnormal_gait"):
        return f"abnormal gait detected ({cadence_str}, {step_time_str})"
    return f"gait within normal range ({cadence_str}, {step_time_str})"


def _audio_finding(audio_row):
    fatigue = audio_row.get("fatigue_mentions") or 0
    pain = audio_row.get("pain_mentions") or 0
    parts = [f"{fatigue} fatigue mention(s)", f"{pain} pain mention(s)"]

    flags = audio_row.get("flags")
    if flags:
        try:
            flags = json.loads(flags) if isinstance(flags, str) else flags
        except (TypeError, ValueError):
            flags = {}
        if flags.get("anxiety_mentioned"):
            parts.append("anxiety mentioned")
    return ", ".join(parts)


def _bone_density_finding(anomaly_row):
    trend = anomaly_row.get("t_score_trend", "trend unavailable")
    if anomaly_row.get("prescription_flag"):
        return f"{trend}; prescription discontinued unexpectedly"
    return f"{trend}; medication regimen stable"


def build_report(patient_id, gait_row, audio_row, anomaly_row, aggregation_result):
    """Build the full doctor-facing report text for one patient."""
    lines = [
        f"Patient ID: {patient_id}",
        f"Video: {_video_finding(gait_row)}",
        f"Audio: {_audio_finding(audio_row)}",
        f"Bone density: {_bone_density_finding(anomaly_row)}",
        f"Combined risk: {aggregation_result['combined_risk_level']} "
        f"({aggregation_result['combined_risk_score']:.1f}/100)",
    ]
    if aggregation_result["combined_risk_level"] == "HIGH":
        lines.append("⚠️ Alert sent to medical team for fall/fracture risk reassessment.")
    return "\n".join(lines)


def build_alert_message(patient_id, aggregation_result):
    """Short, doctor-facing alert message for the `alerts` table row."""
    return (
        f"Patient {patient_id}: combined fall/fracture risk is HIGH "
        f"({aggregation_result['combined_risk_score']:.1f}/100"
        f"{', escalated by 2-of-3 agreement' if aggregation_result['escalated'] else ''}). "
        "Recommend fall/fracture risk reassessment."
    )
