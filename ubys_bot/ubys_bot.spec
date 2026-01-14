# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['gui.py', 'main.py', 'users.py', 'config.py', 'login.py', 'html1.py', 'telegram.py'],
    pathex=['.'],
    binaries=[],
    datas=[],
    hiddenimports=['main', 'users', 'config', 'login', 'html1', 'telegram', 'bs4', 'requests', 'urllib3', 'charset_normalizer', 'certifi', 'idna', 'soupsieve'],
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
    name='UBYS_Bot',
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
)
