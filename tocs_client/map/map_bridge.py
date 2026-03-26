"""
map/map_bridge.py — QObject bridge between Leaflet JS and Python
"""

from PyQt6.QtCore import QObject, pyqtSignal, pyqtSlot


class MapBridge(QObject):
    """
    Registered with QWebChannel as 'tocs'.
    JS calls slots on this object; Python listens to the emitted signals.
    """

    # Emitted when user clicks on an existing asset marker
    asset_clicked = pyqtSignal(int)       # asset_id

    # Emitted when user clicks on an existing sitrep marker
    sitrep_clicked = pyqtSignal(int)      # sitrep_id

    # Emitted when user clicks the map in place-mode
    map_clicked = pyqtSignal(float, float)   # lat, lon

    # Emitted on every mouse move (for coordinate display in status bar)
    mouse_moved = pyqtSignal(float, float)   # lat, lon

    # Emitted once when the map JS has fully loaded
    map_ready = pyqtSignal()

    @pyqtSlot(int)
    def assetClicked(self, asset_id: int):
        self.asset_clicked.emit(asset_id)

    @pyqtSlot(int)
    def sitrepClicked(self, sitrep_id: int):
        self.sitrep_clicked.emit(sitrep_id)

    @pyqtSlot(float, float)
    def mapClicked(self, lat: float, lon: float):
        self.map_clicked.emit(lat, lon)

    @pyqtSlot(float, float)
    def mouseMove(self, lat: float, lon: float):
        self.mouse_moved.emit(lat, lon)

    @pyqtSlot()
    def mapReady(self):
        self.map_ready.emit()
