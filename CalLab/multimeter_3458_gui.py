"""
HP/Agilent 3458A Multimeter GUI Application
A modern PyQt6-based GUI for controlling and monitoring HP 3458A 8.5-digit Multimeter
"""

import sys
import csv
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
        
        # First pass: calculate line heights
        rows = []  # List of (items, line_height) for each row
        current_row_items = []
        current_line_height = 0
        current_x = effective_rect.x()
        
        for item in self._items:
            space_x = self._spacing
            next_x = current_x + item.sizeHint().width() + space_x
            
            if next_x - space_x > effective_rect.right() and current_line_height > 0:
                # Start new row
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
        
        # Second pass: position items with vertical centering
        if not testOnly:
            y = effective_rect.y()
            for row_items, row_height in rows:
                x = effective_rect.x()
                for item in row_items:
                    item_height = item.sizeHint().height()
                    # Vertically center the item in the row
                    item_y = y + (row_height - item_height) // 2
                    item.setGeometry(QRect(QPoint(x, item_y), item.sizeHint()))
                    x += item.sizeHint().width() + self._spacing
                y += row_height + self._spacing
        
        # Calculate total height
        total_height = 0
        for _, row_height in rows:
            total_height += row_height + self._spacing
        if rows:
            total_height -= self._spacing  # Remove last spacing
        
        return margins.top() + total_height + margins.bottom()


class MeasurementThread(QThread):
    """Thread for performing measurements without blocking the UI"""
    measurement_ready = pyqtSignal(float, int, str)  # value, number, timestamp
    measurement_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    
    
    def __init__(self, resource_name, num_measurements, measurement_type, gate_time, auto_zero, range_val="AUTO", mode="Integration", nplc=None, digits=8, offset_comp=False, acband_enabled=False, acband_value=1, lfilter=False, setacv="disable", sniffing=0):
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
        self.sniffing = sniffing  # Time in seconds to wait before recording each value (0 = use NPLC)
        self.is_running = True
        self.measurements = []  # List of (value, timestamp) tuples
    
    def run(self):
        """Execute measurements in background thread"""
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(self.resource_name)
            
            # Set appropriate timeout based on mode
            if self.mode == "NPLC":
                # NPLC mode: timeout based on NPLC value
                # NPLC 1 ≈ 16.7ms (60Hz) or 20ms (50Hz), scale accordingly
                timeout_ms = 30000 + int(self.nplc * 100)  # Conservative estimate
            else:
                # Integration mode: timeout based on gate time
                timeout_ms = 30000 + int(self.gate_time * 1000)
            
            instrument.timeout = timeout_ms
            
            # 1. STOP and Reset
            instrument.write("TARM HOLD")
            instrument.write("TRIG AUTO")
            time.sleep(0.5)

            # 2. Reset and Basic Setup
            instrument.write("RESET")
            time.sleep(1.5)  # Wait for RESET to complete
            instrument.write("END ALWAYS")
            
            # 3. Set Measurement Function
            func_map = {
                "DCV": "DCV",
                "ACV": "ACV", 
                "DCI": "DCI",
                "ACI": "ACI",
                "OHMS": "OHM",
                "OHMF": "OHMF",  # 4-wire
                "FREQ": "FREQ"
            }
            instrument.write(func_map.get(self.measurement_type, "DCV"))
            time.sleep(0.1)

            # 4. Set Range
            if self.range_val == "AUTO":
                 instrument.write("ARANGE ON")
            else:
                 instrument.write(f"RANGE {self.range_val}")
            
            # 5. Set Auto-Zero
            instrument.write(f"AZERO {1 if self.auto_zero else 0}")
            
            # 6. Set NDIG (Number of Digits)
            instrument.write(f"NDIG {int(self.digits)}")
            
            # 7. Set Offset Compensation
            instrument.write(f"OCOMP {1 if self.offset_comp else 0}")
            
            # 8. Set ACBand (only if enabled)
            if self.acband_enabled:
                instrument.write(f"ACBAND {self.acband_value}")
            
            # 9. Set LFilter
            instrument.write(f"LFILTER {1 if self.lfilter else 0}")
            
            # 10. Set SetACV
            if self.setacv == "sync":
                instrument.write("SETACV SYNC")
            else:
                instrument.write("SETACV ACAL")  # Default
            
            # 11. Configure based on mode
            if self.mode == "NPLC":
                # NPLC Mode with optional Sniffing (time delay before each record)
                # If sniffing > 0: wait sniffing seconds, then record one value
                # If sniffing == 0: use NPLC timing only (no additional delay)
                
                if self.sniffing > 0:
                    print(f"DEBUG: NPLC Mode with Sniffing - NPLC = {self.nplc}, Sniffing = {self.sniffing}s per sample")
                else:
                    print(f"DEBUG: NPLC Mode - Setting NPLC = {self.nplc} (no sniffing delay)")
                
                instrument.write(f"NPLC {self.nplc}")
                instrument.write("NRDGS 1")  # Single reading per trigger
                instrument.write("TRIG AUTO")
                instrument.write("TARM AUTO")
                time.sleep(0.5)
                
                # Take measurements
                for i in range(self.num_measurements):
                    if not self.is_running:
                        break
                    
                    # Apply sniffing delay if specified
                    if self.sniffing > 0:
                        print(f"DEBUG: Sniffing - waiting {self.sniffing}s before sample #{i+1}...")
                        time.sleep(self.sniffing)
                    
                    t_start = time.time()
                    try:
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Read value from instrument
                        value_str = instrument.read()
                        
                        # Parse value
                        try:
                            value = float(value_str.strip().split(',')[0])
                        except ValueError:
                            value = float(value_str.strip())
                            
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        self.measurements.append((value, timestamp))
                        
                    except Exception as e:
                        print(f"DEBUG: Error reading value: {e}")
                        self.error_occurred.emit(str(e))
                        break
                    
                    t_end = time.time()
                    if self.sniffing > 0:
                        print(f"DEBUG: Sample #{i+1} took {t_end - t_start:.2f}s (NPLC={self.nplc}, Sniffing={self.sniffing}s)")
                    else:
                        print(f"DEBUG: Sample #{i+1} took {t_end - t_start:.2f}s (NPLC={self.nplc} only)")
            
            else:  # Integration Mode (default)
                # Integration Mode - Software-controlled time intervals
                print(f"DEBUG: Integration Mode - Using time-interval sampling: {self.gate_time}s per sample")
                instrument.write("NRDGS 1")
                instrument.write("TRIG AUTO")
                instrument.write("TARM AUTO")
                time.sleep(0.5)
                
                # Perform time-interval measurements
                for i in range(self.num_measurements):
                    if not self.is_running:
                        break
                    
                    # Wait for the specified interval BEFORE each measurement (including first)
                    print(f"DEBUG: Waiting {self.gate_time}s before sample #{i+1}...")
                    time.sleep(self.gate_time)
                    
                    t_start = time.time()
                    try:
                        from datetime import datetime
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        
                        # Read current value from instrument
                        value_str = instrument.read()
                        
                        # Handle potential comma-separated values
                        try:
                            value = float(value_str.strip().split(',')[0])
                        except ValueError:
                            value = float(value_str.strip())
                            
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        
                    except Exception as e:
                        print(f"DEBUG: Error reading value: {e}")
                        self.error_occurred.emit(str(e))
                        break
                    
                    t_end = time.time()
                    print(f"DEBUG: Sample #{i+1} took {t_end - t_start:.2f}s (read time)")
                    self.measurements.append((value, timestamp))

            # End of loop
            instrument.write("TARM HOLD")  # Stop triggering
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
        
        # Sizing Policy - Crucial for ScrollArea compatibility
        from PyQt6.QtWidgets import QSizePolicy
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.setMinimumHeight(400)
        self.updateGeometry()
        
        # Styling
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
            
            # Add average line
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
        """Add a new measurement and update plot"""
        self.measurements.append(value)
        self.plot_data()
    
    def clear_measurements(self):
        """Clear all measurements"""
        self.measurements = []
        self.plot_data()
    
    def set_unit(self, unit):
        """Set the measurement unit for display"""
        self.unit = unit


class HP3458MultimeterGUI(QMainWindow):
    """Main GUI window for HP 3458A Multimeter application"""
    
    def __init__(self):
        super().__init__()
        self.measurement_thread = None
        self.all_measurements = []
        self.current_unit = "V"
        self.measurement_mode = "Integration"  # Track current mode: "Integration" or "NPLC"
        
        # Range definitions (Label, Unit, SCPI Value)
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
                ("10 mV", "V", "0.01"),
                ("100 mV", "V", "0.1"),
                ("1 V", "V", "1"),
                ("10 V", "V", "10"),
                ("100 V", "V", "100"),
                ("1000 V", "V", "1000")
            ],
            "DCI": [
                ("Auto", "A", "AUTO"),
                ("100 nA", "A", "1e-7"),
                ("1 µA", "A", "1e-6"),
                ("10 µA", "A", "1e-5"),
                ("100 µA", "A", "1e-4"),
                ("1 mA", "A", "1e-3"),
                ("10 mA", "A", "1e-2"),
                ("100 mA", "A", "1e-1"),
                ("1 A", "A", "1")
            ],
            "ACI": [
                 ("Auto", "A", "AUTO"),
                 ("100 µA", "A", "1e-4"),
                 ("1 mA", "A", "1e-3"),
                 ("10 mA", "A", "1e-2"),
                 ("100 mA", "A", "1e-1"),
                 ("1 A", "A", "1")
            ],
            "OHMS": [
                ("Auto", "Ω", "AUTO"),
                ("10 Ω", "Ω", "10"),
                ("100 Ω", "Ω", "100"),
                ("1 kΩ", "Ω", "1e3"),
                ("10 kΩ", "Ω", "1e4"),
                ("100 kΩ", "Ω", "1e5"),
                ("1 MΩ", "Ω", "1e6"),
                ("10 MΩ", "Ω", "1e7"),
                ("100 MΩ", "Ω", "1e8"),
                ("1 GΩ", "Ω", "1e9")
            ],
            "OHMF": [
                ("Auto", "Ω", "AUTO"),
                ("10 Ω", "Ω", "10"),
                ("100 Ω", "Ω", "100"),
                ("1 kΩ", "Ω", "1e3"),
                ("10 kΩ", "Ω", "1e4"),
                ("100 kΩ", "Ω", "1e5"),
                ("1 MΩ", "Ω", "1e6"),
                ("10 MΩ", "Ω", "1e7"),
                ("100 MΩ", "Ω", "1e8"),
                ("1 GΩ", "Ω", "1e9")
            ],
            "FREQ": [
                 ("Auto", "Hz", "AUTO")
            ]
        }
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("HP 3458A Digital Multimeter Control Panel")
        
        # Fixed full screen size: 1920x1080, starting from top-left
        self.setGeometry(0, 0, 1920, 1080)
        
        # Set light theme
        self.set_light_theme()
        
        # Create central widget
        # Create central widget and main scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_box = QVBoxLayout(central_widget)
        main_box.setContentsMargins(0, 0, 0, 0)
        # Create central widget and scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Scrollbar styling (Light mode) - both vertical and horizontal  
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
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
                height: 0px;
            }
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {
                background: none;
            }
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
            QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal {
                width: 0px;
            }
            QScrollBar::add-page:horizontal, QScrollBar::sub-page:horizontal {
                background: none;
            }
        """)
        
        main_box.addWidget(scroll)
        
        # Content Widget inside Scroll Area (no minimum width for natural fit)
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        
        # Title
        title = QLabel("📟 HP 3458A Digital Multimeter Control Panel")
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
        self.progress_bar.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        main_layout.addWidget(self.progress_bar)
        
        # Results and graph layout
        results_layout = QHBoxLayout()
        
        # Results text area
        results_group = QGroupBox("📊 Measurement Results")
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
        
        # Graph
        if MATPLOTLIB_AVAILABLE:
            graph_group = QGroupBox("📈 Live Graph")
            graph_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            graph_group.setStyleSheet(self.get_groupbox_style())
            graph_layout = QVBoxLayout()
            
            self.plot_canvas = PlotCanvas(self, width=6, height=4, dpi=100)
            self.plot_canvas.setMinimumHeight(400) # Ensure height for scrolling
            graph_layout.addWidget(self.plot_canvas)
            graph_group.setLayout(graph_layout)
            results_layout.addWidget(graph_group, 2) # Expand graph ratio
        
        # Adjust Text Edit height
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
        self.status_bar.showMessage("✨ Ready - HP 3458A Multimeter Control")
        
        # Initialize range for default selection (DCV)
        self.on_type_changed(True, "DCV", "V")
        
        # Check dependencies
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
        
        # Measurement types with emojis
        types = [
            ("⚡ DC Voltage", "DCV", "V"),
            ("〜 AC Voltage", "ACV", "V"),
            ("⚡ DC Current", "DCI", "A"),
            ("〜 AC Current", "ACI", "A"),
            ("🔧 2W Ω", "OHMS", "Ω"),
            ("🔧 4W Ω", "OHMF", "Ω"),
            ("📊 Frequency", "FREQ", "Hz")
        ]
        
        for i, (label, type_name, unit) in enumerate(types):
            radio = QRadioButton(label)
            radio.setFont(QFont("Segoe UI", 10))
            radio.setStyleSheet("""
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
        
        # ============== Row 0: Main Measurement Settings (FlowLayout for auto-wrap) ==============
        row0_layout = FlowLayout(spacing=5)
        
        # Number of Measurements
        num_label = QLabel("Number of Measurements:")
        num_label.setFont(QFont("Segoe UI", 10))
        num_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
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
        mode_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row0_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setFont(QFont("Segoe UI", 10))
        self.mode_combo.setStyleSheet(self.get_input_style())
        self.mode_combo.addItems(["-- Select Mode --", "Integration", "NPLC"])
        row0_layout.addWidget(self.mode_combo)
        
        # NPLC controls
        self.nplc_label = QLabel("NPLC:")
        self.nplc_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(self.nplc_label)
        
        self.nplc_spin = QDoubleSpinBox()
        self.nplc_spin.setRange(0.02, 1000.0)
        self.nplc_spin.setValue(100.0)
        self.nplc_spin.setDecimals(2)
        self.nplc_spin.setFont(QFont("Segoe UI", 10))
        self.nplc_spin.setMinimumWidth(130)  # Wide enough for 6 digits + decimals
        self.nplc_spin.setStyleSheet(self.get_spinbox_style())
        self.nplc_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row0_layout.addWidget(self.nplc_spin)
        
        # Sniffing Container (Checkbox + Spinbox + Unit Dropdown) - for NPLC mode
        self.sniffing_container = QWidget()
        sniffing_layout = QHBoxLayout(self.sniffing_container)
        sniffing_layout.setContentsMargins(0, 0, 0, 0)
        sniffing_layout.setSpacing(5)
        
        # sniffing Enable Checkbox
        self.sniffing_enable_check = QCheckBox("Sniffing:")
        self.sniffing_enable_check.setFont(QFont("Segoe UI", 10))
        self.sniffing_enable_check.setStyleSheet(self.get_checkbox_style())
        self.sniffing_enable_check.toggled.connect(self.toggle_sniffing_input)
        sniffing_layout.addWidget(self.sniffing_enable_check)
        
        # Interval Spinbox (5 digits width)
        self.sniffing_spin = QDoubleSpinBox()
        self.sniffing_spin.setRange(0, 99999.0)
        self.sniffing_spin.setValue(0)
        self.sniffing_spin.setDecimals(2)
        self.sniffing_spin.setSpecialValueText("Disable")  # Show "Disable" when value is 0
        self.sniffing_spin.setFont(QFont("Segoe UI", 10))
        self.sniffing_spin.setMinimumWidth(120)  # Wide enough for 5 digits + decimals
        self.sniffing_spin.setStyleSheet(self.get_disabled_spinbox_style())  # Disabled style by default
        self.sniffing_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.sniffing_spin.setEnabled(False)  # Disabled by default
        sniffing_layout.addWidget(self.sniffing_spin)
        
        # Interval Unit Dropdown
        self.sniffing_unit_combo = QComboBox()
        self.sniffing_unit_combo.setFont(QFont("Segoe UI", 10))
        self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())  # Disabled style by default
        self.sniffing_unit_combo.addItems(["seconds", "minutes", "hours"])
        self.sniffing_unit_combo.setEnabled(False)  # Disabled by default
        sniffing_layout.addWidget(self.sniffing_unit_combo)
        
        row0_layout.addWidget(self.sniffing_container)
        
        # Integration/Time Container (Label + Controls)
        self.time_container = QWidget()
        time_layout = QHBoxLayout(self.time_container)
        time_layout.setContentsMargins(0, 0, 0, 0)
        time_layout.setSpacing(5)
        
        # Interval Label
        self.integ_label = QLabel("Interval:")
        self.integ_label.setFont(QFont("Segoe UI", 10))
        time_layout.addWidget(self.integ_label)
        
        self.gate_time_spin = QDoubleSpinBox()
        self.gate_time_spin.setRange(0.001, 1000.0)
        self.gate_time_spin.setValue(1.0)
        self.gate_time_spin.setDecimals(3)
        self.gate_time_spin.setFont(QFont("Segoe UI", 10))
        self.gate_time_spin.setMinimumWidth(110)
        self.gate_time_spin.setStyleSheet(self.get_spinbox_style())
        self.gate_time_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        time_layout.addWidget(self.gate_time_spin)
        
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.setFont(QFont("Segoe UI", 10))
        self.time_unit_combo.setStyleSheet(self.get_input_style())
        self.time_unit_combo.addItems(["seconds", "minutes", "hours"])
        time_layout.addWidget(self.time_unit_combo)
        
        row0_layout.addWidget(self.time_container)
        
        # NDIG
        digits_label = QLabel("NDIG:")
        digits_label.setFont(QFont("Segoe UI", 10))
        digits_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row0_layout.addWidget(digits_label)
        
        self.digit_combo = QComboBox()
        self.digit_combo.setFont(QFont("Segoe UI", 10))
        self.digit_combo.setStyleSheet(self.get_input_style())
        self.digit_combo.addItems(["4", "5", "6", "7", "8"])
        self.digit_combo.setCurrentIndex(4)
        row0_layout.addWidget(self.digit_combo)
        
        # Range
        range_label = QLabel("Range:")
        range_label.setFont(QFont("Segoe UI", 10))
        range_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
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
        
        # Offset Comp
        self.offset_comp_check = QCheckBox("Offset Comp")
        self.offset_comp_check.setFont(QFont("Segoe UI", 10))
        self.offset_comp_check.setStyleSheet(self.get_checkbox_style())
        row0_layout.addWidget(self.offset_comp_check)
        
        # ACBand (continuing in same FlowLayout)
        self.acband_enable_check = QCheckBox("ACBand:")
        self.acband_enable_check.setFont(QFont("Segoe UI", 10))
        self.acband_enable_check.setStyleSheet(self.get_checkbox_style())
        self.acband_enable_check.toggled.connect(self.toggle_acband_input)
        row0_layout.addWidget(self.acband_enable_check)
        
        self.acband_spin = QSpinBox()
        self.acband_spin.setRange(0, 100000)
        self.acband_spin.setValue(0)
        self.acband_spin.setSpecialValueText("Disable")  # Show "Disable" when value is 0
        self.acband_spin.setSuffix(" Hz")
        self.acband_spin.setFont(QFont("Segoe UI", 10))
        self.acband_spin.setStyleSheet(self.get_disabled_spinbox_style())  # Disabled style by default
        self.acband_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.acband_spin.setEnabled(False)  # Disabled by default
        row0_layout.addWidget(self.acband_spin)
        
        # LFilter
        self.lfilter_check = QCheckBox("LFilter")
        self.lfilter_check.setFont(QFont("Segoe UI", 10))
        self.lfilter_check.setStyleSheet(self.get_checkbox_style())
        row0_layout.addWidget(self.lfilter_check)
        
        # SetACV
        setacv_label = QLabel("SetACV:")
        setacv_label.setFont(QFont("Segoe UI", 10))
        setacv_label.setAlignment(Qt.AlignmentFlag.AlignVCenter)
        row0_layout.addWidget(setacv_label)
        
        self.setacv_combo = QComboBox()
        self.setacv_combo.addItems(["disable", "sync"])
        self.setacv_combo.setFont(QFont("Segoe UI", 10))
        self.setacv_combo.setStyleSheet(self.get_input_style())
        row0_layout.addWidget(self.setacv_combo)
        
        layout.addLayout(row0_layout)

        # Connect mode change signal AFTER all controls are created
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        group.setLayout(layout)
        return group
    
    def create_control_buttons(self):
        """Create control buttons layout"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setSpacing(15)
        
        # Start button
        self.start_btn = QPushButton("▶️ Start Measurement")
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(45)
        self.start_btn.setStyleSheet(self.get_button_style("#1a73e8"))
        self.start_btn.clicked.connect(self.start_measurement)
        layout.addWidget(self.start_btn)
        
        # Stop button
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.stop_btn.setMinimumHeight(45)
        self.stop_btn.setStyleSheet(self.get_button_style("#5f6368"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        layout.addWidget(self.stop_btn)
        
        # Math Null button - for zeroing cable lead offset (MOVED TO FRONT)
        self.math_null_btn = QPushButton("Zero Func")
        self.math_null_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.math_null_btn.setMinimumHeight(45)
        self.math_null_btn.setStyleSheet(self.get_button_style("#e91e63"))  # Pink color
        self.math_null_btn.clicked.connect(self.execute_math_null)
        layout.addWidget(self.math_null_btn)
        
        # Zero Fnc button - for zeroing current range only (MOVED TO FRONT, RENAMED)
        self.zero_btn = QPushButton("⚖️ Zero Rng")
        self.zero_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.zero_btn.setMinimumHeight(45)
        self.zero_btn.setStyleSheet(self.get_button_style("#ff9800"))  # Orange color
        self.zero_btn.clicked.connect(self.execute_zero)
        layout.addWidget(self.zero_btn)
        
        # Clear button
        clear_btn = QPushButton("�️ Clear")
        clear_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        clear_btn.setMinimumHeight(45)
        clear_btn.setStyleSheet(self.get_button_style("#f59e0b"))
        clear_btn.clicked.connect(self.clear_results)
        layout.addWidget(clear_btn)
        
        # Save button
        save_btn = QPushButton("💾 Save & Open CSV")
        save_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        save_btn.setMinimumHeight(45)
        save_btn.setStyleSheet(self.get_button_style("#1967d2"))
        save_btn.clicked.connect(self.save_and_open_csv)
        layout.addWidget(save_btn)
        
        return widget

    
    def on_type_changed(self, checked, type_name, unit):
        """Handle measurement type change"""
        if checked:
            self.current_unit = unit
            
            # Update Range Combo (Safety check included)
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
        print(f"DEBUG: on_mode_changed called with mode = '{mode}'")
        
        self.measurement_mode = mode
        
        if mode == "-- Select Mode --" or not mode:
            self.measurement_mode = None
            if hasattr(self, 'time_container'):
                self.time_container.hide()
            self.nplc_label.hide()
            self.nplc_spin.hide()
            self.nplc_spin.setEnabled(False)
            # Hide sniffing container
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.hide()
            
        elif mode == "Integration":
            # Show Integration/Time, Hide NPLC and Sniffing
            if hasattr(self, 'time_container'):
                self.time_container.show()
                self.gate_time_spin.setEnabled(True)
                self.time_unit_combo.setEnabled(True)
            self.nplc_label.hide()
            self.nplc_spin.hide()
            # Hide sniffing container
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.hide()
            
        elif mode == "NPLC":
            # Hide Integration/Time, Show NPLC and Sniffing
            if hasattr(self, 'time_container'):
                self.time_container.hide()
            
            print(f"DEBUG: NPLC mode - showing nplc_label, nplc_spin, and sniffing controls")
            self.nplc_label.show()
            self.nplc_spin.show()
            self.nplc_spin.setEnabled(True)
            # Show sniffing container
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.show()
            
        # Force layout update to remove gaps immediately
        if hasattr(self, 'time_container'):
            self.time_container.update()
            self.time_container.parentWidget().update()
    
    def toggle_sniffing_input(self, checked):
        """Toggle sniffing input controls based on checkbox state"""
        self.sniffing_spin.setEnabled(checked)
        self.sniffing_unit_combo.setEnabled(checked)
        
        if checked:
            # Enable style - normal colors
            self.sniffing_spin.setStyleSheet(self.get_spinbox_style())
            self.sniffing_unit_combo.setStyleSheet(self.get_input_style())
            # Set default value when enabling
            if self.sniffing_spin.value() == 0:
                self.sniffing_spin.setValue(1.0)
        else:
            # Disable style - gray colors
            self.sniffing_spin.setStyleSheet(self.get_disabled_spinbox_style())
            self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())
            # Reset to 0 to show "Disable" text
            self.sniffing_spin.setValue(0)
    
    def set_light_theme(self):
        """Apply light theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QWidget {
                background-color: #f8f9fa;
                color: #3c4043;
            }
        """)
    
    def get_groupbox_style(self):
        """Get stylesheet for group boxes"""
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
    
    def get_input_style(self):
        """Get stylesheet for input widgets"""
        return """
            QComboBox, QLineEdit {
                background-color: white;
                border: 2px solid #dadce0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #3c4043;
                min-height: 24px;
            }
            QComboBox:hover, QLineEdit:hover {
                border: 2px solid #1a73e8;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 2px solid #1a73e8;
                background-color: #f8f9fa;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #1a73e8;
                margin-right: 8px;
            }
        """
    
    def get_disabled_input_style(self):
        """Get stylesheet for disabled input widgets (gray style)"""
        return """
            QComboBox, QLineEdit {
                background-color: #e8eaed;
                border: 2px solid #d0d0d0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #9aa0a6;
                min-height: 24px;
            }
            QComboBox::drop-down {
                border: none;
                width: 30px;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #9aa0a6;
                margin-right: 8px;
            }
        """
    
    def get_button_style(self, color):
        """Get stylesheet for buttons"""
        return f"""
            QPushButton {{
                background-color: {color};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                opacity: 0.9;
            }}
            QPushButton:pressed {{
                opacity: 0.7;
            }}
            QPushButton:disabled {{
                background-color: #95a5a6;
                color: #ecf0f1;
            }}
        """
    
    def get_spinbox_style(self):
        """Get stylesheet for spinbox controls with clear +/- buttons"""
        return """
            QSpinBox, QDoubleSpinBox {
                background-color: white;
                border: 2px solid #dadce0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #3c4043;
                min-height: 24px;
            }
            QSpinBox:hover, QDoubleSpinBox:hover {
                border: 2px solid #1a73e8;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #1a73e8;
                background-color: #f8f9fa;
            }
            
            /* Down Button (Minus) - LEFT SIDE */
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                subcontrol-origin: border;
                subcontrol-position: left;
                width: 28px;
                border-right: 1px solid #dadce0;
                border-top-left-radius: 6px;
                border-bottom-left-radius: 6px;
                background-color: #f8f9fa;
            }
            QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover {
                background-color: #e8f0fe;
            }
            QSpinBox::down-button:pressed, QDoubleSpinBox::down-button:pressed {
                background-color: #d2e3fc;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #1a73e8;
                margin-top: 2px;
            }
            QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {
                border-top: 6px solid #174ea6;
            }
            
            /* Up Button (Plus) - RIGHT SIDE */
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: right;
                width: 28px;
                border-left: 1px solid #dadce0;
                border-top-right-radius: 6px;
                border-bottom-right-radius: 6px;
                background-color: #f8f9fa;
            }
            QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover {
                background-color: #e8f0fe;
            }
            QSpinBox::up-button:pressed, QDoubleSpinBox::up-button:pressed {
                background-color: #d2e3fc;
            }
            QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {
                image: none;
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid #1a73e8;
                margin-bottom: 2px;
            }
            QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {
                border-bottom: 6px solid #174ea6;
            }
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
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-bottom: 6px solid #9aa0a6;
            }
            QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {
                width: 0px;
                height: 0px;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 6px solid #9aa0a6;
            }
        """

    def get_checkbox_style(self):
        """Get stylesheet for checkboxes with checkmark icon"""
        return """
            QCheckBox {
                color: #3c4043;
                spacing: 8px;
            }
            QCheckBox::indicator {
                width: 18px;
                height: 18px;
                border: 2px solid #dadce0;
                border-radius: 4px;
                background-color: white;
            }
            QCheckBox::indicator:hover {
                border-color: #1a73e8;
            }
            QCheckBox::indicator:checked {
                background-color: #1a73e8;
                border-color: #1a73e8;
                image: url(data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxNCIgaGVpZ2h0PSIxNCIgdmlld0JveD0iMCAwIDI0IDI0IiBmaWxsPSJub25lIiBzdHJva2U9IndoaXRlIiBzdHJva2Utd2lkdGg9IjQiIHN0cm9rZS1saW5lY2FwPSJyb3VuZCIgc3Ryb2tlLWxpbmVqb2luPSJyb3VuZCI+PHBvbHlsaW5lIHBvaW50cz0iMjAgNiA5IDE3IDQgMTIiPjwvcG9seWxpbmU+PC9zdmc+);
            }
        """
    
    def check_dependencies(self):
        """Check if required dependencies are installed"""
        messages = []
        
        if not PYVISA_AVAILABLE:
            messages.append("⚠️ PyVISA not installed - Install with: pip install pyvisa pyvisa-py")
        
        if not MATPLOTLIB_AVAILABLE:
            messages.append("⚠️ Matplotlib not installed - Install with: pip install matplotlib")
        
        if messages:
            QMessageBox.warning(self, "Missing Dependencies", "\n".join(messages))
    
    def refresh_resources(self):
        """Refresh available VISA resources"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            
            self.resource_combo.clear()
            
            if resources:
                self.resource_combo.addItems(resources)
                self.resource_combo.setCurrentIndex(0) # Auto-select first available
                self.status_bar.showMessage(f"✅ Found {len(resources)} VISA resource(s). Selected: {resources[0]}")
            else:
                self.resource_combo.addItem("GPIB0::2::INSTR")
                self.status_bar.showMessage("⚠️ No VISA resources found")
            
            # Ensure default is available
            if "GPIB0::2::INSTR" not in [self.resource_combo.itemText(i) for i in range(self.resource_combo.count())]:
                self.resource_combo.addItem("GPIB0::2::INSTR")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to refresh resources:\n{str(e)}")
            self.status_bar.showMessage("❌ Error refreshing resources")
    
    def test_connection(self):
        """Test connection to the instrument"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        
        if not resource_name:
            QMessageBox.warning(self, "Warning", "Please select a VISA resource first!")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            # Query instrument identification
            idn = instrument.query("ID?")
            instrument.close()
            
            # Create custom message box with detailed information
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Connection Successful")
            msg_box.setIcon(QMessageBox.Icon.Information)
            
            # Format the message with detailed information
            message = f"Connected to:\n{idn.strip()}\n\nVISA Resource:\n{resource_name}"
            msg_box.setText(message)
            
            # Style the message box
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #202124;
                    font-size: 13px;
                    min-width: 350px;
                }
                QPushButton {
                    background-color: #1a73e8;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 24px;
                    font-size: 13px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #1557b0;
                }
            """)
            
            msg_box.exec()
            
            self.status_bar.showMessage(f"✅ Connected: {idn.strip()}")
            
        except Exception as e:
            # Error message box
            msg_box = QMessageBox(self)
            msg_box.setWindowTitle("Connection Failed")
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setText(f"Failed to connect to instrument.\n\nError:\n{str(e)}")
            
            msg_box.setStyleSheet("""
                QMessageBox {
                    background-color: white;
                }
                QMessageBox QLabel {
                    color: #202124;
                    font-size: 13px;
                    min-width: 350px;
                }
                QPushButton {
                    background-color: #d93025;
                    color: white;
                    border: none;
                    border-radius: 4px;
                    padding: 8px 24px;
                    font-size: 13px;
                    font-weight: bold;
                    min-width: 80px;
                }
                QPushButton:hover {
                    background-color: #b31412;
                }
            """)
            
            msg_box.exec()
            self.status_bar.showMessage("❌ Connection failed")
    
    def start_measurement(self):
        """Start measurement process"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        # Check if mode is selected
        if not self.measurement_mode or self.measurement_mode == "-- Select Mode --":
            QMessageBox.warning(self, "Mode Not Selected", "Please select a Sampling Mode (Integration or NPLC) before starting measurement!")
            return
        
        resource_name = self.resource_combo.currentText()
        num_measurements = self.num_measurements_spin.value()
        
        # Determine mode and get appropriate parameters
        gate_time_sec = 0
        gate_time_value = 0
        nplc_value = None
        sniffing_value = 0
        time_unit = "s"
        sniffing_display = ""

        if self.measurement_mode == "NPLC":
            # NPLC Mode with optional sniffing
            nplc_value = self.nplc_spin.value()
            
            # Check if sniffing is enabled
            if self.sniffing_enable_check.isChecked():
                sniffing_raw = self.sniffing_spin.value()
                sniffing_unit = self.sniffing_unit_combo.currentText()
                
                # Convert sniffing to seconds
                if sniffing_unit == "minutes":
                    sniffing_value = sniffing_raw * 60.0
                elif sniffing_unit == "hours":
                    sniffing_value = sniffing_raw * 3600.0
                else:  # seconds
                    sniffing_value = sniffing_raw
                    
                sniffing_display = f"{sniffing_raw} {sniffing_unit} ({sniffing_value:.1f}s)"
            else:
                sniffing_value = 0  # Disabled = use NPLC timing only
                
            gate_time_sec = 0  
            time_unit = "NPLC"
        elif self.measurement_mode == "Integration":
            # Integration Mode only - Get time value and convert to seconds
            gate_time_value = self.gate_time_spin.value()
            time_unit = self.time_unit_combo.currentText()
            
            if time_unit == "minutes":
                gate_time_sec = gate_time_value * 60.0
            elif time_unit == "hours":
                gate_time_sec = gate_time_value * 3600.0
            else:  # seconds
                gate_time_sec = gate_time_value

            nplc_value = None
            
        auto_zero = self.auto_zero_check.isChecked()
        
        # Get NDIG and offset compensation settings
        digits = int(self.digit_combo.currentText())
        offset_comp = self.offset_comp_check.isChecked()
        
        # Get selected measurement type
        selected_button = self.type_group.checkedButton()
        if not selected_button:
            QMessageBox.warning(self, "Error", "Please select a measurement type!")
            return
        
        button_id = self.type_group.id(selected_button)
        type_map = ["DCV", "ACV", "DCI", "ACI", "OHMS", "OHMF", "FREQ"]
        measurement_type = type_map[button_id]
        
        # Clear previous results
        self.all_measurements = []
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.clear_measurements()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(num_measurements)
        self.results_text.clear()
        self.results_text.append("🔄 Starting measurement...\n")
        self.results_text.append(f"Type: {measurement_type}")
        self.results_text.append(f"Mode: {self.measurement_mode}")
        
        if self.measurement_mode == "NPLC":
            self.results_text.append(f"NPLC: {nplc_value}")
            if sniffing_value > 0:
                self.results_text.append(f"Sniffing: {sniffing_display}")
            else:
                self.results_text.append(f"Sniffing: OFF (NPLC timing only)")
        else:
            self.results_text.append(f"Integration: {gate_time_value:.2f} {time_unit} ({gate_time_sec:.1f}s)")
        
        self.results_text.append(f"Auto-Zero: {'ON' if auto_zero else 'OFF'}\n")
        
        # Get Range SCPI command
        range_cmd_val = self.range_combo.currentData()
        if not range_cmd_val:
            range_cmd_val = "AUTO"

        # Get new settings values
        acband_enabled = self.acband_enable_check.isChecked()
        acband_value = self.acband_spin.value()
        lfilter = self.lfilter_check.isChecked()
        setacv = self.setacv_combo.currentText()

        # Start measurement thread with mode parameters
        self.measurement_thread = MeasurementThread(
            resource_name, num_measurements, measurement_type, 
            gate_time_sec, auto_zero, range_cmd_val,
            mode=self.measurement_mode,
            nplc=nplc_value,
            digits=digits,
            offset_comp=offset_comp,
            acband_enabled=acband_enabled, 
            acband_value=acband_value, 
            lfilter=lfilter, 
            setacv=setacv,
            sniffing=sniffing_value
        )
        self.measurement_thread.measurement_ready.connect(self.on_measurement_ready)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        self.measurement_thread.start()
        
        self.status_bar.showMessage("🔄 Measurement in progress...")
    
    def stop_measurement(self):
        """Stop ongoing measurement"""
        if self.measurement_thread:
            self.measurement_thread.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_bar.showMessage("⏹️ Measurement stopped by user")
    
    def format_value_with_unit(self, value, base_unit):
        """Format value with appropriate unit scaling
        
        Args:
            value: Raw measurement value
            base_unit: Base unit ('V', 'A', 'Ω', 'Hz')
            
        Returns:
            tuple: (scaled_value, display_unit)
        """
        scale_factor = 1.0
        disp_unit = base_unit
        
        # Voltage scaling
        if base_unit == "V":
            if abs(value) < 1.0:
                scale_factor = 1000.0
                disp_unit = "mV"
        
        # Resistance scaling (Ω → kΩ → MΩ → GΩ)
        elif base_unit == "Ω":
            if abs(value) >= 1e9:
                scale_factor = 1e-9
                disp_unit = "GΩ"
            elif abs(value) >= 1e6:
                scale_factor = 1e-6
                disp_unit = "MΩ"
            elif abs(value) >= 1e3:
                scale_factor = 1e-3
                disp_unit = "kΩ"
        
        # Current scaling (optional: can add nA, µA, mA, A)
        # Frequency scaling (optional: can add kHz, MHz, GHz)
        
        scaled_value = value * scale_factor
        return scaled_value, disp_unit
    
    def format_value_with_unit_for_csv(self, value, base_unit):
        """Format value with text units for CSV/Excel compatibility
        
        Args:
            value: Raw measurement value
            base_unit: Base unit ('V', 'A', 'Ω', 'Hz')
            
        Returns:
            tuple: (scaled_value, display_unit)
        """
        scale_factor = 1.0
        disp_unit = base_unit
        
        # Voltage scaling
        if base_unit == "V":
            if abs(value) < 1.0:
                scale_factor = 1000.0
                disp_unit = "mV"
        
        # Resistance scaling (ohm → kohm → Mohm → Gohm) for CSV
        elif base_unit == "Ω":
            if abs(value) >= 1e9:
                scale_factor = 1e-9
                disp_unit = "Gohm"
            elif abs(value) >= 1e6:
                scale_factor = 1e-6
                disp_unit = "Mohm"
            elif abs(value) >= 1e3:
                scale_factor = 1e-3
                disp_unit = "kohm"
            else:
                disp_unit = "ohm"
        
        # Current scaling (optional)
        # Frequency scaling (optional)
        
        scaled_value = value * scale_factor
        return scaled_value, disp_unit
    
    def on_measurement_ready(self, value, measurement_num, timestamp):
        """Handle new measurement data"""
        self.all_measurements.append((value, timestamp))
        self.progress_bar.setValue(measurement_num)
        
        # Auto-scaling with helper function
        scaled_value, disp_unit = self.format_value_with_unit(value, self.current_unit)
        
        # Use fixed decimal format to show normal decimal numbers (not scientific notation)
        self.results_text.append(f"#{measurement_num} [{timestamp}]: {scaled_value:.8f} {disp_unit}")
        
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.add_measurement(value) # Pass raw, PlotCanvas handles display logic

    def on_mode_changed(self, mode_text):
        """Handle sampling mode changes"""
        pass
        # "Integration", "NPLC"
        if mode_text == "Integration":
            self.gate_time_spin.setVisible(True)
            self.nplc_spin.setVisible(False)
            self.gate_time_spin.setEnabled(True)
            self.nplc_spin.setEnabled(False)
            self.time_unit_combo.setVisible(True)
            self.time_unit_combo.setEnabled(True)
            
            self.integ_label.setVisible(True)
            self.nplc_label.setVisible(False)
            
            self.measurement_mode = "Integration"
        elif mode_text == "NPLC":
            self.gate_time_spin.setVisible(False)
            self.nplc_spin.setVisible(True)
            self.gate_time_spin.setEnabled(False)
            self.nplc_spin.setEnabled(True)
            self.time_unit_combo.setVisible(False)
            self.time_unit_combo.setEnabled(False)
            self.integ_label.setVisible(False)
            self.nplc_label.setVisible(True)
            
            self.measurement_mode = "NPLC"

    def toggle_time_input(self, checked):
        """Toggle time input (legacy support, redirects to on_mode_changed logic if needed)"""
        pass

    def toggle_acband_input(self, checked):
        """Toggle AC Bandwidth input with disable style"""
        self.acband_spin.setEnabled(checked)
        
        if checked:
            # Enable style - normal colors
            self.acband_spin.setStyleSheet(self.get_spinbox_style())
            # Set default value when enabling
            if self.acband_spin.value() == 0:
                self.acband_spin.setValue(10)
        else:
            # Disable style - gray colors
            self.acband_spin.setStyleSheet(self.get_disabled_spinbox_style())
            # Reset to 0 to show "Disable" text
            self.acband_spin.setValue(0)
    
    def on_measurement_complete(self, measurements):
        """Handle measurement completion"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if measurements:
            # Determine scaling based on average (extract values from tuples)
            values = [m[0] for m in measurements]
            avg_raw = sum(values) / len(values)
            
            # Use helper function for automatic unit scaling
            avg_scaled, scale_unit = self.format_value_with_unit(avg_raw, self.current_unit)
            
            # Get scale factor for other stats
            scale_factor = avg_scaled / avg_raw if avg_raw != 0 else 1.0
            
            # Scale stats
            min_val = min(values) * scale_factor
            max_val = max(values) * scale_factor
            
            variance = sum((x - avg_raw) ** 2 for x in values) / (len(values) - 1) if len(values) > 1 else 0
            std_dev = (variance ** 0.5) * scale_factor
            
            self.results_text.append("\n" + "="*50)
            self.results_text.append("📊 STATISTICS")
            self.results_text.append("="*50)
            self.results_text.append(f"Average:        {avg_scaled:.8f} {scale_unit}")
            self.results_text.append(f"Std Deviation:  {std_dev:.8f} {scale_unit}")
            self.results_text.append(f"Min:            {min_val:.8f} {scale_unit}")
            self.results_text.append(f"Max:            {max_val:.8f} {scale_unit}")
            self.results_text.append(f"Range:          {(max_val - min_val):.8f} {scale_unit}")
            
            self.status_bar.showMessage(f"✅ Measurement complete - Avg: {avg_scaled:.6f} {scale_unit}")
            
            # Auto-save
            self.auto_save_and_open_csv()
    
    def on_error(self, error_message):
        """Handle measurement errors"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        QMessageBox.critical(self, "Measurement Error", f"❌ Error:\n{error_message}")
        self.status_bar.showMessage("❌ Measurement error occurred")
    
    def clear_results(self):
        """Clear all results"""
        self.results_text.clear()
        self.all_measurements = []
        self.progress_bar.setValue(0)
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.clear_measurements()
        self.status_bar.showMessage("🗑️ Results cleared")
    
    def execute_math_null(self):
        """Execute MATH NULL to zero out cable lead offset"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Installed",
                              "PyVISA is required for this operation.")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource Selected",
                              "Please select a VISA resource first.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource_name)
            inst.timeout = 30000  # Increase timeout to 30 seconds
            
            self.status_bar.showMessage("🔄 Executing Math Null...")
            
            # Clear previous results and show header
            self.results_text.clear()
            self.results_text.append("🔄 Math NULL - Test Readings")
            self.results_text.append("=" * 40)
            
            # Reset and setup instrument for null
            inst.write("TARM HOLD")  # Hold trigger arm
            inst.write("TRIG HOLD")  # Hold trigger
            time.sleep(0.2)
            
            # Enable NULL function - takes current reading as offset
            inst.write("MATH NULL")
            time.sleep(1.0)  # Wait longer for null to apply
            
            self.results_text.append("✅ Math NULL command sent")
            self.results_text.append("")
            self.results_text.append("📊 Test Readings (should be near zero):")
            
            # Take 2 test readings to verify null worked
            for i in range(2):
                # Trigger single reading and query
                inst.write("TARM SGL")  # Single trigger arm
                time.sleep(0.5)
                try:
                    response = inst.read().strip()
                    value = float(response)
                    # Format with unit
                    scaled_value, unit = self.format_value_with_unit(value, self.current_unit)
                    self.results_text.append(f"  Reading {i+1}: {scaled_value:.6f} {unit}")
                except Exception as read_err:
                    self.results_text.append(f"  Reading {i+1}: Error - {str(read_err)}")
            
            # Restore trigger mode
            inst.write("TARM AUTO")
            
            inst.close()
            
            self.results_text.append("")
            self.results_text.append("=" * 40)
            self.results_text.append("✅ Math Null completed successfully")
            
            self.status_bar.showMessage("🔄 Math Null completed - see Measurement Results")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ Math Null failed: {str(e)}")
            self.results_text.append(f"\n❌ Error: {str(e)}")
    
    def execute_zero(self):
        """Execute AZERO (Auto-Zero) for current range only"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Installed",
                              "PyVISA is required for this operation.")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource Selected",
                              "Please select a VISA resource first.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(resource_name)
            inst.timeout = 30000
            
            self.status_bar.showMessage("⚖️ Executing Zero for current range...")
            
            # Clear previous results and show header
            self.results_text.clear()
            self.results_text.append("⚖️ Zero - Current Range Calibration")
            self.results_text.append("=" * 40)
            
            # Get current range info
            current_range = self.range_combo.currentText() if hasattr(self, 'range_combo') else "Auto"
            self.results_text.append(f"📍 Current Range: {current_range}")
            
            # Get NPLC setting
            nplc_value = self.nplc_spin.value() if hasattr(self, 'nplc_spin') else 100.0
            self.results_text.append(f"⏱️ NPLC: {nplc_value}")
            inst.write(f"NPLC {nplc_value}")
            time.sleep(0.2)
            
            # Get NDIG setting
            ndig_value = self.digit_combo.currentText() if hasattr(self, 'digit_combo') else "8"
            self.results_text.append(f"🔢 NDIG: {ndig_value}")
            inst.write(f"NDIG {ndig_value}")
            time.sleep(0.2)
            
            # Check Offset Comp setting
            offset_comp_enabled = self.offset_comp_check.isChecked() if hasattr(self, 'offset_comp_check') else False
            if offset_comp_enabled:
                self.results_text.append("🔧 Offset Compensation: Enabled")
                inst.write("OCOMP ON")  # Enable offset compensation
                time.sleep(0.5)
            else:
                self.results_text.append("🔧 Offset Compensation: Disabled")
            
            self.results_text.append("")
            
            # Perform Auto-Zero for current range
            inst.write("AZERO ONCE")  # Single auto-zero
            time.sleep(2.0)  # Wait for zero to complete
            
            self.results_text.append("✅ AZERO ONCE command sent")
            self.results_text.append(f"✅ NPLC {nplc_value} applied")
            self.results_text.append(f"✅ NDIG {ndig_value} applied")
            if offset_comp_enabled:
                self.results_text.append("✅ OCOMP ON applied")
            self.results_text.append("")
            self.results_text.append("📊 Test Readings after Zero:")


            
            # Take 2 test readings to verify zero worked
            for i in range(2):
                inst.write("TARM SGL")
                time.sleep(0.5)
                try:
                    response = inst.read().strip()
                    value = float(response)
                    scaled_value, unit = self.format_value_with_unit(value, self.current_unit)
                    self.results_text.append(f"  Reading {i+1}: {scaled_value:.6f} {unit}")
                except Exception as read_err:
                    self.results_text.append(f"  Reading {i+1}: Error - {str(read_err)}")
            
            inst.write("TARM AUTO")
            inst.close()
            
            self.results_text.append("")
            self.results_text.append("=" * 40)
            self.results_text.append("✅ Zero completed successfully")
            
            self.status_bar.showMessage("⚖️ Zero completed - see Measurement Results")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ Zero failed: {str(e)}")
            self.results_text.append(f"\n❌ Error: {str(e)}")
    
    def auto_save_and_open_csv(self):


        """Automatically save and open CSV after measurement completes"""
        if self.all_measurements:
            self.save_and_open_csv()
    
    def save_and_open_csv(self):
        """Save measurements to latest_output.csv and open it automatically"""
        if not self.all_measurements:
            QMessageBox.warning(self, "No Data", "No measurements to save!")
            return
        
        try:
            import subprocess
            import os
            
            # Create output directory relative to this script's location
            script_dir = Path(__file__).parent
            output_dir = script_dir / "Measurement_Results"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = output_dir / "latest_output.csv"
            
            # Write CSV with retry
            max_retries = 3
            for attempt in range(max_retries):
                # Try to force close Excel before writing
                if os.name == 'nt':
                    try:
                        self.results_text.append(f"🔄 Attempting to close Excel (Try {attempt+1})...")
                        # Use PowerShell for more reliable process finding/killing
                        ps_cmd = "Get-Process | Where-Object {$_.MainWindowTitle -like '*latest_output*'} | Stop-Process -Force -PassThru"
                        result = subprocess.run(["powershell", "-Command", ps_cmd], capture_output=True, text=True)
                        
                        if result.stdout.strip():
                             self.results_text.append(f"✅ Killed process: {result.stdout.strip()}")
                        
                        time.sleep(1.0) # Wait longer for handle release
                    except Exception as e:
                        self.results_text.append(f"⚠️ Kill failed: {str(e)}")

                try:
                    with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                        self.write_csv_content(csvfile)
                    
                    # Open file
                    try:
                        self.results_text.append(f"📂 Attempting to open: {filename}")
                        if os.name == 'nt':
                            os.startfile(filename)
                        elif sys.platform == 'darwin':
                            subprocess.run(['open', filename])
                        else:
                            subprocess.run(['xdg-open', filename])
                        self.results_text.append("✅ File open command sent.")
                    except Exception as e:
                        self.results_text.append(f"❌ Failed to open file: {str(e)}")
                    
                    self.status_bar.showMessage(f"💾 Saved and opened: {filename}")
                    self.results_text.append(f"\n💾 Data saved to: {filename}")
                    self.results_text.append(f"📂 File opened automatically\n")
                    break
                    
                except PermissionError:
                    if attempt < max_retries - 1:
                        import time
                        time.sleep(0.5)
                        continue
                    else:
                        QMessageBox.critical(self, "Save Error", 
                                           "Failed to save file (file is locked by Excel).\nPlease close 'latest_output.csv' and try again.")
                        
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{str(e)}")

    def write_csv_content(self, csvfile):
        """Helper to write CSV content (Horizontal Format + Unit at End)"""
        writer = csv.writer(csvfile)
        now = datetime.now()
        
        if not self.all_measurements:
            return

        # 1. Extract values from (value, timestamp) tuples
        values = [m[0] for m in self.all_measurements]
        
        # Calculate Global Scaling based on Average using CSV-specific helper function
        avg_raw = sum(values) / len(values)
        avg_scaled, scale_unit = self.format_value_with_unit_for_csv(avg_raw, self.current_unit)
        scale_factor = avg_scaled / avg_raw if avg_raw != 0 else 1.0

        # 2. Horizontal Layout
        
        # Row 1: Measurement numbers
        measurement_numbers = ['Measurement'] + [str(i) for i in range(1, len(values) + 1)]
        writer.writerow(measurement_numbers)

        # Row 2: Values (Scaled)
        scaled_values = []
        for raw_val in values:
            scaled_val = raw_val * scale_factor
            scaled_values.append(f'{scaled_val:.8g}')
            
        # Append Unit at the end
        values_row = ['Value'] + scaled_values + [scale_unit]
        writer.writerow(values_row)
        
        # Row 3: Date
        date_row = ['Date', now.strftime('%Y-%m-%d')] + [''] * (len(values) - 1)
        writer.writerow(date_row)
        
        # Row 4: Time
        time_row = ['Time', now.strftime('%H:%M:%S')] + [''] * (len(values) - 1)
        writer.writerow(time_row)
        
        writer.writerow([])
        
        # Statistics (using extracted values)
        avg = avg_raw * scale_factor
        min_val = min(values) * scale_factor
        max_val = max(values) * scale_factor
        
        if len(values) > 1:
            variance = sum((x - avg_raw) ** 2 for x in values) / (len(values) - 1)
            std_dev_raw = variance ** 0.5
            std_dev = std_dev_raw * scale_factor
        else:
            std_dev = 0
            
        writer.writerow(['Statistics', 'Average', 'Minimum', 'Maximum', 'Std Deviation'])
        writer.writerow(['', f'{avg:.8g}', f'{min_val:.8g}', f'{max_val:.8g}', f'{std_dev:.8g}', scale_unit])
        
        writer.writerow([])
        selected_button = self.type_group.checkedButton()
        if selected_button:
            # Remove emoji from measurement type for CSV
            measurement_type_text = selected_button.text()
            # Remove emoji by splitting and taking the text part after the emoji
            parts = measurement_type_text.split()
            if len(parts) > 1:
                # Remove first part (emoji) and join the rest
                clean_text = " ".join(parts[1:])
            else:
                clean_text = measurement_type_text
            writer.writerow(['Measurement Type', clean_text])
        

def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    app.setStyle('Fusion')
    
    window = HP3458MultimeterGUI()
    window.showMaximized()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
