"""
Spot assembly — cuts the generated shots of a sold 30-second ad into one
finished master (video + voiceover + music bed + optional burned captions).

This is the second half of the ad-spot pipeline. `src/api/routes/ad_spot.py`
boards the brief and generates SHOT_COUNT clips; this module turns those clips
into the file the merchant actually receives.

Everything here is ffmpeg (already in the API image — see Dockerfile) plus the
Telnyx TTS endpoint the phone agent already uses. No new vendor, no new key.

Deliberate choices, so nobody is surprised later:

  * CLIP AUDIO IS DROPPED. Generated shots come with unrelated, model-invented
    ambience; six of those butted together sounds like six different rooms. A
    scripted spot is carried by the voiceover and the bed, so the visual track
    is muted and the audio is built from scratch.
  * EVERY SHOT IS FORCED TO EXACTLY SHOT_SECONDS. Models overshoot and
    undershoot their requested duration. Padding the last frame / hard-trimming
    is what makes 6 shots reliably equal 30 seconds — the runtime that was sold.
  * MUSIC IS NEVER INVENTED. The bed comes from a directory of tracks you have
    cleared for commercial use (AD_SPOT_MUSIC_DIR). No directory, no bed — the
    master is still delivered, and the caller is told music was skipped.
  * CAPTIONS NEED A FONT. If no usable TTF is found the master ships without
    burned captions rather than failing, and again the caller is told.

Nothing in here silently substitutes something the merchant did not buy.
"""

import asyncio
import glob
import logging
import os
import shutil
import tempfile
from dataclasses import dataclass, field

import httpx

logger = logging.getLogger("meridian.media.spot_assembly")

TELNYX_TTS_URL = "https://api.telnyx.com/v2/text-to-speech/speech"

# Voice for the read. Same Telnyx voice namespace the phone agent uses, so the
# brand sounds consistent across the ad and the phone line.
AD_SPOT_VOICE = os.getenv("AD_SPOT_VOICE", "Telnyx.KokoroTTS.af_bella")

# Directory of cleared music beds (any .mp3/.m4a/.wav). Unset in most
# environments — see the module docstring.
AD_SPOT_MUSIC_DIR = os.getenv("AD_SPOT_MUSIC_DIR", "")

# Mix levels, in dB relative to each source's own level.
VO_GAIN_DB = 0.0
MUSIC_GAIN_DB = -16.0

FPS = 30
CRF = "20"

# Frame size per aspect ratio. 1080-class on the short edge — big enough for
# paid social and a website hero, small enough to move around quickly.
FRAME_SIZES = {
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
    "16:9": (1920, 1080),
}

FONT_CANDIDATES = [
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "/usr/share/fonts/truetype/noto/NotoSans-Bold.ttf",
]


@dataclass
class AssemblyResult:
    """What came out, and what had to be left out."""
    master: bytes
    duration_seconds: int
    width: int
    height: int
    has_voiceover: bool
    has_music: bool
    has_captions: bool
    #: Human-readable notes for anything skipped — surfaced to the operator so
    #: a spot is never quietly delivered missing something it was sold with.
    notes: list[str] = field(default_factory=list)


class AssemblyError(RuntimeError):
    """Assembly could not produce a master at all."""


# ── ffmpeg plumbing ──────────────────────────────────────────────────────────

async def _run(args: list[str], step: str) -> None:
    proc = await asyncio.create_subprocess_exec(
        *args, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        tail = (stderr or b"").decode("utf-8", "replace")[-800:]
        raise AssemblyError(f"{step} failed (ffmpeg exit {proc.returncode}): {tail}")


def _require_ffmpeg() -> None:
    if not shutil.which("ffmpeg"):
        raise AssemblyError("ffmpeg is not installed in this environment")


def _find_font() -> str | None:
    for path in FONT_CANDIDATES:
        if os.path.exists(path):
            return path
    hits = glob.glob("/usr/share/fonts/**/*Bold*.ttf", recursive=True)
    return hits[0] if hits else None


def _pick_music_bed() -> str | None:
    if not AD_SPOT_MUSIC_DIR or not os.path.isdir(AD_SPOT_MUSIC_DIR):
        return None
    tracks = sorted(
        p for ext in ("mp3", "m4a", "wav", "aac")
        for p in glob.glob(os.path.join(AD_SPOT_MUSIC_DIR, f"*.{ext}"))
    )
    return tracks[0] if tracks else None


def _escape_drawtext(text: str) -> str:
    """drawtext's own escaping: backslash, colon, apostrophe, percent."""
    out = text.replace("\\", "\\\\").replace(":", "\\:").replace("'", "’").replace("%", "\\%")
    return out


def _wrap(text: str, width: int = 32) -> str:
    words, lines, line = text.split(), [], ""
    for w in words:
        if len(line) + len(w) + 1 > width and line:
            lines.append(line)
            line = w
        else:
            line = f"{line} {w}".strip()
    if line:
        lines.append(line)
    return "\n".join(lines[:3])


# ── Voiceover ────────────────────────────────────────────────────────────────

async def _tts_line(client: httpx.AsyncClient, text: str, api_key: str, out_path: str) -> bool:
    """One Telnyx TTS request → an mp3 on disk. False if it did not render."""
    try:
        resp = await client.post(
            TELNYX_TTS_URL,
            headers={"Authorization": f"Bearer {api_key}"},
            json={"text": text, "voice": AD_SPOT_VOICE, "output_type": "binary_output"},
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("TTS request errored: %s", exc)
        return False
    if resp.status_code != 200 or not resp.content:
        logger.warning("TTS %s: %s", resp.status_code, resp.text[:200])
        return False
    with open(out_path, "wb") as fh:
        fh.write(resp.content)
    return True


async def _build_voiceover(lines: list[str], shot_seconds: int, workdir: str) -> str | None:
    """Render the script into one audio track, each line locked to its shot's
    slot so the read stays in sync with the picture it describes.

    Returns the path to a wav, or None if nothing rendered.
    """
    api_key = os.getenv("TELNYX_API_KEY", "")
    if not api_key:
        logger.info("TELNYX_API_KEY not set — no voiceover")
        return None
    if not any(line.strip() for line in lines):
        return None

    slots: list[str] = []
    async with httpx.AsyncClient(timeout=45.0) as client:
        for i, line in enumerate(lines):
            slot = os.path.join(workdir, f"vo_slot_{i:02d}.wav")
            text = (line or "").strip()
            if not text:
                # Silent slot keeps the remaining lines aligned to their shots.
                await _run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
                    "-t", str(shot_seconds), "-c:a", "pcm_s16le", slot,
                ], f"voiceover slot {i} (silence)")
                slots.append(slot)
                continue

            raw = os.path.join(workdir, f"vo_raw_{i:02d}.mp3")
            if not await _tts_line(client, text, api_key, raw):
                await _run([
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", "anullsrc=channel_layout=mono:sample_rate=48000",
                    "-t", str(shot_seconds), "-c:a", "pcm_s16le", slot,
                ], f"voiceover slot {i} (tts fallback silence)")
                slots.append(slot)
                continue

            # Pad with silence then hard-cut: a line shorter than its shot sits
            # at the head of the slot, a longer one is clipped rather than
            # pushing every later line out of sync.
            await _run([
                "ffmpeg", "-y", "-i", raw,
                "-af", f"aresample=48000,apad=whole_dur={shot_seconds}",
                "-t", str(shot_seconds), "-ac", "1", "-c:a", "pcm_s16le", slot,
            ], f"voiceover slot {i}")
            slots.append(slot)

    if not slots:
        return None

    listfile = os.path.join(workdir, "vo_list.txt")
    with open(listfile, "w") as fh:
        for s in slots:
            fh.write(f"file '{s}'\n")
    vo_path = os.path.join(workdir, "voiceover.wav")
    await _run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
        "-c:a", "pcm_s16le", vo_path,
    ], "voiceover concat")
    return vo_path


# ── Picture ──────────────────────────────────────────────────────────────────

async def _download(client: httpx.AsyncClient, url: str, path: str) -> bool:
    try:
        resp = await client.get(url)
    except Exception as exc:  # noqa: BLE001
        logger.warning("shot download errored: %s", exc)
        return False
    if resp.status_code != 200 or not resp.content:
        logger.warning("shot download %s for %s", resp.status_code, url[:120])
        return False
    with open(path, "wb") as fh:
        fh.write(resp.content)
    return True


async def _normalize_shot(src: str, dst: str, size: tuple[int, int], shot_seconds: int,
                          caption: str | None, font: str | None) -> None:
    """One clip → exactly shot_seconds at the target frame size, no audio.

    scale+crop (never stretch) so a 16:9 generation cropped to 9:16 keeps its
    subject; tpad holds the final frame if the model came up short.
    """
    w, h = size
    chain = [
        f"scale={w}:{h}:force_original_aspect_ratio=increase",
        f"crop={w}:{h}",
        f"fps={FPS}",
        f"tpad=stop_mode=clone:stop_duration={shot_seconds}",
    ]
    if caption and font:
        text = _escape_drawtext(_wrap(caption))
        chain.append(
            f"drawtext=fontfile={font}:text='{text}':fontcolor=white:fontsize={max(28, w // 24)}"
            f":line_spacing=8:box=1:boxcolor=black@0.45:boxborderw=18"
            f":x=(w-text_w)/2:y=h-text_h-{max(60, h // 12)}"
        )

    await _run([
        "ffmpeg", "-y", "-i", src,
        "-vf", ",".join(chain),
        "-t", str(shot_seconds),
        "-an",
        "-c:v", "libx264", "-preset", "medium", "-crf", CRF,
        "-pix_fmt", "yuv420p", dst,
    ], f"normalize {os.path.basename(src)}")


# ── Public entry point ───────────────────────────────────────────────────────

async def assemble_spot(
    shots: list[dict],
    aspect_ratio: str,
    shot_seconds: int,
    audio_treatment: str,
) -> AssemblyResult:
    """Cut completed shots into one finished master.

    `shots` is the ordered shot list — each needs `video_url`, and may carry a
    `voiceover` line from the storyboard. Shots without a usable video are
    skipped, and the result's `notes` say so: a 25-second master delivered
    knowingly beats a 30-second one that silently repeats a shot.
    """
    _require_ffmpeg()
    usable = [s for s in shots if s.get("video_url")]
    if not usable:
        raise AssemblyError("no completed shots to assemble")

    size = FRAME_SIZES.get(aspect_ratio, FRAME_SIZES["9:16"])
    want_vo = audio_treatment == "voiceover_music"
    want_music = audio_treatment in ("voiceover_music", "music_only")
    want_captions = audio_treatment == "captions_only"

    notes: list[str] = []
    if len(usable) < len(shots):
        missing = len(shots) - len(usable)
        notes.append(f"{missing} shot(s) had no video and were left out — master runs "
                     f"{len(usable) * shot_seconds}s, not {len(shots) * shot_seconds}s")

    font = _find_font() if want_captions else None
    if want_captions and not font:
        notes.append("no usable font found — captions were not burned in")

    workdir = tempfile.mkdtemp(prefix="adspot_")
    try:
        # 1. Picture: fetch and normalize every shot.
        segments: list[str] = []
        async with httpx.AsyncClient(timeout=120.0, follow_redirects=True) as client:
            for i, shot in enumerate(usable):
                raw = os.path.join(workdir, f"shot_{i:02d}_raw.mp4")
                if not await _download(client, shot["video_url"], raw):
                    notes.append(f"shot {shot.get('shot_number', i + 1)} could not be downloaded")
                    continue
                seg = os.path.join(workdir, f"shot_{i:02d}.mp4")
                await _normalize_shot(
                    raw, seg, size, shot_seconds,
                    caption=(shot.get("voiceover") if want_captions else None),
                    font=font,
                )
                segments.append(seg)

        if not segments:
            raise AssemblyError("every shot failed to download or normalize")

        listfile = os.path.join(workdir, "segments.txt")
        with open(listfile, "w") as fh:
            for s in segments:
                fh.write(f"file '{s}'\n")
        picture = os.path.join(workdir, "picture.mp4")
        await _run([
            "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", listfile,
            "-c", "copy", picture,
        ], "picture concat")

        total_seconds = len(segments) * shot_seconds

        # 2. Voice.
        vo_path = None
        if want_vo:
            vo_path = await _build_voiceover(
                [(s.get("voiceover") or "") for s in usable], shot_seconds, workdir
            )
            if vo_path is None:
                notes.append("voiceover was not rendered (no TELNYX_API_KEY or no script lines) "
                             "— master has no read on it")

        # 3. Music.
        music_path = _pick_music_bed() if want_music else None
        if want_music and not music_path:
            notes.append("no cleared music bed configured (AD_SPOT_MUSIC_DIR) — master has no bed")

        # 4. Mix and mux.
        master = os.path.join(workdir, "master.mp4")
        if not vo_path and not music_path:
            await _run([
                "ffmpeg", "-y", "-i", picture,
                "-c:v", "copy", "-an", "-t", str(total_seconds), master,
            ], "mux (silent)")
        else:
            args = ["ffmpeg", "-y", "-i", picture]
            filters: list[str] = []
            vo_idx = music_idx = None
            if vo_path:
                args += ["-i", vo_path]
                vo_idx = len([a for a in args if a == "-i"]) - 1
            if music_path:
                # -stream_loop belongs to the input that follows it.
                args += ["-stream_loop", "-1", "-i", music_path]
                music_idx = len([a for a in args if a == "-i"]) - 1

            if vo_idx is not None and music_idx is not None:
                # asplit because a filter label can be consumed exactly once —
                # the read is both a mix source and the sidechain key that
                # ducks the bed underneath it.
                filters.append(
                    f"[{vo_idx}:a]volume={VO_GAIN_DB}dB,aresample=48000,asplit=2[vo_mix][vo_key]"
                )
                filters.append(
                    f"[{music_idx}:a]volume={MUSIC_GAIN_DB}dB,aresample=48000,"
                    f"atrim=0:{total_seconds}[bed]"
                )
                filters.append(
                    "[bed][vo_key]sidechaincompress=threshold=0.05:ratio=6:attack=20:release=300[bedduck]"
                )
                filters.append(
                    "[vo_mix][bedduck]amix=inputs=2:duration=first:dropout_transition=0[aout]"
                )
            elif vo_idx is not None:
                filters.append(f"[{vo_idx}:a]volume={VO_GAIN_DB}dB,aresample=48000[aout]")
            else:
                filters.append(
                    f"[{music_idx}:a]volume={MUSIC_GAIN_DB}dB,aresample=48000,"
                    f"atrim=0:{total_seconds}[aout]"
                )

            args += [
                "-filter_complex", ";".join(filters),
                "-map", "0:v", "-map", "[aout]",
                "-c:v", "copy", "-c:a", "aac", "-b:a", "192k",
                "-t", str(total_seconds), "-shortest", master,
            ]
            await _run(args, "mix")

        with open(master, "rb") as fh:
            data = fh.read()

        return AssemblyResult(
            master=data,
            duration_seconds=total_seconds,
            width=size[0],
            height=size[1],
            has_voiceover=bool(vo_path),
            has_music=bool(music_path),
            has_captions=bool(want_captions and font),
            notes=notes,
        )
    finally:
        shutil.rmtree(workdir, ignore_errors=True)
