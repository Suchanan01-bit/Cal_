"""
8846A Precision Multimeter GUI Application
A modern PyQt6-based GUI for controlling and monitoring Fluke 8846A 6.5-digit Precision Multimeter
"""

import sys
import csv
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QGroupBox, QFileDialog, QMessageBox, QProgressBar, QStatusBar,
    QDoubleSpinBox, QRadioButton, QButtonGroup, QScrollArea, QCheckBox, QFrame
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QLocale
from PyQt6.QtGui import QFont, QPalette, QColor, QIcon

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


class MeasurementThread(QThread):
    """Thread for performing measurements without blocking the UI"""
    measurement_ready = pyqtSignal(float, int)  # value, measurement_number
    measurement_complete = pyqtSignal(list)  # all measurements
    error_occurred = pyqtSignal(str)
    progress_update = pyqtSignal(int)
    
    def __init__(self, resource_name, num_measurements, measurement_type, sampling_interval, auto_zero=True, offset_comp=False):
        super().__init__()
        self.resource_name = resource_name
        self.num_measurements = num_measurements
        self.measurement_type = measurement_type
        self.sampling_interval = sampling_interval
        self.auto_zero = auto_zero
        self.offset_comp = offset_comp
        self.is_running = True
        self.measurements = []
    
    def run(self):
        """Execute measurements in background thread"""
        try:
            if not PYVISA_AVAILABLE:
                self.error_occurred.emit("PyVISA is not installed. Please install it using: pip install pyvisa pyvisa-py")
                return
            
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(self.resource_name)
            instrument.timeout = int(self.sampling_interval * 1000 + 5000)  # Sampling interval + 5 seconds buffer
            
            # Clear any pending errors/buffer
            try:
                instrument.clear()
            except:
                pass
            
            # Get instrument ID
            idn = instrument.query("*IDN?")
            
            # Configure measurement type
            measurement_commands = {
                "DC Voltage": "CONF:VOLT:DC",
                "AC Voltage": "CONF:VOLT:AC",
                "DC Current": "CONF:CURR:DC",
                "AC Current": "CONF:CURR:AC",
                "Resistance": "CONF:RES",
                "4-Wire Resistance": "CONF:FRES",  # 4-wire resistance
                "Continuity": "CONF:CONT"
            }
            
            if self.measurement_type in measurement_commands:
                instrument.write(measurement_commands[self.measurement_type])
            
            # Configure Auto Zero (AZERO command for FLUKE 8846A)
            # ON = 1, OFF = 0
            instrument.write(f"ZERO:AUTO {'ON' if self.auto_zero else 'OFF'}")
            
            # Configure Offset Compensation
            # This might need to be adjusted based on the specific measurement type
            if self.offset_comp:
                instrument.write("CALC2:NULL:STAT ON")
            else:
                instrument.write("CALC2:NULL:STAT OFF")
            
            self.measurements = []
            
            for i in range(self.num_measurements):
                if not self.is_running:
                    break
                
                # Query measurement
                response = instrument.query("READ?")
                
                # Handle potential comma-separated values (take the latest/first valid)
                # Fluke might return multiple values if triggered multiple times or internal buffer
                clean_response = response.strip()
                if ',' in clean_response:
                    # Take the first value if multiple are returned
                    value_str = clean_response.split(',')[0]
                else:
                    value_str = clean_response
                    
                value = float(value_str)
                
                self.measurements.append(value)
                self.measurement_ready.emit(value, i + 1)
                self.progress_update.emit(int((i + 1) / self.num_measurements * 100))
                
                # Wait for sampling interval
                if i < self.num_measurements - 1:  # Don't wait after last measurement
                    self.msleep(int(self.sampling_interval * 1000))
            
            instrument.close()
            self.measurement_complete.emit(self.measurements)
            
        except Exception as e:
            self.error_occurred.emit(f"Error: {str(e)}")
    
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
        
        # Style the plot
        self.axes.set_facecolor('#f8f9fa')
        self.axes.tick_params(colors='#2c3e50', which='both')
        self.axes.spines['bottom'].set_color('#2c3e50')
        self.axes.spines['top'].set_color('#2c3e50')
        self.axes.spines['left'].set_color('#2c3e50')
        self.axes.spines['right'].set_color('#2c3e50')
        self.axes.xaxis.label.set_color('#2c3e50')
        self.axes.yaxis.label.set_color('#2c3e50')
        self.axes.title.set_color('#2c3e50')
        
        self.measurements = []
        self.measurement_unit = "V"
        # self.scaling_factor = 1.0  <-- Removed
        self.plot_data()
    
    def plot_data(self):
        """Update the plot with current measurements"""
        self.axes.clear()
        
        if self.measurements:
            # Determine appropriate scale based on max value
            max_val = max([abs(x) for x in self.measurements])
            
            # Logic: Default to mV. If > 1000 mV (1.0 V), switch to V
            # Only applying for Voltage currently based on user request
            if self.measurement_unit == "V":
                if max_val >= 1.0:
                     scale_unit = "V"
                     scale_factor = 1.0
                else:
                     scale_unit = "mV"
                     scale_factor = 1000.0
            else:
                 scale_unit = self.measurement_unit
                 scale_factor = 1.0

            # Apply scaling
            scaled_measurements = [x * scale_factor for x in self.measurements]
            x = list(range(1, len(scaled_measurements) + 1))
            self.axes.plot(x, scaled_measurements, 'o-', color='#d1d5db', linewidth=2.5, markersize=8)
            
            # Make labels and title larger and clearer
            self.axes.set_xlabel('Measurement Number', fontsize=12, color='#3c4043', fontweight='bold', labelpad=10)
            self.axes.set_ylabel(f'Value ({scale_unit})', fontsize=12, color='#3c4043', fontweight='bold', labelpad=10)
            self.axes.set_title('Real-time Measurements', fontsize=14, color='#202124', fontweight='bold', pad=15)
            
            # Improved grid
            self.axes.grid(True, which='major', linestyle='-', alpha=0.9, color='#e8eaed')
            self.axes.grid(True, which='minor', linestyle=':', alpha=0.6, color='#e8eaed')
            self.axes.minorticks_on()
            
            # Add statistics with better styling
            if len(scaled_measurements) > 1:
                avg = sum(scaled_measurements) / len(scaled_measurements)
                self.axes.axhline(y=avg, color='#e74c3c', linestyle='--', linewidth=2, 
                                label=f'Average: {avg:.6f} {scale_unit}')
                legend = self.axes.legend(facecolor='#ffffff', edgecolor='#e8eaed', 
                                        labelcolor='#3c4043', fontsize=10, loc='best')
                legend.get_frame().set_linewidth(1)
                
            # Add padding to margins
            self.axes.margins(x=0.05, y=0.1)
            
        else:
            self.axes.text(0.5, 0.5, 'No data yet', 
                          horizontalalignment='center',
                          verticalalignment='center',
                          transform=self.axes.transAxes,
                          fontsize=16, color='#9ca3af', fontweight='bold')
            self.axes.set_xlabel('Measurement Number', fontsize=12, color='#3c4043')
            self.axes.set_ylabel(f'Value ({self.measurement_unit})', fontsize=12, color='#3c4043')
        
        self.fig.tight_layout(pad=2.0)
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
        self.measurement_unit = unit
        self.plot_data()

    # Scaling factor method removed


class DigitalMultimeterGUI(QMainWindow):
    """Main GUI window for Digital Multimeter application"""
    
    def __init__(self):
        super().__init__()
        self.measurement_thread = None
        self.all_measurements = []
        self.current_measurement_type = "DC Voltage"
        
        # Range definitions mapping: Type -> List of (Range Name, Unit, SCPI Command Value)
        # Using base units (V, A, Ω) for all ranges since we display raw values
        self.range_map = {
            "DC Voltage": [
                ("Auto", "V", "AUTO"), ("100 mV", "V", "0.1"), ("1 V", "V", "1"), 
                ("10 V", "V", "10"), ("100 V", "V", "100"), ("1000 V", "V", "1000")
            ],
            "AC Voltage": [
                ("Auto", "V", "AUTO"), ("100 mV", "V", "0.1"), ("1 V", "V", "1"), 
                ("10 V", "V", "10"), ("100 V", "V", "100"), ("1000 V", "V", "1000")
            ],
            "DC Current": [
                ("Auto", "A", "AUTO"), ("100 μA", "A", "1e-4"), ("1 mA", "A", "1e-3"), 
                ("10 mA", "A", "1e-2"), ("100 mA", "A", "0.1"), ("1 A", "A", "1"), ("3 A", "A", "3")
            ],
            "AC Current": [
                ("Auto", "A", "AUTO"), ("100 μA", "A", "1e-4"), ("1 mA", "A", "1e-3"), 
                ("10 mA", "A", "1e-2"), ("100 mA", "A", "0.1"), ("1 A", "A", "1"), ("3 A", "A", "3")
            ],
            "Resistance": [
                ("Auto", "Ω", "AUTO"), ("100 Ω", "Ω", "100"), ("1 kΩ", "Ω", "1e3"), 
                ("10 kΩ", "Ω", "1e4"), ("100 kΩ", "Ω", "1e5"), ("1 MΩ", "Ω", "1e6"), 
                ("10 MΩ", "Ω", "1e7"), ("100 MΩ", "Ω", "1e8")
            ],
            "4-Wire Resistance": [
                ("Auto", "Ω", "AUTO"), ("100 Ω", "Ω", "100"), ("1 kΩ", "Ω", "1e3"), 
                ("10 kΩ", "Ω", "1e4"), ("100 kΩ", "Ω", "1e5"), ("1 MΩ", "Ω", "1e6"), 
                ("10 MΩ", "Ω", "1e7"), ("100 MΩ", "Ω", "1e8")
            ],
            "Continuity": [
                ("Auto", "Ω", "AUTO")
            ]
        }
        
        self.init_ui()
    
    def format_value_with_unit(self, value, base_unit):
        """Format value with appropriate scaled unit for display
        
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
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("FLUKE 8846A Precision Multimeter Control Panel")
        self.setGeometry(100, 100, 1200, 800)
        
        # Set light theme
        self.set_light_theme()
        
        # Create central widget (Scroll Area)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Apply custom scrollbar styling
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
        
        self.setCentralWidget(scroll)
        
        # Create content widget
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("📟 FLUKE 8846A Precision Multimeter Control Panel")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1a73e8; margin: 10px;")
        main_layout.addWidget(title_label)
        
        # Connection Group
        connection_group = self.create_connection_group()
        main_layout.addWidget(connection_group)
        
        # Measurement Type Group
        type_group = self.create_measurement_type_group()
        main_layout.addWidget(type_group)
        
        # Measurement Settings Group
        settings_group = self.create_settings_group()
        main_layout.addWidget(settings_group)
        
        # Control Buttons
        control_layout = self.create_control_buttons()
        main_layout.addLayout(control_layout)
        
        # Progress Bar
        self.progress_bar = QProgressBar()
        self.progress_bar.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 2px solid #d1d5db;
                border-radius: 5px;
                text-align: center;
                background-color: #f8f9fa;
                color: #3c4043;
                font-weight: bold;
            }
            QProgressBar::chunk {
                background-color: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                                  stop:0 #d1d5db, stop:1 #4285f4);
                border-radius: 3px;
            }
        """)
        main_layout.addWidget(self.progress_bar)
        
        # Results and Graph Layout
        results_layout = QHBoxLayout()
        
        # Results Text Area
        results_group = QGroupBox("📊 Measurement Results")
        results_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        results_group.setStyleSheet(self.get_groupbox_style())
        results_layout_inner = QVBoxLayout()
        
        self.results_text = QTextEdit()
        self.results_text.setReadOnly(True)
        self.results_text.setMinimumHeight(400) # Increased height to force scrolling
        self.results_text.setFont(QFont("Consolas", 10))
        self.results_text.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                color: #3c4043;
                border: 2px solid #d1d5db;
                border-radius: 5px;
                padding: 10px;
            }
        """)
        results_layout_inner.addWidget(self.results_text)
        results_group.setLayout(results_layout_inner)
        results_layout.addWidget(results_group, 2)  # Ratio 2 for text
        
        # Graph
        if MATPLOTLIB_AVAILABLE:
            graph_group = QGroupBox("📈 Live Graph")
            graph_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
            graph_group.setStyleSheet(self.get_groupbox_style())
            graph_layout = QVBoxLayout()
            
            self.plot_canvas = PlotCanvas(self, width=6, height=5, dpi=100) # Increased default height
            self.plot_canvas.setMinimumHeight(400) # Ensure minimum height
            graph_layout.addWidget(self.plot_canvas)
            graph_group.setLayout(graph_layout)
            results_layout.addWidget(graph_group, 5)  # INCREASED Ratio to 5 for graph (much wider)
        
        main_layout.addLayout(results_layout, 1)
        
        # Status Bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                color: #5f6368;
                font-weight: 500;
                border-top: 1px solid #e8eaed;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready to connect...")
        
        # Check dependencies
        self.check_dependencies()
    
    def create_connection_group(self):
        """Create connection settings group"""
        group = QGroupBox("🔌 Instrument Connection")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QHBoxLayout()
        
        # Resource name
        resource_label = QLabel("VISA Resource:")
        resource_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(resource_label)
        
        self.resource_combo = QComboBox()
        self.resource_combo.setEditable(True)
        self.resource_combo.setFont(QFont("Segoe UI", 10))
        self.resource_combo.setStyleSheet(self.get_input_style())
        self.resource_combo.addItems([
            "GPIB0::2::INSTR",
            "USB0::0x2A8D::0x0101::MY12345678::INSTR",
            "TCPIP0::192.168.1.101::INSTR"
        ])
        layout.addWidget(self.resource_combo, 1)
        
        # Refresh button
        refresh_btn = QPushButton("🔄 Refresh")
        refresh_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        refresh_btn.setStyleSheet(self.get_button_style("#6c5ce7"))
        refresh_btn.clicked.connect(self.refresh_resources)
        layout.addWidget(refresh_btn)
        
        # Test connection button
        test_btn = QPushButton("🔍 Test Connection")
        test_btn.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        test_btn.setStyleSheet(self.get_button_style("#d1d5db"))
        test_btn.clicked.connect(self.test_connection)
        layout.addWidget(test_btn)
        
        group.setLayout(layout)
        return group
    
        group.setLayout(layout)
        return group
    
    def create_measurement_type_group(self):
        """Create measurement type selection group"""
        group = QGroupBox("📏 Measurement Type")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QHBoxLayout()
        
        # Create button group for radio buttons
        self.type_button_group = QButtonGroup()
        
        # Measurement types
        types = [
            ("⚡ DC Voltage", "DC Voltage", "V"),
            ("〜 AC Voltage", "AC Voltage", "V"),
            ("⚡ DC Current", "DC Current", "A"),
            ("〜 AC Current", "AC Current", "A"),
            ("🔧 Resistance (2W)", "Resistance", "Ω"),
            ("🔧 Resistance (4W)", "4-Wire Resistance", "Ω"),
            ("🔊 Continuity", "Continuity", "Ω")
        ]
        
        for i, (label, type_name, unit) in enumerate(types):
            radio = QRadioButton(label)
            radio.setFont(QFont("Segoe UI", 10))
            radio.setStyleSheet("""
                QRadioButton {
                    color: #2c3e50;
                    padding: 5px;
                }
                QRadioButton::indicator {
                    width: 18px;
                    height: 18px;
                }
                QRadioButton::indicator:checked {
                    background-color: #1a73e8;
                    border: 2px solid #1a73e8;
                    border-radius: 9px;
                }
            """)
            radio.toggled.connect(lambda checked, t=type_name, u=unit: self.on_type_changed(checked, t, u))
            self.type_button_group.addButton(radio, i)
            layout.addWidget(radio)
            
            if i == 0:  # Set DC Voltage as default
                radio.setChecked(True)
        
        group.setLayout(layout)
        return group
    
    def create_settings_group(self):
        """Create measurement settings group"""
        group = QGroupBox("⚙️ Measurement Settings")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QHBoxLayout()
        layout.setSpacing(15)
        
        # 1. Number of Measurements
        num_layout = QHBoxLayout()
        num_label = QLabel("Number of Measurements:")
        num_label.setFont(QFont("Segoe UI", 10))
        num_layout.addWidget(num_label)
        
        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setMinimum(1)
        self.num_measurements_spin.setMaximum(100000)
        self.num_measurements_spin.setValue(10)
        self.num_measurements_spin.setFont(QFont("Segoe UI", 10))
        self.num_measurements_spin.setStyleSheet(self.get_spinbox_style())
        self.num_measurements_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.num_measurements_spin.setMinimumWidth(100)
        num_layout.addWidget(self.num_measurements_spin)
        layout.addLayout(num_layout)
        
        # Separator
        line = QFrame()
        line.setFrameShape(QFrame.Shape.VLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        line.setStyleSheet("background-color: #dadce0;")
        layout.addWidget(line)

        # 2. Sampling Mode Selector
        mode_label = QLabel("Sampling Mode:")
        mode_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setFont(QFont("Segoe UI", 10))
        self.mode_combo.setStyleSheet(self.get_input_style())
        self.mode_combo.addItems(["-- Select Mode --", "Integration", "NPLC"])
        self.mode_combo.setMinimumWidth(140)
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo)
        
        layout.addSpacing(10)

        # 3. Integration Time Inputs (Visible only in Integration Mode)
        self.int_label = QLabel("Integration:")
        self.int_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.int_label)
        
        self.int_time_spin = QDoubleSpinBox()
        self.int_time_spin.setMinimum(0.1)
        self.int_time_spin.setMaximum(3600.0) # 1 hour max in seconds initially
        self.int_time_spin.setValue(1.0)
        self.int_time_spin.setDecimals(1)
        self.int_time_spin.setSingleStep(0.5)
        self.int_time_spin.setFont(QFont("Segoe UI", 10))
        self.int_time_spin.setStyleSheet(self.get_spinbox_style())
        self.int_time_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.int_time_spin.setMinimumWidth(80)
        layout.addWidget(self.int_time_spin)
        
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.setFont(QFont("Segoe UI", 10))
        self.time_unit_combo.setStyleSheet(self.get_input_style())
        self.time_unit_combo.addItems(["sec", "min", "hour"])
        self.time_unit_combo.setMinimumWidth(70)
        layout.addWidget(self.time_unit_combo)

        # 4. NPLC Input (Visible only in NPLC Mode)
        self.nplc_label = QLabel("NPLC:")
        self.nplc_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.nplc_label)
        
        self.nplc_spin = QDoubleSpinBox()
        self.nplc_spin.setMinimum(0.02)
        self.nplc_spin.setMaximum(100.0)
        self.nplc_spin.setValue(10.0)
        self.nplc_spin.setDecimals(2)
        self.nplc_spin.setSingleStep(1.0)
        self.nplc_spin.setFont(QFont("Segoe UI", 10))
        self.nplc_spin.setStyleSheet(self.get_spinbox_style())
        self.nplc_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.nplc_spin.setMinimumWidth(80)
        layout.addWidget(self.nplc_spin)
        
        # NPLC Sampling Enable Checkbox
        self.nplc_sampling_check = QCheckBox("Sampling:")
        self.nplc_sampling_check.setFont(QFont("Segoe UI", 10))
        self.nplc_sampling_check.setChecked(True)  # Enabled by default
        self.nplc_sampling_check.setStyleSheet(self.get_checkbox_style())
        self.nplc_sampling_check.toggled.connect(self.toggle_nplc_sampling)
        layout.addWidget(self.nplc_sampling_check)
        
        # NPLC Sampling Status Label
        self.nplc_sampling_status = QLabel("Enabled")
        self.nplc_sampling_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.nplc_sampling_status.setStyleSheet("color: #34a853;")  # Green for enabled
        layout.addWidget(self.nplc_sampling_status)
        
        layout.addSpacing(10)
        
        # Sniffing Mode Enable Checkbox
        self.sniffing_enable_check = QCheckBox("Sniffing:")
        self.sniffing_enable_check.setFont(QFont("Segoe UI", 10))
        self.sniffing_enable_check.setChecked(False)  # Disabled by default
        self.sniffing_enable_check.setStyleSheet(self.get_checkbox_style())
        self.sniffing_enable_check.toggled.connect(self.toggle_sniffing_mode)
        layout.addWidget(self.sniffing_enable_check)
        
        # Sniffing Status Label
        self.sniffing_status = QLabel("Disable")
        self.sniffing_status.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.sniffing_status.setStyleSheet("color: #9aa0a6;")  # Gray for disabled
        layout.addWidget(self.sniffing_status)
        
        # Sniffing Interval Spinbox
        self.sniffing_spin = QDoubleSpinBox()
        self.sniffing_spin.setMinimum(0.1)
        self.sniffing_spin.setMaximum(3600.0)
        self.sniffing_spin.setValue(1.0)
        self.sniffing_spin.setDecimals(2)
        self.sniffing_spin.setFont(QFont("Segoe UI", 10))
        self.sniffing_spin.setMinimumWidth(80)
        self.sniffing_spin.setStyleSheet(self.get_disabled_spinbox_style())  # Disabled style by default
        self.sniffing_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.sniffing_spin.setEnabled(False)  # Disabled by default
        layout.addWidget(self.sniffing_spin)
        
        # Sniffing Unit Dropdown
        self.sniffing_unit_combo = QComboBox()
        self.sniffing_unit_combo.setFont(QFont("Segoe UI", 10))
        self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())  # Disabled style by default
        self.sniffing_unit_combo.addItems(["sec", "min", "hour"])
        self.sniffing_unit_combo.setEnabled(False)  # Disabled by default
        layout.addWidget(self.sniffing_unit_combo)

        # 5. NDIG (Resolution)
        ndig_label = QLabel("NDIG:")
        ndig_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(ndig_label)
        
        self.digit_combo = QComboBox()
        self.digit_combo.setFont(QFont("Segoe UI", 10))
        self.digit_combo.setStyleSheet(self.get_input_style())
        self.digit_combo.addItems(["4", "5", "6", "7", "8"])
        self.digit_combo.setCurrentText("8")
        self.digit_combo.setMinimumWidth(50)
        layout.addWidget(self.digit_combo)
        
        layout.addSpacing(15)
        
        # Range
        range_label = QLabel("Range:")
        range_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(range_label)
        
        self.range_combo = QComboBox()
        self.range_combo.setFont(QFont("Segoe UI", 10))
        self.range_combo.setStyleSheet(self.get_input_style())
        self.range_combo.setMinimumWidth(100)
        self.range_combo.currentIndexChanged.connect(self.on_range_changed)
        layout.addWidget(self.range_combo)
        
        layout.addSpacing(15)
        
        # Auto Zero
        self.auto_zero_check = QCheckBox("Auto Zero")
        self.auto_zero_check.setFont(QFont("Segoe UI", 10))
        self.auto_zero_check.setChecked(True)  # Default ON
        self.auto_zero_check.setStyleSheet("""
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
                image: url(none);
            }
        """)
        layout.addWidget(self.auto_zero_check)

        # 6. Offset Compensation
        self.offset_comp_check = QCheckBox("Offset Comp")
        self.offset_comp_check.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.offset_comp_check.setStyleSheet("""
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
                image: url(none);
            }
        """)
        layout.addWidget(self.offset_comp_check)
        
        layout.addStretch()
        
        # Initialize visibility
        self.on_mode_changed("-- Select Mode --")
        
        # Initialize ranges for default type
        self.update_range_options("DC Voltage")
        
        group.setLayout(layout)
        return group

    def on_mode_changed(self, mode_text):
        """Handle sampling mode changes to show/hide relevant controls"""
        is_integration = (mode_text == "Integration")
        is_nplc = (mode_text == "NPLC")
        has_mode = is_integration or is_nplc
        
        # Integration controls
        self.int_label.setVisible(is_integration)
        self.int_time_spin.setVisible(is_integration)
        self.time_unit_combo.setVisible(is_integration)
        self.int_label.setEnabled(is_integration)
        self.int_time_spin.setEnabled(is_integration)
        self.time_unit_combo.setEnabled(is_integration)
        
        # NPLC controls
        self.nplc_label.setVisible(is_nplc)
        self.nplc_spin.setVisible(is_nplc)
        
        # NPLC Sampling checkbox and status
        if hasattr(self, 'nplc_sampling_check'):
            self.nplc_sampling_check.setVisible(is_nplc)
        if hasattr(self, 'nplc_sampling_status'):
            self.nplc_sampling_status.setVisible(is_nplc)
        
        # Enable/disable NPLC controls based on mode and sampling checkbox
        if is_nplc:
            is_sampling_enabled = self.nplc_sampling_check.isChecked() if hasattr(self, 'nplc_sampling_check') else True
            self.nplc_label.setEnabled(is_sampling_enabled)
            self.nplc_spin.setEnabled(is_sampling_enabled)
        else:
            self.nplc_label.setEnabled(False)
            self.nplc_spin.setEnabled(False)
        
        # Sniffing controls visibility (only in NPLC mode)
        if hasattr(self, 'sniffing_enable_check'):
            self.sniffing_enable_check.setVisible(is_nplc)
        if hasattr(self, 'sniffing_status'):
            self.sniffing_status.setVisible(is_nplc)
        if hasattr(self, 'sniffing_spin'):
            self.sniffing_spin.setVisible(is_nplc)
        if hasattr(self, 'sniffing_unit_combo'):
            self.sniffing_unit_combo.setVisible(is_nplc)
        
        # Disable start button if no mode selected (logic can be in start_measurement too)
        # But visually, let's keep it clean
    
    def toggle_nplc_sampling(self, checked):
        """Toggle NPLC sampling mode on/off with animated gray effect"""
        if checked:
            # ENABLED - Normal colors with green status
            self.nplc_sampling_status.setText("Enabled")
            self.nplc_sampling_status.setStyleSheet("""
                QLabel {
                    color: #34a853;
                    font-weight: bold;
                }
            """)
            
            # Enable NPLC controls
            self.nplc_label.setStyleSheet("color: #3c4043;")
            self.nplc_spin.setEnabled(True)
            self.nplc_spin.setStyleSheet(self.get_spinbox_style())
        else:
            # DISABLED - Gray colors with "Disable" status
            self.nplc_sampling_status.setText("Disable")
            self.nplc_sampling_status.setStyleSheet("""
                QLabel {
                    color: #9aa0a6;
                    font-weight: bold;
                }
            """)
            
            # Disable NPLC controls with gray style
            self.nplc_label.setStyleSheet("color: #9aa0a6;")
            self.nplc_spin.setEnabled(False)
            self.nplc_spin.setStyleSheet(self.get_disabled_spinbox_style())
    
    def toggle_sniffing_mode(self, checked):
        """Toggle Sniffing mode on/off with gray effect"""
        if checked:
            # ENABLED - Normal colors with green status
            self.sniffing_status.setText("Enabled")
            self.sniffing_status.setStyleSheet("""
                QLabel {
                    color: #34a853;
                    font-weight: bold;
                }
            """)
            
            # Enable Sniffing controls
            self.sniffing_spin.setEnabled(True)
            self.sniffing_spin.setStyleSheet(self.get_spinbox_style())
            self.sniffing_unit_combo.setEnabled(True)
            self.sniffing_unit_combo.setStyleSheet(self.get_input_style())
        else:
            # DISABLED - Gray colors with "Disable" status
            self.sniffing_status.setText("Disable")
            self.sniffing_status.setStyleSheet("""
                QLabel {
                    color: #9aa0a6;
                    font-weight: bold;
                }
            """)
            
            # Disable Sniffing controls with gray style
            self.sniffing_spin.setEnabled(False)
            self.sniffing_spin.setStyleSheet(self.get_disabled_spinbox_style())
            self.sniffing_unit_combo.setEnabled(False)
            self.sniffing_unit_combo.setStyleSheet(self.get_disabled_input_style())
    
    def create_control_buttons(self):
        """Create control buttons layout"""
        layout = QHBoxLayout()
        
        # Start button
        self.start_btn = QPushButton("▶️ Start Measurement")
        self.start_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setStyleSheet(self.get_button_style("#d1d5db"))
        self.start_btn.clicked.connect(self.start_measurement)
        layout.addWidget(self.start_btn)
        
        # Stop button
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setStyleSheet(self.get_button_style("#e74c3c"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        layout.addWidget(self.stop_btn)
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        clear_btn.setMinimumHeight(50)
        clear_btn.setStyleSheet(self.get_button_style("#f39c12"))
        clear_btn.clicked.connect(self.clear_results)
        layout.addWidget(clear_btn)
        
        # Save and Open CSV button
        save_open_btn = QPushButton("💾 Save & Open CSV")
        save_open_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        save_open_btn.setMinimumHeight(50)
        save_open_btn.setStyleSheet(self.get_button_style("#1967d2"))
        save_open_btn.clicked.connect(self.save_and_open_csv)
        layout.addWidget(save_open_btn)
        
        return layout
    
    def on_type_changed(self, checked, type_name, unit):
        """Handle measurement type change"""
        if checked:
            self.current_measurement_type = type_name
            self.update_range_options(type_name)
            
            # Default unit is base unit, range selection will update if specific
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
                self.plot_canvas.set_unit(unit)
                # Clear graph when type changes to avoid confusion
                self.plot_canvas.clear_measurements()
                
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Measurement type: {type_name}")
                
    def update_range_options(self, type_name):
        """Update range combo box based on measurement type"""
        if not hasattr(self, 'range_combo'):
            return
            
        self.range_combo.blockSignals(True)
        self.range_combo.clear()
        
        if type_name in self.range_map:
            for name, unit, val in self.range_map[type_name]:
                self.range_combo.addItem(name, userData=unit)
        
        self.range_combo.blockSignals(False)
        # Trigger update of unit based on default selection (usually Auto)
        self.on_range_changed(0)

    def on_range_changed(self, index):
        """Handle range selection change to update units"""
        if index < 0:
            return
            
        unit = self.range_combo.itemData(index)
        if unit:
            if MATPLOTLIB_AVAILABLE and hasattr(self, 'plot_canvas'):
                self.plot_canvas.set_unit(unit)
                # self.plot_canvas.set_scaling_factor(scaling_factor) <-- Removed
    
    # get_scaling_factor removed
    
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
            QLabel {
                color: #3c4043;
            }
        """)
    
    def get_groupbox_style(self):
        """Get stylesheet for group boxes"""
        return """
            QGroupBox {
                border: 2px solid #e8eaed;
                border-radius: 8px;
                margin-top: 10px;
                padding-top: 10px;
                background-color: #ffffff;
                color: #1a73e8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 5px;
            }
        """
    
    def get_input_style(self):
        """Get stylesheet for input widgets"""
        return """
            QComboBox, QSpinBox, QLineEdit, QDoubleSpinBox {
                background-color: #ffffff;
                color: #3c4043;
                border: 2px solid #d1d5db;
                border-radius: 5px;
                padding: 5px;
                min-height: 25px;
            }
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover, QDoubleSpinBox:hover {
                border-color: #4285f4;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #d1d5db;
                margin-right: 5px;
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
                background-color: #d1d5db;
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
                border: 2px solid #d1d5db;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #d1d5db;
                background-color: #f8f9fa;
            }
            
            /* Up Button (Plus) */
            QSpinBox::up-button, QDoubleSpinBox::up-button {
                subcontrol-origin: border;
                subcontrol-position: right;
                width: 28px;
                border-left: 1px solid #dadce0;
                border-top-right-radius: 6px;
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
                border-bottom: 6px solid #d1d5db;
                margin-bottom: 2px;
            }
            QSpinBox::up-arrow:hover, QDoubleSpinBox::up-arrow:hover {
                border-bottom: 6px solid #174ea6;
            }
            
            /* Down Button (Minus) */
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
                border-top: 6px solid #d1d5db;
                margin-top: 2px;
            }
            QSpinBox::down-arrow:hover, QDoubleSpinBox::down-arrow:hover {
                border-top: 6px solid #174ea6;
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
                border: 2px solid #1a73e8;
            }
            QCheckBox::indicator:checked {
                background-color: #1a73e8;
                border: 2px solid #1a73e8;
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
            
            # Always add default resource first
            default_resource = "GPIB0::2::INSTR"
            self.resource_combo.addItem(default_resource)
            
            if resources:
                # Add other resources (skip if it's the same as default)
                for resource in resources:
                    if resource != default_resource:
                        self.resource_combo.addItem(resource)
                
                self.status_bar.showMessage(f"Found {len(resources)} resource(s)")
                QMessageBox.information(self, "Resources Found", 
                                      f"Found {len(resources)} VISA resource(s):\n" + "\n".join(resources))
            else:
                # No resources found, but default is already added
                self.status_bar.showMessage("No resources found, using default")
                QMessageBox.warning(self, "No Resources", "No VISA resources found!\nUsing default: GPIB0::2::INSTR")
        except Exception as e:
            # On error, still add default
            self.resource_combo.clear()
            self.resource_combo.addItem("GPIB0::2::INSTR")
            QMessageBox.critical(self, "Error", f"Failed to list resources:\n{str(e)}\nUsing default: GPIB0::2::INSTR")
    
    def test_connection(self):
        """Test connection to the instrument"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name or resource_name == "No resources found":
            QMessageBox.warning(self, "Error", "Please select a valid resource!")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            # Query instrument identification
            idn = instrument.query("*IDN?")
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
                    background-color: #d1d5db;
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
            
            self.status_bar.showMessage("✅ Connection test successful!")
            self.results_text.append(f"✅ Connected to: {idn.strip()}\n")
            
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
            self.status_bar.showMessage("❌ Connection test failed!")
    
    def start_measurement(self):
        """Start measurement process"""
        
        # Get settings from UI
        resource_name = self.resource_combo.currentText()
        num_measurements = self.num_measurements_spin.value()
        sampling_interval = 1.0  # Default 1 second interval
        auto_zero = self.auto_zero_check.isChecked()
        offset_comp = self.offset_comp_check.isChecked()
        
        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.all_measurements = []
        
        # Clear previous graph
        if MATPLOTLIB_AVAILABLE:
            self.plot_canvas.clear_measurements()
        
        # Start measurement thread with all settings
        self.measurement_thread = MeasurementThread(
            resource_name, 
            num_measurements, 
            self.current_measurement_type, 
            sampling_interval,
            auto_zero,
            offset_comp
        )
        self.measurement_thread.measurement_ready.connect(self.on_measurement_ready)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        self.measurement_thread.progress_update.connect(self.progress_bar.setValue)
        self.measurement_thread.start()
        
        self.status_bar.showMessage("Measurement in progress...")
        self.results_text.append(f"\n{'='*60}")
        self.results_text.append(f"Starting {num_measurements} measurements at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.results_text.append(f"Measurement Type: {self.current_measurement_type}")
        self.results_text.append(f"Sampling Interval: {sampling_interval} seconds")
        self.results_text.append(f"Auto Zero: {'ON' if auto_zero else 'OFF'}")
        self.results_text.append(f"Offset Compensation: {'ON' if offset_comp else 'OFF'}")
        self.results_text.append(f"{'='*60}\n")
    
    def stop_measurement(self):
        """Stop ongoing measurement"""
        if self.measurement_thread:
            self.measurement_thread.stop()
            self.measurement_thread.wait()
        
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_bar.showMessage("Measurement stopped by user")
        self.results_text.append("\n⏹️ Measurement stopped by user\n")
    
    def on_measurement_ready(self, value, measurement_num):
        """Handle new measurement data"""
        self.all_measurements.append(value)
        
        # Get base unit
        base_unit = "V"
        if "Voltage" in self.current_measurement_type:
            base_unit = "V"
        elif "Current" in self.current_measurement_type:
            base_unit = "A"
        elif "Resistance" in self.current_measurement_type:
             base_unit = "Ω"
             
        # Auto-scaling for display
        scaled_value = value
        disp_unit = base_unit
        
        if base_unit == "V":
             if abs(value) < 1.0:
                 scaled_value = value * 1000.0
                 disp_unit = "mV"
             else:
                 scaled_value = value
                 disp_unit = "V"
        
        self.results_text.append(f"Measurement #{measurement_num}: {scaled_value:.6f} {disp_unit}")
        
        if MATPLOTLIB_AVAILABLE:
            self.plot_canvas.add_measurement(value)
    
    def on_measurement_complete(self, measurements):
        """Handle measurement completion"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # Get unit
        index = self.range_combo.currentIndex()
        if index >= 0:
            unit = self.range_combo.itemData(index) or "V"
        else:
             unit = "V"
             
        # Calculate statistics
        if measurements:
            # Determine scaling based on average value
            avg_raw = sum(measurements) / len(measurements)
            
            # Base unit detection
            base_unit = "V"
            if "Current" in self.current_measurement_type:
                base_unit = "A"
            elif "Resistance" in self.current_measurement_type:
                 base_unit = "Ω"

            scale_unit = base_unit
            scale_factor = 1.0

            # Apply auto-scaling for Voltage logic based on average
            if base_unit == "V":
                 if abs(avg_raw) < 1.0:
                     scale_factor = 1000.0
                     scale_unit = "mV"
                 else:
                     scale_factor = 1.0
                     scale_unit = "V"
            
            # Scale all measurements for stats
            scaled_measurements = [x * scale_factor for x in measurements]
            
            avg = sum(scaled_measurements) / len(scaled_measurements)
            min_val = min(scaled_measurements)
            max_val = max(scaled_measurements)
            
            if len(scaled_measurements) > 1:
                variance = sum((x - avg) ** 2 for x in scaled_measurements) / (len(scaled_measurements) - 1)
                std_dev = variance ** 0.5
            else:
                std_dev = 0
            
            self.results_text.append(f"\n{'='*60}")
            self.results_text.append("📊 STATISTICS:")
            self.results_text.append(f"{'='*60}")
            self.results_text.append(f"Total Measurements: {len(scaled_measurements)}")
            self.results_text.append(f"Average:            {avg:.6f} {scale_unit}")
            self.results_text.append(f"Minimum:            {min_val:.6f} {scale_unit}")
            self.results_text.append(f"Maximum:            {max_val:.6f} {scale_unit}")
            self.results_text.append(f"Std Deviation:      {std_dev:.6f} {scale_unit}")
            self.results_text.append(f"{'='*60}\n")
        
        self.status_bar.showMessage(f"Measurement complete! {len(measurements)} readings taken.")
        
        # Auto-save and open CSV file
        self.auto_save_and_open_csv()
    
    def on_error(self, error_message):
        """Handle errors from measurement thread"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        
        QMessageBox.critical(self, "Measurement Error", error_message)
        self.results_text.append(f"\n❌ ERROR: {error_message}\n")
        self.status_bar.showMessage("Error occurred during measurement")
    
    def clear_results(self):
        """Clear all results"""
        self.results_text.clear()
        self.all_measurements = []
        self.progress_bar.setValue(0)
        
        if MATPLOTLIB_AVAILABLE:
            self.plot_canvas.clear_measurements()
        
        self.status_bar.showMessage("Results cleared")
        self.check_dependencies()
    
    def close_csv_file(self, file_path):
        """Close the CSV file if it's open in Excel (Windows only)"""
        if sys.platform == 'win32':
            try:
                import subprocess
                import time
                filename = Path(file_path).name
                
                # Method 1: Taskkill by Window Title (Most effective without external libs)
                # Excel window title usually contains the filename
                # /FI "WINDOWTITLE eq latest_output.csv - Excel" or similar
                # We use asterisk for partial match
                subprocess.run(f'taskkill /F /FI "WINDOWTITLE eq {filename}*"', 
                             shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                # Also try matching just the name without extension if Excel hides it
                name_only = Path(file_path).stem
                subprocess.run(f'taskkill /F /FI "WINDOWTITLE eq {name_only}*"', 
                             shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)

                # Wait a bit for the process to die and handle to be released
                time.sleep(0.5)
                
            except Exception:
                pass

    def save_and_open_csv(self):
        """Save measurements to latest_output.csv and open it automatically"""
        if not self.all_measurements:
            QMessageBox.warning(self, "No Data", "No measurements to save!")
            return
        
        # Get unit
        # Get unit
        index = self.range_combo.currentIndex()
        if index >= 0:
            unit = self.range_combo.itemData(index) or "V"
        else:
             unit = "V"
        
        # Explicitly set output directory
        output_dir = Path(r"E:\Cal-Lab\Measurement_Results")
        
        # Ensure directory exists
        if not output_dir.exists():
            try:
                output_dir.mkdir(parents=True, exist_ok=True)
            except Exception as e:
                self.status_bar.showMessage(f"Error creating folder: {str(e)}")
                return

        # Target filename
        base_filename = "latest_output.csv"
        final_path = output_dir / base_filename
        
        # Try to save, if locked, try closing again, if still locked, use timestamped name
        max_retries = 3
        save_success = False
        
        for attempt in range(max_retries):
            try:
                # Attempt to write
                with open(final_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    self.write_csv_content(csvfile, unit)
                save_success = True
                break
            except PermissionError:
                # File is locked
                if attempt == 0:
                    # First failure: Try checking/closing file again aggressively
                    self.close_csv_file(final_path)
                    time.sleep(0.5)
                elif attempt == max_retries - 1:
                    # Last failure: Change filename to avoid error
                    timestamp = datetime.now().strftime('%H%M%S')
                    # IMPORTANT: Use output_dir here too
                    final_path = output_dir / f"latest_output_{timestamp}.csv"
                    try:
                        with open(final_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                            self.write_csv_content(csvfile, unit)
                        save_success = True
                        self.status_bar.showMessage(f"File locked, saved as {final_path.name} instead")
                    except Exception as e:
                        QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
                        return
            except Exception as e:
                # If directory issue or other, might fail
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
                return
            except Exception as e:
                # If directory issue or other, might fail
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
                return
        
        if save_success:
            # Open the file automatically
            import os
            try:
                if sys.platform == 'win32':
                    os.startfile(str(final_path))
                elif sys.platform == 'darwin':
                    os.system(f'open "{final_path}"')
                else:
                    os.system(f'xdg-open "{final_path}"')
                
                self.status_bar.showMessage(f"Saved and opened: {final_path.name}")
                self.results_text.append(f"\n💾 Data saved to: {final_path}")
                self.results_text.append(f"📂 File opened automatically\n")
            except Exception as e:
                self.status_bar.showMessage(f"Saved but failed to open: {str(e)}")

    def write_csv_content(self, csvfile, unit):
        """Helper to write CSV content"""
        writer = csv.writer(csvfile)
        now = datetime.now()
        
        if not self.all_measurements:
            return

        # 1. Calculate Global Scaling based on Average (same as Total Result)
        avg_raw = sum(self.all_measurements) / len(self.all_measurements)
        
        base_unit = "V"
        if "Current" in self.current_measurement_type:
            base_unit = "A"
        elif "Resistance" in self.current_measurement_type:
             base_unit = "Ω"

        scale_unit = base_unit
        scale_factor = 1.0

        if base_unit == "V":
             if abs(avg_raw) < 1.0:
                 scale_factor = 1000.0
                 scale_unit = "mV"
             else:
                 scale_factor = 1.0
                 scale_unit = "V"

        # 2. Revert to Horizontal Layout with Unit at the specific placement
        # User request: "Record excel values horizontally, put unit at the very end"
        
        # Row 1: Measurement numbers
        measurement_numbers = ['Measurement'] + [str(i) for i in range(1, len(self.all_measurements) + 1)]
        writer.writerow(measurement_numbers)

        # Row 2: Values
        # Prepare scaled values
        scaled_values = []
        for raw_val in self.all_measurements:
            scaled_val = raw_val * scale_factor
            scaled_values.append(f'{scaled_val:.6f}')
            
        # Add Unit at the end of the values row
        values_row = ['Value'] + scaled_values + [scale_unit]
        writer.writerow(values_row)
        
        # Row 3: Date
        date_row = ['Date', now.strftime('%Y-%m-%d')] + [''] * (len(self.all_measurements) - 1)
        writer.writerow(date_row)
        
        # Row 4: Time
        time_row = ['Time', now.strftime('%H:%M:%S')] + [''] * (len(self.all_measurements) - 1)
        writer.writerow(time_row)
        
        writer.writerow([])
        
        # Statistics (Horizontal)
        avg = avg_raw * scale_factor
        min_val = min(self.all_measurements) * scale_factor
        max_val = max(self.all_measurements) * scale_factor
        
        if len(self.all_measurements) > 1:
            variance = sum((x - avg_raw) ** 2 for x in self.all_measurements) / (len(self.all_measurements) - 1)
            std_dev_raw = variance ** 0.5
            std_dev = std_dev_raw * scale_factor
        else:
            std_dev = 0
            
        writer.writerow(['Statistics', 'Average', 'Minimum', 'Maximum', 'Std Deviation'])
        writer.writerow(['', f'{avg:.6f}', f'{min_val:.6f}', f'{max_val:.6f}', f'{std_dev:.6f}', scale_unit])
        
        writer.writerow([])
        writer.writerow(['Measurement Type', self.current_measurement_type])
        writer.writerow(['Total Measurements', len(self.all_measurements)])
        writer.writerow(['Sampling Interval', f"{self.sampling_rate_spin.value()} s"])
    
    def auto_save_and_open_csv(self):
        """Automatically save and open CSV after measurement completes"""
        if not self.all_measurements:
            return
        
        # Close old file first
        file_path = Path("latest_output.csv").absolute()
        self.close_csv_file(file_path)
        
        # Save and open new file
        self.save_and_open_csv()
    
    def save_and_open_csv(self):
        """Save measurements to latest_output.csv and open it automatically"""
        if not self.all_measurements:
            QMessageBox.warning(self, "No Data", "No measurements to save!")
            return
        
        # Get unit
        units = {
            "DC Voltage": "V",
            "AC Voltage": "V",
            "DC Current": "A",
            "AC Current": "A",
            "Resistance": "Ω",
            "Continuity": "Ω"
        }
        unit = units.get(self.current_measurement_type, "")
        
        # Set fixed filename
        file_path = Path("latest_output.csv").absolute()
        
        # Try multiple times with delays
        max_retries = 3
        for attempt in range(max_retries):
            try:
                with open(file_path, 'w', newline='', encoding='utf-8-sig') as csvfile:
                    self.write_csv_content(csvfile, unit)
                
                # If we get here, save was successful
                # Open the file automatically
                import os
                if sys.platform == 'win32':
                    os.startfile(str(file_path))
                elif sys.platform == 'darwin':  # macOS
                    os.system(f'open "{file_path}"')
                else:  # linux
                    os.system(f'xdg-open "{file_path}"')
                
                self.status_bar.showMessage(f"Saved and opened: {file_path.name}")
                self.results_text.append(f"\n💾 Data saved to: {file_path}")
                self.results_text.append(f"📂 File opened automatically\n")
                return  # Success, exit function
                
            except PermissionError as e:
                if attempt < max_retries - 1:
                    # Wait and try again
                    import time
                    time.sleep(0.5)
                    continue
                else:
                    # Last attempt failed
                    QMessageBox.critical(self, "Save Error", 
                                       f"Failed to save file (file is locked by Excel):\n{str(e)}\n\n"
                                       "Please close the Excel file 'latest_output.csv' and try again.")
            except Exception as e:
                QMessageBox.critical(self, "Save Error", f"Failed to save file:\n{str(e)}")
                return


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = DigitalMultimeterGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
