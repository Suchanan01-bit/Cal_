# -*- mode: python ; coding: utf-8 -*-
"""
PyInstaller spec file for Measurement Tools Hub
Bundles the React DC-RF Simulator dist/ into the executable
"""

import os

block_cipher = None

# Project root (where this spec file lives)
project_root = os.path.abspath('.')

a = Analysis(
    [os.path.join('CalLab', 'measurement_tools_hub.py')],
    pathex=[project_root],
    binaries=[],
    datas=[
        # Bundle the React simulator build output
        (os.path.join('reference', 'dc-rfsimulator', 'dist'),
         os.path.join('reference', 'dc-rfsimulator', 'dist')),
    ],
    hiddenimports=[
        'PyQt6.QtWebEngineWidgets',
        'PyQt6.QtWebEngineCore',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='MeasurementToolsHub',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,  # No console window (GUI app)
    icon=None,      # Add .ico path here if you have one
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='MeasurementToolsHub',
)
