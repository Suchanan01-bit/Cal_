# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['measurement_tools_hub.py'],
    pathex=[],
    binaries=[],
    datas=[('multimeter_34401_gui.py', '.'), ('multimeter_34465_gui.py', '.'), ('multimeter_3458_3d_gui.py', '.'), ('multimeter_3458_gui.py', '.'), ('multimeter_8846.py', '.'), ('reference_multimeter_8508_II_gui.py', '.'), ('reference_multimeter_8508_gui.py', '.'), ('rs_power_meter_gui.py', '.'), ('spectrum_n1996a_gui.py', '.'), ('universal_counter_gui.py', '.'), ('waveform_33120a_gui.py', '.')],
    hiddenimports=['PyQt6', 'PyQt6.QtWidgets', 'PyQt6.QtCore', 'PyQt6.QtGui', 'PyQt6.QtWebEngineWidgets', 'pyvisa', 'matplotlib', 'serial', 'serial.tools.list_ports', 'fluke1620_reader'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='MeasurementToolsHub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['C:\\Users\\Admins\\Documents\\Github\\Cal_\\CalLab\\assets\\icon\\ico.ico.ico'],
)
