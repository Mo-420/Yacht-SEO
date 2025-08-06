"""Utility helpers for reading and writing yacht data to Google Sheets.

Environment variables expected (or Streamlit Cloud secrets):
    GOOGLE_SHEET_CREDS – full JSON of a Google service-account, one line.
    SHEET_ID           – ID of the target Google Sheet.
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from typing import Any

import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

_SCOPES: list[str] = ["https://www.googleapis.com/auth/spreadsheets"]


def _creds() -> Credentials:
    creds_json = os.getenv("GOOGLE_SHEET_CREDS")
    if not creds_json:
        raise RuntimeError(
            "GOOGLE_SHEET_CREDS not set; add your service-account JSON to env or Streamlit secrets."
        )
    info: dict[str, Any] = json.loads(creds_json)
    return Credentials.from_service_account_info(info, scopes=_SCOPES)


def _sheet_id() -> str:
    sid = os.getenv("SHEET_ID")
    if not sid:
        raise RuntimeError("SHEET_ID env var missing.")
    return sid


@lru_cache(maxsize=1)
def _client() -> gspread.Client:
    return gspread.authorize(_creds())


@lru_cache(maxsize=None)
def _ws(tab: str) -> gspread.Worksheet:
    return _client().open_by_key(_sheet_id()).worksheet(tab)


# ---------------------------------------------------------------------------
# Public helpers
# ---------------------------------------------------------------------------


def read_df(tab: str = "Sheet1") -> pd.DataFrame:
    """Return a DataFrame of all rows (as records) from *tab*."""
    return pd.DataFrame(_ws(tab).get_all_records())


def write_df(df: pd.DataFrame, tab: str = "Sheet1") -> None:
    """Overwrite *tab* with *df*, keeping headers."""
    ws = _ws(tab)
    ws.clear()
    ws.update([df.columns.tolist()] + df.values.tolist())