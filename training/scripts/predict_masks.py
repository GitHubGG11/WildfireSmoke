import argparse
import sys
from pathlib import Path

import numpy as np
from PIL import Image

sys.path.append(str(Path(__file__).resolve().parents[1]))
from models.unet import UNet
from scripts.common import find_images, mask_name_for, require_package

torch = require_package("torch")


def main():
    parser = argparse.ArgumentParser(description="Predict smoke masks with a trained U-Net.")
    parser.add_argument("--images", default="training/data/raw")
    parser.add_argument("--checkpoint", default="training/checkpoints/unet_smoke.pt")
    parser.add_argument("--output", default="training/data/masks_predicted")
    parser.add_argument("--threshold", type=float, default=0.5)
    args = parser.parse_args()

    device = "cuda" if torch.cuda.is_available() else "cpu"
    checkpoint = torch.load(args.checkpoint, map_location=device)
    size = checkpoint.get("size", 256)
    model = UNet().to(device)
    model.load_state_dict(checkpoint["model"])
    model.eval()

    output_dir = Path(args.output)
    output_dir.mkdir(parents=True, exist_ok=True)

    for image_path in find_images(args.images):
        image = Image.open(image_path).convert("RGB")
        original_size = image.size
        tensor = np.asarray(image.resize((size, size)), dtype=np.float32).transpose(2, 0, 1) / 255.0
        tensor = torch.from_numpy(tensor)[None].to(device)

        with torch.no_grad():
            prob = torch.sigmoid(model(tensor))[0, 0].cpu().numpy()

        mask = (prob >= args.threshold).astype(np.uint8) * 255
        mask_image = Image.fromarray(mask).resize(original_size)
        out_path = output_dir / mask_name_for(image_path)
        mask_image.save(out_path)
        print(f"Wrote {out_path}")


if __name__ == "__main__":
    main()
