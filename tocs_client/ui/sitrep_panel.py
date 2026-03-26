"""
ui/sitrep_panel.py — Right-side SITREP list panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

from models.sitrep import Sitrep, SEVERITY_COLORS


class SitrepPanel(QWidget):
    sitrep_selected  = pyqtSignal(int)   # sitrep_id
    add_requested    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict[int, QListWidgetItem] = {}
        self._build_ui()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        header = QLabel("  SITREPs")
        header.setObjectName("panelHeader")
        header.setFixedHeight(28)
        layout.addWidget(header)

        self._list = QListWidget()
        self._list.setObjectName("sitrepList")
        self._list.itemClicked.connect(self._on_item_clicked)
        layout.addWidget(self._list)

        btn_row = QHBoxLayout()
        btn_row.setContentsMargins(4, 4, 4, 4)
        add_btn = QPushButton("+ New SITREP")
        add_btn.setObjectName("primaryBtn")
        add_btn.clicked.connect(self.add_requested.emit)
        btn_row.addWidget(add_btn)
        layout.addLayout(btn_row)

    def load_sitreps(self, sitreps: list[Sitrep]):
        self._list.clear()
        self._items.clear()
        for s in sitreps:
            self._add_item(s)

    def add_or_update_sitrep(self, sitrep: Sitrep):
        if sitrep.id in self._items:
            self._update_item(self._items[sitrep.id], sitrep)
        else:
            self._add_item(sitrep)

    def _add_item(self, sitrep: Sitrep):
        item = QListWidgetItem()
        item.setData(Qt.ItemDataRole.UserRole, sitrep.id)
        self._update_item(item, sitrep)
        self._list.addItem(item)
        self._items[sitrep.id] = item

    def _update_item(self, item: QListWidgetItem, sitrep: Sitrep):
        ts = sitrep.timestamp[:16].replace("T", " ") if sitrep.timestamp else ""
        item.setText(f"  [{sitrep.severity.value}] {sitrep.title}\n  {ts}")
        color = SEVERITY_COLORS.get(sitrep.severity, "#cdd6f4")
        item.setForeground(QColor(color))

    def remove_sitrep(self, sitrep_id: int):
        item = self._items.pop(sitrep_id, None)
        if item:
            self._list.takeItem(self._list.row(item))

    def _on_item_clicked(self, item: QListWidgetItem):
        sitrep_id = item.data(Qt.ItemDataRole.UserRole)
        if sitrep_id is not None:
            self.sitrep_selected.emit(sitrep_id)
