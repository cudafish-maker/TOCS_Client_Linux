"""
models/asset.py — Asset dataclasses and enums for TOCS
"""

from __future__ import annotations
from dataclasses import dataclass, field
from enum import Enum
from typing import Optional


class AssetType(str, Enum):
    OPERATOR    = "operator"
    SAFEHOUSE   = "safehouse"
    CACHE       = "cache"
    TXSITE      = "txsite"


class AssetStatus(str, Enum):
    ACTIVE      = "Active"
    STANDBY     = "Standby"
    INACTIVE    = "Inactive"
    COMPROMISED = "Compromised"
    UNKNOWN     = "Unknown"


class TxType(str, Enum):
    RNODE    = "RNode"
    REPEATER = "Repeater"
    SIMPLEX  = "Simplex"
    OTHER    = "Other"


# Predefined skillsets — users can add custom ones to the DB
PREDEFINED_SKILLS = [
    "Medical",
    "Trauma Care",
    "Communications",
    "SIGINT",
    "Navigation",
    "Logistics",
    "Security",
    "Intelligence",
    "HUMINT",
    "Engineering",
    "Surveillance",
    "EOD",
    "K9",
    "Linguistics",
    "Leadership",
    "Transportation",
    "Cyber",
    "OSINT",
    "Reconnaissance",
]

# Map marker colors by asset type
ASSET_COLORS = {
    AssetType.OPERATOR:  "#89b4fa",   # blue
    AssetType.SAFEHOUSE: "#a6e3a1",   # green
    AssetType.CACHE:     "#fab387",   # orange
    AssetType.TXSITE:    "#cba6f7",   # purple
}

def get_asset_color(type_key) -> str:
    """Return marker color for any asset type (built-in or custom)."""
    if isinstance(type_key, AssetType):
        return ASSET_COLORS.get(type_key, "#cdd6f4")
    try:
        import db.asset_type_repo as _repo
        return _repo.get_color(str(type_key))
    except Exception:
        return "#cdd6f4"


def get_type_display_name(type_key) -> str:
    """Return display name for any asset type (built-in or custom)."""
    if isinstance(type_key, AssetType):
        return type_key.value.replace("_", " ").capitalize()
    try:
        import db.asset_type_repo as _repo
        return _repo.get_name(str(type_key))
    except Exception:
        return str(type_key).replace("_", " ").capitalize()


STATUS_COLORS = {
    AssetStatus.ACTIVE:      "#a6e3a1",   # green
    AssetStatus.STANDBY:     "#f9e2af",   # yellow
    AssetStatus.INACTIVE:    "#585b70",   # gray
    AssetStatus.COMPROMISED: "#f38ba8",   # red
    AssetStatus.UNKNOWN:     "#a6adc8",   # subtext
}


@dataclass
class Asset:
    """Base asset — all types share these fields."""
    id:          Optional[int]
    asset_type:  AssetType
    name:        str
    lat:         float
    lon:         float
    status:      AssetStatus = AssetStatus.UNKNOWN
    status_note: str         = ""
    created_at:  str         = ""
    updated_at:  str         = ""
    verified:    bool        = True


@dataclass
class Operator(Asset):
    callsign: str        = ""
    skills:   list[str]  = field(default_factory=list)

    def __post_init__(self):
        self.asset_type = AssetType.OPERATOR


@dataclass
class SafeHouse(Asset):
    codename: str = ""
    capacity: int = 0

    def __post_init__(self):
        self.asset_type = AssetType.SAFEHOUSE


@dataclass
class Cache(Asset):
    contents: str = ""

    def __post_init__(self):
        self.asset_type = AssetType.CACHE


@dataclass
class TxSite(Asset):
    frequency: float  = 0.0
    tx_type:   TxType = TxType.RNODE

    def __post_init__(self):
        self.asset_type = AssetType.TXSITE
