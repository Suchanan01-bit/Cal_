import sys
from pathlib import Path
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QMainWindow, QFrame, QPushButton, QMenu
)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont

try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEBENGINE_AVAILABLE = True
except ImportError:
    WEBENGINE_AVAILABLE = False


class CalibrationSimulatorWidget(QWidget):
    """Widget that embeds the DC-RF Calibration Simulator web app via QWebEngineView"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        if WEBENGINE_AVAILABLE:
            self.web_view = QWebEngineView()
            # Resolve path: support both dev and PyInstaller frozen builds
            if getattr(sys, 'frozen', False):
                # PyInstaller frozen: use the directory where the .exe lives
                base_path = Path(sys.executable).resolve().parent
            else:
                # Development: relative to this file (CalSim -> parent -> root)
                base_path = Path(__file__).resolve().parent.parent
            
            dist_path = base_path / 'CalSim' / 'dc-rfsimulator' / 'dist' / 'index.html'
            if dist_path.exists():
                self.web_view.setUrl(QUrl.fromLocalFile(str(dist_path)))
            else:
                self.web_view.setHtml(
                    '<html><body style="display:flex;align-items:center;justify-content:center;height:100vh;'
                    'font-family:Segoe UI;color:#6b7280;"><h2>Simulator dist not found.<br>'
                    f'Expected at: {dist_path}</h2></body></html>'
                )
            layout.addWidget(self.web_view)
        else:
            placeholder = QLabel(
                "⚠️ PyQt6-WebEngine is not installed.\n\n"
                "Install it with:\n  pip install PyQt6-WebEngine"
            )
            placeholder.setFont(QFont("Segoe UI", 14))
            placeholder.setStyleSheet("color: #e67e22; padding: 60px;")
            placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
            layout.addWidget(placeholder)


class CalibrationSimulatorWindow(QMainWindow):
    """Standalone window for the DC-RF Calibration Simulator — no sidebar"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Calibration Simulator — Cal-Lab")
        self.setGeometry(50, 50, 1600, 950)
        self._setup_ui()

    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Header (same teal gradient as hub) ──────────────────────
        header = QFrame()
        header.setObjectName("cal_sim_header")
        header.setStyleSheet("""
            QFrame#cal_sim_header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4A90E2, stop:0.5 #50C9E8, stop:1 #7DD3C0);
                border: none;
            }
        """)
        header.setFixedHeight(70)

        h_layout = QHBoxLayout(header)
        h_layout.setContentsMargins(30, 15, 30, 15)

        # Title
        title = QLabel("⚙ Calibration Simulator")
        title.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title.setStyleSheet("color: white; letter-spacing: 2px; font-weight: 600;")
        h_layout.addWidget(title)

        h_layout.addStretch()

        # Advanced Settings Button
        self.adv_settings_btn = QPushButton("⚙ Advanced Settings")
        self.adv_settings_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.adv_settings_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.adv_settings_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(0, 0, 0, 0.2);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgba(0, 0, 0, 0.3);
            }
            QPushButton::menu-indicator {
                image: none;
            }
        """)
        
        # Menu for Advanced Settings
        adv_menu = QMenu(self.adv_settings_btn)
        adv_menu.setStyleSheet("""
            QMenu {
                background-color: #1e293b;
                color: white;
                border: 1px solid #475569;
                font-family: 'Segoe UI';
                font-size: 13px;
            }
            QMenu::item {
                padding: 8px 25px 8px 10px;
            }
            QMenu::item:selected {
                background-color: rgba(255, 255, 255, 0.1);
            }
            QMenu::indicator {
                width: 13px;
                height: 13px;
                margin-left: 5px;
            }
        """)

        # Add checkable actions
        self.act_global = adv_menu.addAction("Uncertainty Mode (Global)")
        self.act_global.setCheckable(True)
        self.act_global.triggered.connect(lambda: self._invoke_js("window.simulatorAPI && window.simulatorAPI.toggleUncertainty()"))

        self.act_loading = adv_menu.addAction("Loading Error")
        self.act_loading.setCheckable(True)
        self.act_loading.triggered.connect(lambda: self._invoke_js("window.simulatorAPI && window.simulatorAPI.toggleError('loadingError')"))

        self.act_res = adv_menu.addAction("Resolution Uncertainty")
        self.act_res.setCheckable(True)
        self.act_res.triggered.connect(lambda: self._invoke_js("window.simulatorAPI && window.simulatorAPI.toggleError('resolutionUncertainty')"))

        self.act_inst = adv_menu.addAction("Instrument Error")
        self.act_inst.setCheckable(True)
        self.act_inst.triggered.connect(lambda: self._invoke_js("window.simulatorAPI && window.simulatorAPI.toggleError('instrumentError')"))

        self.adv_settings_btn.setMenu(adv_menu)
        h_layout.addWidget(self.adv_settings_btn)

        # Clear Canvas Button
        clear_btn = QPushButton("🗑️ Clear Canvas")
        clear_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        clear_btn.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(220, 53, 69, 0.8);
                border: 1px solid rgba(255, 255, 255, 0.5);
                border-radius: 4px;
                padding: 6px 12px;
            }
            QPushButton:hover {
                background-color: rgba(220, 53, 69, 1.0);
            }
        """)
        clear_btn.clicked.connect(lambda: self._invoke_js("window.simulatorAPI && window.simulatorAPI.clearAll()"))
        h_layout.addWidget(clear_btn)

        h_layout.addSpacing(10)

        # CAL-LAB button — closes this window / goes back
        back_btn = QPushButton("CAL-LAB")
        back_btn.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        back_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        back_btn.setStyleSheet("""
            QPushButton {
                color: #4A90E2;
                background-color: white;
                border: 2px solid white;
                border-radius: 4px;
                padding: 6px 14px;
                letter-spacing: 1.5px;
            }
            QPushButton:hover {
                color: white;
                background-color: rgba(255, 255, 255, 0.30);
                border: 2px solid white;
            }
            QPushButton:pressed {
                background-color: rgba(255, 255, 255, 0.55);
                color: #1a73e8;
            }
        """)
        back_btn.clicked.connect(self.close)
        h_layout.addWidget(back_btn)

        root.addWidget(header)

        # ── Cal Sim Content ─────────────────────────────────────────
        self._sim_widget = CalibrationSimulatorWidget()
        root.addWidget(self._sim_widget, 1)

    def _invoke_js(self, script):
        if hasattr(self, '_sim_widget') and hasattr(self._sim_widget, 'web_view'):
            self._sim_widget.web_view.page().runJavaScript(script)
