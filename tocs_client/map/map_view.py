"""
map/map_view.py — QWebEngineView wrapper with Leaflet + QWebChannel integration
"""

import os
import json

from PyQt6.QtWebEngineWidgets import QWebEngineView
from PyQt6.QtWebEngineCore import QWebEnginePage, QWebEngineSettings
from PyQt6.QtWebChannel import QWebChannel
from PyQt6.QtCore import QUrl, pyqtSignal

from map.map_bridge import MapBridge


def _qwebchannel_js() -> str:
    """Load qwebchannel.js bundled alongside this module."""
    path = os.path.join(os.path.dirname(__file__), "qwebchannel.js")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


class MapView(QWebEngineView):
    """
    Embeds Leaflet in a QWebEngineView with a Python↔JS bridge via QWebChannel.

    Correct init order (DO NOT change):
      1. QWebEngineView constructed
      2. QWebChannel registered on the page
      3. setHtml() called — bridge is available when JS runs
      4. All JS calls deferred until map_ready signal
    """

    # Re-export bridge signals for convenience
    asset_clicked  = pyqtSignal(int)
    sitrep_clicked = pyqtSignal(int)
    map_clicked    = pyqtSignal(float, float)
    mouse_moved    = pyqtSignal(float, float)
    map_ready      = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._ready = False
        self._hidden_types: set = set()   # type keys currently hidden

        # Set a real browser user agent so OSM doesn't block tile requests
        self.page().profile().setHttpUserAgent(
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )

        # Allow OSM tile requests from file:// origin
        settings = self.page().settings()
        settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)

        # 1. Bridge object
        self._bridge = MapBridge()
        self._bridge.asset_clicked.connect(self.asset_clicked)
        self._bridge.sitrep_clicked.connect(self.sitrep_clicked)
        self._bridge.map_clicked.connect(self.map_clicked)
        self._bridge.mouse_moved.connect(self.mouse_moved)
        self._bridge.map_ready.connect(self._on_map_ready)

        # 2. Register bridge on page BEFORE loading HTML
        self._channel = QWebChannel(self.page())
        self._channel.registerObject("tocs", self._bridge)
        self.page().setWebChannel(self._channel)

        # 3. Load HTML (bridge is registered, so JS can connect immediately)
        self._load_map()

    def _load_map(self):
        html_path = os.path.join(os.path.dirname(__file__), "map.html")
        with open(html_path, "r", encoding="utf-8") as f:
            html = f.read()

        # Inject qwebchannel.js as an inline script before the closing </head>
        qwc_js = _qwebchannel_js()
        if qwc_js:
            injection = f"<script>\n{qwc_js}\n</script>\n</head>"
            html = html.replace("</head>", injection, 1)

        base_url = QUrl.fromLocalFile(os.path.dirname(__file__) + os.sep)
        self.setHtml(html, base_url)

    def _on_map_ready(self):
        self._ready = True
        self.map_ready.emit()

    # ------------------------------------------------------------------
    # Public API — all JS calls go through here
    # ------------------------------------------------------------------

    def _js(self, code: str):
        """Run JS; safe to call before map_ready (queued until ready)."""
        if self._ready:
            self.page().runJavaScript(code)

    def add_or_update_asset(self, asset):
        """Push an asset to the map. `asset` is a models.Asset subclass."""
        from models.asset import get_asset_color
        type_key = asset.asset_type.value if hasattr(asset.asset_type, 'value') else str(asset.asset_type)
        data = {
            "id":          asset.id,
            "name":        asset.name,
            "asset_type":  type_key,
            "color":       get_asset_color(asset.asset_type),
            "verified":    asset.verified,
            "lat":         asset.lat,
            "lon":         asset.lon,
            "status":      asset.status.value,
            "status_note": asset.status_note,
        }
        # Type-specific extras for popup
        from models.asset import Operator, SafeHouse, TxSite
        if isinstance(asset, Operator):
            data["callsign"] = asset.callsign
        elif isinstance(asset, SafeHouse):
            data["codename"] = asset.codename
        elif isinstance(asset, TxSite):
            data["frequency"] = asset.frequency

        self._js(f"addOrUpdateAsset({json.dumps(data)})")
        # If this type is currently hidden, hide the marker we just added
        if type_key in self._hidden_types:
            self._js(f"setTypeVisible({json.dumps(type_key)}, false)")

    def set_type_visible(self, type_key: str, visible: bool):
        """Show or hide all map markers of a given asset type."""
        if visible:
            self._hidden_types.discard(type_key)
        else:
            self._hidden_types.add(type_key)
        self._js(f"setTypeVisible({json.dumps(type_key)}, {'true' if visible else 'false'})")

    def remove_asset(self, asset_id: int):
        self._js(f"removeAsset({asset_id})")

    def add_or_update_sitrep(self, sitrep):
        """Push a sitrep marker. Uses asset position if asset_id set, otherwise lat/lon."""
        if sitrep.lat is None or sitrep.lon is None:
            return
        data = {
            "id":       sitrep.id,
            "title":    sitrep.title,
            "severity": sitrep.severity.value,
            "lat":      sitrep.lat,
            "lon":      sitrep.lon,
        }
        self._js(f"addOrUpdateSitrep({json.dumps(data)})")

    def remove_sitrep(self, sitrep_id: int):
        self._js(f"removeSitrep({sitrep_id})")

    def pan_to(self, lat: float, lon: float, zoom: int = None):
        if zoom is not None:
            self._js(f"panTo({lat}, {lon}, {zoom})")
        else:
            self._js(f"panTo({lat}, {lon})")

    def enter_place_mode(self, mode: str = "asset"):
        """Put map into click-to-place mode. mode: 'asset' or 'sitrep'"""
        self._js(f"enterPlaceMode('{mode}')")

    def exit_place_mode(self):
        self._js("exitPlaceMode()")
