"""
sync/rnode_config.py — Read (and write) RNode settings from a Reticulum config file.

The Reticulum config uses a non-standard INI variant with [[double-bracket]] interface
sections.  This module provides a simple line-based parser so we don't need a dep.
"""

import os
import re

# Radio parameter keys — port is device-specific and excluded from server sync
RADIO_FIELDS = ("frequency", "bandwidth", "txpower", "spreadingfactor", "codingrate")


def read_rnode_config(rns_config_dir: str) -> dict | None:
    """
    Return a dict for the first RNodeInterface found in {rns_config_dir}/config.

    Keys: name, frequency, bandwidth, txpower, spreadingfactor, codingrate,
          port, enabled.
    Numeric fields are returned as int.  Returns None if no RNodeInterface exists.
    """
    config_path = os.path.join(rns_config_dir, "config")
    if not os.path.exists(config_path):
        return None

    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    in_interfaces   = False
    current_name    = None
    current_kvs: dict = {}
    sections: list    = []   # list of (name, kvs)

    for line in lines:
        stripped = line.strip()

        # Top-level [section]
        if re.match(r'^\[(?!\[)[^\]]+\]', stripped):
            if current_name is not None:
                sections.append((current_name, current_kvs))
            section_name = stripped[1:-1].strip()
            in_interfaces  = (section_name == "interfaces")
            current_name   = None
            current_kvs    = {}
            continue

        if not in_interfaces:
            continue

        # Interface sub-section [[Name]]
        m = re.match(r'^\[\[(.+)\]\]', stripped)
        if m:
            if current_name is not None:
                sections.append((current_name, current_kvs))
            current_name = m.group(1).strip()
            current_kvs  = {}
            continue

        # key = value
        if current_name and "=" in stripped and not stripped.startswith("#"):
            key, _, val = stripped.partition("=")
            current_kvs[key.strip().lower()] = val.strip()

    if current_name is not None:
        sections.append((current_name, current_kvs))

    for name, kvs in sections:
        if kvs.get("type", "").lower() == "rnodeinterface":
            result: dict = {"name": name}
            for field in RADIO_FIELDS:
                if field in kvs:
                    try:
                        result[field] = int(kvs[field])
                    except ValueError:
                        result[field] = kvs[field]
            result["port"]    = kvs.get("port", "")
            result["enabled"] = kvs.get("enabled", "yes")
            return result

    return None


def write_rnode_config(rns_config_dir: str, updates: dict) -> bool:
    """
    Update RADIO_FIELDS within the first RNodeInterface block.
    `updates` maps field name → new value (port is intentionally excluded).
    Returns True on success, False if no RNodeInterface block was found.
    """
    config_path = os.path.join(rns_config_dir, "config")
    if not os.path.exists(config_path):
        return False

    with open(config_path, "r", encoding="utf-8") as f:
        lines = f.readlines()

    # Locate the line range of the first RNodeInterface section
    in_interfaces    = False
    current_start    = None
    rnode_start      = None
    rnode_end        = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        if re.match(r'^\[(?!\[)[^\]]+\]', stripped):
            section_name  = stripped[1:-1].strip()
            in_interfaces = (section_name == "interfaces")
            if rnode_start is not None and rnode_end is None:
                rnode_end = i
                break
            current_start = None
            continue

        if not in_interfaces:
            continue

        if re.match(r'^\[\[.+\]\]', stripped):
            if rnode_start is not None and rnode_end is None:
                rnode_end = i
                break
            current_start = i
            continue

        if current_start is not None and rnode_start is None:
            if "=" in stripped and not stripped.startswith("#"):
                key, _, val = stripped.partition("=")
                if key.strip().lower() == "type" and val.strip().lower() == "rnodeinterface":
                    rnode_start = current_start

    if rnode_start is None:
        return False
    if rnode_end is None:
        rnode_end = len(lines)

    # Rewrite matching lines in [rnode_start, rnode_end)
    result_lines = list(lines)
    for i in range(rnode_start, rnode_end):
        s = result_lines[i].strip()
        if "=" in s and not s.startswith("#"):
            key, _, _ = s.partition("=")
            field = key.strip().lower()
            if field in updates:
                indent = len(result_lines[i]) - len(result_lines[i].lstrip())
                result_lines[i] = " " * indent + f"{key.strip()} = {updates[field]}\n"

    with open(config_path, "w", encoding="utf-8") as f:
        f.writelines(result_lines)

    return True


def add_rnode_interface(rns_config_dir: str, port: str, frequency: int,
                        bandwidth: int, txpower: int,
                        spreadingfactor: int, codingrate: int) -> bool:
    """
    Append a new RNodeInterface block to the [interfaces] section.
    Used when the client has no existing RNode configuration.
    Returns True on success.
    """
    config_path = os.path.join(rns_config_dir, "config")
    if not os.path.exists(config_path):
        return False

    block = (
        "\n"
        "  [[RNode LoRa]]\n"
        "    type = RNodeInterface\n"
        "    enabled = yes\n"
        f"    port = {port}\n"
        f"    frequency = {frequency}\n"
        f"    bandwidth = {bandwidth}\n"
        f"    txpower = {txpower}\n"
        f"    spreadingfactor = {spreadingfactor}\n"
        f"    codingrate = {codingrate}\n"
    )

    with open(config_path, "a", encoding="utf-8") as f:
        f.write(block)

    return True
