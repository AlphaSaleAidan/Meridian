"""Cline — Self-healing IT agent for Meridian.

Monitors system health, detects errors, auto-remediates when safe,
and escalates when not. Uses the Karpathy 5-phase reasoning loop
for structured diagnosis.
"""
from .agent import ClineAgent, ClineDiagnosis, RemediationResult
from .error_detector import ErrorDetector
from .remediator import Remediator, RemediationLevel

__all__ = [
    "ClineAgent",
    "ClineDiagnosis",
    "RemediationResult",
    "ErrorDetector",
    "Remediator",
    "RemediationLevel",
]
