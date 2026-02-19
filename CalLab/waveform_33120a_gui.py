"""
HP/Agilent 33120A Waveform Generator GUI Application
A modern PyQt6-based GUI for controlling HP/Agilent 33120A 15 MHz Function/Arbitrary Waveform Generator
"""

import sys
from datetime import datetime
from pathlib import Path
import numpy as np

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QPushButton, QLabel, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QGroupBox, QRadioButton, QButtonGroup, QStatusBar,
    QMessageBox, QCheckBox, QScrollArea, QFrame, QSizePolicy, QLayout
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QLocale, QRect, QSize, QPoint
from PyQt6.QtGui import QFont
import time

try:
    import matplotlib
    matplotlib.use('QtAgg')
    from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
    from matplotlib.figure import Figure
    import matplotlib.pyplot as plt
    MATPLOTLIB_AVAILABLE = True
except ImportError:
    MATPLOTLIB_AVAILABLE = False

try:
    import pyvisa
    PYVISA_AVAILABLE = True
except ImportError:
    PYVISA_AVAILABLE = False


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


class HP33120AGeneratorGUI(QMainWindow):
    """Main GUI window for HP 33120A Waveform Generator application"""
    
    def __init__(self):
        super().__init__()
        self.current_waveform = "SINusoid"
        self.output_enabled = False
        self.init_ui()
    
    def init_ui(self):
        """Initialize the user interface"""
        self.setWindowTitle("HP/Agilent 33120A Waveform Generator Control Panel")
        
        # Fixed full screen size: 1920x1080, starting from top-left
        self.setGeometry(0, 0, 1920, 1080)
        
        # Set light theme
        self.set_light_theme()
        
        # Create central widget and main scroll area
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_box = QVBoxLayout(central_widget)
        main_box.setContentsMargins(0, 0, 0, 0)
        
        # Create scroll area
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll.setFrameShape(QScrollArea.Shape.NoFrame)
        
        # Scrollbar styling (Light mode)
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
        title = QLabel("🌊 HP/Agilent 33120A Function/Arbitrary Waveform Generator")
        title.setFont(QFont("Segoe UI", 18, QFont.Weight.Bold))
        title.setStyleSheet("color: #1a73e8; padding: 10px;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(title)
        
        # Connection group
        main_layout.addWidget(self.create_connection_group())
        
        # Waveform type group
        main_layout.addWidget(self.create_waveform_type_group())
        
        # Waveform settings group
        main_layout.addWidget(self.create_waveform_settings_group())
        
        # Modulation group
        main_layout.addWidget(self.create_modulation_group())
        
        # Output control group
        main_layout.addWidget(self.create_output_control_group())
        
        # Bottom section: Instrument Status (left) + Waveform Preview graph (right) — like 3458 style
        bottom_layout = QHBoxLayout()
        main_layout.addLayout(bottom_layout, 1)
        
        # Instrument Status — left side
        status_group = QGroupBox("📊 Instrument Status")
        status_group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        status_group.setStyleSheet(self.get_groupbox_style())
        status_layout = QVBoxLayout()
        
        self.status_text = QTextEdit()
        self.status_text.setReadOnly(True)
        self.status_text.setFont(QFont("Consolas", 9))
        self.status_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f9fa;
                border: 1px solid #dadce0;
                border-radius: 8px;
                padding: 10px;
                color: #3c4043;
            }
        """)
        status_layout.addWidget(self.status_text)
        status_group.setLayout(status_layout)
        bottom_layout.addWidget(status_group, 2)
        
        # Waveform Preview (graph) — right side, wider
        bottom_layout.addWidget(self.create_waveform_preview_group(), 3)
        
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
        self.status_bar.showMessage("✨ Ready - HP 33120A Waveform Generator Control")
        
        # Connect signals for live waveform preview
        self.frequency_spin.valueChanged.connect(self.update_waveform_preview)
        self.freq_unit_combo.currentTextChanged.connect(self.update_waveform_preview)
        self.amplitude_spin.valueChanged.connect(self.update_waveform_preview)
        self.offset_spin.valueChanged.connect(self.update_waveform_preview)
        self.duty_spin.valueChanged.connect(self.update_waveform_preview)
        
        # Initial draw
        self.update_waveform_preview()
        
        # Check dependencies
        self.check_dependencies()
        
        # Initialize with default message
        self.update_status_display("System initialized. Connect to instrument and configure waveform settings.")
    
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
    
    def create_waveform_type_group(self):
        """Create waveform type selection group"""
        group = QGroupBox("〰️ Waveform Type")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QHBoxLayout()
        
        self.waveform_group = QButtonGroup()
        
        # Waveform types with emojis
        waveforms = [
            ("〰️ Sine", "SINusoid"),
            ("⬜ Square", "SQUare"),
            ("△ Triangle", "TRIangle"),
            ("╱ Ramp", "RAMP"),
            ("⚡ Pulse", "PULSe"),
            ("❄️ Noise", "NOISe"),
            ("━ DC", "DC")
        ]
        
        for i, (label, wave_type) in enumerate(waveforms):
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
            radio.toggled.connect(lambda checked, w=wave_type: self.on_waveform_changed(checked, w))
            self.waveform_group.addButton(radio, i)
            layout.addWidget(radio)
            
            if i == 0:
                radio.setChecked(True)
        
        group.setLayout(layout)
        return group
    
    def create_waveform_settings_group(self):
        """Create waveform settings group"""
        group = QGroupBox("⚙️ Waveform Parameters")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        # Single horizontal row for all parameters
        row_layout = QHBoxLayout()
        row_layout.setSpacing(10)
        row_layout.setContentsMargins(4, 4, 4, 4)
        
        # --- Frequency ---
        freq_label = QLabel("Frequency:")
        freq_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(freq_label)
        
        self.frequency_spin = QDoubleSpinBox()
        self.frequency_spin.setRange(0.001, 15000000)
        self.frequency_spin.setValue(1000)
        self.frequency_spin.setDecimals(3)
        self.frequency_spin.setFont(QFont("Segoe UI", 10))
        self.frequency_spin.setStyleSheet(self.get_spinbox_style())
        self.frequency_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.frequency_spin.setMinimumWidth(130)
        row_layout.addWidget(self.frequency_spin)
        
        self.freq_unit_combo = QComboBox()
        self.freq_unit_combo.addItems(["Hz", "kHz", "MHz"])
        self.freq_unit_combo.setCurrentText("kHz")
        self.freq_unit_combo.setFont(QFont("Segoe UI", 10))
        self.freq_unit_combo.setStyleSheet(self.get_input_style())
        self.freq_unit_combo.setFixedWidth(65)
        row_layout.addWidget(self.freq_unit_combo)
        
        row_layout.addSpacing(8)
        
        # --- Amplitude ---
        amp_label = QLabel("Amplitude:")
        amp_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(amp_label)
        
        self.amplitude_spin = QDoubleSpinBox()
        self.amplitude_spin.setRange(0.01, 10.0)
        self.amplitude_spin.setValue(1.0)
        self.amplitude_spin.setDecimals(3)
        self.amplitude_spin.setFont(QFont("Segoe UI", 10))
        self.amplitude_spin.setStyleSheet(self.get_spinbox_style())
        self.amplitude_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.amplitude_spin.setMinimumWidth(110)
        row_layout.addWidget(self.amplitude_spin)
        
        amp_unit_label = QLabel("Vpp")
        amp_unit_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(amp_unit_label)
        
        row_layout.addSpacing(8)
        
        # --- DC Offset ---
        offset_label = QLabel("DC Offset:")
        offset_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(offset_label)
        
        self.offset_spin = QDoubleSpinBox()
        self.offset_spin.setRange(-5.0, 5.0)
        self.offset_spin.setValue(0.0)
        self.offset_spin.setDecimals(3)
        self.offset_spin.setFont(QFont("Segoe UI", 10))
        self.offset_spin.setStyleSheet(self.get_spinbox_style())
        self.offset_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.offset_spin.setMinimumWidth(110)
        row_layout.addWidget(self.offset_spin)
        
        offset_unit_label = QLabel("V")
        offset_unit_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(offset_unit_label)
        
        row_layout.addSpacing(8)
        
        # --- Output Load ---
        load_label = QLabel("Output Load:")
        load_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(load_label)
        
        self.load_combo = QComboBox()
        self.load_combo.addItems(["50 Ω", "High-Z"])
        self.load_combo.setFont(QFont("Segoe UI", 10))
        self.load_combo.setStyleSheet(self.get_input_style())
        self.load_combo.setFixedWidth(80)
        row_layout.addWidget(self.load_combo)
        
        row_layout.addSpacing(8)
        
        # --- Duty Cycle (hidden by default, shown for Square/Pulse) ---
        self.duty_label = QLabel("Duty Cycle:")
        self.duty_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(self.duty_label)
        
        self.duty_spin = QDoubleSpinBox()
        self.duty_spin.setRange(20, 80)
        self.duty_spin.setValue(50)
        self.duty_spin.setDecimals(1)
        self.duty_spin.setFont(QFont("Segoe UI", 10))
        self.duty_spin.setStyleSheet(self.get_spinbox_style())
        self.duty_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.duty_spin.setMinimumWidth(90)
        row_layout.addWidget(self.duty_spin)
        
        duty_unit_label = QLabel("%")
        duty_unit_label.setFont(QFont("Segoe UI", 10))
        row_layout.addWidget(duty_unit_label)
        
        # Initially hide duty cycle
        self.duty_label.hide()
        self.duty_spin.hide()
        duty_unit_label.hide()
        self.duty_unit_label_ref = duty_unit_label
        
        row_layout.addStretch()
        
        group.setLayout(row_layout)
        return group
    
    def create_waveform_preview_group(self):
        """Create waveform preview graph group"""
        group = QGroupBox("📈 Waveform Preview")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        layout = QVBoxLayout()
        layout.setContentsMargins(8, 8, 8, 8)
        
        if MATPLOTLIB_AVAILABLE:
            self.preview_figure = Figure(figsize=(8, 3.5), dpi=96, facecolor='#f8f9fa')
            self.preview_canvas = FigureCanvas(self.preview_figure)
            self.preview_canvas.setMinimumHeight(250)
            self.preview_ax = self.preview_figure.add_subplot(111)
            self.preview_figure.subplots_adjust(left=0.09, right=0.97, top=0.88, bottom=0.18)
            layout.addWidget(self.preview_canvas)
        else:
            no_graph_label = QLabel("⚠️ matplotlib not installed.\nInstall with: pip install matplotlib")
            no_graph_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            no_graph_label.setFont(QFont("Segoe UI", 10))
            no_graph_label.setStyleSheet("color: #f59e0b; padding: 20px;")
            layout.addWidget(no_graph_label)
        
        group.setLayout(layout)
        return group
    
    def update_waveform_preview(self):
        """Redraw the waveform preview based on current settings"""
        if not MATPLOTLIB_AVAILABLE or not hasattr(self, 'preview_ax'):
            return
        
        # Get current parameters
        freq_value = self.frequency_spin.value() if hasattr(self, 'frequency_spin') else 1000
        freq_unit = self.freq_unit_combo.currentText() if hasattr(self, 'freq_unit_combo') else 'kHz'
        amplitude = self.amplitude_spin.value() if hasattr(self, 'amplitude_spin') else 1.0
        offset = self.offset_spin.value() if hasattr(self, 'offset_spin') else 0.0
        duty = self.duty_spin.value() if hasattr(self, 'duty_spin') else 50.0
        waveform = self.current_waveform
        
        # Convert frequency to Hz for display label
        if freq_unit == 'kHz':
            freq_hz = freq_value * 1000
        elif freq_unit == 'MHz':
            freq_hz = freq_value * 1_000_000
        else:
            freq_hz = freq_value
        
        # Always show 3 complete cycles in the preview
        n_cycles = 3
        t = np.linspace(0, n_cycles, 1000)
        
        # Generate waveform
        if waveform == 'SINusoid':
            y = amplitude * np.sin(2 * np.pi * t) + offset
            color = '#1a73e8'
            label = 'Sine'
        elif waveform == 'SQUare':
            duty_frac = duty / 100.0
            y = amplitude * np.where((t % 1) < duty_frac, 1.0, -1.0) + offset
            color = '#16a34a'
            label = f'Square ({duty:.0f}% duty)'
        elif waveform == 'TRIangle':
            y = amplitude * (2 * np.abs(2 * (t % 1) - 1) - 1) + offset
            color = '#9334e9'
            label = 'Triangle'
        elif waveform == 'RAMP':
            y = amplitude * (2 * (t % 1) - 1) + offset
            color = '#f59e0b'
            label = 'Ramp'
        elif waveform == 'PULSe':
            duty_frac = duty / 100.0
            y = amplitude * np.where((t % 1) < duty_frac, 1.0, -1.0) + offset
            color = '#dc2626'
            label = f'Pulse ({duty:.0f}% duty)'
        elif waveform == 'NOISe':
            np.random.seed(42)
            y = amplitude * np.random.randn(len(t)) + offset
            color = '#6b7280'
            label = 'Noise'
        elif waveform == 'DC':
            y = np.full_like(t, offset)
            color = '#0891b2'
            label = 'DC'
        else:
            y = amplitude * np.sin(2 * np.pi * t) + offset
            color = '#1a73e8'
            label = waveform
        
        # Format frequency label
        if freq_hz >= 1_000_000:
            freq_label = f'{freq_hz/1_000_000:.3g} MHz'
        elif freq_hz >= 1000:
            freq_label = f'{freq_hz/1000:.3g} kHz'
        else:
            freq_label = f'{freq_hz:.3g} Hz'
        
        # Draw
        self.preview_ax.clear()
        self.preview_ax.plot(t, y, color=color, linewidth=1.8, antialiased=True)
        self.preview_ax.axhline(y=offset, color='#9ca3af', linewidth=0.8, linestyle='--', alpha=0.7)
        self.preview_ax.fill_between(t, offset, y, alpha=0.12, color=color)
        
        # Styling
        self.preview_ax.set_facecolor('#f8f9fa')
        self.preview_figure.patch.set_facecolor('#f8f9fa')
        self.preview_ax.set_xlabel('Time (cycles)', fontsize=8, color='#5f6368')
        self.preview_ax.set_ylabel('Voltage (V)', fontsize=8, color='#5f6368')
        self.preview_ax.set_title(
            f'{label}  |  {freq_label}  |  {amplitude:.3g} Vpp  |  Offset: {offset:+.3g} V',
            fontsize=9, color='#3c4043', fontweight='bold', pad=6
        )
        self.preview_ax.tick_params(labelsize=7, colors='#5f6368')
        self.preview_ax.spines['top'].set_visible(False)
        self.preview_ax.spines['right'].set_visible(False)
        self.preview_ax.spines['left'].set_color('#dadce0')
        self.preview_ax.spines['bottom'].set_color('#dadce0')
        self.preview_ax.grid(True, linestyle='--', alpha=0.4, color='#dadce0')
        self.preview_ax.set_xlim(0, n_cycles)
        
        # Y-axis limits with padding
        y_range = max(abs(amplitude), 0.01)
        self.preview_ax.set_ylim(offset - y_range * 1.4, offset + y_range * 1.4)
        
        self.preview_canvas.draw()
    
    def create_modulation_group(self):
        """Create modulation settings group"""
        group = QGroupBox("📡 Modulation")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QVBoxLayout()
        layout.setSpacing(12)
        
        # Modulation type
        mod_type_layout = QHBoxLayout()
        
        mod_label = QLabel("Modulation Type:")
        mod_label.setFont(QFont("Segoe UI", 10))
        mod_type_layout.addWidget(mod_label)
        
        self.modulation_combo = QComboBox()
        self.modulation_combo.addItems(["None", "AM", "FM", "PM", "FSK", "Burst"])
        self.modulation_combo.setFont(QFont("Segoe UI", 10))
        self.modulation_combo.setStyleSheet(self.get_input_style())
        self.modulation_combo.currentTextChanged.connect(self.on_modulation_changed)
        mod_type_layout.addWidget(self.modulation_combo)
        mod_type_layout.addStretch()
        
        layout.addLayout(mod_type_layout)
        
        # Modulation parameters container (will be shown/hidden based on selection)
        self.mod_params_widget = QWidget()
        mod_params_layout = FlowLayout(spacing=10)
        
        # AM Depth
        self.am_depth_label = QLabel("AM Depth:")
        self.am_depth_label.setFont(QFont("Segoe UI", 10))
        mod_params_layout.addWidget(self.am_depth_label)
        
        self.am_depth_spin = QDoubleSpinBox()
        self.am_depth_spin.setRange(0, 120)  # 0% to 120%
        self.am_depth_spin.setValue(50)
        self.am_depth_spin.setDecimals(1)
        self.am_depth_spin.setFont(QFont("Segoe UI", 10))
        self.am_depth_spin.setStyleSheet(self.get_spinbox_style())
        self.am_depth_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        mod_params_layout.addWidget(self.am_depth_spin)
        
        am_unit = QLabel("%")
        am_unit.setFont(QFont("Segoe UI", 10))
        mod_params_layout.addWidget(am_unit)
        
        # FM Deviation
        self.fm_dev_label = QLabel("FM Deviation:")
        self.fm_dev_label.setFont(QFont("Segoe UI", 10))
        mod_params_layout.addWidget(self.fm_dev_label)
        
        self.fm_dev_spin = QDoubleSpinBox()
        self.fm_dev_spin.setRange(0, 1000000)  # Up to 1 MHz
        self.fm_dev_spin.setValue(1000)
        self.fm_dev_spin.setDecimals(1)
        self.fm_dev_spin.setFont(QFont("Segoe UI", 10))
        self.fm_dev_spin.setStyleSheet(self.get_spinbox_style())
        self.fm_dev_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        mod_params_layout.addWidget(self.fm_dev_spin)
        
        fm_unit = QLabel("Hz")
        fm_unit.setFont(QFont("Segoe UI", 10))
        mod_params_layout.addWidget(fm_unit)
        
        # Mod Frequency
        self.mod_freq_label = QLabel("Mod Frequency:")
        self.mod_freq_label.setFont(QFont("Segoe UI", 10))
        mod_params_layout.addWidget(self.mod_freq_label)
        
        self.mod_freq_spin = QDoubleSpinBox()
        self.mod_freq_spin.setRange(0.001, 20000)
        self.mod_freq_spin.setValue(100)
        self.mod_freq_spin.setDecimals(3)
        self.mod_freq_spin.setFont(QFont("Segoe UI", 10))
        self.mod_freq_spin.setStyleSheet(self.get_spinbox_style())
        self.mod_freq_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        mod_params_layout.addWidget(self.mod_freq_spin)
        
        mod_freq_unit = QLabel("Hz")
        mod_freq_unit.setFont(QFont("Segoe UI", 10))
        mod_params_layout.addWidget(mod_freq_unit)
        
        self.mod_params_widget.setLayout(mod_params_layout)
        self.mod_params_widget.hide()  # Hidden by default
        
        layout.addWidget(self.mod_params_widget)
        
        group.setLayout(layout)
        return group
    
    def create_output_control_group(self):
        """Create output control group"""
        group = QGroupBox("🔊 Output Control")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QHBoxLayout()
        
        # Output enable/disable button
        self.output_btn = QPushButton("🔴 Output OFF")
        self.output_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        self.output_btn.setMinimumHeight(50)
        self.output_btn.setStyleSheet(self.get_button_style("#dc2626"))  # Red for OFF
        self.output_btn.clicked.connect(self.toggle_output)
        layout.addWidget(self.output_btn, 1)
        
        # Apply Settings button
        apply_btn = QPushButton("⚙️ Apply Settings")
        apply_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        apply_btn.setMinimumHeight(50)
        apply_btn.setStyleSheet(self.get_button_style("#1a73e8"))
        apply_btn.clicked.connect(self.apply_settings)
        layout.addWidget(apply_btn, 1)
        
        # Recall Config button
        recall_btn = QPushButton("📥 Recall Config")
        recall_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        recall_btn.setMinimumHeight(50)
        recall_btn.setStyleSheet(self.get_button_style("#9334e9"))
        recall_btn.clicked.connect(self.recall_config)
        layout.addWidget(recall_btn, 1)
        
        # Reset button
        reset_btn = QPushButton("🔄 Reset Instrument")
        reset_btn.setFont(QFont("Segoe UI", 12, QFont.Weight.Bold))
        reset_btn.setMinimumHeight(50)
        reset_btn.setStyleSheet(self.get_button_style("#f59e0b"))
        reset_btn.clicked.connect(self.reset_instrument)
        layout.addWidget(reset_btn, 1)
        
        group.setLayout(layout)
        return group
    
    def on_waveform_changed(self, checked, waveform_type):
        """Handle waveform type changes"""
        if checked:
            self.current_waveform = waveform_type
            if hasattr(self, 'status_bar'):
                self.status_bar.showMessage(f"Waveform type changed to: {waveform_type}")
            
            # Show/hide duty cycle for square and pulse waves
            if not hasattr(self, 'duty_label'):
                return  # Settings group not yet created during init
            if waveform_type in ["SQUare", "PULSe"]:
                self.duty_label.show()
                self.duty_spin.show()
                self.duty_unit_label_ref.show()
            else:
                self.duty_label.hide()
                self.duty_spin.hide()
                self.duty_unit_label_ref.hide()
            
            # Update waveform preview graph
            self.update_waveform_preview()
    
    def on_modulation_changed(self, mod_type):
        """Handle modulation type changes"""
        if mod_type == "None":
            self.mod_params_widget.hide()
        else:
            self.mod_params_widget.show()
            # Show/hide specific parameters based on modulation type
            # AM: show depth and mod frequency
            # FM: show deviation and mod frequency
            # PM: show phase and mod frequency
            # etc.
    
    def toggle_output(self):
        """Toggle output on/off"""
        resource_name = self.resource_combo.currentText().strip()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Available", "PyVISA is not installed. Cannot communicate with instrument.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            # Toggle output state
            self.output_enabled = not self.output_enabled
            
            if self.output_enabled:
                instrument.write("OUTPut:STATe ON")
                self.output_btn.setText("🟢 Output ON")
                self.output_btn.setStyleSheet(self.get_button_style("#16a34a"))  # Green for ON
                self.update_status_display("Output enabled.")
                self.status_bar.showMessage("✅ Output is ON")
            else:
                instrument.write("OUTPut:STATe OFF")
                self.output_btn.setText("🔴 Output OFF")
                self.output_btn.setStyleSheet(self.get_button_style("#dc2626"))  # Red for OFF
                self.update_status_display("Output disabled.")
                self.status_bar.showMessage("⭕ Output is OFF")
            
            instrument.close()
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to toggle output:\n{str(e)}")
            self.update_status_display(f"ERROR: Failed to toggle output - {str(e)}")
    
    def apply_settings(self):
        """Apply current settings to instrument"""
        resource_name = self.resource_combo.currentText().strip()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Available", "PyVISA is not installed. Cannot communicate with instrument.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            # Get current settings
            freq_value = self.frequency_spin.value()
            freq_unit = self.freq_unit_combo.currentText()
            
            # Convert frequency to Hz
            if freq_unit == "kHz":
                frequency = freq_value * 1000
            elif freq_unit == "MHz":
                frequency = freq_value * 1000000
            else:
                frequency = freq_value
            
            amplitude = self.amplitude_spin.value()
            offset = self.offset_spin.value()
            
            # Build SCPI command based on waveform type
            if self.current_waveform == "DC":
                scpi_cmd = f"APPLy:DC DEF, DEF, {offset}"
            else:
                scpi_cmd = f"APPLy:{self.current_waveform} {frequency} HZ, {amplitude} VPP, {offset} V"
            
            # Send command
            instrument.write(scpi_cmd)
            
            # Set output load
            load = self.load_combo.currentText()
            if load == "50 Ω":
                instrument.write("OUTPut:LOAD 50")
            else:
                instrument.write("OUTPut:LOAD INF")
            
            # Set duty cycle for square/pulse waves
            if self.current_waveform in ["SQUare", "PULSe"]:
                duty = self.duty_spin.value()
                instrument.write(f"FUNCtion:{self.current_waveform}:DCYCle {duty}")
            
            # Apply modulation if selected
            mod_type = self.modulation_combo.currentText()
            if mod_type != "None":
                self.apply_modulation(instrument, mod_type)
            
            instrument.close()
            
            self.update_status_display(f"Settings applied successfully.\nCommand sent: {scpi_cmd}")
            self.status_bar.showMessage(f"✅ Settings applied: {self.current_waveform} @ {freq_value} {freq_unit}")
            QMessageBox.information(self, "Success", "Settings applied successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to apply settings:\n{str(e)}")
            self.update_status_display(f"ERROR: Failed to apply settings - {str(e)}")
    
    def apply_modulation(self, instrument, mod_type):
        """Apply modulation settings to instrument"""
        try:
            if mod_type == "AM":
                depth = self.am_depth_spin.value()
                mod_freq = self.mod_freq_spin.value()
                instrument.write(f"AM:DEPTh {depth}")
                instrument.write(f"AM:INTernal:FREQuency {mod_freq}")
                instrument.write("AM:STATe ON")
            elif mod_type == "FM":
                deviation = self.fm_dev_spin.value()
                mod_freq = self.mod_freq_spin.value()
                instrument.write(f"FM:DEViation {deviation}")
                instrument.write(f"FM:INTernal:FREQuency {mod_freq}")
                instrument.write("FM:STATe ON")
            # Add PM, FSK, Burst handling as needed
            
        except Exception as e:
            raise Exception(f"Modulation error: {str(e)}")
    
    def recall_config(self):
        """Recall configuration from instrument"""
        resource_name = self.resource_combo.currentText().strip()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Available", "PyVISA is not installed.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            # Query current settings
            settings = []
            settings.append(f"Function: {instrument.query('FUNCtion:SHAPe?').strip()}")
            settings.append(f"Frequency: {instrument.query('FREQuency?').strip()} Hz")
            settings.append(f"Amplitude: {instrument.query('VOLTage?').strip()} Vpp")
            settings.append(f"Offset: {instrument.query('VOLTage:OFFSet?').strip()} V")
            settings.append(f"Output: {instrument.query('OUTPut:STATe?').strip()}")
            
            instrument.close()
            
            status_msg = "Current instrument configuration:\n" + "\n".join(settings)
            self.update_status_display(status_msg)
            QMessageBox.information(self, "Configuration", status_msg)
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to recall configuration:\n{str(e)}")
            self.update_status_display(f"ERROR: Failed to recall config - {str(e)}")
    
    def reset_instrument(self):
        """Reset instrument to default state"""
        reply = QMessageBox.question(
            self, "Confirm Reset",
            "Are you sure you want to reset the instrument to default settings?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.No:
            return
        
        resource_name = self.resource_combo.currentText().strip()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select a VISA resource first.")
            return
        
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Available", "PyVISA is not installed.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            instrument.write("*RST")
            time.sleep(2)  # Wait for reset to complete
            
            instrument.close()
            
            self.update_status_display("Instrument reset to default settings.")
            self.status_bar.showMessage("✅ Instrument reset successfully")
            QMessageBox.information(self, "Success", "Instrument reset successfully!")
            
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to reset instrument:\n{str(e)}")
            self.update_status_display(f"ERROR: Failed to reset instrument - {str(e)}")
    
    def refresh_resources(self):
        """Refresh available VISA resources"""
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Available", 
                              "PyVISA is not installed. Please install it using:\npip install pyvisa pyvisa-py")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            resources = rm.list_resources()
            
            self.resource_combo.clear()
            if resources:
                self.resource_combo.addItems(resources)
                self.status_bar.showMessage(f"✅ Found {len(resources)} VISA resource(s)")
                self.update_status_display(f"Found {len(resources)} VISA resources:\n" + "\n".join(resources))
            else:
                self.status_bar.showMessage("⚠️ No VISA resources found")
                self.update_status_display("No VISA resources found. Check connections.")
                QMessageBox.information(self, "No Resources", "No VISA resources detected. Please check connections.")
                
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Failed to scan for resources:\n{str(e)}")
            self.update_status_display(f"ERROR: Failed to scan resources - {str(e)}")
    
    def test_connection(self):
        """Test connection to selected instrument"""
        resource_name = self.resource_combo.currentText().strip()
        if not resource_name:
            QMessageBox.warning(self, "No Resource", "Please select or enter a VISA resource address.")
            return
        
        if not PYVISA_AVAILABLE:
            QMessageBox.warning(self, "PyVISA Not Available", "PyVISA is not installed.")
            return
        
        try:
            rm = pyvisa.ResourceManager()
            instrument = rm.open_resource(resource_name)
            instrument.timeout = 5000
            
            # Query instrument identity
            idn = instrument.query("*IDN?").strip()
            
            instrument.close()
            
            self.status_bar.showMessage("✅ Connection successful!")
            self.update_status_display(f"Connection successful!\nInstrument ID: {idn}")
            QMessageBox.information(self, "Connection Test", f"Successfully connected!\n\nInstrument ID:\n{idn}")
            
        except Exception as e:
            self.status_bar.showMessage("❌ Connection failed")
            self.update_status_display(f"Connection failed: {str(e)}")
            QMessageBox.critical(self, "Connection Failed", f"Could not connect to instrument.\n\nError:\n{str(e)}")
    
    def update_status_display(self, message):
        """Update status display with timestamp"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        current_text = self.status_text.toPlainText()
        new_entry = f"[{timestamp}] {message}\n"
        self.status_text.setPlainText(new_entry + ("="*60) + "\n" + current_text)
    
    def check_dependencies(self):
        """Check if required dependencies are available"""
        if not PYVISA_AVAILABLE:
            msg = "⚠️ PyVISA not installed. Install with: pip install pyvisa pyvisa-py"
            self.status_bar.showMessage(msg)
            self.update_status_display(msg)
    
    def set_light_theme(self):
        """Set light theme for the application"""
        self.setStyleSheet("""
            QMainWindow {
                background-color: #ffffff;
            }
            QWidget {
                background-color: #ffffff;
                color: #3c4043;
            }
        """)
    
    def get_groupbox_style(self):
        """Get stylesheet for group boxes"""
        return """
            QGroupBox {
                background-color: #ffffff;
                border: 2px solid #e8eaed;
                border-radius: 10px;
                margin-top: 12px;
                padding: 15px;
                font-weight: bold;
                color: #1a73e8;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 15px;
                padding: 0 8px;
                background-color: #ffffff;
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
                padding: 12px 24px;
                font-weight: bold;
                font-size: 11px;
            }}
            QPushButton:hover {{
                background-color: {color};
                opacity: 0.9;
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background-color: {color};
                transform: translateY(1px);
            }}
        """
    
    def get_spinbox_style(self):
        """Get stylesheet for spinboxes"""
        return """
            QSpinBox, QDoubleSpinBox {
                border: 2px solid #dadce0;
                border-radius: 6px;
                padding: 6px;
                background-color: #ffffff;
                color: #3c4043;
                font-size: 10px;
            }
            QSpinBox:focus, QDoubleSpinBox:focus {
                border: 2px solid #1a73e8;
            }
        """
    
    def get_input_style(self):
        """Get stylesheet for input fields"""
        return """
            QComboBox, QLineEdit {
                border: 2px solid #dadce0;
                border-radius: 6px;
                padding: 6px;
                background-color: #ffffff;
                color: #3c4043;
                font-size: 10px;
            }
            QComboBox:focus, QLineEdit:focus {
                border: 2px solid #1a73e8;
            }
            QComboBox::drop-down {
                border: none;
                padding-right: 8px;
            }
        """


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    window = HP33120AGeneratorGUI()
    window.show()
    
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
