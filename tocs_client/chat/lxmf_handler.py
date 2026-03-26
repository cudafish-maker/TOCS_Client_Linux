"""
chat/lxmf_handler.py — LXMF router setup and message delivery for TOCS chat
"""

import os
import threading
import RNS
import LXMF
from LXMF import LXMRouter, LXMessage

APP_NAME = "tocs"

FIELD_MSG_TYPE = 0x01   # value: "group" or "private"
FIELD_SENDER   = 0x02   # value: sender nick


class LXMFHandler:
    def __init__(self, identity: RNS.Identity, config_dir: str, display_cb, peers,
                 propagation_node: bool = False):
        self._identity   = identity
        self._config_dir = config_dir
        self._display    = display_cb
        self._peers      = peers
        self._lock       = threading.Lock()
        self._pending: dict = {}

        storagepath = os.path.join(config_dir, "storage")
        os.makedirs(storagepath, exist_ok=True)

        self._router = LXMRouter(
            storagepath = storagepath,
            autopeer    = True,
        )

        if propagation_node:
            self._router.enable_propagation()
            RNS.log("[chat.lxmf] Propagation node enabled", RNS.LOG_NOTICE)

        self._local_dest = self._router.register_delivery_identity(
            self._identity,
            display_name=None,
        )

        self._router.register_delivery_callback(self._on_message_received)

    @property
    def destination(self):
        return self._local_dest

    @property
    def lxmf_address(self) -> str:
        return RNS.prettyhexrep(self._local_dest.hash)

    def send(self, peer_dest_hash: bytes, peer_nick: str, text: str):
        """Send a private message to a peer via LXMF."""
        peer_identity = RNS.Identity.recall(peer_dest_hash)
        if peer_identity is None:
            self._display(f"[!] No identity known for {peer_nick} — have they announced?")
            return

        lxmf_dest = RNS.Destination(
            peer_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        msg = LXMessage(
            destination    = lxmf_dest,
            source         = self._local_dest,
            content        = text,
            title          = "",
            desired_method = LXMessage.DIRECT,
        )

        msg.register_delivery_callback(lambda m: self._on_delivered(m, peer_nick))
        msg.register_failed_callback(lambda m: self._on_failed(m, peer_nick))

        with self._lock:
            self._pending[msg.hash] = peer_nick

        self._router.handle_outbound(msg)
        self._display(f"[PM -> {peer_nick}] (sending...): {text}")

    def send_group_to_peer(self, peer_dest_hash: bytes, peer_nick: str,
                           sender_nick: str, text: str):
        """Send a group message to one peer via LXMF."""
        peer_identity = RNS.Identity.recall(peer_dest_hash)
        if peer_identity is None:
            return

        lxmf_dest = RNS.Destination(
            peer_identity,
            RNS.Destination.OUT,
            RNS.Destination.SINGLE,
            "lxmf",
            "delivery",
        )

        msg = LXMessage(
            destination    = lxmf_dest,
            source         = self._local_dest,
            content        = text,
            title          = "",
            fields         = {FIELD_MSG_TYPE: "group", FIELD_SENDER: sender_nick},
            desired_method = LXMessage.DIRECT,
        )

        msg.register_failed_callback(lambda m: self._retry_propagated(m, peer_nick))
        self._router.handle_outbound(msg)

    def announce(self):
        self._local_dest.announce()

    def _on_message_received(self, message: LXMessage):
        text   = message.content_as_string()
        fields = message.fields or {}

        rssi = message.rssi
        snr  = message.snr
        sig  = ""
        if rssi is not None:
            sig = f" [{rssi}dBm"
            if snr is not None:
                sig += f" SNR:{snr:.1f}dB"
            sig += "]"

        method_names = {
            LXMessage.OPPORTUNISTIC: "opportunistic",
            LXMessage.DIRECT:        "direct",
            LXMessage.PROPAGATED:    "propagated",
        }
        method = method_names.get(message.method, "unknown")

        if fields.get(FIELD_MSG_TYPE) == "group":
            sender = fields.get(FIELD_SENDER) or message.source_hash.hex()[:8]
            self._display(f"[group] {sender}{sig}: {text}")
        else:
            peer = self._peers.get_by_hash(message.source_hash)
            sender = peer.nick if peer else message.source_hash.hex()[:8]
            self._display(f"[PM from {sender}] ({method}){sig}: {text}")

    def _on_delivered(self, message: LXMessage, nick: str):
        with self._lock:
            self._pending.pop(message.hash, None)
        self._display(f"[+] Message delivered to {nick}")

    def _on_failed(self, message: LXMessage, nick: str):
        with self._lock:
            self._pending.pop(message.hash, None)
        self._display(
            f"[!] Direct delivery to {nick} failed — "
            f"retrying via propagation node if available"
        )
        self._retry_propagated(message, nick)

    def _retry_propagated(self, original: LXMessage, nick: str):
        msg = LXMessage(
            destination    = original.destination,
            source         = self._local_dest,
            content        = original.content_as_string(),
            title          = original.title_as_string(),
            desired_method = LXMessage.PROPAGATED,
        )
        msg.register_delivery_callback(
            lambda m: self._display(f"[+] Message to {nick} accepted by propagation node")
        )
        msg.register_failed_callback(
            lambda m: self._display(f"[!] Propagation delivery to {nick} also failed")
        )
        self._router.handle_outbound(msg)
        self._display(f"[*] Retrying delivery to {nick} via propagation node...")
