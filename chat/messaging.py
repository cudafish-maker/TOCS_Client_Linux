"""
chat/messaging.py — Group and private message send/receive via LXMF
"""

import RNS

from chat.peers import PeerInfo, PeerRegistry
from chat.lxmf_handler import LXMFHandler

MAX_MSG = 280  # bytes


class Messenger:
    def __init__(self, node, peers: PeerRegistry, display_cb, propagation_node: bool = False):
        self._node    = node
        self._peers   = peers
        self._display = display_cb

        self._lxmf = LXMFHandler(
            identity         = node.identity,
            config_dir       = node.config_dir,
            display_cb       = lambda line: self._display(line),
            peers            = peers,
            propagation_node = propagation_node,
        )

    def send_group(self, text: str):
        if len(text.encode("utf-8")) > MAX_MSG:
            self._display("[!] Message too long (max 280 chars)")
            return

        peers = self._peers.all_peers()
        if not peers:
            self._display("[!] No known peers — message not delivered")
            return

        for peer in peers:
            self._lxmf.send_group_to_peer(
                peer_dest_hash = peer.dest_hash,
                peer_nick      = peer.nick,
                sender_nick    = self._node.nick,
                text           = text,
            )

    def send_private(self, peer: PeerInfo, text: str):
        if len(text.encode("utf-8")) > MAX_MSG:
            self._display("[!] Message too long (max 280 chars)")
            return
        self._lxmf.send(peer.dest_hash, peer.nick, text)

    @property
    def lxmf_address(self) -> str:
        return self._lxmf.lxmf_address
