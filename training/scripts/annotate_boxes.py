import argparse
import random
from collections import defaultdict
from pathlib import Path

from common import find_images, load_boxes, require_package, save_boxes

cv2 = require_package("opencv-python", "cv2")


def draw_state(image, points):
    canvas = image.copy()
    if len(points) == 1:
        cv2.circle(canvas, points[0], 5, (0, 255, 255), -1)
    if len(points) == 2:
        cv2.rectangle(canvas, points[0], points[1], (0, 255, 255), 2)
    return canvas


def sample_images_by_folder(images, root, images_per_dir, seed):
    if images_per_dir is None:
        return images

    root = Path(root).resolve()
    rng = random.Random(seed)
    groups = defaultdict(list)

    for image_path in images:
        parent = image_path.resolve().parent
        try:
            group_key = parent.relative_to(root)
        except ValueError:
            group_key = parent
        groups[str(group_key)].append(image_path)

    selected = []
    for group_images in groups.values():
        group_images = sorted(group_images)
        if len(group_images) <= images_per_dir:
            selected.extend(group_images)
            continue
        selected.extend(rng.sample(group_images, images_per_dir))

    return sorted(selected)


def main():
    parser = argparse.ArgumentParser(description="Two-click plume bounding-box annotation.")
    parser.add_argument("--images", default="training/data/raw")
    parser.add_argument("--output", default="training/data/boxes.json")
    parser.add_argument("--manual-save", action="store_true", help="Require pressing s after two clicks instead of auto-saving.")
    parser.add_argument("--images-per-dir", type=int, default=3, help="Random images to annotate from each raw subfolder. Default: 3")
    parser.add_argument("--all-images", action="store_true", help="Annotate every image instead of sampling per subfolder.")
    parser.add_argument("--seed", type=int, default=7, help="Random seed for per-folder image sampling. Default: 7")
    args = parser.parse_args()

    images = find_images(args.images)
    if not images:
        raise SystemExit(f"No images found in {args.images}")
    images = sample_images_by_folder(
        images,
        root=args.images,
        images_per_dir=None if args.all_images else args.images_per_dir,
        seed=args.seed,
    )
    print(f"Annotating {len(images)} sampled images.")

    existing = {}
    if Path(args.output).exists():
        existing = {record["image"]: record for record in load_boxes(args.output)}

    records = list(existing.values())
    window = "two-click plume box"

    for image_path in images:
        image_key = str(image_path.as_posix())
        if image_key in existing:
            continue

        image = cv2.imread(str(image_path))
        if image is None:
            continue

        points = []

        def on_mouse(event, x, y, flags, param):
            if event == cv2.EVENT_LBUTTONDOWN and len(points) < 2:
                points.append((x, y))

        cv2.namedWindow(window, cv2.WINDOW_NORMAL)
        cv2.setMouseCallback(window, on_mouse)

        while True:
            canvas = draw_state(image, points)
            help_text = "2 clicks auto-save | r reset | n skip | q quit"
            if args.manual_save:
                help_text = "2 clicks box | s save | r reset | n skip | q quit"
            cv2.putText(canvas, help_text, (12, 28), cv2.FONT_HERSHEY_SIMPLEX, 0.75, (255, 255, 255), 2)
            cv2.imshow(window, canvas)
            key = cv2.waitKey(30) & 0xFF

            if len(points) == 2 and (not args.manual_save or key == ord("s")):
                (x1, y1), (x2, y2) = points
                left, right = sorted([x1, x2])
                top, bottom = sorted([y1, y2])
                records.append({"image": image_key, "box": [left, top, right, bottom]})
                save_boxes(args.output, records)
                cv2.imshow(window, draw_state(image, points))
                cv2.waitKey(120)
                break
            if key == ord("r"):
                points = []
            if key == ord("n"):
                break
            if key == ord("q"):
                save_boxes(args.output, records)
                cv2.destroyAllWindows()
                return

    cv2.destroyAllWindows()
    save_boxes(args.output, records)


if __name__ == "__main__":
    main()
