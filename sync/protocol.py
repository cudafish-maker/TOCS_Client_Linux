"""
sync/protocol.py — Serialization helpers and message type constants

Wire format: [1 byte: msg_type][1 byte: encoding][N bytes: payload]
  0x4d ('M'): msgpack, uncompressed
  0x5a ('Z'): msgpack + zlib compressed

Payloads larger than _COMPRESS_THRESHOLD bytes are automatically compressed.
msgpack is ~35% smaller than JSON; zlib adds another ~40% on text-heavy payloads
(e.g. SITREP bodies), which matters a lot over slow RNode LoRa links.
"""

import zlib
import msgpack

from models.asset import Asset, Operator, SafeHouse, Cache, TxSite, AssetType, AssetStatus, TxType
from models.sitrep import Sitrep, Severity

# ── Message type constants ────────────────────────────────────────────────────
MSG_ASSET        = b'\x01'   # server → client: add/update asset
MSG_SITREP       = b'\x02'   # server → client: add/update sitrep
MSG_HELLO        = b'\x03'   # client → server: identify + request sync
MSG_ASSET_UPDATE = b'\x04'   # client → server: own profile update
MSG_SITREP_NEW   = b'\x05'   # client → server: new sitrep
MSG_ASSET_DELETE = b'\x06'   # server → client: asset deleted
MSG_SYNC_START      = b'\x07'   # server → client: sync starting
MSG_SYNC_DONE       = b'\x08'   # server → client: sync complete
MSG_SITREP_DELETE   = b'\x09'   # server → client: sitrep deleted
MSG_AUTH_REGISTER   = b'\x0A'   # client → server: create account
MSG_AUTH_LOGIN      = b'\x0B'   # client → server: authenticate
MSG_AUTH_OK         = b'\x0C'   # server → client: auth success
MSG_AUTH_FAIL       = b'\x0D'   # server → client: auth failure
MSG_ASSET_TYPE_DEF  = b'\x0E'   # server → client: asset type definition
MSG_ASSET_TYPE_DEL  = b'\x0F'   # server → client: asset type deleted
MSG_ASSET_VERIFY    = b'\x11'   # client → server: request asset verification
MSG_RNODE_CONFIG    = b'\x12'   # server → client: RNode radio parameters

# ── Encoding flags ────────────────────────────────────────────────────────────
_ENC_MSGPACK = b'\x4d'   # 'M' — msgpack, no compression
_ENC_ZLIB    = b'\x5a'   # 'Z' — msgpack + zlib

_COMPRESS_THRESHOLD = 64   # bytes: compress payloads larger than this


# ── Pack / unpack ─────────────────────────────────────────────────────────────

def pack(msg_type: bytes, payload: dict) -> bytes:
    data = msgpack.packb(payload, use_bin_type=True)
    if len(data) > _COMPRESS_THRESHOLD:
        return msg_type + _ENC_ZLIB + zlib.compress(data, level=6)
    return msg_type + _ENC_MSGPACK + data


def unpack(data: bytes) -> tuple[bytes, dict]:
    msg_type = data[:1]
    enc      = data[1:2]
    payload  = data[2:]
    if enc == _ENC_ZLIB:
        payload = zlib.decompress(payload)
    return msg_type, msgpack.unpackb(payload, raw=False)


def pack_sync_start(n_types: int, n_assets: int, n_sitreps: int) -> bytes:
    return pack(MSG_SYNC_START, {"types": n_types, "assets": n_assets, "sitreps": n_sitreps})


def pack_sync_done() -> bytes:
    return pack(MSG_SYNC_DONE, {})


# ── Asset serialization ───────────────────────────────────────────────────────

def asset_to_dict(asset: Asset) -> dict:
    type_key = asset.asset_type.value if isinstance(asset.asset_type, AssetType) else str(asset.asset_type)
    d = {
        "id":   asset.id,
        "t":    type_key,
        "n":    asset.name,
        "la":   asset.lat,
        "lo":   asset.lon,
        "s":    asset.status.value,
        "sn":   asset.status_note,
        "ca":   asset.created_at,
        "ua":   asset.updated_at,
        "v":    int(asset.verified),
    }
    if isinstance(asset, Operator):
        d["cs"] = asset.callsign
        d["sk"] = asset.skills
    elif isinstance(asset, SafeHouse):
        d["cn"] = asset.codename
        d["cp"] = asset.capacity
    elif isinstance(asset, Cache):
        d["co"] = asset.contents
    elif isinstance(asset, TxSite):
        d["fr"] = asset.frequency
        d["tt"] = asset.tx_type.value
    return d


def dict_to_asset(d: dict) -> Asset:
    # Support both short keys (new) and long keys (old, for migration)
    def g(short, long, default=None):
        return d.get(short, d.get(long, default))

    type_key = g("t", "asset_type")
    try:
        t = AssetType(type_key)
    except (ValueError, TypeError):
        t = type_key

    base = dict(
        id          = g("id", "id"),
        asset_type  = t,
        name        = g("n", "name", ""),
        lat         = g("la", "lat", 0.0),
        lon         = g("lo", "lon", 0.0),
        status      = AssetStatus(g("s", "status", "Unknown")),
        status_note = g("sn", "status_note", ""),
        created_at  = g("ca", "created_at", ""),
        updated_at  = g("ua", "updated_at", ""),
        verified    = bool(g("v", "verified", True)),
    )
    if t == AssetType.OPERATOR:
        return Operator(**base, callsign=g("cs", "callsign", ""), skills=g("sk", "skills", []))
    elif t == AssetType.SAFEHOUSE:
        return SafeHouse(**base, codename=g("cn", "codename", ""), capacity=g("cp", "capacity", 0))
    elif t == AssetType.CACHE:
        return Cache(**base, contents=g("co", "contents", ""))
    elif t == AssetType.TXSITE:
        return TxSite(**base, frequency=g("fr", "frequency", 0.0),
                      tx_type=TxType(g("tt", "tx_type", "RNode")))
    return Asset(**base)


# ── Sitrep serialization ──────────────────────────────────────────────────────

def sitrep_to_dict(sitrep: Sitrep) -> dict:
    return {
        "id": sitrep.id,
        "ti": sitrep.title,
        "b":  sitrep.body,
        "sv": sitrep.severity.value,
        "ai": sitrep.asset_id,
        "la": sitrep.lat,
        "lo": sitrep.lon,
        "ts": sitrep.timestamp,
    }


def dict_to_sitrep(d: dict) -> Sitrep:
    def g(short, long, default=None):
        return d.get(short, d.get(long, default))

    return Sitrep(
        id        = g("id", "id"),
        title     = g("ti", "title", ""),
        body      = g("b",  "body",  ""),
        severity  = Severity(g("sv", "severity", "Routine")),
        asset_id  = g("ai", "asset_id"),
        lat       = g("la", "lat"),
        lon       = g("lo", "lon"),
        timestamp = g("ts", "timestamp", ""),
    )
