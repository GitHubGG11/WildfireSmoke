import json
from pathlib import Path


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".bmp", ".tif", ".tiff"}


def require_package(package_name, import_name=None):
    try:
        return __import__(import_name or package_name)
    except ImportError as exc:
        raise SystemExit(
            f"Missing dependency: {package_name}. Install with: python -m pip install -r training/requirements.txt"
        ) from exc


def find_images(path):
    root = Path(path)
    return sorted(file for file in root.rglob("*") if file.suffix.lower() in IMAGE_EXTENSIONS)


def load_boxes(path):
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def save_boxes(path, records):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as handle:
        json.dump(records, handle, indent=2)


def mask_name_for(image_path):
    image_path = Path(image_path)
    parts = list(image_path.with_suffix("").parts)
    if "raw" in parts:
        parts = parts[parts.index("raw") + 1 :]
    safe_stem = "__".join(parts)
    safe_stem = safe_stem.replace(":", "").replace(" ", "_")
    return f"{safe_stem}.png"
