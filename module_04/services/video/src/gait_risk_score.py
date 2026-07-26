"""Convert gait metrics (cadence, step time) into a 0-100 risk score plus flags.

Threshold source: the source paper's own pose-derived cadence/step-time population
stats aren't published anywhere this project could fetch, so the reference mean/SD is
instead fit directly from this project's own pose-based measurements across the 14 real
Toronto participants, then validated against patients.xlsx's clinical fall-risk scores
(see validate_against_clinical).

Score formula: risk rises when cadence falls below the reference mean and/or step time
exceeds it (matching the paper's negative cadence-vs-TUG correlation), combined as an
equal-weighted average of both z-scores and mapped onto 0-100 (50 = average).
"""

import re
import sys
from pathlib import Path

import numpy as np
import pandas as pd
from scipy.stats import pearsonr

sys.path.insert(0, str(Path(__file__).resolve().parent))
from video_id import parse_video_id  # noqa: E402

ABNORMAL_GAIT_Z_THRESHOLD = 1.0  # >1 SD worse than the reference cohort


def fit_reference_stats(metrics_df):
    """Reference mean/SD for cadence and step time, from this project's own cohort."""
    valid = metrics_df.dropna(subset=["cadence_steps_per_min", "step_time_s_mean"])
    return {
        "cadence_mean": float(valid["cadence_steps_per_min"].mean()),
        "cadence_sd": float(valid["cadence_steps_per_min"].std()),
        "step_time_mean": float(valid["step_time_s_mean"].mean()),
        "step_time_sd": float(valid["step_time_s_mean"].std()),
    }


def score_segment(cadence, step_time, reference):
    """Risk score (0-100) + flags for one segment's cadence/step-time pair."""
    if pd.isna(cadence) or pd.isna(step_time):
        return None, {"abnormal_gait": None, "low_cadence": None, "prolonged_step_time": None}

    z_cadence = (reference["cadence_mean"] - cadence) / reference["cadence_sd"]
    z_step_time = (step_time - reference["step_time_mean"]) / reference["step_time_sd"]
    combined_z = (z_cadence + z_step_time) / 2

    risk_score = float(np.clip(50 + 25 * combined_z, 0, 100))
    flags = {
        "low_cadence": bool(z_cadence > ABNORMAL_GAIT_Z_THRESHOLD),
        "prolonged_step_time": bool(z_step_time > ABNORMAL_GAIT_Z_THRESHOLD),
        "abnormal_gait": bool(combined_z > ABNORMAL_GAIT_Z_THRESHOLD),
    }
    return risk_score, flags


def score_metrics(metrics_df, reference=None):
    """Add risk_score + flag columns, and participant/source metadata, to a metrics table."""
    reference = reference or fit_reference_stats(metrics_df)

    scored_rows = []
    for _, row in metrics_df.iterrows():
        risk_score, flags = score_segment(row["cadence_steps_per_min"], row["step_time_s_mean"], reference)
        participant_id, camera = parse_video_id(row["video_id"])
        source = "toronto" if camera is not None else "self-recorded"
        participant_no = int(re.sub(r"\D", "", participant_id)) if source == "toronto" else None

        scored_rows.append({
            **row.to_dict(),
            "participant_id": participant_id,
            "camera": camera,
            "source": source,
            "ground_truth": "table_1_xlsx" if source == "toronto" else "none",
            "participant_no": participant_no,
            "risk_score": risk_score,
            **{f"flag_{k}": v for k, v in flags.items()},
        })

    return pd.DataFrame(scored_rows), reference


def validate_against_clinical(scored_df, patients_xlsx_path):
    """Pearson correlation of cadence/step time against patients.xlsx clinical scores.

    Aggregates to one row per participant via the MEDIAN across their segments/cameras,
    not the mean - per-participant cadence has substantial within-participant spread,
    and the median is far less sensitive to those than the mean.
    """
    clinical = pd.read_excel(patients_xlsx_path)
    clinical = clinical[pd.to_numeric(clinical["Participant No."], errors="coerce").notna()].copy()
    clinical["participant_no"] = clinical["Participant No."].astype(int)

    per_participant = (
        scored_df[scored_df["source"] == "toronto"]
        .groupby("participant_no")[["cadence_steps_per_min", "step_time_s_mean"]]
        .median()
        .reset_index()
    )
    merged = per_participant.merge(clinical, on="participant_no", how="inner")

    results = []
    for gait_var in ["cadence_steps_per_min", "step_time_s_mean"]:
        for clinical_var in ["POMA-Balance", "POMA-Gait", "BBS", "TUG (s) "]:
            paired = merged[[gait_var, clinical_var]].dropna()
            if len(paired) < 3:
                continue
            r, p = pearsonr(paired[gait_var], paired[clinical_var])
            results.append({
                "gait_variable": f"{gait_var}_median",
                "clinical_variable": clinical_var.strip(),
                "n": len(paired),
                "pearson_r": r,
                "p_value": p,
            })

    return pd.DataFrame(results)
