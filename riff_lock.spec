# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, copy_metadata


def _safe_collect_data(package_name):
    try:
        return collect_data_files(package_name)
    except Exception:
        return []


def _safe_copy_metadata(package_name):
    try:
        return copy_metadata(package_name)
    except Exception:
        return []


def _safe_collect_submodules(package_name):
    try:
        return collect_submodules(package_name)
    except Exception:
        return []


datas = []
datas += _safe_collect_data("customtkinter")
datas += _safe_collect_data("librosa")
datas += _safe_copy_metadata("librosa")

hiddenimports = []
hiddenimports += _safe_collect_submodules("customtkinter")
hiddenimports += _safe_collect_submodules("librosa")
hiddenimports += _safe_collect_submodules("sounddevice")
hiddenimports += _safe_collect_submodules("aubio")
hiddenimports += _safe_collect_submodules("argon2")
hiddenimports += _safe_collect_submodules("cryptography")


a = Analysis(
    ["main.py"],
    pathex=[],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="RiffLock",
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
