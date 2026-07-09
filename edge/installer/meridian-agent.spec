# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for the Meridian one-click agent (no Docker).
# Built in CI on windows/macos/ubuntu runners (see .github/workflows/connector-installer.yml).
# Produces an onedir bundle: dist/meridian-agent/ — packaged by the per-OS installer.
#
# Run from the REPO ROOT:  pyinstaller edge/installer/meridian-agent.spec
import os
from PyInstaller.utils.hooks import collect_all, collect_submodules

ROOT = os.path.abspath(os.getcwd())

datas, binaries, hiddenimports = [], [], []

# Heavy ML deps need their data files + dynamic libs collected explicitly.
for pkg in ("ultralytics", "supervision", "cv2", "torch", "torchvision"):
    try:
        d, b, h = collect_all(pkg)
        datas += d
        binaries += b
        hiddenimports += h
    except Exception as exc:  # pragma: no cover - visible in CI logs
        print(f"[spec] collect_all({pkg}) skipped: {exc}")

# The reused pipeline package + the agent module (imported as top-level 'local_agent').
hiddenimports += collect_submodules("src.camera")
hiddenimports += ["local_agent"]

# Bundle the model weight so the merchant's box never downloads it at runtime.
_weight = os.path.join(ROOT, "yolo11n.pt")
if os.path.exists(_weight):
    datas += [(_weight, ".")]

# go2rtc config (the binary is dropped into edge/installer/dist_bin/ by CI per-OS).
datas += [(os.path.join(ROOT, "edge", "connector", "go2rtc.yaml"), ".")]
_go2rtc = os.path.join(ROOT, "edge", "installer", "dist_bin",
                       "go2rtc.exe" if os.name == "nt" else "go2rtc")
if os.path.exists(_go2rtc):
    binaries += [(_go2rtc, ".")]

a = Analysis(
    [os.path.join(ROOT, "edge", "installer", "agent_entry.py")],
    pathex=[ROOT, os.path.join(ROOT, "edge", "connector")],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    runtime_hooks=[],
    excludes=["tkinter", "matplotlib.tests", "PIL.ImageQt"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="meridian-agent",
    console=True,          # runs headless as a service; console for log capture
    disable_windowed_traceback=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    name="meridian-agent",
)
