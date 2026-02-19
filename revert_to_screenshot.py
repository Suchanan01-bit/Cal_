
import os
import re

file_path = "E:/Cal-Lab/multimeter_3458_gui.py"

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Define the Legacy Settings Group (Grid Layout)
create_settings_group_code = '''    def create_settings_group(self):
        """Create measurement settings group"""
        group = QGroupBox("⚙️ Measurement Parameters")
        group.setFont(QFont("Segoe UI", 11, QFont.Weight.Bold))
        group.setStyleSheet(self.get_groupbox_style())
        
        layout = QGridLayout()
        layout.setVerticalSpacing(15)
        layout.setHorizontalSpacing(15)
        
        # --- Row 1: Measurement Settings ---
        
        # 0. Number of Measurements
        num_label = QLabel("Number of Measurements:")
        num_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(num_label, 0, 0)

        self.num_measurements_spin = QSpinBox()
        self.num_measurements_spin.setRange(1, 1000000)
        self.num_measurements_spin.setValue(10)
        self.num_measurements_spin.setFont(QFont("Segoe UI", 10))
        self.num_measurements_spin.setStyleSheet(self.get_spinbox_style())
        layout.addWidget(self.num_measurements_spin, 0, 1)

        # 1. Sampling Mode
        mode_label = QLabel("Sampling Mode:")
        mode_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(mode_label, 0, 2)
        
        self.mode_combo = QComboBox()
        self.mode_combo.setFont(QFont("Segoe UI", 10))
        self.mode_combo.setStyleSheet(self.get_input_style())
        self.mode_combo.addItems(["-- Select Mode --", "Integration", "NPLC"]) # Match screenshot "-- Select M..."
        self.mode_combo.currentTextChanged.connect(self.on_mode_changed)
        layout.addWidget(self.mode_combo, 0, 3)
        
        # 2. Integration / NPLC (Combined Slot)
        self.integ_label = QLabel("Integration:") # Swapped dynamically
        self.integ_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(self.integ_label, 0, 4)
        
        # Container for Value + Unit
        time_container = QWidget()
        time_layout = QHBoxLayout(time_container)
        time_layout.setContentsMargins(0,0,0,0)
        time_layout.setSpacing(5)
        
        self.gate_time_spin = QDoubleSpinBox()
        self.gate_time_spin.setMinimum(0.001)
        self.gate_time_spin.setMaximum(1000.0)
        self.gate_time_spin.setValue(1.0)
        self.gate_time_spin.setDecimals(3)
        self.gate_time_spin.setSingleStep(0.1)
        # self.gate_time_spin.setSuffix(" s") # Removed suffix, using combo
        self.gate_time_spin.setFont(QFont("Segoe UI", 10))
        self.gate_time_spin.setStyleSheet(self.get_spinbox_style())
        time_layout.addWidget(self.gate_time_spin)
        
        self.time_unit_combo = QComboBox()
        self.time_unit_combo.setFont(QFont("Segoe UI", 10))
        self.time_unit_combo.setStyleSheet(self.get_input_style())
        self.time_unit_combo.addItems(["seconds", "minutes", "hours"])
        time_layout.addWidget(self.time_unit_combo)
        
        # NPLC Spin (Hidden by default, shares space)
        self.nplc_label = QLabel("NPLC:")
        self.nplc_label.setFont(QFont("Segoe UI", 10))
        self.nplc_label.setVisible(False)
        # We might need to add nplc_label to layout but hide it. 
        # For simplicity in grid, let's just swap visibility of integ_label
        
        self.nplc_spin = QDoubleSpinBox()
        self.nplc_spin.setMinimum(0.001) 
        self.nplc_spin.setMaximum(1000.0) 
        self.nplc_spin.setValue(10.0) 
        # self.nplc_spin.setSuffix(" PLC")
        self.nplc_spin.setDecimals(3)
        self.nplc_spin.setFont(QFont("Segoe UI", 10))
        self.nplc_spin.setStyleSheet(self.get_spinbox_style())
        self.nplc_spin.setVisible(False)
        time_layout.addWidget(self.nplc_spin)
        
        layout.addWidget(time_container, 0, 5)

        # 3. NDIG
        digits_label = QLabel("NDIG:")
        digits_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(digits_label, 0, 6)
        
        self.digit_combo = QComboBox()
        self.digit_combo.setFont(QFont("Segoe UI", 10))
        self.digit_combo.setStyleSheet(self.get_input_style())
        self.digit_combo.addItems(["4", "5", "6", "7", "8"])
        self.digit_combo.setCurrentIndex(4)  # Default to 8 digits
        layout.addWidget(self.digit_combo, 0, 7)
        
        # 4. Offset Comp
        self.offset_comp_check = QCheckBox("Offset Comp")
        self.offset_comp_check.setFont(QFont("Segoe UI", 10))
        self.offset_comp_check.setStyleSheet(self.get_checkbox_style())
        layout.addWidget(self.offset_comp_check, 0, 8)
        
        # 5. Range & Auto-Z
        range_label = QLabel("Range:")
        range_label.setFixedWidth(50)
        range_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(range_label, 0, 9)
        
        self.range_combo = QComboBox()
        self.range_combo.setFont(QFont("Segoe UI", 10))
        self.range_combo.setStyleSheet(self.get_input_style())
        layout.addWidget(self.range_combo, 0, 10)
        
        self.auto_zero_check = QCheckBox("Auto-Z")
        self.auto_zero_check.setFont(QFont("Segoe UI", 10))
        self.auto_zero_check.setChecked(True)
        self.auto_zero_check.setStyleSheet(self.get_checkbox_style())
        layout.addWidget(self.auto_zero_check, 0, 11)

        # --- Row 2: Advanced ---
        
        # AC Band: Label -> Spin -> Checkbox
        acband_label = QLabel("ACBand:")
        acband_label.setFont(QFont("Segoe UI", 10))
        layout.addWidget(acband_label, 1, 0)
        
        ac_container = QWidget()
        ac_layout = QHBoxLayout(ac_container)
        ac_layout.setContentsMargins(0,0,0,0)
        
        self.acband_spin = QSpinBox()
        self.acband_spin.setRange(1, 100000)
        self.acband_spin.setValue(1) 
        self.acband_spin.setSuffix("")
        self.acband_spin.setFont(QFont("Segoe UI", 10))
        self.acband_spin.setStyleSheet(self.get_spinbox_style())
        self.acband_spin.setEnabled(False)
        self.acband_spin.setFixedWidth(80)
        ac_layout.addWidget(self.acband_spin)
        
        self.acband_enable_check = QCheckBox("Enable ACBand")
        self.acband_enable_check.setFont(QFont("Segoe UI", 10))
        self.acband_enable_check.setStyleSheet(self.get_checkbox_style())
        self.acband_enable_check.toggled.connect(self.toggle_acband_input)
        ac_layout.addWidget(self.acband_enable_check)
        
        layout.addWidget(ac_container, 1, 1, 1, 2)
        
        # LFILTER
        self.lfilter_check = QCheckBox("LFilter")
        self.lfilter_check.setFont(QFont("Segoe UI", 10))
        self.lfilter_check.setStyleSheet(self.get_checkbox_style())
        layout.addWidget(self.lfilter_check, 1, 3)
        
        # SETACV
        setacv_container = QWidget()
        setacv_layout = QHBoxLayout(setacv_container)
        setacv_layout.setContentsMargins(0,0,0,0)
        
        setacv_label = QLabel("SetACV:")
        setacv_label.setFont(QFont("Segoe UI", 10))
        setacv_layout.addWidget(setacv_label)
        
        self.setacv_combo = QComboBox()
        self.setacv_combo.addItems(["disable", "sync"]) # Match screenshot
        self.setacv_combo.setFont(QFont("Segoe UI", 10))
        self.setacv_combo.setStyleSheet(self.get_input_style())
        setacv_layout.addWidget(self.setacv_combo)
        
        layout.addWidget(setacv_container, 1, 4, 1, 2)

        # Spacer
        layout.setRowStretch(2, 1)

        group.setLayout(layout)
        return group'''

# 2. Define the Legacy start_measurement Logic
start_measurement_code = '''    def start_measurement(self):
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
        time_unit = "s"

        if self.measurement_mode == "NPLC":
            # NPLC Mode only
            nplc_value = self.nplc_spin.value()
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
        self.results_text.append(f"🔄 Starting measurement..." + r"\n")
        self.results_text.append(f"Type: {measurement_type}")
        self.results_text.append(f"Mode: {self.measurement_mode}")
        
        if self.measurement_mode == "NPLC":
            self.results_text.append(f"NPLC: {nplc_value}")
        else:
            self.results_text.append(f"Integration: {gate_time_value:.2f} {time_unit} ({gate_time_sec:.1f}s)")
        
        self.results_text.append(f"Auto-Zero: {'ON' if auto_zero else 'OFF'}" + r"\n")
        
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
            setacv=setacv
        )
        self.measurement_thread.measurement_ready.connect(self.on_measurement_ready)
        self.measurement_thread.measurement_complete.connect(self.on_measurement_complete)
        self.measurement_thread.error_occurred.connect(self.on_error)
        self.measurement_thread.start()
        
        self.status_bar.showMessage("🔄 Measurement in progress...")'''

# 3. Perform Replacement using RegExp to match function blocks exactly

# Replace create_settings_group
pattern_settings = r"def create_settings_group\(self\):.*?return group"
content = re.sub(pattern_settings, create_settings_group_code, content, flags=re.DOTALL)

# Replace start_measurement
pattern_start = r"def start_measurement\(self\):.*?self.status_bar.showMessage\(\"🔄 Measurement in progress\.\.\.\"\)"
content = re.sub(pattern_start, start_measurement_code, content, flags=re.DOTALL)

# 4. Correct on_mode_changed logic (Use string replacement as it's scattered)
# We need to make sure on_mode_changed interacts with the new widgets correctly
# The existing code probably references nplc_label and integ_label, which we added back.
# But it might be swapping visibility of gate_time_spin. We now wrap them in layouts/containers in some cases,
# but calling setVisible on the widget itself typically works even if in layout.

# However, we need to ensure self.nplc_label and self.integ_label are properly defined in the new create_settings_group code.
# (They are defined in the code string above: `self.integ_label = QLabel("Integration:")`)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("File updated to Legacy Fit-Screen version successfully.")
