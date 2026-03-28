"""
db/asset_repo.py — CRUD operations for all asset types
"""

from __future__ import annotations
import sqlite3
from datetime import datetime, timezone
from typing import Optional

from models.asset import Asset, Operator, SafeHouse, Cache, TxSite, AssetType, AssetStatus, TxType
from db.database import get_connection


def _now() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def _row_to_asset(conn: sqlite3.Connection, row: sqlite3.Row) -> Asset:
    """Hydrate a full asset object from an assets row."""
    try:
        t = AssetType(row["asset_type"])
    except ValueError:
        t = row["asset_type"]   # custom type — keep as plain string

    base = dict(
        id          = row["id"],
        asset_type  = t,
        name        = row["name"],
        lat         = row["lat"],
        lon         = row["lon"],
        status      = AssetStatus(row["status"]),
        status_note = row["status_note"],
        created_at  = row["created_at"],
        updated_at  = row["updated_at"],
        verified    = bool(row["verified"]),
    )

    if t == AssetType.OPERATOR:
        op = conn.execute(
            "SELECT callsign FROM operators WHERE asset_id = ?", (row["id"],)
        ).fetchone()
        skill_rows = conn.execute(
            """SELECT s.name FROM skillsets s
               JOIN operator_skillsets os ON s.id = os.skillset_id
               WHERE os.operator_id = ?""",
            (row["id"],),
        ).fetchall()
        return Operator(
            **base,
            callsign = op["callsign"] if op else "",
            skills   = [r["name"] for r in skill_rows],
        )

    elif t == AssetType.SAFEHOUSE:
        sh = conn.execute(
            "SELECT codename, capacity FROM safehouses WHERE asset_id = ?", (row["id"],)
        ).fetchone()
        return SafeHouse(
            **base,
            codename = sh["codename"] if sh else "",
            capacity = sh["capacity"] if sh else 0,
        )

    elif t == AssetType.CACHE:
        c = conn.execute(
            "SELECT contents FROM caches WHERE asset_id = ?", (row["id"],)
        ).fetchone()
        return Cache(**base, contents=c["contents"] if c else "")

    elif t == AssetType.TXSITE:
        tx = conn.execute(
            "SELECT frequency, tx_type FROM txsites WHERE asset_id = ?", (row["id"],)
        ).fetchone()
        return TxSite(
            **base,
            frequency = tx["frequency"] if tx else 0.0,
            tx_type   = TxType(tx["tx_type"]) if tx else TxType.RNODE,
        )

    return Asset(**base)


def get_all() -> list[Asset]:
    conn = get_connection()
    rows = conn.execute("SELECT * FROM assets ORDER BY asset_type, name").fetchall()
    result = [_row_to_asset(conn, r) for r in rows]
    conn.close()
    return result


def get_by_id(asset_id: int) -> Optional[Asset]:
    conn = get_connection()
    row = conn.execute("SELECT * FROM assets WHERE id = ?", (asset_id,)).fetchone()
    result = _row_to_asset(conn, row) if row else None
    conn.close()
    return result


def save(asset: Asset) -> Asset:
    """Insert or update an asset. Returns the asset with id populated."""
    conn = get_connection()
    now = _now()

    if asset.id is None:
        asset.created_at = now
        asset.updated_at = now
        type_str = asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type)
        cur = conn.execute(
            """INSERT INTO assets (asset_type, name, lat, lon, status, status_note, created_at, updated_at, verified)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (type_str, asset.name, asset.lat, asset.lon,
             asset.status.value, asset.status_note, asset.created_at, asset.updated_at,
             int(asset.verified)),
        )
        asset.id = cur.lastrowid
    else:
        asset.updated_at = now
        cur = conn.execute(
            """UPDATE assets SET name=?, lat=?, lon=?, status=?, status_note=?, updated_at=?, verified=?
               WHERE id=?""",
            (asset.name, asset.lat, asset.lon,
             asset.status.value, asset.status_note, asset.updated_at, int(asset.verified), asset.id),
        )
        if cur.rowcount == 0:
            # Asset doesn't exist on this node yet — insert preserving the original ID
            type_str = asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type)
            conn.execute(
                """INSERT INTO assets (id, asset_type, name, lat, lon, status, status_note, created_at, updated_at, verified)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (asset.id, type_str, asset.name, asset.lat, asset.lon,
                 asset.status.value, asset.status_note, asset.created_at or now, asset.updated_at,
                 int(asset.verified)),
            )

    _save_type_fields(conn, asset)
    conn.commit()
    conn.close()
    return asset


def _save_type_fields(conn: sqlite3.Connection, asset: Asset):
    if isinstance(asset, Operator):
        conn.execute(
            "INSERT OR REPLACE INTO operators (asset_id, callsign) VALUES (?, ?)",
            (asset.id, asset.callsign),
        )
        conn.execute(
            "DELETE FROM operator_skillsets WHERE operator_id = ?", (asset.id,)
        )
        for skill_name in asset.skills:
            conn.execute(
                "INSERT OR IGNORE INTO skillsets (name) VALUES (?)", (skill_name,)
            )
            row = conn.execute(
                "SELECT id FROM skillsets WHERE name = ?", (skill_name,)
            ).fetchone()
            conn.execute(
                "INSERT OR IGNORE INTO operator_skillsets (operator_id, skillset_id) VALUES (?, ?)",
                (asset.id, row["id"]),
            )

    elif isinstance(asset, SafeHouse):
        conn.execute(
            "INSERT OR REPLACE INTO safehouses (asset_id, codename, capacity) VALUES (?, ?, ?)",
            (asset.id, asset.codename, asset.capacity),
        )

    elif isinstance(asset, Cache):
        conn.execute(
            "INSERT OR REPLACE INTO caches (asset_id, contents) VALUES (?, ?)",
            (asset.id, asset.contents),
        )

    elif isinstance(asset, TxSite):
        conn.execute(
            "INSERT OR REPLACE INTO txsites (asset_id, frequency, tx_type) VALUES (?, ?, ?)",
            (asset.id, asset.frequency, asset.tx_type.value),
        )


def delete(asset_id: int):
    conn = get_connection()
    conn.execute("DELETE FROM assets WHERE id = ?", (asset_id,))
    conn.commit()
    conn.close()


def get_all_skills() -> list[str]:
    """Return all known skillset names (predefined + custom)."""
    conn = get_connection()
    rows = conn.execute("SELECT name FROM skillsets ORDER BY name").fetchall()
    conn.close()
    return [r["name"] for r in rows]
