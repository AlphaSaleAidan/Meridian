# The vision detector stack (people_counter → supervision/YOLO) is heavy and optional:
# the camera-connect flow (src.camera.streaming) only needs stdlib + httpx. Guard the
# eager imports so a slim API deployment (or a test box without the ML wheels) can still
# import src.camera.streaming without pulling in supervision/ultralytics.
try:  # pragma: no cover - exercised only when ML deps are installed
    from .people_counter import MeridianPeopleCounter, CountResult
    from .zone_loader import load_zones_for_camera, load_entry_lines
    from .supabase_writer import CameraDataWriter

    __all__ = [
        "MeridianPeopleCounter",
        "CountResult",
        "load_zones_for_camera",
        "load_entry_lines",
        "CameraDataWriter",
    ]
except ModuleNotFoundError:  # vision ML deps not present in this environment
    __all__ = []
