"""
ui/sitrep_panel.py — Right-side SITREP list panel
"""

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QListWidget, QListWidgetItem,
    QPushButton, QHBoxLayout, QStyledItemDelegate,
)
from PyQt6.QtCore import Qt, pyqtSignal, QTimer
from PyQt6.QtGui import QColor, QPainter, QPen

from models.sitrep import Sitrep, SEVERITY_COLORS


class _SitrepDelegate(QStyledItemDelegate):
    """Draws a severity-colored flashing outline on alerted items."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._flash_colors: dict[int, QColor] = {}

    def set_flash(self, sitrep_id: int, color: QColor | None):
        if color is None:
            self._flash_colors.pop(sitrep_id, None)
        else:
            self._flash_colors[sitrep_id] = color

    def paint(self, painter: QPainter, option, index):
        super().paint(painter, option, index)
        sitrep_id = index.data(Qt.ItemDataRole.UserRole)
        color = self._flash_colors.get(sitrep_id)
        if color:
            painter.save()
            pen = QPen(color)
            pen.setWidth(3)
            painter.setPen(pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(option.rect.adjusted(2, 2, -2, -2))
            painter.restore()


class SitrepPanel(QWidget):
    sitrep_selected  = pyqtSignal(int)   # sitrep_id
    add_requested    = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items: dict[int, QListWidgetItem] = {}
        self._flash_timers: dict[int, QTimer] = {}
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
        self._delegate = _SitrepDelegate(self._list)
        self._list.setItemDelegate(self._delegate)
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

    def flash_sitrep(self, sitrep_id: int, severity):
        """Flash a severity-colored outline until the user clicks the item."""
        if sitrep_id not in self._items:
            return

        # Cancel any existing flash for this item
        old = self._flash_timers.pop(sitrep_id, None)
        if old:
            old.stop()

        on_color = QColor(SEVERITY_COLORS.get(severity, "#cdd6f4"))
        state = [0]

        def _tick():
            self._delegate.set_flash(sitrep_id, on_color if state[0] % 2 == 0 else None)
            self._list.viewport().update()
            state[0] += 1

        timer = QTimer(self)
        timer.setInterval(400)
        timer.timeout.connect(_tick)
        self._flash_timers[sitrep_id] = timer
        _tick()       # first flash is immediate
        timer.start()

    def _stop_flash(self, sitrep_id: int):
        timer = self._flash_timers.pop(sitrep_id, None)
        if timer:
            timer.stop()
        self._delegate.set_flash(sitrep_id, None)
        self._list.viewport().update()

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
            self._stop_flash(sitrep_id)
            self.sitrep_selected.emit(sitrep_id)
