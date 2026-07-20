# -*- mode: python ; coding: utf-8 -*-

a = Analysis(
    ['main.py'],
    pathex=[],
    binaries=[],
    datas=[
        ('data/*.json', 'data'),
        ('data/car_thumbnails', 'data/car_thumbnails'),
        ('ui/styles/*.qss', 'ui/styles'),
        ('math_channels.json', '.'),
        ('app_icon.png', '.'),
        ('app_icon.icns', '.'),
        ('app_icon.ico', '.')
    ],
    hiddenimports=[
        'pyqtgraph', 'numpy', 'PyQt6'
    ],
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
    [],
    exclude_binaries=True,
    name='GT7TelemetryPro',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon='app_icon.ico',
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='GT7TelemetryPro',
)
app = BUNDLE(
    coll,
    name='GT7TelemetryPro.app',
    icon='app_icon.icns',
    bundle_identifier='com.rgdev.gt7telemetrypro',
)
