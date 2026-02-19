"""
Fluke 8508A Reference Multimeter GUI Application
A modern PyQt6-based GUI for controlling and monitoring Fluke 8508A 8.5-digit Reference Multimeter
Based on HP 3458A GUI structure, simplified for Fluke 8508 procedure functions
"""

import sys
import csv
import time
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QComboBox, QSpinBox, QDoubleSpinBox,
    QGroupBox, QTextEdit, QProgressBar, QMessageBox, QRadioButton,
    QButtonGroup, QStatusBar, QCheckBox, QScrollArea, QFrame,
    QGridLayout, QLayout, QLayoutItem, QSizePolicy
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRect, QSize, QPoint, QLocale
from PyQt6.QtGui import QFont

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
        self.setContentsMargins(margin, margin, margin, margin)
        self.setSpacing(spacing if spacing >= 0 else 5)
    
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
        x = rect.x()
        y = rect.y()
        lineHeight = 0
        spacing = self.spacing()
        
        for item in self._items:
            wid = item.widget()
            spaceX = spacing
            spaceY = spacing
            
            nextX = x + item.sizeHint().width() + spaceX
            if nextX - spaceX > rect.right() and lineHeight > 0:
                x = rect.x()
                y = y + lineHeight + spaceY
                nextX = x + item.sizeHint().width() + spaceX
                lineHeight = 0
            
            if not testOnly:
                item.setGeometry(QRect(QPoint(x, y), item.sizeHint()))
            
            x = nextX
            lineHeight = max(lineHeight, item.sizeHint().height())
        
        return y + lineHeight - rect.y()


class MeasurementThread(QThread):
    """Thread for performing measurements without blocking the UI"""
    measurement_ready = pyqtSignal(float, int, str)  # value, number, timestamp
    measurement_complete = pyqtSignal(list)
    error_occurred = pyqtSignal(str)
    
    def __init__(self, resource_name, num_measurements, measurement_type, gate_time, auto_zero,
                 range_val="AUTO", mode="Integration", digits=8, fourw_mode=0,
                 offset_comp=False, fast=False, filt=False, sniffing=0):
        super().__init__()
        self.resource_name = resource_name
        self.num_measurements = num_measurements
        self.measurement_type = measurement_type
        self.gate_time = gate_time
        self.auto_zero = auto_zero
        self.range_val = range_val
        self.mode = mode
        self.digits = digits
        self.fourw_mode = fourw_mode  # 0=Normal 4W, 1=True OHMS, 2=HV OHMS
        self.offset_comp = offset_comp
        self.fast = fast
        self.filt = filt
        self.sniffing = sniffing  # Time in seconds to wait before recording each value (0 = disabled)
        self.is_running = True
        self.measurements = []  # List of (value, timestamp) tuples
    
    def _parse_8508_value(self, value_str):
        """Parse Fluke 8508A response string to extract numeric value"""
        value_str = value_str.strip()
        # Try to extract numeric value from possibly mixed response
        parts = value_str.replace(',', ' ').split()
        for part in parts:
            try:
                return float(part)
            except ValueError:
                continue
        # If no numeric part found, try the whole string
        return float(value_str)
    
    def _query_measurement(self, instrument):
        """Query a single measurement from Fluke 8508A with fallbacks"""
        # Method 1: Use "?" query - this is the standard Fluke 8508A way
        try:
            value_str = instrument.query("?")
            print(f"DEBUG: Received raw value: {value_str}")
            return self._parse_8508_value(value_str)
        except Exception as e:
            print(f"DEBUG: '?' query failed: {e}")
        
        # Method 2: Fallback to READ?
        try:
            value_str = instrument.query("READ?")
            print(f"DEBUG: READ? raw value: {value_str}")
            return self._parse_8508_value(value_str)
        except Exception as e2:
            print(f"DEBUG: 'READ?' query failed: {e2}")
        
        # Method 3: *TRG + read
        try:
            instrument.write("*TRG")
            time.sleep(0.5)
            value_str = instrument.read()
            print(f"DEBUG: *TRG+read raw value: {value_str}")
            return self._parse_8508_value(value_str)
        except Exception as e3:
            print(f"DEBUG: All read attempts failed: {e3}")
            raise e3
    
    def _setup_function_and_range(self, instrument):
        """Set measurement function and range on Fluke 8508A"""
        # Fluke 8508A commands per manual pages 4-13 to 4-15:
        # - Normal OHMS: OHMS command with TWO_WR or FOUR_WR option
        # - True OHMS: TRUE_OHMS command (always 4-wire)
        # - High Voltage OHMS: HIV_OHMS command
        
        func_map = {
            "DCV": "DCV", "ACV": "ACV", "DCI": "DCI", "ACI": "ACI",
            "OHMS": "OHMS", "TOHMS": "OHMS",
        }
        func_cmd = func_map.get(self.measurement_type, "DCV")
        
        print(f"DEBUG: Measurement Type = {self.measurement_type}")
        print(f"DEBUG: Function Command = {func_cmd}")
        print(f"DEBUG: Range Value = {self.range_val}")
        print(f"DEBUG: 4W Mode = {self.fourw_mode} (0=Normal 4W, 1=True OHMS, 2=HV OHMS)")
        
        if self.measurement_type == "TOHMS":
            if self.fourw_mode == 1:  # True OHMS mode
                if self.range_val == "AUTO":
                    instrument.write("TRUE_OHMS")
                    time.sleep(0.2)
                    instrument.write("AUTO")
                else:
                    instrument.write(f"TRUE_OHMS {self.range_val}")
            elif self.fourw_mode == 2:  # High Voltage OHMS mode
                if self.range_val == "AUTO":
                    instrument.write("HIV_OHMS 1E6")
                    time.sleep(0.5)
                    instrument.write("AUTO")
                else:
                    instrument.write(f"HIV_OHMS {self.range_val}")
            else:  # Normal 4-Wire OHMS mode (fourw_mode == 0)
                if self.range_val == "AUTO":
                    instrument.write("OHMS")
                    time.sleep(0.2)
                    instrument.write("AUTO")
                else:
                    instrument.write(f"OHMS {self.range_val}")
                time.sleep(0.3)
                instrument.write("FOUR_WR")
        elif self.measurement_type == "OHMS":
            # 2-Wire OHMS
            if self.range_val == "AUTO":
                instrument.write("OHMS")
                time.sleep(0.5)
                instrument.write("AUTO")
            else:
                instrument.write(f"OHMS {self.range_val}")
            time.sleep(0.3)
            instrument.write("TWO_WR")
        else:
            # Other measurement types (DCV, ACV, DCI, ACI)
            if self.range_val == "AUTO":
                instrument.write(func_cmd)
                time.sleep(0.2)
                instrument.write("AUTO")
            else:
                instrument.write(f"{func_cmd} {self.range_val}")
        time.sleep(0.3)
    
    def run(self):
        """Execute measurements in background thread"""
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(self.resource_name)
            
            # 1. Set appropriate timeout based on mode
            if self.mode == "NPLC":
                timeout_ms = 60000 + (self.digits * 5000)
            else:
                timeout_ms = 60000 + int(self.gate_time * 1000)
            instrument.timeout = timeout_ms
            
            # 2. Set termination characters for Fluke 8508A
            instrument.read_termination = '\n'
            instrument.write_termination = '\n'
            
            # 3. Reset and Clear
            instrument.write("*RST")
            time.sleep(2.0)
            instrument.write("*CLS")
            time.sleep(0.3)
            
            # 4. Set Measurement Function and Range
            self._setup_function_and_range(instrument)
            
            # 5. Set Auto-Zero
            instrument.write(f"AZERO {'ON' if self.auto_zero else 'OFF'}")
            time.sleep(0.1)
            
            # 6. Set Resolution (NDIG)
            instrument.write(f"NDIG {int(self.digits)}")
            time.sleep(0.1)
            
            # 7. Set Offset Compensation
            if self.offset_comp:
                instrument.write("OCOMP ON")
                print("DEBUG: Offset Compensation ON")
            time.sleep(0.1)
            
            # 8. Set FAST and FILT speed modes
            try:
                instrument.write("FAST_ON" if self.fast else "FAST_OFF")
                print(f"DEBUG: FAST {'ON' if self.fast else 'OFF'}")
            except Exception as e:
                print(f"DEBUG: Failed to set FAST mode: {e}")
            time.sleep(0.1)
            
            try:
                instrument.write("FILT_ON" if self.filt else "FILT_OFF")
                print(f"DEBUG: FILT {'ON' if self.filt else 'OFF'}")
            except Exception as e:
                print(f"DEBUG: Failed to set FILT mode: {e}")
            time.sleep(0.1)
            
            # 9. Configure triggering for Fluke 8508A
            instrument.write("EXTRIG OFF")
            instrument.write("TBUFF OFF")
            time.sleep(0.3)
            
            # 10. Configure based on mode and take measurements
            if self.mode == "NPLC":
                # NPLC Mode with optional Sniffing (time delay before each record)
                if self.sniffing > 0:
                    print(f"DEBUG: NPLC Mode with Sniffing - Sniffing = {self.sniffing}s per sample")
                else:
                    print(f"DEBUG: NPLC Mode (no sniffing delay)")
                
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
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        value = self._query_measurement(instrument)
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        self.measurements.append((value, timestamp))
                    except Exception as e:
                        print(f"DEBUG: Error reading value: {e}")
                        self.error_occurred.emit(str(e))
                        break
                    
                    t_end = time.time()
                    if self.sniffing > 0:
                        print(f"DEBUG: Sample #{i+1} took {t_end - t_start:.2f}s (Sniffing={self.sniffing}s)")
                    else:
                        print(f"DEBUG: Sample #{i+1} took {t_end - t_start:.2f}s (NPLC only)")
            
            else:  # Integration Mode (default)
                # Integration Mode - Software-controlled time intervals
                print(f"DEBUG: Integration Mode - Using time-interval sampling: {self.gate_time}s per sample")
                
                # Perform time-interval measurements
                for i in range(self.num_measurements):
                    if not self.is_running:
                        break
                    
                    # Wait for the specified interval BEFORE each measurement (including first)
                    print(f"DEBUG: Waiting {self.gate_time}s before sample #{i+1}...")
                    time.sleep(self.gate_time)
                    
                    t_start = time.time()
                    try:
                        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                        value = self._query_measurement(instrument)
                        self.measurement_ready.emit(value, i + 1, timestamp)
                        self.measurements.append((value, timestamp))
                    except Exception as e:
                        print(f"DEBUG: Error reading value: {e}")
                        self.error_occurred.emit(str(e))
                        break
                    
                    t_end = time.time()
                    print(f"DEBUG: Sample #{i+1} took {t_end - t_start:.2f}s (read time)")

            # End of loop
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


class Fluke8508MultimeterGUI(QMainWindow):
    """Main GUI window for Fluke 8508A Reference Multimeter application"""
    
    def __init__(self):
        super().__init__()
        self.measurement_thread = None
        self.all_measurements = []
        self.current_unit = "V"
        self.measurement_mode = None  # "Integration" or "NPLC"
        
        # Range definitions (Label, Unit, SCPI Value)
        self.range_map = {
            "DCV": [
                ("Auto", "V", "AUTO"),
                ("200mV", "V", "0.02"),
                ("2 V", "V", "0.2"),  
                ("20 V", "V", "2"),
                ("200 V", "V", "20"),
                ("1000 V", "V", "200"),

            ],
            "ACV": [
                ("Auto", "V", "AUTO"),
                ("200mV", "V", "0.02"),
                ("2 V", "V", "0.2"),
                ("20 V", "V", "2"),
                ("200 V", "V", "20"),
                ("1000 V", "V", "200"),
                
            ],
            "DCI": [
                ("Auto", "A", "AUTO"),
                ("200 µA", "A", "0.00002"),
                ("2 mA", "A", "0.0002"),
                ("20 mA", "A", "0.002"),
                ("200 mA", "A", "0.02"),
                ("2 A", "A", "0.2"),
                ("20 A", "A", "2"),
                ("20 A", "A", "20")
            ],
            "ACI": [
                ("Auto", "A", "AUTO"),
                ("200 µA", "A", "0.00002"),
                ("2 mA", "A", "0.0002"),
                ("20 mA", "A", "0.002"),
                ("200 mA", "A", "0.02"),
                ("2 A", "A", "0.2"),
                ("20 A", "A", "2")
            ],
            "OHMS": [
                ("Auto", "Ω", "AUTO"),
                ("2 Ω", "Ω", "0.2"),
                ("20 Ω", "Ω", "2"),
                ("200 Ω", "Ω", "20"),
                ("2 kΩ", "Ω", "200"),
                ("20 kΩ", "Ω", "2000"),
                ("200 kΩ", "Ω", "20000"),
                ("2 MΩ", "Ω", "200000"),
                ("20 MΩ", "Ω", "2000000"),
                ("200 MΩ", "Ω", "20000000"),
                ("20 GΩ", "Ω", "2000000000")
            ],
            "TOHMS": [
                ("Auto", "Ω", "AUTO"),
                ("2 Ω", "Ω", "0.2"),
                ("20 Ω", "Ω", "2"),
                ("200 Ω", "Ω", "20"),
                ("2 kΩ", "Ω", "200"),
                ("20 kΩ", "Ω", "2000"),
                ("200 kΩ", "Ω", "20000"),
                ("2 MΩ", "Ω", "200000"),
                ("20 MΩ", "Ω", "2000000"),
                ("200 MΩ", "Ω", "20000000"),
                ("20 GΩ", "Ω", "2000000000")
            ]
        }
        
        # Resolution definitions per function (according to Fluke 8508A specification)
        # DCV: 5.5 - 8.5 digits
        # ACV: 5.5 - 6.5 digits
        # DCI: 5.5 - 7.5 digits
        # ACI: 5.5 - 6.5 digits
        # Resistance (OHMS/TOHMS): 5.5 - 8.5 digits
        self.resolution_map = {
            "DCV": ["5.5", "6.5", "7.5", "8.5"],
            "ACV": ["5.5", "6.5"],
            "DCI": ["5.5", "6.5", "7.5"],
            "ACI": ["5.5", "6.5"],
            "OHMS": ["5.5", "6.5", "7.5", "8.5"],
            "TOHMS": ["5.5", "6.5", "7.5", "8.5"]
        }
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Fluke 8508A Reference Multimeter Control Panel")
        
        # Fixed full screen size
        self.setGeometry(0, 0, 1920, 1080)
        
        # Set light theme
        self.set_light_theme()
        
        # Create central widget and main scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_box = QVBoxLayout(central_widget)
        main_box.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Scrollbar styling
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
        
        # Content Widget inside Scroll Area
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📟 Fluke 8508A Reference Multimeter Control Panel")
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
            self.plot_canvas.setMinimumHeight(400)
            graph_layout.addWidget(self.plot_canvas)
            graph_group.setLayout(graph_layout)
            results_layout.addWidget(graph_group, 2)
        
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
        self.status_bar.showMessage("✨ Ready - Fluke 8508A Reference Multimeter Control")
        
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
        
        # VISA Resource
        visa_label = QLabel("VISA Resource:")
        visa_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(visa_label)
        
        self.resource_combo = QComboBox()
        self.resource_combo.setFont(QFont("Segoe UI", 10))
        self.resource_combo.setStyleSheet(self.get_input_style())
        self.resource_combo.setEditable(True)
        self.resource_combo.addItem("GPIB0::6::INSTR")  # Default for Fluke 8508
        layout.addWidget(self.resource_combo, 1)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        refresh_btn.setStyleSheet(self.get_button_style("#9334e9"))
        refresh_btn.clicked.connect(self.refresh_resources)
        layout.addWidget(refresh_btn)
        
        # Test connection button
        test_btn = QPushButton("🔍 Test Connection")
        test_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
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
        
        # Measurement types (Fluke 8508 - no Frequency)
        types = [
            ("⚡ DC Voltage", "DCV", "V"),
            ("〜 AC Voltage", "ACV", "V"),
            ("⚡ DC Current", "DCI", "A"),
            ("〜 AC Current", "ACI", "A"),
            ("🔧 2W Ω", "OHMS", "Ω"),
            ("🔧 4W Ω", "TOHMS", "Ω"),
        ]
        
        for i, (label, type_name, unit) in enumerate(types):
            radio = QRadioButton(label)
            radio.setFont(QFont("Segoe UI", 10))
            radio.setStyleSheet("""
                QRadioButton {
                    color: #3c4043;
                    spacing: 8px;
                }
                QRadioButton:disabled {
                    color: #9aa0a6;
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
                QRadioButton::indicator:disabled {
                    border: 2px solid #e0e0e0;
                    background-color: #f5f5f5;
                }
            """)
            radio.toggled.connect(lambda checked, t=type_name, u=unit: self.on_type_changed(checked, t, u))
            self.type_group.addButton(radio, i)
            
            # Disable 2W OHMS button
            if type_name == "OHMS":
                radio.setEnabled(False)
            
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
        
        # Number of Measurements (Container)
        num_container = QWidget()
        num_layout = QHBoxLayout(num_container)
        num_layout.setContentsMargins(0, 0, 0, 0)
        num_layout.setSpacing(5)
        
        num_label = QLabel("Number of Measurements:")
        num_label.setFont(QFont("Segoe UI", 10))
        num_layout.addWidget(num_label)
        
        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setRange(1, 1000000)
        self.num_measurements_spin.setValue(10)
        self.num_measurements_spin.setFont(QFont("Segoe UI", 10))
        self.num_measurements_spin.setStyleSheet(self.get_spinbox_style())
        self.num_measurements_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        num_layout.addWidget(self.num_measurements_spin)
        
        row0_layout.addWidget(num_container)
        
        # Sampling Mode (Container)
        mode_container = QWidget()
        mode_layout = QHBoxLayout(mode_container)
        mode_layout.setContentsMargins(0, 0, 0, 0)
        mode_layout.setSpacing(5)
        
        mode_label = QLabel("Sampling Mode:")
        mode_label.setFont(QFont("Segoe UI", 10))
        mode_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setFont(QFont("Segoe UI", 10))
        self.mode_combo.setStyleSheet(self.get_input_style())
        self.mode_combo.addItems(["-- Select Mode --", "Integration", "NPLC"])
        mode_layout.addWidget(self.mode_combo)
        
        row0_layout.addWidget(mode_container)
        
        # Note: NPLC mode uses NDIG (Resolution) for Fluke 8508A via RESL command
        # No separate NPLC spinbox needed - resolution is controlled by NDIG setting
        
        # Sniffing Container (Checkbox + Spinbox + Unit Dropdown) - for NPLC mode
        self.sniffing_container = QWidget()
        sniffing_layout = QHBoxLayout(self.sniffing_container)
        sniffing_layout.setContentsMargins(0, 0, 0, 0)
        sniffing_layout.setSpacing(5)
        
        # Sniffing Enable Checkbox
        self.sniffing_enable_check = QCheckBox("Sniffing:")
        self.sniffing_enable_check.setFont(QFont("Segoe UI", 10))
        self.sniffing_enable_check.setStyleSheet(self.get_checkbox_style())
        self.sniffing_enable_check.toggled.connect(self.toggle_sniffing_input)
        sniffing_layout.addWidget(self.sniffing_enable_check)
        
        # Sniffing Interval Spinbox
        self.sniffing_spin = QDoubleSpinBox()
        self.sniffing_spin.setRange(0, 99999.0)
        self.sniffing_spin.setValue(0)
        self.sniffing_spin.setDecimals(2)
        self.sniffing_spin.setSpecialValueText("Disable")
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
        
        # NDIG (Container)
        ndig_container = QWidget()
        ndig_layout = QHBoxLayout(ndig_container)
        ndig_layout.setContentsMargins(0, 0, 0, 0)
        ndig_layout.setSpacing(5)
        
        digits_label = QLabel("NDIG:")
        digits_label.setFont(QFont("Segoe UI", 10))
        ndig_layout.addWidget(digits_label)
        
        self.digit_combo = QComboBox()
        self.digit_combo.setFont(QFont("Segoe UI", 10))
        self.digit_combo.setStyleSheet(self.get_input_style())
        self.digit_combo.addItems(["5.5", "6.5", "7.5", "8.5"])  # Fluke 8508 format
        self.digit_combo.setCurrentIndex(3)  # Default 8.5
        ndig_layout.addWidget(self.digit_combo)
        
        row0_layout.addWidget(ndig_container)
        
        # Range (Container)
        range_container = QWidget()
        range_layout = QHBoxLayout(range_container)
        range_layout.setContentsMargins(0, 0, 0, 0)
        range_layout.setSpacing(5)
        
        range_label = QLabel("Range:")
        range_label.setFont(QFont("Segoe UI", 10))
        range_layout.addWidget(range_label)
        
        self.range_combo = QComboBox()
        self.range_combo.setFont(QFont("Segoe UI", 10))
        self.range_combo.setStyleSheet(self.get_input_style())
        # Initialize with DCV ranges as default
        for name, r_unit, cmd in self.range_map.get("DCV", []):
            self.range_combo.addItem(name, cmd)
        self.range_combo.currentTextChanged.connect(self.on_range_changed)
        range_layout.addWidget(self.range_combo)
        
        row0_layout.addWidget(range_container)
        
        # Auto Zero (Container for vertical and horizontal alignment)
        auto_zero_container = QWidget()
        auto_zero_layout = QHBoxLayout(auto_zero_container)
        auto_zero_layout.setContentsMargins(10, 10, 10, 10)
        auto_zero_layout.setSpacing(15)
        auto_zero_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.auto_zero_check = QCheckBox("Auto Zero")
        self.auto_zero_check.setFont(QFont("Segoe UI", 10))
        self.auto_zero_check.setChecked(True)
        self.auto_zero_check.setStyleSheet(self.get_checkbox_style())
        auto_zero_layout.addWidget(self.auto_zero_check)
        
        # Offset Comp checkbox (for resistance measurements)
        self.offset_comp_check = QCheckBox("Offset Comp")
        self.offset_comp_check.setFont(QFont("Segoe UI", 10))
        self.offset_comp_check.setChecked(False)
        self.offset_comp_check.setStyleSheet(self.get_checkbox_style())
        self.offset_comp_check.setToolTip("Enable Offset Compensation for DC Resistance")
        auto_zero_layout.addWidget(self.offset_comp_check)
        
        # Speed Mode Container (Disable, FILT, FAST, FILT+FAST)
        speed_mode_container = QWidget()
        speed_mode_container.setStyleSheet("""
            QWidget {
                background-color: #e3f2fd;
                border: 2px solid #2196f3;
                border-radius: 8px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #1565c0;
            }
            QRadioButton {
                background-color: transparent;
                border: none;
            }
        """)
        speed_mode_layout = QHBoxLayout(speed_mode_container)
        speed_mode_layout.setContentsMargins(10, 8, 10, 8)
        speed_mode_layout.setSpacing(10)
        
        speed_label = QLabel("Speed:")
        speed_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        speed_mode_layout.addWidget(speed_label)
        
        # Independent checkboxes for FILT and FAST
        self.filt_check = QCheckBox("Low Pass Filter")
        self.filt_check.setFont(QFont("Segoe UI", 9))
        self.filt_check.setStyleSheet(self.get_checkbox_style())
        self.filt_check.setToolTip("Enable Low Pass Filter")
        self.filt_check.stateChanged.connect(self.on_filt_changed)
        speed_mode_layout.addWidget(self.filt_check)
        
        self.fast_check = QCheckBox("Fast")
        self.fast_check.setFont(QFont("Segoe UI", 9))
        self.fast_check.setStyleSheet(self.get_checkbox_style())
        self.fast_check.setToolTip("Enable Fast Mode")
        self.fast_check.stateChanged.connect(self.on_fast_changed)
        speed_mode_layout.addWidget(self.fast_check)
        
        auto_zero_layout.addWidget(speed_mode_container)
        
        row0_layout.addWidget(auto_zero_container)
        
        # 4W Ohms Options Container (only visible when 4W Ω is selected)
        # According to 8508A manual pages 4-13 to 4-15:
        # - Normal 4W: OHMS + FOUR_WR
        # - True OHMS: TRUE_OHMS (always 4-wire)
        # - HV OHMS: HV_OHMS + FOUR_WR (High Voltage OHMS)
        self.fourw_options_container = QWidget()
        self.fourw_options_container.setStyleSheet("""
            QWidget {
                background-color: #e8f5e9;
                border: 2px solid #4caf50;
                border-radius: 8px;
            }
            QLabel {
                background-color: transparent;
                border: none;
                color: #2e7d32;
            }
            QRadioButton {
                background-color: transparent;
                border: none;
            }
        """)
        fourw_layout = QHBoxLayout(self.fourw_options_container)
        fourw_layout.setContentsMargins(10, 10, 10, 10)
        fourw_layout.setSpacing(12)
        
        fourw_label = QLabel("⚙️ 4W Mode:")
        fourw_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        fourw_layout.addWidget(fourw_label)
        
        # Radio button group for 4W mode selection
        # 0 = Normal 4W (OHMS + FOUR_WR)
        # 1 = True OHMS (TRUE_OHMS)
        # 2 = HV OHMS (HV_OHMS + FOUR_WR)
        self.fourw_mode_group = QButtonGroup()
        
        self.normal_4w_radio = QRadioButton("Normal 4W")
        self.normal_4w_radio.setFont(QFont("Segoe UI", 9))
        self.normal_4w_radio.setChecked(True)  # Default selection
        self.normal_4w_radio.setStyleSheet(self.get_radio_style())
        self.normal_4w_radio.setToolTip("Normal 4-Wire: OHMS + FOUR_WR command")
        self.fourw_mode_group.addButton(self.normal_4w_radio, 0)
        fourw_layout.addWidget(self.normal_4w_radio)
        
        self.true_ohms_radio = QRadioButton("True OHMS")
        self.true_ohms_radio.setFont(QFont("Segoe UI", 9))
        self.true_ohms_radio.setStyleSheet(self.get_radio_style())
        self.true_ohms_radio.setToolTip("True OHMS: TRUE_OHMS command (always 4-wire)")
        self.fourw_mode_group.addButton(self.true_ohms_radio, 1)
        fourw_layout.addWidget(self.true_ohms_radio)
        
        self.hv_ohms_radio = QRadioButton("HV OHMS")
        self.hv_ohms_radio.setFont(QFont("Segoe UI", 9))
        self.hv_ohms_radio.setStyleSheet(self.get_radio_style())
        self.hv_ohms_radio.setToolTip("High Voltage OHMS: HV_OHMS + FOUR_WR command")
        self.fourw_mode_group.addButton(self.hv_ohms_radio, 2)
        fourw_layout.addWidget(self.hv_ohms_radio)
        
        # Hide by default (only show when 4W Ω is selected)
        self.fourw_options_container.hide()
        
        row0_layout.addWidget(self.fourw_options_container)
        
        layout.addLayout(row0_layout)
        
        # Connect mode change signal AFTER all controls are created
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        # Connect 4W mode radio buttons to send commands immediately
        self.normal_4w_radio.toggled.connect(self.on_fourw_mode_changed)
        self.true_ohms_radio.toggled.connect(self.on_fourw_mode_changed)
        self.hv_ohms_radio.toggled.connect(self.on_fourw_mode_changed)
        
        group.setLayout(layout)
        return group
    
    def on_mode_changed(self, mode):
        """Handle mode change between Integration and NPLC mode"""
        self.measurement_mode = mode
        
        if mode == "-- Select Mode --" or not mode:
            self.measurement_mode = None
            if hasattr(self, 'time_container'):
                self.time_container.hide()
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.hide()
            
        elif mode == "Integration":
            # Show Integration/Time, Hide Sniffing
            if hasattr(self, 'time_container'):
                self.time_container.show()
                self.gate_time_spin.setEnabled(True)
                self.time_unit_combo.setEnabled(True)
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.hide()
            
        elif mode == "NPLC":
            # Hide Integration/Time, Show Sniffing
            # Note: Resolution is controlled via NDIG setting (sends RESL command)
            if hasattr(self, 'time_container'):
                self.time_container.hide()
            if hasattr(self, 'sniffing_container'):
                self.sniffing_container.show()
            
        # Force layout update
        if hasattr(self, 'time_container'):
            self.time_container.update()
            self.time_container.parentWidget().update()
    
    def toggle_sniffing_input(self, enabled):
        """Toggle sniffing input controls enabled/disabled"""
        self.sniffing_spin.setEnabled(enabled)
        self.sniffing_unit_combo.setEnabled(enabled)
        
        if enabled:
            self.sniffing_spin.setStyleSheet(self.get_spinbox_style())
            self.sniffing_unit_combo.setStyleSheet(self.get_input_style())
        else:
            self.sniffing_spin.setStyleSheet(self.get_disabled_spinbox_style())
            self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())
    
    def on_fourw_mode_changed(self, checked):
        """Handle 4W mode radio button change - send command to instrument immediately.
           This is a best-effort operation - silently ignores errors if instrument is not connected."""
        if not checked:  # Only act on the radio button being selected, not deselected
            return
            
        if not PYVISA_AVAILABLE:
            return
            
        # Check if we're in 4W mode
        selected_btn = self.type_group.checkedButton()
        if not selected_btn:
            return
        btn_id = self.type_group.id(selected_btn)
        if btn_id != 5:  # 5 = TOHMS (4W Ohm)
            return
            
        resource_name = self.resource_combo.currentText()
        if not resource_name or resource_name == "-- Select Resource --":
            return
            
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name, open_timeout=2000)
            instrument.timeout = 5000  # Shorter timeout for quick response
            instrument.read_termination = '\n'
            instrument.write_termination = '\n'
            
            # Quick test if instrument is responding
            try:
                instrument.query("*IDN?")
            except:
                instrument.close()
                return  # Instrument not responding, silently return
            
            # Get current range
            range_val = self.range_combo.currentData() if hasattr(self, 'range_combo') else "AUTO"
            if range_val is None:
                range_val = "AUTO"
            
            # Send command based on 4W mode selection
            fourw_mode = self.fourw_mode_group.checkedId()
            print(f"DEBUG: fourw_mode_group.checkedId() = {fourw_mode}")
            
            if fourw_mode == 0:  # Normal 4W mode (OHMS + FOUR_WR)
                if range_val == "AUTO":
                    print(f"DEBUG: Sending command to instrument: OHMS")
                    instrument.write("OHMS")
                    time.sleep(0.2)
                    print(f"DEBUG: Sending command to instrument: AUTO")
                    instrument.write("AUTO")
                else:
                    cmd = f"OHMS {range_val}"
                    print(f"DEBUG: Sending command to instrument: {cmd}")
                    instrument.write(cmd)
                time.sleep(0.3)
                print(f"DEBUG: Sending command to instrument: FOUR_WR")
                instrument.write("FOUR_WR")
                self.status_bar.showMessage("4W Ohm" + self._get_speed_status_suffix())
                
            elif fourw_mode == 1:  # True OHMS mode (TRUE_OHMS)
                if range_val == "AUTO":
                    print(f"DEBUG: Sending command to instrument: TRUE_OHMS")
                    instrument.write("TRUE_OHMS")
                    time.sleep(0.2)
                    print(f"DEBUG: Sending command to instrument: AUTO")
                    instrument.write("AUTO")
                else:
                    cmd = f"TRUE_OHMS {range_val}"
                    print(f"DEBUG: Sending command to instrument: {cmd}")
                    instrument.write(cmd)
                self.status_bar.showMessage("True OHMS" + self._get_speed_status_suffix())
                
            elif fourw_mode == 2:  # HV OHMS mode (HIVOHMS + FOUR_WR)
                if range_val == "AUTO":
                    print(f"DEBUG: Sending command to instrument: HIV_OHMS 1E6")
                    instrument.write("HIV_OHMS 1E6")
                    time.sleep(0.5)
                    print(f"DEBUG: Sending command to instrument: AUTO")
                    instrument.write("AUTO")
                else:
                    cmd = f"HIV_OHMS {range_val}"
                    print(f"DEBUG: Sending command to instrument: {cmd}")
                    instrument.write(cmd)
                self.status_bar.showMessage("HiVΩ" + self._get_speed_status_suffix())
            
            # Re-apply current speed mode after changing 4W mode
            self._apply_speed_to_instrument(instrument)
            
            instrument.close()
        except Exception as e:
            # Silently ignore errors - instrument may not be connected
            print(f"DEBUG: Instrument not responding (this is OK if not connected): {e}")
    
    def perform_zero_range(self):
        """Perform Zero Range calibration on the instrument (current range only)"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not available.")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "Error", "Please select a VISA resource.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 30000
            instrument.read_termination = '\n'
            instrument.write_termination = '\n'
            
            # Get current function and range settings from GUI
            selected_btn = self.type_group.checkedButton()
            btn_id = self.type_group.id(selected_btn)
            type_map = {0: "DCV", 1: "ACV", 2: "DCI", 3: "ACI", 4: "OHMS", 5: "TOHMS"}
            measurement_type = type_map.get(btn_id, "DCV")
            
            # Map measurement type to SCPI command
            # Fluke 8508A uses: OHMS for 2-wire, OHMS/TRUE_OHMS/HIVOHMS for 4-wire
            func_map = {
                "DCV": "DCV", "ACV": "ACV", "DCI": "DCI", "ACI": "ACI",
                "OHMS": "OHMS", "TOHMS": "OHMS"  # TOHMS uses OHMS with appropriate 4W mode
            }
            func_cmd = func_map.get(measurement_type, "DCV")
            
            # Get range setting directly from combo box data
            range_val = self.range_combo.currentData()
            if range_val is None:
                range_val = "AUTO"
            
            # 1. CRITICAL: Enforce the selected function and range BEFORE zeroing
            print(f"DEBUG Zero Range: measurement_type={measurement_type}, func_cmd={func_cmd}, range_val={range_val}")
            
            # Handle 4W OHMS (TOHMS) based on mode
            if measurement_type == "TOHMS":
                fourw_mode = self.fourw_mode_group.checkedId() if hasattr(self, 'fourw_mode_group') else 0
                
                if fourw_mode == 1:  # True OHMS mode
                    if range_val == "AUTO":
                        print(f"DEBUG Zero Range: Sending command: TRUE_OHMS")
                        instrument.write("TRUE_OHMS")
                        time.sleep(0.2)
                        print(f"DEBUG Zero Range: Sending command: AUTO")
                        instrument.write("AUTO")
                    else:
                        cmd = f"TRUE_OHMS {range_val}"
                        print(f"DEBUG Zero Range: Sending command: {cmd}")
                        instrument.write(cmd)
                elif fourw_mode == 2:  # HV OHMS mode
                    if range_val == "AUTO":
                        print(f"DEBUG Zero Range: Sending command: HIV_OHMS 1E6")
                        instrument.write("HIV_OHMS 1E6")
                        time.sleep(0.5)
                        print(f"DEBUG Zero Range: Sending command: AUTO")
                        instrument.write("AUTO")
                    else:
                        cmd = f"HIV_OHMS {range_val}"
                        print(f"DEBUG Zero Range: Sending command: {cmd}")
                        instrument.write(cmd)
                else:  # Normal 4W mode (fourw_mode == 0)
                    if range_val == "AUTO":
                        print(f"DEBUG Zero Range: Sending command: OHMS")
                        instrument.write("OHMS")
                        time.sleep(0.2)
                        print(f"DEBUG Zero Range: Sending command: AUTO")
                        instrument.write("AUTO")
                    else:
                        cmd = f"OHMS {range_val}"
                        print(f"DEBUG Zero Range: Sending command: {cmd}")
                        instrument.write(cmd)
                    time.sleep(0.3)
                    print(f"DEBUG Zero Range: Sending command: FOUR_WR")
                    instrument.write("FOUR_WR")
            elif measurement_type == "OHMS":
                # 2-Wire OHMS
                if range_val == "AUTO":
                    print(f"DEBUG Zero Range: Sending command: OHMS")
                    instrument.write("OHMS")
                    time.sleep(0.2)
                    print(f"DEBUG Zero Range: Sending command: AUTO")
                    instrument.write("AUTO")
                else:
                    cmd = f"OHMS {range_val}"
                    print(f"DEBUG Zero Range: Sending command: {cmd}")
                    instrument.write(cmd)
                time.sleep(0.5)
                print(f"DEBUG Zero Range: Sending command: TWO_WR")
                instrument.write("TWO_WR")
            else:
                # Other measurement types (DCV, ACV, DCI, ACI)
                if range_val == "AUTO":
                    print(f"DEBUG Zero Range: Sending command: {func_cmd}")
                    instrument.write(func_cmd)
                    time.sleep(0.2)
                    print(f"DEBUG Zero Range: Sending command: AUTO")
                    instrument.write("AUTO")
                else:
                    cmd = f"{func_cmd} {range_val}"
                    print(f"DEBUG Zero Range: Sending command: {cmd}")
                    instrument.write(cmd)
            time.sleep(0.5)

            # 2. Send Zero Range command
            instrument.write("ZERO")
            
            # 3. Wait for completion using *OPC? (more reliable than sleep)
            # This ensures we don't send the next command while it's still zeroing
            try:
                instrument.query("*OPC?")
            except Exception:
                # Fallback if *OPC? times out or fails
                time.sleep(3)
            
            # 4. Enforce the range AGAIN after zeroing to be absolutely sure
            if measurement_type == "TOHMS":
                if fourw_mode == 1:
                    if range_val == "AUTO":
                        instrument.write("TRUE_OHMS")
                        time.sleep(0.2)
                        instrument.write("AUTO")
                    else:
                        instrument.write(f"TRUE_OHMS {range_val}")
                elif fourw_mode == 2:
                    if range_val == "AUTO":
                        instrument.write("HIV_OHMS 1E6")
                        time.sleep(0.2)
                        instrument.write("AUTO")
                    else:
                        instrument.write(f"HIV_OHMS {range_val}")
                else: # Normal 4W (OHMS + FOUR_WR)
                    if range_val == "AUTO":
                        instrument.write("OHMS")
                        time.sleep(0.2)
                        instrument.write("AUTO")
                    else:
                        instrument.write(f"OHMS {range_val}")
                    time.sleep(0.3)
                    instrument.write("FOUR_WR")
            
            elif measurement_type == "OHMS": # 2W
                if range_val == "AUTO":
                    instrument.write("OHMS")
                    time.sleep(0.5)
                    instrument.write("AUTO")
                else:
                    instrument.write(f"OHMS {range_val}")
                # 2W does not need explicit TWO_WR if default, but waiting 0.5s as requested
                time.sleep(0.5)
            else:
                if range_val == "AUTO":
                    instrument.write(measurement_type)
                    time.sleep(0.2)
                    instrument.write("AUTO")
                else:
                    instrument.write(f"{measurement_type} {range_val}")
            
            instrument.close()
            
            self.status_bar.showMessage("✅ Zero Range calibration completed successfully")
            self.results_text.append(f"✅ Zero Range Complete.")
            QMessageBox.information(self, "Zero Range", 
                "Zero Range calibration completed successfully.\n\n"
                "The zero correction is stored for the current range only.")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ Zero Range failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Zero Range failed:\n{str(e)}")
    
    def perform_zero_func(self):
        """Perform Zero Func calibration on the instrument (all ranges in current function)"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not available.")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "Error", "Please select a VISA resource.")
            return

        # Confirm action with user as it takes time
        reply = QMessageBox.question(self, "Confirm Zero Func", 
                                   "Zeroing all ranges for this function will take some time.\n"
                                   "The instrument will cycle through each range.\n\n"
                                   "Do you want to continue?",
                                   QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.No:
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            # Input Zero Func takes a long time as it scans all ranges
            instrument.timeout = 30000 
            instrument.read_termination = '\n'
            instrument.write_termination = '\n'
            
            # Get current settings to restore later
            selected_btn = self.type_group.checkedButton()
            btn_id = self.type_group.id(selected_btn)
            type_map = {0: "DCV", 1: "ACV", 2: "DCI", 3: "ACI", 4: "OHMS", 5: "TOHMS"}
            measurement_type = type_map.get(btn_id, "DCV")
            
            current_range_val = self.range_combo.currentData()
            if current_range_val is None:
                current_range_val = "AUTO"

            # 4W Mode
            fourw_mode = 0
            if hasattr(self, 'fourw_mode_group'):
                fourw_mode = self.fourw_mode_group.checkedId()

            # Get ranges to zero
            ranges = self.range_map.get(measurement_type, [])
            
            # Filter out Auto
            target_ranges = [r for r in ranges if r[2] != "AUTO"]
            
            total_ranges = len(target_ranges)
            self.progress_bar.setRange(0, total_ranges)
            self.progress_bar.setValue(0)
            self.status_bar.showMessage(f"⏳ Starting Zero Func for {measurement_type}...")
            QApplication.processEvents()

            for i, (label, unit, cmd_val) in enumerate(target_ranges):
                self.status_bar.showMessage(f"⏳ Zeroing {measurement_type} range: {label} ({i+1}/{total_ranges})...")
                self.progress_bar.setValue(i)
                QApplication.processEvents()
                
                print(f"DEBUG Zero Func: Zeroing range {label} (cmd={cmd_val})")
                
                # --- Set Range Logic ---
                if measurement_type == "TOHMS":
                    if fourw_mode == 1: # True OHMS
                        instrument.write(f"TRUE_OHMS {cmd_val}")
                    elif fourw_mode == 2: # HIV OHMS
                        instrument.write(f"HIV_OHMS {cmd_val}")
                    else: # Normal 4W
                        instrument.write(f"OHMS {cmd_val}")
                        time.sleep(0.3)
                        instrument.write("FOUR_WR")
                elif measurement_type == "OHMS": # 2W
                    instrument.write(f"OHMS {cmd_val}")
                    # Faster settling for 2W, no explicit TWO_WR needed
                    time.sleep(0.5)
                else:
                    # DCV, ACV, DCI, ACI
                    instrument.write(f"{measurement_type} {cmd_val}")
                
                time.sleep(0.5) # Wait for settling
                
                # --- Send Zero ---
                instrument.write("ZERO")
                
                # --- Wait for completion ---
                try:
                    instrument.query("*OPC?")
                except:
                    time.sleep(2) # Fallback wait
                
            self.progress_bar.setValue(total_ranges)
            self.status_bar.showMessage("✅ Zero Func calibration completed successfully")
            
            # --- Restore Original Settings ---
            print(f"DEBUG Zero Func: Restoring original settings...")
            if measurement_type == "TOHMS":
                # 4-Wire OHMS - Handle based on mode
                if fourw_mode == 1: # True OHMS
                    if current_range_val == "AUTO":
                        instrument.write("TRUE_OHMS")
                        time.sleep(0.2)
                        instrument.write("AUTO")
                    else:
                        instrument.write(f"TRUE_OHMS {current_range_val}")
                elif fourw_mode == 2: # HIV OHMS
                    if current_range_val == "AUTO":
                        instrument.write("HIV_OHMS 1E6")
                        time.sleep(0.2)
                        instrument.write("AUTO")
                    else:
                        instrument.write(f"HIV_OHMS {current_range_val}")
                else: # Normal 4W (OHMS + FOUR_WR)
                    if current_range_val == "AUTO":
                        instrument.write("OHMS")
                        time.sleep(0.2)
                        instrument.write("AUTO")
                    else:
                        instrument.write(f"OHMS {current_range_val}")
                    time.sleep(0.3)
                    instrument.write("FOUR_WR")
            
            elif measurement_type == "OHMS": # 2W
                if current_range_val == "AUTO":
                    instrument.write("OHMS")
                    time.sleep(0.5)
                    instrument.write("AUTO")
                else:
                    instrument.write(f"OHMS {current_range_val}")
                time.sleep(0.5)
                # TWO_WR intentionally omitted for differentiation
            else:
                 if current_range_val == "AUTO":
                    instrument.write(measurement_type)
                    instrument.write("AUTO")
                 else:
                    instrument.write(f"{measurement_type} {current_range_val}")

            instrument.close()
            
            self.results_text.append(f"✅ Zero Func Complete for {measurement_type}")
            QMessageBox.information(self, "Zero Func", 
                "Zero Func calibration completed successfully for all ranges.")

        except Exception as e:
            self.status_bar.showMessage(f"❌ Zero Func failed: {str(e)}")
            QMessageBox.critical(self, "Error", f"Zero Func failed:\n{str(e)}")
            self.progress_bar.reset()
    
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
        
        # Zero Range button (for current range zero calibration)
        self.zero_range_btn = QPushButton("⚖️ Zero Rng")
        self.zero_range_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.zero_range_btn.setMinimumHeight(45)
        self.zero_range_btn.setStyleSheet(self.get_button_style("#ff9800"))
        self.zero_range_btn.setToolTip("Perform Zero calibration for current range only")
        self.zero_range_btn.clicked.connect(self.perform_zero_range)
        layout.addWidget(self.zero_range_btn)
        
        # Zero Func button (for all ranges in current function)
        self.zero_func_btn = QPushButton("⚖️ Zero Func")
        self.zero_func_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.zero_func_btn.setMinimumHeight(45)
        self.zero_func_btn.setStyleSheet(self.get_button_style("#e91e63"))
        self.zero_func_btn.setToolTip("Perform Zero calibration for all ranges in current function")
        self.zero_func_btn.clicked.connect(self.perform_zero_func)
        layout.addWidget(self.zero_func_btn)
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
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
            print(f"===== USER SELECTED MEASUREMENT TYPE: {type_name} (Unit: {unit}) =====")
            self.current_unit = unit
            
            # Update Range Combo (block signals to prevent cascading calls)
            if hasattr(self, 'range_combo'):
                self.range_combo.blockSignals(True)
                self.range_combo.clear()
                ranges = self.range_map.get(type_name, [("Auto", unit, "AUTO")])
                for name, r_unit, cmd in ranges:
                    self.range_combo.addItem(name, cmd)
                self.range_combo.blockSignals(False)
            
            # Update NDIG (Resolution) Combo based on function
            if hasattr(self, 'digit_combo'):
                self.digit_combo.blockSignals(True)
                self.digit_combo.clear()
                resolutions = self.resolution_map.get(type_name, ["5.5", "6.5", "7.5", "8.5"])
                for res in resolutions:
                    self.digit_combo.addItem(res)
                # Set to highest resolution available for this function
                self.digit_combo.setCurrentIndex(len(resolutions) - 1)
                self.digit_combo.blockSignals(False)
            
            # Show/Hide 4W Ohms options based on measurement type
            if hasattr(self, 'fourw_options_container'):
                if type_name == "TOHMS":
                    self.fourw_options_container.show()
                else:
                    self.fourw_options_container.hide()
            
            # Send measurement type command to instrument immediately (only once)
            self.send_measurement_type_to_instrument(type_name)
            
            # Display status for OHMS types (always show, even if instrument not connected)
            if type_name == "TOHMS":
                fourw_mode = self.fourw_mode_group.checkedId() if hasattr(self, 'fourw_mode_group') else 0
                speed = self._get_speed_status_suffix()
                if fourw_mode == 1:
                    self.status_bar.showMessage("True OHMS" + speed)
                elif fourw_mode == 2:
                    self.status_bar.showMessage("HiVΩ" + speed)
                else:
                    self.status_bar.showMessage("4W Ohm" + speed)
            elif type_name == "OHMS":
                self.status_bar.showMessage("⚙️ Measurement Type: 2W OHMS")
                
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
                self.plot_canvas.set_unit(unit)
                self.plot_canvas.plot_data()
    
    def on_range_changed(self, text):
        """Handle range change - immediately update instrument"""
        if hasattr(self, 'type_group'):
            selected_btn = self.type_group.checkedButton()
            if selected_btn:
                btn_id = self.type_group.id(selected_btn)
                type_map = {0: "DCV", 1: "ACV", 2: "DCI", 3: "ACI", 4: "OHMS", 5: "TOHMS"}
                measurement_type = type_map.get(btn_id, "DCV")
                self.send_measurement_type_to_instrument(measurement_type)
    
    def send_measurement_type_to_instrument(self, type_name):
        """Send measurement type command to instrument immediately when user selects it.
           This is a best-effort operation - silently ignores errors if instrument is not connected."""
        if not PYVISA_AVAILABLE:
            return
            
        resource_name = self.resource_combo.currentText()
        if not resource_name or resource_name == "-- Select Resource --":
            return
            
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name, open_timeout=2000)
            instrument.timeout = 5000  # Shorter timeout for quick response
            instrument.read_termination = '\n'
            instrument.write_termination = '\n'
            
            # Quick test if instrument is responding
            try:
                instrument.query("*IDN?")
            except:
                instrument.close()
                return  # Instrument not responding, silently return
            
            # Map measurement type to SCPI command
            func_map = {
                "DCV": "DCV", "ACV": "ACV", "DCI": "DCI", "ACI": "ACI",
                "OHMS": "OHMS", "TOHMS": "OHMS"  # TOHMS uses OHMS with FOUR_WR, or TRUE_OHMS
            }
            func_cmd = func_map.get(type_name, "DCV")
            
            # Get current range
            range_val = self.range_combo.currentData() if hasattr(self, 'range_combo') else "AUTO"
            if range_val is None:
                range_val = "AUTO"
            
            # Handle TOHMS (4W) specially based on mode
            if type_name == "TOHMS":
                fourw_mode = self.fourw_mode_group.checkedId() if hasattr(self, 'fourw_mode_group') else 0
                
                if fourw_mode == 1:  # True OHMS mode
                    if range_val == "AUTO":
                        print(f"DEBUG: Sending command to instrument: TRUE_OHMS")
                        instrument.write("TRUE_OHMS")
                        time.sleep(0.2)
                        print(f"DEBUG: Sending command to instrument: AUTO")
                        instrument.write("AUTO")
                    else:
                        cmd = f"TRUE_OHMS {range_val}"
                        print(f"DEBUG: Sending command to instrument: {cmd}")
                        instrument.write(cmd)
                elif fourw_mode == 2:  # HV OHMS mode
                    if range_val == "AUTO":
                        print(f"DEBUG: Sending command to instrument: HIV_OHMS 1E6")
                        instrument.write("HIV_OHMS 1E6")
                        time.sleep(0.5)
                        print(f"DEBUG: Sending command to instrument: AUTO")
                        instrument.write("AUTO")
                    else:
                        cmd = f"HIV_OHMS {range_val}"
                        print(f"DEBUG: Sending command to instrument: {cmd}")
                        instrument.write(cmd)
                else:  # Normal 4W mode (fourw_mode == 0)
                    if range_val == "AUTO":
                        print(f"DEBUG: Sending command to instrument: OHMS")
                        instrument.write("OHMS")
                        time.sleep(0.2)
                        print(f"DEBUG: Sending command to instrument: AUTO")
                        instrument.write("AUTO")
                    else:
                        cmd = f"OHMS {range_val}"
                        print(f"DEBUG: Sending command to instrument: {cmd}")
                        instrument.write(cmd)
                    time.sleep(0.3)
                    print(f"DEBUG: Sending command to instrument: FOUR_WR")
                    instrument.write("FOUR_WR")
            elif type_name == "OHMS":
                # 2-Wire OHMS (OHMS + TWO_WR)
                if range_val == "AUTO":
                    print(f"DEBUG: Sending command to instrument: OHMS")
                    instrument.write("OHMS")
                    time.sleep(0.2)
                    print(f"DEBUG: Sending command to instrument: AUTO")
                    instrument.write("AUTO")
                else:
                    cmd = f"OHMS {range_val}"
                    print(f"DEBUG: Sending command to instrument: {cmd}")
                    instrument.write(cmd)
                time.sleep(0.3)
                print(f"DEBUG: Sending command to instrument: TWO_WR")
                instrument.write("TWO_WR")
            else:
                # Other measurement types (DCV, ACV, DCI, ACI)
                if range_val == "AUTO":
                    print(f"DEBUG: Sending command to instrument: {func_cmd}")
                    instrument.write(func_cmd)
                    time.sleep(0.2)
                    print(f"DEBUG: Sending command to instrument: AUTO")
                    instrument.write("AUTO")
                else:
                    cmd = f"{func_cmd} {range_val}"
                    print(f"DEBUG: Sending command to instrument: {cmd}")
                    instrument.write(cmd)
            
            # Re-apply current speed mode after changing measurement type
            self._apply_speed_to_instrument(instrument)
            
            instrument.close()
            
            # Show status with wire mode for OHMS types
            speed = self._get_speed_status_suffix()
            if type_name == "TOHMS":
                fourw_mode = self.fourw_mode_group.checkedId() if hasattr(self, 'fourw_mode_group') else 0
                if fourw_mode == 1:
                    self.status_bar.showMessage("True OHMS" + speed)
                elif fourw_mode == 2:
                    self.status_bar.showMessage("HiVΩ" + speed)
                else:
                    self.status_bar.showMessage("4W Ohm" + speed)
            elif type_name == "OHMS":
                self.status_bar.showMessage("2W OHMS" + speed)
            else:
                self.status_bar.showMessage(f"{func_cmd}" + speed)
        except Exception as e:
            # Silently ignore errors - instrument may not be connected
            print(f"DEBUG: Instrument not responding (this is OK if not connected): {e}")
    
    def _get_speed_status_suffix(self):
        """Get speed mode suffix for status bar display."""
        filt = self.filt_check.isChecked() if hasattr(self, 'filt_check') else False
        fast = self.fast_check.isChecked() if hasattr(self, 'fast_check') else False
        
        if filt and fast:
            return " | Low Pass Filter + Fast"
        elif filt:
            return " | Low Pass Filter"
        elif fast:
            return " | Fast"
        return ""

    def _get_measurement_status_prefix(self):
        """Get current measurement mode display name for status bar."""
        if hasattr(self, 'type_group'):
            selected_btn = self.type_group.checkedButton()
            if selected_btn:
                btn_id = self.type_group.id(selected_btn)
                type_map = {0: "DCV", 1: "ACV", 2: "DCI", 3: "ACI", 4: "OHMS", 5: "TOHMS"}
                type_name = type_map.get(btn_id, "")
                if type_name == "TOHMS":
                    fourw_mode = self.fourw_mode_group.checkedId() if hasattr(self, 'fourw_mode_group') else 0
                    if fourw_mode == 1: return "True OHMS"
                    if fourw_mode == 2: return "HiVΩ"
                    return "4W Ohm"
                elif type_name == "OHMS":
                    return "2W OHMS"
                else:
                    return type_name
        return ""

    def _apply_speed_to_instrument(self, instrument):
        """Re-apply the current speed mode (FILT/FAST) setting to the instrument.
           Called after changing measurement type/range/4W mode since the 8508A may reset these."""
        try:
            filt = self.filt_check.isChecked() if hasattr(self, 'filt_check') else False
            fast = self.fast_check.isChecked() if hasattr(self, 'fast_check') else False
            
            if filt:
                instrument.write("FILT_ON")
            else:
                instrument.write("FILT_OFF")
            
            time.sleep(0.2)
            
            if fast:
                instrument.write("FAST_ON")
            else:
                instrument.write("FAST_OFF")
            
            print(f"DEBUG: Re-applied speed mode (FILT={filt}, FAST={fast}) after measurement change")
        except Exception as e:
            print(f"DEBUG: Failed to re-apply speed mode: {e}")

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
    
    def get_spinbox_style(self):
        """Get stylesheet for spinbox widgets"""
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
            QSpinBox::up-button, QDoubleSpinBox::up-button,
            QSpinBox::down-button, QDoubleSpinBox::down-button {
                width: 20px;
                border: none;
            }
        """
    
    def get_radio_style(self):
        """Get stylesheet for radio buttons"""
        return """
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
    
    def get_checkbox_style(self):
        """Get stylesheet for checkboxes"""
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
            QCheckBox::indicator:checked {
                background-color: #1a73e8;
                border-color: #1a73e8;
            }
        """
    
    def get_disabled_spinbox_style(self):
        """Get stylesheet for disabled spinbox widgets"""
        return """
            QDoubleSpinBox, QSpinBox {
                background-color: #f0f0f0;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #9e9e9e;
                min-height: 24px;
            }
            QDoubleSpinBox::up-button, QDoubleSpinBox::down-button,
            QSpinBox::up-button, QSpinBox::down-button {
                width: 20px;
                border: none;
            }
        """
    
    def get_disabled_input_style(self):
        """Get stylesheet for disabled input widgets"""
        return """
            QComboBox, QLineEdit {
                background-color: #f0f0f0;
                border: 2px solid #e0e0e0;
                border-radius: 8px;
                padding: 8px 12px;
                font-size: 14px;
                color: #9e9e9e;
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
                border-top: 6px solid #9e9e9e;
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
                background-color: {color}dd;
            }}
            QPushButton:pressed {{
                background-color: {color}aa;
            }}
            QPushButton:disabled {{
                background-color: #dadce0;
                color: #9aa0a6;
            }}
        """
    
    def check_dependencies(self):
        """Check for required dependencies"""
        missing = []
        if not PYVISA_AVAILABLE:
            missing.append("pyvisa")
        if not MATPLOTLIB_AVAILABLE:
            missing.append("matplotlib")
        
        if missing:
            self.results_text.append(f"⚠️ Missing optional dependencies: {', '.join(missing)}")
            self.results_text.append("Install with: pip install " + " ".join(missing))
    
    def refresh_resources(self):
        """Refresh available VISA resources"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Installed",
                              "PyVISA is required for instrument communication.\n"
                              "Install with: pip install pyvisa pyvisa-py")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            
            self.resource_combo.clear()
            if resources:
                for res in resources:
                    self.resource_combo.addItem(res)
                self.status_bar.showMessage(f"🔄 Found {len(resources)} VISA resources")
            else:
                self.resource_combo.addItem("GPIB0::6::INSTR")
                self.status_bar.showMessage("⚠️ No VISA resources found")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Failed to list resources:\n{str(e)}")
    
    def test_connection(self):
        """Test connection to the instrument"""
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
            inst.timeout = 10000
            
            # Query instrument identity
            idn = inst.query("*IDN?").strip()
            inst.close()
            
            QMessageBox.information(self, "Connection Successful",
                                   f"✅ Connected to:\n{idn}")
            self.status_bar.showMessage(f"✅ Connected: {idn}")
            
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed",
                               f"❌ Failed to connect:\n{str(e)}")
            self.status_bar.showMessage("❌ Connection failed")
    
    def start_measurement(self):
        """Start measurement process"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Installed",
                              "PyVISA is required for measurements.")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "No Resource Selected",
                              "Please select a VISA resource first.")
            return
        
        # Check mode selection
        mode = self.mode_combo.currentText()
        if mode == "-- Select Mode --" or not mode:
            QMessageBox.warning(self, "No Mode Selected",
                              "Please select a Sampling Mode (Integration or NPLC).")
            return
        
        # Get measurement type
        selected_button = self.type_group.checkedButton()
        if not selected_button:
            QMessageBox.warning(self, "No Type Selected",
                              "Please select a measurement type.")
            return
        
        # Get type from button text
        button_text = selected_button.text()
        type_map = {
            "⚡ DC Voltage": "DCV",
            "〜 AC Voltage": "ACV",
            "⚡ DC Current": "DCI",
            "〜 AC Current": "ACI",
            "🔧 2W Ω": "OHMS",
            "🔧 4W Ω (True)": "TOHMS"
        }
        measurement_type = type_map.get(button_text, "DCV")
        
        # Get settings
        num_measurements = self.num_measurements_spin.value()
        auto_zero = self.auto_zero_check.isChecked()
        range_val = self.range_combo.currentData()
        # Fallback if data is None
        if range_val is None:
            range_val = "AUTO"
        print(f"DEBUG: Range selected = {self.range_combo.currentText()}, Range value = {range_val}")
        digits_text = self.digit_combo.currentText()
        digits = int(float(digits_text))  # Convert "8.5" -> 8 (used for RESL command in NPLC mode)
        
        # Calculate gate_time in seconds for Integration mode
        gate_time = 1.0
        if mode == "Integration":
            gate_value = self.gate_time_spin.value()
            time_unit = self.time_unit_combo.currentText()
            if time_unit == "seconds":
                gate_time = gate_value
            elif time_unit == "minutes":
                gate_time = gate_value * 60
            elif time_unit == "hours":
                gate_time = gate_value * 3600
        
        # Setup progress bar
        self.progress_bar.setMaximum(num_measurements)
        self.progress_bar.setValue(0)
        
        # Clear previous measurements
        self.all_measurements = []
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.clear_measurements()
        
        # Create and start measurement thread
        # Note: In NPLC mode, digits value is used for RESL command (resolution)
        # Get 4W mode setting (0=TRUE, 1=HIR)
        fourw_mode = self.fourw_mode_group.checkedId() if hasattr(self, 'fourw_mode_group') else 0
        
        self.measurement_thread = MeasurementThread(
            resource_name=resource_name,
            num_measurements=num_measurements,
            measurement_type=measurement_type,
            auto_zero=auto_zero,
            range_val=range_val,
            digits=digits,
            mode=mode,
            gate_time=gate_time,
            fourw_mode=fourw_mode
        )
        

        
        self.measurement_thread.measurement_ready.connect(self.on_measurement_ready)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        
        self.measurement_thread.start()
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_bar.showMessage(f"🔬 Measurement in progress ({mode} mode)...")
    
    def stop_measurement(self):
        """Stop current measurement"""
        if self.measurement_thread and self.measurement_thread.isRunning():
            self.measurement_thread.stop()
            self.measurement_thread.wait(2000)
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("⏹️ Measurement stopped")
    
    def _send_toggle_command(self, command_name, checked, display_name):
        """Helper function to send ON/OFF toggle commands to instrument"""
        if not PYVISA_AVAILABLE:
            return
            
        resource_name = self.resource_combo.currentText()
        if not resource_name or resource_name == "-- Select Resource --":
            return
            
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            instrument.write_termination = '\n'
            
            cmd = f"{command_name} ON" if checked else f"{command_name} OFF"
            print(f"DEBUG: Sending command: {cmd}")
            instrument.write(cmd)
            instrument.close()
            
            status = "Enabled" if checked else "Disabled"
            self.status_bar.showMessage(f"⚙️ {display_name}: {status}")
        except Exception as e:
            print(f"DEBUG: Failed to set {command_name} mode: {e}")

    def _send_speed_command(self, command, value):
        """Helper to send FILT or FAST commands to instrument."""
        if not PYVISA_AVAILABLE:
            self._update_speed_status()
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            self._update_speed_status()
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name, open_timeout=2000)
            instrument.timeout = 5000
            instrument.read_termination = '\n'
            instrument.write_termination = '\n'
            
            cmd = f"{command}_{'ON' if value else 'OFF'}"
            print(f"DEBUG: Sending {cmd}")
            instrument.write(cmd)
            
            instrument.close()
            self._update_speed_status()
        except Exception as e:
            print(f"DEBUG: Failed to set {command}: {e}")
            self._update_speed_status()
    
    def on_filt_changed(self, state):
        """Handle Low Pass Filter checkbox change."""
        self._send_speed_command("FILT", state == 2)
    
    def on_fast_changed(self, state):
        """Handle Fast checkbox change."""
        self._send_speed_command("FAST", state == 2)
    
    def _update_speed_status(self):
        """Update status bar with current measurement + speed mode."""
        prefix = self._get_measurement_status_prefix()
        suffix = self._get_speed_status_suffix()
        self.status_bar.showMessage(prefix + suffix)
            
    def format_value_with_unit(self, value, base_unit):
        """Format value with appropriate SI prefix"""
        scale_factor = 1.0
        disp_unit = base_unit
        
        abs_val = abs(value)
        
        # General logic: If Abs Value >= 1000, scale UP (k, M, G, etc.)
        # If Abs Value < 1 (except 0), scale DOWN (m, u, n, etc.)
        
        if base_unit == "V":
            if abs_val >= 1000:
                scale_factor = 1e-3
                disp_unit = "kV"
            elif abs_val < 1e-3:
                scale_factor = 1e6
                disp_unit = "µV"
            elif abs_val < 1:
                scale_factor = 1e3
                disp_unit = "mV"
        
        elif base_unit == "Ω":
            if abs_val >= 1e9:
                scale_factor = 1e-9
                disp_unit = "GΩ"
            elif abs_val >= 1e6:
                scale_factor = 1e-6
                disp_unit = "MΩ"
            elif abs_val >= 1000:
                scale_factor = 1e-3
                disp_unit = "kΩ"
        
        elif base_unit == "A":
            if abs_val >= 1000:
                scale_factor = 1e-3
                disp_unit = "kA"
            elif abs_val < 1e-6:
                scale_factor = 1e9
                disp_unit = "nA"
            elif abs_val < 1e-3:
                scale_factor = 1e6
                disp_unit = "µA"
            elif abs_val < 1:
                scale_factor = 1e3
                disp_unit = "mA"
        
        scaled_value = value * scale_factor
        return scaled_value, disp_unit
    
    def on_measurement_ready(self, value, measurement_num, timestamp):
        """Handle new measurement data"""
        self.all_measurements.append((value, timestamp))
        self.progress_bar.setValue(measurement_num)
        
        # Auto-scaling with helper function
        scaled_value, disp_unit = self.format_value_with_unit(value, self.current_unit)
        
        # Display measurement
        self.results_text.append(f"#{measurement_num} [{timestamp}]: {scaled_value:.8f} {disp_unit}")
        
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.add_measurement(value)
    
    def on_measurement_complete(self, measurements):
        """Handle measurement completion"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        if measurements:
            values = [m[0] for m in measurements]
            avg_raw = sum(values) / len(values)
            
            avg_scaled, scale_unit = self.format_value_with_unit(avg_raw, self.current_unit)
            scale_factor = avg_scaled / avg_raw if avg_raw != 0 else 1.0
            
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
    
    def execute_input_zero(self):
        """Execute Input Zero command"""
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
            
            self.status_bar.showMessage("⚖️ Executing Input Zero...")
            
            self.results_text.clear()
            self.results_text.append("⚖️ Input Zero - Offset Calibration")
            self.results_text.append("=" * 40)
            
            # Execute Input Zero command
            inst.write("INPUT_ZERO")
            time.sleep(2.0)
            
            self.results_text.append("✅ INPUT_ZERO command sent")
            self.results_text.append("")
            self.results_text.append("📊 Test Readings after Zero:")
            
            # Take 2 test readings
            for i in range(2):
                try:
                    response = inst.query("VAL?").strip()
                    value = float(response)
                    scaled_value, unit = self.format_value_with_unit(value, self.current_unit)
                    self.results_text.append(f"  Reading {i+1}: {scaled_value:.6f} {unit}")
                except Exception as read_err:
                    self.results_text.append(f"  Reading {i+1}: Error - {str(read_err)}")
            
            inst.close()
            
            self.results_text.append("")
            self.results_text.append("=" * 40)
            self.results_text.append("✅ Input Zero completed successfully")
            
            self.status_bar.showMessage("⚖️ Input Zero completed - see Measurement Results")
            
        except Exception as e:
            self.status_bar.showMessage(f"❌ Input Zero failed: {str(e)}")
            self.results_text.append(f"\n❌ Error: {str(e)}")
    
    def clear_results(self):
        """Clear all results"""
        self.results_text.clear()
        self.all_measurements = []
        self.progress_bar.setValue(0)
        if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
            self.plot_canvas.clear_measurements()
        self.status_bar.showMessage("🗑️ Results cleared")
    
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
            
            script_dir = Path(__file__).parent
            output_dir = script_dir / "Measurement_Results"
            output_dir.mkdir(parents=True, exist_ok=True)
            
            filename = output_dir / "latest_output.csv"
            
            try:
                with open(filename, 'w', newline='', encoding='utf-8') as csvfile:
                    self.write_csv_content(csvfile)
            except PermissionError:
                self.status_bar.showMessage(f"⚠️ Could not save CSV: File is open in another program")
                return
            
            # Open file
            try:
                if os.name == 'nt':
                    os.startfile(filename)
                elif sys.platform == 'darwin':
                    subprocess.run(['open', filename])
                else:
                    subprocess.run(['xdg-open', filename])
            except Exception as e:
                self.results_text.append(f"❌ Failed to open file: {str(e)}")
            
            self.status_bar.showMessage(f"💾 Saved and opened: {filename}")
            self.results_text.append(f"\n💾 Data saved to: {filename}")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to save CSV:\n{str(e)}")
    
    def write_csv_content(self, csvfile):
        """Helper to write CSV content"""
        writer = csv.writer(csvfile)
        now = datetime.now()
        
        if not self.all_measurements:
            return

        values = [m[0] for m in self.all_measurements]
        
        avg_raw = sum(values) / len(values)
        avg_scaled, scale_unit = self.format_value_with_unit(avg_raw, self.current_unit)
        scale_factor = avg_scaled / avg_raw if avg_raw != 0 else 1.0

        # Row 1: Measurement numbers
        measurement_numbers = ['Measurement'] + [str(i) for i in range(1, len(values) + 1)]
        writer.writerow(measurement_numbers)

        # Row 2: Values (Scaled)
        scaled_values = [f'{v * scale_factor:.8g}' for v in values]
        values_row = ['Value'] + scaled_values + [scale_unit]
        writer.writerow(values_row)
        
        # Row 3: Date
        writer.writerow(['Date', now.strftime('%Y-%m-%d')])
        
        # Row 4: Time
        writer.writerow(['Time', now.strftime('%H:%M:%S')])
        
        writer.writerow([])
        
        # Statistics
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
        
        writer.writerow([])
        selected_button = self.type_group.checkedButton()
        if selected_button:
            measurement_type_text = selected_button.text()
            parts = measurement_type_text.split()
            clean_text = " ".join(parts[1:]) if len(parts) > 1 else measurement_type_text
            writer.writerow(['Measurement Type', clean_text])


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    QLocale.setDefault(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
    app.setStyle('Fusion')
    
    window = Fluke8508MultimeterGUI()
    window.showMaximized()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
