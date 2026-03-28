"""
ui/main_window.py — TOCS Client main window with integrated chat
"""

from PyQt6.QtWidgets import (
    QMainWindow, QSplitter, QStatusBar, QLabel, QToolBar, QDockWidget,
)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction

from map.map_view import MapView
from ui.asset_panel import AssetPanel
from ui.sitrep_panel import SitrepPanel
from ui.sitrep_dialog import SitrepDialog
from ui.chat_panel import ChatPanel
from controllers.asset_controller import AssetController
from controllers.sitrep_controller import SitrepController


class MainWindow(QMainWindow):
    def __init__(self, operator_id: int, callsign: str, sync_client=None,
                 rns_config_dir: str = None):
        super().__init__()
        self._operator_id    = operator_id
        self._callsign       = callsign
        self._sync           = sync_client
        self._rns_config     = rns_config_dir
        self._asset_ctrl     = AssetController(self)
        self._sitrep_ctrl    = SitrepController(self)
        self._pending_dialog = None
        self._pending_mode   = None
        self._server_rnode   = None    # last received server RNode config

        self._build_ui()
        self._connect_signals()
        self._init_chat()
        self.setWindowTitle(f"TOCS — {callsign} [CLIENT]")
        self.resize(1280, 860)
        self._map.map_ready.connect(self._on_map_ready)

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        tb = QToolBar("Main")
        tb.setMovable(False)
        self.addToolBar(tb)

        self._act_add_asset    = QAction("+ Asset", self)
        self._act_add_sitrep   = QAction("+ SITREP", self)
        self._act_rnode_config = QAction("RNode Config", self)
        self._act_toggle_chat  = QAction("Chat", self)
        self._act_toggle_chat.setCheckable(True)
        self._act_toggle_chat.setChecked(True)

        tb.addAction(self._act_add_asset)
        tb.addAction(self._act_add_sitrep)
        tb.addSeparator()
        tb.addAction(self._act_rnode_config)
        tb.addSeparator()
        tb.addAction(self._act_toggle_chat)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        self.setCentralWidget(splitter)

        self._asset_panel = AssetPanel()
        self._asset_panel.setMinimumWidth(180)
        self._asset_panel.setMaximumWidth(260)
        splitter.addWidget(self._asset_panel)

        self._map = MapView()
        splitter.addWidget(self._map)

        self._sitrep_panel = SitrepPanel()
        self._sitrep_panel.setMinimumWidth(200)
        self._sitrep_panel.setMaximumWidth(300)
        splitter.addWidget(self._sitrep_panel)

        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setStretchFactor(2, 0)

        # ── Chat dock ──────────────────────────────────────────────────
        self._chat_panel = ChatPanel()
        self._chat_dock  = QDockWidget("Chat", self)
        self._chat_dock.setObjectName("chatDock")
        self._chat_dock.setWidget(self._chat_panel)
        self._chat_dock.setAllowedAreas(
            Qt.DockWidgetArea.BottomDockWidgetArea | Qt.DockWidgetArea.RightDockWidgetArea
        )
        self._chat_dock.setMinimumHeight(180)
        self.addDockWidget(Qt.DockWidgetArea.BottomDockWidgetArea, self._chat_dock)

        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._lbl_coords = QLabel("  Lat: --  Lon: --")
        self._lbl_counts = QLabel()
        self._status.addPermanentWidget(self._lbl_coords)
        self._status.addWidget(self._lbl_counts)

    def _connect_signals(self):
        self._act_add_asset.triggered.connect(self._open_add_asset)
        self._act_add_sitrep.triggered.connect(self._open_add_sitrep)
        self._act_rnode_config.triggered.connect(self._open_rnode_config)
        self._act_toggle_chat.toggled.connect(self._chat_dock.setVisible)
        self._chat_dock.visibilityChanged.connect(self._act_toggle_chat.setChecked)

        self._asset_panel.asset_selected.connect(self._on_asset_selected)
        self._asset_panel.type_visibility_changed.connect(self._map.set_type_visible)
        self._sitrep_panel.add_requested.connect(self._open_add_sitrep)
        self._sitrep_panel.sitrep_selected.connect(self._on_sitrep_selected)

        self._map.asset_clicked.connect(self._on_asset_selected)
        self._map.sitrep_clicked.connect(self._on_sitrep_selected)
        self._map.map_clicked.connect(self._on_map_clicked)
        self._map.mouse_moved.connect(self._on_mouse_moved)

        self._asset_ctrl.asset_saved.connect(self._on_asset_saved)
        self._sitrep_ctrl.sitrep_saved.connect(self._on_sitrep_saved)

        if self._sync:
            self._sync.asset_received.connect(self._on_sync_asset)
            self._sync.sitrep_received.connect(self._on_sync_sitrep)
            self._sync.asset_deleted.connect(self._on_sync_asset_deleted)
            self._sync.sitrep_deleted.connect(self._on_sync_sitrep_deleted)
            self._sync.asset_type_received.connect(self._on_sync_asset_type)
            self._sync.asset_type_deleted.connect(self._on_sync_asset_type_deleted)
            self._sync.sync_complete.connect(self._on_sync_complete)
            self._sync.rnode_config_received.connect(self._on_rnode_config)
            self._sync.server_connected.connect(
                lambda: self._status.showMessage("Connected to server", 3000)
            )
            self._sync.server_lost.connect(
                lambda: self._status.showMessage("Server connection lost — reconnecting...", 0)
            )
            self._sync.status_changed.connect(
                lambda msg: self._status.showMessage(msg, 0)
            )

    def _init_chat(self):
        """Initialise the chat node using the operator's callsign."""
        if not self._rns_config:
            return
        try:
            from chat.node import ChatNode
            from chat.peers import PeerRegistry
            from chat.messaging import Messenger

            node      = ChatNode(nick=self._callsign, config_dir=self._rns_config)
            peers     = PeerRegistry(config_dir=self._rns_config)
            messenger = Messenger(node, peers, display_cb=self._chat_panel.display)

            node.set_peer_callback(peers.on_announce)
            node.start_announce_loop()

            self._chat_panel.init_chat(node, peers, messenger)
        except Exception as e:
            self._chat_panel.display(f"[!] Chat init failed: {e}")

    # ------------------------------------------------------------------
    # Data loading
    # ------------------------------------------------------------------

    def _on_map_ready(self):
        assets  = self._asset_ctrl.load_all()
        sitreps = self._sitrep_ctrl.load_all()
        self._asset_panel.load_assets(assets)
        self._sitrep_panel.load_sitreps(sitreps)
        for a in assets:
            self._map.add_or_update_asset(a)
        for s in sitreps:
            if s.lat is not None and s.lon is not None:
                self._map.add_or_update_sitrep(s)
        self._update_counts()

    def _update_counts(self):
        assets  = self._asset_ctrl.load_all()
        sitreps = self._sitrep_ctrl.load_all()
        self._lbl_counts.setText(f"Assets: {len(assets)}   SITREPs: {len(sitreps)}")

    # ------------------------------------------------------------------
    # Asset flow — own profile only
    # ------------------------------------------------------------------

    def _open_add_asset(self):
        from ui.asset_dialog import AssetDialog
        skills = self._asset_ctrl.get_all_skills()
        dlg = AssetDialog(self, all_skills=skills, exclude_operator=True)
        dlg.pick_button.clicked.connect(lambda: self._start_place_mode(dlg, "asset"))
        dlg.accepted.connect(lambda: self._submit_new_asset(dlg.result_asset))
        dlg.show()

    def _submit_new_asset(self, asset):
        asset.verified = False
        saved = self._asset_ctrl.save(asset)
        self._map.add_or_update_asset(saved)
        self._update_counts()
        self._status.showMessage(f"Asset submitted (pending verification): {saved.name}", 4000)
        if self._sync:
            self._sync.send_asset(saved)

    def _on_asset_selected(self, asset_id: int):
        import db.asset_repo as repo
        asset = repo.get_by_id(asset_id)
        if not asset:
            return
        self._map.pan_to(asset.lat, asset.lon)

        if asset_id == self._operator_id:
            from ui.asset_dialog import AssetDialog
            skills = self._asset_ctrl.get_all_skills()
            dlg = AssetDialog(self, asset=asset, all_skills=skills)
            dlg.pick_button.clicked.connect(lambda: self._start_place_mode(dlg, "asset"))
            dlg.accepted.connect(lambda: self._asset_ctrl.save(dlg.result_asset))
            dlg.show()
            return

        from models.asset import Operator
        if isinstance(asset, Operator):
            self._status.showMessage(
                "View only — you can only edit your own operator profile", 4000
            )
            return

        self._open_asset_info(asset)

    def _open_asset_info(self, asset):
        from PyQt6.QtWidgets import (
            QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QFrame,
        )
        from models.asset import get_type_display_name
        dlg = QDialog(self)
        dlg.setWindowTitle(asset.name)
        dlg.setMinimumWidth(300)
        layout = QVBoxLayout(dlg)
        layout.setSpacing(8)

        layout.addWidget(QLabel(f"<b>{asset.name}</b>"))
        layout.addWidget(QLabel(f"Type: {get_type_display_name(asset.asset_type)}"))
        layout.addWidget(QLabel(f"Status: {asset.status.value}"))
        layout.addWidget(QLabel(f"Position: {asset.lat:.5f}, {asset.lon:.5f}"))
        if asset.status_note:
            layout.addWidget(QLabel(f"Note: {asset.status_note}"))

        if not asset.verified:
            sep = QFrame()
            sep.setFrameShape(QFrame.Shape.HLine)
            layout.addWidget(sep)
            lbl = QLabel("⚠  This asset has not been verified")
            lbl.setStyleSheet("color: #f9e2af;")
            layout.addWidget(lbl)

        btn_row = QHBoxLayout()
        btn_row.addStretch()

        if not asset.verified and self._sync:
            verify_btn = QPushButton("Verify")
            verify_btn.setObjectName("primaryBtn")
            def _do_verify():
                self._sync.send_verify_asset(asset.id)
                dlg.accept()
                self._status.showMessage(f"Verification request sent: {asset.name}", 3000)
            verify_btn.clicked.connect(_do_verify)
            btn_row.addWidget(verify_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.reject)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)
        dlg.exec()

    def _on_sync_complete(self):
        import db.asset_repo as asset_repo
        sitreps = self._sitrep_ctrl.load_all()
        for sitrep in sitreps:
            self._sync.send_sitrep(sitrep)
        asset = asset_repo.get_by_id(self._operator_id)
        if asset:
            self._sync.send_asset(asset)
        if sitreps:
            self._status.showMessage(
                f"Pushed {len(sitreps)} local SITREP(s) to server", 4000
            )

    def _on_sync_asset(self, asset):
        self._asset_panel.add_or_update_asset(asset)
        self._map.add_or_update_asset(asset)
        self._update_counts()

    def _on_sync_sitrep(self, sitrep):
        self._sitrep_panel.add_or_update_sitrep(sitrep)
        if sitrep.lat is not None and sitrep.lon is not None:
            self._map.add_or_update_sitrep(sitrep)
        self._update_counts()

    def _on_sync_sitrep_deleted(self, sitrep_id: int):
        self._sitrep_panel.remove_sitrep(sitrep_id)
        self._map.remove_sitrep(sitrep_id)
        self._update_counts()

    def _on_sync_asset_deleted(self, asset_id: int):
        self._asset_panel.remove_asset(asset_id)
        self._map.remove_asset(asset_id)
        self._update_counts()

    def _on_sync_asset_type(self, type_key: str, name: str, color: str):
        self._asset_panel.add_custom_type_group(type_key, name, color)

    def _on_sync_asset_type_deleted(self, type_key: str):
        self._asset_panel.remove_custom_type_group(type_key)

    def _on_asset_saved(self, asset):
        self._asset_panel.add_or_update_asset(asset)
        self._map.add_or_update_asset(asset)
        self._update_counts()
        if asset.id == self._operator_id and self._sync:
            self._status.showMessage(f"Profile saved: {asset.name}", 3000)
            self._sync.send_asset(asset)

    # ------------------------------------------------------------------
    # SITREP flow
    # ------------------------------------------------------------------

    def _open_add_sitrep(self):
        assets = self._asset_ctrl.load_all()
        dlg = SitrepDialog(self, assets=assets)
        dlg.pick_button.clicked.connect(lambda: self._start_place_mode(dlg, "sitrep"))
        dlg.accepted.connect(lambda: self._sitrep_ctrl.save(dlg.result_sitrep))
        dlg.show()

    def _on_sitrep_selected(self, sitrep_id: int):
        import db.sitrep_repo as repo
        sitrep = repo.get_by_id(sitrep_id)
        if not sitrep:
            return
        if sitrep.lat is not None:
            self._map.pan_to(sitrep.lat, sitrep.lon)
        assets = self._asset_ctrl.load_all()
        dlg = SitrepDialog(self, sitrep=sitrep, assets=assets,
                           mode="append", callsign=self._callsign)
        dlg.accepted.connect(lambda: self._sitrep_ctrl.save(dlg.result_sitrep))
        dlg.show()
        dlg.raise_()
        dlg.activateWindow()

    def _on_sitrep_saved(self, sitrep):
        self._sitrep_panel.add_or_update_sitrep(sitrep)
        if sitrep.lat is not None and sitrep.lon is not None:
            self._map.add_or_update_sitrep(sitrep)
        self._update_counts()
        self._status.showMessage(f"SITREP filed: {sitrep.title}", 3000)
        if self._sync:
            self._sync.send_sitrep(sitrep)

    # ------------------------------------------------------------------
    # Place mode
    # ------------------------------------------------------------------

    def _start_place_mode(self, dialog, mode: str):
        self._pending_dialog = dialog
        self._pending_mode   = mode
        dialog.hide()
        self._map.enter_place_mode(mode)
        self._status.showMessage("Click on the map to set position — Esc to cancel")

    def _on_map_clicked(self, lat: float, lon: float):
        if self._pending_dialog:
            self._pending_dialog.set_position(lat, lon)
            self._pending_dialog.show()
            self._pending_dialog = None
            self._pending_mode   = None
            self._status.showMessage("Position set", 2000)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape and self._pending_dialog:
            self._map.exit_place_mode()
            self._pending_dialog.show()
            self._pending_dialog = None
            self._pending_mode   = None
            self._status.showMessage("Place mode cancelled", 2000)
        super().keyPressEvent(event)

    def _on_mouse_moved(self, lat: float, lon: float):
        self._lbl_coords.setText(f"  Lat: {lat:.5f}  Lon: {lon:.5f}")

    # ------------------------------------------------------------------
    # RNode config
    # ------------------------------------------------------------------

    def _on_rnode_config(self, config: dict):
        self._server_rnode = config

    def _open_rnode_config(self):
        from ui.rnode_dialog import RNodeDialog
        if not self._rns_config:
            self._status.showMessage("No Reticulum config directory set.", 3000)
            return
        dlg = RNodeDialog(
            rns_config_dir = self._rns_config,
            server_config  = self._server_rnode,
            parent         = self,
        )
        dlg.exec()
