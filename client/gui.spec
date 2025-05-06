# -*- mode: python ; coding: utf-8 -*-

import os
import sys
from PyInstaller.utils.hooks import get_package_paths, collect_all

block_cipher = None

# 获取SimConnect包的路径
simconnect_pkg = get_package_paths('SimConnect')
simconnect_dll = os.path.join(simconnect_pkg[1], 'SimConnect.dll')

# 收集PyQt6依赖
qt_binaries, qt_datas, qt_hiddenimports = collect_all('PyQt6')

a = Analysis(
    ['gui.py'],  # 更改为gui.py
    pathex=[],
    binaries=[
        (simconnect_dll, 'SimConnect')
    ] + qt_binaries,
    datas=[
        ('radio.py', '.'),  # 添加radio.py作为数据文件
    ] + qt_datas,
    hiddenimports=[
        'pkg_resources',
        'pkgutil',
        'google.protobuf',
        'SimConnect',
        'keyboard',
        'pymumble_py3',
        'PyQt6.sip',
    ] + qt_hiddenimports,
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
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='radio_gui',  # 更改可执行文件名称
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,  # 设置为False以禁用控制台窗口
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=['favicon.ico'],
)