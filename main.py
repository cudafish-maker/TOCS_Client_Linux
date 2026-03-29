#!/usr/bin/env python3
"""
TOCS Client — Operator profile + SITREPs + integrated chat, syncs via Reticulum

Usage:
  python3 main.py [--rns-config <dir>]
"""

import sys
import os
import argparse
os.environ.setdefault("QTWEBENGINE_CHROMIUM_FLAGS", "--no-sandbox")

import RNS
from PyQt6.QtWidgets import QApplication, QDialog
from db.database import init_db
from ui.theme import STYLESHEET
from ui.main_window import MainWindow


def _find_rns_config():
    candidates = [
        os.path.expanduser("~/claude/i2pchat/config"),
        os.path.expanduser("~/i2pchat/config"),
        os.path.expanduser("~/.config/reticulum"),
    ]
    for path in candidates:
        if os.path.isdir(path):
            return path
    return candidates[0]


DEFAULT_RNS_CONFIG = _find_rns_config()


def main():
    parser = argparse.ArgumentParser(description="TOCS Client")
    parser.add_argument("--rns-config", default=DEFAULT_RNS_CONFIG,
                        help=f"Reticulum config dir (default: {DEFAULT_RNS_CONFIG})")
    parser.add_argument("--loglevel", default=2, type=int, help="RNS log level 0-7")
    args = parser.parse_args()

    os.makedirs(args.rns_config, exist_ok=True)

    print(f"Starting Reticulum... (config: {args.rns_config})")
    RNS.Reticulum(configdir=args.rns_config, loglevel=args.loglevel)

    app = QApplication(sys.argv)
    app.setApplicationName("TOCS Client")
    app.setStyleSheet(STYLESHEET)

    init_db()

    from sync.rns_sync import SyncClient
    sync = SyncClient(config_dir=args.rns_config)

    from ui.login_dialog import LoginDialog
    dlg = LoginDialog(sync_client=sync)

    auth_result = {}

    def _on_login(operator_id, callsign):
        auth_result["operator_id"] = operator_id
        auth_result["callsign"]    = callsign

    dlg.login_successful.connect(_on_login)

    if dlg.exec() != QDialog.DialogCode.Accepted:
        sys.exit(0)

    win = MainWindow(
        operator_id    = auth_result["operator_id"],
        callsign       = auth_result["callsign"],
        sync_client    = sync,
        rns_config_dir = args.rns_config,
    )
    win.show()
    # Signals are now connected — safe to ask the server for data.
    sync.begin_sync()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
