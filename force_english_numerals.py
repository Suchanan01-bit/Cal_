
import os

file_path = "E:/Cal-Lab/multimeter_3458_gui.py"

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
locale_line = '        self.{}.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))\n'

widgets_to_fix = [
    "num_measurements_spin",
    "gate_time_spin",
    "nplc_spin",
    "acband_spin"
]

for line in lines:
    new_lines.append(line)
    
    # Check for widget definitions and inject locale immediately after
    for widget in widgets_to_fix:
        if f"self.{widget} = " in line and "QSpinBox" in line: # Matches QSpinBox and QDoubleSpinBox
            # Calculate indentation
            indent = line[:len(line) - len(line.lstrip())]
            new_lines.append(indent + f"self.{widget}.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))\n")

    # Special case for progress bar which is in init_ui
    if "self.progress_bar = QProgressBar()" in line:
        indent = line[:len(line) - len(line.lstrip())]
        new_lines.append(indent + "self.progress_bar.setLocale(QLocale(QLocale.Language.English, QLocale.Country.UnitedStates))\n")

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Applied English locale to numeric widgets successfully.")
