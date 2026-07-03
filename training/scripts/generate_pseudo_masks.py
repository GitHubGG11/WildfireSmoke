import argparse
from pathlib import Path

import numpy as np

from common import load_boxes, mask_name_for, require_package

cv2 = require_package("opencv-python", "cv2")


def grabcut_mask(image, box, iterations):
    h, w = image.shape[:2]
    x1, y1, x2, y2 = [int(value) for value in box]
    x1, x2 = max(0, x1), min(w - 1, x2)
    y1, y2 = max(0, y1), min(h - 1, y2)
    rect = (x1, y1, max(1, x2 - x1), max(1, y2 - y1))

    mask = np.zeros((h, w), np.uint8)
    bgd = np.zeros((1, 65), np.float64)
    fgd = np.zeros((1, 65), np.float64)
    cv2.grabCut(image, mask, rect, bgd, fgd, iterations, cv2.GC_INIT_WITH_RECT)
    return np.where((mask == cv2.GC_FGD) | (mask == cv2.GC_PR_FGD), 255, 0).astype(np.uint8)


def overlay_mask(image, mask):
    overlay = image.copy()
    color = np.zeros_like(image)
    color[:, :, 1] = 255
    blended = cv2.addWeighted(image, 0.72, color, 0.28, 0)
    overlay[mask > 0] = blended[mask > 0]
    return overlay


def main():
    parser = argparse.ArgumentParser(description="Generate GrabCut pseudo-masks from two-click boxes.")
    parser.add_argument("--boxes", default="training/data/boxes.json")
    parser.add_argument("--mask-dir", default="training/data/masks_pseudo")
    parser.add_argument("--overlay-dir", default="training/data/overlays")
    parser.add_argument("--iterations", type=int, default=5)
    args = parser.parse_args()

    mask_dir = Path(args.mask_dir)
    overlay_dir = Path(args.overlay_dir)
    mask_dir.mkdir(parents=True, exist_ok=True)
    overlay_dir.mkdir(parents=True, exist_ok=True)

    for record in load_boxes(args.boxes):
        image_path = Path(record["image"])
        image = cv2.imread(str(image_path))
        if image is None:
            print(f"Skipping unreadable image: {image_path}")
            continue

        mask = grabcut_mask(image, record["box"], args.iterations)
        mask_path = mask_dir / mask_name_for(image_path)
        overlay_path = overlay_dir / mask_name_for(image_path)
        cv2.imwrite(str(mask_path), mask)
        cv2.imwrite(str(overlay_path), overlay_mask(image, mask))
        print(f"Wrote {mask_path}")


if __name__ == "__main__":
    main()
