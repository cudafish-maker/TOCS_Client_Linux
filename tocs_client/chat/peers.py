"""
chat/peers.py — Peer registry: discovery, lookup, link state, persistence, and online status
"""

import os
import json
import time
import threading
from dataclasses import dataclass, field
from typing import Optional
import RNS

ONLINE_TIMEOUT = 180  # 3 minutes


@dataclass
class PeerInfo:
    dest_hash:  bytes
    nick:       str
    identity:   RNS.Identity
    last_seen:  float = field(default_factory=time.time)
    link:       Optional[RNS.Link] = None

    @property
    def hash_hex(self) -> str:
        return RNS.prettyhexrep(self.dest_hash)

    @property
    def short_hash(self) -> str:
        return self.dest_hash.hex()[:8]

    @property
    def is_online(self) -> bool:
        return (time.time() - self.last_seen) < ONLINE_TIMEOUT


class PeerRegistry:
    PEERS_FILE = "chat_peers.json"

    def __init__(self, config_dir: str = None):
        self._peers:    dict[bytes, PeerInfo] = {}
        self._lock      = threading.Lock()
        self._join_cb   = None
        self._leave_cb  = None
        self._update_cb = None
        self._config_dir = config_dir

        if config_dir:
            self._load()

    def set_join_callback(self, cb):
        self._join_cb = cb

    def set_leave_callback(self, cb):
        self._leave_cb = cb

    def set_update_callback(self, cb):
        self._update_cb = cb

    def on_announce(self, dest_hash: bytes, identity: RNS.Identity, nick: str):
        is_new = False
        with self._lock:
            existing = self._peers.get(dest_hash)
            if existing:
                existing.nick      = nick
                existing.identity  = identity
                existing.last_seen = time.time()
            else:
                peer = PeerInfo(dest_hash=dest_hash, identity=identity, nick=nick)
                self._peers[dest_hash] = peer
                is_new = True

        self._save()

        if is_new and self._join_cb:
            self._join_cb(self._peers[dest_hash])
        elif not is_new and self._update_cb:
            self._update_cb()

    def update_link(self, dest_hash: bytes, link: RNS.Link):
        with self._lock:
            if dest_hash in self._peers:
                self._peers[dest_hash].link = link

    def clear_link(self, dest_hash: bytes):
        with self._lock:
            if dest_hash in self._peers:
                self._peers[dest_hash].link = None

    def get_by_hash(self, dest_hash: bytes) -> Optional[PeerInfo]:
        with self._lock:
            return self._peers.get(dest_hash)

    def get_by_nick(self, prefix: str) -> Optional[PeerInfo]:
        prefix = prefix.lower()
        with self._lock:
            matches = [p for p in self._peers.values()
                       if p.nick.lower().startswith(prefix)]
        if len(matches) == 1:
            return matches[0]
        return None

    def get_by_identity(self, identity: RNS.Identity) -> Optional[PeerInfo]:
        with self._lock:
            for p in self._peers.values():
                if p.identity and p.identity.hash == identity.hash:
                    return p
        return None

    def all_peers(self) -> list:
        with self._lock:
            return list(self._peers.values())

    def count(self) -> int:
        with self._lock:
            return len(self._peers)

    def online_count(self) -> int:
        with self._lock:
            return sum(1 for p in self._peers.values() if p.is_online)

    def _peers_path(self) -> str:
        return os.path.join(self._config_dir, self.PEERS_FILE)

    def _save(self):
        if not self._config_dir:
            return
        try:
            with self._lock:
                data = [
                    {
                        "dest_hash": p.dest_hash.hex(),
                        "nick":      p.nick,
                        "last_seen": p.last_seen,
                    }
                    for p in self._peers.values()
                ]
            with open(self._peers_path(), "w") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _load(self):
        path = self._peers_path()
        if not os.path.exists(path):
            return
        try:
            with open(path) as f:
                data = json.load(f)
            with self._lock:
                for entry in data:
                    dest_hash = bytes.fromhex(entry["dest_hash"])
                    identity  = RNS.Identity.recall(dest_hash)
                    peer = PeerInfo(
                        dest_hash = dest_hash,
                        nick      = entry["nick"],
                        identity  = identity,
                        last_seen = entry.get("last_seen", 0),
                    )
                    self._peers[dest_hash] = peer
        except Exception:
            pass
