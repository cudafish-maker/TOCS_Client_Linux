"""
db/session.py — Local session cache for offline login
"""

from __future__ import annotations
import hashlib
import json
import os
from typing import Optional


def _session_file() -> str:
    data_dir = os.path.join(os.path.dirname(__file__), "..", "data")
    return os.path.join(data_dir, "session.json")


def load() -> Optional[dict]:
    path = _session_file()
    if os.path.exists(path):
        try:
            with open(path) as f:
                return json.load(f)
        except Exception:
            pass
    return None


def save(callsign: str, operator_id: int, password: str):
    """Hash the password with a fresh salt and persist for offline use."""
    salt    = os.urandom(16).hex()
    pw_hash = hashlib.sha256((salt + ":" + password).encode()).hexdigest()
    path    = _session_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump({
            "callsign":    callsign.upper(),
            "operator_id": operator_id,
            "pw_hash":     pw_hash,
            "salt":        salt,
        }, f, indent=2)


def verify_offline(callsign: str, password: str) -> Optional[int]:
    """
    Returns operator_id if callsign + password match the cached session,
    None otherwise.
    """
    data = load()
    if not data:
        return None
    if data.get("callsign", "").upper() != callsign.upper():
        return None
    computed = hashlib.sha256(
        (data["salt"] + ":" + password).encode()
    ).hexdigest()
    if computed == data["pw_hash"]:
        return data["operator_id"]
    return None


def get_last_callsign() -> Optional[str]:
    data = load()
    return data.get("callsign") if data else None


def save_last_sync(timestamp: float):
    """Persist the Unix timestamp of the last successful sync."""
    data = load() or {}
    data["last_sync"] = timestamp
    path = _session_file()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_last_sync() -> float:
    """Return Unix timestamp of last successful sync, or 0.0 (triggers full sync)."""
    data = load()
    return float(data.get("last_sync", 0.0)) if data else 0.0
