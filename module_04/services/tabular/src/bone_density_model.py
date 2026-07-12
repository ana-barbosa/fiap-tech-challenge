"""Bone-density / osteoporosis risk classifier - wraps the pre-trained model from
module_01, unmodified. This model answers "does this snapshot look osteoporotic," not
"is something changing over time" - that's anomaly_risk_score.py's job.

models/random_forest.pkl (RandomForestClassifier(max_depth=3, criterion="gini")) and
models/pre_process_pipeline.pkl (SimpleImputer(median) -> StandardScaler) are copies of
module_01/models/{random_forest,pre_process_pipeline}.pkl, kept local so this service
stays self-contained without module_01 alongside it.

FEATURE_COLUMNS is the exact 20-column order the pipeline was fit on - order matters,
since pipeline.transform() takes a plain array, not column-name-aware input.

Disclosed limitation, inherited as-is from module_01: OP=1 recall is only 0.64 (misses
~4 in 10 real osteoporosis-positive cases), attributed to dataset class imbalance and
female under-representation.
"""

import pickle
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_MODEL_PATH = SERVICE_ROOT / "models" / "random_forest.pkl"
DEFAULT_PIPELINE_PATH = SERVICE_ROOT / "models" / "pre_process_pipeline.pkl"

# Column names/order as in the source dataset (dashes/dots kept) - pipeline.transform()
# only cares about position, not names.
FEATURE_COLUMNS = [
    "Gender", "Age", "Height", "Weight", "BMI", "L1-4", "L1.4T", "FN", "FNT", "TL", "TLT",
    "FBG", "HDL-C", "LDL-C", "Ca", "P", "Mg", "Fracture", "Smoking", "Drinking",
]


def load_model(model_path=DEFAULT_MODEL_PATH, pipeline_path=DEFAULT_PIPELINE_PATH):
    """Load the classifier + its fitted preprocessing pipeline once, for reuse across patients."""
    with open(model_path, "rb") as f:
        model = pickle.load(f)
    with open(pipeline_path, "rb") as f:
        pipeline = pickle.load(f)
    return model, pipeline


def predict_op_risk(patient_features, model, pipeline):
    """Predict osteoporosis risk for one patient snapshot.

    patient_features: dict keyed by FEATURE_COLUMNS. Missing keys raise KeyError
    deliberately - silently defaulting a missing lab value would let SimpleImputer's
    median-fill mask a caller bug instead of a real missing reading.

    Returns (prediction, risk_probability): prediction is 0/1, risk_probability is P(OP=1).
    """
    row = [[patient_features[col] for col in FEATURE_COLUMNS]]
    scaled = pipeline.transform(row)
    prediction = int(model.predict(scaled)[0])
    risk_probability = float(model.predict_proba(scaled)[0][1])
    return prediction, risk_probability


def predict_participant_op_risk(participant_id, blob_store_dir, model, pipeline):
    """Run the OP classifier on participant_id's most recent synthetic visit.

    Reads db/blob_store/{participant_id}/bone_density_history.csv directly - every
    visit row already carries all of FEATURE_COLUMNS, so no extra join or lookup is needed.
    """
    import pandas as pd  # deferred - only this function needs it

    history_path = Path(blob_store_dir) / participant_id / "bone_density_history.csv"
    visits_df = pd.read_csv(history_path)
    latest_visit = visits_df.sort_values("visit_index").iloc[-1]
    features = {col: latest_visit[col] for col in FEATURE_COLUMNS}
    prediction, risk_probability = predict_op_risk(features, model, pipeline)
    return {"op_prediction": prediction, "op_prediction_confidence": risk_probability}
