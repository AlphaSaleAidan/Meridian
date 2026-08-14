"""Spot assembly — the ffmpeg cut that turns generated shots into the master.

These run real ffmpeg over synthetic clips served from a local HTTP server,
because the failure modes that matter here are not type errors: a filter graph
that ffmpeg rejects, a master that is not the runtime we sold, a crop that
squashes the picture, or an audio mix that silently drops the voiceover.

Slow-ish (a few seconds of encoding) and skipped where ffmpeg is unavailable.

Run: python -m pytest tests/media/test_spot_assembly.py -v
"""
import functools
import http.server
import json
import shutil
import subprocess
import sys
import tempfile
import threading
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from src.media import spot_assembly as sa  # noqa: E402

pytestmark = pytest.mark.skipif(
    not shutil.which("ffmpeg") or not shutil.which("ffprobe"),
    reason="ffmpeg/ffprobe not installed",
)

SHOT_SECONDS = 5


def _make_clip(path, i, seconds=6):
    """Deliberately 6s and 16:9 — the pipeline must trim to the shot length and
    crop to the sold aspect, and models really do overshoot their duration."""
    subprocess.run([
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        f"testsrc=size=640x360:rate=30:duration={seconds}",
        "-f", "lavfi", "-i", f"sine=frequency={300 + i * 60}:duration={seconds}",
        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-c:a", "aac", "-shortest", str(path),
    ], check=True, capture_output=True)


def _probe(path):
    out = subprocess.run(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_format", "-show_streams", str(path)],
        check=True, capture_output=True, text=True,
    ).stdout
    d = json.loads(out)
    video = next(s for s in d["streams"] if s["codec_type"] == "video")
    audio = next((s for s in d["streams"] if s["codec_type"] == "audio"), None)
    return {
        "duration": round(float(d["format"]["duration"]), 1),
        "size": (video["width"], video["height"]),
        "has_audio": audio is not None,
    }


@pytest.fixture(scope="module")
def served_shots():
    """Two clips on a local HTTP server, shaped like completed shot rows."""
    work = Path(tempfile.mkdtemp(prefix="adspot_test_"))
    for i in range(2):
        _make_clip(work / f"shot{i}.mp4", i)

    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(work))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    base = f"http://127.0.0.1:{httpd.server_address[1]}"

    shots = [
        {"shot_number": i + 1, "video_url": f"{base}/shot{i}.mp4",
         "voiceover": f"Line {i + 1}: come in this week and taste the difference."}
        for i in range(2)
    ]
    try:
        yield work, shots
    finally:
        httpd.shutdown()
        shutil.rmtree(work, ignore_errors=True)


def _write(work, name, data):
    path = work / name
    path.write_bytes(data)
    return path


async def test_master_runtime_is_shots_times_shot_length(served_shots):
    """The sold runtime is a promise: 2 shots × 5s must be exactly 10s, even
    though every source clip is 6s long."""
    work, shots = served_shots
    result = await sa.assemble_spot(shots, "9:16", SHOT_SECONDS, "music_only")
    probe = _probe(_write(work, "m_runtime.mp4", result.master))

    assert probe["duration"] == 10.0
    assert result.duration_seconds == 10


@pytest.mark.parametrize("aspect,expected", [
    ("9:16", (1080, 1920)),
    ("1:1", (1080, 1080)),
    ("16:9", (1920, 1080)),
])
async def test_every_placement_crops_to_its_frame(served_shots, aspect, expected):
    """Scale-and-crop, never stretch — a 16:9 source in a 9:16 ad."""
    work, shots = served_shots
    result = await sa.assemble_spot(shots, aspect, SHOT_SECONDS, "music_only")
    probe = _probe(_write(work, f"m_{aspect.replace(':', 'x')}.mp4", result.master))

    assert probe["size"] == expected
    assert (result.width, result.height) == expected


async def test_clip_audio_is_dropped(served_shots):
    """Source clips carry model-invented ambience; six of those butted together
    sound like six rooms. With no VO and no bed, the master is silent."""
    work, shots = served_shots
    result = await sa.assemble_spot(shots, "9:16", SHOT_SECONDS, "music_only")

    assert _probe(_write(work, "m_silent.mp4", result.master))["has_audio"] is False


async def test_missing_music_is_reported_not_invented(served_shots):
    """No cleared bed configured → still delivers, and SAYS the bed is missing."""
    _, shots = served_shots
    result = await sa.assemble_spot(shots, "9:16", SHOT_SECONDS, "music_only")

    assert result.has_music is False
    assert any("music bed" in note for note in result.notes)


async def test_voiceover_and_bed_mix_into_one_track(served_shots, monkeypatch):
    """Exercises the real filter graph — asplit + sidechain duck + amix. A
    malformed graph fails here rather than on a merchant's paid spot."""
    work, shots = served_shots
    bed = work / "bed.mp3"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=220:duration=4",
                    "-c:a", "libmp3lame", str(bed)], check=True, capture_output=True)
    vo = work / "vo.wav"
    subprocess.run(["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=700:duration=10",
                    "-c:a", "pcm_s16le", str(vo)], check=True, capture_output=True)

    async def _fake_vo(_lines, _shot_seconds, _workdir):
        return str(vo)

    monkeypatch.setattr(sa, "_build_voiceover", _fake_vo)
    monkeypatch.setattr(sa, "_pick_music_bed", lambda: str(bed))

    result = await sa.assemble_spot(shots, "9:16", SHOT_SECONDS, "voiceover_music")
    probe = _probe(_write(work, "m_mixed.mp4", result.master))

    assert probe["has_audio"] is True
    # A 4-second bed under a 10-second spot must be looped, not left to run out.
    assert probe["duration"] == 10.0
    assert result.has_voiceover and result.has_music
    assert result.notes == []


async def test_captions_are_burned_when_a_font_exists(served_shots):
    _, shots = served_shots
    result = await sa.assemble_spot(shots, "9:16", SHOT_SECONDS, "captions_only")

    assert result.has_captions is (sa._find_font() is not None)


async def test_dropped_shots_shorten_the_master_and_say_so(served_shots):
    """A shot with no video is left out — a knowingly short master beats one
    that silently repeats a shot to pad the runtime."""
    _, shots = served_shots
    result = await sa.assemble_spot(
        shots + [{"shot_number": 3, "video_url": None}], "9:16", SHOT_SECONDS, "music_only"
    )

    assert result.duration_seconds == 10
    assert any("left out" in note for note in result.notes)


async def test_no_usable_shots_raises_rather_than_shipping_nothing(served_shots):
    with pytest.raises(sa.AssemblyError):
        await sa.assemble_spot([{"shot_number": 1}], "9:16", SHOT_SECONDS, "music_only")


def test_drawtext_input_is_escaped():
    """Captions come from LLM-written script lines — an unescaped colon or
    quote breaks the whole filter graph."""
    escaped = sa._escape_drawtext("Open 9:00 'til late — 50% off")

    assert "\\:" in escaped
    assert "\\%" in escaped
    assert "'" not in escaped
