import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image
from tqdm import tqdm

sys.path.append(str(Path(__file__).resolve().parents[1]))
from models.unet import UNet
from scripts.common import find_images, mask_name_for, require_package

torch = require_package("torch")
from torch.utils.data import DataLoader, Dataset


class SmokeDataset(Dataset):
    def __init__(self, image_dir, mask_dir, size):
        self.image_paths = [path for path in find_images(image_dir) if (Path(mask_dir) / mask_name_for(path)).exists()]
        self.mask_dir = Path(mask_dir)
        self.size = (size, size)

    def __len__(self):
        return len(self.image_paths)

    def __getitem__(self, index):
        image_path = self.image_paths[index]
        mask_path = self.mask_dir / mask_name_for(image_path)

        image = Image.open(image_path).convert("RGB").resize(self.size)
        mask = Image.open(mask_path).convert("L").resize(self.size)
        image = np.asarray(image, dtype=np.float32).transpose(2, 0, 1) / 255.0
        mask = (np.asarray(mask, dtype=np.float32)[None, :, :] > 127).astype(np.float32)
        return torch.from_numpy(image), torch.from_numpy(mask)


def dice_loss(logits, targets, smooth=1.0):
    probs = torch.sigmoid(logits)
    intersection = (probs * targets).sum(dim=(1, 2, 3))
    total = probs.sum(dim=(1, 2, 3)) + targets.sum(dim=(1, 2, 3))
    return 1 - ((2 * intersection + smooth) / (total + smooth)).mean()


def main():
    parser = argparse.ArgumentParser(description="Train U-Net smoke plume segmentation.")
    parser.add_argument("--images", default="training/data/raw")
    parser.add_argument("--masks", default="training/data/masks_reviewed")
    parser.add_argument("--checkpoint", default="training/checkpoints/unet_smoke.pt")
    parser.add_argument("--epochs", type=int, default=25)
    parser.add_argument("--batch-size", type=int, default=4)
    parser.add_argument("--size", type=int, default=256)
    parser.add_argument("--lr", type=float, default=1e-3)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dataset = SmokeDataset(args.images, args.masks, args.size)
    if len(dataset) == 0:
        raise SystemExit("No image/mask pairs found. Review masks before training.")

    loader = DataLoader(dataset, batch_size=args.batch_size, shuffle=True)
    model = UNet().to(device)
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr)
    bce = torch.nn.BCEWithLogitsLoss()

    for epoch in range(args.epochs):
        model.train()
        running = 0.0
        progress = tqdm(loader, desc=f"epoch {epoch + 1}/{args.epochs}")
        for images, masks in progress:
            images, masks = images.to(device), masks.to(device)
            logits = model(images)
            loss = bce(logits, masks) + dice_loss(logits, masks)
            optimizer.zero_grad()
            loss.backward()
            optimizer.step()
            running += loss.item()
            progress.set_postfix(loss=f"{running / max(1, progress.n):.4f}")

    checkpoint = Path(args.checkpoint)
    checkpoint.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"model": model.state_dict(), "size": args.size}, checkpoint)
    print(f"Wrote {checkpoint}")


if __name__ == "__main__":
    main()
