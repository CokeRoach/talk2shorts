"""talk2shorts: a vertical short from a section of a horizontal talk."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
from shorts_safezone import PLATFORMS, Box, check_box

from . import __version__
from .captions import fit_lines, group_words, read_srt, transcribe, write_srt
from .fonts import TextMeasure, detect_script, find_font, load_font
from .layout import caption_slot, title_slot
from .media import loudness, parse_time, probe
from .render import Plan, Style, crop_size, render
from .track import detect_centers, smooth_path


def _platforms(value: str) -> tuple[str, ...]:
    if value == "all":
        return PLATFORMS
    keys = tuple(v.strip() for v in value.split(","))
    bad = [k for k in keys if k not in PLATFORMS]
    if bad:
        raise argparse.ArgumentTypeError(f"unknown platform {', '.join(bad)}; use {', '.join(PLATFORMS)}")
    return keys


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="talk2shorts", description=__doc__)
    ap.add_argument("video", help="the horizontal source video")
    ap.add_argument("--start", required=True, help="section start: 83, 1:23 or 0:01:23.5")
    ap.add_argument("--end", required=True, help="section end, same format")
    ap.add_argument("-o", "--output", help="output mp4 (default: VIDEO_short.mp4)")
    ap.add_argument("--title", help="title shown at the top for the first seconds; '\\n' for a line break")
    ap.add_argument("--srt", help="your own captions (times in the source video) instead of speech recognition")
    ap.add_argument("--no-captions", action="store_true", help="no captions at all")
    ap.add_argument("--model", default="small", help="faster-whisper model (tiny, base, small, medium, large-v3)")
    ap.add_argument("--language", help="spoken language code (ko, en, ja...); detected when left out")
    ap.add_argument("--platforms", type=_platforms, default=PLATFORMS,
                    help="keep text clear of these players: all, or a comma list of " + ", ".join(PLATFORMS))
    ap.add_argument("--font", help="font file for captions and title (default: a bold system font with CJK)")
    ap.add_argument("--caption-size", type=int, default=58)
    ap.add_argument("--lines", type=int, choices=(1, 2), default=2, help="lines per caption (default 2)")
    ap.add_argument("--no-track", action="store_true", help="keep the crop centred instead of following the face")
    ap.add_argument("--version", action="version", version=f"talk2shorts {__version__}")
    return ap


def run(args) -> dict:
    src = Path(args.video)
    info = probe(src)
    start, end = parse_time(args.start), parse_time(args.end)
    if not 0 <= start < end:
        raise ValueError("--end must come after --start")
    end = min(end, info.duration) if info.duration else end
    duration = end - start
    out = Path(args.output) if args.output else src.with_name(src.stem + "_short.mp4")

    style = Style(caption_size=args.caption_size)
    crop_w, _ = crop_size(info)
    share = crop_w / info.width

    print(f"[1/4] following the face in {duration:.1f} s", file=sys.stderr)
    face_top = None
    if args.no_track or share >= 0.999:
        centres = np.full(max(1, round(duration * info.fps)), 0.5)
        found = None
    else:
        times, xs, tops = detect_centers(src, start, duration)
        centres = smooth_path(times, xs, share, info.fps, duration)
        found = float((~np.isnan(xs)).mean()) if len(xs) else 0.0
        if np.any(~np.isnan(tops)):
            # The face's top in output pixels: the crop keeps the full source height (9:16 from 16:9).
            _, crop_h = crop_size(info)
            face_top = float(np.nanpercentile(tops, 10)) * info.height * 1920 / crop_h

    plan = Plan(source=src, start=start, duration=duration, probe=info, centres=centres)
    line_h = round(style.caption_size * 1.25 * args.lines + 28)
    raw_lines, words = [], []
    if not args.no_captions:
        print("[2/4] captions", file=sys.stderr)
        if args.srt:
            raw_lines = read_srt(args.srt, start, duration)
        else:
            words = transcribe(src, start, duration, model=args.model, language=args.language)

    # The font follows the script being written: Yu Gothic for Japanese, Nirmala UI for Hindi...
    sample = " ".join([l.text for l in raw_lines] + [w.text for w in words] + [args.title or ""])
    script = detect_script(sample, args.language)
    font_path = find_font(args.font, script)
    if font_path:
        style.font_name = load_font(font_path, 20).getname()[0]
    measure = TextMeasure(font_path, style.caption_size)

    if not args.no_captions:
        slot = caption_slot(args.platforms, line_h)
        max_w = slot.width - 40
        if args.srt:
            lines = fit_lines(raw_lines, measure, max_w, args.lines)
        else:
            lines = group_words(words, measure, max_w, max_lines=args.lines)
        plan.captions, plan.caption_slot = lines, slot
    if args.title:
        t_measure = TextMeasure(font_path, style.title_size)
        raw = args.title.replace("\\n", "\n")
        probe_slot = title_slot(args.platforms, style.title_size * 2.6)
        title_lines = []
        for part in raw.split("\n"):
            title_lines += t_measure.wrap(part, probe_slot.width - 20)
        plan.title_lines = title_lines[:3]
        plan.title_slot = title_slot(args.platforms, style.title_size * 1.25 * len(plan.title_lines) + 20)

    print(f"[3/4] rendering {out.name}", file=sys.stderr)
    info_render = render(plan, style, out)
    srt_path = out.with_suffix(".srt")
    if plan.captions:
        write_srt(plan.captions, srt_path)

    print("[4/4] checking the result", file=sys.stderr)
    report = {"output": str(out), "duration": round(duration, 2), "face_found_share": found,
              "crop": info_render["crop"], "captions": len(plan.captions),
              "script": script, "font": style.font_name}
    if plan.caption_slot:
        widest = max((measure.width(row) for l in plan.captions for row in l.text.split("\n")), default=0) + 28
        s = plan.caption_slot
        box = Box(s.centre - widest / 2, s.top, s.centre + widest / 2, s.bottom)
        report["caption_box"] = [round(box.left), round(box.top), round(box.right - box.left), round(box.bottom - box.top)]
        report["caption_safe"] = check_box(box, platforms=args.platforms)
    if plan.title_slot:
        s = plan.title_slot
        report["title_safe"] = check_box(Box(s.left, s.top, s.right, s.bottom), platforms=args.platforms)
        if face_top is not None:
            report["title_covers_face"] = bool(s.bottom > face_top)
            if s.bottom > face_top:
                print(f"note: the title reaches y {s.bottom:.0f}, below the top of the face (y {face_top:.0f}); "
                      "a shorter title or one line may keep the face clear", file=sys.stderr)
    if info.has_audio:
        report["loudness"] = {"source": info_render["source_loudness"], "output": float(loudness(out)["input_i"])}
    report_path = out.with_suffix(".report.json")
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        report = run(args)
    except (ValueError, RuntimeError, OSError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2, ensure_ascii=False))
    unsafe = [k for k, v in {**report.get("caption_safe", {}), **report.get("title_safe", {})}.items() if v]
    return 1 if unsafe else 0


if __name__ == "__main__":
    raise SystemExit(main())
