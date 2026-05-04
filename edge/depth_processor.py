"""
Depth Anything V2 integration for Meridian Edge Agent.

Estimates per-pixel depth from RGB frames using the Depth-Anything-V2-Small
model (ViT-S backbone). Runs on NVIDIA Jetson Orin Nano at ~15 FPS.

Depth maps stay on-prem — only aggregate metrics (zone occupancy counts,
average distances) are transmitted to cloud.
"""
import logging

import numpy as np

logger = logging.getLogger("meridian.edge.depth")

MODEL_IDS = {
    "small": "depth-anything/Depth-Anything-V2-Small",
    "base": "depth-anything/Depth-Anything-V2-Base",
    "large": "depth-anything/Depth-Anything-V2-Large",
}


class DepthProcessor:
    """Monocular depth estimation via Depth Anything V2."""

    def __init__(self, model_size: str = "small", device: str = "cuda"):
        self.device = device
        self.model_size = model_size
        self.model = None
        self.processor = None
        self._load_model()

    def _load_model(self):
        import torch
        from transformers import AutoImageProcessor, AutoModelForDepthEstimation

        model_id = MODEL_IDS.get(self.model_size, MODEL_IDS["small"])
        logger.info(f"Loading Depth Anything V2 ({self.model_size}) on {self.device}")

        self.processor = AutoImageProcessor.from_pretrained(model_id)
        self.model = AutoModelForDepthEstimation.from_pretrained(model_id)
        self.model.to(self.device)
        self.model.eval()

        logger.info("Depth model loaded")

    def estimate_depth(self, frame: np.ndarray) -> np.ndarray:
        """Return H x W float32 relative depth map. Higher = closer."""
        import torch
        from PIL import Image

        rgb = frame[:, :, ::-1]  # BGR → RGB
        image = Image.fromarray(rgb)

        inputs = self.processor(images=image, return_tensors="pt").to(self.device)
        with torch.no_grad():
            outputs = self.model(**inputs)

        depth = outputs.predicted_depth  # (1, H_model, W_model)
        depth = torch.nn.functional.interpolate(
            depth.unsqueeze(0),
            size=(frame.shape[0], frame.shape[1]),
            mode="bilinear",
            align_corners=False,
        ).squeeze()

        return depth.cpu().numpy().astype(np.float32)

    def get_zone_depths(self, depth_map: np.ndarray, zones: dict) -> dict:
        """Average depth per configured zone.

        zones format: {"entry": {"x1":0,"y1":0,"x2":200,"y2":400}, ...}
        Returns: {"entry": 0.72, "browse": 0.45, ...}
        """
        h, w = depth_map.shape[:2]
        result = {}
        for name, rect in zones.items():
            x1 = max(0, int(rect.get("x1", 0)))
            y1 = max(0, int(rect.get("y1", 0)))
            x2 = min(w, int(rect.get("x2", w)))
            y2 = min(h, int(rect.get("y2", h)))
            region = depth_map[y1:y2, x1:x2]
            if region.size > 0:
                result[name] = round(float(np.mean(region)), 4)
            else:
                result[name] = 0.0
        return result

    def estimate_distances(
        self, depth_map: np.ndarray, bboxes: list
    ) -> list[float]:
        """Median depth within each person bbox (xyxy format).

        Returns list of relative depth values, one per bbox. Lower = farther.
        """
        h, w = depth_map.shape[:2]
        distances = []
        for bbox in bboxes:
            x1 = max(0, int(bbox[0]))
            y1 = max(0, int(bbox[1]))
            x2 = min(w, int(bbox[2]))
            y2 = min(h, int(bbox[3]))
            region = depth_map[y1:y2, x1:x2]
            if region.size > 0:
                distances.append(round(float(np.median(region)), 4))
            else:
                distances.append(0.0)
        return distances

    def classify_zone_by_depth(
        self,
        depth_value: float,
        thresholds: dict | None = None,
    ) -> str:
        """Map a depth value to a semantic zone name.

        Default thresholds assume relative depth (higher = closer to camera):
          > 0.7  → "entry"    (near the camera / door)
          0.4–0.7 → "browse"  (mid-store)
          < 0.4  → "checkout" (far from camera / back)
        """
        if thresholds is None:
            thresholds = {"entry": 0.7, "browse": 0.4}
        if depth_value >= thresholds.get("entry", 0.7):
            return "entry"
        if depth_value >= thresholds.get("browse", 0.4):
            return "browse"
        return "checkout"
