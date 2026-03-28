"""
ui/asset_dialog.py — Create/edit dialog for all asset types
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QGroupBox,
    QLabel, QLineEdit, QComboBox, QDoubleSpinBox, QSpinBox,
    QPushButton, QTextEdit, QListWidget, QListWidgetItem,
    QWidget, QStackedWidget, QCheckBox,
)
from PyQt6.QtCore import Qt

from models.asset import (
    Asset, Operator, SafeHouse, Cache, TxSite,
    AssetType, AssetStatus, TxType,
)


class AssetDialog(QDialog):
    def __init__(self, parent=None, asset: Asset = None, all_skills: list[str] = None,
                 initial_lat: float = None, initial_lon: float = None,
                 initial_type: str = None, exclude_operator: bool = False):
        super().__init__(parent)
        self._asset = asset
        self._all_skills = all_skills or []
        self._exclude_operator = exclude_operator
        self._result_asset = None

        title = "Edit Asset" if asset else "Add Asset"
        self.setWindowTitle(title)
        self.setMinimumWidth(440)

        self._build_ui(initial_lat, initial_lon, initial_type)
        if asset:
            self._populate(asset)

    def _build_ui(self, initial_lat, initial_lon, initial_type):
        root = QVBoxLayout(self)
        root.setSpacing(10)

        # ── Common fields ────────────────────────────────────────────
        common = QGroupBox("Asset")
        form = QFormLayout(common)
        form.setSpacing(8)

        self._type_combo = QComboBox()
        for t in AssetType:
            if self._exclude_operator and t == AssetType.OPERATOR:
                continue
            self._type_combo.addItem(t.value.capitalize(), t.value)
        # Add custom types from DB
        try:
            import db.asset_type_repo as _type_repo
            for td in _type_repo.get_custom():
                self._type_combo.addItem(td["name"], td["type_key"])
        except Exception:
            pass
        if initial_type:
            idx = self._type_combo.findData(initial_type)
            if idx >= 0:
                self._type_combo.setCurrentIndex(idx)
        self._type_combo.currentIndexChanged.connect(self._on_type_changed)

        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Required")

        self._status_combo = QComboBox()
        for s in AssetStatus:
            self._status_combo.addItem(s.value, s)

        self._status_note = QLineEdit()
        self._status_note.setPlaceholderText("Optional note on status")

        form.addRow("Type:",        self._type_combo)
        form.addRow("Name:",        self._name_edit)
        form.addRow("Status:",      self._status_combo)
        form.addRow("Status Note:", self._status_note)
        root.addWidget(common)

        # ── Position ─────────────────────────────────────────────────
        pos_group = QGroupBox("Position")
        pos_layout = QHBoxLayout(pos_group)
        pos_layout.setSpacing(8)

        self._lat_edit = QDoubleSpinBox()
        self._lat_edit.setRange(-90, 90)
        self._lat_edit.setDecimals(6)
        self._lat_edit.setPrefix("Lat: ")

        self._lon_edit = QDoubleSpinBox()
        self._lon_edit.setRange(-180, 180)
        self._lon_edit.setDecimals(6)
        self._lon_edit.setPrefix("Lon: ")

        self._pick_btn = QPushButton("Pick on Map")
        self._pick_btn.setToolTip("Click to activate place mode — then click on the map")

        if initial_lat is not None:
            self._lat_edit.setValue(initial_lat)
        if initial_lon is not None:
            self._lon_edit.setValue(initial_lon)

        pos_layout.addWidget(self._lat_edit)
        pos_layout.addWidget(self._lon_edit)
        pos_layout.addWidget(self._pick_btn)
        root.addWidget(pos_group)

        # ── Type-specific fields (stacked) ────────────────────────────
        self._stack = QStackedWidget()

        self._operator_page  = self._build_operator_page()
        self._safehouse_page = self._build_safehouse_page()
        self._cache_page     = self._build_cache_page()
        self._txsite_page    = self._build_txsite_page()

        self._custom_page = QWidget()   # empty page for custom types

        self._stack.addWidget(self._operator_page)   # index 0
        self._stack.addWidget(self._safehouse_page)  # index 1
        self._stack.addWidget(self._cache_page)      # index 2
        self._stack.addWidget(self._txsite_page)     # index 3
        self._stack.addWidget(self._custom_page)     # index 4

        root.addWidget(self._stack)
        self._on_type_changed()

        # ── Buttons ───────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        self._save_btn = QPushButton("Save")
        self._save_btn.setObjectName("primaryBtn")
        self._save_btn.clicked.connect(self._on_save)

        self._delete_btn = QPushButton("Delete")
        self._delete_btn.setObjectName("dangerBtn")
        self._delete_btn.setVisible(self._asset is not None)   # only in edit mode

        self._verify_btn = QPushButton("Verify")
        self._verify_btn.setObjectName("primaryBtn")
        # Only show if editing an unverified asset
        show_verify = self._asset is not None and not self._asset.verified
        self._verify_btn.setVisible(show_verify)
        self._verify_btn.clicked.connect(self._on_verify)

        btn_row.addWidget(self._delete_btn)
        btn_row.addStretch()
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(self._verify_btn)
        btn_row.addWidget(self._save_btn)
        root.addLayout(btn_row)

    def _build_operator_page(self) -> QWidget:
        w = QGroupBox("Operator Details")
        form = QFormLayout(w)
        self._callsign_edit = QLineEdit()
        self._callsign_edit.setPlaceholderText("e.g. ALPHA-1")
        form.addRow("Callsign:", self._callsign_edit)

        # Skill list
        form.addRow(QLabel("Skillsets:"))
        self._skill_list = QListWidget()
        self._skill_list.setFixedHeight(130)
        for skill in self._all_skills:
            item = QListWidgetItem(skill)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self._skill_list.addItem(item)

        custom_row = QHBoxLayout()
        self._custom_skill = QLineEdit()
        self._custom_skill.setPlaceholderText("Add custom skill...")
        add_skill_btn = QPushButton("Add")
        add_skill_btn.clicked.connect(self._add_custom_skill)
        custom_row.addWidget(self._custom_skill)
        custom_row.addWidget(add_skill_btn)

        form.addRow(self._skill_list)
        form.addRow(custom_row)
        return w

    def _build_safehouse_page(self) -> QWidget:
        w = QGroupBox("Safe House Details")
        form = QFormLayout(w)
        self._codename_edit = QLineEdit()
        self._codename_edit.setPlaceholderText("e.g. BRAVO-NEST")
        self._capacity_spin = QSpinBox()
        self._capacity_spin.setRange(0, 999)
        form.addRow("Codename:", self._codename_edit)
        form.addRow("Capacity:", self._capacity_spin)
        return w

    def _build_cache_page(self) -> QWidget:
        w = QGroupBox("Cache Details")
        form = QFormLayout(w)
        self._contents_edit = QTextEdit()
        self._contents_edit.setFixedHeight(80)
        self._contents_edit.setPlaceholderText("Describe cache contents...")
        form.addRow("Contents:", self._contents_edit)
        return w

    def _build_txsite_page(self) -> QWidget:
        w = QGroupBox("Transmitter Site Details")
        form = QFormLayout(w)
        self._freq_spin = QDoubleSpinBox()
        self._freq_spin.setRange(0.0, 10000.0)
        self._freq_spin.setDecimals(4)
        self._freq_spin.setSuffix(" MHz")
        self._txtype_combo = QComboBox()
        for t in TxType:
            self._txtype_combo.addItem(t.value, t)
        form.addRow("Frequency:", self._freq_spin)
        form.addRow("Type:",      self._txtype_combo)
        return w

    def _on_type_changed(self):
        type_key = self._type_combo.currentData()
        builtin_keys = [t.value for t in AssetType]
        if type_key in builtin_keys:
            idx = builtin_keys.index(type_key)
            self._stack.setCurrentIndex(idx)
        else:
            self._stack.setCurrentIndex(4)   # custom page (no extra fields)

    def _add_custom_skill(self):
        name = self._custom_skill.text().strip()
        if not name:
            return
        # Check not already in list
        for i in range(self._skill_list.count()):
            if self._skill_list.item(i).text().lower() == name.lower():
                self._custom_skill.clear()
                return
        item = QListWidgetItem(name)
        item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        item.setCheckState(Qt.CheckState.Checked)
        self._skill_list.addItem(item)
        self._custom_skill.clear()

    def _populate(self, asset: Asset):
        # Common — type_key is string for both enum and custom types
        type_key = asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type)
        idx = self._type_combo.findData(type_key)
        if idx >= 0:
            self._type_combo.setCurrentIndex(idx)
        self._type_combo.setEnabled(False)   # can't change type of existing asset
        self._name_edit.setText(asset.name)
        idx = self._status_combo.findData(asset.status)
        if idx >= 0:
            self._status_combo.setCurrentIndex(idx)
        self._status_note.setText(asset.status_note)
        self._lat_edit.setValue(asset.lat)
        self._lon_edit.setValue(asset.lon)

        # Type-specific
        if isinstance(asset, Operator):
            self._callsign_edit.setText(asset.callsign)
            skill_set = set(asset.skills)
            for i in range(self._skill_list.count()):
                item = self._skill_list.item(i)
                if item.text() in skill_set:
                    item.setCheckState(Qt.CheckState.Checked)

        elif isinstance(asset, SafeHouse):
            self._codename_edit.setText(asset.codename)
            self._capacity_spin.setValue(asset.capacity)

        elif isinstance(asset, Cache):
            self._contents_edit.setPlainText(asset.contents)

        elif isinstance(asset, TxSite):
            self._freq_spin.setValue(asset.frequency)
            idx = self._txtype_combo.findData(asset.tx_type)
            if idx >= 0:
                self._txtype_combo.setCurrentIndex(idx)

    def set_position(self, lat: float, lon: float):
        """Called externally when user picks a position on the map."""
        self._lat_edit.setValue(lat)
        self._lon_edit.setValue(lon)

    def _on_verify(self):
        """Mark as verified and save."""
        self._force_verified = True
        self._on_save()

    def _on_save(self):
        name = self._name_edit.text().strip()
        if not name:
            self._name_edit.setFocus()
            return

        type_key    = self._type_combo.currentData()
        status      = self._status_combo.currentData()
        lat         = self._lat_edit.value()
        lon         = self._lon_edit.value()
        status_note = self._status_note.text().strip()
        asset_id    = self._asset.id if self._asset else None

        # Resolve to enum if built-in, else keep as string
        try:
            asset_type = AssetType(type_key)
        except ValueError:
            asset_type = type_key   # custom type — plain string

        # verified: True if force-verified or server-created; preserve existing if editing
        if getattr(self, '_force_verified', False):
            verified = True
        elif self._asset is not None:
            verified = self._asset.verified
        else:
            verified = True   # server-created assets are pre-verified

        base = dict(
            id          = asset_id,
            asset_type  = asset_type,
            name        = name,
            lat         = lat,
            lon         = lon,
            status      = status,
            status_note = status_note,
            verified    = verified,
        )

        if asset_type == AssetType.OPERATOR:
            skills = []
            for i in range(self._skill_list.count()):
                item = self._skill_list.item(i)
                if item.checkState() == Qt.CheckState.Checked:
                    skills.append(item.text())
            self._result_asset = Operator(**base, callsign=self._callsign_edit.text().strip(), skills=skills)

        elif asset_type == AssetType.SAFEHOUSE:
            self._result_asset = SafeHouse(**base,
                codename=self._codename_edit.text().strip(),
                capacity=self._capacity_spin.value())

        elif asset_type == AssetType.CACHE:
            self._result_asset = Cache(**base, contents=self._contents_edit.toPlainText().strip())

        elif asset_type == AssetType.TXSITE:
            self._result_asset = TxSite(**base,
                frequency=self._freq_spin.value(),
                tx_type=self._txtype_combo.currentData())

        else:
            # Custom type — base Asset with string type_key
            from models.asset import Asset as _Asset
            self._result_asset = _Asset(**base)

        self.accept()

    @property
    def result_asset(self) -> Asset:
        return self._result_asset

    @property
    def pick_button(self):
        return self._pick_btn

    @property
    def delete_button(self):
        return self._delete_btn
