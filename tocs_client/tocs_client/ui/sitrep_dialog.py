"""
ui/sitrep_dialog.py — Create/edit/append SITREP dialog

mode="new"    — blank form, Save button
mode="edit"   — full edit, Save + Delete buttons  (server)
mode="append" — read-only view + append text area (client)
"""

from datetime import datetime, timezone

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QTextEdit, QPushButton,
    QDoubleSpinBox, QRadioButton, QFrame,
)
from PyQt6.QtCore import Qt

from models.sitrep import Sitrep, Severity, SEVERITY_COLORS


class SitrepDialog(QDialog):
    def __init__(self, parent=None, sitrep: Sitrep = None,
                 assets: list = None, mode: str = "new",
                 callsign: str = ""):
        super().__init__(parent)
        self._sitrep   = sitrep
        self._assets   = assets or []
        self._mode     = mode          # "new" | "edit" | "append"
        self._callsign = callsign
        self._result   = None

        titles = {"new": "New SITREP", "edit": "Edit SITREP", "append": "View / Append SITREP"}
        self.setWindowTitle(titles.get(mode, "SITREP"))
        self.setMinimumWidth(460)

        if mode == "append":
            self._build_append_ui()
        else:
            self._build_edit_ui()

        if sitrep:
            self._populate(sitrep)

    # ------------------------------------------------------------------
    # Edit / New UI
    # ------------------------------------------------------------------

    def _build_edit_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        content = QGroupBox("SITREP")
        form = QFormLayout(content)
        form.setSpacing(8)

        self._title_edit = QLineEdit()
        self._title_edit.setPlaceholderText("Required")

        self._severity_combo = QComboBox()
        for s in Severity:
            self._severity_combo.addItem(s.value, s)

        self._body_edit = QTextEdit()
        self._body_edit.setFixedHeight(120)
        self._body_edit.setPlaceholderText("Situation report details...")

        form.addRow("Title:",    self._title_edit)
        form.addRow("Severity:", self._severity_combo)
        form.addRow("Body:",     self._body_edit)
        root.addWidget(content)

        # Location
        loc = QGroupBox("Location")
        loc_layout = QVBoxLayout(loc)

        radio_row = QHBoxLayout()
        self._radio_asset = QRadioButton("Linked Asset")
        self._radio_pos   = QRadioButton("Map Position")
        self._radio_asset.setChecked(True)
        radio_row.addWidget(self._radio_asset)
        radio_row.addWidget(self._radio_pos)
        radio_row.addStretch()
        loc_layout.addLayout(radio_row)

        self._asset_combo = QComboBox()
        self._asset_combo.addItem("— none —", None)
        for a in self._assets:
            self._asset_combo.addItem(f"{a.name} ({a.asset_type.value})", a.id)
        loc_layout.addWidget(self._asset_combo)

        pos_row = QHBoxLayout()
        self._lat_spin = QDoubleSpinBox()
        self._lat_spin.setRange(-90, 90)
        self._lat_spin.setDecimals(6)
        self._lat_spin.setPrefix("Lat: ")
        self._lon_spin = QDoubleSpinBox()
        self._lon_spin.setRange(-180, 180)
        self._lon_spin.setDecimals(6)
        self._lon_spin.setPrefix("Lon: ")
        self._pick_btn = QPushButton("Pick on Map")
        pos_row.addWidget(self._lat_spin)
        pos_row.addWidget(self._lon_spin)
        pos_row.addWidget(self._pick_btn)
        loc_layout.addLayout(pos_row)

        root.addWidget(loc)

        self._radio_asset.toggled.connect(self._on_radio_changed)
        self._on_radio_changed()

        # Buttons
        btn_row = QHBoxLayout()

        if self._mode == "edit":
            self._delete_btn = QPushButton("Delete")
            self._delete_btn.setObjectName("dangerBtn")
            btn_row.addWidget(self._delete_btn)

        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._on_save)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(save_btn)
        root.addLayout(btn_row)

    # ------------------------------------------------------------------
    # Append (client read-only view + append area) UI
    # ------------------------------------------------------------------

    def _build_append_ui(self):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # Header info
        info = QGroupBox("SITREP")
        form = QFormLayout(info)
        form.setSpacing(6)

        self._lbl_title    = QLabel()
        self._lbl_title.setWordWrap(True)
        self._lbl_severity = QLabel()
        self._lbl_time     = QLabel()
        self._lbl_location = QLabel()

        form.addRow("Title:",     self._lbl_title)
        form.addRow("Severity:",  self._lbl_severity)
        form.addRow("Filed:",     self._lbl_time)
        form.addRow("Location:",  self._lbl_location)
        root.addWidget(info)

        # Existing body (read-only)
        body_box = QGroupBox("Report")
        body_layout = QVBoxLayout(body_box)
        self._body_view = QTextEdit()
        self._body_view.setReadOnly(True)
        self._body_view.setFixedHeight(120)
        body_layout.addWidget(self._body_view)
        root.addWidget(body_box)

        # Divider
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        root.addWidget(line)

        # Append area
        append_box = QGroupBox("Append Update")
        append_layout = QVBoxLayout(append_box)
        self._append_edit = QTextEdit()
        self._append_edit.setFixedHeight(80)
        self._append_edit.setPlaceholderText("Add new information to this SITREP...")
        append_layout.addWidget(self._append_edit)
        root.addWidget(append_box)

        # Buttons
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Close")
        cancel_btn.clicked.connect(self.reject)
        self._append_btn = QPushButton("Append")
        self._append_btn.setObjectName("primaryBtn")
        self._append_btn.clicked.connect(self._on_append)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._append_btn)
        root.addLayout(btn_row)

        # Stub attributes so callers don't crash
        self._pick_btn = QPushButton()   # invisible, never shown

    # ------------------------------------------------------------------
    # Populate
    # ------------------------------------------------------------------

    def _populate(self, s: Sitrep):
        if self._mode == "append":
            self._lbl_title.setText(f"<b>{s.title}</b>")
            color = SEVERITY_COLORS.get(s.severity, "#cdd6f4")
            self._lbl_severity.setText(
                f"<span style='color:{color};font-weight:bold'>{s.severity.value}</span>"
            )
            self._lbl_time.setText(s.timestamp[:16] if s.timestamp else "—")

            if s.asset_id is not None:
                loc_text = f"Asset ID {s.asset_id}"
                for a in self._assets:
                    if a.id == s.asset_id:
                        loc_text = f"{a.name} ({a.asset_type.value})"
                        break
            elif s.lat is not None:
                loc_text = f"{s.lat:.5f}, {s.lon:.5f}"
            else:
                loc_text = "—"
            self._lbl_location.setText(loc_text)

            self._body_view.setPlainText(s.body)
        else:
            self._title_edit.setText(s.title)
            idx = self._severity_combo.findData(s.severity)
            if idx >= 0:
                self._severity_combo.setCurrentIndex(idx)
            self._body_edit.setPlainText(s.body)

            if s.asset_id is not None:
                self._radio_asset.setChecked(True)
                idx = self._asset_combo.findData(s.asset_id)
                if idx >= 0:
                    self._asset_combo.setCurrentIndex(idx)
            else:
                self._radio_pos.setChecked(True)
                if s.lat is not None:
                    self._lat_spin.setValue(s.lat)
                if s.lon is not None:
                    self._lon_spin.setValue(s.lon)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_radio_changed(self):
        asset_mode = self._radio_asset.isChecked()
        self._asset_combo.setVisible(asset_mode)
        self._lat_spin.setVisible(not asset_mode)
        self._lon_spin.setVisible(not asset_mode)
        self._pick_btn.setVisible(not asset_mode)

    def _on_save(self):
        title = self._title_edit.text().strip()
        if not title:
            self._title_edit.setFocus()
            return

        severity = self._severity_combo.currentData()
        body     = self._body_edit.toPlainText().strip()
        sid      = self._sitrep.id if self._sitrep else None

        if self._radio_asset.isChecked():
            asset_id = self._asset_combo.currentData()
            lat, lon = None, None
            for a in self._assets:
                if a.id == asset_id:
                    lat, lon = a.lat, a.lon
                    break
        else:
            asset_id = None
            lat = self._lat_spin.value()
            lon = self._lon_spin.value()

        self._result = Sitrep(
            id=sid, title=title, body=body, severity=severity,
            asset_id=asset_id, lat=lat, lon=lon,
        )
        self.accept()

    def _on_append(self):
        new_text = self._append_edit.toPlainText().strip()
        if not new_text:
            self._append_edit.setFocus()
            return

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        tag = f"[{self._callsign} — {ts}]" if self._callsign else f"[{ts}]"
        existing = self._sitrep.body or ""
        combined = f"{existing}\n\n{tag}\n{new_text}".strip()

        self._result = Sitrep(
            id       = self._sitrep.id,
            title    = self._sitrep.title,
            body     = combined,
            severity = self._sitrep.severity,
            asset_id = self._sitrep.asset_id,
            lat      = self._sitrep.lat,
            lon      = self._sitrep.lon,
        )
        self.accept()

    def set_position(self, lat: float, lon: float):
        if self._mode != "append":
            self._lat_spin.setValue(lat)
            self._lon_spin.setValue(lon)
            self._radio_pos.setChecked(True)

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def result_sitrep(self) -> Sitrep:
        return self._result

    @property
    def pick_button(self):
        return self._pick_btn

    @property
    def delete_button(self):
        return getattr(self, "_delete_btn", None)
