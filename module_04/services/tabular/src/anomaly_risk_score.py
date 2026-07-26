"""Rule-based anomaly detection over synthetic bone-density/prescription history.

This is rule-based, not ML-based, deliberately: a doctor needs to know *why* an alert
fired, not just that a model scored it low-probability.

Two independent rule-based signals, matching db/schema.sql's anomaly_scores columns
exactly (bone_density_risk_score, t_score_trend, prescription_flag):

1. T-score decline: FNT (femoral neck T-score) is checked for a >=0.5-point drop
   between any two consecutive visits.
2. Prescription evolution: any medication column that goes from 1 (prescribed) to 0
   (stopped) between consecutive visits counts as an unexpected discontinuation.

Like audio_risk_score.py, the combined 0-100 risk score is a disclosed, fixed-weight
heuristic, not statistically fit or clinically validated.
"""

from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"

TSCORE_DECLINE_THRESHOLD = 0.5  # T-score points between consecutive visits
TSCORE_COLUMN = "FNT"

MEDICATION_COLUMNS = ["Calsium", "Calcitriol", "Bisphosphonate", "Calcitonin"]

DECLINE_SCORE_PER_POINT = 50  # e.g. a 1.0-point cumulative FNT decline alone -> 50/100
PRESCRIPTION_FLAG_SCORE = 30


def _detect_tscore_decline(visits, column=TSCORE_COLUMN, threshold=TSCORE_DECLINE_THRESHOLD):
    """Check for a >=threshold drop in `column`, either in one consecutive visit pair
    or accumulated across the whole visit history.

    Both checks matter: a single dramatic drop between two visits is one real anomaly
    shape, but so is a gradual, steady decline that only crosses the threshold once
    accumulated across several smaller consecutive drops.

    Returns (flagged: bool, max_drop: float, cumulative_drop: float). cumulative_drop
    is first-visit-value minus last-visit-value (positive = net decline over the whole
    history).
    """
    values = [v[column] for v in visits]
    consecutive_drops = [values[i] - values[i + 1] for i in range(len(values) - 1)]
    max_drop = max(consecutive_drops) if consecutive_drops else 0.0
    cumulative_drop = values[0] - values[-1]
    flagged = max_drop >= threshold or cumulative_drop >= threshold
    return flagged, max_drop, cumulative_drop


def _detect_prescription_discontinuation(visits, medication_columns=MEDICATION_COLUMNS):
    """Check every consecutive visit pair for any medication going from 1 -> 0."""
    for i in range(len(visits) - 1):
        current, following = visits[i], visits[i + 1]
        for col in medication_columns:
            if current.get(col) == 1 and following.get(col) == 0:
                return True, col
    return False, None


def _describe_trend(cumulative_drop, decline_flagged):
    if decline_flagged:
        return f"declining ({cumulative_drop:+.2f} {TSCORE_COLUMN} points over the visit history)"
    if cumulative_drop > 0:
        return f"mild decline ({cumulative_drop:+.2f} {TSCORE_COLUMN} points, below the {TSCORE_DECLINE_THRESHOLD} threshold)"
    return f"stable ({cumulative_drop:+.2f} {TSCORE_COLUMN} points over the visit history)"


def score_patient_history(visits):
    """Score one patient's visit history for anomalies.

    visits: list of per-visit dicts, in visit order.

    Returns dict matching db/schema.sql's anomaly_scores columns: bone_density_risk_score
    (0-100), t_score_trend (human-readable text), prescription_flag (0/1).
    """
    decline_flagged, _, cumulative_drop = _detect_tscore_decline(visits)
    prescription_flagged, _ = _detect_prescription_discontinuation(visits)

    risk_score = min(100, max(0, (
        max(cumulative_drop, 0) * DECLINE_SCORE_PER_POINT
        + (PRESCRIPTION_FLAG_SCORE if prescription_flagged else 0)
    )))

    return {
        "bone_density_risk_score": risk_score,
        "t_score_trend": _describe_trend(cumulative_drop, decline_flagged),
        "prescription_flag": int(prescription_flagged),
    }


def score_participant(participant_id, blob_store_dir=DEFAULT_BLOB_STORE_DIR):
    import pandas as pd  # deferred - only needed to read the CSV back, not for score_patient_history itself

    history_path = blob_store_dir / participant_id / "bone_density_history.csv"
    visits = pd.read_csv(history_path).to_dict(orient="records")
    result = score_patient_history(visits)
    result["participant_id"] = participant_id
    return result
