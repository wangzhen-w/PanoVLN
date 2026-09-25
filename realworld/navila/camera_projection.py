"""Project the camera's ERP frames into the model's forward perspective view."""
from __future__ import annotations

import math
import threading

DEFAULT_PERSPECTIVE_HFOV = 90.0
DEFAULT_PERSPECTIVE_WIDTH = 512
DEFAULT_PERSPECTIVE_HEIGHT = 512


class PerspectiveProjector:
    def __init__(self, width, height, hfov, yaw=0.0, pitch=0.0):
        self.width, self.height = int(width), int(height)
        self.hfov, self.yaw, self.pitch = float(hfov), float(yaw), float(pitch)
        if min(self.width, self.height) < 2:
            raise ValueError("Perspective width and height must be at least 2")
        if not all(math.isfinite(v) for v in (self.hfov, self.yaw, self.pitch)):
            raise ValueError("Perspective angles must be finite")
        if not 0 < self.hfov < 180 or not -90 <= self.pitch <= 90:
            raise ValueError("Perspective HFOV must be between 0 and 180, pitch between -90 and 90")
        self._source_size = None
        self._maps = None
        self._lock = threading.Lock()

    def _sampling_maps(self, source_width, source_height):
        import numpy as np

        size = (source_width, source_height)
        with self._lock:
            if size == self._source_size:
                return self._maps
            if not 1.8 <= source_width / source_height <= 2.2:
                raise ValueError(
                    f"Expected a stitched 2:1 ERP camera frame, got {source_width}x{source_height}. "
                    "Check the camera device and capture mode."
                )
            # Pixel-centred pinhole rays: +x right, +y up, +z forward.
            scale = math.tan(math.radians(self.hfov) / 2)
            cx = ((np.arange(self.width) + 0.5) / self.width * 2 - 1) * scale
            cy = -((np.arange(self.height) + 0.5) / self.height * 2 - 1) * scale * self.height / self.width
            x, y = np.meshgrid(cx, cy)
            z = np.ones_like(x)
            pitch, yaw = map(math.radians, (self.pitch, self.yaw))
            y, z = y * math.cos(pitch) + z * math.sin(pitch), z * math.cos(pitch) - y * math.sin(pitch)
            x, z = x * math.cos(yaw) + z * math.sin(yaw), z * math.cos(yaw) - x * math.sin(yaw)
            longitude = np.arctan2(x, z)
            latitude = np.arctan2(y, np.hypot(x, z))
            u = (longitude / (2 * math.pi) + 0.5) * source_width - 0.5
            v = (0.5 - latitude / math.pi) * source_height - 0.5
            # Wrap longitude at the ERP seam; clamp latitude at the poles.
            self._maps = (
                (u % source_width).astype(np.float32),
                np.clip(v, 0, source_height - 1).astype(np.float32),
            )
            self._source_size = size
            return self._maps

    def __call__(self, frame):
        import cv2

        if frame.ndim != 3 or frame.shape[2] != 3 or frame.dtype.name != "uint8":
            raise ValueError("Expected an 8-bit, three-channel OpenCV camera frame")
        maps = self._sampling_maps(frame.shape[1], frame.shape[0])
        # Keep OpenCV BGR unchanged through projection, JPEG encoding and video.
        return cv2.remap(frame, *maps, interpolation=cv2.INTER_LINEAR, borderMode=cv2.BORDER_WRAP)

    def validate_server(self, ready):
        if ready.get("input_view") != "perspective":
            raise ValueError(
                "The client uploads perspective images. Update/restart the matching model server "
                "with --input-view perspective to avoid projecting the images twice."
            )
        settings = ready.get("settings", {})
        for name, value in (("width", self.width), ("height", self.height),
                            ("hfov", self.hfov), ("yaw", self.yaw), ("pitch", self.pitch)):
            key = "perspective_" + name
            actual = settings.get(key)
            if actual is None or not math.isclose(float(actual), value, abs_tol=1e-6, rel_tol=0):
                raise ValueError(f"Client/server view mismatch: {key}={value}, server={actual}")
