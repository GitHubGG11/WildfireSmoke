import os
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
IMAGES_DIR = ROOT / "images"
DEFAULT_FIRE = "mosquito"
DEFAULT_WORLD = IMAGES_DIR / DEFAULT_FIRE / "worldfiles"
DEFAULT_FIRE_IMAGE = DEFAULT_WORLD / "png_spread.png"
DEFAULT_WORLD_FILE = DEFAULT_WORLD / "worldfile.json"
DEFAULT_OUTPUT_DIR = ROOT / "implementation" / "output"


def ensure_output_dir(path: Path | None = None) -> Path:
    output_dir = path or DEFAULT_OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)
    return output_dir
