"""
controllers/asset_controller.py — Business logic for asset management
"""

from PyQt6.QtCore import QObject, pyqtSignal

from models.asset import Asset
import db.asset_repo as repo


class AssetController(QObject):
    asset_saved   = pyqtSignal(object)   # Asset
    asset_deleted = pyqtSignal(int)      # asset_id

    def __init__(self, parent=None):
        super().__init__(parent)

    def load_all(self) -> list[Asset]:
        return repo.get_all()

    def save(self, asset: Asset) -> Asset:
        saved = repo.save(asset)
        self.asset_saved.emit(saved)
        return saved

    def delete(self, asset_id: int):
        repo.delete(asset_id)
        self.asset_deleted.emit(asset_id)

    def get_all_skills(self) -> list[str]:
        return repo.get_all_skills()
