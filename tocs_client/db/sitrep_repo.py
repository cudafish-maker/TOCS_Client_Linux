"""
db/sitrep_repo.py — CRUD operations for SITREPs
"""

from __future__ import annotations
from datetime import datetime, timezone
from typing import Optional

from models.sitrep import Sitrep, Severity
from db.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_sitrep(row) -> Sitrep:
    return Sitrep(
        id        = row["id"],
        title     = row["title"],
        body      = row["body"],
        severity  = Severity(row["severity"]),
        asset_id  = row["asset_id"],
        lat       = row["lat"],
        lon       = row["lon"],
        timestamp = row["timestamp"],
    )


def get_all() -> list[Sitrep]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sitreps ORDER BY timestamp DESC"
    ).fetchall()
    conn.close()
    return [_row_to_sitrep(r) for r in rows]


def get_by_asset(asset_id: int) -> list[Sitrep]:
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM sitreps WHERE asset_id = ? ORDER BY timestamp DESC",
        (asset_id,),
    ).fetchall()
    conn.close()
    return [_row_to_sitrep(r) for r in rows]


def get_by_id(sitrep_id: int) -> Optional[Sitrep]:
    conn = get_connection()
    row = conn.execute(
        "SELECT * FROM sitreps WHERE id = ?", (sitrep_id,)
    ).fetchone()
    conn.close()
    return _row_to_sitrep(row) if row else None


def save(sitrep: Sitrep) -> Sitrep:
    conn = get_connection()
    if not sitrep.timestamp:
        sitrep.timestamp = _now()

    if sitrep.id is None:
        cur = conn.execute(
            """INSERT INTO sitreps (title, body, severity, asset_id, lat, lon, timestamp)
               VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (sitrep.title, sitrep.body, sitrep.severity.value,
             sitrep.asset_id, sitrep.lat, sitrep.lon, sitrep.timestamp),
        )
        sitrep.id = cur.lastrowid
    else:
        cur = conn.execute(
            """UPDATE sitreps SET title=?, body=?, severity=?, asset_id=?, lat=?, lon=?
               WHERE id=?""",
            (sitrep.title, sitrep.body, sitrep.severity.value,
             sitrep.asset_id, sitrep.lat, sitrep.lon, sitrep.id),
        )
        if cur.rowcount == 0:
            try:
                conn.execute(
                    """INSERT INTO sitreps (id, title, body, severity, asset_id, lat, lon, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (sitrep.id, sitrep.title, sitrep.body, sitrep.severity.value,
                     sitrep.asset_id, sitrep.lat, sitrep.lon, sitrep.timestamp),
                )
            except Exception:
                # asset_id FK not yet on this node — store without asset link
                conn.execute(
                    """INSERT INTO sitreps (id, title, body, severity, asset_id, lat, lon, timestamp)
                       VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                    (sitrep.id, sitrep.title, sitrep.body, sitrep.severity.value,
                     None, sitrep.lat, sitrep.lon, sitrep.timestamp),
                )

    conn.commit()
    conn.close()
    return sitrep


def delete(sitrep_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM sitreps WHERE id = ?", (sitrep_id,))
    conn.commit()
    conn.close()
