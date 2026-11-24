"""Pick a caption font for the script being written, and measure and wrap text in it."""

from __future__ import annotations

import os
import sys
import unicodedata
from pathlib import Path

from PIL import ImageFont

# Bold faces for each script, most likely first. Han without kana or Hangul is read as Chinese.
FONTS = {
    "win32": {
        "ko": ["malgunbd.ttf", "malgun.ttf"],
        "ja": ["YuGothB.ttc", "meiryob.ttc", "msgothic.ttc"],
        "zh": ["msyhbd.ttc", "msyh.ttc", "simhei.ttf"],
        "hi": ["Nirmala.ttc", "NirmalaB.ttf", "Nirmala.ttf", "mangal.ttf"],
        "ar": ["segoeuib.ttf", "tahomabd.ttf", "arialbd.ttf"],
        "th": ["LeelaUIb.ttf", "LeelawUI.ttf", "tahomabd.ttf"],
        "latin": ["segoeuib.ttf", "arialbd.ttf", "malgunbd.ttf"],
    },
    "darwin": {
        "ko": ["AppleSDGothicNeo.ttc"],
        "ja": ["ヒラギノ角ゴシック W6.ttc", "Hiragino Sans GB.ttc"],
        "zh": ["PingFang.ttc", "Hiragino Sans GB.ttc"],
        "hi": ["Kohinoor.ttc", "DevanagariMT.ttc"],
        "ar": ["GeezaPro.ttc", "Arial Unicode.ttf"],
        "th": ["Thonburi.ttc", "Ayuthaya.ttf"],
        "latin": ["HelveticaNeue.ttc", "Arial Bold.ttf"],
    },
    "linux": {
        "ko": ["NotoSansCJK-Bold.ttc", "NotoSansKR-Bold.otf", "NanumGothicBold.ttf"],
        "ja": ["NotoSansCJK-Bold.ttc", "NotoSansJP-Bold.otf"],
        "zh": ["NotoSansCJK-Bold.ttc", "NotoSansSC-Bold.otf", "wqy-zenhei.ttc"],
        "hi": ["NotoSansDevanagari-Bold.ttf", "Lohit-Devanagari.ttf"],
        "ar": ["NotoSansArabic-Bold.ttf", "NotoNaskhArabic-Bold.ttf", "DejaVuSans-Bold.ttf"],
        "th": ["NotoSansThai-Bold.ttf", "Loma-Bold.ttf", "TlwgTypo-Bold.ttf"],
        "latin": ["NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf", "LiberationSans-Bold.ttf"],
    },
}
FONT_DIRS = {
    "win32": [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
              Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"],
    "darwin": [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"],
    "linux": [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"],
}
# Line starts that read badly: closing punctuation and small kana go with the character before.
NO_LINE_START = set("、。，．・：；？！）」』】〕〉》”’ぁぃぅぇぉっゃゅょゎァィゥェォッャュョヮー々,.!?)")


def platform() -> str:
    return "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "linux"


def detect_script(text: str, language: str | None = None) -> str:
    """The writing system most of ``text`` is in: ko, ja, zh, hi, ar, th or latin."""
    if language in ("ko", "ja", "zh", "hi", "ar", "th"):
        return language
    counts = dict.fromkeys(("hangul", "kana", "han", "hi", "ar", "th"), 0)
    for ch in text:
        o = ord(ch)
        if 0xAC00 <= o <= 0xD7A3 or 0x1100 <= o <= 0x11FF or 0x3130 <= o <= 0x318F:
            counts["hangul"] += 1
        elif 0x3040 <= o <= 0x30FF:
            counts["kana"] += 1
        elif 0x4E00 <= o <= 0x9FFF or 0x3400 <= o <= 0x4DBF:
            counts["han"] += 1
        elif 0x0900 <= o <= 0x097F:
            counts["hi"] += 1
        elif 0x0600 <= o <= 0x06FF or 0x0750 <= o <= 0x077F or 0xFB50 <= o <= 0xFEFF:
            counts["ar"] += 1
        elif 0x0E00 <= o <= 0x0E7F:
            counts["th"] += 1
    if counts["hangul"]:
        return "ko"
    if counts["kana"]:
        return "ja"
    best = max(("han", "hi", "ar", "th"), key=lambda k: counts[k])
    if counts[best] == 0:
        return "latin"
    return {"han": "zh"}.get(best, best)


def find_font(explicit: str | None = None, script: str = "ko") -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"font not found: {explicit}")
        return path
    plat = platform()
    for name in FONTS[plat].get(script, []) + FONTS[plat]["latin"]:
        for root in FONT_DIRS[plat]:
            if not root.exists():
                continue
            direct = root / name
            if direct.exists():
                return direct
            found = next(root.rglob(name), None)
            if found:
                return found
    return None


def graphemes(text: str) -> list[str]:
    """Characters with the marks that belong to them (Thai vowels and tones, Devanagari signs)."""
    out: list[str] = []
    for ch in text:
        joins = unicodedata.category(ch) in ("Mn", "Mc", "Me") or ch in "\u200d\u200c"
        if out and (joins or out[-1].endswith("\u200d")):
            out[-1] += ch
        else:
            out.append(ch)
    return out


def load_font(path: Path, size: int) -> ImageFont.FreeTypeFont:
    """The bold face of a font file; a collection (.ttc) holds several, so look for it."""
    if str(path).lower().endswith(".ttc"):
        for index in range(12):
            try:
                face = ImageFont.truetype(str(path), size, index=index)
            except OSError:
                break
            if "bold" in face.getname()[1].lower():
                return face
    return ImageFont.truetype(str(path), size)


class TextMeasure:
    """Pixel width of a line in the caption font, or an estimate when no font file is found."""

    def __init__(self, font_path: Path | None, size: int):
        self.size = size
        self.font = load_font(font_path, size) if font_path else None

    def width(self, text: str) -> float:
        if self.font is not None:
            return self.font.getlength(text)
        return sum(self.size * (1.0 if ord(ch) > 0x2E80 else 0.56) for ch in text)

    def _tokens(self, text: str) -> tuple[list[str], str]:
        """Words for spaced text, else characters with their marks; CJK closing marks stay attached."""
        if " " in text.strip():
            return text.split(" "), " "
        tokens: list[str] = []
        for g in graphemes(text):
            if tokens and g in NO_LINE_START:
                tokens[-1] += g
            else:
                tokens.append(g)
        return tokens, ""

    def balance(self, text: str, max_width: float, max_lines: int = 2) -> list[str]:
        """Wrap into at most ``max_lines`` lines of similar width (a short last line reads badly)."""
        greedy = self.wrap(text, max_width)
        if len(greedy) != 2 or max_lines < 2:
            return greedy
        tokens, sep = self._tokens(text)
        best, best_score = greedy, None
        for i in range(1, len(tokens)):
            a, b = sep.join(tokens[:i]), sep.join(tokens[i:])
            wa, wb = self.width(a), self.width(b)
            if max(wa, wb) > max_width:
                continue
            score = abs(wa - wb) - (self.size * 0.6 if a.rstrip()[-1:] in ",.?!、，。" else 0)
            if best_score is None or score < best_score:
                best, best_score = [a, b], score
        return best

    def wrap(self, text: str, max_width: float) -> list[str]:
        """Greedy wrap; a word too wide for one line (long Thai runs) is split between characters."""
        tokens, sep = self._tokens(text)
        lines, current = [], ""
        for tok in tokens:
            trial = f"{current}{sep}{tok}" if current else tok
            if not current or self.width(trial) <= max_width:
                current = trial
                if self.width(current) <= max_width:
                    continue
            else:
                lines.append(current)
                current = tok
            if sep and self.width(current) > max_width:
                pieces = self.wrap(current, max_width) if " " not in current else [current]
                lines.extend(pieces[:-1])
                current = pieces[-1]
        if current:
            lines.append(current)
        return lines
