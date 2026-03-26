"""
ui/chat_panel.py — Integrated chat panel widget for TOCS

Drop this into a QDockWidget. Requires a ChatNode, PeerRegistry, and Messenger
to be passed in after construction via init_chat().
"""

import time
from PyQt6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout,
    QTextEdit, QLineEdit, QPushButton,
    QListWidget, QListWidgetItem, QLabel, QSplitter,
)
from PyQt6.QtCore import Qt, pyqtSignal, QObject, QTimer
from PyQt6.QtGui import QColor, QFont, QTextCursor

COLOR_ONLINE  = "#a6e3a1"
COLOR_OFFLINE = "#585b70"


# ---------------------------------------------------------------------------
# Thread-safe bridge
# ---------------------------------------------------------------------------

class _Bridge(QObject):
    message_received = pyqtSignal(str, str)   # (tag, text)
    peer_joined      = pyqtSignal(str, str)   # (nick, short_hash)
    peer_updated     = pyqtSignal()


# ---------------------------------------------------------------------------
# Peer list item
# ---------------------------------------------------------------------------

class PeerItem(QListWidgetItem):
    def __init__(self, peer):
        super().__init__()
        self.peer = peer
        self.refresh()

    def refresh(self):
        status = "●" if self.peer.is_online else "○"
        self.setText(f"  {status} {self.peer.nick}\n    {self.peer.short_hash}")
        color = COLOR_ONLINE if self.peer.is_online else COLOR_OFFLINE
        self.setForeground(QColor(color))


# ---------------------------------------------------------------------------
# Chat panel widget
# ---------------------------------------------------------------------------

class ChatPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._node      = None
        self._peers     = None
        self._messenger = None
        self._bridge    = _Bridge()
        self._items: dict = {}

        self._bridge.message_received.connect(self._on_message)
        self._bridge.peer_joined.connect(self._on_peer_joined)
        self._bridge.peer_updated.connect(self._refresh_peer_list)

        self._build_ui()

        self._refresh_timer = QTimer(self)
        self._refresh_timer.timeout.connect(self._refresh_peer_list)
        self._refresh_timer.start(10_000)

    # ------------------------------------------------------------------
    # Initialise chat components (called after login / on startup)
    # ------------------------------------------------------------------

    def init_chat(self, node, peers, messenger):
        self._node      = node
        self._peers     = peers
        self._messenger = messenger

        # Wire messenger display callback to this panel
        self._messenger._display = self.display

        # Wire peer callbacks
        self._peers.set_join_callback(
            lambda p: self._bridge.peer_joined.emit(p.nick, p.short_hash)
        )
        self._peers.set_update_callback(
            lambda: self._bridge.peer_updated.emit()
        )

        # Populate peer list from any saved peers
        self._refresh_peer_list()

        self.display(f"[*] Chat ready — you are '{node.nick}'")
        self.display(f"[*] RNS address:  {node.dest_hash_hex}")
        self.display(f"[*] LXMF address: {messenger.lxmf_address}")
        self.display("[*] Waiting for peers...")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(2)

        # ── Peer list ─────────────────────────────────────────────────
        peer_panel = QWidget()
        peer_panel.setFixedWidth(170)
        peer_layout = QVBoxLayout(peer_panel)
        peer_layout.setContentsMargins(0, 0, 0, 0)
        peer_layout.setSpacing(0)

        peer_header = QLabel("  Chat Peers")
        peer_header.setObjectName("panelHeader")
        peer_header.setFixedHeight(24)

        self._lbl_peers = QLabel("  0 peers")
        self._lbl_peers.setObjectName("chatPeerCount")
        self._lbl_peers.setFixedHeight(20)
        self._lbl_peers.setStyleSheet("color: #6c7086; font-size: 10px; padding-left: 6px;")

        self._peer_list = QListWidget()
        self._peer_list.setObjectName("chatPeerList")
        self._peer_list.itemDoubleClicked.connect(self._on_peer_double_click)
        self._peer_list.setToolTip("Double-click to send a private message")

        peer_layout.addWidget(peer_header)
        peer_layout.addWidget(self._lbl_peers)
        peer_layout.addWidget(self._peer_list)

        splitter.addWidget(peer_panel)

        # ── Message area ──────────────────────────────────────────────
        msg_panel = QWidget()
        msg_layout = QVBoxLayout(msg_panel)
        msg_layout.setContentsMargins(6, 4, 6, 4)
        msg_layout.setSpacing(4)

        self._msg_view = QTextEdit()
        self._msg_view.setObjectName("chatMsgView")
        self._msg_view.setReadOnly(True)
        self._msg_view.setFont(QFont("Monospace", 10))

        input_row = QHBoxLayout()
        input_row.setSpacing(6)

        self._input = QLineEdit()
        self._input.setObjectName("chatInput")
        self._input.setPlaceholderText("Type a message or /msg <callsign> <text> ...")
        self._input.setFont(QFont("Monospace", 10))
        self._input.returnPressed.connect(self._on_send)

        self._send_btn = QPushButton("Send")
        self._send_btn.setObjectName("chatSendBtn")
        self._send_btn.setFixedWidth(64)
        self._send_btn.clicked.connect(self._on_send)

        self._ann_btn = QPushButton("Announce")
        self._ann_btn.setObjectName("chatAnnBtn")
        self._ann_btn.setFixedWidth(80)
        self._ann_btn.clicked.connect(self._on_announce)

        input_row.addWidget(self._input)
        input_row.addWidget(self._send_btn)
        input_row.addWidget(self._ann_btn)

        msg_layout.addWidget(self._msg_view)
        msg_layout.addLayout(input_row)

        splitter.addWidget(msg_panel)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        root.addWidget(splitter)

    # ------------------------------------------------------------------
    # Thread-safe display (called from RNS/LXMF threads)
    # ------------------------------------------------------------------

    def display(self, line: str):
        if line.startswith("[PM"):
            tag = "pm"
        elif line.startswith("[group]"):
            tag = "group"
        elif line.startswith("[you]") or line.startswith("[PM ->"):
            tag = "self"
        elif line.startswith("[!]"):
            tag = "error"
        elif line.startswith("[*]") or line.startswith("***"):
            tag = "system"
        else:
            tag = "info"
        self._bridge.message_received.emit(tag, line)

    # ------------------------------------------------------------------
    # Qt slot handlers
    # ------------------------------------------------------------------

    def _on_message(self, tag: str, text: str):
        colours = {
            "group":  "#cdd6f4",
            "pm":     "#f5c2e7",
            "self":   "#a6e3a1",
            "error":  "#f38ba8",
            "system": "#89b4fa",
            "info":   "#a6adc8",
        }
        colour = colours.get(tag, "#cdd6f4")
        ts     = time.strftime("%H:%M:%S")
        html   = (
            f'<span style="color:#585b70;">[{ts}]</span> '
            f'<span style="color:{colour};">{self._html_escape(text)}</span>'
        )
        self._msg_view.append(html)
        self._msg_view.moveCursor(QTextCursor.MoveOperation.End)

    def _on_peer_joined(self, nick: str, short_hash: str):
        self.display(f"*** {nick} joined [{short_hash}]")
        self._refresh_peer_list()

    def _on_send(self):
        if self._messenger is None:
            return
        text = self._input.text().strip()
        if not text:
            return
        self._input.clear()
        self._handle(text)

    def _on_announce(self):
        if self._node:
            self._node.announce(force=True)
            self.display("[*] Announced.")

    def _on_peer_double_click(self, item):
        if isinstance(item, PeerItem):
            self._input.setText(f"/msg {item.peer.nick} ")
            self._input.setFocus()

    # ------------------------------------------------------------------
    # Input handling
    # ------------------------------------------------------------------

    def _handle(self, line: str):
        if line.startswith("/"):
            parts = line[1:].split(" ", 2)
            cmd   = parts[0].lower()
            args  = parts[1:] if len(parts) > 1 else []

            if cmd == "peers":
                self._show_peers()
            elif cmd == "msg":
                if len(args) < 2:
                    self.display("[!] Usage: /msg <callsign> <message>")
                else:
                    peer = self._peers.get_by_nick(args[0])
                    if peer is None:
                        self.display(f"[!] No peer matching '{args[0]}'")
                    else:
                        self._messenger.send_private(peer, " ".join(args[1:]))
                        self.display(f"[PM -> {peer.nick}]: {' '.join(args[1:])}")
            elif cmd == "announce":
                self._on_announce()
            else:
                self.display(f"[!] Unknown command: /{cmd}")
        else:
            if self._peers and self._peers.count() == 0:
                self.display("[!] No peers known yet — announcing...")
                self._node.announce(force=True)
            self._messenger.send_group(line)
            self.display(f"[you]: {line}")

    def _show_peers(self):
        if not self._peers:
            return
        peers = self._peers.all_peers()
        if not peers:
            self.display("No peers known yet.")
            return
        now = time.time()
        for p in peers:
            age    = int(now - p.last_seen)
            status = "online" if p.is_online else "offline"
            self.display(f"  {p.nick:<20} {p.short_hash}  {status} ({age}s ago)")

    def _refresh_peer_list(self):
        if not self._peers:
            return
        peers = self._peers.all_peers()
        peers.sort(key=lambda p: (not p.is_online, p.nick.lower()))

        self._peer_list.clear()
        self._items.clear()
        for peer in peers:
            item = PeerItem(peer)
            self._peer_list.addItem(item)
            self._items[peer.dest_hash] = item

        total  = self._peers.count()
        online = self._peers.online_count()
        self._lbl_peers.setText(f"  {total} peers ({online} online)")

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _html_escape(text: str) -> str:
        return (text
                .replace("&", "&amp;")
                .replace("<", "&lt;")
                .replace(">", "&gt;"))
