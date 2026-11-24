"""Build the vertical short with one ffmpeg run: moving crop, burned-in captions and title, -14 LUFS."""

from __future__ import annotations

import subprocess
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from .captions import Line
from .layout import H, W, Slot
from .media import Probe, loudness, tool


@dataclass
class Style:
    font_name: str = "Arial"
    caption_size: int = 58
    title_size: int = 80
    box_opacity: float = 0.6          # caption background, 0 = none
    loudness: float = -14.0
    fade: float = 1.0
    title_seconds: float = 3.0


@dataclass
class Plan:
    source: Path
    start: float
    duration: float
    probe: Probe
    centres: np.ndarray               # crop centre per output frame, 0-1 of source width
    captions: list[Line] = field(default_factory=list)
    caption_slot: Slot | None = None
    title_lines: list[str] = field(default_factory=list)
    title_slot: Slot | None = None


def crop_size(p: Probe) -> tuple[int, int]:
    """The largest 9:16 window inside the source frame, in even pixels."""
    if p.width / p.height > 9 / 16:
        h = p.height - p.height % 2
        w = int(h * 9 / 16) // 2 * 2
    else:
        w = p.width - p.width % 2
        h = int(w * 16 / 9) // 2 * 2
    return w, h


def _ass_time(s: float) -> str:
    cs = max(0, round(s * 100))
    return f"{cs // 360000}:{cs // 6000 % 60:02d}:{cs // 100 % 60:02d}.{cs % 100:02d}"


def _ass_text(text: str) -> str:
    return text.replace("\\", "\\\\").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def write_ass(plan: Plan, style: Style, path: Path) -> None:
    box = round(255 * (1 - style.box_opacity))
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: {W}
PlayResY: {H}
WrapStyle: 2
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Caption,{style.font_name},{style.caption_size},&H00FFFFFF,&H00FFFFFF,&H{box:02X}000000,&H{box:02X}000000,-1,0,0,0,100,100,0,0,{3 if style.box_opacity > 0 else 1},{14 if style.box_opacity > 0 else 3},0,2,0,0,0,1
Style: Title,{style.font_name},{style.title_size},&H00FFFFFF,&H00FFFFFF,&H00000000,&H80000000,-1,0,0,0,100,100,0,0,1,5,2,8,0,0,0,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
"""
    events = []
    if plan.caption_slot:
        s = plan.caption_slot
        x, y = round(s.centre), round(s.bottom - (14 if style.box_opacity > 0 else 0))
        for line in plan.captions:
            events.append(f"Dialogue: 0,{_ass_time(line.start)},{_ass_time(line.end)},Caption,,0,0,0,,"
                          f"{{\\an2\\pos({x},{y})}}{_ass_text(line.text)}")
    if plan.title_lines and plan.title_slot:
        s = plan.title_slot
        fade = "{\\fad(250,400)}"
        events.append(f"Dialogue: 1,{_ass_time(0)},{_ass_time(style.title_seconds)},Title,,0,0,0,,"
                      f"{fade}{{\\an8\\pos({round(s.centre)},{round(s.top)})}}" + "\\N".join(_ass_text(t) for t in plan.title_lines))
    path.write_text(header + "\n".join(events) + "\n", encoding="utf-8")


def write_crop_commands(plan: Plan, crop_w: int, path: Path) -> int:
    """sendcmd lines moving the crop every frame; returns the first x."""
    p = plan.probe
    xs = np.clip(np.round(plan.centres * p.width - crop_w / 2), 0, p.width - crop_w).astype(int)
    lines = [f"{i / p.fps:.4f} crop x {x};" for i, x in enumerate(xs)]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return int(xs[0])


def render(plan: Plan, style: Style, out: Path, crf: int = 18) -> dict:
    p = plan.probe
    crop_w, crop_h = crop_size(p)
    with tempfile.TemporaryDirectory(prefix="talk2shorts-") as tmp:
        work = Path(tmp)
        x0 = write_crop_commands(plan, crop_w, work / "crop.cmd")
        write_ass(plan, style, work / "subs.ass")
        y0 = (p.height - crop_h) // 2
        fade_start = max(0.0, plan.duration - style.fade)
        video = (f"sendcmd=f=crop.cmd,crop=w={crop_w}:h={crop_h}:x={x0}:y={y0},"
                 f"scale={W}:{H}:flags=lanczos,setsar=1,ass=subs.ass,"
                 f"fade=t=out:st={fade_start:.3f}:d={style.fade:.3f}")
        cmd = [tool("ffmpeg"), "-v", "error", "-y", "-ss", f"{plan.start:.3f}", "-t", f"{plan.duration:.3f}",
               "-i", str(Path(plan.source).resolve()), "-vf", video]
        measured = None
        if p.has_audio:
            m = loudness(plan.source, plan.start, plan.duration)
            measured = float(m["input_i"])
            audio = (f"loudnorm=I={style.loudness}:TP=-1.5:LRA=11:measured_I={m['input_i']}:"
                     f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:"
                     f"measured_thresh={m['input_thresh']}:offset={m['target_offset']}:linear=true,"
                     f"aresample=48000,afade=t=out:st={fade_start:.3f}:d={style.fade:.3f}")
            cmd += ["-af", audio, "-c:a", "aac", "-b:a", "192k"]
        else:
            cmd += ["-an"]
        cmd += ["-c:v", "libx264", "-crf", str(crf), "-preset", "medium", "-pix_fmt", "yuv420p",
                "-movflags", "+faststart", str(Path(out).resolve())]
        result = subprocess.run(cmd, cwd=work, capture_output=True, text=True, encoding="utf-8", errors="replace")
        if result.returncode != 0:
            raise RuntimeError("ffmpeg failed:\n" + result.stderr.strip()[-2000:])
    return {"crop": [crop_w, crop_h], "source_loudness": measured}
