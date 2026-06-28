# Evidence — CC6.7-ENCRYPTION

**v0.1 — 2026-06-28.** Control: register `CC6.7-ENCRYPTION`. Policy: `/policies/encryption-cryptography.md`.

## Type I evidence (real)
| Control | Location | Notes |
|---|---|---|
| POS OAuth tokens encrypted at rest | `src/security/encryption.py` | **AES-256-GCM**, random 12-byte nonce/op, `v1:` versioned for rotation, fail-closed if `ENCRYPTION_KEY` unset |
| TLS in transit | Railway auto-TLS + Cloudflare | platform-managed |
| HSTS | `src/api/middleware/security_headers.py:13` | `max-age=31536000; includeSubDomains; preload` |
| DB at rest | Supabase managed | AES-256 (AWS RDS) |
| Live-view video | `src/services/cloudflare_stream.py` | WHIP/WHEP over Cloudflare TLS; video never transits Meridian infra |
| Secret scanning | `.gitleaks.toml`, `.github/workflows/gitleaks.yml`, `.pre-commit-config.yaml` | blocking in CI; `.env` gitignored; no committed secrets |

## Corrections / gaps
- **Doc error:** `docs/MERIDIAN_COMPLIANCE_POSTURE.md:279` says "Fernet (AES-128-CBC)" — **wrong**; real impl is
  AES-256-GCM. Correct the posture doc before it reaches an auditor.
- **RTSP edge** streams (camera→edge) unencrypted on merchant LAN — DECISION: RTSPS/VPN (`threat-model-camera.md` V5).
- **CSP** allows `unsafe-inline`/`unsafe-eval` (`security_headers.py`) — weakens XSS posture.
- **Key rotation** procedure undocumented (the `v1:` scheme supports it) — documented in the policy now.
- **Contabo file-secrets** (`/root/.secrets/*.env`) ungoverned (R-15).

## Status 🟢 design strong (at-rest + transit); 🟡 RTSP + CSP + key-rotation doc are follow-ups.
