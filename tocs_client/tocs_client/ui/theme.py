"""
ui/theme.py — Catppuccin Mocha palette and global QSS stylesheet
"""

# Catppuccin Mocha palette
ROSEWATER = "#f5e0dc"
FLAMINGO  = "#f2cdcd"
PINK      = "#f5c2e7"
MAUVE     = "#cba6f7"
RED       = "#f38ba8"
MAROON    = "#eba0ac"
PEACH     = "#fab387"
YELLOW    = "#f9e2af"
GREEN     = "#a6e3a1"
TEAL      = "#94e2d5"
SKY       = "#89dceb"
SAPPHIRE  = "#74c7ec"
BLUE      = "#89b4fa"
LAVENDER  = "#b4befe"
TEXT      = "#cdd6f4"
SUBTEXT1  = "#bac2de"
SUBTEXT0  = "#a6adc8"
OVERLAY2  = "#9399b2"
OVERLAY1  = "#7f849c"
OVERLAY0  = "#6c7086"
SURFACE2  = "#585b70"
SURFACE1  = "#45475a"
SURFACE0  = "#313244"
BASE      = "#1e1e2e"
MANTLE    = "#181825"
CRUST     = "#11111b"

STYLESHEET = f"""
    QMainWindow, QWidget {{
        background-color: {BASE};
        color: {TEXT};
        font-family: "Monospace";
        font-size: 11px;
    }}
    QMenuBar {{
        background-color: {MANTLE};
        color: {TEXT};
        border-bottom: 1px solid {SURFACE0};
    }}
    QMenuBar::item:selected {{
        background-color: {SURFACE0};
    }}
    QMenu {{
        background-color: {MANTLE};
        color: {TEXT};
        border: 1px solid {SURFACE0};
    }}
    QMenu::item:selected {{
        background-color: {SURFACE1};
    }}
    QToolBar {{
        background-color: {MANTLE};
        border-bottom: 1px solid {SURFACE0};
        spacing: 4px;
        padding: 2px;
    }}
    QToolButton {{
        background-color: transparent;
        color: {TEXT};
        border: none;
        border-radius: 4px;
        padding: 4px 8px;
    }}
    QToolButton:hover  {{ background-color: {SURFACE0}; }}
    QToolButton:pressed {{ background-color: {SURFACE1}; }}
    QSplitter::handle  {{ background-color: {SURFACE0}; }}
    QTreeWidget {{
        background-color: {MANTLE};
        border: none;
        color: {TEXT};
        outline: none;
    }}
    QTreeWidget::item {{
        padding: 4px 0;
        border-bottom: 1px solid {SURFACE0};
        font-size: 13px;
    }}
    QTreeWidget::item:selected {{
        background-color: {SURFACE1};
        color: {TEXT};
    }}
    QTreeWidget::branch {{
        background-color: {MANTLE};
    }}
    QHeaderView::section {{
        background-color: {SURFACE0};
        color: {SUBTEXT0};
        border: none;
        padding: 4px;
        font-size: 10px;
    }}
    QListWidget {{
        background-color: {MANTLE};
        border: none;
        color: {TEXT};
    }}
    QListWidget::item {{
        padding: 4px 0;
        border-bottom: 1px solid {SURFACE0};
    }}
    QListWidget::item:selected {{
        background-color: {SURFACE1};
    }}
    QTextEdit, QPlainTextEdit {{
        background-color: {MANTLE};
        border: 1px solid {SURFACE0};
        border-radius: 4px;
        color: {TEXT};
        selection-background-color: {SURFACE2};
    }}
    QLineEdit {{
        background-color: {MANTLE};
        border: 1px solid {SURFACE0};
        border-radius: 4px;
        color: {TEXT};
        padding: 4px 8px;
        height: 26px;
    }}
    QLineEdit:focus {{ border-color: {BLUE}; }}
    QComboBox {{
        background-color: {MANTLE};
        border: 1px solid {SURFACE0};
        border-radius: 4px;
        color: {TEXT};
        padding: 4px 8px;
        height: 26px;
    }}
    QComboBox:focus  {{ border-color: {BLUE}; }}
    QComboBox::drop-down {{ border: none; }}
    QComboBox QAbstractItemView {{
        background-color: {MANTLE};
        color: {TEXT};
        selection-background-color: {SURFACE1};
        border: 1px solid {SURFACE0};
    }}
    QSpinBox, QDoubleSpinBox {{
        background-color: {MANTLE};
        border: 1px solid {SURFACE0};
        border-radius: 4px;
        color: {TEXT};
        padding: 4px;
    }}
    QSpinBox:focus, QDoubleSpinBox:focus {{ border-color: {BLUE}; }}
    QPushButton {{
        background-color: {SURFACE0};
        color: {TEXT};
        border: 1px solid {SURFACE1};
        border-radius: 4px;
        padding: 5px 14px;
    }}
    QPushButton:hover   {{ background-color: {SURFACE1}; }}
    QPushButton:pressed {{ background-color: {SURFACE2}; }}
    QPushButton#primaryBtn {{
        background-color: {BLUE};
        color: {CRUST};
        border: none;
        font-weight: bold;
    }}
    QPushButton#primaryBtn:hover   {{ background-color: {LAVENDER}; }}
    QPushButton#primaryBtn:pressed {{ background-color: {SAPPHIRE}; }}
    QPushButton#dangerBtn {{
        background-color: {RED};
        color: {CRUST};
        border: none;
        font-weight: bold;
    }}
    QPushButton#dangerBtn:hover {{ background-color: {MAROON}; }}
    QLabel#panelHeader {{
        background-color: {MANTLE};
        color: {BLUE};
        font-size: 11px;
        font-weight: bold;
        border-bottom: 1px solid {SURFACE0};
        padding: 4px 8px;
    }}
    QLabel#sectionLabel {{
        color: {SUBTEXT0};
        font-size: 10px;
        font-weight: bold;
    }}
    QScrollBar:vertical {{
        background: {MANTLE}; width: 8px; border-radius: 4px;
    }}
    QScrollBar::handle:vertical {{
        background: {SURFACE2}; border-radius: 4px; min-height: 20px;
    }}
    QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0; }}
    QScrollBar:horizontal {{
        background: {MANTLE}; height: 8px; border-radius: 4px;
    }}
    QScrollBar::handle:horizontal {{
        background: {SURFACE2}; border-radius: 4px; min-width: 20px;
    }}
    QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {{ width: 0; }}
    QStatusBar {{
        background-color: {MANTLE};
        color: {OVERLAY0};
        font-size: 11px;
        border-top: 1px solid {SURFACE0};
    }}
    QDialog {{
        background-color: {BASE};
        color: {TEXT};
    }}
    QGroupBox {{
        border: 1px solid {SURFACE0};
        border-radius: 4px;
        margin-top: 8px;
        padding-top: 4px;
        color: {SUBTEXT0};
        font-size: 10px;
    }}
    QGroupBox::title {{
        subcontrol-origin: margin;
        left: 8px;
    }}
    QCheckBox {{ color: {TEXT}; spacing: 6px; }}
    QCheckBox::indicator {{
        width: 14px; height: 14px;
        border: 1px solid {SURFACE2};
        border-radius: 3px;
        background: {MANTLE};
    }}
    QCheckBox::indicator:checked {{
        background: {BLUE};
        border-color: {BLUE};
    }}
    QTabWidget::pane {{
        border: 1px solid {SURFACE0};
        background: {BASE};
    }}
    QTabBar::tab {{
        background: {MANTLE};
        color: {SUBTEXT0};
        padding: 5px 12px;
        border-bottom: 2px solid transparent;
    }}
    QTabBar::tab:selected {{
        color: {TEXT};
        border-bottom: 2px solid {BLUE};
    }}
    QTabBar::tab:hover {{ color: {TEXT}; }}
"""
