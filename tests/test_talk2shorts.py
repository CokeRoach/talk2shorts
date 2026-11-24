import json
import shutil
import subprocess

import numpy as np
import pytest
from shorts_safezone import Box, check_box

from talk2shorts.captions import Line, Word, fit_lines, group_words, read_srt, write_srt
from talk2shorts.cli import main
from talk2shorts.fonts import TextMeasure
from talk2shorts.layout import H, caption_slot, title_slot
from talk2shorts.media import Probe, parse_time, probe
from talk2shorts.render import crop_size
from talk2shorts.track import smooth_path

ALL = ("youtube", "tiktok", "reels")
EST = TextMeasure(None, 58)  # width estimate, no font file needed


@pytest.mark.parametrize("text, seconds", [("83", 83), ("83.5", 83.5), ("1:23", 83), ("01:23.5", 83.5), ("0:01:23", 83)])
def test_parse_time(text, seconds):
    assert parse_time(text) == seconds


@pytest.mark.parametrize("text", ["", "1::2", "a:b", "1:2:3:4"])
def test_parse_time_rejects(text):
    with pytest.raises(ValueError):
        parse_time(text)


def test_read_srt_shifts_and_clips(tmp_path):
    srt = tmp_path / "in.srt"
    srt.write_text("1\n00:00:09,000 --> 00:00:11,000\nbefore and in\n\n"
                   "2\n00:00:12,500 --> 00:00:14,000\n<i>inside</i>\n\n"
                   "3\n00:00:30,000 --> 00:00:31,000\nafter\n", encoding="utf-8")
    assert read_srt(srt, start=10, duration=10) == [Line(0, 1, "before and in"), Line(2.5, 4, "inside")]


def test_write_then_read_srt(tmp_path):
    lines = [Line(0.0, 1.25, "one"), Line(1.25, 3.5, "two\nlines")]
    write_srt(lines, tmp_path / "out.srt")
    assert read_srt(tmp_path / "out.srt") == [Line(0.0, 1.25, "one"), Line(1.25, 3.5, "two lines")]


def words(text, start=0.0, step=0.3, pause_after=()):
    out, t = [], start
    for i, w in enumerate(text.split()):
        out.append(Word(t, t + step - 0.05, (" " if i else "") + w))
        t += step + (0.8 if i in pause_after else 0)
    return out


def test_captions_break_at_pauses_and_keep_short_sentences_on_screen():
    lines = group_words(words("Hello there. This is a test of captions", pause_after=(5,)), EST, 600)
    texts = [l.text.replace("\n", " ") for l in lines]
    # "Hello there." alone would flash for half a second, so it shares a caption with the next
    # sentence; the long pause after "test" still starts a new caption.
    assert texts == ["Hello there. This is a test", "of captions"]
    assert all(len(l.text.split("\n")) <= 2 for l in lines)


def test_captions_break_at_a_sentence_end_when_both_last():
    lines = group_words(words("This first sentence runs on for a while. Then a second one follows here."), EST, 900)
    assert lines[0].text.replace("\n", " ") == "This first sentence runs on for a while."


def test_captions_never_leave_a_lone_word():
    ws = words("experiments are you conducting right now? Well this mission has been great.")
    lines = group_words(ws, TextMeasure(None, 58), 380)
    assert all(len(l.text.split()) > 1 for l in lines), [l.text for l in lines]


def test_captions_do_not_overlap_and_last_long_enough():
    lines = group_words(words(" ".join(["word"] * 40)), EST, 500)
    for a, b in zip(lines, lines[1:]):
        assert a.end <= b.start + 1e-9
    assert all(l.end - l.start >= 0.6 for l in lines)


def test_balance_prefers_even_lines():
    rows = EST.balance("this is a fairly long caption that needs two lines", 1100)
    assert len(rows) == 2
    assert abs(EST.width(rows[0]) - EST.width(rows[1])) < EST.size * 4


def test_fit_lines_splits_long_cues_by_length():
    out = fit_lines([Line(0, 6, " ".join(["word"] * 30))], EST, 400, max_lines=2)
    assert len(out) > 1
    assert out[0].start == 0 and abs(out[-1].end - 6) < 1e-9
    assert all(len(l.text.split("\n")) <= 2 for l in out)


def test_fit_lines_splits_between_sentences():
    measure = TextMeasure(None, 58)
    out = fit_lines([Line(0, 4, "우주에서 사는 건 어떤 느낌일까요? 매일이 새로운 경험입니다")], measure, 560, 2)
    assert [l.text.replace("\n", " ") for l in out] == ["우주에서 사는 건 어떤 느낌일까요?", "매일이 새로운 경험입니다"]


@pytest.mark.parametrize("height", [100, 173])
def test_caption_slot_is_clear_on_every_platform(height):
    slot = caption_slot(ALL, height)
    box = Box(slot.left, slot.top, slot.right, slot.bottom)
    assert check_box(box) == {k: [] for k in ALL}
    assert slot.top > H * 0.45


def test_caption_slot_for_youtube_alone_is_wider():
    assert caption_slot(("youtube",), 100).width > caption_slot(ALL, 100).width


def test_title_slot_is_clear():
    s = title_slot(ALL, 200)
    assert check_box(Box(s.left, s.top, s.right, s.bottom)) == {k: [] for k in ALL}


def test_crop_size_is_9_16_and_even():
    assert crop_size(Probe(1920, 1080, 30, 10, True)) == (606, 1080)
    assert crop_size(Probe(1280, 720, 30, 10, True)) == (404, 720)
    assert crop_size(Probe(1080, 1920, 30, 10, True)) == (1080, 1920)


def test_no_face_keeps_the_crop_centred():
    path = smooth_path(np.arange(10) * 0.2, np.full(10, np.nan), 0.3, 30, 2)
    assert np.allclose(path, 0.5)


def test_small_moves_do_not_shake_the_crop():
    rng = np.random.default_rng(1)
    xs = 0.5 + rng.uniform(-0.01, 0.01, 50)
    path = smooth_path(np.arange(50) * 0.2, xs, 0.3, 30, 10)
    assert np.ptp(path) < 0.01


def test_crop_follows_a_real_move_and_stays_inside():
    xs = np.r_[np.full(25, 0.3), np.full(25, 0.7)]
    path = smooth_path(np.arange(50) * 0.2, xs, 0.3, 30, 10)
    assert path[0] < 0.35 and path[-1] > 0.65
    assert path.min() >= 0.15 and path.max() <= 0.85


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_end_to_end_with_srt(tmp_path, capsys):
    src = tmp_path / "talk.mp4"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "testsrc2=s=1280x720:r=30:d=8",
                    "-f", "lavfi", "-i", "sine=frequency=440:sample_rate=48000:d=8", "-af", "volume=0.05",
                    "-pix_fmt", "yuv420p", "-shortest", str(src)], check=True)
    srt = tmp_path / "talk.srt"
    srt.write_text("1\n00:00:02,000 --> 00:00:04,000\nFirst caption line\n\n"
                   "2\n00:00:04,000 --> 00:00:06,500\nAnd a second one\n", encoding="utf-8")
    out = tmp_path / "short.mp4"
    code = main([str(src), "--start", "1", "--end", "7", "--srt", str(srt), "--no-track",
                 "--title", "A test title", "-o", str(out)])
    report = json.loads(capsys.readouterr().out)
    assert code == 0
    p = probe(out)
    assert (p.width, p.height) == (1080, 1920)
    assert abs(p.duration - 6) < 0.2
    assert report["captions"] == 2
    assert report["caption_safe"] == {k: [] for k in ALL}
    assert report["title_safe"] == {k: [] for k in ALL}
    assert abs(report["loudness"]["output"] - (-14)) < 1.0
    assert out.with_suffix(".srt").exists() and out.with_suffix(".report.json").exists()
