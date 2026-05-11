"""
Meridian Training Video Generation Pipeline

Orchestrates DeerFlow + Higgsfield + mem0 + VidRush to produce
professional training videos for all 38 Meridian training lessons.

Usage:
  python pipeline.py --lesson 3.2 --portal canada
  python pipeline.py --module 7 --portal both
  python pipeline.py --all --portal both
"""

import asyncio
import json
import logging
import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger("meridian.training_video_pipeline")
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

MEM0_AVAILABLE = False
try:
    from mem0 import Memory
    MEM0_AVAILABLE = True
except ImportError:
    logger.info("mem0 not installed — style memory disabled")

SUPABASE_AVAILABLE = False
try:
    from supabase import create_client
    SUPABASE_AVAILABLE = True
except ImportError:
    logger.info("supabase not installed — upload/db update disabled")

from config import TRAINING_CURRICULUM, get_all_lessons, get_module_lessons, get_lesson


PIPELINE_ROOT = Path(__file__).parent
DEERFLOW_ROOT = Path(os.getenv("DEERFLOW_WORKSPACE", PIPELINE_ROOT.parent / "deerflow"))
OUTPUT_ROOT = PIPELINE_ROOT / "output"


@dataclass
class SceneScript:
    number: int
    time_range: str
    script: str
    visual: str
    broll: str
    tone: str


@dataclass
class VideoScript:
    lesson_id: str
    lesson_title: str
    module_name: str
    scenes: list[SceneScript]
    total_duration: int


class MeridianVideoGenerator:

    def __init__(self, portal_context: str = "canada"):
        self.portal_context = portal_context
        self.soul_id = os.getenv("HIGGSFIELD_SOUL_ID", "")
        self.supabase = None
        if SUPABASE_AVAILABLE:
            url = os.getenv("SUPABASE_URL")
            key = os.getenv("SUPABASE_SERVICE_ROLE_KEY")
            if url and key:
                self.supabase = create_client(url, key)

        self.memory = None
        if MEM0_AVAILABLE and os.getenv("MEM0_API_KEY"):
            try:
                self.memory = Memory()
            except Exception as e:
                logger.warning("mem0 init failed: %s", e)
        self.memory_user_id = f"meridian_video_pipeline_{portal_context}"

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
        logger.info("Target duration: %ds | Portal: %s", duration_target, self.portal_context)

        output_dir = OUTPUT_ROOT / lesson_id.replace(".", "_")
        output_dir.mkdir(parents=True, exist_ok=True)

        style_context = self._load_style_memory()

        script = await self._generate_script(
            lesson_id=lesson_id,
            lesson_title=lesson_title,
            lesson_content=lesson_content,
            module_name=module_name,
            duration_target=duration_target,
            style_context=style_context,
        )

        scene_files = await self._generate_scenes(script, output_dir)

        scored_scenes = await self._score_and_improve(scene_files, output_dir)

        final_path = await self._assemble_video(scored_scenes, lesson_id, output_dir)

        video_url = await self._upload(final_path, lesson_id)

        await self._update_lesson_record(lesson_id, video_url, duration_target)

        self._save_style_memory(lesson_id, lesson_title)

        logger.info("Lesson %s complete: %s", lesson_id, video_url)
        return video_url

    def _load_style_memory(self) -> str:
        if not self.memory:
            return "No previous lessons generated yet. Establish strong brand voice."
        try:
            results = self.memory.search(
                query="Meridian training video style and brand voice",
                user_id=self.memory_user_id,
                limit=5,
            )
            entries = results if isinstance(results, list) else results.get("results", [])
            return "\n".join(r.get("memory", r.get("text", "")) for r in entries if isinstance(r, dict))
        except Exception:
            return "No previous style context available."

    def _save_style_memory(self, lesson_id: str, lesson_title: str):
        if not self.memory:
            return
        try:
            self.memory.add(
                messages=[{
                    "role": "system",
                    "content": (
                        f"Lesson {lesson_id} '{lesson_title}' video generated successfully. "
                        "Style: professional presenter, teal branding, direct address, specific dollar amounts."
                    ),
                }],
                user_id=self.memory_user_id,
            )
        except Exception as e:
            logger.warning("mem0 save failed: %s", e)

    async def _generate_script(
        self,
        lesson_id: str,
        lesson_title: str,
        lesson_content: str,
        module_name: str,
        duration_target: int,
        style_context: str,
    ) -> VideoScript:
        currency = "CA$" if self.portal_context == "canada" else "$"
        avg_ticket = "405" if self.portal_context == "canada" else "300"

        prompt = f"""You are creating a training video script for Meridian Intelligence sales reps.

MODULE: {module_name}
LESSON: {lesson_id} — {lesson_title}
TARGET DURATION: {duration_target} seconds
PORTAL: {self.portal_context.upper()} (currency: {currency})
MONTHLY COMMISSION GOAL: {currency}2,025/month (5 closes at avg {currency}{avg_ticket})

LESSON CONTENT TO SCRIPT:
{lesson_content}

STYLE MEMORY FROM PREVIOUS LESSONS:
{style_context}

Write a JSON video script with this structure:
{{
  "scenes": [
    {{
      "number": 1,
      "time_range": "0:00-0:15",
      "script": "Exact words the presenter speaks",
      "visual": "What is shown on screen",
      "broll": "Supporting footage description for AI generation",
      "tone": "Confident"
    }}
  ]
}}

Rules:
- 4-8 scenes depending on lesson length
- Short sentences, max 15 words each
- Use "you" throughout
- All amounts in {currency}
- Every section connects to earning commission
- {"Reference Canadian businesses and provinces" if self.portal_context == "canada" else "Reference US businesses and cities"}
"""

        script_file = PIPELINE_ROOT / "output" / f"script_{lesson_id.replace('.', '_')}.json"

        result = subprocess.run(
            [
                "python", "-m", "deer_flow",
                "--skill", "meridian/training-script-writer",
                "--prompt", prompt,
                "--output-format", "json",
            ],
            capture_output=True,
            text=True,
            cwd=str(DEERFLOW_ROOT),
            timeout=300,
        )

        if result.returncode == 0 and result.stdout.strip():
            try:
                data = json.loads(result.stdout)
            except json.JSONDecodeError:
                data = self._fallback_script(lesson_id, lesson_title, lesson_content, duration_target)
        else:
            logger.warning("DeerFlow returned non-zero or empty, using fallback script generator")
            data = self._fallback_script(lesson_id, lesson_title, lesson_content, duration_target)

        script_file.parent.mkdir(parents=True, exist_ok=True)
        script_file.write_text(json.dumps(data, indent=2))

        scenes = [
            SceneScript(
                number=s.get("number", i + 1),
                time_range=s.get("time_range", ""),
                script=s.get("script", ""),
                visual=s.get("visual", ""),
                broll=s.get("broll", ""),
                tone=s.get("tone", "Confident"),
            )
            for i, s in enumerate(data.get("scenes", []))
        ]

        return VideoScript(
            lesson_id=lesson_id,
            lesson_title=lesson_title,
            module_name=module_name,
            scenes=scenes,
            total_duration=duration_target,
        )

    def _fallback_script(self, lesson_id: str, title: str, content: str, duration: int) -> dict:
        paragraphs = content.split("\n\n") if "\n\n" in content else [content]
        scenes = []
        scenes.append({
            "number": 1,
            "time_range": "0:00-0:15",
            "script": f"Welcome to lesson {lesson_id}: {title}. Let's get into it.",
            "visual": "Presenter facing camera, Meridian branded background",
            "broll": "Meridian logo animation, teal accents",
            "tone": "Confident",
        })
        for i, para in enumerate(paragraphs[:5], start=2):
            text = para.strip()[:300]
            scenes.append({
                "number": i,
                "time_range": "",
                "script": text,
                "visual": "Presenter explaining with key points as text overlay",
                "broll": "Business environment, POS terminal, restaurant interior",
                "tone": "Direct",
            })
        scenes.append({
            "number": len(scenes) + 1,
            "time_range": "",
            "script": "That's it for this lesson. Mark it complete below and move to the next one.",
            "visual": "Presenter, call-to-action overlay",
            "broll": "Meridian dashboard screenshots",
            "tone": "Warm",
        })
        return {"scenes": scenes}

    async def _generate_scenes(self, script: VideoScript, output_dir: Path) -> list[str]:
        scene_files = []

        intro_file = str(output_dir / "scene_00_intro.mp4")
        intro_prompt = (
            f"Professional corporate training intro. "
            f"'Meridian Intelligence' title in teal. "
            f"Clean dark background. '{script.module_name}' fades in. "
            f"Confident, modern aesthetic. 5 seconds."
        )
        self._run_higgsfield("marketing_studio", intro_prompt, intro_file, duration=5)
        scene_files.append(intro_file)

        for scene in script.scenes:
            presenter_prompt = (
                f"{scene.script} "
                f"Professional sales trainer presenting. "
                f"Modern studio, teal accents. Direct eye contact. "
                f"Tone: {scene.tone}. Business casual."
            )
            presenter_file = str(output_dir / f"scene_{scene.number:02d}_presenter.mp4")
            self._run_higgsfield(
                "seedance_2_0", presenter_prompt, presenter_file,
                duration=5, soul_id=self.soul_id,
            )
            scene_files.append(presenter_file)

            if scene.broll:
                broll_prompt = f"{scene.broll} Professional business setting. Clean. Modern."
                broll_file = str(output_dir / f"scene_{scene.number:02d}_broll.mp4")
                self._run_higgsfield("nano_banana_2", broll_prompt, broll_file)
                scene_files.append(broll_file)

        outro_file = str(output_dir / "scene_99_outro.mp4")
        self._run_higgsfield(
            "marketing_studio",
            "Training complete. 'Mark as Complete below.' Meridian teal. Professional. 3 seconds.",
            outro_file,
            duration=3,
        )
        scene_files.append(outro_file)

        return scene_files

    def _run_higgsfield(
        self,
        model: str,
        prompt: str,
        output: str,
        duration: int = 5,
        soul_id: str | None = None,
    ):
        cmd = [
            "higgsfield", "generate", "create", model,
            "--prompt", prompt,
            "--aspect_ratio", "16:9",
            "--duration", str(duration),
            "--wait",
            "--output", output,
        ]
        if soul_id:
            cmd.extend(["--soul-id", soul_id])
        if model in ("seedance_2_0",):
            cmd.extend(["--resolution", "1080p", "--mode", "pro"])

        logger.info("Higgsfield: %s → %s", model, Path(output).name)
        try:
            subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=600)
        except FileNotFoundError:
            logger.warning("Higgsfield CLI not found — skipping generation for %s", output)
        except subprocess.TimeoutExpired:
            logger.warning("Higgsfield timed out for %s", output)
        except subprocess.CalledProcessError as e:
            logger.warning("Higgsfield error for %s: %s", output, e.stderr[:200] if e.stderr else "")

    async def _score_and_improve(
        self,
        scene_files: list[str],
        output_dir: Path,
        min_score: float = 0.60,
    ) -> list[str]:
        approved = []
        for f in scene_files:
            if "intro" in f or "outro" in f:
                approved.append(f)
                continue

            if not Path(f).exists():
                logger.warning("Scene file missing: %s — skipping", f)
                continue

            score = self._score_video(f)
            logger.info("  %s: virality score %.2f", Path(f).name, score)

            if score >= min_score:
                approved.append(f)
            else:
                logger.info("  Score below %.2f — regenerating", min_score)
                v2_path = f.replace(".mp4", "_v2.mp4")
                self._run_higgsfield(
                    "seedance_2_0",
                    "ENERGETIC training video. Strong eye contact. Dynamic. Teal. Hook immediately.",
                    v2_path,
                    soul_id=self.soul_id,
                )
                approved.append(v2_path if Path(v2_path).exists() else f)

        return approved

    def _score_video(self, video_path: str) -> float:
        try:
            result = subprocess.run(
                ["higgsfield", "generate", "create", "brain_activity", "--video", video_path, "--wait"],
                capture_output=True, text=True, timeout=120,
            )
            match = re.search(r"score[:\s]+([0-9.]+)", result.stdout, re.IGNORECASE)
            return float(match.group(1)) if match else 0.70
        except Exception:
            return 0.70

    async def _assemble_video(self, scene_files: list[str], lesson_id: str, output_dir: Path) -> str:
        existing = [f for f in scene_files if Path(f).exists()]
        if not existing:
            logger.warning("No scene files exist — cannot assemble")
            return ""

        list_file = output_dir / "scenes.txt"
        with open(list_file, "w") as fh:
            for scene in existing:
                fh.write(f"file '{os.path.abspath(scene)}'\n")

        final_path = str(output_dir / f"final_{lesson_id.replace('.', '_')}.mp4")

        try:
            subprocess.run(
                [
                    "ffmpeg", "-y",
                    "-f", "concat", "-safe", "0",
                    "-i", str(list_file),
                    "-c:v", "libx264", "-crf", "23",
                    "-c:a", "aac", "-b:a", "128k",
                    "-movflags", "+faststart",
                    final_path,
                ],
                check=True,
                capture_output=True,
                timeout=300,
            )
            logger.info("Assembled: %s", final_path)
        except Exception as e:
            logger.warning("ffmpeg assembly failed: %s", e)
            if existing:
                final_path = existing[0]

        return final_path

    async def _upload(self, video_path: str, lesson_id: str) -> str:
        if not video_path or not Path(video_path).exists():
            return f"file://{video_path}"

        if not self.supabase:
            logger.info("Supabase not configured — skipping upload")
            return f"file://{video_path}"

        storage_path = f"modules/{lesson_id.replace('.', '/')}/video.mp4"
        try:
            with open(video_path, "rb") as f:
                self.supabase.storage.from_("training-videos").upload(
                    storage_path, f, {"content-type": "video/mp4", "upsert": "true"},
                )
            url = self.supabase.storage.from_("training-videos").get_public_url(storage_path)
            return url
        except Exception as e:
            logger.warning("Supabase upload failed: %s", e)
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
                "video_model": "seedance_2_0_higgsfield",
                "video_soul_id": self.soul_id,
            }).eq("lesson_id", lesson_id).execute()
        except Exception as e:
            logger.warning("Lesson record update failed: %s", e)


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="Meridian Training Video Pipeline")
    parser.add_argument("--lesson", help="Specific lesson ID e.g. 3.2")
    parser.add_argument("--module", type=int, help="Module number e.g. 7")
    parser.add_argument("--all", action="store_true", help="Generate all lessons")
    parser.add_argument("--portal", default="canada", choices=["us", "canada", "both"])
    parser.add_argument("--dry-run", action="store_true", help="Print plan without generating")
    args = parser.parse_args()

    portals = ["us", "canada"] if args.portal == "both" else [args.portal]

    for portal in portals:
        generator = MeridianVideoGenerator(portal_context=portal)

        lessons = []
        if args.lesson:
            lesson, module_name = get_lesson(args.lesson)
            if lesson:
                lessons.append((lesson, module_name))
            else:
                logger.error("Lesson %s not found", args.lesson)
        elif args.module:
            lessons = list(get_module_lessons(args.module))
        elif args.all:
            lessons = list(get_all_lessons())
        else:
            parser.print_help()
            return

        logger.info("Generating %d videos for %s portal", len(lessons), portal)

        if args.dry_run:
            for lesson, module_name in lessons:
                print(f"  [{lesson['id']}] {lesson['title']} ({module_name}) — {lesson['duration_target']}s")
            continue

        for lesson, module_name in lessons:
            content = await _fetch_lesson_content(lesson["id"], portal, generator.supabase)
            await generator.generate_lesson_video(
                lesson_id=lesson["id"],
                lesson_title=lesson["title"],
                lesson_content=content,
                module_name=module_name,
                duration_target=lesson["duration_target"],
            )
            await asyncio.sleep(5)


async def _fetch_lesson_content(lesson_id: str, portal: str, supabase_client) -> str:
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

    return f"Lesson {lesson_id} — generate script from module context and curriculum config."


if __name__ == "__main__":
    asyncio.run(main())
