# Smoke Plume Segmentation Training

This folder contains a practical workflow for building a smoke plume segmentation dataset and training a U-Net model.

Pipeline:

```text
two-click box
-> rough mask using GrabCut pseudo-labeling
-> manually inspect/fix bad masks
-> train U-Net
-> use model predictions to label more data
-> evaluate correct predictions
```

## Install

From the project root:

```powershell
python -m pip install -r training/requirements.txt
```

PyTorch install can vary by GPU/CPU setup. If the `torch` install fails, use the command from:

```text
https://pytorch.org/get-started/locally/
```

## Folder Layout

```text
training/
  data/
    raw/                 # input images
    boxes.json           # two-click plume boxes
    masks_pseudo/        # GrabCut masks
    masks_reviewed/      # manually accepted/fixed masks
    masks_predicted/     # model-predicted masks for more data
    overlays/            # quick visual checks
  checkpoints/           # trained model weights
  scripts/
  models/
```

Put source images in:

```text
training/data/raw
```

You can also point the scripts at another image folder.

## 1. Two-Click Boxes

Click the upper-left and lower-right corners around the plume.

```powershell
python training/scripts/annotate_boxes.py --images training/data/raw --output training/data/boxes.json
```

Controls:

- left click twice: save current box and advance
- `r`: reset current box
- `n`: skip image
- `q`: quit

Use `--manual-save` if you want the older behavior where `s` saves after the two clicks.

## 2. Generate Pseudo-Masks

Uses OpenCV GrabCut from the two-click boxes.

```powershell
python training/scripts/generate_pseudo_masks.py --boxes training/data/boxes.json --mask-dir training/data/masks_pseudo --overlay-dir training/data/overlays
```

## 3. Inspect/Fix Masks

```powershell
python training/scripts/review_masks.py --boxes training/data/boxes.json --mask-dir training/data/masks_pseudo --reviewed-dir training/data/masks_reviewed
```

Controls:

- left drag: paint foreground
- right drag: erase/background
- `+` / `-`: brush size
- `a`: accept and save
- `n`: skip
- `r`: reset to original pseudo-mask
- `q`: quit

## 4. Train U-Net

```powershell
python training/scripts/train_unet.py --images training/data/raw --masks training/data/masks_reviewed --checkpoint training/checkpoints/unet_smoke.pt --epochs 25
```

## 5. Predict More Masks

```powershell
python training/scripts/predict_masks.py --images training/data/raw --checkpoint training/checkpoints/unet_smoke.pt --output training/data/masks_predicted
```

Then run `review_masks.py` on `masks_predicted` to accept/fix model labels.

## 6. Evaluate

```powershell
python training/scripts/evaluate_masks.py --truth training/data/masks_reviewed --pred training/data/masks_predicted
```

Reports mean IoU and Dice score.
