"""
Universal Counter GUI Application
A modern PyQt6-based GUI for controlling and monitoring Universal Counter instruments
"""

import sys
import csv
import statistics
from datetime import datetime
from pathlib import Path

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QLineEdit, QTextEdit, QComboBox, QSpinBox,
    QGroupBox, QFileDialog, QMessageBox, QProgressBar, QStatusBar, QScrollArea
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
    
    def __init__(self, resource_name, num_measurements, gate_time, channel=1, impedance=50, coupling="DC", trig_auto=True, trig_level=0.0, sensitivity=50):
        super().__init__()
        self.resource_name = resource_name
        self.num_measurements = num_measurements
        self.gate_time = gate_time
        self.channel = channel  # Channel number (1, 2, or 3)
        self.impedance = impedance  # Impedance in ohms (50 or 1000000)
        self.coupling = coupling  # Coupling type ("DC" or "AC")
        self.trig_auto = trig_auto  # Trigger auto ON/OFF
        self.trig_level = trig_level  # Trigger level in volts
        self.sensitivity = sensitivity  # Sensitivity/Hysteresis (0, 50, 100)
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
            instrument.timeout = int(self.gate_time * 1000 + 5000)  # Gate time + 5 seconds buffer
            
            # Get instrument ID
            idn = instrument.query("*IDN?")
            
            # Configure input channel selection
            try:
                # Select input channel (INP1, INP2, or INP3)
                instrument.write(f":INP{self.channel}")
            except:
                pass  # Instrument may not support this command format
            
            # Configure input impedance
            try:
                # Set impedance for the selected channel
                instrument.write(f":INP{self.channel}:IMP {self.impedance}")
            except:
                pass  # Instrument may not support this command
            
            # Configure input coupling
            try:
                # Set coupling (DC or AC) for the selected channel
                instrument.write(f":INP{self.channel}:COUP {self.coupling}")
            except:
                pass  # Instrument may not support this command
            
            # Configure trigger auto
            try:
                if self.trig_auto:
                    instrument.write(f":INP{self.channel}:LEV:AUTO ON")
                else:
                    instrument.write(f":INP{self.channel}:LEV:AUTO OFF")
                    # Set specific trigger level when auto is off
                    instrument.write(f":INP{self.channel}:LEV {self.trig_level}")
            except:
                pass  # Instrument may not support this command
            
            # Configure sensitivity (hysteresis)
            try:
                # Set hysteresis relative (0, 50, or 100 percent)
                # Command: [:SENSe]:EVENt[1|2]:HYSTeresis:RELative <percent>
                # Note: SCPI node might be SENSe or just EVENt depending on exact model firmware, trying standard
                instrument.write(f":EVEN{self.channel}:HYST:REL {self.sensitivity}")
            except:
                pass  # Instrument may not support this command

            # Configure gate time (if supported by instrument)
            try:
                # Common SCPI commands for gate time configuration
                instrument.write(f":FREQ:ARM:STAR:SOUR IMM")
                instrument.write(f":FREQ:ARM:STOP:SOUR TIM")
                instrument.write(f":FREQ:ARM:STOP:TIM {self.gate_time}")
            except:
                pass  # Instrument may not support these commands
            
            self.measurements = []
            
            for i in range(self.num_measurements):
                if not self.is_running:
                    break
                
                # Query measurement
                response = instrument.query("READ?")
                value = float(response.strip())
                
                self.measurements.append(value)
                self.measurement_ready.emit(value, i + 1)
                self.progress_update.emit(int((i + 1) / self.num_measurements * 100))
                
                # Wait for gate time plus small buffer
                self.msleep(int(self.gate_time * 1000) + 100)
            
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
        self.plot_data()
    
    def plot_data(self):
        """Update the plot with current measurements"""
        self.axes.clear()
        
        if self.measurements:
            x = list(range(1, len(self.measurements) + 1))
            self.axes.plot(x, self.measurements, 'o-', color='#0066cc', linewidth=2, markersize=8)
            self.axes.set_xlabel('Measurement Number', fontsize=10, color='#2c3e50')
            self.axes.set_ylabel('Frequency (Hz)', fontsize=10, color='#2c3e50')
            self.axes.set_title('Real-time Measurements', fontsize=12, color='#2c3e50', fontweight='bold')
            self.axes.grid(True, alpha=0.2, color='#bdc3c7')
            
            # Add statistics
            if len(self.measurements) > 1:
                avg = sum(self.measurements) / len(self.measurements)
                self.axes.axhline(y=avg, color='#e74c3c', linestyle='--', linewidth=2, label=f'Average: {avg:.6f} Hz')
                self.axes.legend(facecolor='#ffffff', edgecolor='#3c4043', labelcolor='#3c4043')
        else:
            self.axes.text(0.5, 0.5, 'No data yet', 
                          horizontalalignment='center',
                          verticalalignment='center',
                          transform=self.axes.transAxes,
                          fontsize=14, color='#95a5a6')
            self.axes.set_xlabel('Measurement Number', fontsize=10, color='#2c3e50')
            self.axes.set_ylabel('Frequency (Hz)', fontsize=10, color='#2c3e50')
        
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


class UniversalCounterGUI(QMainWindow):
    """Main GUI window for Universal Counter application"""
    
    def __init__(self):
        super().__init__()
        self.measurement_thread = None
        self.all_measurements = []
        self.use_arabic_numerals = False  # Toggle for Arabic numerals (False = Western numerals)
        self.init_ui()
    
    def to_arabic_numerals(self, text):
        """Convert Western numerals (0-9) to Arabic-Indic numerals (٠-٩)"""
        if not self.use_arabic_numerals:
            return text
        
        arabic_digits = {
            '0': '٠', '1': '١', '2': '٢', '3': '٣', '4': '٤',
            '5': '٥', '6': '٦', '7': '٧', '8': '٨', '9': '٩'
        }
        
        result = str(text)
        for western, arabic in arabic_digits.items():
            result = result.replace(western, arabic)
        return result
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("53132A Universal Counter Control Panel")
        self.setGeometry(100, 100, 1400, 900)  # Increased size for better visibility
        
        # Set light theme
        self.set_light_theme()
        
        # Create central widget and main scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_box = QVBoxLayout(central_widget)
        main_box.setContentsMargins(0, 0, 0, 0)
        
        # Scroll Area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
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
        
        # Content Widget inside Scroll Area
        content_widget = QWidget()
        scroll.setWidget(content_widget)
        
        main_layout = QVBoxLayout(content_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title_label = QLabel("📊 53132A Universal Counter Control Panel")
        title_label.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        title_label.setStyleSheet("color: #1a73e8; padding: 10px;")
        main_layout.addWidget(title_label)
        
        # Connection Group
        connection_group = self.create_connection_group()
        main_layout.addWidget(connection_group)
        
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
        
        # Statistics Group
        stats_group = self.create_statistics_group()
        main_layout.addWidget(stats_group)
        
        # Results and Graph Layout
        results_layout = QHBoxLayout()
        
        # Results Text Area
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
        self.results_text.setMinimumHeight(400)
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
        
        main_layout.addLayout(results_layout, 1)
        
        # Status Bar
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
        self.status_bar.showMessage("✨ Ready - Universal Counter Control")
        
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
            "GPIB0::3::INSTR",  # Default for 53132A
            "GPIB0::2::INSTR",
            "USB0::0x0957::0x1807::MY12345678::INSTR",
            "TCPIP0::192.168.1.100::INSTR"
        ])
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
    
    def create_settings_group(self):
        """Create measurement settings group"""
        group = QGroupBox("⚙️ Measurement Settings")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        # Use Grid Layout for more compact design
        layout = QGridLayout()
        layout.setVerticalSpacing(15)
        layout.setHorizontalSpacing(20)
        
        # --- Row 0: Input Channels & Properties ---
        
        # Input Channel
        channel_label = QLabel("Input Select:")
        channel_label.setFont(QFont("Segoe UI", 10))
        self.channel_combo = QComboBox()
        self.channel_combo.setFont(QFont("Segoe UI", 10))
        self.channel_combo.setStyleSheet(self.get_input_style())
        self.channel_combo.addItems(["Channel 1", "Channel 2", "Channel 3"])
        self.channel_combo.setCurrentIndex(0)
        
        layout.addWidget(channel_label, 0, 0)
        layout.addWidget(self.channel_combo, 0, 1)

        # Input Impedance
        impedance_label = QLabel("I/P Impedance:")
        impedance_label.setFont(QFont("Segoe UI", 10))
        self.impedance_combo = QComboBox()
        self.impedance_combo.setFont(QFont("Segoe UI", 10))
        self.impedance_combo.setStyleSheet(self.get_input_style())
        self.impedance_combo.addItems(["50 Ω", "1 MΩ"])
        self.impedance_combo.setCurrentIndex(0)
        
        layout.addWidget(impedance_label, 0, 2)
        layout.addWidget(self.impedance_combo, 0, 3)

        # Input Coupling
        coupling_label = QLabel("I/P Coupling:")
        coupling_label.setFont(QFont("Segoe UI", 10))
        self.coupling_combo = QComboBox()
        self.coupling_combo.setFont(QFont("Segoe UI", 10))
        self.coupling_combo.setStyleSheet(self.get_input_style())
        self.coupling_combo.addItems(["DC", "AC"])
        self.coupling_combo.setCurrentIndex(0)
        
        layout.addWidget(coupling_label, 0, 4)
        layout.addWidget(self.coupling_combo, 0, 5)

        # --- Row 1: Gate Time & Sensitivity ---

        # Gate Time
        gate_time_label = QLabel("Gate Time (s):")
        gate_time_label.setFont(QFont("Segoe UI", 10))
        
        from PyQt6.QtWidgets import QDoubleSpinBox
        self.gate_time_spin = QDoubleSpinBox()
        self.gate_time_spin.setMinimum(0.001)
        self.gate_time_spin.setMaximum(1000.0)
        self.gate_time_spin.setValue(10.0)
        self.gate_time_spin.setDecimals(3)
        self.gate_time_spin.setSingleStep(0.5)
        self.gate_time_spin.setFont(QFont("Segoe UI", 10))
        self.gate_time_spin.setStyleSheet(self.get_spinbox_style())
        self.gate_time_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        
        layout.addWidget(gate_time_label, 1, 0)
        layout.addWidget(self.gate_time_spin, 1, 1)
        
        # Sensitivity
        sens_label = QLabel("Sensitivity:")
        sens_label.setFont(QFont("Segoe UI", 10))
        
        self.sens_combo = QComboBox()
        self.sens_combo.setFont(QFont("Segoe UI", 10))
        self.sens_combo.setStyleSheet(self.get_input_style())
        self.sens_combo.addItems(["High (0%)", "Medium (50%)", "Low (100%)"])
        self.sens_combo.setCurrentIndex(1)
        
        layout.addWidget(sens_label, 1, 2)
        layout.addWidget(self.sens_combo, 1, 3)
        
        # Number of measurements
        num_meas_label = QLabel("Readings:")
        num_meas_label.setFont(QFont("Segoe UI", 10))
        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setRange(1, 1000000)
        self.num_measurements_spin.setValue(10)
        self.num_measurements_spin.setFont(QFont("Segoe UI", 10))
        self.num_measurements_spin.setStyleSheet(self.get_spinbox_style())
        self.num_measurements_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))

        layout.addWidget(num_meas_label, 1, 4)
        layout.addWidget(self.num_measurements_spin, 1, 5)

        # --- Row 2: Trigger Controls ---
        
        # Trigger Auto (Checkbox)
        from PyQt6.QtWidgets import QCheckBox
        self.trig_auto_check = QCheckBox("Trig Auto")
        self.trig_auto_check.setFont(QFont("Segoe UI", 10, QFont.Weight.Bold))
        self.trig_auto_check.setChecked(True)
        self.trig_auto_check.setStyleSheet("""
            QCheckBox { color: #3c4043; spacing: 8px; }
            QCheckBox::indicator { width: 20px; height: 20px; border: 2px solid #dadce0; border-radius: 4px; background-color: white; }
            QCheckBox::indicator:checked { background-color: #1a73e8; border-color: #1a73e8; image: url(none); }
        """)
        
        layout.addWidget(self.trig_auto_check, 2, 0, 1, 2)

        # Trigger Level
        trig_level_label = QLabel("Trig Level (V):")
        trig_level_label.setFont(QFont("Segoe UI", 10))
        
        self.trig_level_spin = QDoubleSpinBox()
        self.trig_level_spin.setMinimum(-10.0)
        self.trig_level_spin.setMaximum(10.0)
        self.trig_level_spin.setValue(0.0)
        self.trig_level_spin.setDecimals(3)
        self.trig_level_spin.setSingleStep(0.1)
        self.trig_level_spin.setFont(QFont("Segoe UI", 10))
        self.trig_level_spin.setStyleSheet(self.get_spinbox_style())
        self.trig_level_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        
        layout.addWidget(trig_level_label, 2, 2)
        layout.addWidget(self.trig_level_spin, 2, 3)

        # Add flexible spacer at the bottom
        layout.setRowStretch(3, 1)
        
        group.setLayout(layout)
        return group
    
    def create_statistics_group(self):
        """Create statistics display group"""
        group = QGroupBox("📈 Statistics")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QHBoxLayout()
        
        # Helper to create stat labels
        def create_stat_widget(title, color):
            widget = QWidget()
            vbox = QVBoxLayout(widget)
            vbox.setContentsMargins(5, 5, 5, 5)
            
            title_lbl = QLabel(title)
            title_lbl.setFont(QFont("Segoe UI", 9))
            title_lbl.setStyleSheet("color: #5f6368;")
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            value_lbl = QLabel("---")
            value_lbl.setFont(QFont("Segoe UI", 14, QFont.Weight.Bold))
            value_lbl.setStyleSheet(f"color: {color};")
            value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            
            vbox.addWidget(title_lbl)
            vbox.addWidget(value_lbl)
            return widget, value_lbl

        self.stat_mean_widget, self.stat_mean_lbl = create_stat_widget("Mean", "#1a73e8")
        self.stat_max_widget, self.stat_max_lbl = create_stat_widget("Max", "#d93025")
        self.stat_min_widget, self.stat_min_lbl = create_stat_widget("Min", "#188038")
        self.stat_std_widget, self.stat_std_lbl = create_stat_widget("Std Dev", "#e37400")
        self.stat_count_widget, self.stat_count_lbl = create_stat_widget("Count", "#5f6368")

        layout.addWidget(self.stat_count_widget)
        layout.addWidget(self.stat_mean_widget)
        layout.addWidget(self.stat_max_widget)
        layout.addWidget(self.stat_min_widget)
        layout.addWidget(self.stat_std_widget)
        
        group.setLayout(layout)
        return group
    
    def create_control_buttons(self):
        """Create control buttons layout"""
        layout = QHBoxLayout()
        
        # Start button
        self.start_btn = QPushButton("▶️ Start Measurement")
        self.start_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.start_btn.setMinimumHeight(50)
        self.start_btn.setStyleSheet(self.get_button_style("#1a73e8"))
        self.start_btn.clicked.connect(self.start_measurement)
        layout.addWidget(self.start_btn)
        
        # Stop button
        self.stop_btn = QPushButton("⏹️ Stop")
        self.stop_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.stop_btn.setMinimumHeight(50)
        self.stop_btn.setStyleSheet(self.get_button_style("#5f6368"))
        self.stop_btn.setEnabled(False)
        self.stop_btn.clicked.connect(self.stop_measurement)
        layout.addWidget(self.stop_btn)
        
        # Clear button
        clear_btn = QPushButton("🗑️ Clear")
        clear_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        clear_btn.setMinimumHeight(50)
        clear_btn.setStyleSheet(self.get_button_style("#f9ab00"))
        clear_btn.clicked.connect(self.clear_results)
        layout.addWidget(clear_btn)
        
        # Save and Open CSV button
        save_btn = QPushButton("💾 Save & Open CSV")
        save_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        save_btn.setMinimumHeight(50)
        save_btn.setStyleSheet(self.get_button_style("#1e8e3e"))
        save_btn.clicked.connect(self.save_and_open_csv)
        layout.addWidget(save_btn)
        
        return layout
    
    def set_light_theme(self):
        """Apply light theme to the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f8f9fa;
            }
            QWidget {
                background-color: #f8f9fa;
                color: #2c3e50;
            }
            QLabel {
                color: #2c3e50;
            }
        """)
    
    def get_groupbox_style(self):
        """Get stylesheet for group boxes"""
        return """
            QGroupBox {
                border: 2px solid #dadce0;
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
            QComboBox, QSpinBox, QLineEdit {
                background-color: #ffffff;
                color: #3c4043;
                border: 2px solid #dadce0;
                border-radius: 5px;
                padding: 5px;
                min-height: 25px;
            }
            QComboBox:hover, QSpinBox:hover, QLineEdit:hover {
                border-color: #9aa0a6;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: none;
                border-left: 5px solid transparent;
                border-right: 5px solid transparent;
                border-top: 5px solid #5f6368;
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
                background-color: {self.lighten_color(color)};
            }}
            QPushButton:pressed {{
                background-color: {self.darken_color(color)};
            }}
            QPushButton:disabled {{
                background-color: #555555;
                color: #888888;
            }}
        """
    
    def lighten_color(self, color):
        """Lighten a hex color"""
        # Simple lightening by increasing RGB values
        return color  # Simplified for now
    
    def darken_color(self, color):
        """Darken a hex color"""
        # Simple darkening by decreasing RGB values
        return color  # Simplified for now
    
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
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "Error", "PyVISA is not installed!")
            return
        
        resource_name = self.resource_combo.currentText()
        if not resource_name or resource_name == "No resources found":
            QMessageBox.warning(self, "Error", "Please select a valid resource!")
            return
        
        num_measurements = self.num_measurements_spin.value()
        gate_time = self.gate_time_spin.value()
        
        # Get selected channel (1, 2, or 3)
        channel_text = self.channel_combo.currentText()  # "Channel 1", "Channel 2", or "Channel 3"
        channel = int(channel_text.split()[-1])  # Extract the number
        
        # Get selected impedance
        impedance_text = self.impedance_combo.currentText()  # "50 Ω" or "1 MΩ"
        if "50" in impedance_text:
            impedance = 50
        else:
            impedance = 1000000  # 1 MΩ = 1,000,000 Ω
        
        # Get selected coupling
        coupling = self.coupling_combo.currentText()  # "DC" or "AC"
        
        # Get trigger settings
        trig_auto = self.trig_auto_check.isChecked()  # True or False
        trig_level = self.trig_level_spin.value()  # Voltage value
        
        # Get sensitivity
        sens_text = self.sens_combo.currentText()
        if "High" in sens_text:
            sensitivity = 0
        elif "Low" in sens_text:
            sensitivity = 100
        else:
            sensitivity = 50

        # Update UI
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.progress_bar.setValue(0)
        self.all_measurements = []
        
        # Reset Stat Labels
        self.stat_mean_lbl.setText("---")
        self.stat_max_lbl.setText("---")
        self.stat_min_lbl.setText("---")
        self.stat_std_lbl.setText("---")
        self.stat_count_lbl.setText("0")
        
        # Clear previous graph
        if MATPLOTLIB_AVAILABLE:
            self.plot_canvas.clear_measurements()
        
        # Start measurement thread with all parameters
        self.measurement_thread = MeasurementThread(resource_name, num_measurements, gate_time, channel, impedance, coupling, trig_auto, trig_level, sensitivity)
        self.measurement_thread.measurement_ready.connect(self.on_measurement_ready)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        self.measurement_thread.progress_update.connect(self.progress_bar.setValue)
        self.measurement_thread.start()
        
        self.status_bar.showMessage("Measurement in progress...")
        gate_time = self.gate_time_spin.value()
        self.results_text.append(f"\n{'='*60}")
        timestamp = self.to_arabic_numerals(datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
        self.results_text.append(self.to_arabic_numerals(f"Starting {num_measurements} measurements at {timestamp}"))
        self.results_text.append(self.to_arabic_numerals(f"Input Channel: {channel_text}"))
        self.results_text.append(self.to_arabic_numerals(f"Input Impedance: {impedance_text}"))
        self.results_text.append(self.to_arabic_numerals(f"Input Coupling: {coupling}"))
        trig_auto_status = "ON" if trig_auto else f"OFF (Level: {trig_level}V)"
        self.results_text.append(self.to_arabic_numerals(f"Trigger Auto: {trig_auto_status}"))
        self.results_text.append(self.to_arabic_numerals(f"Sensitivity: {sens_text}"))
        self.results_text.append(self.to_arabic_numerals(f"Gate Time: {gate_time} seconds"))
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
        result_text = f"Measurement #{measurement_num}: {value:.6f} Hz"
        self.results_text.append(self.to_arabic_numerals(result_text))
        
        if MATPLOTLIB_AVAILABLE:
            self.plot_canvas.add_measurement(value)
            
        # Update Real-time Statistics
        measurements = self.all_measurements
        count = len(measurements)
        self.stat_count_lbl.setText(str(count))
        
        if count > 0:
            avg = sum(measurements) / count
            self.stat_mean_lbl.setText(f"{avg:.3e}")
            self.stat_max_lbl.setText(f"{max(measurements):.3e}")
            self.stat_min_lbl.setText(f"{min(measurements):.3e}")
            
            if count > 1:
                try:
                    std_dev = statistics.stdev(measurements)
                    self.stat_std_lbl.setText(f"{std_dev:.3e}")
                except:
                    pass
    
    def on_measurement_complete(self, measurements):
        """Handle measurement completion"""
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.progress_bar.setValue(100)
        
        # Calculate statistics
        # Calculate statistics
        if measurements:
            avg = sum(measurements) / len(measurements)
            min_val = min(measurements)
            max_val = max(measurements)
            
            if len(measurements) > 1:
                std_dev = statistics.stdev(measurements)
            else:
                std_dev = 0
            
            # Update Stat Labels (Final)
            self.stat_mean_lbl.setText(f"{avg:.3e}")
            self.stat_max_lbl.setText(f"{max_val:.3e}")
            self.stat_min_lbl.setText(f"{min_val:.3e}")
            self.stat_std_lbl.setText(f"{std_dev:.3e}")
            self.stat_count_lbl.setText(str(len(measurements)))
            
            self.results_text.append(f"\n{'='*60}")
            self.results_text.append("📊 STATISTICS:")
            self.results_text.append(f"{'='*60}")
            self.results_text.append(self.to_arabic_numerals(f"Total Measurements: {len(measurements)}"))
            self.results_text.append(self.to_arabic_numerals(f"Average:            {avg:.6f} Hz"))
            self.results_text.append(self.to_arabic_numerals(f"Minimum:            {min_val:.6f} Hz"))
            self.results_text.append(self.to_arabic_numerals(f"Maximum:            {max_val:.6f} Hz"))
            self.results_text.append(self.to_arabic_numerals(f"Std Deviation:      {std_dev:.6f} Hz"))
            self.results_text.append(f"{'='*60}\n")
        
        status_msg = f"Measurement complete! {len(measurements)} readings taken."
        self.status_bar.showMessage(self.to_arabic_numerals(status_msg))
        
        # Auto save and open CSV
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
                subprocess.run(f'taskkill /F /FI "WINDOWTITLE eq {filename}*"', 
                             shell=True, capture_output=True, creationflags=subprocess.CREATE_NO_WINDOW)
                
                # Also try matching just the name without extension
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
                    self.write_csv_content(csvfile)
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
                            self.write_csv_content(csvfile)
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

    def write_csv_content(self, csvfile):
        """Helper to write CSV content"""
        writer = csv.writer(csvfile)
        now = datetime.now()
        
        # Header information commented out or simplified for certificates?
        # Let's follow the Multimeter horizontal format strictly
        
        # Row 1: Measurement numbers
        measurement_numbers = ['Measurement'] + [str(i) for i in range(1, len(self.all_measurements) + 1)]
        writer.writerow(measurement_numbers)
        
        # Row 2: Values
        values = ['Value (Hz)'] + [f'{value:.6f}' for value in self.all_measurements]
        writer.writerow(values)
        
        # Row 3: Date
        date_row = ['Date', now.strftime('%Y-%m-%d')] + [''] * (len(self.all_measurements) - 1)
        writer.writerow(date_row)
        
        # Row 4: Time
        time_row = ['Time', now.strftime('%H:%M:%S')] + [''] * (len(self.all_measurements) - 1)
        writer.writerow(time_row)
        
        writer.writerow([])
        
        # Statistics
        avg = sum(self.all_measurements) / len(self.all_measurements)
        min_val = min(self.all_measurements)
        max_val = max(self.all_measurements)
        if len(self.all_measurements) > 1:
            variance = sum((x - avg) ** 2 for x in self.all_measurements) / (len(self.all_measurements) - 1)
            std_dev = variance ** 0.5
        else:
            std_dev = 0
            
        writer.writerow(['Statistics', 'Average', 'Minimum', 'Maximum', 'Std Deviation'])
        writer.writerow(['', f'{avg:.6f}', f'{min_val:.6f}', f'{max_val:.6f}', f'{std_dev:.6f}'])
        
        writer.writerow([])
        writer.writerow(['Measurement Type', 'Frequency'])
        writer.writerow(['Total Measurements', len(self.all_measurements)])
        writer.writerow(['Gate Time (seconds)', self.gate_time_spin.value()])

    def auto_save_and_open_csv(self):
        """Automatically save and open CSV after measurement completes"""
        QTimer.singleShot(500, self.save_and_open_csv)


def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')  # Use Fusion style for better cross-platform appearance
    
    window = UniversalCounterGUI()
    window.showMaximized()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
