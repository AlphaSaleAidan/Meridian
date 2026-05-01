#!/usr/bin/env bash
# Meridian Vision Edge — Setup Script
# For: NVIDIA Jetson (Nano/Orin), Raspberry Pi 5, x86 Linux
#
# Usage:
#   curl -fsSL https://get.meridianpos.ai/edge | bash
#   -- or --
#   chmod +x setup.sh && ./setup.sh

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PYTHON_MIN="3.11"
LOG_FILE="/tmp/meridian-edge-setup.log"

info()  { echo -e "\033[0;36m[meridian]\033[0m $*"; }
warn()  { echo -e "\033[0;33m[meridian]\033[0m $*"; }
error() { echo -e "\033[0;31m[meridian]\033[0m $*" >&2; }
ok()    { echo -e "\033[0;32m[meridian]\033[0m $*"; }

# ── Detect platform ──────────────────────────────────────────

detect_platform() {
    if [ -f /etc/nv_tegra_release ]; then
        PLATFORM="jetson"
        JETPACK=$(head -1 /etc/nv_tegra_release | grep -oP 'R\K[0-9]+' || echo "unknown")
        info "Detected: NVIDIA Jetson (JetPack R${JETPACK})"
    elif grep -q "Raspberry Pi" /proc/cpuinfo 2>/dev/null; then
        PLATFORM="rpi"
        info "Detected: Raspberry Pi"
    else
        PLATFORM="x86"
        info "Detected: x86 Linux"
    fi
}

# ── Check Python ─────────────────────────────────────────────

check_python() {
    if command -v python3.11 &>/dev/null; then
        PYTHON="python3.11"
    elif command -v python3 &>/dev/null; then
        local ver
        ver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
        if python3 -c "import sys; exit(0 if sys.version_info >= (3,11) else 1)"; then
            PYTHON="python3"
        else
            error "Python >= ${PYTHON_MIN} required (found ${ver})"
            info "Install: sudo apt install python3.11 python3.11-venv"
            exit 1
        fi
    else
        error "Python not found"
        info "Install: sudo apt install python3.11 python3.11-venv"
        exit 1
    fi
    ok "Python: $($PYTHON --version)"
}

# ── Create virtual environment ───────────────────────────────

setup_venv() {
    local venv_dir="${SCRIPT_DIR}/venv"
    if [ -d "$venv_dir" ]; then
        info "Virtual environment exists at ${venv_dir}"
    else
        info "Creating virtual environment..."
        $PYTHON -m venv "$venv_dir"
        ok "Virtual environment created"
    fi
    source "${venv_dir}/bin/activate"
    pip install --upgrade pip setuptools wheel >> "$LOG_FILE" 2>&1
}

# ── Install dependencies ─────────────────────────────────────

install_deps() {
    info "Installing edge dependencies..."

    pip install \
        "httpx>=0.27.0" \
        "numpy>=1.26" \
        "opencv-python-headless>=4.9.0" \
        "pyyaml>=6.0" \
        >> "$LOG_FILE" 2>&1

    info "Installing ML packages (this may take a few minutes)..."

    pip install "ultralytics>=8.2.0" >> "$LOG_FILE" 2>&1
    ok "  ultralytics (YOLO v8)"

    pip install "boxmot>=10.0.0" >> "$LOG_FILE" 2>&1
    ok "  boxmot (DeepOCSORT tracker)"

    pip install "insightface>=0.7.3" >> "$LOG_FILE" 2>&1
    ok "  insightface (ArcFace embeddings)"

    pip install "deepface>=0.0.89" >> "$LOG_FILE" 2>&1
    ok "  deepface (demographics)"

    pip install "supervision>=0.21.0" >> "$LOG_FILE" 2>&1
    ok "  supervision (zone analytics)"

    # Platform-specific GPU support
    if [ "$PLATFORM" = "jetson" ]; then
        info "Installing Jetson-specific ONNX runtime..."
        pip install onnxruntime-gpu >> "$LOG_FILE" 2>&1 || warn "onnxruntime-gpu install skipped"
    elif command -v nvidia-smi &>/dev/null; then
        info "NVIDIA GPU detected, installing CUDA support..."
        pip install onnxruntime-gpu >> "$LOG_FILE" 2>&1 || warn "onnxruntime-gpu install skipped"
    else
        pip install onnxruntime >> "$LOG_FILE" 2>&1
    fi

    ok "All dependencies installed"
}

# ── Download models ──────────────────────────────────────────

download_models() {
    local model_dir="${SCRIPT_DIR}/models"
    mkdir -p "$model_dir"

    info "Downloading YOLO v8 nano model..."
    $PYTHON -c "
from ultralytics import YOLO
model = YOLO('yolov8n.pt')
print('YOLO model ready')
" >> "$LOG_FILE" 2>&1
    ok "  yolov8n.pt downloaded"

    info "Preparing InsightFace buffalo_l model..."
    $PYTHON -c "
import insightface
app = insightface.app.FaceAnalysis(name='buffalo_l', providers=['CPUExecutionProvider'])
app.prepare(ctx_id=0, det_size=(640, 640))
print('InsightFace model ready')
" >> "$LOG_FILE" 2>&1
    ok "  buffalo_l model ready"
}

# ── Create config if missing ─────────────────────────────────

setup_config() {
    local config_file="${SCRIPT_DIR}/config.yaml"
    if [ -f "$config_file" ]; then
        info "Config exists at ${config_file}"
        return
    fi

    if [ -f "${SCRIPT_DIR}/config.example.yaml" ]; then
        cp "${SCRIPT_DIR}/config.example.yaml" "$config_file"
        warn "Config created from example — edit ${config_file} before running"
    else
        error "No config.example.yaml found"
    fi
}

# ── Create systemd service ───────────────────────────────────

install_service() {
    if [ "$(id -u)" -ne 0 ]; then
        warn "Skipping systemd service (run as root to install)"
        return
    fi

    cat > /etc/systemd/system/meridian-edge.service << UNIT
[Unit]
Description=Meridian Vision Edge Agent
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
WorkingDirectory=${SCRIPT_DIR}
ExecStart=${SCRIPT_DIR}/venv/bin/python ${SCRIPT_DIR}/run_pipeline.py
Restart=always
RestartSec=10
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
UNIT

    systemctl daemon-reload
    ok "Systemd service installed: meridian-edge"
    info "  Start: sudo systemctl start meridian-edge"
    info "  Enable: sudo systemctl enable meridian-edge"
}

# ── Main ─────────────────────────────────────────────────────

main() {
    echo ""
    info "═══════════════════════════════════════════"
    info " Meridian Vision Edge — Setup"
    info "═══════════════════════════════════════════"
    echo ""

    detect_platform
    check_python
    setup_venv
    install_deps
    download_models
    setup_config
    install_service

    echo ""
    ok "═══════════════════════════════════════════"
    ok " Setup complete!"
    ok "═══════════════════════════════════════════"
    echo ""
    info "Next steps:"
    info "  1. Edit config.yaml with your store_id and API key"
    info "  2. Add camera RTSP URLs"
    info "  3. Run: source venv/bin/activate && python run_pipeline.py"
    echo ""
}

main "$@"
