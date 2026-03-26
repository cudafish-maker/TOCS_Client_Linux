"""
ui/login_dialog.py — Startup login / registration dialog
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QPushButton, QTabWidget, QWidget, QFrame,
)
from PyQt6.QtCore import Qt, pyqtSignal

import db.session as session_cache


class LoginDialog(QDialog):
    login_successful = pyqtSignal(int, str)   # operator_id, callsign

    def __init__(self, sync_client, parent=None):
        super().__init__(parent)
        self._sync = sync_client
        self.setWindowTitle("TOCS — Login")
        self.setModal(True)
        self.setMinimumWidth(380)
        self.setWindowFlag(Qt.WindowType.WindowCloseButtonHint, False)
        self._build_ui()
        self._connect_signals()

        # Pre-fill last known callsign
        last = session_cache.get_last_callsign()
        if last:
            self._login_callsign.setText(last)
            self._login_password.setFocus()

    def _build_ui(self):
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)

        title = QLabel("TOCS")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title.setObjectName("loginTitle")
        sub = QLabel("Tactical Operations Command Software")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        layout.addWidget(sub)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(sep)

        # Tabs
        self._tabs = QTabWidget()

        # ------ Login tab ------
        login_tab = QWidget()
        lt = QVBoxLayout(login_tab)
        lt.setSpacing(8)

        lt.addWidget(QLabel("Callsign:"))
        self._login_callsign = QLineEdit()
        self._login_callsign.setPlaceholderText("e.g. W1AW")
        lt.addWidget(self._login_callsign)

        lt.addWidget(QLabel("Password:"))
        self._login_password = QLineEdit()
        self._login_password.setEchoMode(QLineEdit.EchoMode.Password)
        self._login_password.returnPressed.connect(self._on_login)
        lt.addWidget(self._login_password)

        self._login_btn = QPushButton("Log In")
        self._login_btn.setObjectName("primaryBtn")
        lt.addWidget(self._login_btn)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.HLine)
        lt.addWidget(sep2)

        self._offline_btn = QPushButton("Login Offline")
        self._offline_btn.setToolTip(
            "Use last cached credentials if the server is unreachable"
        )
        lt.addWidget(self._offline_btn)
        lt.addStretch()

        self._tabs.addTab(login_tab, "Log In")

        # ------ Register tab ------
        reg_tab = QWidget()
        rt = QVBoxLayout(reg_tab)
        rt.setSpacing(8)

        rt.addWidget(QLabel("Callsign:"))
        self._reg_callsign = QLineEdit()
        self._reg_callsign.setPlaceholderText("e.g. W1AW")
        rt.addWidget(self._reg_callsign)

        rt.addWidget(QLabel("Password:"))
        self._reg_password = QLineEdit()
        self._reg_password.setEchoMode(QLineEdit.EchoMode.Password)
        rt.addWidget(self._reg_password)

        rt.addWidget(QLabel("Confirm Password:"))
        self._reg_confirm = QLineEdit()
        self._reg_confirm.setEchoMode(QLineEdit.EchoMode.Password)
        self._reg_confirm.returnPressed.connect(self._on_register)
        rt.addWidget(self._reg_confirm)

        rt.addWidget(QLabel("Registration Passphrase:"))
        self._reg_passphrase = QLineEdit()
        self._reg_passphrase.setPlaceholderText("Provided by your network operator")
        rt.addWidget(self._reg_passphrase)

        self._reg_btn = QPushButton("Create Account")
        self._reg_btn.setObjectName("primaryBtn")
        rt.addWidget(self._reg_btn)
        rt.addStretch()

        self._tabs.addTab(reg_tab, "Register")

        layout.addWidget(self._tabs)

        # Status label
        self._status = QLabel("")
        self._status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._status.setWordWrap(True)
        self._status.setObjectName("loginStatus")
        layout.addWidget(self._status)

    def _connect_signals(self):
        self._login_btn.clicked.connect(self._on_login)
        self._offline_btn.clicked.connect(self._on_offline)
        self._reg_btn.clicked.connect(self._on_register)
        self._sync.auth_ok.connect(self._on_auth_ok)
        self._sync.auth_fail.connect(self._on_auth_fail)
        self._sync.status_changed.connect(self._status.setText)

    # ------------------------------------------------------------------

    def _on_login(self):
        callsign = self._login_callsign.text().strip().upper()
        password = self._login_password.text()
        if not callsign or not password:
            self._status.setText("Enter your callsign and password.")
            return
        self._set_busy(True)
        self._sync.authenticate(callsign, password, "login")

    def _on_register(self):
        callsign   = self._reg_callsign.text().strip().upper()
        password   = self._reg_password.text()
        confirm    = self._reg_confirm.text()
        passphrase = self._reg_passphrase.text().strip()
        if not callsign or not password:
            self._status.setText("Enter a callsign and password.")
            return
        if password != confirm:
            self._status.setText("Passwords do not match.")
            return
        if not passphrase:
            self._status.setText("Enter the registration passphrase.")
            return
        self._set_busy(True)
        self._sync.authenticate(callsign, password, "register",
                                reg_passphrase=passphrase)

    def _on_offline(self):
        callsign = self._login_callsign.text().strip().upper()
        password = self._login_password.text()
        if not callsign or not password:
            self._status.setText("Enter your callsign and password for offline login.")
            return
        op_id = session_cache.verify_offline(callsign, password)
        if op_id is not None:
            self.login_successful.emit(op_id, callsign)
            self.accept()
        else:
            self._status.setText(
                "Offline login failed — no cached session found for this callsign."
            )

    def _on_auth_ok(self, operator_id: int, callsign: str):
        self._set_busy(False)
        self.login_successful.emit(operator_id, callsign)
        self.accept()

    def _on_auth_fail(self, reason: str):
        self._set_busy(False)
        self._status.setText(f"Authentication failed: {reason}")

    def _set_busy(self, busy: bool):
        self._login_btn.setEnabled(not busy)
        self._reg_btn.setEnabled(not busy)
        self._offline_btn.setEnabled(not busy)
        self._tabs.setEnabled(not busy)
        if busy:
            self._status.setText("Connecting to server...")
