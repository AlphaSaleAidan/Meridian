# Customer Recognizer

> Group: **pos-analytics**
> Tier: **Tier 2**
> Availability: **Base product (all merchants)**

## What it does

Repeat-visitor frequency, new-vs-returning ratio, even without a formal loyalty program.

## What it needs

Customer IDs in transactions (Square, Toast, Clover all expose; CSV varies). Falls back to card-fingerprint matching where available.

## Example output

> 62% of weekly revenue comes from returning customers (last-90-day visit). Your 'regular' base is 184 customers — protect it.

## Where it lives

Source: `src/ai/agents/customer_recognizer.py` or `src/camera/customer_recognizer.py` (vision modules) or `src/ai/customer_recognizer.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
