# Meridian Vision Agent — native one-click installer (no Docker)

For merchants who don't run Docker. Freezes the local processing agent (YOLO on
CPU) + bundled go2rtc into a native install that runs as a boot service on their
own PC/POS, taps their existing ONVIF cameras, and posts anonymous counts.

Same engine as the Docker connector — this is just a Docker-free delivery.

## Merchant experience

| OS | Artifact | Steps |
|----|----------|-------|
| **Windows** | `meridian-agent-setup.exe` | Double-click → paste pairing code → Finish. Runs as a boot Scheduled Task. |
| **macOS** | `meridian-agent-macOS.tar.gz` | Unpack → `sudo ./install-unix.sh <code>`. Runs as a launchd daemon. |
| **Linux** | `meridian-agent-Linux.tar.gz` | Unpack → `sudo ./install-unix.sh <code>`. Runs as a systemd service. |

The pairing code comes from the portal → **Connect cameras** wizard (15-min TTL);
the agent then holds only its per-org device token.

## How it's built

`.github/workflows/connector-installer.yml` builds on `windows`, `macos`, and
`ubuntu` runners (tag `agent-v*` or manual dispatch):

1. `pip install pyinstaller` + CPU-only torch + `edge/connector/requirements.txt`.
2. Fetch YOLO weights + the go2rtc binary for the OS.
3. `pyinstaller edge/installer/meridian-agent.spec` → `dist/meridian-agent/` (bundle).
4. Package: Windows → Inno Setup `.exe`; macOS/Linux → tarball + `install-unix.sh`.
5. **Conditional code-signing** (unsigned if secrets absent).

## Code-signing secrets (optional but recommended)

Set these repo secrets to get signed/notarized artifacts:

| Secret | Purpose |
|--------|---------|
| `WINDOWS_CERT_BASE64` / `WINDOWS_CERT_PASSWORD` | Authenticode `.pfx` (base64) for `signtool` |
| `APPLE_CERT_BASE64` / `APPLE_CERT_PASSWORD` | Developer ID Application cert (base64 `.p12`) |
| `APPLE_TEAM_ID` / `APPLE_NOTARY_USER` / `APPLE_NOTARY_PASSWORD` | notarization (`notarytool`) |

Without them the workflow still produces working (unsigned) installers — Windows
SmartScreen / macOS Gatekeeper will warn on first run until certs are added.

## ⚠️ Needs a validation run on real runners

PyInstaller + torch/ultralytics bundling is fragile and can't be validated on this
Linux box. First CI run may need spec tweaks (hidden imports / data files) and a
go2rtc asset-name/version bump (`GO2RTC_VERSION`). The Docker connector image
(`local_agent.Dockerfile`) is the already-verified path; this native installer is
the Docker-free alternative pending that first green CI build + a hardware smoke test.

## Files

- `agent_entry.py` — frozen entrypoint: load config → start go2rtc → run the agent
- `meridian-agent.spec` — PyInstaller onedir bundle (pipeline + weights + go2rtc)
- `install-unix.sh` — Linux/macOS one-command installer (systemd / launchd)
- `linux/meridian-agent.service`, `macos/com.meridian.agent.plist` — service units
- `windows/meridian-agent.iss` — Inno Setup installer (pairing-code prompt + task)
