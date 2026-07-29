"""One-shot: alert the hiring team about the two backfilled US applicants
(companion to send_backfilled_applicant_alerts.py, same authorized mechanism).

  * Nate Wilkinson — US career application 2026-07-18 (Team Lead)
  * Haider Raza — US portal rep signup 2026-06-16 (no application form; details
    from auth signup metadata)

Authorized by the owner 2026-07-29 ("go ahead and run the US backfill too").

Run with production env injected:

    cd /root/Meridian && railway run -s Meridian -e production -- env PYTHONPATH=/root/meridian-careers-fix \
        /root/Meridian/.venv/bin/python /root/meridian-careers-fix/scripts/send_us_backfilled_applicant_alerts.py
"""
import asyncio
import sys

from src.email.send import send_career_application

RECIPIENTS = [
    "aidanpierce72@gmail.com",
    "cheungenochmgmt@gmail.com",
    "aidanvietnguyen@gmail.com",
]

APPLICATIONS = [
    {
        "position_label": "Sales Team Lead",
        "application_id": "e3bf1462-0b81-43b1-a91f-976ff86ffc64",
        "applicant_name": "Nate Wilkinson",
        "applicant_email": "natewilk@gmail.com",
        "applicant_phone": "9195002120",
        "experience": "2 years",
        "motivation": (
            "Love understanding how things work.\n3 years of robotics and CAD exp.\n"
            "Building my app with ai.\nGood social skills.\n\nI thrive from remote "
            "work+sales\nMsg me back!\n\n"
            "(applied 2026-07-18 — pending in US Team > Applications)"
        ),
    },
    {
        "position_label": "Sales Representative",
        "application_id": "",
        "applicant_name": "Haider Raza",
        "applicant_email": "haiderr099@gmail.com",
        "applicant_phone": "",
        "experience": "",
        "motivation": (
            "Registered directly via the US rep portal signup on 2026-06-16 (no "
            "application form on file) — now pending in US Team > Applications"
        ),
    },
]


async def main() -> int:
    failures = 0
    for app in APPLICATIONS:
        for to in RECIPIENTS:
            result = await send_career_application(
                to,
                country_label="US",
                availability="",
                commission_experience="",
                linkedin_url="",
                referral_source="",
                referral_name="",
                location="",
                **app,
            )
            status = result.get("status", "unknown")
            print(f"{app['applicant_name']} -> {to}: {status}")
            if status != "sent":
                failures += 1
                print(f"  detail: {result}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
