"""Smoke tests for bone_density_model.py, using two example patient payloads
(translated to bone_density_model.FEATURE_COLUMNS' dashed/dotted names).

Only checks output shape/range (0/1 prediction, probability in [0, 1]), not exact values.
"""

import bone_density_model as bdm

# module_01/service/README.md's first curl example (higher risk profile: older, lower
# bone density T-scores, prior fracture).
HIGHER_RISK_PATIENT = {
    "Gender": 1, "Age": 68, "Height": 160, "Weight": 55, "BMI": 21.5,
    "L1-4": 0.85, "L1.4T": -1.8, "FN": 0.75, "FNT": -2.0, "TL": 0.7, "TLT": -2.1,
    "FBG": 5.6, "HDL-C": 1.1, "LDL-C": 3.5, "Ca": 2.3, "P": 1.0, "Mg": 0.9,
    "Fracture": 1, "Smoking": 0, "Drinking": 0,
}

# module_01/service/README.md's second curl example (lower risk profile: younger,
# normal T-scores, no fracture history).
LOWER_RISK_PATIENT = {
    "Gender": 0, "Age": 45, "Height": 170, "Weight": 70, "BMI": 24.2,
    "L1-4": 1.1, "L1.4T": 0.3, "FN": 1.0, "FNT": 0.2, "TL": 0.95, "TLT": 0.1,
    "FBG": 5.2, "HDL-C": 1.4, "LDL-C": 2.8, "Ca": 2.35, "P": 1.1, "Mg": 1.0,
    "Fracture": 0, "Smoking": 0, "Drinking": 0,
}


def test_feature_columns_match_payload_keys():
    assert set(bdm.FEATURE_COLUMNS) == set(HIGHER_RISK_PATIENT.keys())
    assert set(bdm.FEATURE_COLUMNS) == set(LOWER_RISK_PATIENT.keys())


def test_predict_op_risk_returns_well_formed_output():
    model, pipeline = bdm.load_model()
    for patient in (HIGHER_RISK_PATIENT, LOWER_RISK_PATIENT):
        prediction, risk_probability = bdm.predict_op_risk(patient, model, pipeline)
        assert prediction in (0, 1)
        assert 0.0 <= risk_probability <= 1.0


def test_predict_op_risk_missing_feature_raises():
    incomplete = {k: v for k, v in HIGHER_RISK_PATIENT.items() if k != "Age"}
    model, pipeline = bdm.load_model()
    try:
        bdm.predict_op_risk(incomplete, model, pipeline)
        assert False, "expected KeyError for a missing feature"
    except KeyError:
        pass


def test_predict_participant_op_risk_uses_latest_visit(tmp_path):
    # Rows written out of visit_index order deliberately - predict_participant_op_risk
    # must pick the highest visit_index (the current snapshot), not just the last row
    # in file order, per its own docstring on why "latest" means most recent visit.
    import pandas as pd

    patient_dir = tmp_path / "OAWTEST"
    patient_dir.mkdir()
    visit_1 = {**LOWER_RISK_PATIENT, "participant_id": "OAWTEST", "visit_index": 1}
    visit_0 = {**HIGHER_RISK_PATIENT, "participant_id": "OAWTEST", "visit_index": 0}
    pd.DataFrame([visit_1, visit_0]).to_csv(patient_dir / "bone_density_history.csv", index=False)

    model, pipeline = bdm.load_model()
    result = bdm.predict_participant_op_risk("OAWTEST", tmp_path, model, pipeline)

    expected_prediction, expected_probability = bdm.predict_op_risk(LOWER_RISK_PATIENT, model, pipeline)
    assert result["op_prediction"] == expected_prediction
    assert result["op_prediction_confidence"] == expected_probability
