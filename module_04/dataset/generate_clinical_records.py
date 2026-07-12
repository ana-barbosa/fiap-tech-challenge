"""Generate synthetic longitudinal bone-density/prescription history records.

For each of the 14 patient_ids shared with video/audio, generates 4 synthetic visits
(6 months apart) trending consistent with that patient's risk tier, so all three
modalities tell the same risk story per patient.

Baseline demographics (Gender/Age/Height/Weight/BMI) are real, read from
dataset/raw/patients.xlsx - only bone density, labs, and medications are synthesized.

Risk tier reuses the fixed tier assignment from docs/consultation_scripts.md rather
than the live gait_scores.risk_score, so a later change to the video pipeline's
scoring can't retroactively contradict an already-written consultation script.

OP0_STATS/OP1_STATS/OP0_RATES/OP1_RATES/OVERALL_LAB_STATS below are hardcoded from
module_01/analysis/UA.csv's OP=0 vs. OP=1 split, so this doesn't depend on module_01
being present alongside module_04.

Output: dataset/synthetic/tabular/OAWXX_bone_density_history.csv (4 visits each).

Usage:
    python dataset/generate_clinical_records.py
"""

import argparse
import zlib
from pathlib import Path

import numpy as np
import pandas as pd

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_PATIENTS_XLSX = REPO_ROOT / "dataset" / "raw" / "patients.xlsx"
DEFAULT_OUTPUT_DIR = REPO_ROOT / "dataset" / "synthetic" / "tabular"

VISIT_COUNT = 4
VISIT_INTERVAL_MONTHS = 6

LBS_TO_KG = 0.453592

# Locked tier assignment, matching docs/consultation_scripts.md exactly.
RISK_TIER_BY_PATIENT = {
    "OAW01": "moderate", "OAW02": "low", "OAW03": "moderate", "OAW04": "high",
    "OAW05": "moderate", "OAW06": "moderate", "OAW07": "moderate", "OAW08": "low",
    "OAW09": "low", "OAW10": "moderate", "OAW11": "low", "OAW12": "high",
    "OAW13": "moderate", "OAW14": "moderate",
}

# OP-discriminative bone-density columns: mean/std by OP class, from UA.csv (n=969
# OP=0, n=568 OP=1). FN/FNT/TL/TLT only - L1-4/L1.4T excluded (near-zero OP=0 vs
# OP=1 gap in this dataset).
OP0_STATS = {"FN": (0.931, 0.128), "FNT": (-0.818, 0.975), "TL": (1.000, 0.131), "TLT": (-0.435, 0.991)}
OP1_STATS = {"FN": (0.758, 0.105), "FNT": (-2.125, 0.804), "TL": (0.822, 0.119), "TLT": (-1.779, 0.883)}

# Non-discriminative labs: sampled from the overall population regardless of tier.
OVERALL_LAB_STATS = {
    "L1-4": (1.136, 0.188), "L1.4T": (-0.552, 1.526), "FBG": (5.330, 1.541),
    "HDL-C": (1.250, 0.379), "LDL-C": (2.599, 0.900), "Ca": (2.238, 0.160),
    "P": (1.040, 0.209), "Mg": (0.869, 0.096),
}

# Binary column rates by OP class, from UA.csv.
OP0_RATES = {"Fracture": 0.011, "Smoking": 0.261, "Drinking": 0.261,
             "Calsium": 0.080, "Calcitriol": 0.073, "Bisphosphonate": 0.030, "Calcitonin": 0.011}
OP1_RATES = {"Fracture": 0.035, "Smoking": 0.252, "Drinking": 0.171,
             "Calsium": 0.261, "Calcitriol": 0.338, "Bisphosphonate": 0.114, "Calcitonin": 0.136}
MEDICATION_COLUMNS = ["Calsium", "Calcitriol", "Bisphosphonate", "Calcitonin"]

# T-score points lost per 6-month visit interval, by tier. High tier's per-visit
# decline (0.35) accumulates past the 0.5-point anomaly_risk_score.py threshold within
# a couple of visits; moderate's (0.12) stays mostly under it (borderline by design);
# low's (0.0, plus noise only) should essentially never trigger it.
FNT_TLT_DECLINE_PER_VISIT = {"low": 0.0, "moderate": 0.12, "high": 0.35}
TREND_NOISE_STD = 0.05  # small per-visit measurement noise, all tiers


def _load_baseline_demographics(patients_xlsx=DEFAULT_PATIENTS_XLSX):
    """Real per-patient Gender/Age/Height/Weight/BMI from the Toronto archive's own
    clinical spreadsheet.

    Filters out the summary rows (mean/SD/Min/Max) the spreadsheet appends after the
    14 real participants."""
    df = pd.read_excel(patients_xlsx)
    df = df[pd.to_numeric(df["Participant No."], errors="coerce").notna()].copy()
    df["participant_no"] = df["Participant No."].astype(int)

    demographics = {}
    for _, row in df.iterrows():
        participant_id = f"OAW{row['participant_no']:02d}"
        weight_kg = row["Weight (lbs)"] * LBS_TO_KG
        height_cm = row["Height (cm)"]
        height_m = height_cm / 100.0
        demographics[participant_id] = {
            "Gender": 1 if row["Sex"] == "M" else 2,  # UA.csv encoding: 1=Male, 2=Female
            "Age": float(row["Age (years)"]),
            "Height": height_cm,
            "Weight": weight_kg,
            "BMI": weight_kg / (height_m ** 2),
        }
    return demographics


def _sample_baseline_bone_density(tier, rng):
    """Sample FN/FNT/TL/TLT baseline from the tier-appropriate OP=0/OP=1 distribution."""
    values = {}
    for col in OP0_STATS:
        mean0, std0 = OP0_STATS[col]
        mean1, std1 = OP1_STATS[col]
        if tier == "low":
            mean, std = mean0, std0
        elif tier == "high":
            mean, std = mean1, std1
        else:
            mean, std = (mean0 + mean1) / 2, (std0 + std1) / 2
        values[col] = float(rng.normal(mean, std))
    return values


def _sample_overall_labs(rng):
    return {col: float(rng.normal(mean, std)) for col, (mean, std) in OVERALL_LAB_STATS.items()}


def _sample_binary_rate(column, tier, rng):
    rate0, rate1 = OP0_RATES[column], OP1_RATES[column]
    rate = rate0 if tier == "low" else rate1 if tier == "high" else (rate0 + rate1) / 2
    return int(rng.random() < rate)


def _apply_medication_event(medications, tier, visit_index, rng):
    """Insert an unexpected discontinuation/switch event at a random non-first visit
    for high-risk patients; moderate gets a smaller chance of a switch; low stays stable."""
    if visit_index == 0:
        return medications
    event_probability = {"low": 0.0, "moderate": 0.15, "high": 0.5}[tier]
    if rng.random() >= event_probability:
        return medications
    active = [col for col in MEDICATION_COLUMNS if medications[col] == 1]
    if not active:
        return medications
    discontinued = medications.copy()
    discontinued[rng.choice(active)] = 0
    return discontinued


def generate_patient_visits(participant_id, tier, demographics, seed=None):
    """Generate VISIT_COUNT synthetic visits for one patient.

    demographics: this patient's dict from _load_baseline_demographics().
    seed: defaults to a stable hash of participant_id, so re-running is deterministic.
    Uses zlib.crc32, not builtin hash() - str hashing is randomized per-process
    (PYTHONHASHSEED) unless seeded, so hash("OAW01") isn't stable across runs."""
    stable_seed = zlib.crc32(participant_id.encode())
    rng = np.random.default_rng(seed if seed is not None else stable_seed)

    baseline_bone_density = _sample_baseline_bone_density(tier, rng)
    overall_labs = _sample_overall_labs(rng)
    medications = {col: _sample_binary_rate(col, tier, rng) for col in MEDICATION_COLUMNS}
    fracture = _sample_binary_rate("Fracture", tier, rng)
    smoking = _sample_binary_rate("Smoking", tier, rng)
    drinking = _sample_binary_rate("Drinking", tier, rng)

    decline_per_visit = FNT_TLT_DECLINE_PER_VISIT[tier]

    visits = []
    for visit_index in range(VISIT_COUNT):
        cumulative_decline = decline_per_visit * visit_index
        fnt = baseline_bone_density["FNT"] - cumulative_decline + rng.normal(0, TREND_NOISE_STD)
        tlt = baseline_bone_density["TLT"] - cumulative_decline + rng.normal(0, TREND_NOISE_STD)
        # FN/TL trend with their T-score counterparts, scaled down - plausibility only.
        fn = baseline_bone_density["FN"] - cumulative_decline * 0.05 + rng.normal(0, TREND_NOISE_STD * 0.1)
        tl = baseline_bone_density["TL"] - cumulative_decline * 0.05 + rng.normal(0, TREND_NOISE_STD * 0.1)

        medications = _apply_medication_event(medications, tier, visit_index, rng)

        visit = {
            "participant_id": participant_id,
            "visit_index": visit_index,
            "Gender": demographics["Gender"],
            "Age": demographics["Age"] + (visit_index * VISIT_INTERVAL_MONTHS) / 12.0,
            "Height": demographics["Height"],
            "Weight": demographics["Weight"],
            "BMI": demographics["BMI"],
            "L1-4": overall_labs["L1-4"],
            "L1.4T": overall_labs["L1.4T"],
            "FN": fn,
            "FNT": fnt,
            "TL": tl,
            "TLT": tlt,
            "FBG": overall_labs["FBG"],
            "HDL-C": overall_labs["HDL-C"],
            "LDL-C": overall_labs["LDL-C"],
            "Ca": overall_labs["Ca"],
            "P": overall_labs["P"],
            "Mg": overall_labs["Mg"],
            "Fracture": fracture,
            "Smoking": smoking,
            "Drinking": drinking,
            **medications,
        }
        visits.append(visit)

    return visits


def generate_all_patients(patients_xlsx=DEFAULT_PATIENTS_XLSX):
    """Generate visits for all 14 patients, keyed by participant_id."""
    demographics_by_patient = _load_baseline_demographics(patients_xlsx)
    return {
        participant_id: generate_patient_visits(participant_id, tier, demographics_by_patient[participant_id])
        for participant_id, tier in RISK_TIER_BY_PATIENT.items()
    }


def write_patient_history(participant_id, visits, output_dir=DEFAULT_OUTPUT_DIR):
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / f"{participant_id}_bone_density_history.csv"
    pd.DataFrame(visits).to_csv(output_path, index=False)
    return output_path


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--patients-xlsx", type=Path, default=DEFAULT_PATIENTS_XLSX)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR, help="Defaults to dataset/synthetic/tabular")
    args = parser.parse_args()

    all_visits = generate_all_patients(args.patients_xlsx)
    for participant_id, visits in all_visits.items():
        output_path = write_patient_history(participant_id, visits, args.output_dir)
        print(f"{participant_id}: wrote {len(visits)} visits -> {output_path}")
    print(f"generated {len(all_visits)} participants -> {args.output_dir}")


if __name__ == "__main__":
    main()
