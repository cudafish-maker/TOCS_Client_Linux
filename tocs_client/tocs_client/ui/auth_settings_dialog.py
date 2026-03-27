"""
ui/auth_settings_dialog.py — Configure registration passphrase and view registered users
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QFrame, QListWidget, QListWidgetItem, QMessageBox,
)
from PyQt6.QtCore import Qt

import db.server_config as server_config
import db.user_repo as user_repo


class AuthSettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Auth Settings")
        self.setMinimumWidth(440)
        self._build_ui()
        self._load_users()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(10)

        # --- Passphrase section ---
        layout.addWidget(QLabel("Registration Passphrase:"))

        row = QHBoxLayout()
        self._passphrase = QLineEdit()
        self._passphrase.setText(server_config.get_registration_passphrase())
        self._passphrase.setPlaceholderText("Leave empty to disable all new registrations")
        row.addWidget(self._passphrase)

        save_btn = QPushButton("Save")
        save_btn.setObjectName("primaryBtn")
        save_btn.clicked.connect(self._save_passphrase)
        row.addWidget(save_btn)
        layout.addLayout(row)

        note = QLabel(
            "Users must supply this passphrase when creating an account.\n"
            "Leave empty to block all new registrations."
        )
        note.setWordWrap(True)
        layout.addWidget(note)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # --- Registered users section ---
        layout.addWidget(QLabel("Registered Users:"))
        self._user_list = QListWidget()
        self._user_list.setMaximumHeight(180)
        layout.addWidget(self._user_list)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _load_users(self):
        self._user_list.clear()
        for u in user_repo.get_all_users():
            self._user_list.addItem(
                QListWidgetItem(f"  {u['callsign']}  (operator_id={u['operator_id']})")
            )

    def _save_passphrase(self):
        passphrase = self._passphrase.text().strip()
        server_config.set_registration_passphrase(passphrase)
        if passphrase:
            QMessageBox.information(self, "Saved",
                "Registration passphrase updated.")
        else:
            QMessageBox.information(self, "Saved",
                "Passphrase cleared — new registrations are now disabled.")
