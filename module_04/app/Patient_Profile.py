"""Doctor-facing dashboard - reads db/hospital.sqlite and blob_store/ only, read-only,
no inference. Per-patient view; the cross-patient overview lives on its own page
(app/pages/1_All_Alerts.py). Run with `make run-app` (after `make setup-app`).
"""

import json

import pandas as pd
import streamlit as st

from db_utils import BLOB_STORE_DIR, DB_PATH, query_df

RISK_COLORS = {"LOW": "green", "MODERATE": "orange", "HIGH": "red"}
HIGHLIGHT_ROW_CSS = "background-color: rgba(255, 43, 43, 0.25)"


def load_patient_ids():
    return query_df("SELECT patient_id FROM patients ORDER BY patient_id")["patient_id"].tolist()


def render_patient_header(patient_id):
    """Identity block: age/sex/height/weight/BMI/fall history."""
    patient_row = query_df("SELECT * FROM patients WHERE patient_id = ?", (patient_id,))
    if patient_row.empty:
        return
    row = patient_row.iloc[0]

    st.header(f"Patient ID: {patient_id}", anchor="patient-info")

    def fmt(value, suffix="", ndigits=None):
        if pd.isna(value):
            return "N/A"
        if ndigits is not None:
            value = round(value, ndigits)
            if ndigits == 0:
                value = int(value)
        return f"{value}{suffix}"

    col1, col2, col3, col4, col5, col6 = st.columns(6)
    col1.metric("Age", fmt(row["age"], " yrs", ndigits=0))
    col2.metric("Sex", fmt(row["sex"]))
    col3.metric("Height", fmt(row["height_cm"], " cm", ndigits=0))
    col4.metric("Weight", fmt(row["weight_kg"], " kg", ndigits=1))
    col5.metric("BMI", fmt(row["bmi"], ndigits=1))
    col6.metric("Falls (6mo)", fmt(row["falls_last_6mo"], ndigits=0))


def render_video_player(patient_id, selected_video_id):
    """Play the skeleton-overlay annotation, falling back to the raw video if
    `make run-video` hasn't generated it yet.

    muted=True is required alongside autoplay=True - browsers silently block
    unmuted autoplay otherwise. Clips have no audio track, so this costs nothing."""
    annotated_path = BLOB_STORE_DIR / patient_id / f"{selected_video_id}_annotated.mp4"
    if annotated_path.exists():
        st.video(str(annotated_path), autoplay=True, muted=True)
        return

    raw_path = BLOB_STORE_DIR / patient_id / f"{selected_video_id}.mp4"
    if raw_path.exists():
        st.video(str(raw_path), autoplay=True, muted=True)
        st.caption(
            "Showing the raw video - no landmark overlay yet. Generate it with "
            "`make run-video`."
        )
    else:
        st.info(f"Video file for {selected_video_id} not found locally.")


def _style_abnormal_rows(df):
    """Tint rows flagged abnormal_gait.

    Compares with `== 1`, not truthiness - flag_abnormal_gait is SQL-nullable and pandas
    reads NULL back as float NaN, which is truthy in Python."""
    def highlight(row):
        return [HIGHLIGHT_ROW_CSS if row["flag_abnormal_gait"] == 1 else ""] * len(row)
    return df.style.apply(highlight, axis=1)


def _style_flagged_transcript_rows(df):
    """Tint transcript rows flagged for fatigue/pain/anxiety mentions. Only
    patient-role rows can ever be True here, so doctor/unknown rows never highlight."""
    def highlight(row):
        flagged = row["fatigue_mentioned"] or row["pain_mentioned"] or row["anxiety_mentioned"]
        return [HIGHLIGHT_ROW_CSS if flagged else ""] * len(row)
    return df.style.apply(highlight, axis=1)


def render_video_section(patient_id):
    st.subheader("Video - gait analysis", anchor="video")
    gait_df = query_df(
        "SELECT video_id, direction, camera, cadence_steps_per_min, step_time_s_mean, "
        "risk_score, flag_low_cadence, flag_prolonged_step_time, flag_abnormal_gait "
        "FROM gait_scores WHERE patient_id = ? ORDER BY video_id, segment_id",
        (patient_id,),
    )
    if gait_df.empty:
        st.info("No gait_scores rows for this patient yet - run `make run-video`.")
        return

    valid = gait_df.dropna(subset=["risk_score"])
    col1, col2, col3 = st.columns(3)
    col1.metric("Median cadence", f"{valid['cadence_steps_per_min'].median():.1f} steps/min")
    col2.metric("Median step time", f"{valid['step_time_s_mean'].median():.2f} s")
    col3.metric("Median gait risk score", f"{valid['risk_score'].median():.1f}/100")
    abnormal_segments = int(valid["flag_abnormal_gait"].sum())
    st.caption(f"{abnormal_segments}/{len(valid)} segments flagged abnormal gait.")

    video_ids = sorted(gait_df["video_id"].unique())
    selected_video_id = st.segmented_control(
        None, video_ids, default=video_ids[0], key=f"video_select_{patient_id}",
    )
    if selected_video_id is None:  # segmented_control allows deselecting back to None
        selected_video_id = video_ids[0]

    video_col, table_col = st.columns([1, 1])
    with video_col:
        render_video_player(patient_id, selected_video_id)
    with table_col:
        filtered_df = gait_df[gait_df["video_id"] == selected_video_id]
        st.dataframe(_style_abnormal_rows(filtered_df), use_container_width=True, hide_index=True, height=460)


def render_audio_section(patient_id):
    st.subheader("Audio - consultation distress analysis", anchor="audio")
    audio_row = query_df(
        "SELECT * FROM audio_scores WHERE patient_id = ? ORDER BY processed_at DESC, id DESC LIMIT 1",
        (patient_id,),
    )
    if audio_row.empty:
        st.info("No audio_scores row for this patient yet - run `make run-audio`.")
        return
    row = audio_row.iloc[0]

    col1, col2, col3 = st.columns(3)
    col1.metric("Distress score", f"{row['distress_score']:.0f}/100")
    col2.metric("Fatigue mentions", int(row["fatigue_mentions"]))
    col3.metric("Pain mentions", int(row["pain_mentions"]))

    flags = json.loads(row["flags"]) if row["flags"] else {}
    active_flags = [k for k, v in flags.items() if v]
    if active_flags:
        st.caption("Flags: " + ", ".join(active_flags))

    audio_path = BLOB_STORE_DIR / patient_id / "consultation.wav"
    if audio_path.exists():
        st.audio(str(audio_path))

    transcript_path = BLOB_STORE_DIR / patient_id / "diarized_transcript.json"
    if transcript_path.exists():
        segments = json.loads(transcript_path.read_text(encoding="utf-8"))["segments"]
        segments_df = pd.DataFrame(segments)
        flag_columns = ["fatigue_mentioned", "pain_mentioned", "anxiety_mentioned"]
        for col in flag_columns:
            if col not in segments_df.columns:
                segments_df[col] = False
        display_df = segments_df[["start", "end", "role", "text", *flag_columns]]
        st.markdown("**Diarized transcript**")
        st.dataframe(
            _style_flagged_transcript_rows(display_df),
            use_container_width=True, hide_index=True,
        )


def render_tabular_section(patient_id):
    st.subheader("Tabular - bone density / prescription anomaly detection", anchor="tabular")
    anomaly_row = query_df(
        "SELECT * FROM anomaly_scores WHERE patient_id = ? ORDER BY processed_at DESC, id DESC LIMIT 1",
        (patient_id,),
    )
    if anomaly_row.empty:
        st.info("No anomaly_scores row for this patient yet - run `make run-tabular`.")
        return
    row = anomaly_row.iloc[0]

    col1, col2 = st.columns(2)
    op_label = "Positive" if row["op_prediction"] == 1 else "Negative"
    col1.metric("OP prediction (latest visit)", op_label, help="Run on this "
                "patient's most recent synthetic visit - a snapshot classification, not a trend.")
    col2.metric("OP risk probability", f"{row['op_prediction_confidence'] * 100:.0f}%")
    st.caption(
        "Disclosed model limitation: "
        "OP=1 recall is only 0.64 on the original evaluation - the model misses ~4 in "
        "10 real osteoporosis-positive cases. Treat a Negative prediction as inconclusive, "
        "not a clean bill of health."
    )

    col1, col2 = st.columns(2)
    col1.metric("Anomaly risk score", f"{row['bone_density_risk_score']:.0f}/100", help="Rule-based - "
                "T-score decline across visits + prescription changes, not from the classifier above.")
    col2.metric("Prescription discontinuation flag", "Yes" if row["prescription_flag"] else "No")
    st.caption(f"T-score trend: {row['t_score_trend']}")

    history_path = BLOB_STORE_DIR / patient_id / "bone_density_history.csv"
    if history_path.exists():
        history_df = pd.read_csv(history_path)
        st.line_chart(history_df.set_index("visit_index")[["FNT", "TLT"]])
        with st.expander("Full visit history"):
            st.dataframe(history_df, use_container_width=True, hide_index=True)


def render_aggregated_section(patient_id):
    aggregated_row = query_df(
        "SELECT * FROM aggregated_assessments WHERE patient_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
        (patient_id,),
    )
    if aggregated_row.empty:
        st.info("No aggregated_assessments row for this patient yet - run `make run-aggregation`.")
        return
    row = aggregated_row.iloc[0]
    level = row["combined_risk_level"]

    st.subheader(f"Combined risk: :{RISK_COLORS.get(level, 'gray')}[{level}]", anchor="aggregated-assessment")
    # Drop the rationale's own leading "Patient ID: ..." line - render_patient_header() already shows it.
    rationale_lines = row["rationale"].split("\n")
    st.text("\n".join(rationale_lines[1:] if rationale_lines[0].startswith("Patient ID:") else rationale_lines))

    alert_row = query_df(
        "SELECT * FROM alerts WHERE aggregated_assessment_id = ? ORDER BY created_at DESC, id DESC LIMIT 1",
        (row["id"],),
    )
    if not alert_row.empty:
        st.error(f"ALERT: {alert_row.iloc[0]['message']}")


def render_patient_alerts_section(patient_id):
    """This patient's own alert history, most recent first. Complements the
    all-patients overview on app/pages/1_All_Alerts.py rather than duplicating it."""
    st.subheader("Alerts for this patient", anchor="alerts")
    alerts_df = query_df(
        "SELECT alert_level, message, created_at FROM alerts WHERE patient_id = ? "
        "ORDER BY created_at DESC, id DESC",
        (patient_id,),
    )
    if alerts_df.empty:
        st.info("No alerts for this patient yet.")
        return
    st.dataframe(alerts_df, use_container_width=True, hide_index=True)


def main():
    st.set_page_config(page_title="Osteoporosis Multimodal Monitoring", layout="wide")
    st.title("Osteoporosis Multimodal Monitoring")

    if not DB_PATH.exists():
        st.error(f"{DB_PATH} not found - run `make setup-dataset && make generate-dataset` "
                 "and the modality services first.")
        return

    patient_ids = load_patient_ids()
    if not patient_ids:
        st.warning("No patients in the database yet - run the video/audio/tabular services first.")
        return

    # Priority: a cross-page jump from 1_All_Alerts.py (via st.session_state, popped so
    # it doesn't override later reruns), else ?patient_id=... from the URL.
    # st.switch_page() lands on the target page's bare URL, dropping any query string
    # set beforehand - so session_state, not query_params, is what carries the jump.
    requested_patient_id = st.session_state.pop("requested_patient_id", None) or st.query_params.get("patient_id")
    default_index = patient_ids.index(requested_patient_id) if requested_patient_id in patient_ids else 0
    patient_id = st.sidebar.selectbox("Patient", patient_ids, index=default_index)
    st.query_params["patient_id"] = patient_id

    st.sidebar.divider()
    st.sidebar.caption("Jump to")
    st.sidebar.markdown(
        "- [Patient info](#patient-info)\n"
        "- [Aggregated assessment](#aggregated-assessment)\n"
        "- [Video](#video)\n"
        "- [Audio](#audio)\n"
        "- [Tabular](#tabular)\n"
        "- [Alerts](#alerts)"
    )

    render_patient_header(patient_id)
    render_aggregated_section(patient_id)
    st.divider()
    render_video_section(patient_id)
    st.divider()
    render_audio_section(patient_id)
    st.divider()
    render_tabular_section(patient_id)
    st.divider()
    render_patient_alerts_section(patient_id)


if __name__ == "__main__":
    main()
