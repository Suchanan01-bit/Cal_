"""
Agilent N1996A CSA Spectrum Analyzer GUI Application
A modern PyQt6-based GUI for controlling and monitoring the Agilent N1996A
Cable & Antenna Spectrum Analyzer (100 kHz – 3 GHz)
Template: HP 3458A Multimeter GUI style
"""

import sys
import csv
import os
import subprocess
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QGroupBox, QRadioButton, QButtonGroup, QProgressBar, QStatusBar,
    QMessageBox, QCheckBox, QScrollArea, QFrame, QSizePolicy, QLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QLocale, QRect, QSize, QPoint
from PyQt6.QtGui import QFont
import time

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False

try:
    from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


# ──────────────────────────────────────────────────────────────────────────────
# FlowLayout  (identical to 3458A template)
# ──────────────────────────────────────────────────────────────────────────────

class FlowLayout(QLayout):
    """A layout that arranges widgets in a flow, wrapping to the next line when needed"""

    def __init__(self, parent=None, margin=0, spacing=-1):
        super().__init__(parent)
        self._items = []
        self._spacing = spacing if spacing >= 0 else 8
        if margin >= 0:
            self.setContentsMargins(margin, margin, margin, margin)

    def addItem(self, item):
        self._items.append(item)

    def count(self):
        return len(self._items)

    def itemAt(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return None

    def takeAt(self, index):
        if 0 <= index < len(self._items):
            return self._items.pop(index)
        return None

    def expandingDirections(self):
        return Qt.Orientation(0)

    def hasHeightForWidth(self):
        return True

    def heightForWidth(self, width):
        return self._doLayout(QRect(0, 0, width, 0), True)

    def setGeometry(self, rect):
        super().setGeometry(rect)
        self._doLayout(rect, False)

    def sizeHint(self):
        return self.minimumSize()

    def minimumSize(self):
        size = QSize()
        for item in self._items:
            size = size.expandedTo(item.minimumSize())
        margins = self.contentsMargins()
        size += QSize(margins.left() + margins.right(), margins.top() + margins.bottom())
        return size

    def _doLayout(self, rect, testOnly):
        margins = self.contentsMargins()
        effective_rect = rect.adjusted(margins.left(), margins.top(), -margins.right(), -margins.bottom())
        x = effective_rect.x()
        y = effective_rect.y()
        line_height = 0

        rows = []
        current_row_items = []
        current_line_height = 0
        current_x = effective_rect.x()

        for item in self._items:
            space_x = self._spacing
            next_x = current_x + item.sizeHint().width() + space_x

            if next_x - space_x > effective_rect.right() and current_line_height > 0:
                rows.append((current_row_items, current_line_height))
                current_row_items = []
                current_line_height = 0
                current_x = effective_rect.x()
                next_x = current_x + item.sizeHint().width() + space_x

            current_row_items.append(item)
            current_line_height = max(current_line_height, item.sizeHint().height())
            current_x = next_x

        if current_row_items:
            rows.append((current_row_items, current_line_height))

        if not testOnly:
            y = effective_rect.y()
            for row_items, row_height in rows:
                x = effective_rect.x()
                for item in row_items:
                    item_height = item.sizeHint().height()
                    item_y = y + (row_height - item_height) // 2
                    item.setGeometry(QRect(QPoint(x, item_y), item.sizeHint()))
                    x += item.sizeHint().width() + self._spacing
                y += row_height + self._spacing

        total_height = 0
        for _, row_height in rows:
            total_height += row_height + self._spacing
        if rows:
            total_height -= self._spacing

        return margins.top() + total_height + margins.bottom()


# ──────────────────────────────────────────────────────────────────────────────
# Background Thread: Spectrum Sweep
# ──────────────────────────────────────────────────────────────────────────────

class SweepThread(QThread):
    """Thread that performs a single or continuous spectrum sweep."""
    sweep_ready    = pyqtSignal(list, list, float, float)  # freqs_hz, amps, peak_freq, peak_amp
    sweep_complete = pyqtSignal(list)                       # list of (freq_mhz, amp) tuples
    error_occurred = pyqtSignal(str)

    def __init__(self, resource_name, center_hz, span_hz, rbw_hz, vbw_hz,
                 ref_level, units, num_sweeps=1, continuous=False):
        super().__init__()
        self.resource_name = resource_name
        self.center_hz     = center_hz
        self.span_hz       = span_hz
        self.rbw_hz        = rbw_hz
        self.vbw_hz        = vbw_hz
        self.ref_level     = ref_level
        self.units         = units
        self.num_sweeps    = num_sweeps
        self.continuous    = continuous
        self.is_running    = True
        self.results       = []  # list of (freq_mhz, amp, timestamp)

    def run(self):
        try:
            rm   = pyvisa.ResourceManager()
            inst = rm.open_resource(self.resource_name)
            inst.timeout = 20000

            # Configure
            inst.write("*CLS")
            inst.write("INST:SEL SA")
            inst.write(f"FREQ:CENT {self.center_hz}")
            inst.write(f"FREQ:SPAN {self.span_hz}")
            inst.write(f"DISP:WIND:TRAC:Y:RLEV {self.ref_level}")

            unit_map = {"dBm": "DBM", "dBV": "DBV", "dBmV": "DBMV", "dBµV": "DBUV"}
            inst.write(f"UNIT:POW {unit_map.get(self.units, 'DBM')}")
            inst.write(f"SENS:BAND:RES {self.rbw_hz}")
            inst.write(f"SENS:BAND:VID {self.vbw_hz}")
            inst.write("INIT:CONT OFF")

            sweep_count = 0
            while self.is_running:
                inst.write("INIT:IMM")
                inst.query("*OPC?")

                raw    = inst.query("TRAC? TRACE1")
                values = [float(v) for v in raw.strip().split(',')]

                start_hz = self.center_hz - self.span_hz / 2
                stop_hz  = self.center_hz + self.span_hz / 2
                num_pts  = len(values)
                if num_pts > 1:
                    step  = (stop_hz - start_hz) / (num_pts - 1)
                    freqs = [start_hz + i * step for i in range(num_pts)]
                else:
                    freqs = [self.center_hz]

                peak_amp  = max(values)
                peak_idx  = values.index(peak_amp)
                peak_freq = freqs[peak_idx]

                self.sweep_ready.emit(freqs, values, peak_freq, peak_amp)

                ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.results.append((peak_freq / 1e6, peak_amp, ts))

                sweep_count += 1
                if not self.continuous and sweep_count >= self.num_sweeps:
                    break

            inst.close()
            self.sweep_complete.emit(self.results)

        except Exception as e:
            self.error_occurred.emit(str(e))

    def stop(self):
        self.is_running = False


# ──────────────────────────────────────────────────────────────────────────────
# Spectrum Canvas  (Matplotlib)
# ──────────────────────────────────────────────────────────────────────────────

class SpectrumCanvas(FigureCanvas):
    """Matplotlib canvas for live spectrum display."""

    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.fig  = Figure(figsize=(width, height), dpi=dpi, facecolor="#ffffff")
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(380)
        self.updateGeometry()

        # light style matching 3458A PlotCanvas
        self.axes.set_facecolor("#f8f9fa")
        self.axes.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        self.axes.spines["top"].set_visible(False)
        self.axes.spines["right"].set_visible(False)
        self.axes.spines["left"].set_color("#3c4043")
        self.axes.spines["bottom"].set_color("#3c4043")
        self.axes.tick_params(colors="#3c4043", labelsize=9)

        self.freqs   = []
        self.amps    = []
        self.unit    = "dBm"
        self.plot_data()

    def plot_data(self):
        self.axes.clear()

        if self.freqs and self.amps:
            freqs_mhz = [f / 1e6 for f in self.freqs]
            self.axes.plot(freqs_mhz, self.amps, color="#1a73e8",
                           linewidth=1.5, label="Trace 1")
            self.axes.fill_between(freqs_mhz, self.amps,
                                   min(self.amps) - 5, alpha=0.12, color="#1a73e8")

            peak_amp  = max(self.amps)
            peak_idx  = self.amps.index(peak_amp)
            peak_mhz  = freqs_mhz[peak_idx]
            self.axes.axvline(peak_mhz, color="#ea4335", linestyle=":",
                              linewidth=1.2, label=f"Peak: {peak_mhz:.4f} MHz")

            self.axes.set_xlabel("Frequency (MHz)", fontsize=10, color="#3c4043", weight="bold")
            self.axes.set_ylabel(f"Amplitude ({self.unit})", fontsize=10, color="#3c4043", weight="bold")
            self.axes.set_title("Spectrum — Agilent N1996A", fontsize=12, color="#3c4043", weight="bold", pad=15)
            self.axes.legend(loc="upper right", fontsize=9, framealpha=0.9)
            self.axes.grid(True, alpha=0.3, linestyle="--", linewidth=0.5)
        else:
            self.axes.text(0.5, 0.5, "No sweep data yet", ha="center", va="center",
                           fontsize=14, color="#9aa0a6", transform=self.axes.transAxes)
            self.axes.set_xlabel("Frequency (MHz)", fontsize=10, color="#3c4043", weight="bold")
            self.axes.set_ylabel(f"Amplitude ({self.unit})", fontsize=10, color="#3c4043", weight="bold")

        self.fig.tight_layout()
        self.draw()

    def update_trace(self, freqs_hz, amps):
        self.freqs = freqs_hz
        self.amps  = list(amps)
        self.plot_data()

    def clear_data(self):
        self.freqs = []
        self.amps  = []
        self.plot_data()

    def set_unit(self, unit):
        self.unit = unit


# ──────────────────────────────────────────────────────────────────────────────
# Main GUI
# ──────────────────────────────────────────────────────────────────────────────

class AgilentN1996AGUI(QMainWindow):
    """Main GUI window for Agilent N1996A CSA Spectrum Analyzer — 3458A style"""

    def __init__(self):
        super().__init__()
        self.sweep_thread   = None
        self.all_results    = []   # list of (freq_mhz, amp, timestamp)
        self.current_unit   = "dBm"

        self.init_ui()

    # ──────────────────────────────────────────────────────────────────────────
    # init_ui  (mirrors HP3458MultimeterGUI.init_ui structure)
    # ──────────────────────────────────────────────────────────────────────────

    def init_ui(self):
        self.setWindowTitle("Agilent N1996A CSA Spectrum Analyzer Control Panel")
        self.setGeometry(0, 0, 1920, 1080)
        self.set_light_theme()

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_box = QVBoxLayout(central_widget)
        main_box.setContentsMargins(0, 0, 0, 0)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 12px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #d1d5db;
                border-radius: 6px;
                min-height: 30px;
            }
            QScrollBar::handle:vertical:hover {
                background-color: #9ca3af;
            }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            QScrollBar:horizontal {
                background-color: transparent;
                height: 12px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #d1d5db;
                border-radius: 6px;
                min-width: 30px;
            }
            QScrollBar::handle:horizontal:hover {
                background-color: #9ca3af;
            }
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0px; }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal { background: none; }
        """)
        main_box.addWidget(scroll)

        content_widget = QWidget()
        scroll.setWidget(content_widget)

        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)

        # Title
        title = QLabel("📡 Agilent N1996A  CSA Spectrum Analyzer  •  100 kHz – 3 GHz")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #1a73e8; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)

        # Connection group
        main_layout.addWidget(self.create_connection_group())

        # Sweep mode group
        main_layout.addWidget(self.create_sweep_mode_group())

        # Settings group
        main_layout.addWidget(self.create_settings_group())

        # Control buttons
        main_layout.addWidget(self.create_control_buttons())

        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #dadce0;
                border-radius: 8px;
                text-align: center;
                font-weight: bold;
                color: #3c4043;
                background-color: #f8f9fa;
                min-height: 25px;
            }
            QProgressBar::chunk {
                background-color: #1a73e8;
                border-radius: 6px;
            }
        """)
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)

        # Results + Graph layout  (matches 3458A pattern)
        results_layout = QHBoxLayout()

        results_group = QGroupBox("📊 Sweep Results")
        results_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        results_group.setStyleSheet(self.get_groupbox_style())
        results_layout_inner = QVBoxLayout()

        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 9))
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
                border-radius: 8px;
                padding: 10px;
                color: #3c4043;
            }
        """)
        results_layout_inner.addWidget(self.results_text)
        results_group.setLayout(results_layout_inner)
        results_layout.addWidget(results_group, 1)

        if MATPLOTLIB_AVAILABLE:
            graph_group = QGroupBox("📈 Live Spectrum")
            graph_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            graph_group.setStyleSheet(self.get_groupbox_style())
            graph_layout = QVBoxLayout()

            self.spectrum_canvas = SpectrumCanvas(self, width=6, height=4, dpi=100)
            self.spectrum_canvas.setMinimumHeight(380)
            graph_layout.addWidget(self.spectrum_canvas)
            graph_group.setLayout(graph_layout)
            results_layout.addWidget(graph_group, 2)

        self.results_text.setMinimumHeight(400)
        main_layout.addLayout(results_layout, 1)

        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                color: #5f6368;
                font-weight: 500;
                border-top: 1px solid #e8eaed;
                padding: 8px;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✨ Ready — Agilent N1996A Spectrum Analyzer Control")

        self.check_dependencies()

    # ──────────────────────────────────────────────────────────────────────────
    # Group Builders
    # ──────────────────────────────────────────────────────────────────────────

    def create_connection_group(self):
        """Create instrument connection group — identical pattern to 3458A"""
        group = QGroupBox("🔌 Instrument Connection")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        layout = QHBoxLayout()

        visa_label = QLabel("VISA Resource:")
        visa_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(visa_label)

        self.resource_combo = QComboBox()
        self.resource_combo.setFont(QFont("Segoe UI", 10))
        self.resource_combo.setEditable(True)
        self.resource_combo.setStyleSheet(self.get_input_style())
        layout.addWidget(self.resource_combo, 1)

        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setStyleSheet(self.get_button_style("#9334e9"))
        refresh_btn.clicked.connect(self.refresh_resources)
        layout.addWidget(refresh_btn)

        test_btn = QPushButton("🔍 Test Connection")
        test_btn.setStyleSheet(self.get_button_style("#1a73e8"))
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)

        group.setLayout(layout)
        return group

    def create_sweep_mode_group(self):
        """Sweep mode/type selection — mirrors 3458A measurement type group"""
        group = QGroupBox("🔬 Sweep Mode")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())

        layout = QHBoxLayout()
        self.mode_group = QButtonGroup()

        modes = [
            ("📶 Center / Span",  "cent_span"),
            ("📶 Start / Stop",   "start_stop"),
            ("🔄 Single Sweep",   "single"),
            ("🔄 Continuous",     "continuous"),
        ]

        radio_style = """
            QRadioButton {
                color: #3c4043;
                spacing: 8px;
            }
            QRadioButton::indicator {
                width: 18px;
                height: 18px;
            }
            QRadioButton::indicator:unchecked {
                border: 2px solid #dadce0;
                border-radius: 9px;
                background-color: white;
            }
            QRadioButton::indicator:checked {
                border: 2px solid #1a73e8;
                border-radius: 9px;
                background-color: #1a73e8;
            }
        """

        for i, (label, mode_id) in enumerate(modes):
            rb = QRadioButton(label)
            rb.setFont(QFont("Segoe UI", 10))
            rb.setStyleSheet(radio_style)
            self.mode_group.addButton(rb, i)
            layout.addWidget(rb)
            if i == 0:
                rb.setChecked(True)

        group.setLayout(layout)
        return group

    def create_settings_group(self):
        """Measurement parameters group — uses FlowLayout exactly like 3458A"""
        group = QGroupBox("⚙️ Spectrum Parameters")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())

        layout = QVBoxLayout()
        layout.setSpacing(12)

        row = FlowLayout(spacing=5)

        # ── Frequency ──────────────────────────────────────────────────

        # Center Frequency
        lbl = QLabel("Center Freq:")
        lbl.setFont(QFont("Segoe UI", 10))
        lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lbl)

        self.center_spin = QDoubleSpinBox()
        self.center_spin.setRange(0.0001, 3000.0)
        self.center_spin.setValue(1000.0)
        self.center_spin.setDecimals(4)
        self.center_spin.setFont(QFont("Segoe UI", 10))
        self.center_spin.setMinimumWidth(130)
        self.center_spin.setStyleSheet(self.get_spinbox_style())
        self.center_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row.addWidget(self.center_spin)

        self.center_unit = QComboBox()
        self.center_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        self.center_unit.setCurrentText("MHz")
        self.center_unit.setFont(QFont("Segoe UI", 10))
        self.center_unit.setStyleSheet(self.get_input_style())
        row.addWidget(self.center_unit)

        # Span
        lbl2 = QLabel("Span:")
        lbl2.setFont(QFont("Segoe UI", 10))
        lbl2.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(lbl2)

        self.span_spin = QDoubleSpinBox()
        self.span_spin.setRange(0.0001, 3000.0)
        self.span_spin.setValue(100.0)
        self.span_spin.setDecimals(4)
        self.span_spin.setFont(QFont("Segoe UI", 10))
        self.span_spin.setMinimumWidth(130)
        self.span_spin.setStyleSheet(self.get_spinbox_style())
        self.span_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row.addWidget(self.span_spin)

        self.span_unit = QComboBox()
        self.span_unit.addItems(["Hz", "kHz", "MHz", "GHz"])
        self.span_unit.setCurrentText("MHz")
        self.span_unit.setFont(QFont("Segoe UI", 10))
        self.span_unit.setStyleSheet(self.get_input_style())
        row.addWidget(self.span_unit)

        # ── Reference Level ──────────────────────────────────────────

        ref_lbl = QLabel("Ref Level:")
        ref_lbl.setFont(QFont("Segoe UI", 10))
        ref_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(ref_lbl)

        self.ref_spin = QDoubleSpinBox()
        self.ref_spin.setRange(-150.0, 30.0)
        self.ref_spin.setValue(0.0)
        self.ref_spin.setDecimals(1)
        self.ref_spin.setSuffix(" dBm")
        self.ref_spin.setFont(QFont("Segoe UI", 10))
        self.ref_spin.setMinimumWidth(110)
        self.ref_spin.setStyleSheet(self.get_spinbox_style())
        self.ref_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row.addWidget(self.ref_spin)

        # Units
        unit_lbl = QLabel("Units:")
        unit_lbl.setFont(QFont("Segoe UI", 10))
        unit_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(unit_lbl)

        self.unit_combo = QComboBox()
        self.unit_combo.addItems(["dBm", "dBV", "dBmV", "dBµV"])
        self.unit_combo.setFont(QFont("Segoe UI", 10))
        self.unit_combo.setStyleSheet(self.get_input_style())
        self.unit_combo.currentTextChanged.connect(self.on_unit_changed)
        row.addWidget(self.unit_combo)

        # ── RBW ─────────────────────────────────────────────────────

        rbw_lbl = QLabel("RBW:")
        rbw_lbl.setFont(QFont("Segoe UI", 10))
        rbw_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(rbw_lbl)

        self.rbw_spin = QDoubleSpinBox()
        self.rbw_spin.setRange(0.001, 3000.0)
        self.rbw_spin.setValue(100.0)
        self.rbw_spin.setDecimals(3)
        self.rbw_spin.setFont(QFont("Segoe UI", 10))
        self.rbw_spin.setMinimumWidth(110)
        self.rbw_spin.setStyleSheet(self.get_spinbox_style())
        self.rbw_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row.addWidget(self.rbw_spin)

        self.rbw_unit = QComboBox()
        self.rbw_unit.addItems(["Hz", "kHz", "MHz"])
        self.rbw_unit.setCurrentText("kHz")
        self.rbw_unit.setFont(QFont("Segoe UI", 10))
        self.rbw_unit.setStyleSheet(self.get_input_style())
        row.addWidget(self.rbw_unit)

        # ── VBW ─────────────────────────────────────────────────────

        # Auto VBW checkbox
        self.auto_vbw_check = QCheckBox("Auto VBW")
        self.auto_vbw_check.setFont(QFont("Segoe UI", 10))
        self.auto_vbw_check.setChecked(True)
        self.auto_vbw_check.setStyleSheet(self.get_checkbox_style())
        self.auto_vbw_check.toggled.connect(self.toggle_vbw_input)
        row.addWidget(self.auto_vbw_check)

        # VBW container
        self.vbw_container = QWidget()
        vbw_lay = QHBoxLayout(self.vbw_container)
        vbw_lay.setContentsMargins(0, 0, 0, 0)
        vbw_lay.setSpacing(5)

        vbw_lbl = QLabel("VBW:")
        vbw_lbl.setFont(QFont("Segoe UI", 10))
        vbw_lay.addWidget(vbw_lbl)

        self.vbw_spin = QDoubleSpinBox()
        self.vbw_spin.setRange(0.001, 3000.0)
        self.vbw_spin.setValue(300.0)
        self.vbw_spin.setDecimals(3)
        self.vbw_spin.setFont(QFont("Segoe UI", 10))
        self.vbw_spin.setMinimumWidth(100)
        self.vbw_spin.setStyleSheet(self.get_disabled_spinbox_style())
        self.vbw_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.vbw_spin.setEnabled(False)
        vbw_lay.addWidget(self.vbw_spin)

        self.vbw_unit = QComboBox()
        self.vbw_unit.addItems(["Hz", "kHz", "MHz"])
        self.vbw_unit.setCurrentText("kHz")
        self.vbw_unit.setFont(QFont("Segoe UI", 10))
        self.vbw_unit.setStyleSheet(self.get_disabled_input_style())
        self.vbw_unit.setEnabled(False)
        vbw_lay.addWidget(self.vbw_unit)

        row.addWidget(self.vbw_container)

        # ── Number of Sweeps ─────────────────────────────────────────

        nsweep_lbl = QLabel("Number of Sweeps:")
        nsweep_lbl.setFont(QFont("Segoe UI", 10))
        nsweep_lbl.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row.addWidget(nsweep_lbl)

        self.num_sweeps_spin = QSpinBox()
        self.num_sweeps_spin.setRange(1, 1000000)
        self.num_sweeps_spin.setValue(1)
        self.num_sweeps_spin.setFont(QFont("Segoe UI", 10))
        self.num_sweeps_spin.setStyleSheet(self.get_spinbox_style())
        self.num_sweeps_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row.addWidget(self.num_sweeps_spin)

        layout.addLayout(row)
        group.setLayout(layout)
        return group

    def create_control_buttons(self):
        """Control buttons — identical pattern to 3458A"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(15)

        self.start_btn = QPushButton("▶️ Single Sweep")
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet(self.get_button_style("#1a73e8"))
        self.start_btn.clicked.connect(self.start_single_sweep)
        layout.addWidget(self.start_btn)

        self.cont_btn = QPushButton("🔄 Continuous")
        self.cont_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.cont_btn.setMinimumHeight(45)
        self.cont_btn.setStyleSheet(self.get_button_style("#0f9d58"))
        self.cont_btn.clicked.connect(self.start_continuous_sweep)
        layout.addWidget(self.cont_btn)

        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setStyleSheet(self.get_button_style("#5f6368"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_sweep)
        layout.addWidget(self.stop_btn)

        peak_btn = QPushButton("📌 Peak Search")
        peak_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        peak_btn.setMinimumHeight(45)
        peak_btn.setStyleSheet(self.get_button_style("#e91e63"))
        peak_btn.clicked.connect(self.peak_search)
        layout.addWidget(peak_btn)

        clear_btn = QPushButton("🧹 Clear")
        clear_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        clear_btn.setMinimumHeight(45)
        clear_btn.setStyleSheet(self.get_button_style("#f59e0b"))
        clear_btn.clicked.connect(self.clear_results)
        layout.addWidget(clear_btn)

        save_btn = QPushButton("💾 Save & Open CSV")
        save_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        save_btn.setMinimumHeight(45)
        save_btn.setStyleSheet(self.get_button_style("#1967d2"))
        save_btn.clicked.connect(self.save_and_open_csv)
        layout.addWidget(save_btn)

        return widget

    # ──────────────────────────────────────────────────────────────────────────
    # Event Handlers
    # ──────────────────────────────────────────────────────────────────────────

    def on_unit_changed(self, unit):
        self.current_unit = unit
        self.ref_spin.setSuffix(f" {unit}")
        if MATPLOTLIB_AVAILABLE and hasattr(self, "spectrum_canvas"):
            self.spectrum_canvas.set_unit(unit)
            self.spectrum_canvas.plot_data()

    def toggle_vbw_input(self, checked):
        self.vbw_spin.setEnabled(not checked)
        self.vbw_unit.setEnabled(not checked)
        self.vbw_spin.setStyleSheet(
            self.get_spinbox_style() if not checked else self.get_disabled_spinbox_style()
        )
        self.vbw_unit.setStyleSheet(
            self.get_input_style() if not checked else self.get_disabled_input_style()
        )

    def _get_hz(self, spin, unit_combo):
        mult = {"Hz": 1, "kHz": 1e3, "MHz": 1e6, "GHz": 1e9}
        return spin.value() * mult.get(unit_combo.currentText(), 1)

    def _get_center_span(self):
        center_hz = self._get_hz(self.center_spin, self.center_unit)
        span_hz   = self._get_hz(self.span_spin, self.span_unit)
        return center_hz, span_hz

    def _start_sweep(self, continuous):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed.")
            return

        resource = self.resource_combo.currentText().strip()
        if not resource:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource.")
            return

        center_hz, span_hz = self._get_center_span()
        rbw_hz  = self._get_hz(self.rbw_spin, self.rbw_unit)

        if self.auto_vbw_check.isChecked():
            vbw_hz = rbw_hz * 3
        else:
            vbw_hz = self._get_hz(self.vbw_spin, self.vbw_unit)

        num_sweeps = self.num_sweeps_spin.value()
        ref_level  = self.ref_spin.value()
        units      = self.unit_combo.currentText()

        self.all_results = []
        self.results_text.clear()
        if MATPLOTLIB_AVAILABLE:
            self.spectrum_canvas.clear_data()
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(num_sweeps if not continuous else 0)

        self.sweep_thread = SweepThread(
            resource, center_hz, span_hz, rbw_hz, vbw_hz,
            ref_level, units, num_sweeps, continuous
        )
        self.sweep_thread.sweep_ready.connect(self.on_sweep_ready)
        self.sweep_thread.sweep_complete.connect(self.on_sweep_complete)
        self.sweep_thread.error_occurred.connect(self.on_error)
        self.sweep_thread.start()

        self.start_btn.setEnabled(False)
        self.cont_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        mode = "Continuous sweep" if continuous else "Single sweep"
        self.status_bar.showMessage(f"⟳ {mode} in progress…")

    def start_single_sweep(self):
        self._start_sweep(continuous=False)

    def start_continuous_sweep(self):
        self._start_sweep(continuous=True)

    def stop_sweep(self):
        if self.sweep_thread and self.sweep_thread.isRunning():
            self.sweep_thread.stop()
        self.start_btn.setEnabled(True)
        self.cont_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("⏹ Sweep stopped.")

    def on_sweep_ready(self, freqs_hz, amps, peak_freq_hz, peak_amp):
        units    = self.current_unit
        peak_mhz = peak_freq_hz / 1e6
        ts       = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        if MATPLOTLIB_AVAILABLE:
            self.spectrum_canvas.update_trace(freqs_hz, amps)

        sweep_num = len(self.all_results) + 1
        self.results_text.append(
            f"[{ts}]  Sweep #{sweep_num}  |  Peak: {peak_mhz:.4f} MHz  {peak_amp:.2f} {units}"
        )
        self.all_results.append((peak_mhz, peak_amp, ts))
        self.progress_bar.setValue(min(sweep_num, self.progress_bar.maximum()))
        self.status_bar.showMessage(
            f"✔ Sweep {sweep_num}  |  Peak: {peak_mhz:.4f} MHz,  {peak_amp:.2f} {units}"
        )

    def on_sweep_complete(self, results):
        self.start_btn.setEnabled(True)
        self.cont_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        n = len(results)
        self.status_bar.showMessage(f"✅ Sweep complete — {n} sweep(s) captured.")
        QMessageBox.information(self, "Done", f"Captured {n} sweep(s).")

    def on_error(self, message):
        self.start_btn.setEnabled(True)
        self.cont_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage(f"❌ Error: {message}")
        QMessageBox.critical(self, "Sweep Error", message)

    def peak_search(self):
        if not self.all_results:
            QMessageBox.information(self, "Peak Search", "No sweep data available.")
            return
        last = self.all_results[-1]
        QMessageBox.information(
            self, "Peak Search Result",
            f"Peak Frequency : {last[0]:.6f} MHz\n"
            f"Peak Amplitude : {last[1]:.2f} {self.current_unit}\n"
            f"Timestamp      : {last[2]}"
        )

    def clear_results(self):
        self.all_results = []
        self.results_text.clear()
        if MATPLOTLIB_AVAILABLE:
            self.spectrum_canvas.clear_data()
        self.progress_bar.setValue(0)
        self.status_bar.showMessage("✨ Ready — Agilent N1996A Spectrum Analyzer Control")

    def save_and_open_csv(self):
        """Save results to CSV and open — mirrors 3458A save_and_open_csv"""
        if not self.all_results:
            QMessageBox.warning(self, "No Data", "No sweep data to save!")
            return

        try:
            script_dir  = Path(__file__).parent
            output_dir  = script_dir / "Measurement_Results"
            output_dir.mkdir(parents=True, exist_ok=True)
            filename    = output_dir / "N1996A_latest_output.csv"

            max_retries = 3
            for attempt in range(max_retries):
                if os.name == "nt":
                    try:
                        self.results_text.append(f"🔄 Attempting to close Excel (Try {attempt+1})...")
                        ps_cmd = "Get-Process | Where-Object {$_.MainWindowTitle -like '*N1996A*'} | Stop-Process -Force -PassThru"
                        subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
                        time.sleep(1.0)
                    except Exception as e:
                        self.results_text.append(f"⚠️ Kill failed: {e}")

                try:
                    with open(filename, "w", newline="", encoding="utf-8") as f:
                        self._write_csv(f)

                    self.results_text.append(f"💾 Saved to: {filename}")
                    try:
                        if os.name == "nt":
                            os.startfile(filename)
                        elif sys.platform == "darwin":
                            subprocess.run(["open", str(filename)])
                        else:
                            subprocess.run(["xdg-open", str(filename)])
                        self.results_text.append("📂 File opened automatically.")
                    except Exception as e:
                        self.results_text.append(f"❌ Could not open file: {e}")

                    self.status_bar.showMessage(f"💾 Saved: {filename}")
                    break

                except PermissionError:
                    if attempt < max_retries - 1:
                        time.sleep(0.5)
                    else:
                        QMessageBox.critical(self, "Save Error",
                                             "File is locked. Close N1996A_latest_output.csv and try again.")

        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{e}")

    def _write_csv(self, csvfile):
        writer = csv.writer(csvfile)
        now    = datetime.now()

        freqs = [r[0] for r in self.all_results]
        amps  = [r[1] for r in self.all_results]

        # Horizontal format matching 3458A style
        writer.writerow(["Sweep"] + [str(i) for i in range(1, len(freqs) + 1)])
        writer.writerow(["Peak Freq (MHz)"] + [f"{f:.6f}" for f in freqs])
        writer.writerow(["Peak Amp"] + [f"{a:.4f}" for a in amps] + [self.current_unit])
        writer.writerow(["Date", now.strftime("%Y-%m-%d")] + [""] * (len(freqs) - 1))
        writer.writerow(["Time", now.strftime("%H:%M:%S")] + [""] * (len(freqs) - 1))
        writer.writerow([])

        if amps:
            avg  = sum(amps) / len(amps)
            minv = min(amps)
            maxv = max(amps)
            std  = (sum((a - avg) ** 2 for a in amps) / max(len(amps) - 1, 1)) ** 0.5
            writer.writerow(["Statistics", "Average", "Minimum", "Maximum", "Std Deviation"])
            writer.writerow(["", f"{avg:.4f}", f"{minv:.4f}", f"{maxv:.4f}", f"{std:.4f}", self.current_unit])

    def refresh_resources(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA not installed.")
            return
        try:
            rm        = pyvisa.ResourceManager()
            resources = rm.list_resources()
            self.resource_combo.clear()
            self.resource_combo.addItems(resources)
            self.status_bar.showMessage(f"Found {len(resources)} VISA resource(s).")
        except Exception as e:
            QMessageBox.warning(self, "VISA Error", str(e))

    def test_connection(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA not installed.")
            return
        resource = self.resource_combo.currentText().strip()
        if not resource:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource.")
            return
        try:
            rm   = pyvisa.ResourceManager()
            inst = rm.open_resource(resource)
            inst.timeout = 5000
            idn  = inst.query("*IDN?")
            inst.close()
            QMessageBox.information(self, "Connection OK", f"Device:\n{idn.strip()}")
            self.status_bar.showMessage(f"✔ Connected: {idn.strip()[:80]}")
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", str(e))
            self.status_bar.showMessage(f"✘ Connection failed: {e}")

    def check_dependencies(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing Dependency",
                                "PyVISA not found. Install with: pip install pyvisa pyvisa-py")
        if not MATPLOTLIB_AVAILABLE:
            QMessageBox.warning(self, "Missing Dependency",
                                "Matplotlib not found. Install with: pip install matplotlib")

    # ──────────────────────────────────────────────────────────────────────────
    # Style Methods  (exact 3458A equivalents)
    # ──────────────────────────────────────────────────────────────────────────

    def set_light_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QWidget      { background-color: #f8f9fa; color: #3c4043; }
        """)

    def get_groupbox_style(self):
        return """
            QGroupBox {
                font-weight: bold;
                border: 2px solid #e8eaed;
                border-radius: 12px;
                margin-top: 12px;
                padding-top: 18px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                color: #1a73e8;
                background-color: white;
            }
        """

    def get_button_style(self, color):
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px 16px;
                font-weight: bold;
            }}
            QPushButton:hover    {{ opacity: 0.9; }}
            QPushButton:pressed  {{ opacity: 0.7; }}
            QPushButton:disabled {{ background-color: #95a5a6; }}
        """

    def get_spinbox_style(self):
        return """
            QDoubleSpinBox, QSpinBox {
                border: 2px solid #dadce0;
                border-radius: 6px;
                padding: 4px 8px;
                background-color: white;
                color: #3c4043;
                selection-background-color: #1a73e8;
            }
            QDoubleSpinBox:hover, QSpinBox:hover { border-color: #1a73e8; }
            QDoubleSpinBox:focus, QSpinBox:focus  { border-color: #1a73e8; }
        """

    def get_disabled_spinbox_style(self):
        return """
            QDoubleSpinBox, QSpinBox {
                border: 2px solid #e8eaed;
                border-radius: 6px;
                padding: 4px 8px;
                background-color: #f8f9fa;
                color: #9aa0a6;
            }
        """

    def get_input_style(self):
        return """
            QComboBox {
                border: 2px solid #dadce0;
                border-radius: 6px;
                padding: 4px 8px;
                background-color: white;
                color: #3c4043;
            }
            QComboBox:hover { border-color: #1a73e8; }
            QComboBox:focus { border-color: #1a73e8; }
            QComboBox::drop-down { border: none; }
        """

    def get_disabled_input_style(self):
        return """
            QComboBox {
                border: 2px solid #e8eaed;
                border-radius: 6px;
                padding: 4px 8px;
                background-color: #f8f9fa;
                color: #9aa0a6;
            }
            QComboBox::drop-down { border: none; }
        """

    def get_checkbox_style(self):
        return """
            QCheckBox {
                color: #3c4043;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
            }
            QCheckBox::indicator:unchecked {
                border: 2px solid #dadce0;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:checked {
                border: 2px solid #1a73e8;
                border-radius: 4px;
                background-color: #1a73e8;
            }
        """


# ──────────────────────────────────────────────────────────────────────────────
# Entry point
# ──────────────────────────────────────────────────────────────────────────────

def main():
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    app.setStyle("Fusion")

    window = AgilentN1996AGUI()
    window.showMaximized()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
