from __future__ import annotations

import logging
import queue
import threading

import cv2
import numpy as np

logger = logging.getLogger("meridian.camera.rtsp")


class RTSPStreamHandler:

    def __init__(self, rtsp_url: str, camera_id: str) -> None:
        self._url = rtsp_url
        self._camera_id = camera_id
        self._cap: cv2.VideoCapture | None = None
        self._frame_queue: queue.Queue[np.ndarray] = queue.Queue(maxsize=2)
        self._thread: threading.Thread | None = None
        self._running = False

    @property
    def camera_id(self) -> str:
        return self._camera_id

    @property
    def is_running(self) -> bool:
        return self._running

    def start(self) -> None:
        if self._running:
            return

        self._cap = cv2.VideoCapture(self._url)
        self._cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        if not self._cap.isOpened():
            logger.error("Failed to open RTSP stream for camera %s: %s", self._camera_id, self._url)
            self._cap.release()
            self._cap = None
            raise ConnectionError(f"Cannot open RTSP stream: {self._url}")

        self._running = True
        self._thread = threading.Thread(
            target=self._read_loop,
            name=f"rtsp-{self._camera_id}",
            daemon=True,
        )
        self._thread.start()
        logger.info("Started RTSP stream for camera %s", self._camera_id)

    def stop(self) -> None:
        self._running = False
        if self._thread is not None:
            self._thread.join(timeout=5.0)
            self._thread = None
        if self._cap is not None:
            self._cap.release()
            self._cap = None
        logger.info("Stopped RTSP stream for camera %s", self._camera_id)

    def get_latest_frame(self, timeout: float = 2.0) -> np.ndarray | None:
        try:
            return self._frame_queue.get(timeout=timeout)
        except queue.Empty:
            return None

    def _read_loop(self) -> None:
        while self._running:
            if self._cap is None or not self._cap.isOpened():
                logger.warning("RTSP capture lost for camera %s, stopping", self._camera_id)
                self._running = False
                break

            ret, frame = self._cap.read()
            if not ret:
                logger.warning("Failed to read frame from camera %s", self._camera_id)
                continue

            # Always drop old frames to keep only the freshest
            if self._frame_queue.full():
                try:
                    self._frame_queue.get_nowait()
                except queue.Empty:
                    pass

            self._frame_queue.put(frame)
