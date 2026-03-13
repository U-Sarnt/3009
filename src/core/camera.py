"""Camera helpers for live QR scanning."""

from __future__ import annotations

import sys
from typing import Optional

import cv2
from PySide6.QtCore import QMutex, QMutexLocker, QThread, Signal
from PySide6.QtGui import QImage


def _backend_candidates():
    """Return backend candidates ordered by platform preference."""
    candidates = []

    if sys.platform.startswith("win"):
        if hasattr(cv2, "CAP_DSHOW"):
            candidates.append(cv2.CAP_DSHOW)
        if hasattr(cv2, "CAP_MSMF"):
            candidates.append(cv2.CAP_MSMF)
    elif sys.platform == "darwin":
        if hasattr(cv2, "CAP_AVFOUNDATION"):
            candidates.append(cv2.CAP_AVFOUNDATION)
        if hasattr(cv2, "CAP_QT"):
            candidates.append(cv2.CAP_QT)
    elif sys.platform.startswith("linux"):
        if hasattr(cv2, "CAP_V4L2"):
            candidates.append(cv2.CAP_V4L2)
        if hasattr(cv2, "CAP_GSTREAMER"):
            candidates.append(cv2.CAP_GSTREAMER)

    candidates.append(None)
    return candidates


def open_video_capture(index: int = 0) -> Optional[cv2.VideoCapture]:
    """Open a camera using the best backend available for the host OS."""
    for backend in _backend_candidates():
        try:
            capture = (
                cv2.VideoCapture(index, backend)
                if backend is not None
                else cv2.VideoCapture(index)
            )
            if capture is not None and capture.isOpened():
                return capture
            if capture is not None:
                capture.release()
        except Exception:
            continue

    return None


class CameraThread(QThread):
    """Threaded camera capture with built-in QR detection using OpenCV."""

    frame_ready = Signal(QImage)
    qr_detected = Signal(str)
    error_occurred = Signal(str)

    def __init__(self, camera_index: int = 0, parent=None):
        super().__init__(parent)
        self.camera_index = camera_index
        self.running = False
        self.mutex = QMutex()
        self.last_qr_data = None
        self.qr_cooldown = 0
        self.qr_detector = cv2.QRCodeDetector()

    def run(self) -> None:
        capture = open_video_capture(self.camera_index)
        if capture is None:
            self.error_occurred.emit("No se pudo abrir la camara")
            return

        self.running = True
        try:
            while self.running:
                ok, frame = capture.read()
                if not ok:
                    continue

                self.detect_qr_codes(frame)

                rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                height, width, channels = rgb_frame.shape
                bytes_per_line = channels * width
                image = QImage(
                    rgb_frame.data,
                    width,
                    height,
                    bytes_per_line,
                    QImage.Format_RGB888,
                )
                self.frame_ready.emit(image.copy())

                if self.qr_cooldown > 0:
                    self.qr_cooldown -= 1

                self.msleep(30)
        except Exception as exc:
            self.error_occurred.emit(f"Error en camara: {exc}")
        finally:
            capture.release()

    def detect_qr_codes(self, frame) -> None:
        """Detect QR codes in the current frame and emit the decoded payload."""
        try:
            data, bbox, _ = self.qr_detector.detectAndDecode(frame)
            if not data:
                return

            with QMutexLocker(self.mutex):
                if data != self.last_qr_data or self.qr_cooldown == 0:
                    self.last_qr_data = data
                    self.qr_cooldown = 30
                    self.qr_detected.emit(data)

            if bbox is not None:
                bbox = bbox.astype(int)
                cv2.polylines(frame, [bbox], True, (0, 255, 0), 3)
        except Exception as exc:
            print(f"Error detectando QR: {exc}")

    def stop(self) -> None:
        """Request a clean stop of the camera thread."""
        with QMutexLocker(self.mutex):
            self.running = False
