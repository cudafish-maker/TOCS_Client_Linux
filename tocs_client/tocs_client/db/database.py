"""
db/database.py — SQLite connection factory and schema management
"""

import os
import sqlite3
from models.asset import PREDEFINED_SKILLS

DB_FILE   = "tocs.db"
TILE_FILE = "tocs_tiles.db"

_SCHEMA = """
PRAGMA foreign_keys = ON;
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS assets (
    id          INTEGER PRIMARY KEY,
    asset_type  TEXT    NOT NULL,
    name        TEXT    NOT NULL,
    lat         REAL    NOT NULL,
    lon         REAL    NOT NULL,
    status      TEXT    NOT NULL DEFAULT 'Unknown',
    status_note TEXT    NOT NULL DEFAULT '',
    created_at  TEXT    NOT NULL,
    updated_at  TEXT    NOT NULL,
    verified    INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS operators (
    asset_id    INTEGER PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
    callsign    TEXT NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS skillsets (
    id    INTEGER PRIMARY KEY,
    name  TEXT NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS operator_skillsets (
    operator_id  INTEGER NOT NULL REFERENCES assets(id) ON DELETE CASCADE,
    skillset_id  INTEGER NOT NULL REFERENCES skillsets(id) ON DELETE CASCADE,
    PRIMARY KEY (operator_id, skillset_id)
);

CREATE TABLE IF NOT EXISTS safehouses (
    asset_id  INTEGER PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
    codename  TEXT    NOT NULL DEFAULT '',
    capacity  INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS caches (
    asset_id  INTEGER PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
    contents  TEXT    NOT NULL DEFAULT ''
);

CREATE TABLE IF NOT EXISTS txsites (
    asset_id   INTEGER PRIMARY KEY REFERENCES assets(id) ON DELETE CASCADE,
    frequency  REAL    NOT NULL DEFAULT 0.0,
    tx_type    TEXT    NOT NULL DEFAULT 'RNode'
);

CREATE TABLE IF NOT EXISTS sitreps (
    id         INTEGER PRIMARY KEY,
    title      TEXT NOT NULL,
    body       TEXT NOT NULL,
    severity   TEXT NOT NULL DEFAULT 'Routine',
    asset_id   INTEGER REFERENCES assets(id) ON DELETE SET NULL,
    lat        REAL,
    lon        REAL,
    timestamp  TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS asset_type_defs (
    type_key   TEXT    PRIMARY KEY,
    name       TEXT    NOT NULL,
    color      TEXT    NOT NULL DEFAULT '#cdd6f4',
    is_builtin INTEGER NOT NULL DEFAULT 0
);

CREATE TABLE IF NOT EXISTS users (
    id            INTEGER PRIMARY KEY,
    callsign      TEXT    NOT NULL UNIQUE,
    password_hash TEXT    NOT NULL,
    salt          TEXT    NOT NULL,
    operator_id   INTEGER REFERENCES assets(id) ON DELETE SET NULL
);

CREATE INDEX IF NOT EXISTS idx_assets_type       ON assets(asset_type);
CREATE INDEX IF NOT EXISTS idx_assets_status     ON assets(status);
CREATE INDEX IF NOT EXISTS idx_sitreps_asset     ON sitreps(asset_id);
CREATE INDEX IF NOT EXISTS idx_sitreps_severity  ON sitreps(severity);
CREATE INDEX IF NOT EXISTS idx_sitreps_timestamp ON sitreps(timestamp);
CREATE INDEX IF NOT EXISTS idx_users_callsign    ON users(callsign);
"""

_TILE_SCHEMA = """
PRAGMA journal_mode = WAL;

CREATE TABLE IF NOT EXISTS tiles (
    zoom_level  INTEGER NOT NULL,
    tile_column INTEGER NOT NULL,
    tile_row    INTEGER NOT NULL,
    tile_data   BLOB    NOT NULL,
    PRIMARY KEY (zoom_level, tile_column, tile_row)
);

CREATE TABLE IF NOT EXISTS metadata (
    name   TEXT PRIMARY KEY,
    value  TEXT
);
"""


def _data_dir() -> str:
    """Returns the directory where DB files are stored (next to this package)."""
    return os.path.join(os.path.dirname(__file__), "..", "data")


def get_connection(db_file: str = None) -> sqlite3.Connection:
    """Open a connection to the main TOCS database with WAL and FK enabled."""
    if db_file is None:
        db_file = os.path.join(_data_dir(), DB_FILE)
    os.makedirs(os.path.dirname(db_file), exist_ok=True)
    conn = sqlite3.connect(db_file, timeout=15)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def get_tile_connection() -> sqlite3.Connection:
    """Open a connection to the tile cache database."""
    path = os.path.join(_data_dir(), TILE_FILE)
    os.makedirs(os.path.dirname(path), exist_ok=True)
    conn = sqlite3.connect(path)
    conn.execute("PRAGMA journal_mode = WAL")
    return conn


def init_db():
    """Create all tables and seed predefined skillsets."""
    conn = get_connection()
    conn.executescript(_SCHEMA)
    conn.commit()

    # Migrate: add verified column if it doesn't exist yet
    try:
        conn.execute("ALTER TABLE assets ADD COLUMN verified INTEGER NOT NULL DEFAULT 1")
        conn.commit()
    except sqlite3.OperationalError:
        pass  # column already exists

    # Seed built-in asset type definitions
    _BUILTIN_TYPES = [
        ("operator",  "Operator",         "#89b4fa"),
        ("safehouse", "Safe House",        "#a6e3a1"),
        ("cache",     "Cache",             "#fab387"),
        ("txsite",    "Transmitter Site",  "#cba6f7"),
    ]
    for type_key, name, color in _BUILTIN_TYPES:
        conn.execute(
            "INSERT OR IGNORE INTO asset_type_defs (type_key, name, color, is_builtin) VALUES (?, ?, ?, 1)",
            (type_key, name, color),
        )
    conn.commit()

    # Seed predefined skills (ignore if already present)
    for skill in PREDEFINED_SKILLS:
        conn.execute(
            "INSERT OR IGNORE INTO skillsets (name) VALUES (?)", (skill,)
        )
    conn.commit()
    conn.close()

    # Init tile DB
    tile_conn = get_tile_connection()
    tile_conn.executescript(_TILE_SCHEMA)
    tile_conn.commit()
    tile_conn.close()
