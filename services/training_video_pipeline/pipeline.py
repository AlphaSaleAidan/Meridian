"""
Meridian Training Video Generation Pipeline (100% Free / Open Source)

Stack:
  DeerFlow    — Script generation via Claude (you supply your own API key)
  edge-tts    — Free neural text-to-speech (Microsoft Edge voices, no API key)
  Pillow      — Branded slide image generation
  ffmpeg      — Audio/video assembly
  SadTalker   — Optional talking-head from a single photo (local GPU)

All output is local. No paid APIs required beyond your existing Anthropic key.

Usage:
  python pipeline.py --lesson 3.2 --portal canada
  python pipeline.py --module 7 --portal both
  python pipeline.py --all --portal both
  python pipeline.py --all --portal canada --dry-run
"""

import asyncio
import json
import logging
import os
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

from config import get_all_lessons, get_lesson, get_module_lessons


PIPELINE_ROOT = Path(__file__).parent
DEERFLOW_ROOT = Path(os.getenv("DEERFLOW_WORKSPACE", PIPELINE_ROOT.parent / "deerflow"))
OUTPUT_ROOT = PIPELINE_ROOT / "output"
ASSETS_ROOT = PIPELINE_ROOT / "assets"
MEMORY_FILE = PIPELINE_ROOT / "style_memory.json"

# 1920x1080 branded slide colors
BRAND = {
    "bg": (10, 15, 13),          # #0a0f0d
    "card_bg": (15, 21, 18),     # #0f1512
    "border": (26, 36, 32),      # #1a2420
    "teal": (0, 212, 170),       # #00d4aa
    "white": (255, 255, 255),
    "muted": (107, 122, 116),    # #6b7a74
    "accent": (0, 229, 255),     # #00e5ff
}

TTS_VOICE_CA = "en-CA-LiamNeural"
TTS_VOICE_US = "en-US-GuyNeural"


@dataclass
class SceneScript:
    number: int
    text: str
    key_point: str
    tone: str = "Confident"


@dataclass
class VideoScript:
    lesson_id: str
    lesson_title: str
    module_name: str
    scenes: list[SceneScript] = field(default_factory=list)
    duration_target: int = 180


class SlideRenderer:
    """Generates branded 1920x1080 slide images with Pillow."""

    WIDTH = 1920
    HEIGHT = 1080

    def __init__(self):
        self._font_large = self._load_font(48)
        self._font_medium = self._load_font(32)
        self._font_small = self._load_font(24)
        self._font_tiny = self._load_font(18)

    def _load_font(self, size: int):
        if not PIL_AVAILABLE:
            return None
        for path in [
            "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
            "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
            "/System/Library/Fonts/Helvetica.ttc",
        ]:
            if Path(path).exists():
                return ImageFont.truetype(path, size)
        return ImageFont.load_default()

    def render_title_card(self, module_name: str, lesson_title: str, output_path: str):
        if not PIL_AVAILABLE:
            return
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), BRAND["bg"])
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, self.WIDTH, 4], fill=BRAND["teal"])

        draw.text(
            (self.WIDTH // 2, 360), "MERIDIAN INTELLIGENCE",
            fill=BRAND["teal"], font=self._font_large, anchor="mm",
        )
        draw.text(
            (self.WIDTH // 2, 440), module_name.upper(),
            fill=BRAND["muted"], font=self._font_medium, anchor="mm",
        )

        wrapped = textwrap.fill(lesson_title, width=40)
        draw.text(
            (self.WIDTH // 2, 560), wrapped,
            fill=BRAND["white"], font=self._font_large, anchor="mm",
        )

        draw.rectangle([0, self.HEIGHT - 4, self.WIDTH, self.HEIGHT], fill=BRAND["teal"])
        img.save(output_path)

    def render_content_slide(
        self,
        scene_number: int,
        key_point: str,
        lesson_title: str,
        output_path: str,
    ):
        if not PIL_AVAILABLE:
            return
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), BRAND["bg"])
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, self.WIDTH, 4], fill=BRAND["teal"])

        draw.rectangle([60, 40, self.WIDTH - 60, 100], fill=BRAND["card_bg"])
        draw.text(
            (100, 70), lesson_title,
            fill=BRAND["muted"], font=self._font_small, anchor="lm",
        )

        card_y = 160
        card_h = 700
        draw.rounded_rectangle(
            [120, card_y, self.WIDTH - 120, card_y + card_h],
            radius=20, fill=BRAND["card_bg"], outline=BRAND["border"],
        )

        circle_x, circle_y = 200, card_y + 60
        draw.ellipse(
            [circle_x - 25, circle_y - 25, circle_x + 25, circle_y + 25],
            fill=BRAND["teal"],
        )
        draw.text(
            (circle_x, circle_y), str(scene_number),
            fill=BRAND["bg"], font=self._font_medium, anchor="mm",
        )

        text_x = 260
        text_y = card_y + 100
        max_width = 50

        wrapped = textwrap.fill(key_point, width=max_width)
        lines = wrapped.split("\n")
        for i, line in enumerate(lines[:12]):
            draw.text(
                (text_x, text_y + i * 48), line,
                fill=BRAND["white"], font=self._font_medium,
            )

        draw.rectangle([0, self.HEIGHT - 4, self.WIDTH, self.HEIGHT], fill=BRAND["teal"])
        img.save(output_path)

    def render_outro_card(self, output_path: str):
        if not PIL_AVAILABLE:
            return
        img = Image.new("RGB", (self.WIDTH, self.HEIGHT), BRAND["bg"])
        draw = ImageDraw.Draw(img)

        draw.rectangle([0, 0, self.WIDTH, 4], fill=BRAND["teal"])

        draw.text(
            (self.WIDTH // 2, 400), "Lesson Complete",
            fill=BRAND["teal"], font=self._font_large, anchor="mm",
        )
        draw.text(
            (self.WIDTH // 2, 500), "Mark as complete below to track your progress.",
            fill=BRAND["muted"], font=self._font_medium, anchor="mm",
        )
        draw.text(
            (self.WIDTH // 2, 600), "MERIDIAN INTELLIGENCE",
            fill=BRAND["white"], font=self._font_small, anchor="mm",
        )

        draw.rectangle([0, self.HEIGHT - 4, self.WIDTH, self.HEIGHT], fill=BRAND["teal"])
        img.save(output_path)


class FreeVideoGenerator:
    """Generates training videos using only free/open-source tools."""

    def __init__(self, portal_context: str = "canada"):
        self.portal = portal_context
        self.voice = TTS_VOICE_CA if portal_context == "canada" else TTS_VOICE_US
        self.renderer = SlideRenderer()
        self.supabase = None
        if SUPABASE_AVAILABLE:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if url and key:
                self.supabase = create_client(url, key)

    async def generate_lesson_video(
        self,
        lesson_id: str,
        lesson_title: str,
        lesson_content: str,
        module_name: str,
        duration_target: int,
    ) -> str:
        logger.info("=" * 60)
        logger.info("Generating: %s — %s", lesson_id, lesson_title)
        logger.info("Target: %ds | Portal: %s | Voice: %s", duration_target, self.portal, self.voice)

        out = OUTPUT_ROOT / lesson_id.replace(".", "_")
        out.mkdir(parents=True, exist_ok=True)

        # 1. Generate or load script
        script = await self._generate_script(
            lesson_id, lesson_title, lesson_content, module_name, duration_target,
        )
        logger.info("Script: %d scenes", len(script.scenes))

        # 2. Render slides (Pillow)
        slide_paths = self._render_slides(script, out)
        logger.info("Slides: %d images", len(slide_paths))

        # 3. Generate narration audio (edge-tts)
        audio_paths = await self._generate_audio(script, out)
        logger.info("Audio: %d clips", len(audio_paths))

        # 4. Combine each slide + audio into video segments
        segment_paths = self._create_segments(slide_paths, audio_paths, out)
        logger.info("Segments: %d clips", len(segment_paths))

        # 5. Concatenate into final video
        final_path = self._concat_segments(segment_paths, lesson_id, out)
        logger.info("Final: %s", final_path)

        # 6. Upload to Supabase (if configured)
        video_url = await self._upload(final_path, lesson_id)

        # 7. Update lesson record
        await self._update_lesson_record(lesson_id, video_url, duration_target)

        # 8. Save to local style memory
        self._save_memory(lesson_id, lesson_title)

        logger.info("Done: %s → %s", lesson_id, video_url)
        return video_url

    # ── Script Generation ────────────────────────────────────

    async def _generate_script(
        self,
        lesson_id: str,
        lesson_title: str,
        lesson_content: str,
        module_name: str,
        duration_target: int,
    ) -> VideoScript:
        currency = "CA$" if self.portal == "canada" else "$"

        prompt = f"""Write a training video script for a Meridian Intelligence sales lesson.

MODULE: {module_name}
LESSON: {lesson_id} — {lesson_title}
TARGET: {duration_target} seconds of narration
CURRENCY: {currency}

SOURCE CONTENT:
{lesson_content}

Output valid JSON only — no markdown fences, no commentary:
{{
  "scenes": [
    {{"number": 1, "text": "Narration text for the presenter to speak", "key_point": "Short bullet shown on screen", "tone": "Confident"}},
    ...
  ]
}}

Rules:
- 4-8 scenes
- Each scene's "text" is 2-4 sentences of spoken narration
- Each "key_point" is a short phrase shown on the slide (max 120 chars)
- Use "you" — speak directly to the sales rep
- All dollar amounts in {currency}
- Scene 1 is a hook. Last scene is a CTA to mark lesson complete.
"""

        script_cache = OUTPUT_ROOT / f"script_{lesson_id.replace('.', '_')}.json"

        # Try DeerFlow first
        data = None
        try:
            result = subprocess.run(
                [
                    "python", "-m", "deer_flow",
                    "--skill", "meridian/training-script-writer",
                    "--prompt", prompt,
                    "--output-format", "json",
                ],
                capture_output=True, text=True,
                cwd=str(DEERFLOW_ROOT), timeout=300,
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout)
        except Exception as e:
            logger.info("DeerFlow unavailable (%s), using fallback", e)

        if not data:
            data = self._fallback_script(lesson_id, lesson_title, lesson_content)

        script_cache.parent.mkdir(parents=True, exist_ok=True)
        script_cache.write_text(json.dumps(data, indent=2))

        scenes = [
            SceneScript(
                number=s.get("number", i + 1),
                text=s.get("text", ""),
                key_point=s.get("key_point", ""),
                tone=s.get("tone", "Confident"),
            )
            for i, s in enumerate(data.get("scenes", []))
        ]

        return VideoScript(
            lesson_id=lesson_id,
            lesson_title=lesson_title,
            module_name=module_name,
            scenes=scenes,
            duration_target=duration_target,
        )

    def _fallback_script(self, lesson_id: str, title: str, content: str) -> dict:
        paragraphs = [p.strip() for p in content.split("\n") if p.strip()]
        scenes = []

        scenes.append({
            "number": 1,
            "text": f"Welcome to lesson {lesson_id}: {title}. This is going to change how you sell. Let's get into it.",
            "key_point": title,
            "tone": "Confident",
        })

        for i, para in enumerate(paragraphs[:6], start=2):
            text = para[:400]
            key = para[:120].split(".")[0] + "." if "." in para[:120] else para[:120]
            scenes.append({
                "number": i,
                "text": text,
                "key_point": key,
                "tone": "Direct",
            })

        scenes.append({
            "number": len(scenes) + 1,
            "text": "That covers everything for this lesson. Mark it complete below and move on to the next one. Your pipeline will thank you.",
            "key_point": "Mark Complete & Continue",
            "tone": "Warm",
        })

        return {"scenes": scenes}

    # ── Slide Rendering (Pillow) ─────────────────────────────

    def _render_slides(self, script: VideoScript, out: Path) -> list[str]:
        paths = []

        title_path = str(out / "slide_00_title.png")
        self.renderer.render_title_card(script.module_name, script.lesson_title, title_path)
        paths.append(title_path)

        for scene in script.scenes:
            slide_path = str(out / f"slide_{scene.number:02d}.png")
            self.renderer.render_content_slide(
                scene.number, scene.key_point, script.lesson_title, slide_path,
            )
            paths.append(slide_path)

        outro_path = str(out / "slide_99_outro.png")
        self.renderer.render_outro_card(outro_path)
        paths.append(outro_path)

        return paths

    # ── TTS Audio (edge-tts — free, no API key) ──────────────

    async def _generate_audio(self, script: VideoScript, out: Path) -> list[str]:
        paths = []

        # Title card — 3 seconds of silence
        silence_path = str(out / "audio_00_silence.mp3")
        self._generate_silence(silence_path, 3)
        paths.append(silence_path)

        for scene in script.scenes:
            audio_path = str(out / f"audio_{scene.number:02d}.mp3")
            if TTS_AVAILABLE:
                try:
                    communicate = edge_tts.Communicate(scene.text, self.voice)
                    await communicate.save(audio_path)
                except Exception as e:
                    logger.warning("TTS failed for scene %d: %s", scene.number, e)
                    self._generate_silence(audio_path, 5)
            else:
                self._generate_silence(audio_path, 5)
            paths.append(audio_path)

        # Outro — 3 seconds of silence
        outro_silence = str(out / "audio_99_silence.mp3")
        self._generate_silence(outro_silence, 3)
        paths.append(outro_silence)

        return paths

    def _generate_silence(self, path: str, duration: float):
        try:
            subprocess.run(
                [
                    "ffmpeg", "-y", "-f", "lavfi",
                    "-i", f"anullsrc=r=44100:cl=mono",
                    "-t", str(duration),
                    "-q:a", "9",
                    path,
                ],
                capture_output=True, timeout=30,
            )
        except Exception:
            Path(path).touch()

    # ── Segment Assembly (ffmpeg) ────────────────────────────

    def _create_segments(
        self, slides: list[str], audios: list[str], out: Path,
    ) -> list[str]:
        segments = []
        pairs = list(zip(slides, audios))

        for i, (slide, audio) in enumerate(pairs):
            segment_path = str(out / f"segment_{i:02d}.mp4")

            if not Path(slide).exists():
                continue

            # Get audio duration (or default to 5s)
            duration = self._get_duration(audio) if Path(audio).exists() else 5.0
            if duration < 1:
                duration = 5.0

            try:
                subprocess.run(
                    [
                        "ffmpeg", "-y",
                        "-loop", "1", "-i", slide,
                        "-i", audio,
                        "-c:v", "libx264", "-tune", "stillimage",
                        "-c:a", "aac", "-b:a", "128k",
                        "-pix_fmt", "yuv420p",
                        "-t", str(duration + 0.5),
                        "-shortest",
                        segment_path,
                    ],
                    capture_output=True, timeout=120,
                )
                if Path(segment_path).exists() and Path(segment_path).stat().st_size > 0:
                    segments.append(segment_path)
            except Exception as e:
                logger.warning("Segment %d failed: %s", i, e)

        return segments

    def _get_duration(self, audio_path: str) -> float:
        try:
            result = subprocess.run(
                [
                    "ffprobe", "-v", "quiet",
                    "-show_entries", "format=duration",
                    "-of", "csv=p=0",
                    audio_path,
                ],
                capture_output=True, text=True, timeout=10,
            )
            return float(result.stdout.strip())
        except Exception:
            return 5.0

    # ── Final Concatenation ──────────────────────────────────

    def _concat_segments(self, segments: list[str], lesson_id: str, out: Path) -> str:
        if not segments:
            logger.warning("No segments to concatenate")
            return ""

        list_file = out / "segments.txt"
        with open(list_file, "w") as f:
            for seg in segments:
                f.write(f"file '{os.path.abspath(seg)}'\n")

        final = str(out / f"final_{lesson_id.replace('.', '_')}.mp4")

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(list_file),
                    "-c:v", "libx264", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    final,
                ],
                check=True, capture_output=True, timeout=300,
            )
        except Exception as e:
            logger.warning("Concat failed: %s", e)
            if segments:
                final = segments[0]

        return final

    # ── Upload & DB ──────────────────────────────────────────

    async def _upload(self, video_path: str, lesson_id: str) -> str:
        if not video_path or not Path(video_path).exists():
            return f"file://{video_path}"

        if not self.supabase:
            logger.info("No Supabase — video stays local at %s", video_path)
            return f"file://{video_path}"

        storage_path = f"modules/{lesson_id.replace('.', '/')}/video.mp4"
        try:
            with open(video_path, "rb") as f:
                self.supabase.storage.from_("training-videos").upload(
                    storage_path, f, {"content-type": "video/mp4", "upsert": "true"},
                )
            return self.supabase.storage.from_("training-videos").get_public_url(storage_path)
        except Exception as e:
            logger.warning("Upload failed: %s", e)
            return f"file://{video_path}"

    async def _update_lesson_record(self, lesson_id: str, video_url: str, duration: int):
        if not self.supabase:
            return
        try:
            self.supabase.table("training_lessons").update({
                "video_url": video_url,
                "video_duration_seconds": duration,
                "has_video": True,
                "video_generated_at": datetime.now(timezone.utc).isoformat(),
                "video_model": "edge_tts_pillow_ffmpeg",
                "video_soul_id": "",
            }).eq("lesson_id", lesson_id).execute()
        except Exception as e:
            logger.warning("DB update failed: %s", e)

    # ── Local Style Memory (JSON file, no paid API) ─────────

    def _save_memory(self, lesson_id: str, lesson_title: str):
        data = {}
        if MEMORY_FILE.exists():
            try:
                data = json.loads(MEMORY_FILE.read_text())
            except Exception:
                pass
        data[lesson_id] = {
            "title": lesson_title,
            "portal": self.portal,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "voice": self.voice,
        }
        MEMORY_FILE.write_text(json.dumps(data, indent=2))


# ── Optional: SadTalker talking-head upgrade ─────────────────
#
# If you want a talking presenter instead of slides:
#   1. Clone SadTalker: git clone https://github.com/OpenTalker/SadTalker services/sadtalker
#   2. Install: cd services/sadtalker && pip install -r requirements.txt
#   3. Provide one presenter photo: services/training_video_pipeline/assets/presenter/face.jpg
#   4. Run: python inference.py --driven_audio audio.mp3 --source_image face.jpg --result_dir output/
#
# This generates a lip-synced video of the presenter speaking the narration.
# Requires a GPU with 4+ GB VRAM. Each scene takes ~30s to generate.
#
# To integrate: replace _create_segments() slide+audio with SadTalker output.


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Meridian Training Video Pipeline (Free/OSS)")
    parser.add_argument("--lesson", help="Specific lesson ID e.g. 3.2")
    parser.add_argument("--module", type=int, help="Module number e.g. 7")
    parser.add_argument("--all", action="store_true", help="Generate all 38 lessons")
    parser.add_argument("--portal", default="canada", choices=["us", "canada", "both"])
    parser.add_argument("--dry-run", action="store_true", help="List lessons without generating")
    parser.add_argument("--voice", help="Override TTS voice (e.g. en-CA-ClaraNeural)")
    args = parser.parse_args()

    portals = ["us", "canada"] if args.portal == "both" else [args.portal]

    for portal in portals:
        gen = FreeVideoGenerator(portal_context=portal)
        if args.voice:
            gen.voice = args.voice

        lessons = []
        if args.lesson:
            lesson, mod = get_lesson(args.lesson)
            if lesson:
                lessons.append((lesson, mod))
            else:
                logger.error("Lesson %s not found", args.lesson)
        elif args.module:
            lessons = list(get_module_lessons(args.module))
        elif args.all:
            lessons = list(get_all_lessons())
        else:
            parser.print_help()
            return

        logger.info("Pipeline: %d lessons for %s portal", len(lessons), portal)

        if args.dry_run:
            for lesson, mod in lessons:
                print(f"  [{lesson['id']}] {lesson['title']} ({mod}) — {lesson['duration_target']}s")
            continue

        for lesson, mod in lessons:
            content = await _fetch_content(lesson["id"], gen.supabase)
            await gen.generate_lesson_video(
                lesson_id=lesson["id"],
                lesson_title=lesson["title"],
                lesson_content=content,
                module_name=mod,
                duration_target=lesson["duration_target"],
            )
            await asyncio.sleep(1)

    logger.info("All done.")


async def _fetch_content(lesson_id: str, supabase_client) -> str:
    if supabase_client:
        try:
            result = (
                supabase_client.table("training_lessons")
                .select("content, key_takeaways")
                .eq("lesson_id", lesson_id)
                .execute()
            )
            if result.data:
                row = result.data[0]
                return f"{row.get('content', '')}\n\n{row.get('key_takeaways', '')}"
        except Exception:
            pass
    return f"Lesson {lesson_id} — content from curriculum config."


if __name__ == "__main__":
    asyncio.run(main())
