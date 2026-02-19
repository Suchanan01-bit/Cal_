"""
Rohde & Schwarz Power Meter GUI Application
A modern PyQt6-based GUI for controlling and monitoring Rohde & Schwarz Power Meters (NRVS/NRP Series)
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
    
    def __init__(self, resource_name, num_measurements, measurement_type, frequency_corr):
        super().__init__()
        self.resource_name = resource_name
        self.num_measurements = num_measurements
        self.measurement_type = measurement_type # "dBm" or "W"
        self.frequency_corr = frequency_corr
        self.is_running = True
        self.measurements = []  # List of (value, timestamp) tuples
    
    def run(self):
        """Execute measurements in background thread"""
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(self.resource_name)
            instrument.timeout = 5000
            
            # Basic Setup
            instrument.write("*RST")
            time.sleep(0.5)
            
            # Set Unit
            if self.measurement_type == "dBm":
                instrument.write("UNIT:POW DBM")
            else:
                instrument.write("UNIT:POW W")
            
            # Set Frequency Correction if valid
            if self.frequency_corr > 0:
                instrument.write(f"SENS:FREQ {self.frequency_corr}")
            
            # Take measurements
            for i in range(self.num_measurements):
                if not self.is_running:
                    break
                
                t_start = time.time()
                try:
                    from datetime import datetime
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    # Read value from instrument
                    # Try READ? first (Initiate + Fetch), or MEAS?
                    # R&S usually supports MEAS? for simple scalar
                    value_str = instrument.query("READ?") 
                    
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
                
                # Small delay to prevent flooding if instrument is super fast
                time.sleep(0.1) 
            
            instrument.close()
            self.measurement_complete.emit(self.measurements)
            
        except Exception as e:
            print(f"DEBUG: Main loop thread error: {e}")
            self.error_occurred.emit(str(e))

    def stop(self):
        """Stop the measurement thread"""
        self.is_running = False


class ZeroThread(QThread):
    """Thread for Zero/Calibration"""
    zero_complete = pyqtSignal(bool, str) # success, message
    
    def __init__(self, resource_name):
        super().__init__()
        self.resource_name = resource_name
        
    def run(self):
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(self.resource_name)
            instrument.timeout = 20000 # Zeroing can take time
            
            # Perform Zeroing
            # Standard SCPI or R&S specific
            # Trying standard CAL:ZERO:AUTO ON or CAL ?
            instrument.write("CAL:ZERO:AUTO ON") 
            # Some units use CALIBRATION:ZERO:AUTO ONCE
            # Let's assume generic R&S SCPI for now:
            # SENS:CORR:ZERO:AUTO ONCE
            
            # Attempt to find the right command or just use a generic approach
            # Using common R&S NRP command sets as best guess
            try:
                instrument.write("SENS:CORR:ZERO:AUTO ONCE")
            except:
                pass # Fallback

            # Wait for operation complete
            instrument.query("*OPC?")
            
            instrument.close()
            self.zero_complete.emit(True, "Zeroing completed successfully.")
        except Exception as e:
            self.zero_complete.emit(False, str(e))


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
        
        # Styling
        self.axes.set_facecolor('#f8f9fa')
        self.axes.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        self.axes.spines['top'].set_visible(False)
        self.axes.spines['right'].set_visible(False)
        self.axes.spines['left'].set_color('#3c4043')
        self.axes.spines['bottom'].set_color('#3c4043')
        self.axes.tick_params(colors='#3c4043', labelsize=9)
        
        self.measurements = []
        self.unit = "dBm"
        self.plot_data()
    
    def plot_data(self):
        """Update the plot with current measurements"""
        self.axes.clear()
        
        if self.measurements:
            x = list(range(1, len(self.measurements) + 1))
            self.axes.plot(x, self.measurements, 'o-', color='#1a73e8', 
                          linewidth=2, markersize=6, label='Power')
            
            # Add average line
            avg = sum(self.measurements) / len(self.measurements)
            self.axes.axhline(y=avg, color='#ea4335', linestyle='--', 
                            linewidth=1.5, label=f'Average: {avg:.4f} {self.unit}')
            
            self.axes.set_xlabel('Measurement Number', fontsize=10, color='#3c4043', weight='bold')
            self.axes.set_ylabel(f'Power ({self.unit})', fontsize=10, color='#3c4043', weight='bold')
            self.axes.set_title('Real-time Power Measurements', fontsize=12, color='#3c4043', weight='bold', pad=15)
            self.axes.legend(loc='upper right', fontsize=9, framealpha=0.9)
            self.axes.grid(True, alpha=0.3, linestyle='--', linewidth=0.5)
        else:
            self.axes.text(0.5, 0.5, 'No data yet', ha='center', va='center',
                          fontsize=14, color='#9aa0a6', transform=self.axes.transAxes)
            self.axes.set_xlabel('Measurement Number', fontsize=10, color='#3c4043', weight='bold')
            self.axes.set_ylabel(f'Power ({self.unit})', fontsize=10, color='#3c4043', weight='bold')
        
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


class RSPowerMeterGUI(QMainWindow):
    """Main GUI window for Rohde & Schwarz Power Meter application"""
    
    def __init__(self):
        super().__init__()
        self.measurement_thread = None
        self.zero_thread = None
        self.all_measurements = []
        self.current_unit = "dBm"
        
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Rohde & Schwarz Power Meter Control Panel")
        self.setGeometry(0, 0, 1920, 1080)
        self.set_light_theme()
        
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_box = QVBoxLayout(central_widget)
        main_box.setContentsMargins(0, 0, 0, 0)
        
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        main_box.addWidget(scroll)
        
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📡 Rohde & Schwarz Power Meter Control Panel")
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
        results_layout_inner.addWidget(self.results_text)
        results_group.setLayout(results_layout_inner)
        results_layout.addWidget(results_group, 1)
        
        # Graph
        if MATPLOTLIB_AVAILABLE:
            graph_group = QGroupBox("📈 Live Graph (dBm/W)")
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
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("✨ Ready - Rohde & Schwarz Power Meter Control")
        
        self.check_dependencies()
        
    def create_connection_group(self):
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
        group = QGroupBox("🔬 Measurement Type")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        layout = QHBoxLayout()
        
        self.type_group = QButtonGroup()
        types = [
            ("📡 Power (dBm)", "dBm", "dBm"),
            ("⚡ Power (Watts)", "W", "W")
        ]
        
        for i, (label, type_name, unit) in enumerate(types):
            radio = QRadioButton(label)
            radio.setFont(QFont("Segoe UI", 10))
            radio.toggled.connect(lambda checked, t=type_name, u=unit: self.on_type_changed(checked, t, u))
            self.type_group.addButton(radio, i)
            layout.addWidget(radio)
            if i == 0: radio.setChecked(True)
            
        group.setLayout(layout)
        return group
    
    def create_settings_group(self):
        group = QGroupBox("⚙️ Measurement Parameters")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        layout = QVBoxLayout()
        
        row0_layout = QHBoxLayout()
        
        num_label = QLabel("Number of Measurements:")
        num_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(num_label)
        
        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setRange(1, 100000)
        self.num_measurements_spin.setValue(10)
        self.num_measurements_spin.setFont(QFont("Segoe UI", 10))
        # Enforce English locale to ensure Arabic numerals (1, 2, 3) instead of Thai (๑, ๒, ๓)
        self.num_measurements_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row0_layout.addWidget(self.num_measurements_spin)
        
        freq_label = QLabel("Correction Freq (Hz):")
        freq_label.setFont(QFont("Segoe UI", 10))
        row0_layout.addWidget(freq_label)
        
        self.freq_spin = QDoubleSpinBox()
        self.freq_spin.setRange(0, 100e9) # 100 GHz max
        self.freq_spin.setValue(1e9) # 1 GHz default
        self.freq_spin.setDecimals(1)
        self.freq_spin.setFont(QFont("Segoe UI", 10))
        self.freq_spin.setMinimumWidth(120)
        # Enforce English locale to ensure Arabic numerals
        self.freq_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        row0_layout.addWidget(self.freq_spin)
        
        layout.addLayout(row0_layout)
        group.setLayout(layout)
        return group

    def create_control_buttons(self):
        widget = QWidget()
        layout = QHBoxLayout(widget)
        
        self.start_btn = QPushButton("▶️ Start Measurement")
        self.start_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.start_btn.setStyleSheet(self.get_button_style("#1a73e8"))
        self.start_btn.clicked.connect(self.start_measurement)
        layout.addWidget(self.start_btn)
        
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.stop_btn.setStyleSheet(self.get_button_style("#5f6368"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        layout.addWidget(self.stop_btn)
        
        self.zero_btn = QPushButton("⚖️ Zero / Cal")
        self.zero_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        self.zero_btn.setStyleSheet(self.get_button_style("#d93025"))
        self.zero_btn.clicked.connect(self.execute_zero)
        layout.addWidget(self.zero_btn)
        
        clear_btn = QPushButton("🧹 Clear")
        clear_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        clear_btn.setStyleSheet(self.get_button_style("#f59e0b"))
        clear_btn.clicked.connect(self.clear_results)
        layout.addWidget(clear_btn)
        
        save_btn = QPushButton("💾 Save CSV")
        save_btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        save_btn.setStyleSheet(self.get_button_style("#1967d2"))
        save_btn.clicked.connect(self.save_csv)
        layout.addWidget(save_btn)
        
        return widget

    def on_type_changed(self, checked, type_name, unit):
        if checked:
            self.current_unit = unit
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
                self.plot_canvas.set_unit(unit)
                self.plot_canvas.plot_data()

    def start_measurement(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA not installed!")
            return
            
        resource_name = self.resource_combo.currentText()
        if not resource_name:
            QMessageBox.warning(self, "Error", "Please select a VISA resource!")
            return

        num = self.num_measurements_spin.value()
        freq = self.freq_spin.value()
        
        # Get meas type
        selected_button = self.type_group.checkedButton()
        if not selected_button: return
        unit_type = ["dBm", "W"][self.type_group.id(selected_button)]
        
        # Clear
        self.all_measurements = []
        if MATPLOTLIB_AVAILABLE: self.plot_canvas.clear_measurements()
        self.results_text.clear()
        
        self.measurement_thread = MeasurementThread(resource_name, num, unit_type, freq)
        self.measurement_thread.measurement_ready.connect(self.update_measurement)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.progress_bar.setMaximum(num)
        
        self.measurement_thread.start()
        self.status_bar.showMessage("Measuring...")

    def update_measurement(self, value, number, timestamp):
        self.all_measurements.append((number, value, timestamp))
        self.results_text.append(f"{number}. {value:.6f} {self.current_unit}")
        self.progress_bar.setValue(number)
        
        if MATPLOTLIB_AVAILABLE:
            self.plot_canvas.add_measurement(value)

    def on_measurement_complete(self, measurements):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("Measurement Complete")
        QMessageBox.information(self, "Done", f"Captured {len(measurements)} measurements.")

    def on_error(self, message):
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("Error occurred")
        QMessageBox.critical(self, "Error", message)

    def stop_measurement(self):
        if self.measurement_thread and self.measurement_thread.isRunning():
            self.measurement_thread.stop()
            self.start_btn.setEnabled(True)
            self.stop_btn.setEnabled(False)
            self.status_bar.showMessage("Stopped")

    def execute_zero(self):
        resource_name = self.resource_combo.currentText()
        if not resource_name: return
        
        self.zero_btn.setEnabled(False)
        self.status_bar.showMessage("Zeroing sensor...")
        
        self.zero_thread = ZeroThread(resource_name)
        self.zero_thread.zero_complete.connect(self.on_zero_complete)
        self.zero_thread.start()

    def on_zero_complete(self, success, message):
        self.zero_btn.setEnabled(True)
        if success:
            QMessageBox.information(self, "Zero Cal", message)
            self.status_bar.showMessage("Zero calibration successful")
        else:
            QMessageBox.warning(self, "Zero Cal Failed", message)
            self.status_bar.showMessage("Zero calibration failed")

    def clear_results(self):
        self.results_text.clear()
        self.all_measurements = []
        if MATPLOTLIB_AVAILABLE: self.plot_canvas.clear_measurements()
        self.progress_bar.setValue(0)

    def save_csv(self):
        if not self.all_measurements:
            QMessageBox.warning(self, "No Data", "No measurements to save.")
            return
            
        filename = f"power_meas_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
        try:
            with open(filename, 'w', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(["Index", f"Power ({self.current_unit})", "Timestamp"])
                writer.writerows(self.all_measurements)
            QMessageBox.information(self, "Saved", f"Saved to {filename}")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Could not save file: {e}")

    def refresh_resources(self):
        if not PYVISA_AVAILABLE: return
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            self.resource_combo.clear()
            self.resource_combo.addItems(resources)
        except Exception as e:
            QMessageBox.warning(self, "Error", str(e))

    def test_connection(self):
        if not PYVISA_AVAILABLE: return
        try:
            rm = pyvisa.ResourceManager()
            inst = rm.open_resource(self.resource_combo.currentText())
            idn = inst.query("*IDN?")
            inst.close()
            QMessageBox.information(self, "Connected", f"Device: {idn}")
        except Exception as e:
            QMessageBox.critical(self, "Connection Failed", str(e))
            
    def check_dependencies(self):
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Missing", "PyVISA not found.")
        if not MATPLOTLIB_AVAILABLE:
            QMessageBox.warning(self, "Missing", "Matplotlib not found.")

    def set_light_theme(self):
        self.setStyleSheet("""
            QMainWindow { background-color: #f8f9fa; }
            QWidget { background-color: #f8f9fa; color: #3c4043; }
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
                padding: 10px;
                font-weight: bold;
            }}
            QPushButton:hover {{ opacity: 0.9; }}
            QPushButton:pressed {{ opacity: 0.7; }}
            QPushButton:disabled {{ background-color: #95a5a6; }}
        """

if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = RSPowerMeterGUI()
    window.show()
    sys.exit(app.exec())
