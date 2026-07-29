"""One-shot: send the standard career-application alert email for the Canada
applications whose original notifications only went to the unmonitored
careers-canada@ alias (pre-PR#428/#429 behavior).

Reuses src.email.send.send_career_application — identical subject/body/from
as the live flow, logged to email_send_log. Recipients: the hiring team
(same trio as careers.py's _ADMIN_NOTIFY_EMAILS default).

Authorized by the owner 2026-07-29 ("add them and send out the emails").

Run with production env injected:

    cd /root/Meridian && railway run -- env PYTHONPATH=/root/meridian-careers-fix \
        /root/Meridian/.venv/bin/python /root/meridian-careers-fix/scripts/send_backfilled_applicant_alerts.py
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
        "application_id": "ba600507-64e4-4f31-a46d-5b5ae6c712d3",
        "applicant_name": "Kyle Ng",
        "applicant_email": "kyle.ng621@gmail.com",
        "applicant_phone": "2365188117",
        "location": "Vancouver, BC",
        "experience": "1",
        "commission_experience": "no",
        "availability": "Immediately",
        "referral_source": "Referral",
        "referral_name": "Aidan",
        "motivation": "(applied 2026-07-28 — already has a rep account)",
    },
    {
        "application_id": "db147fb7-2f0b-42d1-af42-00025cd83767",
        "applicant_name": "Dylan Brown",
        "applicant_email": "db538340@gmail.com",
        "applicant_phone": "7788149255",
        "location": "Vancouver, BC",
        "experience": "0",
        "commission_experience": "no",
        "availability": "Immediately",
        "referral_source": "Other",
        "referral_name": "",
        "motivation": "(applied 2026-07-29 — pending in Team > Applications)",
    },
    {
        "application_id": "212d6216-795f-436a-abee-2cdf1ba19726",
        "applicant_name": "Aaron Zeng",
        "applicant_email": "aaronzeng2020@gmail.com",
        "applicant_phone": "2362346839",
        "location": "Vancouver, BC",
        "experience": "None at the moment",
        "commission_experience": "no",
        "availability": "Immediately",
        "referral_source": "Referral",
        "referral_name": "Enoch Cheung",
        "motivation": (
            "Very passionate person, will be available anytime if I am free, love "
            "working with people and doing my job. I feel that this job is going to be "
            "extremely efficient for the future and this is something i'm passionate "
            "about and want to pursue "
            "(applied 2026-07-29 — pending in Team > Applications)"
        ),
    },
]


async def main() -> int:
    failures = 0
    for app in APPLICATIONS:
        for to in RECIPIENTS:
            result = await send_career_application(
                to,
                country_label="Canada",
                position_label="Sales Representative",
                linkedin_url="",
                **app,
            )
            status = result.get("status", "unknown")
            print(f"{app['applicant_name']} -> {to}: {status}")
            if status not in ("sent",):
                failures += 1
                print(f"  detail: {result}")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
