"""
Meridian Vision Intelligence — edge-side analytics engine.

Pipeline: Camera → YOLO detect → BoxMOT track → InsightFace recognize
  → DeepFace demographics → Supervision zones → batch upload to cloud.

All CV processing runs on merchant edge hardware. Only anonymized
metrics are transmitted to the Meridian cloud API.
"""
from .detector import PersonDetector
from .tracker import PersonTracker
from .face_engine import FaceEngine
from .zone_analytics import ZoneAnalytics
from .pipeline import VisionPipeline

__all__ = [
    "PersonDetector",
    "PersonTracker",
    "FaceEngine",
    "ZoneAnalytics",
    "VisionPipeline",
]
