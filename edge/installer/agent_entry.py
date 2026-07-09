#!/usr/bin/env python3
"""Frozen entrypoint for the Meridian one-click installer (no Docker).

PyInstaller bundles this + the vision pipeline + a go2rtc binary into a single
native executable per OS. Installed as a background service (Windows Service /
macOS launchd / Linux systemd) that starts on boot. It:

  1. Loads config (pairing code + API) from env or an agent.conf the installer wrote.
  2. Starts the bundled go2rtc (ONVIF discovery + local frame API).
  3. Runs the local processing agent (YOLO on CPU -> POST anonymous counts).

Config file (KEY=VALUE lines), searched in order:
  $MERIDIAN_AGENT_CONF
  <exe dir>/agent.conf
  Windows: %PROGRAMDATA%\\Meridian\\agent.conf
  macOS/Linux: /etc/meridian/agent.conf, /usr/local/etc/meridian/agent.conf
"""
from __future__ import annotations

import logging
import os
import pathlib
import shutil
import subprocess
import sys

logging.basicConfig(level=logging.INFO, format="%(asctime)s meridian-agent %(levelname)s %(message)s")
log = logging.getLogger("meridian-agent")


def _bundle_dir() -> pathlib.Path:
    """Directory holding bundled assets (go2rtc, go2rtc.yaml). Handles PyInstaller."""
    if getattr(sys, "frozen", False):
        return pathlib.Path(getattr(sys, "_MEIPASS", pathlib.Path(sys.executable).parent))
    return pathlib.Path(__file__).resolve().parent


def _config_candidates() -> list[pathlib.Path]:
    cands: list[pathlib.Path] = []
    if os.environ.get("MERIDIAN_AGENT_CONF"):
        cands.append(pathlib.Path(os.environ["MERIDIAN_AGENT_CONF"]))
    cands.append(pathlib.Path(sys.executable).resolve().parent / "agent.conf")
    if os.name == "nt":
        pd = os.environ.get("PROGRAMDATA", r"C:\ProgramData")
        cands.append(pathlib.Path(pd) / "Meridian" / "agent.conf")
    else:
        cands.append(pathlib.Path("/etc/meridian/agent.conf"))
        cands.append(pathlib.Path("/usr/local/etc/meridian/agent.conf"))
    return cands


def _load_conf() -> None:
    """Populate os.environ from the first agent.conf found (env values win)."""
    for path in _config_candidates():
        try:
            if not path.is_file():
                continue
            for line in path.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                key, val = line.split("=", 1)
                os.environ.setdefault(key.strip(), val.strip())
            log.info("loaded config from %s", path)
            return
        except Exception as e:  # noqa: BLE001
            log.debug("config read %s failed: %s", path, e)


def _start_go2rtc(bundle: pathlib.Path):
    """Start the bundled go2rtc (ONVIF discovery + local frame API). Optional:
    if it's missing, the agent still runs against any manually-configured RTSP."""
    exe_name = "go2rtc.exe" if os.name == "nt" else "go2rtc"
    exe = bundle / exe_name
    cfg = bundle / "go2rtc.yaml"
    if not exe.exists():
        found = shutil.which("go2rtc")
        if not found:
            log.warning("go2rtc not bundled and not on PATH — ONVIF discovery disabled")
            return None
        exe = pathlib.Path(found)
    args = [str(exe)]
    if cfg.exists():
        args += ["-config", str(cfg)]
    try:
        log.info("starting go2rtc: %s", " ".join(args))
        return subprocess.Popen(args)
    except Exception as e:  # noqa: BLE001
        log.warning("could not start go2rtc: %s", e)
        return None


def main() -> int:
    _load_conf()
    if not os.environ.get("MERIDIAN_PAIRING_CODE") and not os.environ.get("MERIDIAN_DEVICE_TOKEN"):
        log.error(
            "No pairing code configured. Set MERIDIAN_PAIRING_CODE in agent.conf "
            "(from the portal 'Connect cameras' wizard)."
        )
        return 2

    bundle = _bundle_dir()
    go2rtc = _start_go2rtc(bundle)
    try:
        # Import the agent lazily so config/env is set first. Works frozen
        # (bundled as a top-level module) and from source (edge.connector).
        try:
            import local_agent  # type: ignore
        except ImportError:
            from edge.connector import local_agent  # type: ignore
        return local_agent.main()
    finally:
        if go2rtc is not None:
            go2rtc.terminate()


if __name__ == "__main__":
    raise SystemExit(main())
