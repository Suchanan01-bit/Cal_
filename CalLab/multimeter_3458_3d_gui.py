"""
HP 3458A Multimeter – 3D Instrument Panel GUI
Redesigned to mimic the physical front panel of the HP 3458A.
All measurement logic is identical to multimeter_3458_gui.py.
"""

import sys
import traceback
import csv
import os
import subprocess
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox,
    QButtonGroup, QProgressBar, QStatusBar,
    QMessageBox, QCheckBox, QScrollArea, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QLocale, QTimer
from PyQt6.QtGui import QFont, QColor, QPalette, QLinearGradient, QPainter, QBrush, QPen

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False




# ─────────────────────────────────────────────────────────────
#  Background measurement thread  (identical logic to original)
# ─────────────────────────────────────────────────────────────
class MeasurementThread(QThread):
    measurement_ready = pyqtSignal(float, int, str)
    measurement_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)

    def __init__(self, resource_name, num_measurements, measurement_type,
                 gate_time, auto_zero, range_val="AUTO", mode="Integration",
                 nplc=None, digits=8, offset_comp=False,
                 acband_enabled=False, acband_value=1,
                 lfilter=False, setacv="disable", sniffing=0):
        super().__init__()
        self.resource_name = resource_name
        self.num_measurements = num_measurements
        self.measurement_type = measurement_type
        self.gate_time = gate_time
        self.auto_zero = auto_zero
        self.range_val = range_val
        self.mode = mode
        self.nplc = nplc
        self.digits = digits
        self.offset_comp = offset_comp
        self.acband_enabled = acband_enabled
        self.acband_value = acband_value
        self.lfilter = lfilter
        self.setacv = setacv
        self.sniffing = sniffing
        self.is_running = True
        self.measurements = []

    def run(self):
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(self.resource_name)
            if self.mode == "NPLC":
                instrument.timeout = 30000 + int(self.nplc * 100)
            else:
                instrument.timeout = 30000 + int(self.gate_time * 1000)

            instrument.write("TARM HOLD")
            instrument.write("TRIG AUTO")
            time.sleep(0.5)
            instrument.write("RESET")
            time.sleep(1.5)
            instrument.write("END ALWAYS")

            func_map = {"DCV": "DCV", "ACV": "ACV", "DCI": "DCI",
                        "ACI": "ACI", "OHMS": "OHM", "OHMF": "OHMF", "FREQ": "FREQ"}
            instrument.write(func_map.get(self.measurement_type, "DCV"))
            time.sleep(0.1)

            if self.range_val == "AUTO":
                instrument.write("ARANGE ON")
            else:
                instrument.write(f"RANGE {self.range_val}")

            instrument.write(f"AZERO {1 if self.auto_zero else 0}")
            instrument.write(f"NDIG {int(self.digits)}")
            instrument.write(f"OCOMP {1 if self.offset_comp else 0}")
            if self.acband_enabled:
                instrument.write(f"ACBAND {self.acband_value}")
            instrument.write(f"LFILTER {1 if self.lfilter else 0}")
            if self.setacv == "sync":
                instrument.write("SETACV SYNC")
            else:
                instrument.write("SETACV ACAL")

            if self.mode == "NPLC":
                instrument.write(f"NPLC {self.nplc}")
                instrument.write("NRDGS 1")
                instrument.write("TRIG AUTO")
                instrument.write("TARM AUTO")
                time.sleep(0.5)
                for i in range(self.num_measurements):
                    if not self.is_running:
                        break
                    if self.sniffing > 0:
                        time.sleep(self.sniffing)
                    try:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        value_str = instrument.read()
                        try:
                            value = float(value_str.strip().split(',')[0])
                        except ValueError:
                            value = float(value_str.strip())
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        self.measurements.append((value, timestamp))
                    except Exception as e:
                        self.error_occurred.emit(str(e))
                        break
            else:
                instrument.write("NRDGS 1")
                instrument.write("TRIG AUTO")
                instrument.write("TARM AUTO")
                time.sleep(0.5)
                for i in range(self.num_measurements):
                    if not self.is_running:
                        break
                    time.sleep(self.gate_time)
                    try:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        value_str = instrument.read()
                        try:
                            value = float(value_str.strip().split(',')[0])
                        except ValueError:
                            value = float(value_str.strip())
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        self.measurements.append((value, timestamp))
                    except Exception as e:
                        self.error_occurred.emit(str(e))
                        break

            instrument.write("TARM HOLD")
            instrument.close()
            self.measurement_complete.emit(self.measurements)
        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self.is_running = False




# ─────────────────────────────────────────────────────────────
#  Custom 3D-style instrument button
# ─────────────────────────────────────────────────────────────
class InstrumentButton(QPushButton):
    """A button styled to look like a physical instrument button with 3D effect."""

    STYLES = {
        'func': {'bg': '#3a3a4a', 'top': '#5a5a6e', 'text': '#e0e0ff',
                 'active_bg': '#1a4a8a', 'active_top': '#2a6acc', 'active_text': '#ffffff'},
        'green': {'bg': '#1a4a1a', 'top': '#2a7a2a', 'text': '#88ff88',
                  'active_bg': '#0d7a0d', 'active_top': '#12bb12', 'active_text': '#ffffff'},
        'red':   {'bg': '#4a1a1a', 'top': '#7a2a2a', 'text': '#ff8888',
                  'active_bg': '#8a0d0d', 'active_top': '#cc1212', 'active_text': '#ffffff'},
        'orange': {'bg': '#4a2e00', 'top': '#7a4d00', 'text': '#ffcc66',
                   'active_bg': '#8a5500', 'active_top': '#cc8800', 'active_text': '#ffe0aa'},
        'yellow': {'bg': '#3a3000', 'top': '#6a5800', 'text': '#ffe050',
                   'active_bg': '#6a5800', 'active_top': '#aa9000', 'active_text': '#ffee80'},
        'blue':  {'bg': '#001a4a', 'top': '#002a7a', 'text': '#88aaff',
                  'active_bg': '#0d2e8a', 'active_top': '#1244cc', 'active_text': '#ffffff'},
        'gray':  {'bg': '#2a2a2a', 'top': '#444444', 'text': '#aaaaaa',
                  'active_bg': '#404040', 'active_top': '#606060', 'active_text': '#cccccc'},
    }

    def __init__(self, text, style='func', checkable=False, parent=None):
        super().__init__(text, parent)
        self._style_key = style
        self._is_active = False
        self.setCheckable(checkable)
        self._apply_style(False)
        if checkable:
            self.toggled.connect(self._apply_style)

    def _apply_style(self, active):
        self._is_active = active
        s = self.STYLES.get(self._style_key, self.STYLES['func'])
        if active:
            bg, top, text = s['active_bg'], s['active_top'], s['active_text']
            border_bottom = "border-bottom: 2px solid #000;"
            border_top = "border-top: 1px solid #ffffff33;"
        else:
            bg, top, text = s['bg'], s['top'], s['text']
            border_bottom = "border-bottom: 4px solid #000;"
            border_top = "border-top: 2px solid #ffffff44;"
        self.setStyleSheet(f"""
            QPushButton {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 {top}, stop:0.4 {bg}, stop:1 #111111);
                color: {text};
                border: 1px solid #111;
                border-radius: 5px;
                {border_top}
                {border_bottom}
                font-family: 'Segoe UI';
                font-size: 11px;
                font-weight: bold;
                padding: 6px 10px;
                min-height: 32px;
            }}
            QPushButton:hover {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #ffffff22, stop:1 #00000000);
                border-color: #888;
            }}
            QPushButton:pressed {{
                background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                    stop:0 #000000, stop:1 {bg});
                border-bottom: 1px solid #000;
                border-top: 3px solid #000;
            }}
            QPushButton:disabled {{
                background: #1a1a1a;
                color: #444;
                border: 1px solid #222;
            }}
        """)

    def set_active(self, active):
        if self.isCheckable():
            self.setChecked(active)
        else:
            self._apply_style(active)


# ─────────────────────────────────────────────────────────────
#  LED Indicator widget
# ─────────────────────────────────────────────────────────────
class LEDIndicator(QLabel):
    def __init__(self, color_on='#00ff44', color_off='#003311', size=12, parent=None):
        super().__init__(parent)
        self._color_on = color_on
        self._color_off = color_off
        self._size = size
        self._on = False
        self.setFixedSize(size, size)
        self._update_style()

    def _update_style(self):
        color = self._color_on if self._on else self._color_off
        glow = f"0 0 4px {self._color_on}" if self._on else "none"
        self.setStyleSheet(f"""
            QLabel {{
                background-color: {color};
                border-radius: {self._size // 2}px;
                border: 1px solid #001100;
            }}
        """)

    def set_on(self, on):
        self._on = on
        self._update_style()

    def is_on(self):
        return self._on


# ─────────────────────────────────────────────────────────────
#  Main 3D Instrument GUI class
# ─────────────────────────────────────────────────────────────
class HP3458MultimeterGUI3D(QMainWindow):
    """HP 3458A Multimeter – instrument-panel style GUI"""

    RANGE_MAP = {
        "DCV": [("Auto","V","AUTO"),("100 mV","V","0.1"),("1 V","V","1"),
                ("10 V","V","10"),("100 V","V","100"),("1000 V","V","1000")],
        "ACV": [("Auto","V","AUTO"),("10 mV","V","0.01"),("100 mV","V","0.1"),
                ("1 V","V","1"),("10 V","V","10"),("100 V","V","100"),("1000 V","V","1000")],
        "DCI": [("Auto","A","AUTO"),("100 nA","A","1e-7"),("1 µA","A","1e-6"),
                ("10 µA","A","1e-5"),("100 µA","A","1e-4"),("1 mA","A","1e-3"),
                ("10 mA","A","1e-2"),("100 mA","A","1e-1"),("1 A","A","1")],
        "ACI": [("Auto","A","AUTO"),("100 µA","A","1e-4"),("1 mA","A","1e-3"),
                ("10 mA","A","1e-2"),("100 mA","A","1e-1"),("1 A","A","1")],
        "OHMS": [("Auto","Ω","AUTO"),("10 Ω","Ω","10"),("100 Ω","Ω","100"),
                 ("1 kΩ","Ω","1e3"),("10 kΩ","Ω","1e4"),("100 kΩ","Ω","1e5"),
                 ("1 MΩ","Ω","1e6"),("10 MΩ","Ω","1e7"),("100 MΩ","Ω","1e8"),("1 GΩ","Ω","1e9")],
        "OHMF": [("Auto","Ω","AUTO"),("10 Ω","Ω","10"),("100 Ω","Ω","100"),
                 ("1 kΩ","Ω","1e3"),("10 kΩ","Ω","1e4"),("100 kΩ","Ω","1e5"),
                 ("1 MΩ","Ω","1e6"),("10 MΩ","Ω","1e7"),("100 MΩ","Ω","1e8"),("1 GΩ","Ω","1e9")],
        "FREQ": [("Auto","Hz","AUTO")],
    }

    FUNC_NAMES = ["DCV", "ACV", "DCI", "ACI", "OHMS", "OHMF", "FREQ"]

    def __init__(self):
        super().__init__()
        # Pre-initialize variables to prevent AttributeError if accessed early
        self.measurement_thread = None
        self.mode_combo = None
        self.range_combo = None
        self.auto_zero_check = None
        self.offset_comp_check = None
        
        self.all_measurements = []
        self.current_unit = "V"
        self.current_func = "DCV"
        self.measurement_mode = None
        self._func_btns = {}
        self._func_leds = {}
        
        try:
            self.init_ui()
        except Exception:
            traceback.print_exc()
            # Try to show message box if possible
            try:
                msg = traceback.format_exc()
                QMessageBox.critical(None, "Startup Error", f"Error during startup:\n{msg}")
            except:
                print("Could not show MessageBox")

    # ── UI Construction ───────────────────────────────────────

    # ── shared sub-panel style (cream/beige inset) ───────────
    PANEL_STYLE = """
        QFrame {
            background: qlineargradient(x1:0,y1:0,x2:0,y2:1,
                stop:0 #d8d0c0, stop:0.5 #ccc4b2, stop:1 #bab0a0);
            border: 1px solid #a09080;
            border-radius: 4px;
        }
    """

    # cream body colours
    BODY_BG   = "#c8c0b0"
    BODY_MID  = "#bfb8a8"
    BODY_DARK = "#a89888"

    def init_ui(self):
        self.setWindowTitle("HP 3458A  │  8.5-Digit Digital Multimeter")
        self.setMinimumSize(1300, 520)

        # Light beige window background
        self.setStyleSheet("""
            QMainWindow { background-color: #b0a898; }
            QWidget      { background-color: transparent; color: #222; font-family: 'Segoe UI'; }
            QToolTip     { background: #003; color: #0f0; border: 1px solid #0f0; }
        """)

        root = QWidget()
        root.setStyleSheet("background-color: #b0a898;")
        self.setCentralWidget(root)
        root_layout = QVBoxLayout(root)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        scroll.setStyleSheet(
            "QScrollArea { border: none; background: #b0a898; }"
            "QScrollBar:vertical { background:#a09080; width:10px; }"
            "QScrollBar::handle:vertical { background:#807060; border-radius:5px; }"
            "QScrollBar:horizontal { background:#a09080; height:10px; }"
            "QScrollBar::handle:horizontal { background:#807060; border-radius:5px; }")
        root_layout.addWidget(scroll)

        content = QWidget()
        content.setStyleSheet("background-color: #b0a898;")
        scroll.setWidget(content)
        main = QVBoxLayout(content)
        main.setContentsMargins(12, 10, 12, 10)
        main.setSpacing(8)

        # Dependencies: Build dependent widgets first
        settings_panel = self._build_settings_panel()
        action_btns = self._build_action_buttons()

        # ── VISA connection bar (top) ──────────────────────────
        main.addWidget(self._build_top_bar())

        # ── Instrument body outer bezel (cream/beige) ──────────
        bezel = QFrame()
        bezel.setStyleSheet("""
            QFrame {
                background: qlineargradient(x1:0,y1:0,x2:1,y2:1,
                    stop:0 #d8d2c4, stop:0.4 #ccc6b8, stop:1 #b8b0a0);
                border: 3px solid #706050;
                border-top: 3px solid #e0d8c8;
                border-left: 3px solid #d0c8b8;
                border-right: 3px solid #908070;
                border-bottom: 3px solid #908070;
                border-radius: 6px;
            }
        """)
        bezel_layout = QVBoxLayout(bezel)
        bezel_layout.setContentsMargins(10, 8, 10, 8)
        bezel_layout.setSpacing(0)

        # ── Top section: HP logo area + VFD display (full width) ─
        bezel_layout.addWidget(self._build_display_section())

        # ── Bottom section: all controls in one horizontal row ─
        bottom_row = QHBoxLayout()
        bottom_row.setSpacing(6)
        bottom_row.setContentsMargins(0, 6, 0, 0)

        # Left: FUNCTION/RANGE + Power/Control buttons
        bottom_row.addWidget(self._build_function_row(), 3)

        # Middle: MENU column
        bottom_row.addWidget(self._build_menu_section(), 2)

        # Numeric/USER keypad
        bottom_row.addWidget(self._build_numeric_keypad(), 2)

        # Right: extra menu column + Terminals
        bottom_row.addWidget(self._build_terminals_section(), 1)

        bezel_layout.addLayout(bottom_row)
        main.addWidget(bezel)

        # ── Settings panel (below bezel) ──────────────────────
        main.addWidget(settings_panel)
        main.addWidget(action_btns)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet(
            "QStatusBar { background:#2a240e; color:#00cc66; "
            "font-family:'Courier New'; font-size:11px; border-top:1px solid #555; padding:4px; }")
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("● READY  —  HP 3458A  8.5-Digit Multimeter")

        self.check_dependencies()
        self._on_func_selected("DCV") # Call this last to update UI state

    # ── TOP BAR (VISA) ───────────────────────────────────────
    def _build_top_bar(self):
        # Separate bar above the instrument for connection controls
        frame = QFrame()
        frame.setStyleSheet("background: transparent; border: none;")
        h = QHBoxLayout(frame)
        h.setContentsMargins(4, 0, 4, 0)
        
        lbl = QLabel("VISA Resource:")
        lbl.setFont(QFont("Segoe UI", 9))
        h.addWidget(lbl)

        self.resource_combo = QComboBox()
        self.resource_combo.setEditable(True)
        self.resource_combo.setMinimumWidth(250)
        self.resource_combo.setStyleSheet("""
            QComboBox { background:#fff; color:#333; border:1px solid #aaa; border-radius:3px; padding:2px; }
        """)
        h.addWidget(self.resource_combo)

        btn_refresh = QPushButton("Refresh")
        btn_refresh.setStyleSheet("padding:3px 8px;")
        btn_refresh.clicked.connect(self.refresh_resources)
        h.addWidget(btn_refresh)

        btn_test = QPushButton("Connect")
        btn_test.setStyleSheet("background:#dceadd; border:1px solid #abc; padding:3px 8px;")
        btn_test.clicked.connect(self.test_connection)
        h.addWidget(btn_test)

        h.addStretch()
        return frame

    # ── DISPLAY SECTION (Top Half) ───────────────────────────
    def _build_display_section(self):
        # Container for the top dark window area
        # The physical unit has a long dark acrylic window covering the display
        
        container = QFrame()
        container.setStyleSheet(f"background: {self.BODY_BG}; border: none;")
        layout = QHBoxLayout(container)
        layout.setContentsMargins(15, 10, 15, 5)
        layout.setSpacing(20)

        # 1. Left branding area (on the beige panel, left of the display window)
        # Actually physically, the logo is printed ON the panel or the window bezel.
        # Let's put it inside a "window bezel" wrapper.
        
        # Black bezel wrapper for the VFD
        window_bezel = QFrame()
        window_bezel.setStyleSheet("""
            QFrame {
                background: #101010;
                border-radius: 4px;
                border: 2px solid #555;
                border-bottom: 2px solid #777; /* highlight */
                border-top: 2px solid #333;    /* shadow */
            }
        """)
        wb_layout = QHBoxLayout(window_bezel)
        wb_layout.setContentsMargins(15, 8, 15, 8)
        wb_layout.setSpacing(15)

        # HP Logo & Text
        brand_col = QVBoxLayout()
        brand_col.setSpacing(0)
        
        logo = QLabel("hp")
        logo.setFont(QFont("Times New Roman", 18, QFont.Weight.Bold, True)) # Italic
        logo.setStyleSheet("color: #ccc; background: transparent; margin-bottom: -4px;")
        logo.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        brand_txt = QLabel("HEWLETT\nPACKARD")
        brand_txt.setFont(QFont("Arial", 5, QFont.Weight.Bold))
        brand_txt.setStyleSheet("color: #ccc; background: transparent;")
        brand_txt.setAlignment(Qt.AlignmentFlag.AlignCenter)

        model_txt = QLabel("3458A\nMULTIMETER")
        model_txt.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        model_txt.setStyleSheet("color: #ccc; background: transparent; margin-top: 4px;")
        
        brand_col.addWidget(logo)
        brand_col.addWidget(brand_txt)
        brand_col.addWidget(model_txt)
        brand_col.addStretch()
        
        wb_layout.addLayout(brand_col)

        # VFD Display Area
        # Bright green segments on dark background
        
        self.display_label = QLabel("   -0.0000052")
        self.display_label.setFont(QFont("Consolas", 36)) # Monospaced like VFD
        self.display_label.setStyleSheet("color: #00ffaa; background: transparent;")
        self.display_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        
        # Unit and annunciators
        ann_col = QVBoxLayout()
        ann_col.setSpacing(2)
        
        self.unit_label = QLabel("V DC")
        self.unit_label.setFont(QFont("Arial", 14, QFont.Weight.Bold))
        self.unit_label.setStyleSheet("color: #00dd99; background: transparent;")
        
        # "NPL" or other status indicators on the VFD
        self.status_indicators_lbl = QLabel("NPL  AZ  SMPL") 
        self.status_indicators_lbl.setFont(QFont("Arial", 7))
        self.status_indicators_lbl.setStyleSheet("color: #007744; background: transparent;") # Dimmer green
        
        ann_col.addStretch()
        ann_col.addWidget(self.unit_label)
        ann_col.addWidget(self.status_indicators_lbl)
        ann_col.addStretch()

        wb_layout.addStretch()
        wb_layout.addWidget(self.display_label)
        wb_layout.addLayout(ann_col)
        wb_layout.addSpacing(20)

        layout.addWidget(window_bezel)
        return container


    # ── FUNCTION / RANGE (Bottom Left) ───────────────────────
    def _build_function_row(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(10, 5, 5, 5)
        layout.setSpacing(5)

        # Power switch
        pwr_row = QHBoxLayout()
        pwr_btn = QPushButton("Power")
        pwr_btn.setCheckable(True)
        pwr_btn.setChecked(True)
        pwr_btn.setFixedSize(50, 25)
        pwr_btn.setStyleSheet("""
            QPushButton { background: #e0e0e0; border: 1px solid #999; border-radius: 2px; color: #333; font-size: 9px; }
            QPushButton:checked { background: #3da03d; color: #fff; border: 1px solid #286028; } /* Green when ON */
        """)
        pwr_row.addWidget(pwr_btn)
        pwr_row.addStretch()
        layout.addLayout(pwr_row)

        # Main Function Group Box lookalike
        # Outline with title "FUNCTION / RANGE"
        
        # We'll just group buttons visually closely
        grid = QGridLayout()
        grid.setSpacing(6)

        # Labels above keys: (ACDCV) (OHM) (ACDCI) (PER) are blue labels above keys
        # We can implement these as labels in the grid or part of the button custom widget
        # For simplicity, I'll pass blue text to the button creator to draw it.

        # Row 1
        # [DCV] [ACV] [OHM] [DCI] [ACI] [FREQ]
        # Blue: (ACDCV) (OHM) (ACDCI) (PER) ?? Mapping from photo
        
        # Mapping based on 3458A photo:
        # Key: DCV, Blue: (ACDCV)
        # Key: ACV, Blue: (ACDCV) -> wait, maybe auto?
        # Let's just use the main labels for functionality and blue for decoration
        
        self._func_btns = {}
        self._func_leds = {} # Initialize empty dict to prevent AttributeError
        self._func_btn_group = QButtonGroup(self)
        self._func_btn_group.setExclusive(True)

        funcs = [
            ("DCV", "DCV", "Auto"),
            ("ACV", "ACV", "Range"),
            ("OHMS", "OHM", "Hold"),
            ("DCI", "DCI", "Test"),
            ("ACI", "ACI", "Reset"),
            ("FREQ", "FREQ", "Addr"),
        ]

        # In physical unit:
        # Top Row: DCV, ACV, OHM, DCI, ACI, FREQ
        # Bot Row: Auto, Range, Hold, Test, Reset, Address (blue: Local)
        # Also shifted blue text above top row keys?
        # Actually, let's just make the Functional Keys.

        # ROW 1: Measurement Functions
        col = 0
        for mode, text, blue_txt in funcs:
            btn = self._create_btn(text, blue_text=blue_txt, width=50, height=35)
            btn.setCheckable(True)
            self._func_btn_group.addButton(btn)
            self._func_btns[mode] = btn
            btn.clicked.connect(lambda ch, m=mode: self._on_func_selected(m) if ch else None)
            grid.addWidget(btn, 0, col)
            col += 1

        # ROW 2: Range / Control
        # [Auto] [Range] [Hold] [Test] [Reset] [Local]
        # Functional implementation: Auto/Hold/Reset are standard.
        # Range is scroll? In 3458A, Range is up/down arrows.
        # Wait, the physical photo shows "Auto" button, "Range" button (with arrows?), "Hold", etc.
        # Actually "Range" implies manual ranging.
        
        controls = [
            ("AUTO_RNG", "Auto", "Arng"),
            ("RANGE_UP", "Range ▲", ""), # customized symbol
            ("RANGE_DN", "Range ▼", ""),
            ("HOLD", "Hold", ""),
            ("TEST", "Test", ""),
            ("RESET", "Reset", ""),
            ("LOCAL", "Local", "")
        ]
        
        # The photo shows: 
        # [Auto] [Range (Up/Down combined? No, separate)] -> Actually standard 3458A has [Auto] [Range Up] [Range Down]?
        # Let's look at the photo again... "Auto", "Range", "Hold"...
        # It seems "Range" is one button? Or maybe toggle?
        # Standard 3458A has: [Auto], [Def Key]?, arrows are separate?
        # The arrow keys are typically near the display or separate group.
        # Let's stick to standard buttons for row 2.
        
        # Row 2 Implementation
        btn_auto = self._create_btn("Auto", "Auth", width=50, height=35)
        btn_auto.clicked.connect(lambda: self.range_combo.setCurrentText("Auto"))
        grid.addWidget(btn_auto, 1, 0)
        
        # Range Up/Down
        # We'll use two buttons for Range since physical might be scroll
        btn_rup = self._create_btn("▲", "Rng+", width=50, height=35) # Range Up
        btn_rdn = self._create_btn("▼", "Rng-", width=50, height=35) # Range Down
        btn_rup.clicked.connect(self._range_up)
        btn_rdn.clicked.connect(self._range_down)
        grid.addWidget(btn_rup, 1, 1)
        grid.addWidget(btn_rdn, 1, 2)
        
        btn_hold = self._create_btn("Hold", "", width=50, height=35)
        # toggle hold
        grid.addWidget(btn_hold, 1, 3)

        btn_reset = self._create_btn("Reset", "", width=50, height=35)
        btn_reset.clicked.connect(self.clear_results) # partially reset
        grid.addWidget(btn_reset, 1, 4)

        btn_local = self._create_btn("Local", "Addr", width=50, height=35, blue_btn=True) # Blue button?
        grid.addWidget(btn_local, 1, 5)

        layout.addLayout(grid)
        
        # Menu scroll arrows (Up/Down) separate below
        # Display/Window arrows (Left/Right)
        
        nav_row = QHBoxLayout()
        arrow_up = self._create_btn("▲", "Menu", width=40, height=25, flat=True)
        arrow_dn = self._create_btn("▼", "Scroll", width=40, height=25, flat=True)
        arrow_l  = self._create_btn("◄", "Disp", width=40, height=25, flat=True)
        arrow_r  = self._create_btn("►", "Wind", width=40, height=25, flat=True)
        
        nav_row.addWidget(QLabel("MENU"))
        nav_row.addWidget(arrow_up)
        nav_row.addWidget(arrow_dn)
        nav_row.addSpacing(10)
        nav_row.addWidget(QLabel("DISP"))
        nav_row.addWidget(arrow_l)
        nav_row.addWidget(arrow_r)
        
        layout.addLayout(nav_row)
        layout.addStretch()

        return frame

    # ── MENU SECTION (Middle) ──────────────────────────────
    def _build_menu_section(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)
        
        lbl = QLabel("MENU")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        layout.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(6)
        
        # 2 Columns of 4 buttons
        # Col 1: Auto Cal, Auto Zero, Trig, Recall State
        # Col 2: NPLC, Offset Comp, N Rdgs/Trig, Store State
        
        # Row 0
        grid.addWidget(self._create_btn("Auto\nCal", "C", width=50, height=35), 0, 0)
        
        btn_nplc = self._create_btn("NPLC", "E", width=50, height=35)
        btn_nplc.clicked.connect(lambda: self.mode_combo.setCurrentText("NPLC"))
        grid.addWidget(btn_nplc, 0, 1)

        # Row 1
        btn_azero = self._create_btn("Auto\nZero", "L", width=50, height=35)
        btn_azero.clicked.connect(lambda: self.auto_zero_check.toggle())
        grid.addWidget(btn_azero, 1, 0)
        
        btn_ocomp = self._create_btn("Offset\nComp", "N", width=50, height=35)
        btn_ocomp.clicked.connect(lambda: self.offset_comp_check.toggle())
        grid.addWidget(btn_ocomp, 1, 1)

        # Row 2
        btn_trig = self._create_btn("Trig", "R", width=50, height=35)
        btn_trig.clicked.connect(self.start_measurement) # Manual Trigger
        grid.addWidget(btn_trig, 2, 0)
        
        btn_nrdgs = self._create_btn("N Rdgs/\nTrig", "S", width=50, height=35)
        grid.addWidget(btn_nrdgs, 2, 1)

        # Row 3
        grid.addWidget(self._create_btn("Recall\nState", "T", width=50, height=35), 3, 0)
        grid.addWidget(self._create_btn("Store\nState", "?", width=50, height=35), 3, 1)

        layout.addLayout(grid)
        layout.addStretch()
        return frame

    # ── NUMERIC / USER KEYPAD (Right) ──────────────────────
    def _build_numeric_keypad(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 5, 5, 5)

        lbl = QLabel("NUMERIC / USER")
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setFont(QFont("Arial", 8, QFont.Weight.Bold))
        layout.addWidget(lbl)

        grid = QGridLayout()
        grid.setSpacing(6)
        
        # 4x4 Grid (mostly)
        # 7, 8, 9, E
        # 4, 5, 6, Error
        # 1, 2, 3, Clear
        # 0, ., ,, Enter
        
        keys = [
            ("7", "f1"), ("8", "f2"), ("9", "f3"), ("E", "Menu"),
            ("4", "f4"), ("5", "f5"), ("6", "f6"), ("Error", "-"),
            ("1", "I"),  ("2", "J"),  ("3", "K"),  ("Clear", "Back"),
            ("0", "O"),  (".", ","),  (",", "Sep"), ("Enter", "Ent")
        ]

        row, col = 0, 0
        for text, blue in keys:
            # Special coloring for Enter?
            is_enter = (text == "Enter")
            is_gray = text in ["E", "Error", "Clear", "Enter"]
            
            btn = self._create_btn(text, blue, width=40, height=35, 
                                   bg_color="#888" if is_gray else "#ddd")
            
            grid.addWidget(btn, row, col)
            col += 1
            if col > 3:
                col = 0
                row += 1
        
        layout.addLayout(grid)
        layout.addStretch()
        return frame

    # ── TERMINALS SECTION (Far Right) ──────────────────────
    def _build_terminals_section(self):
        frame = QFrame()
        frame.setStyleSheet("background: transparent;")
        layout = QVBoxLayout(frame)
        layout.setContentsMargins(5, 15, 10, 5)
        layout.setSpacing(10)

        # Labels
        layout.addWidget(QLabel("Ω Sense\n(4 Wire)"))
        
        # Terminals (Circles with color)
        # Hi, Lo
        
        def terminal(label, color="#d00"):
            v = QVBoxLayout()
            v.setSpacing(2)
            lbl = QLabel(label)
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            # The terminal circle
            term_btn = QPushButton()
            term_btn.setFixedSize(24, 24)
            term_btn.setStyleSheet(f"""
                QPushButton {{
                    background: {color};
                    border: 2px solid #333;
                    border-radius: 12px;
                    margin: 2px;
                }}
            """)
            v.addWidget(lbl)
            v.addWidget(term_btn)
            v.setAlignment(Qt.AlignmentFlag.AlignCenter)
            return v
        
        # Grid of terminals
        # Top: Hi (Input), Hi (Sense)
        # Bot: Lo (Input), Lo (Sense)
        # Guard
        
        term_grid = QGridLayout()
        term_grid.addLayout(terminal("HI", "#d00"), 0, 1) # Input
        term_grid.addLayout(terminal("HI", "#d00"), 0, 0) # Sense
        
        term_grid.addLayout(terminal("LO", "#222"), 1, 1) # Input
        term_grid.addLayout(terminal("LO", "#222"), 1, 0) # Sense
        
        term_grid.addLayout(terminal("Guard", "#d90"), 2, 0) # Guard (Orange?) No, usually white/gold
        term_grid.addLayout(terminal("Amps", "#d00"), 2, 1) # Amps/Fuse? 3458A has specific layout
        
        layout.addLayout(term_grid)
        
        # Terminals label
        lbl_term = QLabel("Terminals")
        lbl_term.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(lbl_term)
        
        # Front/Rear switch
        btn_fr = QPushButton("Front/Rear")
        btn_fr.setFixedSize(60, 20)
        layout.addWidget(btn_fr)
        
        layout.addStretch()
        return frame


    # ── Button Factory Helper ──────────────────────────────
    def _create_btn(self, text, blue_text="", width=50, height=40, bg_color="#e6e0d4", blue_btn=False, flat=False):
        """
        Creates a button that looks like the HP keys.
        - bg_color: main face color (beige-gray)
        - blue_text: Shift function text (printed above or on key)
        - blue_btn: If the key itself is the blue shift key
        """
        btn = QPushButton()
        btn.setFixedSize(width, height)
        
        # Text layout logic
        # If blue_text is present, we might want to use a complex stylesheet or just multiline
        # But commonly physical keys have label ON them.
        # Blue text is usually ABOVE the key on the panel.
        # For this GUI, fitting it on the button is easier for layout.
        
        label = text
        if blue_text:
            # use smaller blue text on top line? or just tooltop?
            btn.setToolTip(f"Shift: {blue_text}")
        
        btn.setText(label)
        
        if blue_btn:
             # Blue shift button
             base = "#3366cc"
             border = "#224488"
             txt_col = "white"
        elif flat:
             # Arrow keys etc
             base = "#d0c8b8"
             border = "none"
             txt_col = "#333"
        else:
             # Standard beige key
             base = bg_color
             border = "#998877" # darker beige border
             txt_col = "#222"

        if flat:
            btn.setStyleSheet(f"""
                QPushButton {{
                    background: {base};
                    border: 1px solid {border};
                    border-radius: 4px;
                    color: {txt_col};
                    font-weight: bold;
                }}
                QPushButton:pressed {{ background: #999; }}
            """)
        else:
             btn.setStyleSheet(f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                        stop:0 {base}, stop:1 #bbb);
                    border: 1px solid {border};
                    border-bottom: 2px solid {border};
                    border-radius: 4px;
                    color: {txt_col};
                    font-family: 'Segoe UI';
                    font-size: 10px;
                    font-weight: bold;
                }}
                QPushButton:pressed {{
                    background: #999;
                    border-top: 2px solid {border};
                    border-bottom: 1px solid {border};
                }}
                QPushButton:checked {{
                    background: #ddd;
                    border: 1px inset #555;
                }}
            """)
        return btn

    # ── SETTINGS PANEL ───────────────────────────────────────
    def _build_settings_panel(self):
        frame = QFrame()
        frame.setStyleSheet(self.PANEL_STYLE)
        grid = QGridLayout(frame)
        grid.setContentsMargins(12, 10, 12, 10)
        grid.setHorizontalSpacing(14)
        grid.setVerticalSpacing(8)

        # ── Initialize Indicators Early ─────────────────────────
        # logic compatibility
        indicators = [
            ("AUTO RNG", "#00ff88"), ("AUTO ZERO", "#00ff88"),
            ("4W OHMS",  "#ffaa00"), ("AC BAND",   "#ffaa00"),
            ("L FILTER", "#aaaaff"), ("OFFSET COMP","#aaaaff"),
            ("MEAS RDY", "#00ff22"),
        ]
        self._indicator_leds = {}
        
        # We'll display them at the bottom
        status_row = QHBoxLayout()
        status_row.setContentsMargins(0, 10, 0, 0)
        led_layout = QHBoxLayout()
        led_layout.addWidget(QLabel("Status:"))

        for name, color in indicators:
            led = LEDIndicator(color_on=color, color_off="#333", size=8)
            lbl_ind = QLabel(name)
            lbl_ind.setStyleSheet("font-size: 9px; color: #555;")
            led_layout.addWidget(led)
            led_layout.addWidget(lbl_ind)
            led_layout.addSpacing(5)
            self._indicator_leds[name] = led
        
        led_layout.addStretch()
        
        # Progress Bar & Sample Count
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setFixedWidth(100)
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 1px solid #999; border-radius: 3px; background: #eee; height: 10px; }
            QProgressBar::chunk { background: #00cc66; }
        """)
        
        self.sample_count_lbl = QLabel("0 / 0")
        self.sample_count_lbl.setStyleSheet("font-size: 10px; color: #555;")
        
        status_row.addLayout(led_layout)
        status_row.addWidget(self.progress_bar)
        status_row.addWidget(self.sample_count_lbl)
        
        # ── Settings Controls ───────────────────────────────────

        def lbl(text):
            l = QLabel(text)
            l.setFont(QFont("Courier New", 9))
            l.setStyleSheet("color:#556; background:transparent;")
            return l

        # Row 0: Mode, NPLC, Interval, # Measurements
        grid.addWidget(lbl("SAMPLING MODE"), 0, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["-- Select Mode --", "Integration", "NPLC"])
        self.mode_combo.setStyleSheet(self._combo_style())
        self.mode_combo.setFixedWidth(140)
        self.mode_combo.currentTextChanged.connect(self._on_mode_changed)
        grid.addWidget(self.mode_combo, 0, 1)

        # RANGE (Hidden/Settings)
        grid.addWidget(lbl("RANGE"), 0, 8)
        self.range_combo = QComboBox()
        self.range_combo.setMinimumWidth(80)
        self.range_combo.setStyleSheet(self._combo_style())
        grid.addWidget(self.range_combo, 0, 9)

        self.nplc_lbl = lbl("NPLC")
        grid.addWidget(self.nplc_lbl, 0, 2)

        self.nplc_spin = QDoubleSpinBox()
        self.nplc_spin.setRange(0.02, 1000)
        self.nplc_spin.setValue(100)
        self.nplc_spin.setDecimals(2)
        self.nplc_spin.setFixedWidth(100)
        self.nplc_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.nplc_spin.setStyleSheet(self._spinbox_style())
        grid.addWidget(self.nplc_spin, 0, 3)

        self.integ_lbl = lbl("INTERVAL")
        grid.addWidget(self.integ_lbl, 0, 4)

        integ_h = QHBoxLayout()
        integ_h.setSpacing(4)
        self.gate_time_spin = QDoubleSpinBox()
        self.gate_time_spin.setRange(0.001, 100000)
        self.gate_time_spin.setValue(1.0)
        self.gate_time_spin.setDecimals(3)
        self.gate_time_spin.setFixedWidth(90)
        self.gate_time_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.gate_time_spin.setStyleSheet(self._spinbox_style())
        integ_h.addWidget(self.gate_time_spin)
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.addItems(["seconds", "minutes", "hours"])
        self.time_unit_combo.setFixedWidth(80)
        self.time_unit_combo.setStyleSheet(self._combo_style())
        integ_h.addWidget(self.time_unit_combo)
        grid.addLayout(integ_h, 0, 5)

        grid.addWidget(lbl("# MEAS"), 0, 6)
        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setRange(1, 1000000)
        self.num_measurements_spin.setValue(10)
        self.num_measurements_spin.setFixedWidth(90)
        self.num_measurements_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.num_measurements_spin.setStyleSheet(self._spinbox_style())
        grid.addWidget(self.num_measurements_spin, 0, 7)

        # Row 1: Checkboxes section
        grid.addWidget(lbl("OPTIONS"), 1, 0)

        self.auto_zero_check = QCheckBox("AUTO ZERO")
        self.auto_zero_check.setChecked(True)
        self.auto_zero_check.setStyleSheet(self._checkbox_style())
        grid.addWidget(self.auto_zero_check, 1, 1)

        self.offset_comp_check = QCheckBox("OFFSET COMP")
        self.offset_comp_check.setStyleSheet(self._checkbox_style())
        self.offset_comp_check.toggled.connect(lambda v: self._indicator_leds["OFFSET COMP"].set_on(v))
        grid.addWidget(self.offset_comp_check, 1, 2)

        self.lfilter_check = QCheckBox("L FILTER")
        self.lfilter_check.setStyleSheet(self._checkbox_style())
        self.lfilter_check.toggled.connect(lambda v: self._indicator_leds["L FILTER"].set_on(v))
        grid.addWidget(self.lfilter_check, 1, 3)

        # ACBand
        self.acband_enable_check = QCheckBox("AC BAND →")
        self.acband_enable_check.setStyleSheet(self._checkbox_style())
        self.acband_enable_check.toggled.connect(self._toggle_acband)
        self.acband_enable_check.toggled.connect(lambda v: self._indicator_leds["AC BAND"].set_on(v))
        grid.addWidget(self.acband_enable_check, 1, 4)

        self.acband_spin = QSpinBox()
        self.acband_spin.setRange(0, 100000)
        self.acband_spin.setValue(0)
        self.acband_spin.setSpecialValueText("OFF")
        self.acband_spin.setSuffix(" Hz")
        self.acband_spin.setFixedWidth(90)
        self.acband_spin.setEnabled(False)
        self.acband_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.acband_spin.setStyleSheet(self._spinbox_style())
        grid.addWidget(self.acband_spin, 1, 5)

        # SetACV
        grid.addWidget(lbl("SET ACV"), 1, 6)
        self.setacv_combo = QComboBox()
        self.setacv_combo.addItems(["disable", "sync"])
        self.setacv_combo.setFixedWidth(80)
        self.setacv_combo.setStyleSheet(self._combo_style())
        grid.addWidget(self.setacv_combo, 1, 7)

        # Row 2: Sniffing
        self.sniffing_enable_check = QCheckBox("SNIFFING DELAY →")
        self.sniffing_enable_check.setStyleSheet(self._checkbox_style())
        self.sniffing_enable_check.toggled.connect(self._toggle_sniffing)
        grid.addWidget(self.sniffing_enable_check, 2, 0, 1, 2)

        self.sniffing_spin = QDoubleSpinBox()
        self.sniffing_spin.setRange(0, 99999)
        self.sniffing_spin.setValue(0)
        self.sniffing_spin.setDecimals(2)
        self.sniffing_spin.setSpecialValueText("OFF")
        self.sniffing_spin.setFixedWidth(90)
        self.sniffing_spin.setEnabled(False)
        self.sniffing_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.sniffing_spin.setStyleSheet(self._spinbox_style())
        grid.addWidget(self.sniffing_spin, 2, 2)

        self.sniffing_unit_combo = QComboBox()
        self.sniffing_unit_combo.addItems(["seconds", "minutes", "hours"])
        self.sniffing_unit_combo.setEnabled(False)
        self.sniffing_unit_combo.setFixedWidth(80)
        self.sniffing_unit_combo.setStyleSheet(self._combo_style())
        grid.addWidget(self.sniffing_unit_combo, 2, 3)

        # Init (call after widgets created)
        self._on_mode_changed("-- Select Mode --")
        
        # Add the status row created at start
        grid.addLayout(status_row, 3, 0, 1, 8) 

        return frame

    # ── ACTION BUTTONS ────────────────────────────────────────
    def _build_action_buttons(self):
        frame = QFrame()
        frame.setStyleSheet(self.PANEL_STYLE)
        h = QHBoxLayout(frame)
        h.setContentsMargins(12, 8, 12, 8)
        h.setSpacing(10)

        self.start_btn = InstrumentButton("▶  START", 'green')
        self.start_btn.setMinimumHeight(44)
        self.start_btn.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        self.start_btn.clicked.connect(self.start_measurement)
        h.addWidget(self.start_btn, 2)

        self.stop_btn = InstrumentButton("■  STOP", 'red')
        self.stop_btn.setMinimumHeight(44)
        self.stop_btn.setFont(QFont("Courier New", 12, QFont.Weight.Bold))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        h.addWidget(self.stop_btn, 1)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.VLine)
        sep.setStyleSheet("color:#333;")
        h.addWidget(sep)

        self.math_null_btn = InstrumentButton("MATH NULL\n(Zero Func)", 'blue')
        self.math_null_btn.setMinimumHeight(44)
        self.math_null_btn.clicked.connect(self.execute_math_null)
        h.addWidget(self.math_null_btn, 1)

        self.zero_btn = InstrumentButton("AZERO ONCE\n(Zero Rng)", 'orange')
        self.zero_btn.setMinimumHeight(44)
        self.zero_btn.clicked.connect(self.execute_zero)
        h.addWidget(self.zero_btn, 1)

        sep2 = QFrame()
        sep2.setFrameShape(QFrame.Shape.VLine)
        sep2.setStyleSheet("color:#333;")
        h.addWidget(sep2)

        clear_btn = InstrumentButton("CLR\nRESULTS", 'gray')
        clear_btn.setMinimumHeight(44)
        clear_btn.clicked.connect(self.clear_results)
        h.addWidget(clear_btn, 1)

        save_btn = InstrumentButton("SAVE &\nCSV", 'blue')
        save_btn.setMinimumHeight(44)
        save_btn.clicked.connect(self.save_and_open_csv)
        h.addWidget(save_btn, 1)

        return frame


    # ── Stylesheet helpers ────────────────────────────────────
    def _combo_style(self):
        return """
            QComboBox { background:#0a0a0a; color:#00cc66; border:1px solid #334;
                border-radius:4px; padding:4px 8px;
                font-family:'Courier New'; font-size:11px; }
            QComboBox::drop-down { border:none; width:16px; }
            QComboBox::down-arrow { border-left:4px solid transparent;
                border-right:4px solid transparent; border-top:5px solid #00cc66; }
            QComboBox QAbstractItemView { background:#111; color:#0d0; }
            QComboBox:disabled { color:#334; border-color:#222; }
        """

    def _spinbox_style(self):
        return """
            QSpinBox, QDoubleSpinBox { background:#0a0a0a; color:#00cc66;
                border:1px solid #334; border-radius:4px; padding:4px 6px;
                font-family:'Courier New'; font-size:11px; }
            QSpinBox::up-button, QDoubleSpinBox::up-button { background:#111; width:16px; border:none; }
            QSpinBox::down-button, QDoubleSpinBox::down-button { background:#111; width:16px; border:none; }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                border-left:4px solid transparent; border-right:4px solid transparent;
                border-bottom:5px solid #00cc66; }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                border-left:4px solid transparent; border-right:4px solid transparent;
                border-top:5px solid #00cc66; }
            QSpinBox:disabled, QDoubleSpinBox:disabled { color:#334; border-color:#222; }
        """

    def _checkbox_style(self):
        return """
            QCheckBox { color:#889; font-family:'Courier New'; font-size:10px;
                spacing:6px; background:transparent; }
            QCheckBox::indicator { width:14px; height:14px; border:1px solid #445;
                border-radius:3px; background:#050505; }
            QCheckBox::indicator:checked { background:#00aa44; border-color:#00ff88; }
            QCheckBox::indicator:hover { border-color:#00ff88; }
        """

    # ── Event handlers / Logic ────────────────────────────────

    def _on_func_selected(self, key):
        self.current_func = key
        # Handle func leds if they exist
        if hasattr(self, '_func_leds'):
            for k, led in self._func_leds.items():
                if led: led.set_on(k == key)
        
        # Ensure _indicator_leds exists before accessing
        if hasattr(self, '_indicator_leds') and "4W OHMS" in self._indicator_leds:
            self._indicator_leds["4W OHMS"].set_on(key == "OHMF")
            
        if key in self._func_btns and not self._func_btns[key].isChecked():
            self._func_btns[key].setChecked(True)
        self.range_combo.clear()
        for name, unit, cmd in self.RANGE_MAP.get(key, [("Auto", "V", "AUTO")]):
            self.range_combo.addItem(name, cmd)
        unit_map = {"DCV": "V DC", "ACV": "V AC", "DCI": "A DC",
                    "ACI": "A AC", "OHMS": "Ω 2W", "OHMF": "Ω 4W", "FREQ": "Hz"}
        self.current_unit = {"DCV": "V", "ACV": "V", "DCI": "A",
                             "ACI": "A", "OHMS": "Ω", "OHMF": "Ω", "FREQ": "Hz"}.get(key, "V")
        self.unit_label.setText(unit_map.get(key, "V"))

    def _on_mode_changed(self, mode):
        self.measurement_mode = mode if mode not in ("-- Select Mode --", "") else None
        nplc_vis = (mode == "NPLC")
        integ_vis = (mode == "Integration")
        sniff_vis = (mode == "NPLC")

        self.nplc_lbl.setVisible(nplc_vis)
        self.nplc_spin.setVisible(nplc_vis)
        self.nplc_spin.setEnabled(nplc_vis)
        self.integ_lbl.setVisible(integ_vis)
        self.gate_time_spin.setVisible(integ_vis)
        self.time_unit_combo.setVisible(integ_vis)
        self.sniffing_enable_check.setVisible(sniff_vis)
        self.sniffing_spin.setVisible(sniff_vis)
        self.sniffing_unit_combo.setVisible(sniff_vis)
        self._indicator_leds["AUTO ZERO"].set_on(integ_vis or nplc_vis)

    def _toggle_acband(self, checked):
        self.acband_spin.setEnabled(checked)
        if checked and self.acband_spin.value() == 0:
            self.acband_spin.setValue(10)
        elif not checked:
            self.acband_spin.setValue(0)

    def _toggle_sniffing(self, checked):
        self.sniffing_spin.setEnabled(checked)
        self.sniffing_unit_combo.setEnabled(checked)
        if checked and self.sniffing_spin.value() == 0:
            self.sniffing_spin.setValue(1.0)
        elif not checked:
            self.sniffing_spin.setValue(0)

    def _range_up(self):
        idx = self.range_combo.currentIndex()
        if idx < self.range_combo.count() - 1:
            self.range_combo.setCurrentIndex(idx + 1)

    def _range_down(self):
        idx = self.range_combo.currentIndex()
        if idx > 0:
            self.range_combo.setCurrentIndex(idx - 1)

    # ── Instrument Actions ────────────────────────────────────

    def refresh_resources(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing", "PyVISA not installed.")
            return
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            self.resource_combo.clear()
            if resources:
                self.resource_combo.addItems(resources)
                self.status_bar.showMessage(f"● VISA: {len(resources)} resource(s) found")
            else:
                self.resource_combo.addItem("GPIB0::22::INSTR")
                self.status_bar.showMessage("● VISA: No resources found")
            if "GPIB0::22::INSTR" not in [self.resource_combo.itemText(i) for i in range(self.resource_combo.count())]:
                self.resource_combo.addItem("GPIB0::22::INSTR")
        except Exception as e:
            QMessageBox.critical(self, "Error", str(e))

    def test_connection(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing", "PyVISA not installed.")
            return
        resource = self.resource_combo.currentText()
        if not resource:
            QMessageBox.warning(self, "Warning", "Select a VISA resource first.")
            return
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource)
            inst.timeout = 5000
            idn = inst.query("ID?")
            inst.close()
            self.status_bar.showMessage(f"● CONNECTED: {idn.strip()}")
            QMessageBox.information(self, "Connected", f"{idn.strip()}\n\n{resource}")
        except Exception as e:
            self.status_bar.showMessage("● CONNECTION FAILED")
            QMessageBox.critical(self, "Failed", str(e))

    def start_measurement(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing", "PyVISA not installed.")
            return
        if not self.measurement_mode:
            QMessageBox.warning(self, "Mode Not Set",
                                "Please select Sampling Mode (Integration or NPLC).")
            return
        if not self._func_btn_group.checkedButton():
            QMessageBox.warning(self, "No Function", "Please select a measurement function.")
            return

        resource = self.resource_combo.currentText()
        n = self.num_measurements_spin.value()
        digits = int(self.digit_combo.currentText())
        auto_zero = self.auto_zero_check.isChecked()
        offset_comp = self.offset_comp_check.isChecked()
        acband_enabled = self.acband_enable_check.isChecked()
        acband_value = self.acband_spin.value()
        lfilter = self.lfilter_check.isChecked()
        setacv = self.setacv_combo.currentText()
        range_cmd = self.range_combo.currentData() or "AUTO"

        gate_time_sec = 0
        nplc_value = None
        sniffing_value = 0

        if self.measurement_mode == "NPLC":
            nplc_value = self.nplc_spin.value()
            if self.sniffing_enable_check.isChecked():
                sv = self.sniffing_spin.value()
                su = self.sniffing_unit_combo.currentText()
                sniffing_value = sv * (60 if su == "minutes" else 3600 if su == "hours" else 1)
        else:
            gtv = self.gate_time_spin.value()
            gtu = self.time_unit_combo.currentText()
            gate_time_sec = gtv * (60 if gtu == "minutes" else 3600 if gtu == "hours" else 1)

        self.all_measurements = []

        self.progress_bar.setMaximum(n)
        self.progress_bar.setValue(0)
        self.sample_count_lbl.setText(f"0 / {n}")
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self._indicator_leds["MEAS RDY"].set_on(False)
        self.status_bar.showMessage("● MEASURING …")
        self.display_label.setText("  --------")

        self.measurement_thread = MeasurementThread(
            resource, n, self.current_func, gate_time_sec, auto_zero, range_cmd,
            mode=self.measurement_mode, nplc=nplc_value, digits=digits,
            offset_comp=offset_comp, acband_enabled=acband_enabled,
            acband_value=acband_value, lfilter=lfilter, setacv=setacv,
            sniffing=sniffing_value
        )
        self.measurement_thread.measurement_ready.connect(self.on_measurement_ready)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        self.measurement_thread.start()

    def stop_measurement(self):
        if self.measurement_thread:
            self.measurement_thread.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("● STOPPED")

    def on_measurement_ready(self, value, num, timestamp):
        self.all_measurements.append((value, timestamp))
        self.progress_bar.setValue(num)
        n = self.num_measurements_spin.value()
        self.sample_count_lbl.setText(f"{num} / {n}")
        scaled, unit = self._scale(value)
        self.display_label.setText(f"  {scaled:+.8f}")
        self.unit_label.setText(f"{unit}  [{self.current_func}]")

    def on_measurement_complete(self, measurements):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._indicator_leds["MEAS RDY"].set_on(True)
        if measurements:
            values = [m[0] for m in measurements]
            avg_raw = sum(values) / len(values)
            avg_s, unit = self._scale(avg_raw)
            self.status_bar.showMessage(f"● COMPLETE  Avg={avg_s:.6f} {unit}")
            self.display_label.setText(f"  {avg_s:+.8f}")
            self.auto_save_and_open_csv()

    def on_error(self, msg):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self._indicator_leds["MEAS RDY"].set_on(False)
        QMessageBox.critical(self, "Error", msg)
        self.status_bar.showMessage(f"● ERROR: {msg[:60]}")

    def execute_math_null(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing", "PyVISA not installed."); return
        resource = self.resource_combo.currentText()
        if not resource:
            QMessageBox.warning(self, "No Resource", "Select VISA resource first."); return
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource)
            inst.timeout = 30000
            self.status_bar.showMessage("● Math NULL …")
            inst.write("TARM HOLD")
            inst.write("TRIG HOLD")
            time.sleep(0.2)
            inst.write("MATH NULL")
            time.sleep(1.0)
            inst.write("TARM AUTO")
            inst.close()
            self.status_bar.showMessage("● MATH NULL complete")
        except Exception as e:
            self.status_bar.showMessage(f"● MATH NULL error: {e}")

    def execute_zero(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing", "PyVISA not installed."); return
        resource = self.resource_combo.currentText()
        if not resource:
            QMessageBox.warning(self, "No Resource", "Select VISA resource first."); return
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource)
            inst.timeout = 30000
            self.status_bar.showMessage("● AZERO ONCE …")
            nplc = self.nplc_spin.value() if self.nplc_spin.isVisible() else 100
            ndig = self.digit_combo.currentText()
            inst.write(f"NPLC {nplc}")
            inst.write(f"NDIG {ndig}")
            inst.write("AZERO ONCE")
            time.sleep(2.0)
            inst.write("TARM AUTO")
            inst.close()
            self.status_bar.showMessage("● AZERO ONCE complete")
        except Exception as e:
            self.status_bar.showMessage(f"● AZERO error: {e}")

    def clear_results(self):
        self.all_measurements = []
        self.progress_bar.setValue(0)
        self.sample_count_lbl.setText("0 / 0")
        self.display_label.setText("  0.00000000")
        self._indicator_leds["MEAS RDY"].set_on(False)
        self.status_bar.showMessage("● CLEARED")

    def auto_save_and_open_csv(self):
        if self.all_measurements:
            self.save_and_open_csv()

    def save_and_open_csv(self):
        if not self.all_measurements:
            QMessageBox.warning(self, "No Data", "No measurements to save."); return
        try:
            script_dir = Path(__file__).parent
            out_dir = script_dir / "Measurement_Results"
            out_dir.mkdir(parents=True, exist_ok=True)
            fname = out_dir / "latest_output.csv"

            values = [m[0] for m in self.all_measurements]
            avg_raw = sum(values) / len(values)
            avg_s, unit = self._scale_csv(avg_raw)
            sf = avg_s / avg_raw if avg_raw != 0 else 1

            with open(fname, 'w', newline='', encoding='utf-8') as f:
                w = csv.writer(f)
                w.writerow(['Measurement'] + list(range(1, len(values)+1)))
                w.writerow(['Value'] + [f'{v*sf:.8g}' for v in values] + [unit])
                now = datetime.now()
                w.writerow(['Date', now.strftime('%Y-%m-%d')])
                w.writerow(['Time', now.strftime('%H:%M:%S')])
                w.writerow([])
                mn, mx = min(values)*sf, max(values)*sf
                std = (sum((x-avg_raw)**2 for x in values)/max(1,len(values)-1))**0.5*sf
                w.writerow(['Statistics','Average','Minimum','Maximum','StdDev'])
                w.writerow(['',f'{avg_s:.8g}',f'{mn:.8g}',f'{mx:.8g}',f'{std:.8g}',unit])
                w.writerow([])
                w.writerow(['Instrument','HP 3458A'])
                w.writerow(['Function', self.current_func])

            if os.name == 'nt':
                os.startfile(fname)
            elif sys.platform == 'darwin':
                subprocess.run(['open', str(fname)])
            else:
                subprocess.run(['xdg-open', str(fname)])

            self.status_bar.showMessage(f"● SAVED: {fname}")
        except Exception as e:
            QMessageBox.critical(self, "Save Error", str(e))

    def _scale(self, value):
        u = self.current_unit
        if u == "V" and abs(value) < 1.0:
            return value * 1000, "mV"
        if u == "Ω":
            if abs(value) >= 1e9: return value * 1e-9, "GΩ"
            if abs(value) >= 1e6: return value * 1e-6, "MΩ"
            if abs(value) >= 1e3: return value * 1e-3, "kΩ"
        return value, u

    def _scale_csv(self, value):
        u = self.current_unit
        if u == "V" and abs(value) < 1.0:
            return value * 1000, "mV"
        if u == "Ω":
            if abs(value) >= 1e9: return value * 1e-9, "Gohm"
            if abs(value) >= 1e6: return value * 1e-6, "Mohm"
            if abs(value) >= 1e3: return value * 1e-3, "kohm"
            return value, "ohm"
        return value, u

    def check_dependencies(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing Dependencies",
                                "PyVISA not installed  →  pip install pyvisa pyvisa-py")


# ─────────────────────────────────────────────────────────────
#  Entry point
# ─────────────────────────────────────────────────────────────
def main():
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    app.setStyle('Fusion')

    # Force dark palette so system-light theme doesn't bleed through
    pal = QPalette()
    pal.setColor(QPalette.ColorRole.Window, QColor(28, 28, 28))
    pal.setColor(QPalette.ColorRole.WindowText, QColor(200, 200, 200))
    pal.setColor(QPalette.ColorRole.Base, QColor(10, 10, 10))
    pal.setColor(QPalette.ColorRole.AlternateBase, QColor(22, 22, 22))
    pal.setColor(QPalette.ColorRole.ToolTipBase, QColor(10, 10, 10))
    pal.setColor(QPalette.ColorRole.ToolTipText, QColor(0, 255, 136))
    pal.setColor(QPalette.ColorRole.Text, QColor(0, 220, 100))
    pal.setColor(QPalette.ColorRole.Button, QColor(40, 40, 50))
    pal.setColor(QPalette.ColorRole.ButtonText, QColor(200, 200, 200))
    pal.setColor(QPalette.ColorRole.Highlight, QColor(0, 160, 80))
    pal.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
    app.setPalette(pal)

    window = HP3458MultimeterGUI3D()
    window.showMaximized()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()

