"""Export YOLO model to ONNX for edge deployment (Jetson Nano/Orin)."""
import argparse
from ultralytics import YOLO


def export(model_path: str = "yolo11n.pt", imgsz: int = 640, half: bool = False):
    model = YOLO(model_path)
    model.export(format="onnx", imgsz=imgsz, half=half, simplify=True)
    print(f"Exported {model_path} → ONNX (imgsz={imgsz}, half={half})")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="yolo11n.pt")
    parser.add_argument("--imgsz", type=int, default=640)
    parser.add_argument("--half", action="store_true")
    args = parser.parse_args()
    export(args.model, args.imgsz, args.half)
