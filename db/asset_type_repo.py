"""
db/asset_type_repo.py — CRUD for asset type definitions (built-in + custom)
"""

from __future__ import annotations
import re
from typing import Optional
from db.database import get_connection


def _slugify(name: str) -> str:
    """Turn a display name into a safe type_key slug, e.g. 'Food Bank' → 'food_bank'."""
    return re.sub(r'[^a-z0-9]+', '_', name.lower()).strip('_')


def get_all() -> list[dict]:
    """Return all type defs — built-ins first, then custom alphabetically."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT type_key, name, color, is_builtin FROM asset_type_defs "
        "ORDER BY is_builtin DESC, name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_custom() -> list[dict]:
    """Return only user-defined (non-builtin) type defs."""
    conn = get_connection()
    rows = conn.execute(
        "SELECT type_key, name, color FROM asset_type_defs "
        "WHERE is_builtin = 0 ORDER BY name"
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def save(type_key: str, name: str, color: str):
    """Insert or update a custom asset type definition."""
    conn = get_connection()
    conn.execute(
        "INSERT OR REPLACE INTO asset_type_defs (type_key, name, color, is_builtin) "
        "VALUES (?, ?, ?, 0)",
        (type_key, name, color),
    )
    conn.commit()
    conn.close()


def save_from_sync(type_key: str, name: str, color: str):
    """Save a type def received from the server (preserves is_builtin flag)."""
    conn = get_connection()
    existing = conn.execute(
        "SELECT is_builtin FROM asset_type_defs WHERE type_key = ?", (type_key,)
    ).fetchone()
    is_builtin = existing["is_builtin"] if existing else 0
    conn.execute(
        "INSERT OR REPLACE INTO asset_type_defs (type_key, name, color, is_builtin) "
        "VALUES (?, ?, ?, ?)",
        (type_key, name, color, is_builtin),
    )
    conn.commit()
    conn.close()


def delete(type_key: str):
    """Delete a custom type (built-ins are protected)."""
    conn = get_connection()
    conn.execute(
        "DELETE FROM asset_type_defs WHERE type_key = ? AND is_builtin = 0",
        (type_key,),
    )
    conn.commit()
    conn.close()


def get_color(type_key: str, default: str = "#cdd6f4") -> str:
    conn = get_connection()
    row = conn.execute(
        "SELECT color FROM asset_type_defs WHERE type_key = ?", (type_key,)
    ).fetchone()
    conn.close()
    return row["color"] if row else default


def get_name(type_key: str) -> str:
    conn = get_connection()
    row = conn.execute(
        "SELECT name FROM asset_type_defs WHERE type_key = ?", (type_key,)
    ).fetchone()
    conn.close()
    return row["name"] if row else type_key.replace("_", " ").capitalize()


def make_unique_key(name: str) -> str:
    """Generate a unique type_key slug, appending a counter if already taken."""
    base = _slugify(name) or "custom"
    conn = get_connection()
    existing = {r["type_key"] for r in conn.execute(
        "SELECT type_key FROM asset_type_defs"
    ).fetchall()}
    conn.close()
    key = base
    n = 2
    while key in existing:
        key = f"{base}_{n}"
        n += 1
    return key
