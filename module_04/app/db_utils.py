"""Shared DB access helpers for app/Patient_Profile.py and app/pages/*.py."""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

REPO_ROOT = Path(__file__).resolve().parents[1]
DB_PATH = REPO_ROOT / "db" / "hospital.sqlite"
BLOB_STORE_DIR = REPO_ROOT / "db" / "blob_store"


@st.cache_resource
def get_connection():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def query_df(sql, params=()):
    return pd.read_sql_query(sql, get_connection(), params=params)
