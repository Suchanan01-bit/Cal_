"""
Measurement Tools Hub - Central Application
A comprehensive PyQt6-based GUI hub for controlling multiple measurement instruments
"""

import sys
import threading
import time
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QStackedWidget, QFrame, QScrollArea,
    QGridLayout, QGroupBox, QStatusBar, QMessageBox, QComboBox,
    QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
)
from PyQt6.QtCore import Qt, QSize, QPropertyAnimation, QEasingCurve, QTimer, pyqtSignal, QObject
from PyQt6.QtGui import QFont, QIcon, QPalette, QColor
from PyQt6.QtWidgets import QGraphicsDropShadowEffect

# Import instrument modules
try:
    from universal_counter_gui import UniversalCounterGUI
    COUNTER_AVAILABLE = True
except ImportError:
    COUNTER_AVAILABLE = False

try:
    from multimeter_8846 import DigitalMultimeterGUI
    MULTIMETER_AVAILABLE = True
except ImportError:
    MULTIMETER_AVAILABLE = False

try:
    from multimeter_3458_gui import HP3458MultimeterGUI
    MULTIMETER_3458_AVAILABLE = True
except ImportError:
    MULTIMETER_3458_AVAILABLE = False

try:
    from multimeter_34401_gui import HP34401MultimeterGUI
    MULTIMETER_34401_AVAILABLE = True
except ImportError:
    MULTIMETER_34401_AVAILABLE = False

try:
    from reference_multimeter_8508_gui import Fluke8508MultimeterGUI
    MULTIMETER_8508_AVAILABLE = True
except ImportError:
    MULTIMETER_8508_AVAILABLE = False

try:
    from multimeter_34465_gui import Keysight34465MultimeterGUI
    MULTIMETER_34465_AVAILABLE = True
except ImportError:
    MULTIMETER_34465_AVAILABLE = False

try:
    from rs_power_meter_gui import RSPowerMeterGUI
    RS_POWER_METER_AVAILABLE = True
except ImportError:
    RS_POWER_METER_AVAILABLE = False

try:
    from waveform_33120a_gui import HP33120AGeneratorGUI
    WAVEFORM_33120A_AVAILABLE = True
except ImportError:
    WAVEFORM_33120A_AVAILABLE = False

try:
    from spectrum_n1996a_gui import AgilentN1996AGUI
    SPECTRUM_N1996A_AVAILABLE = True
except ImportError:
    SPECTRUM_N1996A_AVAILABLE = False

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False

try:
    from fluke1620_reader import Fluke1620Reader
    FLUKE1620_AVAILABLE = True
except ImportError:
    FLUKE1620_AVAILABLE = False



class InstrumentCard(QFrame):
    """Card widget for each instrument"""
    
    def __init__(self, title, description, icon, status="Available", parent=None):
        super().__init__(parent)
        self.title = title
        self.description = description
        self.icon = icon
        self.status = status
        self.setup_ui()
    
    def setup_ui(self):
        """Setup the card UI"""
        self.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Raised)
        
        # Professional lab equipment styling
        self.setStyleSheet("""
            InstrumentCard {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f9fafb);
                border: 1px solid #d1d5db;
                border-radius: 12px;
            }
            InstrumentCard:hover {
                background: qlineargradient(x1:0, y1:0, x2:0, y2:1,
                    stop:0 #ffffff, stop:1 #f0f4f8);
                border: 1px solid #3498db;
                transform: translateY(-2px);
            }
        """)
        
        # Professional shadow effect
        shadow = QGraphicsDropShadowEffect()
        shadow.setBlurRadius(12)
        shadow.setXOffset(0)
        shadow.setYOffset(2)
        shadow.setColor(QColor(0, 0, 0, 25))  # Subtle dark shadow
        self.setGraphicsEffect(shadow)
        
        self.setMinimumHeight(180)
        self.setMaximumHeight(200)
        
        layout = QVBoxLayout(self)
        layout.setSpacing(12)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Icon and title row
        header_layout = QHBoxLayout()
        header_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        
        icon_label = QLabel(self.icon)
        icon_label.setFont(QFont("Segoe UI Emoji", 26))
        icon_label.setStyleSheet("color: #4b5563;")
        header_layout.addWidget(icon_label)
        
        header_layout.addSpacing(12)
        
        title_label = QLabel(self.title)
        title_label.setFont(QFont("Segoe UI", 13, QFont.Weight.DemiBold))
        title_label.setStyleSheet("color: #4b5563; letter-spacing: 0.3px;")
        title_label.setWordWrap(True)
        header_layout.addWidget(title_label, 1)
        
        layout.addLayout(header_layout)
        
        # Description
        desc_label = QLabel(self.description)
        desc_label.setFont(QFont("Segoe UI", 9))
        desc_label.setStyleSheet("color: #6b7280; line-height: 1.5;")
        desc_label.setWordWrap(True)
        desc_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        layout.addWidget(desc_label, 1)
        
        # LED-style status indicator
        status_container = QHBoxLayout()
        status_container.setSpacing(8)
        
        # LED indicator dot
        led_label = QLabel("●")
        led_label.setFont(QFont("Segoe UI", 12))
        
        if self.status == "Available":
            led_label.setStyleSheet("color: #27ae60;")
            status_text = "Ready"
            status_color = "#27ae60"
        elif self.status == "Coming Soon":
            led_label.setStyleSheet("color: #f39c12;")
            status_text = "In Development"
            status_color = "#f39c12"
        elif self.status == "Not Ready":
            led_label.setStyleSheet("color: #e67e22;")
            status_text = "Not Ready"
            status_color = "#e67e22"
        elif self.status == "Not Available":
            led_label.setStyleSheet("color: #e67e22;")
            status_text = "Not Available"
            status_color = "#e67e22"
        else:
            led_label.setStyleSheet("color: #95a5a6;")
            status_text = "Offline"
            status_color = "#95a5a6"
        
        status_label = QLabel(status_text)
        status_label.setFont(QFont("Consolas", 9, QFont.Weight.Medium))
        status_label.setStyleSheet(f"color: {status_color}; letter-spacing: 0.5px;")
        
        status_container.addWidget(led_label)
        status_container.addWidget(status_label)
        status_container.addStretch()
        layout.addLayout(status_container)


class MultimeterWidget(QWidget):
    """Widget for Digital Multimeter control"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📟 Digital Multimeter")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #0066cc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Coming soon message
        message = QLabel("🚧 This module is under development\n\nFeatures will include:\n• Voltage measurement (DC/AC)\n• Current measurement\n• Resistance measurement\n• Continuity test\n• Data logging")
        message.setFont(QFont("Segoe UI", 12))
        message.setStyleSheet("color: #7f8c8d; padding: 40px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message, 1)


class OscilloscopeWidget(QWidget):
    """Widget for Oscilloscope control"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📊 Digital Oscilloscope")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #0066cc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Coming soon message
        message = QLabel("🚧 This module is under development\n\nFeatures will include:\n• Waveform capture\n• FFT analysis\n• Measurement cursors\n• Screenshot capture\n• Auto measurements")
        message.setFont(QFont("Segoe UI", 12))
        message.setStyleSheet("color: #7f8c8d; padding: 40px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message, 1)


class PowerSupplyWidget(QWidget):
    """Widget for Power Supply control"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("⚡ Programmable Power Supply")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #0066cc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Coming soon message
        message = QLabel("🚧 This module is under development\n\nFeatures will include:\n• Voltage/Current control\n• Output enable/disable\n• Over-voltage protection\n• Current limiting\n• Preset configurations")
        message.setFont(QFont("Segoe UI", 12))
        message.setStyleSheet("color: #7f8c8d; padding: 40px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message, 1)


class SignalGeneratorWidget(QWidget):
    """Widget for Signal Generator control"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("🌊 Signal Generator")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #0066cc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Coming soon message
        message = QLabel("🚧 This module is under development\n\nFeatures will include:\n• Waveform generation (Sine, Square, Triangle)\n• Frequency control\n• Amplitude control\n• Modulation (AM/FM)\n• Sweep function")
        message.setFont(QFont("Segoe UI", 12))
        message.setStyleSheet("color: #7f8c8d; padding: 40px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message, 1)


class SpectrumAnalyzerWidget(QWidget):
    """Widget for Spectrum Analyzer control"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 20)
        
        # Title
        title = QLabel("📡 Spectrum Analyzer")
        title.setFont(QFont("Segoe UI", 24, QFont.Weight.Bold))
        title.setStyleSheet("color: #0066cc;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Coming soon message
        message = QLabel("🚧 This module is under development\n\nFeatures will include:\n• Frequency spectrum display\n• Peak detection\n• Marker measurements\n• Span/Center frequency control\n• Trace averaging")
        message.setFont(QFont("Segoe UI", 12))
        message.setStyleSheet("color: #7f8c8d; padding: 40px;")
        message.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(message, 1)


class EnvDataSignal(QObject):
    """Signal bridge for thread-safe UI updates from env monitor thread"""
    data_updated = pyqtSignal(dict)


class EnvironmentMonitorWidget(QWidget):
    """Full-page Environment Monitor with connection controls, readout cards, real-time graph, and history"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.fluke_reader = Fluke1620Reader() if FLUKE1620_AVAILABLE else None
        self.monitoring = False
        self.env_history: List[Dict] = []
        self.signal = EnvDataSignal()
        self.signal.data_updated.connect(self._on_data)
        
        # Real-time graph data
        self.rt_times = []
        self.rt_temps = []
        self.rt_humids = []
        self.max_rt_points = 60
        
        self.setup_ui()
        QTimer.singleShot(500, self.refresh_ports)
    
    def setup_ui(self):
        from matplotlib.figure import Figure
        from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg
        import matplotlib.dates as mdates
        self._mdates = mdates
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(25, 20, 25, 20)
        layout.setSpacing(12)
        
        # ── Title Row ──
        title_row = QHBoxLayout()
        title = QLabel("🌡️ Environment Monitor")
        title.setFont(QFont("Segoe UI", 20, QFont.Weight.Bold))
        title.setStyleSheet("color: #0d9488;")
        title_row.addWidget(title)
        title_row.addStretch()
        
        # Status
        self.status_label = QLabel("● Disconnected")
        self.status_label.setFont(QFont("Consolas", 10))
        self.status_label.setStyleSheet("color: #ef4444;")
        title_row.addWidget(self.status_label)
        layout.addLayout(title_row)
        
        subtitle = QLabel("Real-time temperature & humidity from Fluke 1620A DewK")
        subtitle.setFont(QFont("Segoe UI", 10))
        subtitle.setStyleSheet("color: #6b7280;")
        layout.addWidget(subtitle)
        
        # ── Connection Controls ──
        conn_frame = QFrame()
        conn_frame.setStyleSheet("QFrame { background-color: #f0fdfa; border: 1px solid #ccfbf1; border-radius: 8px; }")
        conn_layout = QHBoxLayout(conn_frame)
        conn_layout.setContentsMargins(12, 8, 12, 8)
        conn_layout.setSpacing(8)
        
        conn_layout.addWidget(QLabel("COM Port:"))
        self.port_combo = QComboBox()
        self.port_combo.setMinimumWidth(180)
        self.port_combo.setMinimumHeight(28)
        self.port_combo.setStyleSheet("QComboBox { background: white; border: 1px solid #d1d5db; border-radius: 4px; padding: 2px 6px; }")
        conn_layout.addWidget(self.port_combo)
        
        refresh_btn = QPushButton("🔄")
        refresh_btn.setFixedSize(28, 28)
        refresh_btn.setStyleSheet("QPushButton { background: white; border: 1px solid #d1d5db; border-radius: 4px; } QPushButton:hover { background: #e5e7eb; }")
        refresh_btn.clicked.connect(self.refresh_ports)
        conn_layout.addWidget(refresh_btn)
        
        self.connect_btn = QPushButton("Connect")
        self.connect_btn.setMinimumHeight(28)
        self.connect_btn.setStyleSheet("QPushButton { background-color: #0d9488; color: white; border: none; border-radius: 4px; padding: 4px 16px; font-weight: bold; } QPushButton:hover { background-color: #0f766e; }")
        self.connect_btn.clicked.connect(self.toggle_connection)
        conn_layout.addWidget(self.connect_btn)
        
        self.monitor_btn = QPushButton("▶ Start Monitor")
        self.monitor_btn.setMinimumHeight(28)
        self.monitor_btn.setEnabled(False)
        self.monitor_btn.setStyleSheet("QPushButton { background-color: #14b8a6; color: white; border: none; border-radius: 4px; padding: 4px 16px; font-weight: bold; } QPushButton:hover { background-color: #0d9488; } QPushButton:disabled { background-color: #94a3b8; }")
        self.monitor_btn.clicked.connect(self.toggle_monitoring)
        conn_layout.addWidget(self.monitor_btn)
        
        conn_layout.addStretch()
        layout.addWidget(conn_frame)
        
        # ── Readout Cards (horizontal row) ──
        cards_layout = QHBoxLayout()
        cards_layout.setSpacing(12)
        
        self.big_labels = {}
        big_cards_info = [
            ("Temperature 1", "°C", "#ea580c"),
            ("Temperature 2", "°C", "#f97316"),
            ("Humidity", "%RH", "#0891b2"),
            ("Dewpoint", "°C", "#7c3aed"),
        ]
        
        for label, unit, color in big_cards_info:
            card = QFrame()
            card.setStyleSheet(f"QFrame {{ background-color: white; border: none; border-radius: 10px; }}")
            card.setMinimumHeight(100)
            card_layout = QVBoxLayout(card)
            card_layout.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.setSpacing(2)
            card_layout.setContentsMargins(8, 6, 8, 6)
            
            name_lbl = QLabel(label)
            name_lbl.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
            name_lbl.setStyleSheet(f"color: {color};")
            name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(name_lbl)
            
            val_lbl = QLabel("--")
            val_lbl.setFont(QFont("Consolas", 28, QFont.Weight.Bold))
            val_lbl.setStyleSheet(f"color: {color};")
            val_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(val_lbl)
            
            unit_lbl = QLabel(unit)
            unit_lbl.setFont(QFont("Segoe UI", 9))
            unit_lbl.setStyleSheet(f"color: {color}90;")
            unit_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            card_layout.addWidget(unit_lbl)
            
            shadow = QGraphicsDropShadowEffect()
            shadow.setBlurRadius(12)
            shadow.setXOffset(0)
            shadow.setYOffset(3)
            shadow.setColor(QColor(0, 0, 0, 18))
            card.setGraphicsEffect(shadow)
            
            self.big_labels[label] = val_lbl
            cards_layout.addWidget(card)
        
        layout.addLayout(cards_layout)
        
        # ── Real-Time Graph (matplotlib) ──
        graph_frame = QFrame()
        graph_frame.setStyleSheet("QFrame { background-color: white; border: 1px solid #e5e7eb; border-radius: 8px; }")
        graph_inner = QVBoxLayout(graph_frame)
        graph_inner.setContentsMargins(8, 8, 8, 8)
        
        graph_header = QLabel("📊 Real-Time Graph")
        graph_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        graph_header.setStyleSheet("color: #374151; border: none;")
        graph_inner.addWidget(graph_header)
        
        self.rt_fig = Figure(figsize=(8, 3), dpi=90, facecolor='white')
        self.rt_ax = self.rt_fig.add_subplot(111)
        self.rt_ax2 = self.rt_ax.twinx()
        self.rt_ax.set_facecolor('white')
        self.rt_ax.grid(True, linestyle='-', alpha=0.3)
        self.rt_ax.set_ylabel('Temperature [°C]', fontsize=9, color='#FF6600')
        self.rt_ax2.set_ylabel('Humidity [%RH]', fontsize=9, color='#00BFFF')
        self.rt_ax.tick_params(axis='y', colors='#FF6600', labelsize=8)
        self.rt_ax2.tick_params(axis='y', colors='#00BFFF', labelsize=8)
        self.rt_ax.tick_params(axis='x', colors='black', labelsize=8)
        self.rt_fig.tight_layout()
        
        self.rt_canvas = FigureCanvasQTAgg(self.rt_fig)
        self.rt_canvas.setMinimumHeight(220)
        self.rt_canvas.setStyleSheet("border: none;")
        graph_inner.addWidget(self.rt_canvas)
        
        self.rt_time_label = QLabel("")
        self.rt_time_label.setFont(QFont("Consolas", 8))
        self.rt_time_label.setStyleSheet("color: #94a3b8; border: none;")
        self.rt_time_label.setAlignment(Qt.AlignmentFlag.AlignRight)
        graph_inner.addWidget(self.rt_time_label)
        
        layout.addWidget(graph_frame, 1)
        
        # ── History Table ──
        history_header = QLabel("📋 Reading History (last 50)")
        history_header.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        history_header.setStyleSheet("color: #374151;")
        layout.addWidget(history_header)
        
        self.history_table = QTableWidget(0, 5)
        self.history_table.setHorizontalHeaderLabels(["Time", "Temp 1 (°C)", "Temp 2 (°C)", "Humidity (%RH)", "Dewpoint (°C)"])
        self.history_table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.history_table.setAlternatingRowColors(True)
        self.history_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        self.history_table.setMaximumHeight(200)
        self.history_table.setStyleSheet("""
            QTableWidget { background-color: white; border: 1px solid #e5e7eb; border-radius: 8px; gridline-color: #f3f4f6; }
            QHeaderView::section { background-color: #f0fdfa; color: #0d9488; font-weight: bold; border: none; padding: 6px; }
            QTableWidget::item:alternate { background-color: #f9fafb; }
        """)
        layout.addWidget(self.history_table)
    
    # ── Connection Logic ──
    def refresh_ports(self):
        self.port_combo.clear()
        if not FLUKE1620_AVAILABLE:
            return
        ports = Fluke1620Reader.list_available_ports()
        for port, desc in ports:
            self.port_combo.addItem(f"{port} - {desc}", port)
    
    def toggle_connection(self):
        if self.fluke_reader and self.fluke_reader.is_connected():
            self.disconnect_fluke()
        else:
            self.connect_fluke()
    
    def connect_fluke(self):
        port = self.port_combo.currentData()
        if not port or not self.fluke_reader:
            return
        success, msg = self.fluke_reader.connect(port)
        if success:
            self.status_label.setText(f"● Connected ({port})")
            self.status_label.setStyleSheet("color: #16a34a;")
            self.connect_btn.setText("Disconnect")
            self.connect_btn.setStyleSheet("QPushButton { background-color: #dc2626; color: white; border: none; border-radius: 4px; padding: 4px 16px; font-weight: bold; } QPushButton:hover { background-color: #b91c1c; }")
            self.monitor_btn.setEnabled(True)
        else:
            self.status_label.setText("● Connection failed")
            self.status_label.setStyleSheet("color: #ef4444;")
    
    def disconnect_fluke(self):
        self.stop_monitoring()
        if self.fluke_reader:
            self.fluke_reader.disconnect()
        self.status_label.setText("● Disconnected")
        self.status_label.setStyleSheet("color: #ef4444;")
        self.connect_btn.setText("Connect")
        self.connect_btn.setStyleSheet("QPushButton { background-color: #0d9488; color: white; border: none; border-radius: 4px; padding: 4px 16px; font-weight: bold; } QPushButton:hover { background-color: #0f766e; }")
        self.monitor_btn.setEnabled(False)
        self.monitor_btn.setText("▶ Start Monitor")
    
    def toggle_monitoring(self):
        if self.monitoring:
            self.stop_monitoring()
        else:
            self.start_monitoring()
    
    def start_monitoring(self):
        if not self.fluke_reader or not self.fluke_reader.is_connected():
            return
        self.monitoring = True
        self.monitor_btn.setText("■ Stop Monitor")
        self.monitor_btn.setStyleSheet("QPushButton { background-color: #dc2626; color: white; border: none; border-radius: 4px; padding: 4px 16px; font-weight: bold; } QPushButton:hover { background-color: #b91c1c; }")
        threading.Thread(target=self._monitor_loop, daemon=True).start()
    
    def stop_monitoring(self):
        self.monitoring = False
        self.monitor_btn.setText("▶ Start Monitor")
        self.monitor_btn.setStyleSheet("QPushButton { background-color: #14b8a6; color: white; border: none; border-radius: 4px; padding: 4px 16px; font-weight: bold; } QPushButton:hover { background-color: #0d9488; } QPushButton:disabled { background-color: #94a3b8; }")
    
    def _monitor_loop(self):
        while self.monitoring:
            if not self.fluke_reader or not self.fluke_reader.is_connected():
                self.monitoring = False
                break
            try:
                data = self.fluke_reader.read_all()
                data['timestamp'] = datetime.now()
                self.env_history.append(data)
                if len(self.env_history) > 50:
                    self.env_history = self.env_history[-50:]
                self.signal.data_updated.emit(data)
            except Exception as e:
                print(f"Env monitor error: {e}")
            time.sleep(2)
    
    # ── UI Update (main thread via signal) ──
    def _on_data(self, data):
        """Update readout cards, real-time graph, and history table"""
        def _fmt(v):
            return f"{v:.2f}" if v is not None else "--"
        
        # Update readout cards
        mapping = {
            "Temperature 1": 'temperature1',
            "Temperature 2": 'temperature2',
            "Humidity": 'humidity',
            "Dewpoint": 'dewpoint',
        }
        for label, key in mapping.items():
            self.big_labels[label].setText(_fmt(data.get(key)))
        
        # Update real-time graph
        self._update_realtime_graph(data)
        
        # Update history table (insert at top)
        ts = data.get('timestamp')
        ts_str = ts.strftime("%H:%M:%S") if ts else "--"
        
        self.history_table.insertRow(0)
        self.history_table.setItem(0, 0, QTableWidgetItem(ts_str))
        self.history_table.setItem(0, 1, QTableWidgetItem(_fmt(data.get('temperature1'))))
        self.history_table.setItem(0, 2, QTableWidgetItem(_fmt(data.get('temperature2'))))
        self.history_table.setItem(0, 3, QTableWidgetItem(_fmt(data.get('humidity'))))
        self.history_table.setItem(0, 4, QTableWidgetItem(_fmt(data.get('dewpoint'))))
        
        while self.history_table.rowCount() > 50:
            self.history_table.removeRow(self.history_table.rowCount() - 1)
    
    def _update_realtime_graph(self, data):
        """Update the real-time graph with new data - dual Y-axis like SmartGraph3"""
        try:
            now = data.get('timestamp', datetime.now())
            temp_val = data.get('temperature1')
            humid_val = data.get('humidity')
            
            if temp_val is not None:
                self.rt_times.append(now)
                self.rt_temps.append(temp_val)
                self.rt_humids.append(humid_val if humid_val is not None else 0)
                
                # Keep rolling window
                if len(self.rt_times) > self.max_rt_points:
                    self.rt_times = self.rt_times[-self.max_rt_points:]
                    self.rt_temps = self.rt_temps[-self.max_rt_points:]
                    self.rt_humids = self.rt_humids[-self.max_rt_points:]
            
            # Redraw
            self.rt_ax.clear()
            self.rt_ax2.clear()
            
            self.rt_ax.set_facecolor('white')
            self.rt_ax.grid(True, linestyle='-', alpha=0.3)
            
            if len(self.rt_times) > 1:
                # Temperature on left axis (Orange)
                line1, = self.rt_ax.plot(self.rt_times, self.rt_temps,
                    color='#FF6600', linewidth=1.5, label='Temperature [°C]')
                # Humidity on right axis (Cyan)
                line2, = self.rt_ax2.plot(self.rt_times, self.rt_humids,
                    color='#00BFFF', linewidth=1.5, label='Humidity [%RH]')
                
                # Combined legend
                lines = [line1, line2]
                labels = [l.get_label() for l in lines]
                self.rt_ax.legend(lines, labels, loc='upper left', fontsize=7,
                    facecolor='white', edgecolor='gray', framealpha=0.9)
            
            # Axis labels and colors
            self.rt_ax.set_ylabel('Temperature [°C]', fontsize=9, color='#FF6600')
            self.rt_ax2.set_ylabel('Humidity [%RH]', fontsize=9, color='#00BFFF')
            self.rt_ax.tick_params(axis='y', colors='#FF6600', labelsize=8)
            self.rt_ax2.tick_params(axis='y', colors='#00BFFF', labelsize=8)
            
            # Date range title
            if self.rt_times:
                start_t = self.rt_times[0].strftime('%d/%m/%Y %H:%M:%S')
                end_t = self.rt_times[-1].strftime('%d/%m/%Y %H:%M:%S')
                self.rt_ax.set_title(f'({start_t} — {end_t})', fontsize=8, color='#374151')
            
            # X-axis formatting
            self.rt_ax.xaxis.set_major_formatter(self._mdates.DateFormatter('%H:%M:%S'))
            self.rt_ax.tick_params(axis='x', colors='black', labelsize=7)
            for lbl in self.rt_ax.get_xticklabels():
                lbl.set_rotation(30)
            
            self.rt_fig.tight_layout()
            self.rt_canvas.draw()
            
            # Update time label
            self.rt_time_label.setText(f"Last update: {now.strftime('%H:%M:%S')}")
            
        except Exception as e:
            print(f"Graph update error: {e}")


class MeasurementToolsHub(QMainWindow):
    """Main hub window for all measurement instruments"""
    
    def __init__(self):
        super().__init__()
        self.current_instrument = None
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("Measurement Tools Hub - Cal-Lab")
        self.setGeometry(50, 50, 1400, 900)
        
        # Create central widget
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(0)
        main_layout.setContentsMargins(0, 0, 0, 0)
        
        # Header
        header = self.create_header()
        main_layout.addWidget(header)
        
        # Content area
        content_layout = QHBoxLayout()
        content_layout.setSpacing(0)
        content_layout.setContentsMargins(0, 0, 0, 0)
        
        # Sidebar
        sidebar = self.create_sidebar()
        content_layout.addWidget(sidebar)

        
        # Main content area (stacked widget)
        self.stacked_widget = QStackedWidget()
        self.stacked_widget.setStyleSheet("background-color: #f8f9fa;")
        
        # Add pages
        self.home_page = self.create_home_page()
        self.stacked_widget.addWidget(self.home_page)
        
        # Add instrument pages
        if COUNTER_AVAILABLE:
            self.counter_widget = UniversalCounterGUI()
            self.counter_widget.setWindowFlags(Qt.WindowType.Widget)  # Make it a widget, not a window
            self.stacked_widget.addWidget(self.counter_widget)
        else:
            self.counter_widget = QLabel("Universal Counter module not available")
            self.stacked_widget.addWidget(self.counter_widget)
        
        # Multimeter
        if MULTIMETER_AVAILABLE:
            self.multimeter_widget = DigitalMultimeterGUI()
            self.multimeter_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.multimeter_widget)
        else:
            self.multimeter_widget = MultimeterWidget()
            self.stacked_widget.addWidget(self.multimeter_widget)
        
        # HP 3458A Multimeter
        if MULTIMETER_3458_AVAILABLE:
            self.multimeter_3458_widget = HP3458MultimeterGUI()
            self.multimeter_3458_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.multimeter_3458_widget)
        else:
            self.multimeter_3458_widget = QLabel("HP 3458A Multimeter module not available")
            self.stacked_widget.addWidget(self.multimeter_3458_widget)
        
        self.oscilloscope_widget = OscilloscopeWidget()
        self.stacked_widget.addWidget(self.oscilloscope_widget)
        
        self.power_supply_widget = PowerSupplyWidget()
        self.stacked_widget.addWidget(self.power_supply_widget)
        
        self.signal_generator_widget = SignalGeneratorWidget()
        self.stacked_widget.addWidget(self.signal_generator_widget)
        
        self.spectrum_analyzer_widget = SpectrumAnalyzerWidget()
        self.stacked_widget.addWidget(self.spectrum_analyzer_widget)
        
        # HP 34401A Multimeter (Index 8)
        if MULTIMETER_34401_AVAILABLE:
            self.multimeter_34401_widget = HP34401MultimeterGUI()
            self.multimeter_34401_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.multimeter_34401_widget)
        else:
            self.multimeter_34401_widget = QLabel("HP 34401A Multimeter module not available")
            self.stacked_widget.addWidget(self.multimeter_34401_widget)
        
        # Fluke 8508A Reference Multimeter (Index 9)
        if MULTIMETER_8508_AVAILABLE:
            self.multimeter_8508_widget = Fluke8508MultimeterGUI()
            self.multimeter_8508_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.multimeter_8508_widget)
        else:
            self.multimeter_8508_widget = QLabel("Fluke 8508A module not available")
            self.stacked_widget.addWidget(self.multimeter_8508_widget)
        
        # Keysight 34465A Multimeter (Index 10)
        if MULTIMETER_34465_AVAILABLE:
            self.multimeter_34465_widget = Keysight34465MultimeterGUI()
            self.multimeter_34465_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.multimeter_34465_widget)
        else:
            self.multimeter_34465_widget = QLabel("Keysight 34465A module not available")
            self.stacked_widget.addWidget(self.multimeter_34465_widget)

        # R&S Power Meter (Index 11) - Using a new index
        if RS_POWER_METER_AVAILABLE:
            self.rs_power_meter_widget = RSPowerMeterGUI()
            self.rs_power_meter_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.rs_power_meter_widget)
        else:
            self.rs_power_meter_widget = QLabel("Rohde & Schwarz Power Meter module not available")
            self.stacked_widget.addWidget(self.rs_power_meter_widget)
        
        # HP/Agilent 33120A Waveform Generator (Index 12)
        if WAVEFORM_33120A_AVAILABLE:
            self.waveform_33120a_widget = HP33120AGeneratorGUI()
            self.waveform_33120a_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.waveform_33120a_widget)
        else:
            self.waveform_33120a_widget = QLabel("HP/Agilent 33120A Waveform Generator module not available")
            self.stacked_widget.addWidget(self.waveform_33120a_widget)

        # Agilent N1996A CSA Spectrum Analyzer (Index 13)
        if SPECTRUM_N1996A_AVAILABLE:
            self.spectrum_n1996a_widget = AgilentN1996AGUI()
            self.spectrum_n1996a_widget.setWindowFlags(Qt.WindowType.Widget)
            self.stacked_widget.addWidget(self.spectrum_n1996a_widget)
        else:
            self.spectrum_n1996a_widget = QLabel("Agilent N1996A Spectrum Analyzer module not available")
            self.stacked_widget.addWidget(self.spectrum_n1996a_widget)
        
        # Environment Monitor Widget (Index 13)
        self.env_monitor_widget = EnvironmentMonitorWidget()
        self.env_monitor_widget.signal.data_updated.connect(self._update_env_navbar)
        self.stacked_widget.addWidget(self.env_monitor_widget)
        
        content_layout.addWidget(self.stacked_widget, 1)
        
        main_layout.addLayout(content_layout, 1)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background-color: #f8f9fa;
                color: #5f6368;
                font-weight: 500;
                border-top: 1px solid #e5e7eb;
                padding: 8px 20px;
                font-size: 11px;
                font-family: 'Consolas', monospace;
                letter-spacing: 0.5px;
            }
        """)
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("● SYSTEM READY | Select an instrument to begin measurement")
        

    
    def create_header(self):
        """Create the header section"""
        self.header = QFrame()
        self.header.setObjectName("header")
        self.header.setStyleSheet("""
            QFrame#header {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                    stop:0 #4A90E2, stop:0.5 #50C9E8, stop:1 #7DD3C0);
                border: none;
            }
        """)
        self.header.setMinimumHeight(70)
        self.header.setMaximumHeight(70)
        
        layout = QHBoxLayout(self.header)
        layout.setContentsMargins(30, 15, 30, 15)
        
        # Professional title
        title_label = QLabel("⚙ MEASUREMENT TOOLS HUB")
        title_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        title_label.setStyleSheet("""
            color: white; 
            letter-spacing: 2px;
            font-weight: 600;
        """)
        layout.addWidget(title_label)
        
        layout.addStretch()
        
        # Environment indicator badge (clickable)
        self.env_badge = QPushButton("🌡️ --°C  |  💧 --%RH")
        self.env_badge.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        self.env_badge.setCursor(Qt.CursorShape.PointingHandCursor)
        self.env_badge.setStyleSheet("""
            QPushButton {
                color: white;
                background-color: rgba(255, 255, 255, 0.18);
                border: 1px solid rgba(255, 255, 255, 0.35);
                border-radius: 6px;
                padding: 6px 14px;
                letter-spacing: 0.5px;
            }
            QPushButton:hover {
                background-color: rgba(255, 255, 255, 0.30);
                border: 1px solid rgba(255, 255, 255, 0.55);
            }
        """)
        self.env_badge.clicked.connect(lambda: self.switch_page(13))
        layout.addWidget(self.env_badge)
        
        layout.addSpacing(12)
        
        # System status indicator
        status_widget = QWidget()
        status_layout = QHBoxLayout(status_widget)
        status_layout.setContentsMargins(0, 0, 0, 0)
        status_layout.setSpacing(6)
        
        status_led = QLabel("●")
        status_led.setFont(QFont("Segoe UI", 10))
        status_led.setStyleSheet("color: #2ecc71;")
        
        status_text = QLabel("SYSTEM READY")
        status_text.setFont(QFont("Consolas", 9, QFont.Weight.Medium))
        status_text.setStyleSheet("color: white; letter-spacing: 1px;")
        
        status_layout.addWidget(status_led)
        status_layout.addWidget(status_text)
        layout.addWidget(status_widget)
        
        layout.addSpacing(12)
        
        # Lab badge
        info_label = QLabel("CAL-LAB")
        info_label.setFont(QFont("Consolas", 10, QFont.Weight.Bold))
        info_label.setStyleSheet("""
            color: #4A90E2;
            background-color: white;
            padding: 6px 14px;
            border-radius: 4px;
            letter-spacing: 1.5px;
        """)
        layout.addWidget(info_label)
        
        return self.header
    
    def create_sidebar(self):
        """Create the sidebar navigation"""
        self.sidebar = QFrame()
        self.sidebar.setObjectName("sidebar")
        self.sidebar.setStyleSheet("""
            QFrame#sidebar {
                background-color: #ffffff;
                border-right: 1px solid #e5e7eb;
            }
        """)
        self.sidebar.setMinimumWidth(250)
        self.sidebar.setMaximumWidth(250)
        
        # Create scroll area for sidebar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("""
            QScrollArea {
                border: none;
                background-color: transparent;
            }
            QScrollBar:vertical {
                background-color: #f3f4f6;
                width: 6px;
            }
            QScrollBar::handle:vertical {
                background-color: #d1d5db;
                border-radius: 3px;
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
                height: 0px;
            }
        """)
        
        scroll_content = QWidget()
        scroll_content.setObjectName("sidebar_content")
        scroll_content.setStyleSheet("QWidget#sidebar_content { background-color: #ffffff; }")
        layout = QVBoxLayout(scroll_content)
        layout.setSpacing(4)
        layout.setContentsMargins(8, 16, 8, 16)
        
        # Navigation buttons
        self.nav_buttons = []
        self.category_widgets = {}  # Store category widgets for collapse/expand
        
        # Home button
        home_btn = self.create_nav_button("🏠 Home", 0)
        layout.addWidget(home_btn)
        
        # Main separator
        layout.addWidget(self.create_separator())
        
        # ========== DC/AC CATEGORY ==========
        dc_ac_label, dc_ac_container = self.create_collapsible_category(
            "⚡ DC/AC Instruments",
            [
                ("📟 FLUKE 8846A Precision Multimeter", 2, MULTIMETER_AVAILABLE),
                ("📟 HP 3458A Multimeter", 3, MULTIMETER_3458_AVAILABLE),
                ("📟 HP 34401A Multimeter", 8, MULTIMETER_34401_AVAILABLE),
                ("📟 Keysight 34465A Multimeter", 10, MULTIMETER_34465_AVAILABLE),
                ("📟 Fluke 8508A Reference Multimeter", 9, MULTIMETER_8508_AVAILABLE),
                ("⚡ Power Supply", 5, False),
                ("🔋 DC Source", 10, False),
            ]
        )
        layout.addWidget(dc_ac_label)
        layout.addWidget(dc_ac_container)
        self.category_widgets['dc_ac'] = dc_ac_container
        
        # ========== RF CATEGORY ==========
        rf_label, rf_container = self.create_collapsible_category(
            "📡 RF Instruments",
            [
                ("🔬 Agilent 53132 Universal Counter", 1, COUNTER_AVAILABLE),
                ("📡 Power Meter (R&S NRP)", 11, RS_POWER_METER_AVAILABLE),
                ("🌊 HP 33120A Waveform Generator", 12, WAVEFORM_33120A_AVAILABLE),
                ("📡 Agilent N1996A Spectrum Analyzer", 13, SPECTRUM_N1996A_AVAILABLE),
                ("🌊 Signal Generator", 6, False),
                ("📻 Network Analyzer", 10, False),
            ]
        )
        layout.addWidget(rf_label)
        layout.addWidget(rf_container)
        self.category_widgets['rf'] = rf_container
        
        # ========== OSCILLOSCOPE CATEGORY ==========
        scope_label, scope_container = self.create_collapsible_category(
            "📊 Oscilloscope",
            [
                ("📊 Digital Oscilloscope", 4, False),
                ("🔍 Mixed Signal Scope", 10, False),
            ]
        )
        layout.addWidget(scope_label)
        layout.addWidget(scope_container)
        self.category_widgets['scope'] = scope_container
        
        # ========== AVIONICS CATEGORY ==========
        avionics_label, avionics_container = self.create_collapsible_category(
            "✈️ Avionics",
            [
                ("✈️ Avionics Tester", 10, False),
                ("🧭 Navigation Tester", 11, False),
            ]
        )
        layout.addWidget(avionics_label)
        layout.addWidget(avionics_container)
        self.category_widgets['avionics'] = avionics_container
        
        # ========== FIBRE OPTICS CATEGORY ==========
        fiber_label, fiber_container = self.create_collapsible_category(
            "💡 Fibre Optics",
            [
                ("💡 Optical Power Meter", 12, False),
                ("🔦 Light Source", 13, False),
                ("📏 OTDR", 14, False),
            ]
        )
        layout.addWidget(fiber_label)
        layout.addWidget(fiber_container)
        self.category_widgets['fiber'] = fiber_container
        
        # ========== ENVIRONMENT CATEGORY ==========
        env_label, env_container = self.create_collapsible_category(
            "🌡️ Environment",
            [
                ("🌡️ Fluke 1620A Env Monitor", 13, FLUKE1620_AVAILABLE),
            ]
        )
        layout.addWidget(env_label)
        layout.addWidget(env_container)
        self.category_widgets['environment'] = env_container
        
        layout.addStretch()
        
        # About button
        about_btn = QPushButton("ℹ️ About")
        about_btn.setFont(QFont("Segoe UI", 11))
        about_btn.setStyleSheet(self.get_nav_button_style())
        about_btn.clicked.connect(self.show_about)
        layout.addWidget(about_btn)
        
        scroll.setWidget(scroll_content)
        
        sidebar_layout = QVBoxLayout(self.sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.addWidget(scroll)
        
        return self.sidebar
    
    def create_collapsible_category(self, title, instruments):
        """Create a collapsible category with toggle button"""
        # Create container widget
        container_widget = QWidget()
        container_layout = QVBoxLayout(container_widget)
        container_layout.setContentsMargins(0, 0, 0, 0)
        container_layout.setSpacing(2)
        
        # Create category header with arrow button
        header_widget = QWidget()
        header_widget.setStyleSheet("""
            QWidget {
                background-color: transparent;
                border: none;
            }
        """)
        header_layout = QHBoxLayout(header_widget)
        header_layout.setContentsMargins(10, 8, 10, 8)
        header_layout.setSpacing(8)
        
        # Category label
        label = QLabel(title)
        label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        label.setStyleSheet("""
            QLabel {
                color: #5f6368;
                background-color: transparent;
                text-transform: uppercase;
                letter-spacing: 0.8px;
                border: none;
                border-bottom: none;
            }
        """)
        header_layout.addWidget(label)
        header_layout.addStretch()
        
        # Arrow button for toggle (moved to right side)
        arrow_btn = QPushButton("▼")
        arrow_btn.setFixedSize(24, 24)
        arrow_btn.setFont(QFont("Segoe UI", 10))
        arrow_btn.setStyleSheet("""
            QPushButton {
                background-color: transparent;
                color: #4A90E2;
                border: none;
                font-weight: bold;
            }
            QPushButton:hover {
                color: #50C9E8;
            }
        """)
        header_layout.addWidget(arrow_btn)
        
        # Create instruments container
        instruments_widget = QWidget()
        instruments_layout = QVBoxLayout(instruments_widget)
        instruments_layout.setContentsMargins(0, 0, 0, 0)
        instruments_layout.setSpacing(2)
        
        # Add instrument buttons
        for name, index, available in instruments:
            btn = self.create_nav_button(name, index, available)
            instruments_layout.addWidget(btn)
        
        # Toggle function
        def toggle_category():
            is_visible = instruments_widget.isVisible()
            instruments_widget.setVisible(not is_visible)
            arrow_btn.setText("▶" if is_visible else "▼")
        
        arrow_btn.clicked.connect(toggle_category)
        
        return header_widget, instruments_widget
    
    def create_category_label(self, text):
        """Create a category label for sidebar"""
        label = QLabel(text)
        label.setFont(QFont("Segoe UI", 9, QFont.Weight.Bold))
        label.setStyleSheet("""
            QLabel {
                color: #5f6368;
                padding: 16px 20px 8px 20px;
                background-color: transparent;
                text-transform: uppercase;
                letter-spacing: 0.8px;
            }
        """)
        return label
    
    def create_nav_button(self, text, index, enabled=True):
        """Create a navigation button"""
        btn = QPushButton(text)
        btn.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        btn.setMinimumHeight(45)
        btn.setStyleSheet(self.get_nav_button_style())
        btn.setEnabled(enabled)
        btn.clicked.connect(lambda: self.switch_page(index))
        self.nav_buttons.append(btn)
        return btn
    
    def create_separator(self):
        """Create a visual separator"""
        separator = QFrame()
        separator.setFrameShape(QFrame.Shape.HLine)
        separator.setStyleSheet("background-color: #e8eaed; margin: 12px 20px;")
        separator.setMaximumHeight(1)
        return separator
    
    def get_nav_button_style(self):
        """Get stylesheet for navigation buttons"""
        return """
            QPushButton {
                background-color: transparent;
                color: #4b5563;
                border: none;
                border-radius: 6px;
                padding: 12px 16px;
                text-align: left;
                font-size: 11px;
                font-weight: 500;
                letter-spacing: 0.3px;
            }
            QPushButton:hover:enabled {
                background-color: rgba(74, 144, 226, 0.1);
                color: #4A90E2;
                border-left: 3px solid #50C9E8;
            }
            QPushButton:pressed:enabled {
                background-color: rgba(52, 152, 219, 0.2);
            }
            QPushButton:disabled {
                color: #9ca3af;
            }
        """

    def create_home_page(self):
        """Create the home page with instrument cards"""
        page = QWidget()
        layout = QVBoxLayout(page)
        layout.setContentsMargins(40, 40, 40, 40)
        layout.setSpacing(25)
        
        # Welcome Header Section
        header_layout = QVBoxLayout()
        header_layout.setSpacing(6)
        
        welcome_label = QLabel("INSTRUMENT SELECTION")
        welcome_label.setFont(QFont("Segoe UI", 22, QFont.Weight.Bold))
        welcome_label.setStyleSheet("color: #4b5563; letter-spacing: 1.5px;")
        header_layout.addWidget(welcome_label)
        
        subtitle = QLabel("Select a measurement instrument to configure and begin data acquisition")
        subtitle.setFont(QFont("Segoe UI", 11))
        subtitle.setStyleSheet("color: #7f8c8d;")
        header_layout.addWidget(subtitle)
        
        layout.addLayout(header_layout)
        
        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setStyleSheet("background-color: #d1d5db; margin-bottom: 10px;")
        line.setMaximumHeight(1)
        layout.addWidget(line)
        
        # Scroll area for cards with modern scrollbar
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        
        # Modern scrollbar styling
        scroll.setStyleSheet("""
            QScrollArea { 
                border: none; 
                background-color: transparent; 
            }
            QScrollBar:vertical {
                background-color: transparent;
                width: 8px;
                margin: 0px;
            }
            QScrollBar::handle:vertical {
                background-color: #d1d5db;
                border-radius: 4px;
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
                height: 8px;
                margin: 0px;
            }
            QScrollBar::handle:horizontal {
                background-color: #d1d5db;
                border-radius: 4px;
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
        
        scroll_content = QWidget()
        grid_layout = QGridLayout(scroll_content)
        grid_layout.setSpacing(20)
        grid_layout.setContentsMargins(4, 4, 4, 4)
        
        # Create instrument cards
        instruments = [
            ("Agilent 53132 Universal Counter", "Frequency and time interval measurements.", "🔬", 
             "Available" if COUNTER_AVAILABLE else "Not Available", 1),
            ("FLUKE 8846A Precision Multimeter", "6.5-digit precision multimeter for voltage, current, and resistance.", "📟", 
             "Available" if MULTIMETER_AVAILABLE else "Not Available", 2),
            ("HP 3458A Multimeter", "8.5-digit high-precision multimeter with NPLC control.", "📟", 
             "Available" if MULTIMETER_3458_AVAILABLE else "Not Available", 3),
            ("HP 34401A Multimeter", "6.5-digit multimeter with dB/dBm and Sniffing feature.", "📟", 
             "Available" if MULTIMETER_34401_AVAILABLE else "Not Available", 8),
            ("Keysight 34465A Multimeter", "6.5-digit Truevolt DMM with Temperature and Capacitance measurement.", "📟", 
             "Available" if MULTIMETER_34465_AVAILABLE else "Not Available", 10),
            ("Fluke 8508A Reference Multimeter", "8.5-digit reference multimeter for calibration.", "📟", 
             "Not Ready", 9),
            ("Oscilloscope", "Waveform visualization and analysis.", "📊", 
             "Coming Soon", 4),
            ("Power Supply", "Programmable voltage and current source.", "⚡", 
             "Coming Soon", 5),
            ("Signal Generator", "Arbitrary waveform generation.", "🌊", 
             "Coming Soon", 6),
            ("Agilent N1996A CSA", "Cable & Antenna Spectrum Analyzer, 100 kHz – 3 GHz.", "📡",
             "Available" if SPECTRUM_N1996A_AVAILABLE else "Not Available", 13),
        ]
        
        row, col = 0, 0
        for title, desc, icon, status, index in instruments:
            card = InstrumentCard(title, desc, icon, status)
            card.setCursor(Qt.CursorShape.PointingHandCursor)
            card.mousePressEvent = lambda event, idx=index: self.switch_page(idx)
            grid_layout.addWidget(card, row, col)
            
            col += 1
            if col > 2:  # 3 columns
                col = 0
                row += 1
        
        # Add spacers to push content up if grid is not full
        grid_layout.setRowStretch(row + 1, 1)
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll, 1)
        
        # Professional stats panel
        stats_frame = QFrame()
        stats_frame.setStyleSheet("""
            QFrame {
                background-color: #f5f5f7;
                border: 1px solid #d1d5db;
                border-radius: 8px;
            }
        """)
        stats_frame.setMaximumHeight(85)
        
        stats_layout = QHBoxLayout(stats_frame)
        stats_layout.setSpacing(50)
        stats_layout.setContentsMargins(30, 15, 30, 15)
        
        stats = [
            ("TOTAL", "7"),
            ("ONLINE", "3"),
            ("OFFLINE", "4"),
        ]
        
        for label, value in stats:
            stat_widget = QWidget()
            stat_layout = QHBoxLayout(stat_widget)
            stat_layout.setSpacing(12)
            stat_layout.setContentsMargins(0, 0, 0, 0)
            
            value_label = QLabel(value)
            value_label.setFont(QFont("Consolas", 26, QFont.Weight.Bold))
            value_label.setStyleSheet("color: #2980b9;")
            
            label_label = QLabel(label)
            label_label.setFont(QFont("Segoe UI", 10, QFont.Weight.Medium))
            label_label.setStyleSheet("color: #7f8c8d; letter-spacing: 1px;")
            
            stat_layout.addWidget(value_label)
            stat_layout.addWidget(label_label)
            
            stats_layout.addWidget(stat_widget)
        
        stats_layout.addStretch()
        
        layout.addWidget(stats_frame)
        
        return page
    
    def _update_env_navbar(self, data):
        """Update the env badge in the navbar with live temp/humidity values"""
        def _f(v):
            return f"{v:.1f}" if v is not None else "--"
        temp = _f(data.get('temperature1'))
        humid = _f(data.get('humidity'))
        self.env_badge.setText(f"🌡️ {temp}°C  |  💧 {humid}%RH")
    
    def switch_page(self, index):
        """Switch to a different page"""
        self.stacked_widget.setCurrentIndex(index)
        
        # Update status bar
        pages = [
            "Home - Select an instrument to begin",
            "Agilent 53132 Universal Counter - Frequency and time measurements",
            "FLUKE 8846A Precision Multimeter - Voltage, current, and resistance",
            "HP 3458A Multimeter - High-precision measurement",
            "Oscilloscope - Under development",
            "Power Supply - Under development",
            "Signal Generator - Under development",
            "Spectrum Analyzer - Under development",
            "HP 34401A Multimeter - 6.5-digit precision measurement",
            "Fluke 8508A Reference Multimeter - 8.5-digit reference measurement",
            "Keysight 34465A Multimeter - 6.5-digit Truevolt with Temperature/Capacitance",
            "Rohde & Schwarz Power Meter - Precision Power Measurement (dBm/W)"
        ]
        
        if index < len(pages):
            self.status_bar.showMessage(pages[index])
    
    def show_about(self):
        """Show about dialog"""
        about_text = """
        <h2>Measurement Tools Hub</h2>
        <p><b>Version:</b> 1.0.0</p>
        <p><b>Developer:</b> Cal-Lab</p>
        <p><b>Created:</b> 2026-01-12</p>
        <br>
        <p>A comprehensive control center for laboratory measurement instruments.</p>
        <br>
        <p><b>Available Instruments:</b></p>
        <ul>
            <li>✅ Universal Counter</li>
            <li>🚧 Digital Multimeter (Coming Soon)</li>
            <li>🚧 Oscilloscope (Coming Soon)</li>
            <li>🚧 Power Supply (Coming Soon)</li>
            <li>🚧 Signal Generator (Coming Soon)</li>
            <li>🚧 Spectrum Analyzer (Coming Soon)</li>
        </ul>
        <br>
        <p><b>Dependencies:</b></p>
        <ul>
            <li>PyQt6 - GUI Framework</li>
            <li>PyVISA - Instrument Communication</li>
            <li>Matplotlib - Data Visualization</li>
        </ul>
        """
        
        QMessageBox.about(self, "About Measurement Tools Hub", about_text)
    



def main():
    """Main application entry point"""
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Set application info
    app.setApplicationName("Measurement Tools Hub")
    app.setOrganizationName("Cal-Lab")
    
    window = MeasurementToolsHub()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
