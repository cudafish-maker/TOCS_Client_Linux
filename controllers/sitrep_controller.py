"""
controllers/sitrep_controller.py — Business logic for SITREP management
"""

from PyQt6.QtCore import QObject, pyqtSignal

from models.sitrep import Sitrep
import db.sitrep_repo as repo


class SitrepController(QObject):
    sitrep_saved   = pyqtSignal(object)  # Sitrep
    sitrep_deleted = pyqtSignal(int)     # sitrep_id

    def __init__(self, parent=None):
        super().__init__(parent)

    def load_all(self) -> list[Sitrep]:
        return repo.get_all()

    def save(self, sitrep: Sitrep) -> Sitrep:
        saved = repo.save(sitrep)
        self.sitrep_saved.emit(saved)
        return saved

    def delete(self, sitrep_id: int):
        repo.delete(sitrep_id)
        self.sitrep_deleted.emit(sitrep_id)
