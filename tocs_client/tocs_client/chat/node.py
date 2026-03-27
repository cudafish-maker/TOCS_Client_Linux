"""
chat/node.py — RNS identity, destinations, and announce management for TOCS chat
"""

import os
import time
import threading
import RNS

APP_NAME    = "tocs"
ASPECT_PEER = "chat"


class AnnounceHandler:
    """Registered with RNS Transport to receive peer announce packets."""

    aspect_filter = f"{APP_NAME}.{ASPECT_PEER}"

    def __init__(self, on_peer_cb):
        self._on_peer = on_peer_cb

    def received_announce(self, destination_hash, announced_identity, app_data):
        nick = "unknown"
        if app_data:
            try:
                nick = app_data.decode("utf-8")
            except Exception:
                pass
        self._on_peer(destination_hash, announced_identity, nick)


class ChatNode:
    ANNOUNCE_INTERVAL_LORA = 300   # seconds — conservative for LoRa airtime budget
    ANNOUNCE_INTERVAL_MIN  = 60    # minimum between back-to-back announces

    def __init__(self, nick: str, config_dir: str):
        self.nick       = nick
        self.config_dir = config_dir
        self._stop      = threading.Event()
        self._last_ann  = 0.0
        self._peer_cb   = None
        self._link_cb   = None

        os.makedirs(config_dir, exist_ok=True)
        self.identity = self._load_or_create_identity()
        self._setup_destinations()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_peer_callback(self, cb):
        """Called when a peer announce is received: cb(dest_hash, identity, nick)"""
        self._peer_cb = cb

    def set_link_callback(self, cb):
        """Called when an inbound Link is established: cb(link)"""
        self._link_cb = cb

    def announce(self, force: bool = False):
        now = time.time()
        if not force and (now - self._last_ann) < self.ANNOUNCE_INTERVAL_MIN:
            return
        self._last_ann = now
        self.private_dest.announce(app_data=self.nick.encode("utf-8"))
        RNS.log(f"[chat.node] Announced as '{self.nick}'", RNS.LOG_DEBUG)

    def start_announce_loop(self):
        t = threading.Thread(target=self._announce_loop, daemon=True)
        t.start()

    def shutdown(self):
        self._stop.set()

    @property
    def dest_hash_hex(self) -> str:
        return RNS.prettyhexrep(self.private_dest.hash)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _load_or_create_identity(self) -> RNS.Identity:
        path = os.path.join(self.config_dir, "chat_identity")
        if os.path.exists(path):
            identity = RNS.Identity(create_keys=False)
            identity.load(path)
            RNS.log(f"[chat.node] Loaded identity from {path}", RNS.LOG_DEBUG)
        else:
            identity = RNS.Identity()
            identity.to_file(path)
            RNS.log(f"[chat.node] Created new identity, saved to {path}", RNS.LOG_DEBUG)
        return identity

    def _setup_destinations(self):
        self.private_dest = RNS.Destination(
            self.identity,
            RNS.Destination.IN,
            RNS.Destination.SINGLE,
            APP_NAME,
            ASPECT_PEER,
        )
        self.private_dest.set_link_established_callback(self._on_link_established)
        self.private_dest.accepts_links(True)

        RNS.Transport.register_announce_handler(
            AnnounceHandler(self._on_peer_announce)
        )

    def _on_peer_announce(self, dest_hash, identity, nick):
        if dest_hash == self.private_dest.hash:
            return  # our own announce echoed back
        if self._peer_cb:
            self._peer_cb(dest_hash, identity, nick)
        threading.Thread(target=lambda: self.announce(force=True), daemon=True).start()

    def _on_link_established(self, link: RNS.Link):
        if self._link_cb:
            self._link_cb(link)

    def _announce_loop(self):
        self.announce(force=True)
        while not self._stop.wait(self.ANNOUNCE_INTERVAL_LORA):
            self.announce(force=True)
