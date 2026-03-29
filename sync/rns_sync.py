"""
sync/rns_sync.py — Client-side RNS sync over Reticulum
Discovers the TOCS server via announces, authenticates, and syncs data.
"""

import threading
import time
import RNS
from PyQt6.QtCore import QObject, pyqtSignal

from sync.protocol import (
    MSG_ASSET, MSG_SITREP, MSG_ASSET_DELETE, MSG_SITREP_DELETE,
    MSG_HELLO, MSG_ASSET_UPDATE, MSG_SITREP_NEW,
    MSG_AUTH_REGISTER, MSG_AUTH_LOGIN, MSG_AUTH_OK, MSG_AUTH_FAIL,
    MSG_ASSET_TYPE_DEF, MSG_ASSET_TYPE_DEL, MSG_ASSET_VERIFY,
    MSG_SYNC_START, MSG_SYNC_DONE, MSG_RNODE_CONFIG,
    asset_to_dict, sitrep_to_dict, dict_to_asset, dict_to_sitrep,
    pack, unpack,
)

APP_NAME         = "tocs"
ASPECT_SYNC      = "sync"
RECONNECT_DELAY  = 5    # seconds between reconnect attempts


class _AnnounceHandler:
    """RNS announce handler — captures tocs.sync server destinations."""
    def __init__(self, callback):
        self.aspect_filter = f"{APP_NAME}.{ASPECT_SYNC}"
        self._cb = callback

    def received_announce(self, destination_hash, announced_identity, app_data):
        if app_data == b"tocs-server":
            self._cb(destination_hash)


class SyncClient(QObject):
    """
    Discovers the TOCS server via RNS announces, authenticates, and syncs.
    Emits Qt signals for all received data so the UI stays on the main thread.
    """
    auth_ok               = pyqtSignal(int, str)       # operator_id, callsign
    auth_fail             = pyqtSignal(str)             # reason
    status_changed        = pyqtSignal(str)
    asset_received        = pyqtSignal(object)
    sitrep_received       = pyqtSignal(object)
    asset_deleted         = pyqtSignal(int)
    sitrep_deleted        = pyqtSignal(int)
    asset_type_received   = pyqtSignal(str, str, str)  # type_key, name, color
    asset_type_deleted    = pyqtSignal(str)
    sync_complete         = pyqtSignal()
    server_connected      = pyqtSignal()
    server_lost           = pyqtSignal()
    rnode_config_received = pyqtSignal(dict)

    def __init__(self, config_dir: str, parent=None):
        super().__init__(parent)
        self._config_dir     = config_dir
        self._server_hash    = None       # bytes — server destination hash
        self._link           = None       # active RNS.Link or None
        self._authenticated  = False
        self._callsign       = None
        self._password       = None
        self._auth_mode      = None       # "login" or "register"
        self._reg_passphrase = None
        self._lock           = threading.Lock()
        self._stop           = threading.Event()

        self._announce_handler = _AnnounceHandler(self._on_server_announce)
        RNS.Transport.register_announce_handler(self._announce_handler)

        threading.Thread(target=self._reconnect_loop, daemon=True).start()
        self.status_changed.emit("Searching for TOCS server...")

    # ------------------------------------------------------------------
    # Server discovery
    # ------------------------------------------------------------------

    def _on_server_announce(self, dest_hash: bytes):
        with self._lock:
            self._server_hash = dest_hash
            already = self._link is not None
        if not already:
            threading.Thread(target=self._connect, daemon=True).start()

    # ------------------------------------------------------------------
    # Connection
    # ------------------------------------------------------------------

    def _reconnect_loop(self):
        while not self._stop.wait(RECONNECT_DELAY):
            with self._lock:
                connected  = self._link is not None
                has_server = self._server_hash is not None
            if not connected and has_server:
                self._connect()

    def _connect(self):
        with self._lock:
            if self._link is not None:
                return
            server_hash = self._server_hash
        if server_hash is None:
            return

        try:
            self.status_changed.emit("Connecting to server...")
            identity = RNS.Identity.recall(server_hash)
            if identity is None:
                self.status_changed.emit("Discovering path to server...")
                RNS.Transport.request_path(server_hash)
                threading.Timer(4.0, self._connect).start()
                return

            dest = RNS.Destination(
                identity,
                RNS.Destination.OUT,
                RNS.Destination.SINGLE,
                APP_NAME,
                ASPECT_SYNC,
            )
            link = RNS.Link(dest)
            link.set_link_established_callback(self._on_link_established)
            link.set_link_closed_callback(self._on_link_closed)
            link.set_packet_callback(self._on_packet)
            with self._lock:
                self._link = link
        except Exception as e:
            RNS.log(f"[tocs] Connect error: {e}", RNS.LOG_ERROR)
            with self._lock:
                self._link = None

    def _on_link_established(self, link: RNS.Link):
        self.status_changed.emit("Link established — ready to authenticate")
        self.server_connected.emit()
        with self._lock:
            callsign = self._callsign
            password = self._password
            mode     = self._auth_mode
            reg_pp   = self._reg_passphrase
        if callsign and password and mode:
            self._send_auth(link, callsign, password, mode, reg_pp)

    def _on_link_closed(self, link: RNS.Link):
        with self._lock:
            self._link          = None
            self._authenticated = False
        self.server_lost.emit()
        self.status_changed.emit("Server connection lost — reconnecting...")

    # ------------------------------------------------------------------
    # Auth (public)
    # ------------------------------------------------------------------

    def authenticate(self, callsign: str, password: str, mode: str,
                     reg_passphrase: str = None):
        with self._lock:
            self._callsign       = callsign
            self._password       = password
            self._auth_mode      = mode
            self._reg_passphrase = reg_passphrase
            link = self._link

        if link and link.status == RNS.Link.ACTIVE:
            self._send_auth(link, callsign, password, mode, reg_passphrase)
        else:
            self.status_changed.emit("Waiting for server connection...")
            with self._lock:
                has_server = self._server_hash is not None
                no_link    = self._link is None
            if has_server and no_link:
                threading.Thread(target=self._connect, daemon=True).start()

    def _send_auth(self, link, callsign, password, mode, reg_passphrase):
        try:
            if mode == "register":
                payload = {
                    "callsign":       callsign,
                    "password":       password,
                    "reg_passphrase": reg_passphrase or "",
                }
                RNS.Packet(link, pack(MSG_AUTH_REGISTER, payload)).send()
            else:
                payload = {"callsign": callsign, "password": password}
                RNS.Packet(link, pack(MSG_AUTH_LOGIN, payload)).send()
            self.status_changed.emit("Authenticating...")
        except Exception as e:
            RNS.log(f"[tocs] Auth send error: {e}", RNS.LOG_ERROR)

    # ------------------------------------------------------------------
    # Receive from server
    # ------------------------------------------------------------------

    def _on_packet(self, message: bytes, packet: RNS.Packet):
        if not message:
            return
        msg_type = message[:1]
        try:
            if msg_type == MSG_AUTH_OK:
                _, payload = unpack(message)
                op_id    = payload["operator_id"]
                callsign = payload["callsign"]
                with self._lock:
                    self._authenticated = True
                    self._callsign      = callsign
                    password            = self._password
                import db.session as session_cache
                session_cache.save(callsign, op_id, password or "")
                # Do NOT send HELLO here — the main window hasn't connected its
                # signals yet, so any data the server sends would be lost.
                # client_main.py calls begin_sync() after MainWindow is fully constructed.
                self.auth_ok.emit(op_id, callsign)

            elif msg_type == MSG_AUTH_FAIL:
                _, payload = unpack(message)
                self.auth_fail.emit(payload.get("reason", "Authentication failed"))

            elif msg_type == MSG_SYNC_START:
                pass

            elif msg_type == MSG_SYNC_DONE:
                import db.session as session_cache
                session_cache.save_last_sync(time.time())
                self.sync_complete.emit()

            elif msg_type == MSG_ASSET:
                _, payload = unpack(message)
                self.asset_received.emit(dict_to_asset(payload))

            elif msg_type == MSG_SITREP:
                _, payload = unpack(message)
                self.sitrep_received.emit(dict_to_sitrep(payload))

            elif msg_type == MSG_ASSET_DELETE:
                _, payload = unpack(message)
                self.asset_deleted.emit(payload["id"])

            elif msg_type == MSG_SITREP_DELETE:
                _, payload = unpack(message)
                self.sitrep_deleted.emit(payload["id"])

            elif msg_type == MSG_ASSET_TYPE_DEF:
                _, payload = unpack(message)
                self.asset_type_received.emit(
                    payload["type_key"], payload["name"], payload["color"]
                )

            elif msg_type == MSG_ASSET_TYPE_DEL:
                _, payload = unpack(message)
                self.asset_type_deleted.emit(payload["type_key"])

            elif msg_type == MSG_RNODE_CONFIG:
                _, payload = unpack(message)
                self.rnode_config_received.emit(payload)

        except Exception as e:
            RNS.log(f"[tocs] Packet parse error: {e}", RNS.LOG_ERROR)

    # ------------------------------------------------------------------
    # Send to server
    # ------------------------------------------------------------------

    def _send(self, data: bytes):
        with self._lock:
            link = self._link
            auth = self._authenticated
        if link and auth and link.status == RNS.Link.ACTIVE:
            try:
                RNS.Packet(link, data).send()
            except Exception as e:
                RNS.log(f"[tocs] Send error: {e}", RNS.LOG_WARNING)

    def begin_sync(self):
        """
        Send HELLO to the server to trigger a full/delta sync.
        Must be called AFTER MainWindow has connected its signals — otherwise
        the server's response arrives before any slots are registered.
        """
        with self._lock:
            link     = self._link
            auth     = self._authenticated
            callsign = self._callsign
        if link and auth and callsign and link.status == RNS.Link.ACTIVE:
            import db.session as session_cache
            last_sync = session_cache.get_last_sync()
            try:
                RNS.Packet(link, pack(MSG_HELLO, {"callsign": callsign, "last_sync": last_sync})).send()
            except Exception as e:
                RNS.log(f"[tocs] begin_sync error: {e}", RNS.LOG_ERROR)

    def send_asset(self, asset):
        self._send(pack(MSG_ASSET_UPDATE, asset_to_dict(asset)))

    def send_sitrep(self, sitrep):
        self._send(pack(MSG_SITREP_NEW, sitrep_to_dict(sitrep)))

    def send_verify_asset(self, asset_id: int):
        self._send(pack(MSG_ASSET_VERIFY, {"id": asset_id}))

    def stop(self):
        self._stop.set()
