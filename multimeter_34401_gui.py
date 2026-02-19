"""
HP/Agilent 34401A Multimeter GUI Application
A modern PyQt6-based GUI for controlling and monitoring HP 34401A 6.5-digit Multimeter
Based on HP 3458A template with features specific to 34401A
"""

import sys
import csv
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QGroupBox, QRadioButton, QButtonGroup, QProgressBar, QStatusBar,
    QMessageBox, QCheckBox, QScrollArea, QFrame, QSizePolicy, QLayout, QLineEdit
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
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False


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


class MeasurementThread(QThread):
    """Thread for performing measurements without blocking the UI"""
    measurement_ready = pyqtSignal(float, int, str)  # value, number, timestamp
    measurement_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, resource_name, num_measurements, measurement_type, gate_time, auto_zero, range_val="AUTO", mode="Integration", nplc=None, digits=6, sniffing_enabled=False, sniffing_interval=0):
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
        self.sniffing_enabled = sniffing_enabled
        self.sniffing_interval = sniffing_interval
        self.is_running = True
        self.measurements = []
    
    def run(self):
        """Execute measurements in background thread"""
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(self.resource_name)
            
            # Set appropriate timeout based on mode
            if self.mode == "NPLC":
                timeout_ms = 30000 + int(self.nplc * 100)
            else:
                timeout_ms = 30000 + int(self.gate_time * 1000)
            
            instrument.timeout = timeout_ms
            
            # Reset instrument
            instrument.write("*RST")
            time.sleep(1.0)
            instrument.write("*CLS")
            time.sleep(0.3)
            
            # Set Measurement Function using SCPI commands
            func_map = {
                "DCV": "CONF:VOLT:DC",
                "ACV": "CONF:VOLT:AC",
                "DCI": "CONF:CURR:DC",
                "ACI": "CONF:CURR:AC",
                "OHMS": "CONF:RES",
                "OHMF": "CONF:FRES",
                "FREQ": "CONF:FREQ",
                "CONT": "CONF:CONT",
                "DIODE": "CONF:DIOD"
            }
            conf_cmd = func_map.get(self.measurement_type, "CONF:VOLT:DC")
            instrument.write(conf_cmd)
            time.sleep(0.3)
            
            # Set Range
            if self.range_val != "AUTO":
                range_cmd_map = {
                    "DCV": "SENS:VOLT:DC:RANG",
                    "ACV": "SENS:VOLT:AC:RANG", 
                    "DCI": "SENS:CURR:DC:RANG",
                    "ACI": "SENS:CURR:AC:RANG",
                    "OHMS": "SENS:RES:RANG",
                    "OHMF": "SENS:FRES:RANG"
                }
                range_cmd = range_cmd_map.get(self.measurement_type)
                if range_cmd:
                    instrument.write(f"{range_cmd} {self.range_val}")
            
            # Set Auto-Zero
            if self.measurement_type in ["DCV", "DCI", "OHMS", "OHMF"]:
                azero_cmd = "SENS:ZERO:AUTO ON" if self.auto_zero else "SENS:ZERO:AUTO OFF"
                instrument.write(azero_cmd)
            
            # Set NPLC
            if self.mode == "NPLC":
                nplc_cmd_map = {
                    "DCV": "SENS:VOLT:DC:NPLC",
                    "ACV": "SENS:VOLT:AC:BAND",  # ACV uses bandwidth, not NPLC
                    "DCI": "SENS:CURR:DC:NPLC",
                    "OHMS": "SENS:RES:NPLC",
                    "OHMF": "SENS:FRES:NPLC"
                }
                nplc_cmd = nplc_cmd_map.get(self.measurement_type)
                if nplc_cmd and self.measurement_type != "ACV":
                    instrument.write(f"{nplc_cmd} {self.nplc}")
                
                print(f"DEBUG: NPLC Mode - Setting NPLC = {self.nplc}")
                if self.sniffing_enabled:
                    print(f"DEBUG: Sniffing Enabled - Interval = {self.sniffing_interval}s between measurements")
                
                # Take measurements
                for i in range(self.num_measurements):
                    if not self.is_running:
                        break
                    
                    # Apply sniffing interval delay if enabled
                    if self.sniffing_enabled and self.sniffing_interval > 0:
                        time.sleep(self.sniffing_interval)
                    
                    try:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Read value from instrument
                        value_str = instrument.query("READ?")
                        value = float(value_str.strip())
                        
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        self.measurements.append((value, timestamp))
                        
                    except Exception as e:
                        print(f"DEBUG: Error reading value: {e}")
                        self.error_occurred.emit(str(e))
                        break
            
            else:  # Integration Mode (default)
                print(f"DEBUG: Integration Mode - Using time-interval sampling: {self.gate_time}s per sample")
                
                for i in range(self.num_measurements):
                    if not self.is_running:
                        break
                    
                    # Wait for the specified interval
                    time.sleep(self.gate_time)
                    
                    try:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Read value from instrument
                        value_str = instrument.query("READ?")
                        value = float(value_str.strip())
                        
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        self.measurements.append((value, timestamp))
                        
                    except Exception as e:
                        print(f"DEBUG: Error reading value: {e}")
                        self.error_occurred.emit(str(e))
                        break

            instrument.close()
            self.measurement_complete.emit(self.measurements)
            
        except Exception as e:
            print(f"DEBUG: Main loop thread error: {e}")
            self.error_occurred.emit(str(e))
    
    def stop(self):
        """Stop the measurement thread"""
        self.is_running = False


class PlotCanvas(FigureCanvas):
    """Matplotlib canvas for plotting measurements"""
    
    def __init__(self, parent=None, width=8, height=4, dpi=100):
        self.fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#ffffff')
        self.axes = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)
        
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(400)
        self.updateGeometry()
        
        self.axes.set_facecolor('#f8f9fa')
        self.axes.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.spines['left'].set_color('#3c4043')
        self.axes.spines['bottom'].set_color('#3c4043')
        self.axes.tick_params(colors='#3c4043', labelsize=9)
        
        self.measurements = []
        self.unit = "V"
        self.plot_data()
    
    def plot_data(self):
        """Update the plot with current measurements"""
        self.axes.clear()
        
        if self.measurements:
            x = list(range(1, len(self.measurements) + 1))
            self.axes.plot(x, self.measurements, 'o-', color='#1a73e8', 
                          linewidth=2, markersize=6, label='Measurements')
            
            avg = sum(self.measurements) / len(self.measurements)
            self.axes.axhline(y=avg, color='#ea4335', linestyle='--', 
                            linewidth=1.5, label=f'Average: {avg:.8f} {self.unit}')
            
            self.axes.set_xlabel('Measurement Number', fontsize=10, color='#3c4043', weight='bold')
            self.axes.set_ylabel(f'Value ({self.unit})', fontsize=10, color='#3c4043', weight='bold')
            self.axes.set_title('Real-time Measurements', fontsize=12, color='#3c4043', weight='bold', pad=15)
            self.axes.legend(loc='upper right', fontsize=9, framealpha=0.9)
            self.axes.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        else:
            self.axes.text(0.5, 0.5, 'No data yet', ha='center', va='center',
                          fontsize=14, color='#9aa0a6', transform=self.axes.transAxes)
            self.axes.set_xlabel('Measurement Number', fontsize=10, color='#3c4043', weight='bold')
            self.axes.set_ylabel(f'Value ({self.unit})', fontsize=10, color='#3c4043', weight='bold')
        
        self.fig.tight_layout()
        self.draw()
    
    def add_measurement(self, value):
        self.measurements.append(value)
        self.plot_data()
    
    def clear_measurements(self):
        self.measurements = []
        self.plot_data()
    
    def set_unit(self, unit):
        self.unit = unit


class HP34401MultimeterGUI(QMainWindow):
    """Main GUI window for HP 34401A Multimeter application"""
    
    def __init__(self):
        super().__init__()
        self.measurement_thread = None
        self.all_measurements = []
        self.current_unit = "V"
        self.measurement_mode = "Integration"
        
        # Range definitions for HP 34401A (Label, Unit, SCPI Value)
        self.range_map = {
            "DCV": [
                ("Auto", "V", "AUTO"),
                ("100 mV", "V", "0.1"),
                ("1 V", "V", "1"),
                ("10 V", "V", "10"),
                ("100 V", "V", "100"),
                ("1000 V", "V", "1000")
            ],
            "ACV": [
                ("Auto", "V", "AUTO"),
                ("100 mV", "V", "0.1"),
                ("1 V", "V", "1"),
                ("10 V", "V", "10"),
                ("100 V", "V", "100"),
                ("750 V", "V", "750")
            ],
            "DCI": [
                ("Auto", "A", "AUTO"),
                ("10 mA", "A", "0.01"),
                ("100 mA", "A", "0.1"),
                ("1 A", "A", "1"),
                ("3 A", "A", "3")
            ],
            "ACI": [
                ("Auto", "A", "AUTO"),
                ("1 A", "A", "1"),
                ("3 A", "A", "3")
            ],
            "OHMS": [
                ("Auto", "Ω", "AUTO"),
                ("100 Ω", "Ω", "100"),
                ("1 kΩ", "Ω", "1e3"),
                ("10 kΩ", "Ω", "1e4"),
                ("100 kΩ", "Ω", "1e5"),
                ("1 MΩ", "Ω", "1e6"),
                ("10 MΩ", "Ω", "1e7"),
                ("100 MΩ", "Ω", "1e8")
            ],
            "OHMF": [
                ("Auto", "Ω", "AUTO"),
                ("100 Ω", "Ω", "100"),
                ("1 kΩ", "Ω", "1e3"),
                ("10 kΩ", "Ω", "1e4"),
                ("100 kΩ", "Ω", "1e5"),
                ("1 MΩ", "Ω", "1e6"),
                ("10 MΩ", "Ω", "1e7"),
                ("100 MΩ", "Ω", "1e8")
            ],
            "FREQ": [
                ("Auto", "Hz", "AUTO")
            ],
            "CONT": [
                ("Fixed", "Ω", "1000")
            ],
            "DIODE": [
                ("Fixed", "V", "1")
            ]
        }
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("HP 34401A Digital Multimeter Control Panel")
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
            QScrollArea { border: none; background-color: transparent; }
            QScrollBar:vertical { background-color: transparent; width: 12px; margin: 0px; }
            QScrollBar::handle:vertical { background-color: #d1d5db; border-radius: 6px; min-height: 30px; }
            QScrollBar::handle:vertical:hover { background-color: #9ca3af; }
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical { background: none; }
            QScrollBar:horizontal { background-color: transparent; height: 12px; margin: 0px; }
            QScrollBar::handle:horizontal { background-color: #d1d5db; border-radius: 6px; min-width: 30px; }
            QScrollBar::handle:horizontal:hover { background-color: #9ca3af; }
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
        title = QLabel("📟 HP 34401A Digital Multimeter Control Panel")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #1a73e8; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Connection group
        main_layout.addWidget(self.create_connection_group())
        
        # Measurement type group
        main_layout.addWidget(self.create_measurement_type_group())
        
        # Settings group
        main_layout.addWidget(self.create_settings_group())
        
        # Control buttons
        main_layout.addWidget(self.create_control_buttons())
        
        # Progress bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.progress_bar.setStyleSheet("""
            QProgressBar { border: 2px solid #dadce0; border-radius: 8px; text-align: center;
                          font-weight: bold; color: #3c4043; background-color: #f8f9fa; min-height: 25px; }
            QProgressBar::chunk { background-color: #1a73e8; border-radius: 6px; }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Results and graph layout
        results_layout = QHBoxLayout()
        
        results_group = QGroupBox("📊 Measurement Results")
        results_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        results_group.setStyleSheet(self.get_groupbox_style())
        results_layout_inner = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setFont(QFont("Consolas", 9))
        self.results_text.setStyleSheet("""
            QTextEdit { background-color: #f8f9fa; border: 1px solid #dadce0;
                       border-radius: 8px; padding: 10px; color: #3c4043; }
        """)
        results_layout_inner.addWidget(self.results_text)
        results_group.setLayout(results_layout_inner)
        results_layout.addWidget(results_group, 1)
        
        if MATPLOTLIB_AVAILABLE:
            graph_group = QGroupBox("📈 Live Graph")
            graph_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            graph_group.setStyleSheet(self.get_groupbox_style())
            graph_layout = QVBoxLayout()
            
            self.plot_canvas = PlotCanvas(self, width=6, height=4, dpi=100)
            self.plot_canvas.setMinimumHeight(400)
            graph_layout.addWidget(self.plot_canvas)
            graph_group.setLayout(graph_layout)
            results_layout.addWidget(graph_group, 2)
        
        self.results_text.setMinimumHeight(400)
        main_layout.addLayout(results_layout, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar { background-color: #f8f9fa; color: #5f6368; font-weight: 500;
                        border-top: 1px solid #e8eaed; padding: 8px; }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✨ Ready - HP 34401A Multimeter Control")
        
        # Initialize range for default selection
        self.on_type_changed(True, "DCV", "V")
        self.check_dependencies()
    
    def create_connection_group(self):
        """Create connection settings group"""
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
    
    def create_measurement_type_group(self):
        """Create measurement type selection group"""
        group = QGroupBox("🔬 Measurement Type")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QHBoxLayout()
        self.type_group = QButtonGroup()
        
        # Measurement types for HP 34401A
        types = [
            ("⚡ DC Voltage", "DCV", "V"),
            ("〜 AC Voltage", "ACV", "V"),
            ("⚡ DC Current", "DCI", "A"),
            ("〜 AC Current", "ACI", "A"),
            ("🔧 2W Ω", "OHMS", "Ω"),
            ("🔧 4W Ω", "OHMF", "Ω"),
            ("📊 Frequency", "FREQ", "Hz"),
            ("🔊 Continuity", "CONT", "Ω"),
            ("💡 Diode", "DIODE", "V")
        ]
        
        for i, (label, type_name, unit) in enumerate(types):
            radio = QRadioButton(label)
            radio.setFont(QFont("Segoe UI", 10))
            radio.setStyleSheet("""
                QRadioButton { color: #3c4043; spacing: 8px; }
                QRadioButton::indicator { width: 18px; height: 18px; }
                QRadioButton::indicator:unchecked { border: 2px solid #dadce0; border-radius: 9px; background-color: white; }
                QRadioButton::indicator:checked { border: 2px solid #1a73e8; border-radius: 9px; background-color: #1a73e8; }
            """)
            radio.toggled.connect(lambda checked, t=type_name, u=unit: self.on_type_changed(checked, t, u))
            self.type_group.addButton(radio, i)
            layout.addWidget(radio)
            
            if i == 0:
                radio.setChecked(True)
        
        group.setLayout(layout)
        return group
    
    def create_settings_group(self):
        """Create measurement settings group"""
        group = QGroupBox("⚙️ Measurement Parameters")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        row0_layout = FlowLayout(spacing=5)
        
        # Number of Measurements
        num_label = QLabel("Number of Measurements:")
        num_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(num_label)
        
        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setRange(1, 1000000)
        self.num_measurements_spin.setValue(10)
        self.num_measurements_spin.setFont(QFont("Segoe UI", 10))
        self.num_measurements_spin.setStyleSheet(self.get_spinbox_style())
        self.num_measurements_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row0_layout.addWidget(self.num_measurements_spin)
        
        # Sampling Mode
        mode_label = QLabel("Sampling Mode:")
        mode_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setFont(QFont("Segoe UI", 10))
        self.mode_combo.setStyleSheet(self.get_input_style())
        self.mode_combo.addItems(["-- Select Mode --", "Integration", "NPLC"])
        row0_layout.addWidget(self.mode_combo)
        
        # NPLC controls (max 100 for 34401A)
        self.nplc_label = QLabel("NPLC:")
        self.nplc_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(self.nplc_label)
        
        self.nplc_spin = QDoubleSpinBox()
        self.nplc_spin.setRange(0.02, 100.0)  # 34401A max NPLC is 100
        self.nplc_spin.setValue(10.0)
        self.nplc_spin.setDecimals(2)
        self.nplc_spin.setFont(QFont("Segoe UI", 10))
        self.nplc_spin.setMinimumWidth(100)
        self.nplc_spin.setStyleSheet(self.get_spinbox_style())
        self.nplc_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row0_layout.addWidget(self.nplc_spin)
        
        # Sniffing Container (Checkbox + Spinbox + Unit Dropdown) - for NPLC mode (like 3458A)
        self.sniffing_container = QWidget()
        sniffing_layout = QHBoxLayout(self.sniffing_container)
        sniffing_layout.setContentsMargins(0, 0, 0, 0)
        sniffing_layout.setSpacing(5)
        
        # Sniffing Enable Checkbox
        self.sniffing_enable_check = QCheckBox("Sniffing:")
        self.sniffing_enable_check.setFont(QFont("Segoe UI", 10))
        self.sniffing_enable_check.setStyleSheet(self.get_checkbox_style())
        self.sniffing_enable_check.toggled.connect(self.toggle_sniffing_mode)
        sniffing_layout.addWidget(self.sniffing_enable_check)
        
        # Sniffing Interval Spinbox (shows "Disable" when value is 0)
        self.sniffing_spin = QDoubleSpinBox()
        self.sniffing_spin.setRange(0, 99999.0)
        self.sniffing_spin.setValue(0)
        self.sniffing_spin.setDecimals(2)
        self.sniffing_spin.setSpecialValueText("Disable")  # Show "Disable" when value is 0
        self.sniffing_spin.setFont(QFont("Segoe UI", 10))
        self.sniffing_spin.setMinimumWidth(120)
        self.sniffing_spin.setStyleSheet(self.get_disabled_spinbox_style())
        self.sniffing_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.sniffing_spin.setEnabled(False)
        sniffing_layout.addWidget(self.sniffing_spin)
        
        # Sniffing Unit Dropdown
        self.sniffing_unit_combo = QComboBox()
        self.sniffing_unit_combo.setFont(QFont("Segoe UI", 10))
        self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())
        self.sniffing_unit_combo.addItems(["seconds", "minutes", "hours"])
        self.sniffing_unit_combo.setEnabled(False)
        sniffing_layout.addWidget(self.sniffing_unit_combo)
        
        row0_layout.addWidget(self.sniffing_container)
        
        # Integration/Time Container
        self.time_container = QWidget()
        time_layout = QHBoxLayout(self.time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(5)
        
        self.integ_label = QLabel("Interval:")
        self.integ_label.setFont(QFont("Segoe UI", 10))
        time_layout.addWidget(self.integ_label)
        
        self.gate_time_spin = QDoubleSpinBox()
        self.gate_time_spin.setRange(0.001, 1000.0)
        self.gate_time_spin.setValue(1.0)
        self.gate_time_spin.setDecimals(3)
        self.gate_time_spin.setFont(QFont("Segoe UI", 10))
        self.gate_time_spin.setMinimumWidth(100)
        self.gate_time_spin.setStyleSheet(self.get_spinbox_style())
        self.gate_time_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        time_layout.addWidget(self.gate_time_spin)
        
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.setFont(QFont("Segoe UI", 10))
        self.time_unit_combo.setStyleSheet(self.get_input_style())
        self.time_unit_combo.addItems(["seconds", "minutes", "hours"])
        time_layout.addWidget(self.time_unit_combo)
        
        row0_layout.addWidget(self.time_container)
        
        # NDIG (34401A: 4, 5, 6 digits only)
        digits_label = QLabel("NDIG:")
        digits_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(digits_label)
        
        self.digit_combo = QComboBox()
        self.digit_combo.setFont(QFont("Segoe UI", 10))
        self.digit_combo.setStyleSheet(self.get_input_style())
        self.digit_combo.addItems(["4", "5", "6"])  # 34401A is 6.5 digit max
        self.digit_combo.setCurrentIndex(2)  # Default to 6
        row0_layout.addWidget(self.digit_combo)
        
        # Range
        range_label = QLabel("Range:")
        range_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(range_label)
        
        self.range_combo = QComboBox()
        self.range_combo.setFont(QFont("Segoe UI", 10))
        self.range_combo.setStyleSheet(self.get_input_style())
        row0_layout.addWidget(self.range_combo)
        
        # Auto Zero
        self.auto_zero_check = QCheckBox("Auto Zero")
        self.auto_zero_check.setFont(QFont("Segoe UI", 10))
        self.auto_zero_check.setChecked(True)
        self.auto_zero_check.setStyleSheet(self.get_checkbox_style())
        row0_layout.addWidget(self.auto_zero_check)
        
        layout.addLayout(row0_layout)
        
        # Connect mode change signal
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        group.setLayout(layout)
        return group
    
    def create_control_buttons(self):
        """Create control buttons layout"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(15)
        
        self.start_btn = QPushButton("▶️ Start Measurement")
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet(self.get_button_style("#1a73e8"))
        self.start_btn.clicked.connect(self.start_measurement)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setStyleSheet(self.get_button_style("#5f6368"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        layout.addWidget(self.stop_btn)
        
        clear_btn = QPushButton("🗑️ Clear")
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
        
        # Separator
        layout.addSpacing(20)
        
        # Math Null button - Zero out lead resistance/offset
        math_null_btn = QPushButton("⚖️ Math Null")
        math_null_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        math_null_btn.setMinimumHeight(45)
        math_null_btn.setStyleSheet(self.get_button_style("#059669"))
        math_null_btn.setToolTip("Enable Math Null to subtract lead resistance/offset")
        math_null_btn.clicked.connect(self.execute_math_null)
        layout.addWidget(math_null_btn)
        
        return widget
    
    def on_type_changed(self, checked, type_name, unit):
        """Handle measurement type change"""
        if checked:
            self.current_unit = unit
            
            if hasattr(self, 'range_combo'):
                self.range_combo.clear()
                ranges = self.range_map.get(type_name, [("Auto", unit, "AUTO")])
                for name, r_unit, cmd in ranges:
                    self.range_combo.addItem(name, cmd)
                
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
                self.plot_canvas.set_unit(unit)
                self.plot_canvas.plot_data()
    
    def on_mode_changed(self, mode):
        """Handle mode change between Integration and NPLC mode"""
        self.measurement_mode = mode
        
        if mode == "-- Select Mode --" or not mode:
            self.measurement_mode = None
            if hasattr(self, 'time_container'):
                self.time_container.hide()
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.hide()
            self.nplc_label.hide()
            self.nplc_spin.hide()
            self.nplc_spin.setEnabled(False)
            
        elif mode == "Integration":
            if hasattr(self, 'time_container'):
                self.time_container.show()
                self.gate_time_spin.setEnabled(True)
                self.time_unit_combo.setEnabled(True)
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.hide()
            self.nplc_label.hide()
            self.nplc_spin.hide()
            
        elif mode == "NPLC":
            if hasattr(self, 'time_container'):
                self.time_container.hide()
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.show()
            
            self.nplc_label.show()
            self.nplc_spin.show()
            self.nplc_spin.setEnabled(True)
    
    def toggle_sniffing_mode(self, checked):
        """Toggle Sniffing mode on/off with gray effect (like 3458A)"""
        if checked:
            # ENABLED - Normal active colors
            self.sniffing_spin.setEnabled(True)
            self.sniffing_spin.setStyleSheet(self.get_spinbox_style())
            self.sniffing_unit_combo.setEnabled(True)
            self.sniffing_unit_combo.setStyleSheet(self.get_input_style())
        else:
            # DISABLED - Gray colors, spinbox shows "Disable" via SpecialValueText
            self.sniffing_spin.setValue(0)  # Reset to 0 to show "Disable"
            self.sniffing_spin.setEnabled(False)
            self.sniffing_spin.setStyleSheet(self.get_disabled_spinbox_style())
            self.sniffing_unit_combo.setEnabled(False)
            self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())
            self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())
    
    def set_light_theme(self):
        """Apply light theme"""
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QWidget { background-color: #f8f9fa; color: #3c4043; }
        """)
    
    def get_groupbox_style(self):
        return """
            QGroupBox { font-weight: bold; border: 2px solid #e8eaed; border-radius: 12px;
                       margin-top: 12px; padding-top: 18px; background-color: white; }
            QGroupBox::title { subcontrol-origin: margin; left: 15px; padding: 0 8px;
                              color: #1a73e8; background-color: white; }
        """
    
    def get_input_style(self):
        return """
            QComboBox, QLineEdit { background-color: white; border: 2px solid #dadce0;
                border-radius: 8px; padding: 8px 12px; font-size: 14px; color: #3c4043; min-height: 24px; }
            QComboBox:hover, QLineEdit:hover { border: 2px solid #1a73e8; }
            QComboBox:focus, QLineEdit:focus { border: 2px solid #1a73e8; background-color: #f8f9fa; }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow { image: none; border-left: 5px solid transparent;
                border-right: 5px solid transparent; border-top: 6px solid #1a73e8; margin-right: 8px; }
        """
    
    def get_button_style(self, color):
        return f"""
            QPushButton {{ background-color: {color}; color: white; border: none;
                border-radius: 8px; padding: 10px; font-weight: bold; }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:pressed {{ opacity: 0.7; }}
            QPushButton:disabled {{ background-color: #95a5a6; color: #ecf0f1; }}
        """
    
    def get_spinbox_style(self):
        return """
            QSpinBox, QDoubleSpinBox { background-color: white; border: 2px solid #dadce0;
                border-radius: 8px; padding: 8px 12px; font-size: 14px; color: #3c4043; min-height: 24px; }
            QSpinBox:hover, QDoubleSpinBox:hover { border: 2px solid #1a73e8; }
            QSpinBox:focus, QDoubleSpinBox:focus { border: 2px solid #1a73e8; background-color: #f8f9fa; }
            QSpinBox::down-button, QDoubleSpinBox::down-button { subcontrol-origin: border;
                subcontrol-position: left; width: 28px; border-right: 1px solid #dadce0;
                border-top-left-radius: 6px; border-bottom-left-radius: 6px; background-color: #f8f9fa; }
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover { background-color: #e8f0fe; }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow { image: none; width: 0px; height: 0px;
                border-left: 5px solid transparent; border-right: 5px solid transparent;
                border-top: 6px solid #1a73e8; margin-top: 2px; }
            QSpinBox::up-button, QDoubleSpinBox::up-button { subcontrol-origin: border;
                subcontrol-position: right; width: 28px; border-left: 1px solid #dadce0;
                border-top-right-radius: 6px; border-bottom-right-radius: 6px; background-color: #f8f9fa; }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover { background-color: #e8f0fe; }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow { image: none; width: 0px; height: 0px;
                border-left: 5px solid transparent; border-right: 5px solid transparent;
                border-bottom: 6px solid #1a73e8; margin-bottom: 2px; }
        """
    
    def get_checkbox_style(self):
        return """
            QCheckBox { color: #3c4043; spacing: 8px; }
            QCheckBox::indicator { width: 18px; height: 18px; border: 2px solid #dadce0;
                border-radius: 4px; background-color: white; }
            QCheckBox::indicator:hover { border: 2px solid #1a73e8; }
            QCheckBox::indicator:checked { background-color: #1a73e8; border: 2px solid #1a73e8; }
        """
    
    def get_disabled_spinbox_style(self):
        """Get stylesheet for disabled spinbox controls (gray style)"""
        return """
            QSpinBox, QDoubleSpinBox {
                background-color: #e8eaed;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 14px;
                color: #9aa0a6;
                min-height: 24px;
            }
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                background-color: #d0d0d0;
                border: none;
                width: 20px;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                width: 0px; height: 0px;
                border-left: 5px solid transparent; border-right: 5px solid transparent;
                border-bottom: 6px solid #9aa0a6;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                width: 0px; height: 0px;
                border-left: 5px solid transparent; border-right: 5px solid transparent;
                border-top: 6px solid #9aa0a6;
            }
        """
    
    def get_disabled_input_style(self):
        """Get stylesheet for disabled input controls (gray style)"""
        return """
            QComboBox, QLineEdit {
                background-color: #e8eaed;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                padding: 5px 10px;
                font-size: 14px;
                color: #9aa0a6;
                min-height: 24px;
            }
            QComboBox::drop-down { border: none; width: 30px; }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #9aa0a6;
                margin-right: 8px;
            }
        """
    
    def execute_math_null(self):
        """Execute Math Null function - subtract lead resistance/offset"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource_name)
            inst.timeout = 10000
            
            self.status_bar.showMessage("⚖️ Executing Math Null...")
            self.results_text.append("\n⚖️ Math Null Function")
            self.results_text.append("=" * 40)
            
            # Read current value as null reference
            current_val = inst.query("READ?")
            self.results_text.append(f"📍 Current reading: {current_val.strip()}")
            
            # Enable Null math function
            inst.write("CALC:FUNC NULL")
            inst.write("CALC:STAT ON")
            time.sleep(0.3)
            
            self.results_text.append("✅ Math Null enabled")
            self.results_text.append("📌 All subsequent readings will have this offset subtracted")
            
            inst.close()
            self.status_bar.showMessage("⚖️ Math Null enabled successfully")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ Math Null failed: {str(e)}")
            self.results_text.append(f"\n❌ Error: {str(e)}")
    
    def execute_db_mode(self):
        """Execute dB relative measurement mode"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource_name)
            inst.timeout = 10000
            
            self.status_bar.showMessage("📊 Enabling dB mode...")
            self.results_text.append("\n📊 dB Relative Measurement Mode")
            self.results_text.append("=" * 40)
            
            # Get current voltage as reference
            current_val = inst.query("READ?")
            ref_voltage = float(current_val.strip())
            self.results_text.append(f"📍 Reference voltage: {ref_voltage:.6f} V")
            
            # Set dB reference and enable
            inst.write(f"CALC:DB:REF {ref_voltage}")
            inst.write("CALC:FUNC DB")
            inst.write("CALC:STAT ON")
            time.sleep(0.3)
            
            self.results_text.append("✅ dB mode enabled")
            self.results_text.append(f"📌 dB = 20 × log10(V / {ref_voltage:.6f})")
            
            inst.close()
            self.status_bar.showMessage("📊 dB mode enabled successfully")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ dB mode failed: {str(e)}")
            self.results_text.append(f"\n❌ Error: {str(e)}")
    
    def execute_dbm_mode(self):
        """Execute dBm power measurement mode (reference: 600Ω)"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource_name)
            inst.timeout = 10000
            
            self.status_bar.showMessage("📻 Enabling dBm mode...")
            self.results_text.append("\n📻 dBm Power Measurement Mode")
            self.results_text.append("=" * 40)
            
            # Set reference impedance (600Ω is common for audio)
            inst.write("CALC:DBM:REF 600")  # 600 ohm reference
            inst.write("CALC:FUNC DBM")
            inst.write("CALC:STAT ON")
            time.sleep(0.3)
            
            # Take a reading
            reading = inst.query("READ?")
            self.results_text.append(f"📍 dBm reading: {reading.strip()} dBm")
            self.results_text.append("✅ dBm mode enabled (Reference: 600Ω)")
            self.results_text.append("📌 dBm = 10 × log10(V²/R / 1mW)")
            
            inst.close()
            self.status_bar.showMessage("📻 dBm mode enabled successfully")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ dBm mode failed: {str(e)}")
            self.results_text.append(f"\n❌ Error: {str(e)}")
    
    def execute_minmax(self):
        """Read Min/Max statistics from instrument"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource_name)
            inst.timeout = 10000
            
            self.status_bar.showMessage("📈 Reading Min/Max statistics...")
            self.results_text.append("\n📈 Min/Max Statistics")
            self.results_text.append("=" * 40)
            
            # Enable Min/Max mode if not already
            inst.write("CALC:FUNC AVER")
            inst.write("CALC:STAT ON")
            time.sleep(0.5)
            
            # Read statistics
            try:
                min_val = inst.query("CALC:AVER:MIN?")
                self.results_text.append(f"🔻 Minimum: {min_val.strip()}")
            except:
                self.results_text.append("🔻 Minimum: Not available")
            
            try:
                max_val = inst.query("CALC:AVER:MAX?")
                self.results_text.append(f"🔺 Maximum: {max_val.strip()}")
            except:
                self.results_text.append("🔺 Maximum: Not available")
            
            try:
                avg_val = inst.query("CALC:AVER:AVER?")
                self.results_text.append(f"📊 Average: {avg_val.strip()}")
            except:
                self.results_text.append("📊 Average: Not available")
            
            try:
                count = inst.query("CALC:AVER:COUN?")
                self.results_text.append(f"🔢 Count: {count.strip()}")
            except:
                self.results_text.append("🔢 Count: Not available")
            
            self.results_text.append("\n✅ Min/Max statistics retrieved")
            
            inst.close()
            self.status_bar.showMessage("📈 Min/Max statistics read successfully")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ Min/Max failed: {str(e)}")
            self.results_text.append(f"\n❌ Error: {str(e)}")
    
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        messages = []
        if not PYVISA_AVAILABLE:
            messages.append("⚠️ PyVISA not installed. Install with: pip install pyvisa pyvisa-py")
        if not MATPLOTLIB_AVAILABLE:
            messages.append("⚠️ Matplotlib not installed. Install with: pip install matplotlib")
        if messages:
            self.results_text.append("\n".join(messages))
            self.results_text.append("\n" + "="*60 + "\n")
    
    def refresh_resources(self):
        """Refresh available VISA resources"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            
            self.resource_combo.clear()
            self.resource_combo.addItem("GPIB0::22::INSTR")  # Default 34401A address
            
            if resources:
                for resource in resources:
                    if resource != "GPIB0::22::INSTR":
                        self.resource_combo.addItem(resource)
                self.status_bar.showMessage(f"Found {len(resources)} resource(s)")
            else:
                self.status_bar.showMessage("No resources found, using default")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to list resources:\n{str(e)}")
    
    def test_connection(self):
        """Test connection to instrument"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            idn = instrument.query("*IDN?")
            instrument.close()
            
            QMessageBox.information(self, "Connection Successful", f"Connected to:\n{idn}")
            self.status_bar.showMessage(f"✅ Connected: {idn[:50]}...")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", f"Could not connect:\n{str(e)}")
            self.status_bar.showMessage(f"❌ Connection failed")
    
    def start_measurement(self):
        """Start measurement process"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        if self.measurement_mode not in ["Integration", "NPLC"]:
            QMessageBox.warning(self, "No Mode Selected", "Please select a Sampling Mode first.")
            return
        
        num_measurements = self.num_measurements_spin.value()
        
        # Get selected measurement type
        selected_button = self.type_group.checkedButton()
        if selected_button:
            button_id = self.type_group.id(selected_button)
            types = ["DCV", "ACV", "DCI", "ACI", "OHMS", "OHMF", "FREQ", "CONT", "DIODE"]
            measurement_type = types[button_id] if button_id < len(types) else "DCV"
        else:
            measurement_type = "DCV"
        
        # Get range value
        range_idx = self.range_combo.currentIndex()
        if range_idx >= 0:
            range_data = self.range_combo.itemData(range_idx)
            range_val = range_data if range_data else "AUTO"
        else:
            range_val = "AUTO"
        
        auto_zero = self.auto_zero_check.isChecked()
        nplc_value = self.nplc_spin.value() if self.measurement_mode == "NPLC" else None
        digits = int(self.digit_combo.currentText())
        
        # Calculate gate time
        gate_time_value = self.gate_time_spin.value()
        time_unit = self.time_unit_combo.currentText()
        if time_unit == "minutes":
            gate_time_sec = gate_time_value * 60
        elif time_unit == "hours":
            gate_time_sec = gate_time_value * 3600
        else:
            gate_time_sec = gate_time_value
        
        # Get sniffing settings (only for NPLC mode)
        sniffing_enabled = False
        sniffing_interval = 0
        if self.measurement_mode == "NPLC" and hasattr(self, 'sniffing_enable_check'):
            sniffing_enabled = self.sniffing_enable_check.isChecked()
            if sniffing_enabled:
                sniffing_value = self.sniffing_spin.value()
                sniffing_unit = self.sniffing_unit_combo.currentText()
                if sniffing_unit == "minutes":
                    sniffing_interval = sniffing_value * 60
                elif sniffing_unit == "hours":
                    sniffing_interval = sniffing_value * 3600
                else:  # seconds
                    sniffing_interval = sniffing_value
        
        # Clear previous results
        self.results_text.clear()
        self.all_measurements = []
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.clear_measurements()
        
        self.progress_bar.setMaximum(num_measurements)
        self.progress_bar.setValue(0)
        
        # Display configuration
        self.results_text.append("📊 HP 34401A Measurement Started")
        self.results_text.append("=" * 50)
        self.results_text.append(f"Type: {measurement_type} | Range: {self.range_combo.currentText()}")
        self.results_text.append(f"NDIG: {digits} | Auto-Zero: {'ON' if auto_zero else 'OFF'}")
        if self.measurement_mode == "NPLC":
            self.results_text.append(f"NPLC: {nplc_value}")
            if sniffing_enabled:
                self.results_text.append(f"Sniffing: Enabled ({self.sniffing_spin.value()} {self.sniffing_unit_combo.currentText()})")
            else:
                self.results_text.append("Sniffing: Disabled")
        else:
            self.results_text.append(f"Interval: {gate_time_value} {time_unit}")
        
        # Display dB and dBm reference info for voltage measurements
        if measurement_type in ["DCV", "ACV"]:
            self.results_text.append("-" * 50)
            self.results_text.append("📊 dB/dBm Reference Information:")
            self.results_text.append("  • dB = 20 × log10(V / V_ref)")
            self.results_text.append("  • dBm = 10 × log10(V²/R / 1mW)")
            self.results_text.append("  • dBm Reference Impedance: 600 Ω")
        
        self.results_text.append("=" * 50 + "\n")
        
        # Create and start measurement thread
        self.measurement_thread = MeasurementThread(
            resource_name=resource_name,
            num_measurements=num_measurements,
            measurement_type=measurement_type,
            gate_time=gate_time_sec,
            auto_zero=auto_zero,
            range_val=range_val,
            mode=self.measurement_mode,
            nplc=nplc_value,
            digits=digits,
            sniffing_enabled=sniffing_enabled,
            sniffing_interval=sniffing_interval
        )
        
        self.measurement_thread.measurement_ready.connect(self.on_measurement_ready)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_bar.showMessage("📈 Measurement in progress...")
        
        self.measurement_thread.start()
    
    def stop_measurement(self):
        """Stop current measurement"""
        if self.measurement_thread:
            self.measurement_thread.stop()
            self.measurement_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("⏹️ Measurement stopped")
    
    def on_measurement_ready(self, value, number, timestamp):
        """Handle single measurement result"""
        self.all_measurements.append((value, timestamp))
        self.progress_bar.setValue(number)
        
        scaled_value, unit = self.format_value_with_unit(value, self.current_unit)
        self.results_text.append(f"[{timestamp}] #{number}: {scaled_value:.8g} {unit}")
        
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.add_measurement(value)
    
    def on_measurement_complete(self, measurements):
        """Handle measurement completion"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if measurements:
            values = [m[0] for m in measurements]
            avg = sum(values) / len(values)
            min_val = min(values)
            max_val = max(values)
            
            if len(values) > 1:
                variance = sum((x - avg) ** 2 for x in values) / (len(values) - 1)
                std_dev = variance ** 0.5
            else:
                std_dev = 0
            
            self.results_text.append("\n" + "=" * 50)
            self.results_text.append("📊 Statistics:")
            scaled_avg, unit = self.format_value_with_unit(avg, self.current_unit)
            scaled_min, _ = self.format_value_with_unit(min_val, self.current_unit)
            scaled_max, _ = self.format_value_with_unit(max_val, self.current_unit)
            scaled_std, _ = self.format_value_with_unit(std_dev, self.current_unit)
            
            self.results_text.append(f"Average: {scaled_avg:.8g} {unit}")
            self.results_text.append(f"Min: {scaled_min:.8g} {unit}")
            self.results_text.append(f"Max: {scaled_max:.8g} {unit}")
            self.results_text.append(f"Std Dev: {scaled_std:.8g} {unit}")
            
            # Calculate and display dB/dBm for voltage measurements
            if self.current_unit == "V" and avg != 0:
                import math
                
                self.results_text.append("\n" + "-" * 50)
                self.results_text.append("📊 dB/dBm Calculations (Reference: Average):")
                
                # dB calculation (relative to average)
                # For each value, dB = 20 * log10(V / V_ref)
                # Using average as reference, so dB of average = 0
                self.results_text.append(f"  • dB Reference (V_ref): {avg:.8g} V")
                
                if min_val > 0:
                    db_min = 20 * math.log10(min_val / avg)
                    self.results_text.append(f"  • dB (Min vs Avg): {db_min:.4f} dB")
                
                if max_val > 0:
                    db_max = 20 * math.log10(max_val / avg)
                    self.results_text.append(f"  • dB (Max vs Avg): {db_max:.4f} dB")
                
                # dBm calculation: dBm = 10 * log10(V^2 / R / 0.001)
                # where R = 600 ohm (reference impedance)
                R_ref = 600  # Reference impedance in ohms
                if avg > 0:
                    power_mw = (avg ** 2) / R_ref / 0.001  # Power in mW
                    dbm_avg = 10 * math.log10(power_mw)
                    self.results_text.append(f"\n  • dBm Reference Impedance: {R_ref} Ω")
                    self.results_text.append(f"  • dBm (Average): {dbm_avg:.4f} dBm")
                
                if min_val > 0:
                    power_min = (min_val ** 2) / R_ref / 0.001
                    dbm_min = 10 * math.log10(power_min)
                    self.results_text.append(f"  • dBm (Min): {dbm_min:.4f} dBm")
                
                if max_val > 0:
                    power_max = (max_val ** 2) / R_ref / 0.001
                    dbm_max = 10 * math.log10(power_max)
                    self.results_text.append(f"  • dBm (Max): {dbm_max:.4f} dBm")
        
        self.status_bar.showMessage(f"✅ Measurement complete - {len(measurements)} readings")
        
        # Automatically save and open CSV
        self.save_and_open_csv()
    
    def on_error(self, error_msg):
        """Handle measurement error"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.results_text.append(f"\n❌ Error: {error_msg}")
        self.status_bar.showMessage(f"❌ Error: {error_msg}")
    
    def clear_results(self):
        """Clear all results"""
        self.results_text.clear()
        self.all_measurements = []
        self.progress_bar.setValue(0)
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.clear_measurements()
        self.status_bar.showMessage("🗑️ Results cleared")
    
    def format_value_with_unit(self, value, base_unit):
        """Format value with appropriate scaled unit"""
        scale_factor = 1.0
        disp_unit = base_unit
        
        if base_unit == "V":
            if abs(value) < 1.0:
                scale_factor = 1000.0
                disp_unit = "mV"
        elif base_unit == "Ω":
            if abs(value) >= 1e6:
                scale_factor = 1e-6
                disp_unit = "MΩ"
            elif abs(value) >= 1e3:
                scale_factor = 1e-3
                disp_unit = "kΩ"
        
        return value * scale_factor, disp_unit
    
    def format_value_with_unit_for_csv(self, value, base_unit):
        """Format value for CSV with text-safe units"""
        scale_factor = 1.0
        disp_unit = base_unit
        
        if base_unit == "V":
            if abs(value) < 1.0:
                scale_factor = 1000.0
                disp_unit = "mV"
        elif base_unit == "Ω":
            if abs(value) >= 1e6:
                scale_factor = 1e-6
                disp_unit = "Mohm"
            elif abs(value) >= 1e3:
                scale_factor = 1e-3
                disp_unit = "kohm"
            else:
                disp_unit = "ohm"
        
        return value * scale_factor, disp_unit
    
    def save_and_open_csv(self):
        """Save measurements to CSV and open"""
        if not self.all_measurements:
            return
        
        try:
            import subprocess
            import os
            
            script_dir = Path(__file__).parent
            output_dir = script_dir / "Measurement_Results"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = output_dir / "34401A_output.csv"
            
            # Function to perform save
            def perform_save():
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    self.write_csv_content(csvfile)

            try:
                perform_save()
            except PermissionError:
                # File is open in another app. Force close it.
                self.status_bar.showMessage("⚠️ Closing open file...")
                file_base = filename.name
                
                # 1. Try to kill process with window title containing filename (e.g. "Excel - file.csv")
                subprocess.run(f'taskkill /F /FI "WINDOWTITLE eq *{file_base}*"', 
                             shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                time.sleep(0.5)
                
                try:
                    perform_save()
                except PermissionError:
                    # 2. If valid save still fails, try closing Excel completely (aggressive)
                    # This is what user wants ("close file and overwrite")
                    subprocess.run('taskkill /F /IM excel.exe', 
                                 shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    time.sleep(1.0)
                    perform_save()  # Final retry
            
            # Open file
            if os.name == 'nt':
                os.startfile(filename)
            elif sys.platform == 'darwin':
                subprocess.run(['open', filename])
            else:
                subprocess.run(['xdg-open', filename])
            
            self.status_bar.showMessage(f"💾 Saved and opened: {filename}")
            self.results_text.append(f"\n💾 Data saved to: {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{str(e)}")
    
    def write_csv_content(self, csvfile):
        """Write CSV content"""
        writer = csv.writer(csvfile)
        now = datetime.now()
        
        if not self.all_measurements:
            return
        
        values = [m[0] for m in self.all_measurements]
        
        avg_raw = sum(values) / len(values)
        avg_scaled, scale_unit = self.format_value_with_unit_for_csv(avg_raw, self.current_unit)
        scale_factor = avg_scaled / avg_raw if avg_raw != 0 else 1.0
        
        measurement_numbers = ['Measurement'] + [str(i) for i in range(1, len(values) + 1)]
        writer.writerow(measurement_numbers)
        
        scaled_values = [f'{v * scale_factor:.8g}' for v in values]
        values_row = ['Value'] + scaled_values + [scale_unit]
        writer.writerow(values_row)
        
        writer.writerow(['Date', now.strftime('%Y-%m-%d')])
        writer.writerow(['Time', now.strftime('%H:%M:%S')])
        writer.writerow([])
        
        avg = avg_raw * scale_factor
        min_val = min(values) * scale_factor
        max_val = max(values) * scale_factor
        
        if len(values) > 1:
            variance = sum((x - avg_raw) ** 2 for x in values) / (len(values) - 1)
            std_dev = (variance ** 0.5) * scale_factor
        else:
            std_dev = 0
        
        writer.writerow(['Statistics', 'Average', 'Minimum', 'Maximum', 'Std Deviation'])
        writer.writerow(['', f'{avg:.8g}', f'{min_val:.8g}', f'{max_val:.8g}', f'{std_dev:.8g}', scale_unit])


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    app.setStyle('Fusion')
    
    window = HP34401MultimeterGUI()
    window.showMaximized()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
