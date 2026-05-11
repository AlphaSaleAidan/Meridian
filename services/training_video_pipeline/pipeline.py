"""
Meridian Training Video Generation Pipeline (100% Free / Open Source)

Produces professional animated screen-recording-style training videos:
  - Real screenshots of the Meridian dashboard (captured via Playwright)
  - Ken Burns zoom/pan animation on each screen
  - Crossfade transitions between screens
  - Semi-transparent text overlays showing key points
  - Neural TTS narration (edge-tts, free, no API key)
  - Branded title card + outro card

Usage:
  python pipeline.py --lesson 3.2 --portal canada
  python pipeline.py --module 1 --portal canada
  python pipeline.py --all --portal both
  python pipeline.py --all --dry-run

Prerequisites:
  pip install edge-tts Pillow python-dotenv
  apt install ffmpeg fonts-dejavu-core
  python capture.py   # One-time: grab dashboard screenshots
"""

import asyncio
import json
import logging
import os
import random
import subprocess
import textwrap
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("meridian.training_video_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

TTS_AVAILABLE = False
try:
    import edge_tts
    TTS_AVAILABLE = True
except ImportError:
    logger.warning("edge-tts not installed — run: pip install edge-tts")

PIL_AVAILABLE = False
try:
    from PIL import Image, ImageDraw, ImageFont
    PIL_AVAILABLE = True
except ImportError:
    logger.warning("Pillow not installed — run: pip install Pillow")

SUPABASE_AVAILABLE = False
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    pass

from capture import MODULE_SCREENS
from config import get_all_lessons, get_lesson, get_module_lessons

PIPELINE_ROOT = Path(__file__).parent
OUTPUT_ROOT = PIPELINE_ROOT / "output"
SCREENS_DIR = PIPELINE_ROOT / "assets" / "screens"
MEMORY_FILE = PIPELINE_ROOT / "style_memory.json"
DEERFLOW_ROOT = Path(os.getenv("DEERFLOW_WORKSPACE", PIPELINE_ROOT.parent / "deerflow"))

BRAND = {
    "bg": (10, 15, 13),
    "teal": (0, 212, 170),
    "white": (255, 255, 255),
    "muted": (107, 122, 116),
}

TTS_VOICE_CA = "en-CA-LiamNeural"
TTS_VOICE_US = "en-US-GuyNeural"

# Ken Burns patterns: (start_zoom, end_zoom, x_drift, y_drift)
ZOOM_PATTERNS = [
    (1.0, 1.15, 0, -30),   # Slow zoom in, drift up (overview)
    (1.15, 1.0, 0, 20),    # Slow zoom out, drift down
    (1.0, 1.12, -40, 0),   # Zoom in, drift left (scan sidebar)
    (1.0, 1.12, 40, 0),    # Zoom in, drift right (scan data)
    (1.05, 1.18, -20, -20),# Zoom into top-left (logo area)
    (1.08, 1.0, 30, 15),   # Zoom out from center-right
]


@dataclass
class SceneScript:
    number: int
    text: str
    key_point: str
    screen: str = ""
    tone: str = "Confident"


@dataclass
class VideoScript:
    lesson_id: str
    lesson_title: str
    module_name: str
    scenes: list[SceneScript] = field(default_factory=list)
    duration_target: int = 180


class TitleCardRenderer:
    """Renders title and outro cards with Pillow."""

    W, H = 1920, 1080

    def __init__(self):
        self._font_lg = self._load(48)
        self._font_md = self._load(32)
        self._font_sm = self._load(24)

    def _load(self, size):
        if not PIL_AVAILABLE:
            return None
        for p in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
        ]:
            if Path(p).exists():
                return ImageFont.truetype(p, size)
        return ImageFont.load_default()

    def title(self, module: str, lesson: str, out: str):
        if not PIL_AVAILABLE:
            return
        img = Image.new("RGB", (self.W, self.H), BRAND["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, self.W, 4], fill=BRAND["teal"])
        d.text((self.W // 2, 340), "MERIDIAN INTELLIGENCE", fill=BRAND["teal"], font=self._font_lg, anchor="mm")
        d.text((self.W // 2, 420), module.upper(), fill=BRAND["muted"], font=self._font_md, anchor="mm")
        d.text((self.W // 2, 540), textwrap.fill(lesson, 40), fill=BRAND["white"], font=self._font_lg, anchor="mm")
        d.rectangle([0, self.H - 4, self.W, self.H], fill=BRAND["teal"])
        img.save(out)

    def outro(self, out: str):
        if not PIL_AVAILABLE:
            return
        img = Image.new("RGB", (self.W, self.H), BRAND["bg"])
        d = ImageDraw.Draw(img)
        d.rectangle([0, 0, self.W, 4], fill=BRAND["teal"])
        d.text((self.W // 2, 400), "Lesson Complete", fill=BRAND["teal"], font=self._font_lg, anchor="mm")
        d.text((self.W // 2, 490), "Mark as complete below to track your progress.", fill=BRAND["muted"], font=self._font_md, anchor="mm")
        d.text((self.W // 2, 580), "MERIDIAN INTELLIGENCE", fill=BRAND["white"], font=self._font_sm, anchor="mm")
        d.rectangle([0, self.H - 4, self.W, self.H], fill=BRAND["teal"])
        img.save(out)


class AnimatedVideoGenerator:

    def __init__(self, portal: str = "canada"):
        self.portal = portal
        self.voice = TTS_VOICE_CA if portal == "canada" else TTS_VOICE_US
        self.cards = TitleCardRenderer()
        self.supabase = None
        if SUPABASE_AVAILABLE:
            url, key = os.getenv("SUPABASE_URL"), os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if url and key:
                self.supabase = create_client(url, key)

    async def generate(
        self, lesson_id: str, lesson_title: str, lesson_content: str,
        module_name: str, duration_target: int,
    ) -> str:
        logger.info("=" * 60)
        logger.info("[%s] %s — %s", lesson_id, lesson_title, module_name)
        logger.info("Target: %ds | Voice: %s | Portal: %s", duration_target, self.voice, self.portal)

        out = OUTPUT_ROOT / lesson_id.replace(".", "_")
        out.mkdir(parents=True, exist_ok=True)

        # 1. Script
        script = await self._script(lesson_id, lesson_title, lesson_content, module_name, duration_target)
        logger.info("Script: %d scenes", len(script.scenes))

        # 2. Audio (TTS)
        audio_paths = await self._tts(script, out)
        logger.info("Audio: %d clips generated", len(audio_paths))

        # 3. Animated screen segments (Ken Burns + text overlay)
        segments = self._animate_scenes(script, audio_paths, out)
        logger.info("Segments: %d animated clips", len(segments))

        # 4. Concatenate with crossfade transitions
        final = self._final_assembly(segments, lesson_id, out)
        logger.info("Final: %s", final)

        # 5. Upload + DB
        url = await self._upload(final, lesson_id)
        await self._update_db(lesson_id, url, duration_target)
        self._save_memory(lesson_id, lesson_title)

        logger.info("Done: %s", url)
        return url

    # ── Script ───────────────────────────────────────────────

    async def _script(self, lid, title, content, module, dur) -> VideoScript:
        currency = "CA$" if self.portal == "canada" else "$"

        # Determine which screens to use for this module
        mod_num = lid.split(".")[0]
        mod_key = f"module_{mod_num}"
        screens = MODULE_SCREENS.get(mod_key, ["overview", "insights", "revenue"])

        prompt = f"""Write a training video script for Meridian Intelligence sales reps.

MODULE: {module}
LESSON: {lid} — {title}
TARGET: {dur} seconds | CURRENCY: {currency}

SOURCE CONTENT:
{content}

Output valid JSON only:
{{
  "scenes": [
    {{"number": 1, "text": "Spoken narration (2-4 sentences)", "key_point": "Short bullet for screen overlay (max 80 chars)", "screen": "dashboard_page_name", "tone": "Confident"}}
  ]
}}

Available screen names: {', '.join(screens)}
- 5-8 scenes. Scene 1 = hook. Last scene = CTA.
- Assign each scene a screen name from the list above (the most relevant dashboard page).
- Use "you" throughout. All amounts in {currency}.
"""

        data = None
        try:
            r = subprocess.run(
                ["python3", "-m", "deer_flow", "--skill", "meridian/training-script-writer",
                 "--prompt", prompt, "--output-format", "json"],
                capture_output=True, text=True, cwd=str(DEERFLOW_ROOT), timeout=300,
            )
            if r.returncode == 0 and r.stdout.strip():
                data = json.loads(r.stdout)
        except Exception as e:
            logger.info("DeerFlow unavailable (%s), using fallback", type(e).__name__)

        if not data:
            data = self._fallback(lid, title, content, screens)

        (OUTPUT_ROOT / f"script_{lid.replace('.', '_')}.json").write_text(json.dumps(data, indent=2))

        return VideoScript(
            lesson_id=lid, lesson_title=title, module_name=module,
            duration_target=dur,
            scenes=[
                SceneScript(
                    number=s.get("number", i + 1),
                    text=s.get("text", ""),
                    key_point=s.get("key_point", ""),
                    screen=s.get("screen", screens[i % len(screens)]),
                    tone=s.get("tone", "Confident"),
                )
                for i, s in enumerate(data.get("scenes", []))
            ],
        )

    def _fallback(self, lid, title, content, screens):
        paras = [p.strip() for p in content.split("\n") if p.strip()]
        scenes = []
        scenes.append({
            "number": 1,
            "text": f"Welcome to lesson {lid}: {title}. This is going to level up your sales game. Let's dive in.",
            "key_point": title,
            "screen": screens[0] if screens else "overview",
            "tone": "Confident",
        })
        for i, para in enumerate(paras[:6], start=2):
            key = para[:80].rsplit(" ", 1)[0] if len(para) > 80 else para
            if not key.endswith("."):
                key += "..."
            scenes.append({
                "number": i,
                "text": para[:500],
                "key_point": key,
                "screen": screens[i % len(screens)] if screens else "overview",
                "tone": "Direct",
            })
        scenes.append({
            "number": len(scenes) + 1,
            "text": "That covers everything for this lesson. Mark it complete below and keep building your pipeline. Every lesson makes you a stronger closer.",
            "key_point": "Mark Complete & Continue",
            "screen": screens[0] if screens else "overview",
            "tone": "Warm",
        })
        return {"scenes": scenes}

    # ── TTS ──────────────────────────────────────────────────

    async def _tts(self, script: VideoScript, out: Path) -> list[str]:
        paths = []

        # Title card silence
        title_audio = str(out / "audio_00_title.mp3")
        self._silence(title_audio, 4)
        paths.append(title_audio)

        for scene in script.scenes:
            p = str(out / f"audio_{scene.number:02d}.mp3")
            if TTS_AVAILABLE:
                try:
                    comm = edge_tts.Communicate(scene.text, self.voice)
                    await comm.save(p)
                except Exception as e:
                    logger.warning("TTS scene %d failed: %s", scene.number, e)
                    self._silence(p, 8)
            else:
                self._silence(p, 8)
            paths.append(p)

        # Outro silence
        outro_audio = str(out / "audio_99_outro.mp3")
        self._silence(outro_audio, 4)
        paths.append(outro_audio)

        return paths

    def _silence(self, path, dur):
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "lavfi", "-i", f"anullsrc=r=44100:cl=mono",
                 "-t", str(dur), "-q:a", "9", path],
                capture_output=True, timeout=15,
            )
        except Exception:
            Path(path).touch()

    # ── Animated Scene Generation ────────────────────────────

    def _animate_scenes(self, script: VideoScript, audios: list[str], out: Path) -> list[str]:
        segments = []

        # Title card
        title_img = str(out / "title_card.png")
        self.cards.title(script.module_name, script.lesson_title, title_img)
        title_seg = str(out / "seg_00_title.mp4")
        self._static_segment(title_img, audios[0], title_seg)
        if Path(title_seg).exists():
            segments.append(title_seg)

        # Content scenes — animated screenshots
        for i, scene in enumerate(script.scenes):
            audio_path = audios[i + 1] if (i + 1) < len(audios) else audios[-1]
            seg_path = str(out / f"seg_{scene.number:02d}.mp4")

            screen_img = SCREENS_DIR / f"{scene.screen}.png"
            if not screen_img.exists():
                screen_img = SCREENS_DIR / "overview.png"
            if not screen_img.exists():
                logger.warning("No screenshot for %s — skipping", scene.screen)
                continue

            duration = self._audio_duration(audio_path)
            if duration < 2:
                duration = 8.0

            # Pick a Ken Burns pattern
            pattern = ZOOM_PATTERNS[i % len(ZOOM_PATTERNS)]

            self._ken_burns_segment(
                image=str(screen_img),
                audio=audio_path,
                output=seg_path,
                duration=duration,
                key_point=scene.key_point,
                zoom_start=pattern[0],
                zoom_end=pattern[1],
                x_drift=pattern[2],
                y_drift=pattern[3],
            )

            if Path(seg_path).exists() and Path(seg_path).stat().st_size > 1000:
                segments.append(seg_path)

        # Outro card
        outro_img = str(out / "outro_card.png")
        self.cards.outro(outro_img)
        outro_seg = str(out / "seg_99_outro.mp4")
        self._static_segment(outro_img, audios[-1], outro_seg)
        if Path(outro_seg).exists():
            segments.append(outro_seg)

        return segments

    def _ken_burns_segment(
        self, image: str, audio: str, output: str, duration: float,
        key_point: str, zoom_start: float, zoom_end: float,
        x_drift: int, y_drift: int,
    ):
        """
        Create an animated segment with:
        - Ken Burns zoom/pan on the screenshot
        - Semi-transparent dark banner at bottom
        - White text overlay showing the key point
        """
        fps = 30
        total_frames = int(duration * fps)
        if total_frames < 1:
            total_frames = fps * 5

        safe_text = key_point.replace("'", "'").replace(":", "\\:").replace('"', '\\"')

        # zoompan: smooth zoom from zoom_start to zoom_end with drift
        # d=total_frames, s=1920x1080 output, z='zoom' expression
        zoom_expr = f"{zoom_start}+({zoom_end - zoom_start})*on/{total_frames}"

        # Center position with drift
        cx = 960  # center of 1920
        cy = 540  # center of 1080
        x_expr = f"(iw/2-(iw/zoom/2))+{x_drift}*on/{total_frames}"
        y_expr = f"(ih/2-(ih/zoom/2))+{y_drift}*on/{total_frames}"

        # Build ffmpeg filter chain
        vfilter = (
            f"zoompan=z='{zoom_expr}':x='{x_expr}':y='{y_expr}'"
            f":d={total_frames}:s=1920x1080:fps={fps},"
            # Dark gradient bar at bottom for text
            f"drawbox=x=0:y=ih-120:w=iw:h=120:color=black@0.65:t=fill,"
            # Key point text
            f"drawtext=text='{safe_text}'"
            f":fontsize=36:fontcolor=white:fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
            f":x=(w-text_w)/2:y=h-80"
            # Teal accent line above text bar
            f",drawbox=x=0:y=ih-122:w=iw:h=2:color=0x00d4aa@0.9:t=fill"
        )

        cmd = [
            "ffmpeg", "-y",
            "-i", image,
            "-i", audio,
            "-filter_complex", f"[0:v]{vfilter}[v]",
            "-map", "[v]", "-map", "1:a",
            "-c:v", "libx264", "-preset", "medium", "-crf", "22",
            "-c:a", "aac", "-b:a", "128k",
            "-pix_fmt", "yuv420p",
            "-t", str(duration + 0.3),
            "-shortest",
            output,
        ]

        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)
            if result.returncode != 0:
                logger.warning("Ken Burns failed: %s", result.stderr[-300:] if result.stderr else "unknown")
                self._static_segment(image, audio, output)
        except Exception as e:
            logger.warning("Ken Burns error: %s — falling back to static", e)
            self._static_segment(image, audio, output)

    def _static_segment(self, image: str, audio: str, output: str):
        dur = self._audio_duration(audio) if Path(audio).exists() else 4.0
        if dur < 1:
            dur = 4.0
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-loop", "1", "-i", image, "-i", audio,
                 "-c:v", "libx264", "-tune", "stillimage", "-c:a", "aac",
                 "-b:a", "128k", "-pix_fmt", "yuv420p", "-t", str(dur + 0.3),
                 "-shortest", output],
                capture_output=True, timeout=60,
            )
        except Exception:
            pass

    def _audio_duration(self, path: str) -> float:
        try:
            r = subprocess.run(
                ["ffprobe", "-v", "quiet", "-show_entries", "format=duration",
                 "-of", "csv=p=0", path],
                capture_output=True, text=True, timeout=10,
            )
            return float(r.stdout.strip())
        except Exception:
            return 8.0

    # ── Final Assembly with Crossfades ───────────────────────

    def _final_assembly(self, segments: list[str], lesson_id: str, out: Path) -> str:
        if not segments:
            return ""

        if len(segments) == 1:
            return segments[0]

        # Use xfade for crossfade transitions between segments
        # For many segments, chain xfade filters
        final = str(out / f"final_{lesson_id.replace('.', '_')}.mp4")

        if len(segments) <= 2:
            # Simple concat for 1-2 segments
            return self._simple_concat(segments, final, out)

        # For 3+ segments: use concat with crossfade
        # xfade gets complex with many inputs, so use concat demuxer
        # with a brief fade-in/fade-out on each segment
        faded_segments = []
        for i, seg in enumerate(segments):
            faded = str(out / f"faded_{i:02d}.mp4")
            dur = self._audio_duration(seg)
            if dur < 1:
                dur = 4.0
            fade_dur = min(0.5, dur / 4)

            try:
                subprocess.run(
                    ["ffmpeg", "-y", "-i", seg,
                     "-vf", f"fade=in:0:d={fade_dur},fade=out:st={dur - fade_dur}:d={fade_dur}",
                     "-af", f"afade=in:0:d={fade_dur},afade=out:st={dur - fade_dur}:d={fade_dur}",
                     "-c:v", "libx264", "-crf", "22", "-c:a", "aac",
                     "-pix_fmt", "yuv420p", faded],
                    capture_output=True, timeout=60,
                )
                if Path(faded).exists() and Path(faded).stat().st_size > 500:
                    faded_segments.append(faded)
                else:
                    faded_segments.append(seg)
            except Exception:
                faded_segments.append(seg)

        return self._simple_concat(faded_segments, final, out)

    def _simple_concat(self, segments: list[str], final: str, out: Path) -> str:
        list_file = out / "concat.txt"
        with open(list_file, "w") as f:
            for s in segments:
                f.write(f"file '{os.path.abspath(s)}'\n")
        try:
            subprocess.run(
                ["ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", str(list_file),
                 "-c:v", "libx264", "-crf", "22", "-c:a", "aac", "-b:a", "128k",
                 "-movflags", "+faststart", final],
                check=True, capture_output=True, timeout=300,
            )
        except Exception:
            if segments:
                final = segments[0]
        return final

    # ── Upload / DB / Memory ─────────────────────────────────

    async def _upload(self, video_path: str, lesson_id: str) -> str:
        if not video_path or not Path(video_path).exists():
            return f"file://{video_path}"
        if not self.supabase:
            return f"file://{video_path}"
        path = f"modules/{lesson_id.replace('.', '/')}/video.mp4"
        try:
            with open(video_path, "rb") as f:
                self.supabase.storage.from_("training-videos").upload(
                    path, f, {"content-type": "video/mp4", "upsert": "true"})
            return self.supabase.storage.from_("training-videos").get_public_url(path)
        except Exception as e:
            logger.warning("Upload failed: %s", e)
            return f"file://{video_path}"

    async def _update_db(self, lesson_id, url, dur):
        if not self.supabase:
            return
        try:
            self.supabase.table("training_lessons").update({
                "video_url": url, "video_duration_seconds": dur, "has_video": True,
                "video_generated_at": datetime.now(timezone.utc).isoformat(),
                "video_model": "edge_tts_kenburns_ffmpeg",
            }).eq("lesson_id", lesson_id).execute()
        except Exception as e:
            logger.warning("DB update failed: %s", e)

    def _save_memory(self, lid, title):
        data = {}
        if MEMORY_FILE.exists():
            try:
                data = json.loads(MEMORY_FILE.read_text())
            except Exception:
                pass
        data[lid] = {"title": title, "portal": self.portal,
                     "generated_at": datetime.now(timezone.utc).isoformat(), "voice": self.voice}
        MEMORY_FILE.write_text(json.dumps(data, indent=2))


async def main():
    import argparse
    parser = argparse.ArgumentParser(description="Meridian Training Videos (Animated Screen Recordings)")
    parser.add_argument("--lesson", help="e.g. 3.2")
    parser.add_argument("--module", type=int, help="e.g. 1")
    parser.add_argument("--all", action="store_true")
    parser.add_argument("--portal", default="canada", choices=["us", "canada", "both"])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--voice", help="Override TTS voice")
    args = parser.parse_args()

    portals = ["us", "canada"] if args.portal == "both" else [args.portal]

    for portal in portals:
        gen = AnimatedVideoGenerator(portal=portal)
        if args.voice:
            gen.voice = args.voice

        lessons = []
        if args.lesson:
            l, m = get_lesson(args.lesson)
            if l:
                lessons.append((l, m))
        elif args.module:
            lessons = list(get_module_lessons(args.module))
        elif args.all:
            lessons = list(get_all_lessons())
        else:
            parser.print_help()
            return

        logger.info("%d lessons for %s portal", len(lessons), portal)

        if args.dry_run:
            for l, m in lessons:
                print(f"  [{l['id']}] {l['title']} ({m}) — {l['duration_target']}s")
            continue

        for l, m in lessons:
            content = await _fetch(l["id"], gen.supabase)
            await gen.generate(l["id"], l["title"], content, m, l["duration_target"])
            await asyncio.sleep(1)

    logger.info("All done.")


async def _fetch(lid, sb):
    if sb:
        try:
            r = sb.table("training_lessons").select("content, key_takeaways").eq("lesson_id", lid).execute()
            if r.data:
                return f"{r.data[0].get('content', '')}\n\n{r.data[0].get('key_takeaways', '')}"
        except Exception:
            pass
    return f"Lesson {lid} — content from curriculum config."


if __name__ == "__main__":
    asyncio.run(main())
