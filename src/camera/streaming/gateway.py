"""StreamGateway interface — keeps the rest of the stack ignorant of the media
server. MediaMtxGateway is the live impl; KvsGateway is a stub so ingest/storage/TURN
can move to AWS Kinesis Video Streams later without touching anything above this layer.

ponytail: pure URL/derivation logic + thin config; no media handling here (MediaMTX does
that). No new deps.
"""
from __future__ import annotations

import os
from abc import ABC, abstractmethod


def _camera_path(camera_id: str) -> str:
    """Canonical MediaMTX path a camera publishes to."""
    return f"cam/{camera_id}"


class StreamGateway(ABC):
    """Everything above the media server talks to this, not to MediaMTX/KVS directly."""

    @abstractmethod
    def publish_url(self, camera_id: str) -> str:
        """Where the connector pushes the camera's video (outbound, WHIP/RTSP-over-TLS)."""

    @abstractmethod
    def viewer_whep_url(self, camera_id: str) -> str:
        """Browser WebRTC (WHEP) playback URL (sub-second)."""

    @abstractmethod
    def viewer_hls_url(self, camera_id: str) -> str:
        """LL-HLS fallback playback URL."""

    @abstractmethod
    def inference_rtsp_url(self, camera_id: str) -> str:
        """RTSP URL the GPU/inference box pulls for the analytics fork."""


class MediaMtxGateway(StreamGateway):
    """Live gateway backed by self-hosted MediaMTX (+ coturn) on Contabo."""

    def __init__(self, host: str | None = None, *, internal_host: str | None = None):
        # public host browsers reach; internal host the inference box/API reach
        self.host = host or os.environ.get("MEDIA_STREAM_HOST", "stream.meridian.tips")
        self.internal_host = internal_host or os.environ.get("MEDIA_STREAM_INTERNAL_HOST", "127.0.0.1")

    def publish_url(self, camera_id: str) -> str:
        return f"https://{self.host}:8889/{_camera_path(camera_id)}/whip"

    def viewer_whep_url(self, camera_id: str) -> str:
        return f"https://{self.host}:8889/{_camera_path(camera_id)}/whep"

    def viewer_hls_url(self, camera_id: str) -> str:
        return f"https://{self.host}:8888/{_camera_path(camera_id)}/index.m3u8"

    def inference_rtsp_url(self, camera_id: str) -> str:
        # internal pull (the inference box dials out to the gateway)
        return f"rtsp://{self.internal_host}:8554/{_camera_path(camera_id)}"


class KvsGateway(StreamGateway):
    """Stub for AWS Kinesis Video Streams — offload ingest/storage/TURN later without
    touching callers. KVS time-indexes every fragment, which fits the POS cross-reference
    /clip contract identically. ponytail: not built until bandwidth forces it."""

    def __init__(self, *_, **__):  # pragma: no cover - stub
        raise NotImplementedError(
            "KvsGateway is a planned offload target; MediaMtxGateway is the live impl."
        )

    def publish_url(self, camera_id: str) -> str: ...  # pragma: no cover
    def viewer_whep_url(self, camera_id: str) -> str: ...  # pragma: no cover
    def viewer_hls_url(self, camera_id: str) -> str: ...  # pragma: no cover
    def inference_rtsp_url(self, camera_id: str) -> str: ...  # pragma: no cover


def get_gateway() -> StreamGateway:
    """Factory — swap impls via STREAM_GATEWAY env (default mediamtx)."""
    impl = os.environ.get("STREAM_GATEWAY", "mediamtx").lower()
    if impl == "kvs":
        return KvsGateway()
    return MediaMtxGateway()
