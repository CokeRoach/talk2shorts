"""Speech to one-line captions: transcribe with faster-whisper, or read an SRT, then break into lines."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .fonts import TextMeasure


@dataclass(frozen=True)
class Word:
    start: float
    end: float
    text: str


@dataclass(frozen=True)
class Line:
    start: float
    end: float
    text: str


def transcribe(video: str | Path, start: float, duration: float, model: str = "small",
               language: str | None = None, device: str = "auto") -> list[Word]:
    """Words with times relative to ``start``. Needs ``pip install talk2shorts[captions]``."""
    try:
        from faster_whisper import WhisperModel
    except ImportError:
        raise RuntimeError("automatic captions need faster-whisper: pip install 'talk2shorts[captions]', "
                           "or pass --srt with your own captions") from None
    import subprocess

    import numpy as np

    from .media import tool

    # ffmpeg decodes the audio itself and hands faster-whisper the samples, so its own decoder
    # (PyAV, whose newer releases changed an argument faster-whisper passes) is never used.
    pcm = subprocess.run([tool("ffmpeg"), "-v", "error", "-ss", f"{start:.3f}", "-t", f"{duration:.3f}",
                          "-i", str(video), "-vn", "-ac", "1", "-ar", "16000", "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    audio = np.frombuffer(pcm, np.float32)

    def run(dev: str, compute: str) -> list[Word]:
        whisper = WhisperModel(model, device=dev, compute_type=compute)
        segments, _ = whisper.transcribe(audio, language=language, word_timestamps=True, vad_filter=True)
        return [Word(w.start, w.end, w.word) for seg in segments for w in (seg.words or [])]

    try:
        words = run(device, "default")
    except RuntimeError as exc:
        # A GPU without the CUDA libraries faster-whisper needs (cuBLAS, cuDNN) fails only once
        # decoding starts; the CPU gives the same words, just slower.
        if device == "cpu" or not any(k in str(exc).lower() for k in ("cublas", "cudnn", "cuda")):
            raise
        words = run("cpu", "int8")
    return [w for w in words if w.text.strip()]


_SRT_TIME = re.compile(r"(\d+):(\d{2}):(\d{2})[,.](\d{1,3})")


def read_srt(path: str | Path, start: float = 0.0, duration: float | None = None) -> list[Line]:
    """Cues from an SRT file, shifted so ``start`` becomes 0 and clipped to the segment."""
    text = Path(path).read_text(encoding="utf-8-sig")
    lines = []
    for block in re.split(r"\n\s*\n", text.replace("\r\n", "\n").strip()):
        rows = block.split("\n")
        timing = next((i for i, r in enumerate(rows) if "-->" in r), None)
        if timing is None:
            continue
        a, b = (_seconds(m) for m in _SRT_TIME.finditer(rows[timing]))
        body = " ".join(r.strip() for r in rows[timing + 1:] if r.strip())
        body = re.sub(r"<[^>]+>", "", body)
        a, b = a - start, b - start
        if duration is not None:
            if b <= 0 or a >= duration:
                continue
            a, b = max(0.0, a), min(duration, b)
        if body:
            lines.append(Line(a, b, body))
    return lines


def _seconds(m: re.Match) -> float:
    h, mi, s, ms = m.groups()
    return int(h) * 3600 + int(mi) * 60 + int(s) + int(ms.ljust(3, "0")) / 1000


def _join(words: list[Word]) -> str:
    return "".join(w.text for w in words).strip()


def group_words(words: list[Word], measure: TextMeasure, max_width: float, max_lines: int = 2,
                pause: float = 0.5, max_seconds: float = 4.0, min_seconds: float = 1.0,
                tail: float = 0.15) -> list[Line]:
    """Captions of up to ``max_lines`` lines, cut at a pause, a sentence end, or when full.

    A caption shorter than ``min_seconds`` joins the next one when the two still fit, so a
    stray "now?" does not flash on its own. Lines inside a caption are balanced in width.
    """
    groups: list[list[Word]] = []
    current: list[Word] = []
    for word in words:
        if current:
            gap = word.start - current[-1].end
            too_full = len(measure.wrap(_join(current + [word]), max_width)) > max_lines
            too_long = word.end - current[0].start > max_seconds
            ends_sentence = current[-1].text.strip()[-1:] in ".?!。？！…"
            if gap >= pause or ends_sentence:
                groups.append(current)
                current = []
            elif too_full or too_long:
                # Break after the last comma in the second half rather than mid-phrase.
                cut = next((j for j in range(len(current) - 1, len(current) // 2 - 1, -1)
                            if current[j].text.strip()[-1:] in ",;:、，"), None)
                if cut is not None and cut < len(current) - 1:
                    groups.append(current[:cut + 1])
                    current = current[cut + 1:]
                else:
                    groups.append(current)
                    current = []
        current.append(word)
    if current:
        groups.append(current)

    # A lone word right after a full caption takes the last words of that caption with it.
    for i in range(1, len(groups)):
        prev, cur = groups[i - 1], groups[i]
        if len(cur) == 1 and len(prev) >= 4 and cur[0].start - prev[-1].end < 0.3:
            while len(cur) < 3 and len(prev) > 3:
                moved = cur[:0] + [prev[-1]] + cur
                if len(measure.wrap(_join(moved), max_width)) > max_lines or prev[-2].text.strip()[-1:] in ".?!。？！":
                    break
                cur.insert(0, prev.pop())

    merged: list[list[Word]] = []
    for group in groups:
        if merged:
            prev = merged[-1]
            short = prev[-1].end - prev[0].start < min_seconds or group[-1].end - group[0].start < min_seconds
            close = group[0].start - prev[-1].end < 0.8
            fits = len(measure.wrap(_join(prev + group), max_width)) <= max_lines
            if short and close and fits and group[-1].end - prev[0].start <= max_seconds + 1:
                prev.extend(group)
                continue
        merged.append(list(group))

    out = []
    for i, group in enumerate(merged):
        start, end = group[0].start, group[-1].end + tail
        if i + 1 < len(merged):
            nxt = merged[i + 1][0].start
            end = nxt if nxt - end < 0.4 else min(end, nxt)
        text = "\n".join(measure.balance(_join(group), max_width, max_lines))
        out.append(Line(start, max(end, start + 0.6), text))
    return out


def fit_lines(lines: list[Line], measure: TextMeasure, max_width: float, max_lines: int = 2) -> list[Line]:
    """Fit each cue into ``max_lines`` balanced lines; a longer cue becomes several, sharing its time by length."""
    out = []
    for line in lines:
        rows = measure.wrap(line.text, max_width)
        if len(rows) <= max_lines:
            out.append(Line(line.start, line.end, "\n".join(measure.balance(line.text, max_width, max_lines))))
            continue
        sep = " " if " " in line.text else ""
        chunks: list[str] = []
        # Sentences first, so a cue holding two sentences splits between them.
        for sentence in re.split(r"(?<=[.?!。？！])\s+", line.text.strip()):
            if chunks and len(measure.wrap(chunks[-1] + sep + sentence, max_width)) <= max_lines:
                chunks[-1] += sep + sentence
                continue
            rows = measure.wrap(sentence, max_width)
            chunks += [sep.join(rows[i:i + max_lines]) for i in range(0, len(rows), max_lines)]
        total = sum(len(c) for c in chunks) or 1
        t = line.start
        for chunk in chunks:
            span = (line.end - line.start) * len(chunk) / total
            out.append(Line(t, t + span, "\n".join(measure.balance(chunk, max_width, max_lines))))
            t += span
    return out


def write_srt(lines: list[Line], path: str | Path) -> None:
    def ts(s: float) -> str:
        ms = round(s * 1000)
        return f"{ms // 3600000:02d}:{ms // 60000 % 60:02d}:{ms // 1000 % 60:02d},{ms % 1000:03d}"
    blocks = [f"{i}\n{ts(l.start)} --> {ts(l.end)}\n{l.text}\n" for i, l in enumerate(lines, 1)]
    Path(path).write_text("\n".join(blocks), encoding="utf-8")
