"""
models/sitrep.py — SITREP dataclass and severity enum
"""

from __future__ import annotations
from dataclasses import dataclass
from enum import Enum
from typing import Optional


class Severity(str, Enum):
    ROUTINE   = "Routine"
    PRIORITY  = "Priority"
    FLASH     = "Flash"
    IMMEDIATE = "Immediate"


SEVERITY_COLORS = {
    Severity.ROUTINE:   "#89b4fa",   # blue
    Severity.PRIORITY:  "#f9e2af",   # yellow
    Severity.FLASH:     "#fab387",   # orange
    Severity.IMMEDIATE: "#f38ba8",   # red
}


@dataclass
class Sitrep:
    id:        Optional[int]
    title:     str
    body:      str
    severity:  Severity         = Severity.ROUTINE
    asset_id:  Optional[int]    = None   # linked asset (or None for position-only)
    lat:       Optional[float]  = None   # populated when not linked to an asset
    lon:       Optional[float]  = None
    timestamp: str              = ""
