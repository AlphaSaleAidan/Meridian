# Meridian GPU voice box — Windows setup for the office RTX 3080 machine.
# Run in an elevated PowerShell:  powershell -ExecutionPolicy Bypass -File .\gpu_voice_box_setup.ps1
#
# Stands up two OpenAI-compatible model servers in Docker (WSL2 GPU backend):
#   STT  :8790  NVIDIA Parakeet TDT 0.6B (whisper-compatible API, ~3GB VRAM)
#   TTS  :4123  Chatterbox (OpenAI /v1/audio/speech, ~3-4GB VRAM)
# and connects the box to the VPS over Tailscale (no ports opened to the internet).

function Say($m) { Write-Host "`n== $m ==" -ForegroundColor Cyan }
function Need($cmd, $hint) {
  if (-not (Get-Command $cmd -ErrorAction SilentlyContinue)) { Write-Host "MISSING: $cmd — $hint" -ForegroundColor Yellow; return $false }
  return $true
}

Say "checks"
$ok = $true
if (-not (Need nvidia-smi "install the NVIDIA Game Ready/Studio driver (includes WSL CUDA)")) { $ok = $false } else { nvidia-smi --query-gpu=name,memory.total --format=csv,noheader }
if (-not (Need wsl "run:  wsl --install   (then reboot)")) { $ok = $false }
if (-not (Need docker "install Docker Desktop:  winget install Docker.DockerDesktop  — enable 'Use WSL 2 based engine' + GPU in Settings>Resources")) { $ok = $false }
if (-not (Need git "winget install Git.Git")) { $ok = $false }
if (-not $ok) { Write-Host "`nInstall the missing pieces above, reboot if WSL was just installed, re-run this script." -ForegroundColor Red; exit 1 }

# GPU visible to docker?
docker run --rm --gpus all nvidia/cuda:12.4.1-base-ubuntu22.04 nvidia-smi 2>$null | Out-Null
if ($LASTEXITCODE -ne 0) { Write-Host "Docker can't see the GPU — Docker Desktop > Settings > Resources > WSL integration + ensure WSL2 engine; update Docker Desktop." -ForegroundColor Red; exit 1 }
Write-Host "docker GPU passthrough OK" -ForegroundColor Green

$work = "$HOME\meridian-voice-box"
New-Item -ItemType Directory -Force -Path $work | Out-Null
Set-Location $work

Say "STT — Parakeet (whisper-compatible server on :8790)"
if (-not (Test-Path parakeet)) { git clone --depth 1 https://github.com/achetronic/parakeet.git }
Push-Location parakeet
docker compose up -d 2>$null
if ($LASTEXITCODE -ne 0) { Write-Host "NOTE: check parakeet\README.md for its current run command; expose port 8790" -ForegroundColor Yellow }
Pop-Location

Say "TTS — Chatterbox (OpenAI-compatible on :4123)"
if (-not (Test-Path chatterbox-tts-api)) { git clone --depth 1 https://github.com/travisvn/chatterbox-tts-api.git }
Push-Location chatterbox-tts-api
if ((Test-Path .env.example.docker) -and -not (Test-Path .env)) { Copy-Item .env.example.docker .env }
docker compose -f docker/docker-compose.gpu.yml up -d 2>$null
if ($LASTEXITCODE -ne 0) { docker compose up -d }
Pop-Location

Say "smoke test (first run downloads models — can take a few minutes)"
Start-Sleep -Seconds 30
try {
  Invoke-RestMethod -Method Post -Uri http://127.0.0.1:4123/v1/audio/speech `
    -ContentType 'application/json' `
    -Body '{"model":"tts-1","voice":"alloy","input":"Thanks for calling, what can I get started for you?"}' `
    -OutFile "$work\tts-test.wav"
  Write-Host "TTS OK → $work\tts-test.wav — PLAY THIS, it's the voice callers will hear" -ForegroundColor Green
} catch { Write-Host "TTS not up yet — try again in a few min:  docker logs chatterbox-tts-api" -ForegroundColor Yellow }

Say "network — Tailscale"
if (-not (Get-Command tailscale -ErrorAction SilentlyContinue)) { winget install tailscale.tailscale; Write-Host "Sign in when the Tailscale window opens." }
# Allow the VPS (tailnet 100.x range) to reach the two model ports
New-NetFirewallRule -DisplayName "Meridian voice box (tailscale)" -Direction Inbound -Action Allow `
  -Protocol TCP -LocalPort 8790,4123 -RemoteAddress 100.64.0.0/10 -ErrorAction SilentlyContinue | Out-Null
$ip = (tailscale ip -4 2>$null | Select-Object -First 1)
Write-Host "This box's tailscale IP: $ip"

Say "done — next steps"
Write-Host @"
1. On the VPS:  curl -fsSL https://tailscale.com/install.sh | sh && tailscale up   (same Tailscale account)
2. Add to /root/meridian-voice-sidecar/services/phone_agent/.env:
     GPU_STT_BASE_URL=http://$ip`:8790/v1
     GPU_TTS_BASE_URL=http://$ip`:4123/v1
3. pm2 restart meridian-voice-sidecar — the test line then rotates premium/gpu/nemotron per call.
"@
