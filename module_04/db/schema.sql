-- Shared SQLite contract between services. Each service only writes its own table(s);
-- only the aggregation service reads across tables. patients is the exception - no
-- modality service writes to it; dataset/seed_patients.py seeds it from
-- dataset/raw/patients.xlsx before any service runs, so video/audio/tabular can run in
-- parallel without racing to satisfy this table's FK.

CREATE TABLE IF NOT EXISTS patients (
    patient_id TEXT PRIMARY KEY,
    source TEXT NOT NULL,              -- 'toronto' | 'self-recorded'
    age REAL,
    sex TEXT,                          -- 'M' | 'F', as given in patients.xlsx
    height_cm REAL,
    weight_kg REAL,
    bmi REAL,
    falls_last_6mo INTEGER,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS gait_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    video_id TEXT NOT NULL,
    segment_id INTEGER NOT NULL,
    direction TEXT,
    camera TEXT,
    ground_truth TEXT,
    landmarks_path TEXT,               -- repo-relative path to the cached per-video
                                        -- landmarks CSV in db/blob_store/{patient_id}/
    start_frame INTEGER,
    end_frame INTEGER,
    duration_s REAL,
    n_frames INTEGER,
    hip_width_px_median REAL,
    num_steps_detected INTEGER,
    cadence_steps_per_min REAL,
    step_time_s_mean REAL,
    step_time_s_std REAL,
    step_width_norm_mean REAL,
    step_width_norm_cv REAL,
    margin_of_stability_norm_mean REAL,
    risk_score REAL,
    flag_low_cadence INTEGER,
    flag_prolonged_step_time INTEGER,
    flag_abnormal_gait INTEGER,
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (video_id, segment_id)
);

CREATE TABLE IF NOT EXISTS audio_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    audio_file TEXT NOT NULL,
    distress_score REAL,
    fatigue_mentions INTEGER,
    pain_mentions INTEGER,
    flags TEXT,                        -- JSON-encoded list, kept as TEXT - sqlite has no array type
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (audio_file)
);

CREATE TABLE IF NOT EXISTS anomaly_scores (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    bone_density_risk_score REAL,
    t_score_trend TEXT,
    prescription_flag INTEGER,
    op_prediction INTEGER,             -- 0/1, module_01's RandomForestClassifier, run on
                                        -- the patient's latest synthetic visit. Disclosed
                                        -- OP=1 recall is only 0.64.
    op_prediction_confidence REAL,     -- P(OP=1) from the same model
    processed_at TEXT DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (patient_id)                -- re-running upserts in place instead of piling
                                        -- up duplicate rows
);

CREATE TABLE IF NOT EXISTS aggregated_assessments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    gait_score_id INTEGER REFERENCES gait_scores(id),
    audio_score_id INTEGER REFERENCES audio_scores(id),
    anomaly_score_id INTEGER REFERENCES anomaly_scores(id),
    combined_risk_level TEXT,          -- 'LOW' | 'MODERATE' | 'HIGH'
    rationale TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    patient_id TEXT NOT NULL REFERENCES patients(patient_id),
    aggregated_assessment_id INTEGER REFERENCES aggregated_assessments(id),
    alert_level TEXT,
    message TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
