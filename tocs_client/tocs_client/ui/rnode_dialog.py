"""
ui/rnode_dialog.py — RNode radio configuration dialog.

Shows the client's current RNode settings alongside the server's settings,
and offers a "Sync to Server" button that applies the server's radio parameters
to the local Reticulum config (preserving the client's own port selection).
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QLineEdit, QPushButton, QFrame, QMessageBox,
)
from PyQt6.QtCore import Qt


def _fmt_freq(hz) -> str:
    if hz is None:
        return "—"
    try:
        return f"{int(hz) / 1_000_000:.3f} MHz"
    except (TypeError, ValueError):
        return str(hz)


def _fmt_bw(hz) -> str:
    if hz is None:
        return "—"
    try:
        return f"{int(hz) / 1_000:.0f} kHz"
    except (TypeError, ValueError):
        return str(hz)


def _fmt_cr(cr) -> str:
    if cr is None:
        return "—"
    try:
        return f"4/{int(cr)}"
    except (TypeError, ValueError):
        return str(cr)


def _val(d: dict | None, key: str) -> str:
    if d is None:
        return "—"
    v = d.get(key)
    return "—" if v is None else str(v)


class RNodeDialog(QDialog):
    def __init__(self, rns_config_dir: str, server_config: dict | None, parent=None):
        super().__init__(parent)
        self._rns_config_dir = rns_config_dir
        self._server_config  = server_config
        self.setWindowTitle("RNode Configuration")
        self.setMinimumWidth(460)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI
    # ------------------------------------------------------------------

    def _build_ui(self):
        from sync.rnode_config import read_rnode_config
        client_cfg = read_rnode_config(self._rns_config_dir)

        layout = QVBoxLayout(self)
        layout.setSpacing(12)

        # ── Client settings ──────────────────────────────────────────
        lbl_c = QLabel("Client Settings")
        lbl_c.setObjectName("sectionHeader")
        layout.addWidget(lbl_c)

        if client_cfg:
            layout.addLayout(self._settings_grid(client_cfg, show_port=True))
        else:
            none_lbl = QLabel("No RNode interface configured.")
            none_lbl.setObjectName("dimLabel")
            layout.addWidget(none_lbl)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # ── Server settings ──────────────────────────────────────────
        lbl_s = QLabel("Server Settings")
        lbl_s.setObjectName("sectionHeader")
        layout.addWidget(lbl_s)

        if self._server_config:
            layout.addLayout(self._settings_grid(self._server_config, show_port=False))
        else:
            none_lbl2 = QLabel("No server RNode config received yet.")
            none_lbl2.setObjectName("dimLabel")
            layout.addWidget(none_lbl2)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep2)

        # ── Port input (shown when client has no RNode) ──────────────
        self._port_row = QHBoxLayout()
        self._port_lbl = QLabel("Device port:")
        self._port_edit = QLineEdit()
        self._port_edit.setPlaceholderText("/dev/ttyUSB0")
        self._port_edit.setMaximumWidth(180)
        self._port_row.addWidget(self._port_lbl)
        self._port_row.addWidget(self._port_edit)
        self._port_row.addStretch()
        port_widget_visible = (client_cfg is None and self._server_config is not None)
        self._port_lbl.setVisible(port_widget_visible)
        self._port_edit.setVisible(port_widget_visible)
        layout.addLayout(self._port_row)

        # ── Buttons ──────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()

        self._sync_btn = QPushButton("Sync to Server")
        self._sync_btn.setObjectName("primaryBtn")
        self._sync_btn.setEnabled(self._server_config is not None)
        self._sync_btn.clicked.connect(self._on_sync)
        btn_row.addWidget(self._sync_btn)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)

        layout.addLayout(btn_row)

    def _settings_grid(self, cfg: dict, show_port: bool) -> QGridLayout:
        grid = QGridLayout()
        grid.setColumnMinimumWidth(0, 140)
        grid.setHorizontalSpacing(12)
        grid.setVerticalSpacing(4)

        rows = []
        if show_port:
            rows.append(("Port:",           _val(cfg, "port")))
        rows += [
            ("Frequency:",      _fmt_freq(cfg.get("frequency"))),
            ("Bandwidth:",      _fmt_bw(cfg.get("bandwidth"))),
            ("TX Power:",       f"{_val(cfg, 'txpower')} dBm"),
            ("Spreading Factor:", _val(cfg, "spreadingfactor")),
            ("Coding Rate:",    _fmt_cr(cfg.get("codingrate"))),
        ]

        for r, (label, value) in enumerate(rows):
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
            val = QLabel(value)
            grid.addWidget(lbl, r, 0)
            grid.addWidget(val, r, 1)

        return grid

    # ------------------------------------------------------------------
    # Sync action
    # ------------------------------------------------------------------

    def _on_sync(self):
        from sync.rnode_config import (
            read_rnode_config, write_rnode_config, add_rnode_interface, RADIO_FIELDS,
        )
        if not self._server_config:
            return

        updates = {k: self._server_config[k]
                   for k in RADIO_FIELDS
                   if k in self._server_config and k != "port"}

        client_cfg = read_rnode_config(self._rns_config_dir)

        if client_cfg:
            # Update existing RNode block (preserve port)
            ok = write_rnode_config(self._rns_config_dir, updates)
            if ok:
                QMessageBox.information(
                    self, "Sync Complete",
                    "RNode radio settings updated.\n\n"
                    "Restart TOCS for Reticulum to apply the new settings."
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Sync Failed",
                                    "Could not write to the Reticulum config file.")
        else:
            # No RNode configured — need a port
            port = self._port_edit.text().strip()
            if not port:
                QMessageBox.warning(self, "Port Required",
                                    "Enter the serial port for your RNode (e.g. /dev/ttyUSB0).")
                return
            ok = add_rnode_interface(
                self._rns_config_dir,
                port        = port,
                frequency   = updates.get("frequency", 915000000),
                bandwidth   = updates.get("bandwidth", 125000),
                txpower     = updates.get("txpower", 17),
                spreadingfactor = updates.get("spreadingfactor", 11),
                codingrate  = updates.get("codingrate", 8),
            )
            if ok:
                QMessageBox.information(
                    self, "RNode Added",
                    "RNode interface added to Reticulum config.\n\n"
                    "Restart TOCS for Reticulum to apply the new settings."
                )
                self.accept()
            else:
                QMessageBox.warning(self, "Failed",
                                    "Could not write to the Reticulum config file.")
