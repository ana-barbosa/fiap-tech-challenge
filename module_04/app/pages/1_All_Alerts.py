"""All Alerts - every alert across all patients, on its own page rather than embedded
in Patient_Profile.py, so it's unambiguous the list isn't scoped to one patient.

Each alert is a full-width st.button rather than st.dataframe row-selection, so a
click anywhere on the row navigates via st.switch_page - a button's return value is
only True on the rerun it was clicked, so no session_state guard against
re-triggering on reruns is needed.

The target patient is passed via st.session_state, not st.query_params: st.switch_page
lands on the target page's bare URL, dropping any query string set beforehand.
Patient_Profile.py reads and pops it once on load.
"""

import sys
from pathlib import Path

import streamlit as st

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from db_utils import query_df  # noqa: E402

st.set_page_config(page_title="All Alerts - Osteoporosis Multimodal Monitoring", layout="wide")
st.title("All Alerts")
st.caption("Every alert emitted by the aggregation service, across all patients. Click a row to open that patient's profile.")

alerts_df = query_df(
    "SELECT patient_id, alert_level, message, created_at FROM alerts ORDER BY created_at DESC, id DESC"
)

if alerts_df.empty:
    st.info("No alerts have fired yet - run `make run-aggregation` once all three modalities are scored.")
else:
    for i, alert in enumerate(alerts_df.itertuples()):
        label = f"🔴 {alert.patient_id} — {alert.alert_level} — {alert.message} ({alert.created_at})"
        if st.button(label, key=f"alert_row_{i}", use_container_width=True):
            st.session_state["requested_patient_id"] = alert.patient_id
            st.switch_page("Patient_Profile.py")
