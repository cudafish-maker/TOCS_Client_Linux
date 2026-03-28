"""
ui/asset_type_dialog.py — Manage custom asset type definitions
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QListWidget, QListWidgetItem, QFrame,
    QMessageBox, QColorDialog,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QColor

import db.asset_type_repo as repo
from models.asset import AssetType


class AssetTypeDialog(QDialog):
    type_saved   = pyqtSignal(str, str, str)   # type_key, name, color
    type_deleted = pyqtSignal(str)             # type_key

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Asset Types")
        self.setMinimumWidth(480)
        self.setMinimumHeight(420)
        self._build_ui()
        self._refresh_list()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        layout.addWidget(QLabel("Manage asset types. Built-in types cannot be deleted."))

        self._list = QListWidget()
        self._list.currentRowChanged.connect(self._on_selection_changed)
        layout.addWidget(self._list)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Edit form
        form_label = QLabel("New / Edit Type:")
        layout.addWidget(form_label)

        row1 = QHBoxLayout()
        self._name_edit = QLineEdit()
        self._name_edit.setPlaceholderText("Display name (e.g. Food Bank)")
        self._name_edit.textChanged.connect(self._on_name_changed)
        row1.addWidget(self._name_edit)
        layout.addLayout(row1)

        row2 = QHBoxLayout()
        row2.addWidget(QLabel("Color:"))
        self._color_preview = QPushButton()
        self._color_preview.setFixedWidth(80)
        self._color_preview.setFixedHeight(28)
        self._color_preview.clicked.connect(self._pick_color)
        self._selected_color = "#cdd6f4"
        self._update_color_preview()
        row2.addWidget(self._color_preview)

        self._key_label = QLabel("key: —")
        self._key_label.setStyleSheet("color: #585b70; font-size: 11px;")
        row2.addWidget(self._key_label)
        row2.addStretch()
        layout.addLayout(row2)

        btn_row = QHBoxLayout()
        self._save_btn = QPushButton("Save Type")
        self._save_btn.setObjectName("primaryBtn")
        self._save_btn.setEnabled(False)
        self._save_btn.clicked.connect(self._on_save)

        self._delete_btn = QPushButton("Delete Selected")
        self._delete_btn.setEnabled(False)
        self._delete_btn.clicked.connect(self._on_delete)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)

        btn_row.addWidget(self._delete_btn)
        btn_row.addStretch()
        btn_row.addWidget(close_btn)
        btn_row.addWidget(self._save_btn)
        layout.addLayout(btn_row)

    def _refresh_list(self):
        self._list.clear()
        for td in repo.get_all():
            label = f"  {td['name']}  [{td['type_key']}]"
            if td["is_builtin"]:
                label += "  (built-in)"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, td)
            item.setForeground(QColor(td["color"]))
            self._list.addItem(item)

    def _on_selection_changed(self, row: int):
        item = self._list.item(row)
        if item is None:
            self._delete_btn.setEnabled(False)
            return
        td = item.data(Qt.ItemDataRole.UserRole)
        is_builtin = td.get("is_builtin", 0)
        self._delete_btn.setEnabled(not is_builtin)
        # Pre-fill form for editing
        if not is_builtin:
            self._name_edit.setText(td["name"])
            self._selected_color = td["color"]
            self._update_color_preview()
            self._key_label.setText(f"key: {td['type_key']}")
            self._save_btn.setEnabled(True)
            # Store the existing key so save knows it's an edit
            self._editing_key = td["type_key"]
        else:
            self._editing_key = None

    def _on_name_changed(self, text: str):
        if not hasattr(self, '_editing_key') or self._editing_key is None:
            # Generate preview key for new type
            import re
            key = re.sub(r'[^a-z0-9]+', '_', text.lower()).strip('_') or "—"
            self._key_label.setText(f"key: {key}")
        self._save_btn.setEnabled(bool(text.strip()))

    def _pick_color(self):
        color = QColorDialog.getColor(
            QColor(self._selected_color), self, "Choose Type Color"
        )
        if color.isValid():
            self._selected_color = color.name()
            self._update_color_preview()

    def _update_color_preview(self):
        self._color_preview.setStyleSheet(
            f"background-color: {self._selected_color}; border: 1px solid #45475a; border-radius: 3px;"
        )

    def _on_save(self):
        name = self._name_edit.text().strip()
        if not name:
            return

        editing_key = getattr(self, '_editing_key', None)
        if editing_key:
            type_key = editing_key
        else:
            type_key = repo.make_unique_key(name)

        # Protect built-ins from overwrite
        all_types = {td["type_key"]: td for td in repo.get_all()}
        if type_key in all_types and all_types[type_key]["is_builtin"]:
            QMessageBox.warning(self, "Protected", "Cannot overwrite a built-in asset type.")
            return

        repo.save(type_key, name, self._selected_color)
        self.type_saved.emit(type_key, name, self._selected_color)
        self._refresh_list()
        self._name_edit.clear()
        self._selected_color = "#cdd6f4"
        self._update_color_preview()
        self._key_label.setText("key: —")
        self._editing_key = None
        self._save_btn.setEnabled(False)

    def _on_delete(self):
        item = self._list.currentItem()
        if not item:
            return
        td = item.data(Qt.ItemDataRole.UserRole)
        if td.get("is_builtin"):
            return
        confirm = QMessageBox.question(
            self, "Delete Type",
            f"Delete asset type \"{td['name']}\"?\n\n"
            "Existing assets of this type will remain but may display incorrectly.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if confirm == QMessageBox.StandardButton.Yes:
            repo.delete(td["type_key"])
            self.type_deleted.emit(td["type_key"])
            self._refresh_list()
            self._editing_key = None
