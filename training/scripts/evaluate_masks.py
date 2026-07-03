import argparse
from pathlib import Path

import numpy as np
from PIL import Image


def load_mask(path):
    return np.asarray(Image.open(path).convert("L")) > 127


def main():
    parser = argparse.ArgumentParser(description="Evaluate predicted segmentation masks.")
    parser.add_argument("--truth", default="training/data/masks_reviewed")
    parser.add_argument("--pred", default="training/data/masks_predicted")
    args = parser.parse_args()

    truth_dir = Path(args.truth)
    pred_dir = Path(args.pred)
    scores = []

    for truth_path in sorted(truth_dir.glob("*.png")):
        pred_path = pred_dir / truth_path.name
        if not pred_path.exists():
            continue

        truth = load_mask(truth_path)
        pred = load_mask(pred_path)
        if pred.shape != truth.shape:
            pred = np.asarray(Image.fromarray(pred.astype(np.uint8) * 255).resize((truth.shape[1], truth.shape[0]))) > 127

        intersection = np.logical_and(truth, pred).sum()
        union = np.logical_or(truth, pred).sum()
        truth_sum = truth.sum()
        pred_sum = pred.sum()
        iou = intersection / union if union else 1.0
        dice = (2 * intersection) / (truth_sum + pred_sum) if (truth_sum + pred_sum) else 1.0
        scores.append((iou, dice))
        print(f"{truth_path.name}: IoU={iou:.4f} Dice={dice:.4f}")

    if not scores:
        raise SystemExit("No matching truth/predicted masks found.")

    mean_iou = sum(score[0] for score in scores) / len(scores)
    mean_dice = sum(score[1] for score in scores) / len(scores)
    print(f"Mean IoU: {mean_iou:.4f}")
    print(f"Mean Dice: {mean_dice:.4f}")


if __name__ == "__main__":
    main()
