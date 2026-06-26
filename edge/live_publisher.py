"""
On-demand live publisher — RTSP camera → Cloudflare Stream (WHIP).

The edge agent polls the backend's /live-state for each camera. When a viewer is
watching (publish=true), we run ffmpeg to push the camera's RTSP feed to the
Cloudflare WHIP ingest URL; when the viewer leaves, we stop. So Cloudflare (and
billing) only runs while someone is actually watching — no idle cost, nothing
streamed off-site otherwise.

H.264 is passed through (`-c:v copy`) when possible — no transcode = best quality
and ~zero CPU; falls back to libx264 only if the camera's codec isn't WHIP-safe.

Requires ffmpeg >= 7.1 on the edge (the `whip` muxer). Verified separately: the
Cloudflare relay accepts the published stream and exposes it via WHEP.
"""
import asyncio
import logging
import os

logger = logging.getLogger("meridian.edge.live")

FFMPEG_BIN = os.environ.get("FFMPEG_BIN", "ffmpeg")


class LivePublisher:
    """Manages a single camera's on-demand ffmpeg WHIP publish process."""

    def __init__(self, camera_id: str, rtsp_url: str):
        self.camera_id = camera_id
        self.rtsp_url = rtsp_url
        self._proc: asyncio.subprocess.Process | None = None
        self._whip: str = ""

    def is_running(self) -> bool:
        return self._proc is not None and self._proc.returncode is None

    async def ensure(self, publish: bool, whip_url: str | None):
        """Start publishing if a viewer wants it (and we're not already), stop otherwise."""
        if publish and whip_url:
            if self.is_running() and self._whip == whip_url:
                return  # already streaming to the right place
            await self.stop()
            await self._start(whip_url)
        else:
            await self.stop()

    async def _start(self, whip_url: str):
        # -c:v copy: pass the camera's H.264 through untouched (best quality, no CPU).
        cmd = [
            FFMPEG_BIN, "-loglevel", "warning",
            "-rtsp_transport", "tcp", "-i", self.rtsp_url,
            "-an", "-c:v", "copy",
            "-f", "whip", whip_url,
        ]
        try:
            self._proc = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL)
            self._whip = whip_url
            logger.info("live publish started: camera=%s", self.camera_id)
        except FileNotFoundError:
            logger.error("ffmpeg not found (need >=7.1 with whip) — cannot publish camera=%s",
                         self.camera_id)
            self._proc = None
        except Exception as e:  # noqa: BLE001
            logger.error("live publish start failed camera=%s: %s", self.camera_id, e)
            self._proc = None

    async def stop(self):
        if self._proc is not None and self._proc.returncode is None:
            try:
                self._proc.terminate()
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=5)
                except asyncio.TimeoutError:
                    self._proc.kill()
                logger.info("live publish stopped: camera=%s", self.camera_id)
            except Exception as e:  # noqa: BLE001
                logger.debug("live publish stop error camera=%s: %s", self.camera_id, e)
        self._proc = None
        self._whip = ""
