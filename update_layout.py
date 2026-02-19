
import os

file_path = "E:/Cal-Lab/multimeter_3458_gui.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
skip = False
inserted = False

method_code = '''    def create_settings_group(self):
        """Create measurement settings group"""
        group = QGroupBox("⚙️ Measurement Parameters")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        # Main Vertical Layout
        layout = QVBoxLayout()
        layout.setSpacing(15)
        
        # --- Row 1: Basic Settings (Range, Digits, AZERO, OCOMP) ---
        row1_layout = QHBoxLayout()
        row1_layout.setSpacing(20)
        
        # Range
        range_label = QLabel("Range:")
        range_label.setFont(QFont("Segoe UI", 10))
        self.range_combo = QComboBox()
        self.range_combo.setFont(QFont("Segoe UI", 10))
        self.range_combo.setStyleSheet(self.get_input_style())
        # Default items will be populated by on_type_changed
        
        row1_layout.addWidget(range_label)
        row1_layout.addWidget(self.range_combo)

        # Digits (NDIG)
        digits_label = QLabel("NDIG:")
        digits_label.setFont(QFont("Segoe UI", 10))
        self.digit_combo = QComboBox()
        self.digit_combo.setFont(QFont("Segoe UI", 10))
        self.digit_combo.setStyleSheet(self.get_input_style())
        self.digit_combo.addItems(["4", "5", "6", "7", "8"])
        self.digit_combo.setCurrentIndex(4)  # Default to 8 digits
        
        row1_layout.addWidget(digits_label)
        row1_layout.addWidget(self.digit_combo)
        
        # Auto Zero
        self.auto_zero_check = QCheckBox("AZERO")
        self.auto_zero_check.setFont(QFont("Segoe UI", 10))
        self.auto_zero_check.setChecked(True)
        self.auto_zero_check.setStyleSheet(self.get_checkbox_style())
        
        row1_layout.addWidget(self.auto_zero_check)
        
        # Offset Comp
        self.offset_comp_check = QCheckBox("OCOMP")
        self.offset_comp_check.setFont(QFont("Segoe UI", 10))
        self.offset_comp_check.setStyleSheet(self.get_checkbox_style())
        row1_layout.addWidget(self.offset_comp_check)
        
        row1_layout.addStretch() # Push everything to left
        layout.addLayout(row1_layout)

        # --- Row 2: Sampling Configuration ---
        row2_layout = QHBoxLayout()
        row2_layout.setSpacing(20)
        
        # Mode selector
        mode_label = QLabel("Sampling:")
        mode_label.setFont(QFont("Segoe UI", 10))
        row2_layout.addWidget(mode_label)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setFont(QFont("Segoe UI", 10))
        self.mode_combo.setStyleSheet(self.get_input_style())
        self.mode_combo.addItems(["Integration", "NPLC"])
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        
        row2_layout.addWidget(self.mode_combo)

        # Time/NPLC Value Input     
        self.gate_time_spin = QDoubleSpinBox()
        self.gate_time_spin.setMinimum(0.001)
        self.gate_time_spin.setMaximum(1000.0)
        self.gate_time_spin.setValue(1.0)
        self.gate_time_spin.setDecimals(3)
        self.gate_time_spin.setSingleStep(0.1)
        self.gate_time_spin.setSuffix(" s") # Default suffix
        self.gate_time_spin.setFont(QFont("Segoe UI", 10))
        self.gate_time_spin.setStyleSheet(self.get_spinbox_style())
        self.gate_time_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        
        row2_layout.addWidget(self.gate_time_spin)
        
        # NPLC spinbox (initially hidden)
        self.nplc_spin = QDoubleSpinBox()
        self.nplc_spin.setMinimum(0.001) 
        self.nplc_spin.setMaximum(1000.0) 
        self.nplc_spin.setValue(10.0) 
        self.nplc_spin.setSuffix(" PLC")
        self.nplc_spin.setDecimals(3)
        self.nplc_spin.setFont(QFont("Segoe UI", 10))
        self.nplc_spin.setStyleSheet(self.get_spinbox_style())
        self.nplc_spin.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))
        self.nplc_spin.setVisible(False)
        
        row2_layout.addWidget(self.nplc_spin)

        # Number of measurements
        num_label = QLabel("Readings:")
        num_label.setFont(QFont("Segoe UI", 10))
        row2_layout.addWidget(num_label)

        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setRange(1, 1000000)
        self.num_measurements_spin.setValue(5)
        self.num_measurements_spin.setFont(QFont("Segoe UI", 10))
        self.num_measurements_spin.setStyleSheet(self.get_spinbox_style())
        row2_layout.addWidget(self.num_measurements_spin)
        
        row2_layout.addStretch()
        layout.addLayout(row2_layout)

        # --- Row 3: Advanced AC Settings ---
        row3_layout = QHBoxLayout()
        row3_layout.setSpacing(20)
        
        # AC Bandwidth
        self.acband_enable_check = QCheckBox("AC Band")
        self.acband_enable_check.setFont(QFont("Segoe UI", 10))
        self.acband_enable_check.setStyleSheet(self.get_checkbox_style())
        self.acband_enable_check.toggled.connect(self.toggle_acband_input)
        row3_layout.addWidget(self.acband_enable_check)
        
        self.acband_spin = QSpinBox()
        self.acband_spin.setRange(1, 100000)
        self.acband_spin.setValue(20) 
        self.acband_spin.setSuffix(" Hz")
        self.acband_spin.setFont(QFont("Segoe UI", 10))
        self.acband_spin.setStyleSheet(self.get_spinbox_style())
        self.acband_spin.setEnabled(False)
        row3_layout.addWidget(self.acband_spin)

        # LFILTER (AC)
        self.lfilter_check = QCheckBox("LFILTER")
        self.lfilter_check.setToolTip("Enhance accuracy for low frequency AC signals")
        self.lfilter_check.setFont(QFont("Segoe UI", 10))
        self.lfilter_check.setStyleSheet(self.get_checkbox_style())
        row3_layout.addWidget(self.lfilter_check)

        setacv_label = QLabel("SETACV:")
        setacv_label.setFont(QFont("Segoe UI", 10))
        row3_layout.addWidget(setacv_label)
        
        self.setacv_combo = QComboBox()
        self.setacv_combo.addItems(["ACAL", "SYNC"])
        self.setacv_combo.setFont(QFont("Segoe UI", 10))
        self.setacv_combo.setStyleSheet(self.get_input_style())
        self.setacv_combo.setToolTip("SETACV SYNC improves accuracy for synchronous AC signals")
        row3_layout.addWidget(self.setacv_combo, 2, 4, 1, 2) # Span 2 columns
        
        layout.setRowStretch(3, 1)

        group.setLayout(layout)
        return group
'''

for line in lines:
    if "def create_settings_group(self):" in line:
        skip = True
        new_lines.append(method_code + "\n")
        inserted = True
    elif "def create_control_buttons(self):" in line:
        skip = False
    
    if not skip:
        # Also fix main behavior if present (just in case)
        if "window.showMaximized()" in line:
            new_lines.append(line.replace("window.showMaximized()", "window.show()"))
        else:
            new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("File updated successfully.")
