"""Incremental storage so a run can be interrupted and resumed."""

import os
import sqlite3
from io import BytesIO

import pandas as pd

from config import DB_PATH, DATA_DIR
from models import Place

COLUMNS = [
    "place_id", "name", "address", "phone", "email", "website",
    "description", "category", "rating", "reviews",
    "latitude", "longitude", "distance_km", "maps_url", "run_id",
]


# ------------------------------------------------------------ 1. SCHEMA
def init_db() -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS places (
                place_id    TEXT PRIMARY KEY,
                name        TEXT,
                address     TEXT,
                phone       TEXT,
                email       TEXT,
                website     TEXT,
                description TEXT,
                category    TEXT,
                rating      REAL,
                reviews     INTEGER,
                latitude    REAL,
                longitude   REAL,
                distance_km REAL,
                maps_url    TEXT,
                run_id      TEXT,
                created_at  TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


# ------------------------------------------------------------- 2. WRITE
def save_place(place: Place, run_id: str) -> None:
    row = place.to_dict()
    row["run_id"] = run_id
    placeholders = ", ".join(["?"] * len(COLUMNS))
    with sqlite3.connect(DB_PATH) as connection:
        connection.execute(
            f"INSERT OR REPLACE INTO places ({', '.join(COLUMNS)}) VALUES ({placeholders})",
            [row.get(column) for column in COLUMNS],
        )


def known_place_ids(run_id: str) -> set:
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            "SELECT place_id FROM places WHERE run_id = ?", (run_id,)
        ).fetchall()
    return {row[0] for row in rows}


# -------------------------------------------------------------- 3. READ
def load_dataframe(run_id: str | None = None) -> pd.DataFrame:
    with sqlite3.connect(DB_PATH) as connection:
        if run_id:
            return pd.read_sql_query(
                "SELECT * FROM places WHERE run_id = ? ORDER BY distance_km",
                connection, params=(run_id,),
            )
        return pd.read_sql_query(
            "SELECT * FROM places ORDER BY created_at DESC", connection
        )


def list_runs() -> list:
    with sqlite3.connect(DB_PATH) as connection:
        rows = connection.execute(
            "SELECT run_id, COUNT(*) FROM places GROUP BY run_id ORDER BY MAX(created_at) DESC"
        ).fetchall()
    return rows


# ------------------------------------------------------------ 4. EXPORT
def dataframe_to_excel_bytes(frame: pd.DataFrame) -> bytes:
    buffer = BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        frame.to_excel(writer, index=False, sheet_name="results")
    return buffer.getvalue()


def dataframe_to_csv_bytes(frame: pd.DataFrame) -> bytes:
    return frame.to_csv(index=False).encode("utf-8-sig")
