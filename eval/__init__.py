"""Real-data model evaluation harness.

Lives outside src/ so it never accidentally ships in the API or CLI.
Run with the venv interpreter:

    PYTHONPATH=/root/Meridian /root/Meridian/.venv/bin/python -m eval.recon

All DB access is read-only — every connection opens a `SET TRANSACTION
READ ONLY` block. Customer identifiers never leave the box: reports
contain counts, percentages, and aggregate statistics only.
"""
