# Payment Optimizer

> Group: **pos-analytics**
> Tier: **Tier 4**
> Availability: **Base product (all merchants)**

## What it does

Payment-method mix and processor-fee optimization.

## What it needs

Transactions with payment method + processor fee data (where exposed).

## Example output

> AmEx is 12% of volume at 3.4% fee vs Visa/MC at 2.1%. Offering cash discount on AmEx projects -CA$140/mo in fees.

## Where it lives

Source: `src/ai/agents/payment_optimizer.py` or `src/camera/payment_optimizer.py` (vision modules) or `src/ai/payment_optimizer.py` (coordination)

---

_Last updated: 2026-05-31_
_Sourced from: src/ai/agents/ + src/camera/ class-level metadata_
