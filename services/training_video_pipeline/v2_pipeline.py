#!/usr/bin/env python3
"""
Meridian Training Video Pipeline v2
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
10 training videos + 2 Instagram commercials.
Uses OpenAI TTS (gpt-4o-mini-tts) for human-sounding narration.
Per-video storyboards with varied screenshots per scene.
"""
import asyncio
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass, field
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent.parent.parent / ".env")

OPENAI_KEY = os.getenv("OPENAI_API_KEY", "")
TTS_MODEL = "gpt-4o-mini-tts"
TTS_VOICE = "ash"  # male, warm, professional
SCREENS_DIR = Path(__file__).parent / "assets" / "screens"
OUTPUT_DIR = Path(__file__).parent / "output_v2"

AVAILABLE_SCREENS = [
    "overview.png", "revenue.png", "customers.png", "products.png",
    "inventory.png", "margins.png", "insights.png", "anomalies.png",
    "forecasts.png", "actions.png", "agents.png", "staff.png",
    "peak-hours.png", "menu-matrix.png", "phone-orders.png",
    "notifications.png", "settings.png",
]

KEN_BURNS_PATTERNS = [
    ("zoom_in_center", "1.0+(0.15*on/{d})", "(iw/2-(iw/zoom/2))", "(ih/2-(ih/zoom/2))"),
    ("pan_right",      "1.08",              "40*on/{d}",           "(ih/2-(ih/zoom/2))"),
    ("pan_left",       "1.08",              "iw-iw/zoom-40*on/{d}","(ih/2-(ih/zoom/2))"),
    ("zoom_out",       "1.15-(0.12*on/{d})", "(iw/2-(iw/zoom/2))", "(ih/2-(ih/zoom/2))"),
    ("pan_down",       "1.08",              "(iw/2-(iw/zoom/2))",  "30*on/{d}"),
    ("drift_right_zoom","1.0+(0.12*on/{d})", "40*on/{d}",          "(ih/2-(ih/zoom/2))+20*on/{d}"),
]


@dataclass
class Scene:
    narration: str
    screen: str  # which screenshot to use
    duration_hint: float = 0  # set after TTS


@dataclass
class VideoSpec:
    id: str
    title: str
    scenes: list[Scene] = field(default_factory=list)
    is_commercial: bool = False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# STORYBOARDS — each video has unique scenes & visuals
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRAINING_VIDEOS: list[VideoSpec] = [
    VideoSpec("01_welcome", "Welcome to Meridian", [
        Scene("Welcome to Meridian — the AI-powered analytics platform that helps independent businesses find hidden revenue in their point-of-sale data.", "overview.png"),
        Scene("We work with restaurants, smoke shops, salons, retail stores, and food trucks across Canada and the US.", "customers.png"),
        Scene("As a Meridian sales rep, you'll help business owners see exactly where they're leaving money on the table — and you'll earn seventy percent commission on every deal you close.", "revenue.png"),
        Scene("Your portal has everything you need — a lead pipeline to track prospects, training to sharpen your pitch, and a one-click onboarding flow to get customers live in under five minutes.", "actions.png"),
        Scene("Let's get you selling. By the end of this training, you'll know the product inside out, have a killer pitch, and be ready to close your first deal.", "insights.png"),
    ]),

    VideoSpec("02_product_pricing", "Product & Pricing", [
        Scene("Meridian connects to any point-of-sale system — Square, Clover, Moneris, Toast, Lightspeed — and turns raw transaction data into actionable insights.", "overview.png"),
        Scene("Our AI analyzes sales patterns, identifies anomalies, forecasts demand, and even detects which menu items or products are dragging down margins.", "margins.png"),
        Scene("We offer two plans. The Standard plan is two-fifty per month Canadian — that covers full analytics, AI agents, and unlimited users.", "products.png"),
        Scene("The Weekly plan is sixty-five dollars per week — same features, but easier for businesses that prefer weekly billing. Both plans pay for themselves within the first month.", "forecasts.png"),
        Scene("When you pitch, always anchor to the dollar amount they're losing. A restaurant wasting three hundred dollars a month on over-ordered inventory is already paying for Meridian — they just don't know it yet.", "anomalies.png"),
    ]),

    VideoSpec("03_first_week", "Your First Week", [
        Scene("Day one — set up your portal. Log in, complete your profile, and add your first five leads to the pipeline.", "settings.png"),
        Scene("Your pipeline has stages — prospecting, contacted, demo scheduled, proposal sent, and negotiation. Drag leads through as conversations progress.", "actions.png"),
        Scene("Day two and three — start making calls. Use the elevator pitch you'll learn in the next video. Aim for ten outreach touches per day.", "phone-orders.png"),
        Scene("Day four and five — book your first demos. The Create Customer page generates an onboarding link you can text directly to the business owner.", "customers.png"),
        Scene("By end of week one, you should have at least five active conversations and one demo booked. Top reps hit their first close within ten days.", "revenue.png"),
    ]),

    VideoSpec("04_sales_conversation", "The Sales Conversation", [
        Scene("The sixty-second pitch. Hey, I work with a company called Meridian. We plug into your POS and show you exactly where you're losing money — most owners find at least three hundred dollars a month in waste they didn't know about. Takes five minutes to set up. Can I show you?", "overview.png"),
        Scene("Tailor the pain point to the vertical. For restaurants — food cost creep and over-ordering. For smoke shops — dead inventory sitting on shelves. For salons — no-show patterns and rebooking gaps.", "menu-matrix.png"),
        Scene("When they say it's too expensive, reframe it. Two-fifty a month is about eight dollars a day. If we find you even one insight that saves you fifteen dollars a day — you're doubling your money.", "margins.png"),
        Scene("Against competitors, we win on three things. First — we're AI-native, not just dashboards. Second — we support every major POS, not just one. Third — our pricing is flat, no per-location surcharges.", "insights.png"),
        Scene("Never oversell. Stick to what the platform actually does. If a prospect asks about a feature we don't have, be honest and log it as feedback.", "notifications.png"),
    ]),

    VideoSpec("05_demo_mastery", "Running the Demo", [
        Scene("Before every demo, run a quick discovery. What POS do you use? How many locations? What's your biggest operational headache right now? These three questions shape your entire pitch.", "customers.png"),
        Scene("Start the demo with the overview dashboard. Point out the revenue trend and say — this is what your data looks like when AI is watching it twenty-four seven.", "overview.png"),
        Scene("Then go to the insight that matches their pain point. For restaurants, show the menu matrix — which items are high-margin versus low-margin. For retail, show inventory velocity.", "menu-matrix.png"),
        Scene("Show the anomaly detection. Say — last Tuesday, your evening sales dropped eighteen percent versus your usual pattern. Would you have caught that? Meridian did, in real time.", "anomalies.png"),
        Scene("Close with the setup. Say — I can get you live in under five minutes, right now. All I need is your email and your POS login. Then walk them through the onboarding wizard.", "settings.png"),
    ]),

    VideoSpec("06_verticals", "Vertical Playbooks", [
        Scene("Restaurants and cafes — lead with menu matrix analysis and peak hour optimization. The average restaurant owner is losing three to five hundred dollars a month on over-ordered ingredients they end up throwing away.", "menu-matrix.png"),
        Scene("Smoke shops and vape stores — lead with dead inventory detection. These stores have hundreds of SKUs and no idea which ones are actually moving. Meridian highlights what's sitting on shelves costing them money.", "inventory.png"),
        Scene("Salons and spas — lead with customer retention and rebooking rates. Staff scheduling is their biggest cost. Show how Meridian tracks no-show patterns and helps them fill empty chairs.", "staff.png"),
        Scene("Retail and boutiques — lead with seasonal trend forecasting. Help them buy smarter for next season based on actual sales data, not gut feeling.", "forecasts.png"),
        Scene("Food trucks and quick service — lead with location-based sales analysis and peak-hour staffing. These operators have thin margins and every dollar counts.", "peak-hours.png"),
    ]),

    VideoSpec("07_advanced_selling", "Advanced Selling & Commissions", [
        Scene("Create urgency without pressure. Say — we're onboarding ten new businesses in your area this month. The sooner you're live, the sooner you start seeing insights. Would you rather start this week or next?", "actions.png"),
        Scene("Multi-location upsell — if a prospect has more than one location, pitch consolidated analytics. One dashboard, all locations, same flat price per location.", "overview.png"),
        Scene("Referral programs work. After onboarding a customer, ask — do you know another business owner who'd benefit from this? If they sign up, you earn commission on both.", "customers.png"),
        Scene("Your commission is seventy percent of the first month. On a two-fifty per month deal, that's one-seventy-five in your pocket. Close ten deals a month and that's seventeen-fifty just in first-month commissions.", "revenue.png"),
        Scene("Here's where it gets exciting — residuals. Every customer you sign keeps paying monthly, and you keep earning. After six months of consistent closing, your residual income alone can clear two to three thousand a month on top of new deal commissions.", "forecasts.png"),
    ]),

    VideoSpec("08_compliance", "Compliance & Ethics", [
        Scene("Sales ethics are non-negotiable at Meridian. Never make promises about specific revenue increases. Never guarantee results. Always say — based on what we see with similar businesses.", "insights.png"),
        Scene("Data privacy matters. We're PIPEDA compliant in Canada. Customer POS data is encrypted in transit and at rest. We never share merchant data with third parties. Ever.", "settings.png"),
        Scene("If you're selling Camera Intelligence, privacy signage is legally required before any camera goes live. Walk the business owner through the signage requirements — never skip this step.", "notifications.png"),
    ]),

    VideoSpec("09_camera_intelligence", "Camera Intelligence", [
        Scene("Camera Intelligence is our premium add-on. It uses AI-powered cameras to track foot traffic, customer flow, and zone engagement — without identifying individuals.", "agents.png"),
        Scene("Hardware is simple — one or two standard IP cameras per location. Meridian's AI does the processing. No expensive hardware needed.", "settings.png"),
        Scene("The ROI pitch — a restaurant that knows their peak entry times can staff better, reduce wait times, and serve more customers. That insight alone can add five to ten percent to revenue.", "peak-hours.png"),
        Scene("PIPEDA compliance is mandatory. The business must post visible privacy signage before cameras go live. We provide the signage templates — your job is to make sure the owner installs them.", "notifications.png"),
    ]),

    VideoSpec("10_pos_integrations", "POS Integrations", [
        Scene("Meridian integrates with every major POS in Canada. Square, Clover, Moneris, Toast, Lightspeed, TouchBistro — if they use it, we connect to it.", "overview.png"),
        Scene("Square and Clover use OAuth — the customer clicks Authorize in our onboarding wizard and they're connected in seconds. No API keys, no technical setup.", "settings.png"),
        Scene("Moneris requires an API key from the Moneris Developer Portal. Walk the customer through generating the key and pasting it into the Meridian setup page.", "agents.png"),
        Scene("If a connection fails, the first troubleshoot is always — check the POS credentials. Ninety percent of issues are expired tokens or wrong API keys. The retry button in settings handles most cases.", "notifications.png"),
        Scene("Once connected, historical data starts flowing in within minutes. The customer will see their first insights within twenty-four hours as the AI analyzes their transaction patterns.", "forecasts.png"),
    ]),
]

COMMERCIAL_VIDEOS: list[VideoSpec] = [
    VideoSpec("commercial_01_hidden_money", "Your POS is Hiding Money From You", [
        Scene("You check your POS every day. Sales are up. Things look fine.", "revenue.png"),
        Scene("But buried in that data — three hundred dollars a month in waste you can't see. Over-ordered stock. Under-performing products. Dead inventory.", "anomalies.png"),
        Scene("Meridian connects to your POS and finds it in minutes. AI-powered analytics for independent businesses.", "insights.png"),
        Scene("Five minutes to set up. Pays for itself in week one. Meridian — the smart operator's unfair advantage.", "overview.png"),
    ], is_commercial=True),

    VideoSpec("commercial_02_join_team", "Join the Meridian Sales Team", [
        Scene("Independent businesses are drowning in POS data they can't use. You can fix that — and earn serious money doing it.", "customers.png"),
        Scene("Meridian reps earn seventy percent commission — that's one-seventy-five per deal. Build your book and your residuals grow every single month.", "revenue.png"),
        Scene("No cold calling required. We give you leads, training, and a portal that handles everything from pitch to onboarding.", "actions.png"),
        Scene("Apply now at meridian dot tips slash careers. Meridian — Canada's fastest-growing POS analytics team.", "overview.png"),
    ], is_commercial=True),
]


async def generate_tts(text: str, output_path: str, voice: str = TTS_VOICE) -> float:
    """Generate TTS audio via OpenAI API. Returns duration in seconds."""
    async with httpx.AsyncClient(timeout=60) as client:
        resp = await client.post(
            "https://api.openai.com/v1/audio/speech",
            headers={"Authorization": f"Bearer {OPENAI_KEY}"},
            json={
                "model": TTS_MODEL,
                "voice": voice,
                "input": text,
                "response_format": "mp3",
                "speed": 1.0,
            },
        )
        if resp.status_code != 200:
            raise RuntimeError(f"TTS failed {resp.status_code}: {resp.text[:200]}")
        Path(output_path).write_bytes(resp.content)

    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", output_path
    ]).decode().strip())
    return dur


def ken_burns_segment(image: str, audio: str, output: str, pattern_idx: int) -> str:
    """Create a Ken Burns animated segment with narration subtitle."""
    dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", audio
    ]).decode().strip())

    fps = 30
    frames = int(dur * fps)
    name, z_expr, x_expr, y_expr = KEN_BURNS_PATTERNS[pattern_idx % len(KEN_BURNS_PATTERNS)]

    z = z_expr.replace("{d}", str(frames))
    x = x_expr.replace("{d}", str(frames))
    y = y_expr.replace("{d}", str(frames))

    # Bottom bar overlay for cinematic look
    filter_complex = (
        f"[0:v]zoompan=z='{z}':x='{x}':y='{y}':d={frames}:s=1920x1080:fps={fps},"
        f"drawbox=x=0:y=ih-100:w=iw:h=100:color=black@0.55:t=fill,"
        f"drawbox=x=0:y=ih-102:w=iw:h=2:color=0x00d4aa@0.9:t=fill[v]"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-i", image, "-i", audio,
        "-filter_complex", filter_complex,
        "-map", "[v]", "-map", "1:a",
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-t", str(dur),
        "-shortest", output,
    ], check=True, capture_output=True)
    return output


def title_card(title: str, subtitle: str, duration: float, output: str):
    """Generate a title card with Meridian branding."""
    # Escape special characters for ffmpeg drawtext
    title_esc = title.replace(":", r"\:").replace("'", r"\'")
    subtitle_esc = subtitle.replace(":", r"\:").replace("'", r"\'")

    filter_complex = (
        f"color=c=0x0a0f0d:s=1920x1080:d={duration},"
        f"drawtext=text='{title_esc}':fontsize=56:fontcolor=white:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-30,"
        f"drawtext=text='{subtitle_esc}':fontsize=24:fontcolor=0x00d4aa:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"x=(w-text_w)/2:y=(h-text_h)/2+40,"
        f"drawbox=x=w/2-100:y=h/2+75:w=200:h=3:color=0x00d4aa:t=fill"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", filter_complex,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-t", str(duration), output,
    ], check=True, capture_output=True)


def outro_card(duration: float, output: str):
    """Generate an outro card."""
    filter_complex = (
        f"color=c=0x0a0f0d:s=1920x1080:d={duration},"
        f"drawtext=text='meridian.tips':fontsize=48:fontcolor=0x00d4aa:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf:"
        f"x=(w-text_w)/2:y=(h-text_h)/2-20,"
        f"drawtext=text='The smart operator\\'s unfair advantage.':fontsize=22:fontcolor=0x6b7a74:"
        f"fontfile=/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf:"
        f"x=(w-text_w)/2:y=(h-text_h)/2+30"
    )

    subprocess.run([
        "ffmpeg", "-y",
        "-f", "lavfi", "-i", filter_complex,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-pix_fmt", "yuv420p",
        "-t", str(duration), output,
    ], check=True, capture_output=True)


async def build_video(spec: VideoSpec):
    """Build a single video from its storyboard spec."""
    vid_dir = OUTPUT_DIR / spec.id
    vid_dir.mkdir(parents=True, exist_ok=True)

    print(f"\n{'='*50}")
    print(f"  Building: {spec.title} ({spec.id})")
    print(f"  Scenes: {len(spec.scenes)}")
    print(f"{'='*50}")

    segments = []

    # Title card
    title_path = str(vid_dir / "seg_00_title.mp4")
    title_dur = 2.5 if not spec.is_commercial else 1.5
    subtitle = "Sales Training" if not spec.is_commercial else "Meridian Analytics"
    title_card(spec.title, subtitle, title_dur, title_path)
    segments.append(title_path)
    print(f"  [title] {title_dur}s")

    # Scenes
    for i, scene in enumerate(spec.scenes):
        audio_path = str(vid_dir / f"audio_{i:02d}.mp3")
        seg_path = str(vid_dir / f"seg_{i+1:02d}.mp4")

        print(f"  [{i+1}/{len(spec.scenes)}] TTS: {scene.narration[:60]}...", end=" ", flush=True)
        dur = await generate_tts(scene.narration, audio_path)
        scene.duration_hint = dur
        print(f"{dur:.1f}s", end=" ", flush=True)

        image_path = str(SCREENS_DIR / scene.screen)
        if not Path(image_path).exists():
            image_path = str(SCREENS_DIR / "overview.png")

        ken_burns_segment(image_path, audio_path, seg_path, pattern_idx=i)
        segments.append(seg_path)
        print("OK")

    # Outro
    outro_path = str(vid_dir / "seg_99_outro.mp4")
    outro_dur = 3.0 if not spec.is_commercial else 2.0
    outro_card(outro_dur, outro_path)
    segments.append(outro_path)

    # Final assembly
    concat_file = str(vid_dir / "concat.txt")
    with open(concat_file, "w") as f:
        for seg in segments:
            f.write(f"file '{seg}'\n")

    final_path = str(vid_dir / f"{spec.id}.mp4")
    subprocess.run([
        "ffmpeg", "-y", "-f", "concat", "-safe", "0", "-i", concat_file,
        "-c:v", "libx264", "-preset", "medium", "-crf", "20",
        "-c:a", "aac", "-b:a", "192k",
        "-pix_fmt", "yuv420p",
        "-movflags", "+faststart",
        final_path,
    ], check=True, capture_output=True)

    total_dur = float(subprocess.check_output([
        "ffprobe", "-v", "error", "-show_entries", "format=duration",
        "-of", "csv=p=0", final_path
    ]).decode().strip())

    size_mb = Path(final_path).stat().st_size / 1024 / 1024
    print(f"  DONE: {final_path} ({total_dur:.0f}s, {size_mb:.1f}MB)")
    return final_path


async def main():
    if not OPENAI_KEY:
        print("ERROR: OPENAI_API_KEY not set in .env")
        sys.exit(1)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    targets = sys.argv[1:] if len(sys.argv) > 1 else None

    all_videos = TRAINING_VIDEOS + COMMERCIAL_VIDEOS

    if targets:
        all_videos = [v for v in all_videos if v.id in targets or any(t in v.id for t in targets)]

    print(f"Building {len(all_videos)} videos with OpenAI TTS ({TTS_MODEL}/{TTS_VOICE})")
    print(f"Output: {OUTPUT_DIR}")

    results = []
    for spec in all_videos:
        try:
            path = await build_video(spec)
            results.append((spec.id, path, "OK"))
        except Exception as e:
            print(f"  FAILED: {e}")
            results.append((spec.id, "", str(e)))

    print(f"\n{'='*50}")
    print(f"  RESULTS")
    print(f"{'='*50}")
    for vid_id, path, status in results:
        print(f"  {vid_id}: {status}")
    print(f"\nDone: {sum(1 for _,_,s in results if s == 'OK')}/{len(results)} succeeded")


if __name__ == "__main__":
    asyncio.run(main())
