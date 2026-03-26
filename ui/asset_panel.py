"""
ui/asset_panel.py — Asset tree panel (server: full access)
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QTreeWidget, QTreeWidgetItem,
    QPushButton, QHBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from models.asset import Asset, AssetType, ASSET_COLORS, STATUS_COLORS, get_type_display_name

_BUILTIN_LABELS = {
    AssetType.OPERATOR:  "Operators",
    AssetType.SAFEHOUSE: "Safe Houses",
    AssetType.CACHE:     "Caches",
    AssetType.TXSITE:    "Transmitter Sites",
}


class AssetPanel(QWidget):
    asset_selected         = pyqtSignal(int)
    add_requested          = pyqtSignal(str)
    type_visibility_changed = pyqtSignal(str, bool)   # (type_key, visible)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict[int, QTreeWidgetItem] = {}
        self._groups: dict[str, QTreeWidgetItem] = {}   # type_key → group node
        self._build_ui()
        self._load_custom_type_groups()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("  Assets")
        header.setObjectName("panelHeader")
        header.setFixedHeight(28)
        layout.addWidget(header)

        self._tree = QTreeWidget()
        self._tree.setHeaderHidden(True)
        self._tree.itemClicked.connect(self._on_item_clicked)
        self._tree.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._tree)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(4, 4, 4, 4)
        add_btn = QPushButton("+ Add Asset")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(lambda: self.add_requested.emit("operator"))
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

        # Create built-in type groups
        for t in AssetType:
            self._create_group(t.value, _BUILTIN_LABELS[t], ASSET_COLORS[t])

    def _load_custom_type_groups(self):
        """Create tree groups for any custom types already in the DB."""
        try:
            import db.asset_type_repo as repo
            for td in repo.get_custom():
                if td["type_key"] not in self._groups:
                    self._create_group(td["type_key"], td["name"] + "s", td["color"])
        except Exception:
            pass

    def _create_group(self, type_key: str, label: str, color: str) -> QTreeWidgetItem:
        group = QTreeWidgetItem(self._tree, [f"  {label}"])
        group.setForeground(0, QColor(color))
        group.setFlags(
            (group.flags() & ~Qt.ItemFlag.ItemIsSelectable) | Qt.ItemFlag.ItemIsUserCheckable
        )
        group.setCheckState(0, Qt.CheckState.Checked)
        group.setExpanded(True)
        self._groups[type_key] = group
        return group

    def _get_or_create_group(self, type_key: str) -> QTreeWidgetItem:
        if type_key in self._groups:
            return self._groups[type_key]
        # Unknown custom type — create on the fly
        try:
            import db.asset_type_repo as repo
            color = repo.get_color(type_key)
            name  = repo.get_name(type_key)
        except Exception:
            color, name = "#cdd6f4", type_key.replace("_", " ").capitalize()
        return self._create_group(type_key, name + "s", color)

    def add_custom_type_group(self, type_key: str, name: str, color: str):
        """Called when a new custom type is defined (server: local; client: from sync)."""
        if type_key not in self._groups:
            self._create_group(type_key, name + "s", color)
        else:
            # Update existing group label/color
            group = self._groups[type_key]
            group.setForeground(0, QColor(color))
            self._update_group_counts()

    def remove_custom_type_group(self, type_key: str):
        """Remove a custom type group (only if it has no children)."""
        group = self._groups.pop(type_key, None)
        if group:
            idx = self._tree.indexOfTopLevelItem(group)
            if idx >= 0:
                self._tree.takeTopLevelItem(idx)

    # ------------------------------------------------------------------

    def load_assets(self, assets: list[Asset]):
        for group in self._groups.values():
            while group.childCount():
                group.removeChild(group.child(0))
        self._items.clear()
        for asset in assets:
            self._add_item(asset)
        self._update_group_counts()

    def add_or_update_asset(self, asset: Asset):
        if asset.id in self._items:
            self._update_item(self._items[asset.id], asset)
        else:
            self._add_item(asset)
        self._update_group_counts()

    def remove_asset(self, asset_id: int):
        if asset_id in self._items:
            item = self._items.pop(asset_id)
            parent = item.parent()
            if parent:
                parent.removeChild(item)
        self._update_group_counts()

    def _add_item(self, asset: Asset):
        type_key = asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type)
        group = self._get_or_create_group(type_key)
        item = QTreeWidgetItem(group)
        item.setData(0, Qt.ItemDataRole.UserRole, asset.id)
        self._update_item(item, asset)
        self._items[asset.id] = item

    def _update_item(self, item: QTreeWidgetItem, asset: Asset):
        from models.asset import Operator
        subtitle = f" [{asset.callsign}]" if isinstance(asset, Operator) and asset.callsign else ""
        item.setText(0, f"  {asset.name}{subtitle}")
        item.setForeground(0, QColor(STATUS_COLORS.get(asset.status, "#a6adc8")))
        item.setToolTip(0, f"{asset.status.value}  {asset.lat:.5f}, {asset.lon:.5f}")

    def _update_group_counts(self):
        self._tree.blockSignals(True)
        for type_key, group in self._groups.items():
            label = _BUILTIN_LABELS.get(type_key)
            if label is None:
                label = get_type_display_name(type_key) + "s"
            group.setText(0, f"  {label}  ({group.childCount()})")
        self._tree.blockSignals(False)

    def _on_item_clicked(self, item: QTreeWidgetItem, _col: int):
        asset_id = item.data(0, Qt.ItemDataRole.UserRole)
        if asset_id is not None:
            self.asset_selected.emit(asset_id)

    def _on_item_changed(self, item: QTreeWidgetItem, _col: int):
        """Fired when a group checkbox is toggled — emit visibility signal."""
        if item.data(0, Qt.ItemDataRole.UserRole) is not None:
            return  # asset item, not a group header
        for type_key, group in self._groups.items():
            if group is item:
                visible = item.checkState(0) == Qt.CheckState.Checked
                self.type_visibility_changed.emit(type_key, visible)
                break
