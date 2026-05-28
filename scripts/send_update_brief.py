"""
Send an update brief to the Canada team via Resend.

Usage:
  python scripts/send_update_brief.py                    # dry-run (prints HTML)
  python scripts/send_update_brief.py --send             # sends to all active Canada reps + admin
  python scripts/send_update_brief.py --send --to me     # sends only to admin email
"""
import asyncio
import argparse
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dotenv import load_dotenv
load_dotenv(os.path.join(os.path.dirname(__file__), "..", ".env"))

from src.email.send import send_update_brief, fetch_canada_rep_emails
from src.email.templates.update_brief import render

ADMIN_EMAIL = "aidanpierce@meridian.tips"


def build_may_29_brief() -> dict:
    return dict(
        subject="Meridian Platform Update — May 29, 2026",
        greeting="Team",
        intro=(
            "Here's a summary of the latest features and improvements "
            "shipped to the Meridian Intelligence Platform this week."
        ),
        sections=[
            {
                "title": "Content Marketing Suite",
                "items": [
                    "<strong>Post Generator</strong> — AI-powered social post creation with tone, platform, and image style controls",
                    "<strong>SEO Generator</strong> — Keyword-targeted content builder with meta description, schema markup, and readability scoring",
                    "<strong>Duration-based Video Pricing</strong> — Video studio now prices by duration (15s/30s/60s) instead of flat rate",
                    "<strong>Element Photo Uploads</strong> — Upload custom product photos directly into the commercial editor",
                ],
            },
            {
                "title": "Scheduling (7shifts-style Redesign)",
                "items": [
                    "Staff grouped by role (Management, Kitchen, Front of House, Bar) with collapsible headers",
                    "Overtime badges with weekly hour tracking and daily labor cost totals",
                    "Copy Previous Week and role filter pills for fast schedule building",
                    "Split shift support and per-shift cost display in the edit popover",
                ],
            },
            {
                "title": "Phone Orders AI",
                "items": [
                    "Voice preview with live waveform, speed/pitch/warmth sliders, and language selection (EN/FR/ES)",
                    "Agent Personality panel — formality, upsell style, humor toggle, custom phrases, brand keywords",
                    "Enhanced live call banner with real-time transcript and running order total",
                    "5 smarter conversation patterns: standard, regular customer, indecisive, large group, complaint handling",
                ],
            },
            {
                "title": "Menu Engineering",
                "items": [
                    "<strong>Price Builder</strong> — New tab with editable table, inline editing, sortable columns",
                    "Auto-calculated food cost %, margin, and BCG quadrant classification",
                    "AI pricing suggestions with projected annual revenue impact",
                    "Bulk actions for price adjustments and category changes",
                ],
            },
            {
                "title": "Bug Fixes & Polish",
                "items": [
                    "Eliminated tab switching glitch across all dashboard pages",
                    "Fixed button nesting DOM violation in voice card components",
                    "Quick-add menu item fix for phone orders",
                ],
            },
        ],
        closing=(
            "All features are live now at meridian.tips. "
            "Reply to this email with any questions or feedback."
        ),
        cta_text="Open Meridian Dashboard",
        cta_url="https://meridian.tips/canada/portal/dashboard",
    )


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--send", action="store_true", help="Actually send emails")
    parser.add_argument("--to", default="all", help="'all' for reps+admin, 'me' for admin only")
    args = parser.parse_args()

    brief = build_may_29_brief()

    if not args.send:
        html = render(subject_line=brief["subject"], **{k: v for k, v in brief.items() if k != "subject"})
        print("=== DRY RUN — HTML preview ===")
        print(html[:500])
        print(f"\n... ({len(html)} chars total)")
        print("\nRun with --send to deliver via Resend.")
        return

    recipients: list[str] = []
    if args.to == "all":
        rep_emails = await fetch_canada_rep_emails()
        recipients.extend(rep_emails)
        print(f"Found {len(rep_emails)} active Canada reps: {rep_emails}")
    if ADMIN_EMAIL not in recipients:
        recipients.append(ADMIN_EMAIL)

    print(f"Sending to {len(recipients)} recipients: {recipients}")
    results = await send_update_brief(
        recipients,
        brief["subject"],
        greeting=brief["greeting"],
        intro=brief["intro"],
        sections=brief["sections"],
        closing=brief["closing"],
        cta_text=brief["cta_text"],
        cta_url=brief["cta_url"],
        reply_to=ADMIN_EMAIL,
    )

    for r in results:
        status = r.get("status", "unknown")
        to = r.get("to", "?")
        provider = r.get("provider", "")
        msg_id = r.get("message_id", "")
        print(f"  {to}: {status} (via {provider}) {msg_id}")

    sent = sum(1 for r in results if r.get("status") == "sent")
    print(f"\nDone: {sent}/{len(results)} sent successfully.")


if __name__ == "__main__":
    asyncio.run(main())
