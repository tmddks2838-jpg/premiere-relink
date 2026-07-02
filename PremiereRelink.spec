# -*- mode: python ; coding: utf-8 -*-
import os

FFPROBE = os.path.expanduser("~/.local/bin/ffprobe")

a = Analysis(
    ["app_web.py"],
    pathex=["."],
    binaries=[(FFPROBE, ".")] if os.path.isfile(FFPROBE) else [],
    datas=[("templates", "templates")],
    hiddenimports=[
        "engine",
        "engine.pipeline",
        "engine.models",
        "engine.reader",
        "engine.detector",
        "engine.indexer",
        "engine.matcher",
        "engine.writer",
        "flask",
    ],
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
    [],
    exclude_binaries=True,
    name="Premiere Relink",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,      # 터미널 창 숨김
    disable_windowed_traceback=False,
    argv_emulation=True,
    target_arch="universal2",   # Intel + Apple Silicon 모두 지원
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="Premiere Relink",
)

app = BUNDLE(
    coll,
    name="Premiere Relink.app",
    icon=None,
    bundle_identifier="com.premiererlink.app",
    info_plist={
        "NSHighResolutionCapable": True,
        "CFBundleShortVersionString": "1.0.0",
        "LSMinimumSystemVersion": "12.0",
    },
)
