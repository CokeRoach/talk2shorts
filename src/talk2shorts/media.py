"""ffmpeg and ffprobe helpers."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path

import numpy as np


def tool(name: str) -> str:
    path = shutil.which(name)
    if path is None:
        raise RuntimeError(f"{name} not found on PATH; install ffmpeg (https://ffmpeg.org)")
    return path


@dataclass(frozen=True)
class Probe:
    width: int
    height: int
    fps: float
    duration: float
    has_audio: bool


def probe(path: str | Path) -> Probe:
    if shutil.which("ffprobe") is None:
        return _probe_with_ffmpeg(path)
    out = subprocess.run(
        [tool("ffprobe"), "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)],
        capture_output=True, text=True, encoding="utf-8",
    )
    if out.returncode != 0:
        raise RuntimeError(f"ffprobe could not read {path}: {out.stderr.strip()}")
    data = json.loads(out.stdout)
    video = next((s for s in data["streams"] if s.get("codec_type") == "video"), None)
    if video is None:
        raise RuntimeError(f"{path} has no video stream")
    num, den = (int(x) for x in video.get("avg_frame_rate", "30/1").split("/"))
    fps = num / den if den else 30.0
    rotation = 0
    for side in video.get("side_data_list", []):
        rotation = int(side.get("rotation", rotation) or 0)
    w, h = int(video["width"]), int(video["height"])
    if abs(rotation) in (90, 270):
        w, h = h, w
    return Probe(
        width=w, height=h, fps=fps or 30.0,
        duration=float(data["format"].get("duration", video.get("duration", 0)) or 0),
        has_audio=any(s.get("codec_type") == "audio" for s in data["streams"]),
    )


def _probe_with_ffmpeg(path: str | Path) -> Probe:
    """The same facts from ``ffmpeg -i``, for installs that ship ffmpeg without ffprobe."""
    err = subprocess.run([tool("ffmpeg"), "-hide_banner", "-i", str(path)],
                         capture_output=True, text=True, encoding="utf-8", errors="replace").stderr
    video = re.search(r"Stream #\S+.*?: Video: .*", err)
    if not video:
        raise RuntimeError(f"ffmpeg could not read a video stream from {path}")
    size = re.search(r"(\d{2,5})x(\d{2,5})", video.group(0))
    fps = re.search(r"([\d.]+) fps", video.group(0)) or re.search(r"([\d.]+) tbr", video.group(0))
    dur = re.search(r"Duration: (\d+):(\d+):([\d.]+)", err)
    w, h = int(size.group(1)), int(size.group(2))
    rot = re.search(r"rotation of (-?[\d.]+) degrees", err)
    if rot and round(abs(float(rot.group(1)))) % 180 == 90:
        w, h = h, w
    duration = int(dur.group(1)) * 3600 + int(dur.group(2)) * 60 + float(dur.group(3)) if dur else 0.0
    return Probe(width=w, height=h, fps=float(fps.group(1)) if fps else 30.0, duration=duration,
                 has_audio=bool(re.search(r"Stream #\S+.*?: Audio:", err)))


def sample_frames(path: str | Path, start: float, duration: float, every: float, width: int):
    """Yield (time, BGR frame) every ``every`` seconds, scaled to ``width`` px wide."""
    info = probe(path)
    height = round(info.height * width / info.width / 2) * 2
    cmd = [
        tool("ffmpeg"), "-v", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}", "-i", str(path),
        "-vf", f"fps=1/{every},scale={width}:{height}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-",
    ]
    size = width * height * 3
    with subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL) as proc:
        i = 0
        while True:
            buf = proc.stdout.read(size)
            if len(buf) < size:
                break
            yield i * every, np.frombuffer(buf, np.uint8).reshape(height, width, 3)
            i += 1


def loudness(path: str | Path, start: float = 0.0, duration: float | None = None) -> dict:
    """Integrated loudness, true peak and range from ffmpeg's loudnorm analysis."""
    cmd = [tool("ffmpeg"), "-hide_banner", "-nostats", "-ss", f"{start:.3f}"]
    if duration is not None:
        cmd += ["-t", f"{duration:.3f}"]
    cmd += ["-i", str(path), "-vn", "-af", "loudnorm=I=-14:TP=-1.5:LRA=11:print_format=json", "-f", "null", "-"]
    out = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    match = re.search(r"\{[^{}]*\"input_i\"[^{}]*\}", out.stderr, re.S)
    if not match:
        raise RuntimeError("ffmpeg loudnorm printed no measurement")
    return json.loads(match.group(0))


def parse_time(text: str) -> float:
    """'83', '83.5', '1:23', '01:23.5' or '0:01:23' as seconds."""
    parts = text.strip().split(":")
    if not 1 <= len(parts) <= 3 or any(p == "" for p in parts):
        raise ValueError(f"not a time: {text!r}")
    seconds = 0.0
    for part in parts:
        seconds = seconds * 60 + float(part)
    if seconds < 0:
        raise ValueError(f"negative time: {text!r}")
    return seconds
