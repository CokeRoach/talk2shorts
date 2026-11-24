"""Find a caption font that has the script being written, and measure text in it."""

from __future__ import annotations

import os
import sys
from pathlib import Path

from PIL import ImageFont

# Bold faces first; each list covers Latin, Hangul, kana, Han and Cyrillic between them.
CANDIDATES = {
    "win32": ["malgunbd.ttf", "malgun.ttf", "YuGothB.ttc", "msyhbd.ttc", "arialbd.ttf"],
    "darwin": ["AppleSDGothicNeo.ttc", "Hiragino Sans GB.ttc", "Arial Bold.ttf"],
    "linux": ["NotoSansCJK-Bold.ttc", "NotoSansCJKkr-Bold.otf", "NotoSans-Bold.ttf", "DejaVuSans-Bold.ttf"],
}
FONT_DIRS = {
    "win32": [Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts",
              Path(os.environ.get("LOCALAPPDATA", "")) / "Microsoft/Windows/Fonts"],
    "darwin": [Path("/System/Library/Fonts"), Path("/Library/Fonts"), Path.home() / "Library/Fonts"],
    "linux": [Path("/usr/share/fonts"), Path("/usr/local/share/fonts"), Path.home() / ".fonts"],
}


def find_font(explicit: str | None = None) -> Path | None:
    if explicit:
        path = Path(explicit)
        if not path.exists():
            raise FileNotFoundError(f"font not found: {explicit}")
        return path
    platform = "win32" if sys.platform.startswith("win") else "darwin" if sys.platform == "darwin" else "linux"
    for name in CANDIDATES[platform]:
        for root in FONT_DIRS[platform]:
            if not root.exists():
                continue
            direct = root / name
            if direct.exists():
                return direct
            found = next(root.rglob(name), None)
            if found:
                return found
    return None


class TextMeasure:
    """Pixel width of a line in the caption font, or an estimate when no font file is found."""

    def __init__(self, font_path: Path | None, size: int):
        self.size = size
        self.font = ImageFont.truetype(str(font_path), size) if font_path else None

    def width(self, text: str) -> float:
        if self.font is not None:
            return self.font.getlength(text)
        return sum(self.size * (1.0 if ord(ch) > 0x2E80 else 0.56) for ch in text)

    def balance(self, text: str, max_width: float, max_lines: int = 2) -> list[str]:
        """Wrap into at most ``max_lines`` lines of similar width (a short last line reads badly)."""
        greedy = self.wrap(text, max_width)
        if len(greedy) != 2 or max_lines < 2:
            return greedy
        spaced = " " in text.strip()
        tokens = text.split(" ") if spaced else list(text)
        sep = " " if spaced else ""
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
        """Break at spaces where there are any, else between characters (CJK)."""
        tokens = text.split(" ") if " " in text.strip() else list(text)
        sep = " " if " " in text.strip() else ""
        lines, current = [], ""
        for tok in tokens:
            trial = f"{current}{sep}{tok}" if current else tok
            if current and self.width(trial) > max_width:
                lines.append(current)
                current = tok
            else:
                current = trial
        if current:
            lines.append(current)
        return lines
