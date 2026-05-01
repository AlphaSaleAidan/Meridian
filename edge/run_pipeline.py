"""
Meridian Vision Edge — Pipeline Runner.

Loads config, initializes cameras, runs the full vision pipeline
(detect → track → recognize → demographics → zones → batch upload).

Usage:
    python run_pipeline.py
    python run_pipeline.py --config /path/to/config.yaml
"""
import asyncio
import argparse
import logging
import signal
import sys
from pathlib import Path

logger = logging.getLogger("meridian.edge")

CONFIG_PATHS = [
    Path("config.yaml"),
    Path("config/config.yaml"),
    Path("/etc/meridian/config.yaml"),
]


def load_config(path: str | None = None) -> dict:
    try:
        import yaml
    except ImportError:
        logger.error("pyyaml not installed — run: pip install pyyaml")
        sys.exit(1)

    if path:
        config_path = Path(path)
    else:
        config_path = next((p for p in CONFIG_PATHS if p.exists()), None)

    if not config_path or not config_path.exists():
        logger.error(
            "Config not found. Searched: %s",
            ", ".join(str(p) for p in CONFIG_PATHS),
        )
        logger.error("Copy config.example.yaml to config.yaml and edit it.")
        sys.exit(1)

    with open(config_path) as f:
        config = yaml.safe_load(f)

    logger.info("Config loaded from %s", config_path)
    return config


def validate_config(config: dict):
    store = config.get("store", {})
    if not store.get("store_id") or store["store_id"] == "your-store-uuid-here":
        logger.error("store.store_id not set in config.yaml")
        sys.exit(1)
    if not store.get("api_endpoint"):
        logger.error("store.api_endpoint not set in config.yaml")
        sys.exit(1)

    cameras = config.get("cameras", [])
    if not cameras:
        logger.error("No cameras configured in config.yaml")
        sys.exit(1)

    for cam in cameras:
        if not cam.get("rtsp_url"):
            logger.error("Camera %s missing rtsp_url", cam.get("id", "?"))
            sys.exit(1)

    logger.info("Config validated: %d camera(s)", len(cameras))


def setup_logging(config: dict):
    log_config = config.get("logging", {})
    level = getattr(logging, log_config.get("level", "INFO").upper(), logging.INFO)
    fmt = "%(asctime)s | %(name)-25s | %(levelname)-5s | %(message)s"

    handlers = [logging.StreamHandler()]
    log_file = log_config.get("file")
    if log_file:
        try:
            fh = logging.FileHandler(log_file, maxBytes=log_config.get("max_size_mb", 50) * 1024 * 1024)
            handlers.append(fh)
        except (OSError, TypeError):
            pass

    logging.basicConfig(level=level, format=fmt, handlers=handlers)


async def run_camera_pipeline(config: dict, cam_config: dict):
    sys.path.insert(0, str(Path(__file__).parent.parent / "src"))
    from vision.pipeline import VisionPipeline, PipelineConfig

    store = config.get("store", {})
    processing = config.get("processing", {})
    privacy = config.get("privacy", {})

    pipeline_config = PipelineConfig(
        camera_id=cam_config.get("id", ""),
        org_id=store.get("store_id", ""),
        rtsp_url=cam_config["rtsp_url"],
        zone_config=cam_config.get("zone_config", {}),
        compliance_mode=privacy.get("compliance_mode", "anonymous"),
        active_hours=cam_config.get("active_hours", {"start": "07:00", "end": "22:00"}),
        detection_confidence=processing.get("detection_confidence", 0.4),
        recognition_interval_sec=processing.get("recognition_interval_sec", 5),
        batch_interval_sec=processing.get("batch_interval_sec", 60),
        api_url=store.get("api_endpoint", "http://localhost:8000"),
        heartbeat_interval_sec=processing.get("heartbeat_interval_sec", 30),
    )

    pipeline = VisionPipeline(pipeline_config)
    logger.info("Starting pipeline for camera: %s (%s)", cam_config.get("name", "?"), cam_config["rtsp_url"])

    await pipeline.run_camera()


async def main(config: dict):
    cameras = config.get("cameras", [])
    logger.info(
        "Starting Meridian Vision Edge — %d camera(s), mode: %s",
        len(cameras),
        config.get("privacy", {}).get("compliance_mode", "anonymous"),
    )

    shutdown_event = asyncio.Event()

    def handle_signal(sig, frame):
        logger.info("Received %s — shutting down gracefully...", signal.Signals(sig).name)
        shutdown_event.set()

    signal.signal(signal.SIGINT, handle_signal)
    signal.signal(signal.SIGTERM, handle_signal)

    tasks = []
    for cam in cameras:
        task = asyncio.create_task(run_camera_pipeline(config, cam))
        tasks.append(task)

    shutdown_task = asyncio.create_task(shutdown_event.wait())
    done, pending = await asyncio.wait(
        [*tasks, shutdown_task],
        return_when=asyncio.FIRST_COMPLETED,
    )

    for task in pending:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    logger.info("All pipelines stopped. Goodbye.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Meridian Vision Edge Pipeline")
    parser.add_argument("--config", "-c", type=str, help="Path to config.yaml")
    args = parser.parse_args()

    config = load_config(args.config)
    setup_logging(config)
    validate_config(config)

    asyncio.run(main(config))
