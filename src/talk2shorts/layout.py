"""Where captions and the title go: inside the safe area of every chosen platform."""

from __future__ import annotations

from dataclasses import dataclass

from shorts_safezone import ZONES, scaled_bands

W, H = 1080, 1920


@dataclass(frozen=True)
class Slot:
    left: float
    right: float
    top: float
    bottom: float

    @property
    def width(self) -> float:
        return self.right - self.left

    @property
    def centre(self) -> float:
        return (self.left + self.right) / 2


def clear_x(platforms: tuple[str, ...], top: float, bottom: float) -> tuple[float, float]:
    """The x range clear on every platform for a box spanning ``top``-``bottom``."""
    left, right = 0.0, float(W)
    for key in platforms:
        bands = scaled_bands(ZONES[key], W, H)
        if top < bands[0][0] or bottom > bands[-1][1]:
            return 0.0, 0.0
        for t, b, l, r in bands:
            if bottom <= t or top >= b:
                continue
            left, right = max(left, l), min(right, r)
    return left, right


def caption_slot(platforms: tuple[str, ...], height: float, margin: float = 12) -> Slot:
    """The lowest box of ``height`` px that is clear everywhere, as wide as it can be there.

    Captions sit as low as the zones allow (close to where viewers expect them), but never
    lower than the shared safe bottom. On TikTok the lower part is narrower because of the
    buttons on the right, so the slot moves up while that buys more than a fifth of width.
    """
    bottom_limit = min(scaled_bands(ZONES[k], W, H)[-1][1] for k in platforms) - margin
    best = None
    y = bottom_limit
    while y - height > H * 0.45:
        left, right = clear_x(platforms, y - height, y)
        if right - left > 0:
            cand = Slot(left + margin, right - margin, y - height, y)
            if best is None or cand.width > best.width * 1.2:
                best = cand
        y -= 10
    if best is None:
        raise ValueError("no caption position is clear on every chosen platform")
    return best


def title_slot(platforms: tuple[str, ...], height: float, margin: float = 16) -> Slot:
    top = max(scaled_bands(ZONES[k], W, H)[0][0] for k in platforms) + margin
    left, right = clear_x(platforms, top, top + height)
    if right - left <= 0:
        raise ValueError("no title position is clear on every chosen platform")
    return Slot(left + margin, right - margin, top, top + height)
