"""Follow the speaker's face horizontally and turn it into a steady 9:16 crop path."""

from __future__ import annotations

import hashlib
import os
import urllib.request
from pathlib import Path

import numpy as np

from .media import sample_frames

# YuNet face detector from the OpenCV model zoo (MIT licence).
MODEL_URL = (
    "https://media.githubusercontent.com/media/opencv/opencv_zoo/main/models/"
    "face_detection_yunet/face_detection_yunet_2023mar.onnx"
)
MODEL_SHA256 = "8f2383e4dd3cfbb4553ea8718107fc0423210dc964f9f4280604804ed2552fa4"
DETECT_WIDTH = 640


def model_path() -> Path:
    """The YuNet model, downloaded once into the user cache and checked by hash."""
    cache = Path(os.environ.get("TALK2SHORTS_CACHE") or Path.home() / ".cache" / "talk2shorts")
    path = cache / "face_detection_yunet_2023mar.onnx"
    if path.exists() and _sha256(path) == MODEL_SHA256:
        return path
    cache.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".part")
    urllib.request.urlretrieve(MODEL_URL, tmp)
    if _sha256(tmp) != MODEL_SHA256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError("downloaded face model failed its checksum; try again later")
    tmp.replace(path)
    return path


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def detect_centers(video: str | Path, start: float, duration: float, every: float = 0.2):
    """(times, centres, tops): the face's x centre and top edge as 0-1 shares of the frame, NaN without a face."""
    import cv2

    try:
        cv2.utils.logging.setLogLevel(cv2.utils.logging.LOG_LEVEL_ERROR)
    except AttributeError:
        pass
    detector = None
    times, centers, tops = [], [], []
    last = None
    for t, frame in sample_frames(video, start, duration, every, DETECT_WIDTH):
        if detector is None:
            h, w = frame.shape[:2]
            # Load from bytes: OpenCV cannot open a path with non-ASCII characters on Windows
            # (a Korean or Japanese user name puts them in every cache path).
            model = np.frombuffer(model_path().read_bytes(), np.uint8)
            detector = cv2.FaceDetectorYN.create("onnx", model, np.empty(0, np.uint8), (w, h), 0.7, 0.3, 5000)
        _, faces = detector.detect(frame)
        x = top = np.nan
        if faces is not None and len(faces):
            w = frame.shape[1]
            # The biggest face, but stay with the speaker we had when another face is close in size.
            sizes = faces[:, 2] * faces[:, 3]
            order = np.argsort(-sizes)
            pick = order[0]
            if last is not None:
                near = [i for i in order if sizes[i] >= 0.6 * sizes[order[0]]]
                pick = min(near, key=lambda i: abs((faces[i, 0] + faces[i, 2] / 2) / w - last))
            x = float((faces[pick, 0] + faces[pick, 2] / 2) / w)
            top = float(faces[pick, 1] / frame.shape[0])
            last = x
        times.append(t)
        centers.append(x)
        tops.append(top)
    return np.array(times), np.array(centers, dtype=float), np.array(tops, dtype=float)


def smooth_path(times, centers, crop_share: float, fps: float, duration: float,
                dead_zone: float = 0.06, follow: float = 0.9) -> np.ndarray:
    """Crop centre (0-1 of frame width) for every output frame.

    Gaps without a face hold the last position. Small moves inside ``dead_zone`` (a share of
    the frame width) are ignored, so the frame does not wobble with the speaker's gestures;
    larger moves are followed with a time constant of ``follow`` seconds.
    """
    n = max(1, int(round(duration * fps)))
    half = crop_share / 2
    if len(centers) == 0 or np.all(np.isnan(centers)):
        return np.full(n, 0.5)
    filled = np.array(centers, dtype=float)
    valid = ~np.isnan(filled)
    filled[~valid] = np.interp(np.flatnonzero(~valid), np.flatnonzero(valid), filled[valid])
    k = 5
    padded = np.pad(filled, (k // 2, k // 2), mode="edge")
    filled = np.array([np.median(padded[i:i + k]) for i in range(len(filled))])
    target = np.interp(np.arange(n) / fps, times, filled)
    out = np.empty(n)
    pos = target[0]
    alpha = 1 - np.exp(-1 / (fps * follow))
    for i, goal in enumerate(target):
        if abs(goal - pos) > dead_zone:
            pos += (goal - pos) * alpha * 4
        elif abs(goal - pos) > dead_zone / 4:
            pos += (goal - pos) * alpha
        out[i] = pos
    return np.clip(out, half, 1 - half)
