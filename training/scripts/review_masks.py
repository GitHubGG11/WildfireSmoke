import argparse
from pathlib import Path

import numpy as np

from common import load_boxes, mask_name_for, require_package

cv2 = require_package("opencv-python", "cv2")


def make_overlay(image, mask):
    overlay = image.copy()
    green = np.zeros_like(image)
    green[:, :, 1] = 255
    blended = cv2.addWeighted(image, 0.68, green, 0.32, 0)
    overlay[mask > 0] = blended[mask > 0]
    return overlay


def main():
    parser = argparse.ArgumentParser(description="Review and lightly edit segmentation masks.")
    parser.add_argument("--boxes", default="training/data/boxes.json")
    parser.add_argument("--mask-dir", default="training/data/masks_pseudo")
    parser.add_argument("--reviewed-dir", default="training/data/masks_reviewed")
    args = parser.parse_args()

    reviewed_dir = Path(args.reviewed_dir)
    reviewed_dir.mkdir(parents=True, exist_ok=True)
    window = "review smoke mask"

    for record in load_boxes(args.boxes):
        image_path = Path(record["image"])
        mask_path = Path(args.mask_dir) / mask_name_for(image_path)
        out_path = reviewed_dir / mask_name_for(image_path)

        if out_path.exists() or not mask_path.exists():
            continue

        image = cv2.imread(str(image_path))
        original = cv2.imread(str(mask_path), cv2.IMREAD_GRAYSCALE)
        if image is None or original is None:
            continue

        mask = original.copy()
        brush = 18
        drawing = {"active": False, "value": 255}

        def on_mouse(event, x, y, flags, param):
            nonlocal mask
            if event == cv2.EVENT_LBUTTONDOWN:
                drawing["active"] = True
                drawing["value"] = 255
            elif event == cv2.EVENT_RBUTTONDOWN:
                drawing["active"] = True
                drawing["value"] = 0
            elif event in (cv2.EVENT_LBUTTONUP, cv2.EVENT_RBUTTONUP):
                drawing["active"] = False

            if drawing["active"] or event in (cv2.EVENT_LBUTTONDOWN, cv2.EVENT_RBUTTONDOWN):
                cv2.circle(mask, (x, y), brush, drawing["value"], -1)

        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window, on_mouse)

        while True:
            canvas = make_overlay(image, mask)
            cv2.putText(canvas, "left fg | right bg | +/- brush | a accept | r reset | n skip | q quit", (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
            cv2.putText(canvas, f"brush {brush}", (12, 58), cv2.FONT_HERSHEY_SIMPLEX, 0.65, (255, 255, 255), 2)
            cv2.imshow(window, canvas)
            key = cv2.waitKey(20) & 0xFF

            if key == ord("a"):
                cv2.imwrite(str(out_path), mask)
                print(f"Accepted {out_path}")
                break
            if key == ord("r"):
                mask = original.copy()
            if key in (ord("+"), ord("=")):
                brush = min(120, brush + 4)
            if key in (ord("-"), ord("_")):
                brush = max(2, brush - 4)
            if key == ord("n"):
                break
            if key == ord("q"):
                cv2.destroyAllWindows()
                return

    cv2.destroyAllWindows()


if __name__ == "__main__":
    main()
