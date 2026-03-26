"""
sync/protocol.py — Serialization helpers and message type constants
"""

import json
from models.asset import Asset, Operator, SafeHouse, Cache, TxSite, AssetType, AssetStatus, TxType
from models.sitrep import Sitrep, Severity

# Single-byte message type prefix for RNS packets
MSG_ASSET        = b'\x01'   # server → client: add/update asset
MSG_SITREP       = b'\x02'   # server → client: add/update sitrep
MSG_HELLO        = b'\x03'   # client → server: identify + request full sync
MSG_ASSET_UPDATE = b'\x04'   # client → server: own profile update
MSG_SITREP_NEW   = b'\x05'   # client → server: new sitrep
MSG_ASSET_DELETE = b'\x06'   # server → client: asset deleted
MSG_SYNC_START      = b'\x07'   # server → client: full sync starting
MSG_SYNC_DONE       = b'\x08'   # server → client: full sync complete
MSG_SITREP_DELETE   = b'\x09'   # server → client: sitrep deleted
MSG_AUTH_REGISTER   = b'\x0A'   # client → server: create account
MSG_AUTH_LOGIN      = b'\x0B'   # client → server: authenticate
MSG_AUTH_OK         = b'\x0C'   # server → client: auth success
MSG_AUTH_FAIL       = b'\x0D'   # server → client: auth failure
MSG_ASSET_TYPE_DEF  = b'\x0E'   # server → client: asset type definition
MSG_ASSET_TYPE_DEL  = b'\x0F'   # server → client: asset type deleted
MSG_ASSET_VERIFY    = b'\x11'   # client → server: request asset verification
MSG_RNODE_CONFIG    = b'\x12'   # server → client: RNode radio parameters


def asset_to_dict(asset: Asset) -> dict:
    # asset_type may be an AssetType enum (built-in) or a plain string (custom)
    type_key = asset.asset_type.value if isinstance(asset.asset_type, AssetType) else str(asset.asset_type)
    d = {
        "id":          asset.id,
        "asset_type":  type_key,
        "name":        asset.name,
        "lat":         asset.lat,
        "lon":         asset.lon,
        "status":      asset.status.value,
        "status_note": asset.status_note,
        "created_at":  asset.created_at,
        "updated_at":  asset.updated_at,
        "verified":    asset.verified,
    }
    if isinstance(asset, Operator):
        d["callsign"] = asset.callsign
        d["skills"]   = asset.skills
    elif isinstance(asset, SafeHouse):
        d["codename"] = asset.codename
        d["capacity"] = asset.capacity
    elif isinstance(asset, Cache):
        d["contents"] = asset.contents
    elif isinstance(asset, TxSite):
        d["frequency"] = asset.frequency
        d["tx_type"]   = asset.tx_type.value
    return d


def dict_to_asset(d: dict) -> Asset:
    try:
        t = AssetType(d["asset_type"])
    except ValueError:
        # Custom asset type — use base Asset with the raw string key
        t = d["asset_type"]
    base = dict(
        id          = d.get("id"),
        asset_type  = t,
        name        = d["name"],
        lat         = d["lat"],
        lon         = d["lon"],
        status      = AssetStatus(d.get("status", "Unknown")),
        status_note = d.get("status_note", ""),
        created_at  = d.get("created_at", ""),
        updated_at  = d.get("updated_at", ""),
        verified    = bool(d.get("verified", True)),
    )
    if t == AssetType.OPERATOR:
        return Operator(**base, callsign=d.get("callsign", ""), skills=d.get("skills", []))
    elif t == AssetType.SAFEHOUSE:
        return SafeHouse(**base, codename=d.get("codename", ""), capacity=d.get("capacity", 0))
    elif t == AssetType.CACHE:
        return Cache(**base, contents=d.get("contents", ""))
    elif t == AssetType.TXSITE:
        return TxSite(**base, frequency=d.get("frequency", 0.0),
                      tx_type=TxType(d.get("tx_type", "RNode")))
    # Custom type — base Asset with raw string type_key
    return Asset(**base)


def sitrep_to_dict(sitrep: Sitrep) -> dict:
    return {
        "id":        sitrep.id,
        "title":     sitrep.title,
        "body":      sitrep.body,
        "severity":  sitrep.severity.value,
        "asset_id":  sitrep.asset_id,
        "lat":       sitrep.lat,
        "lon":       sitrep.lon,
        "timestamp": sitrep.timestamp,
    }


def dict_to_sitrep(d: dict) -> Sitrep:
    return Sitrep(
        id        = d.get("id"),
        title     = d["title"],
        body      = d["body"],
        severity  = Severity(d.get("severity", "Routine")),
        asset_id  = d.get("asset_id"),
        lat       = d.get("lat"),
        lon       = d.get("lon"),
        timestamp = d.get("timestamp", ""),
    )


def pack(msg_type: bytes, payload: dict) -> bytes:
    return msg_type + json.dumps(payload).encode("utf-8")


def unpack(data: bytes) -> tuple[bytes, dict]:
    return data[:1], json.loads(data[1:].decode("utf-8"))


def pack_sync_start(n_types: int, n_assets: int, n_sitreps: int) -> bytes:
    return MSG_SYNC_START + json.dumps(
        {"types": n_types, "assets": n_assets, "sitreps": n_sitreps}
    ).encode("utf-8")


def pack_sync_done() -> bytes:
    return MSG_SYNC_DONE + b'{}'
