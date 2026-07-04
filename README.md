# Wildfire Smoke

**Live demo:** https://githubgg11.github.io/WildfireSmoke/implementation/demo/viewer.html?

This project is a cleaned-up wildfire smoke visualization and simulation workspace. The main thing to look at first is the Cesium demo above: it loads CZML smoke particle output, adds a denser visual point cloud, and lets you inspect saved wildfire camera views in the browser.

## System Design Overview

This project is an end-to-end wildfire smoke data pipeline and visualization system.

The system ingests wildfire perimeter data, historical weather parameters, vegetation/fuel data, and camera metadata from multiple public sources. These inputs are normalized into a common simulation format, passed through a Python smoke-plume simulation backend, and exported as CZML files that can be rendered in a browser using CesiumJS.

At a high level, the workflow is:

1. **Data ingestion**: collect wildfire perimeters, weather parameters, fuel/vegetation values, and camera metadata from public datasets and scraped sources.
2. **Preprocessing**: convert heterogeneous geospatial and meteorological inputs into simulation-ready parameters.
3. **Simulation**: run a simplified smoke plume model with wind, buoyancy, diffusion, and cloud/rain dynamics.
4. **Export**: serialize smoke particle outputs into CZML.
5. **Visualization**: render saved wildfire scenarios in an interactive CesiumJS web viewer hosted on GitHub Pages.

The goal of the project is not only to simulate wildfire smoke, but to demonstrate a full-stack scientific computing workflow: data ingestion, preprocessing, numerical modeling, output serialization, and browser-based geospatial visualization.

## Project Background

For the accompanying writeup, see [Technical_Report.pdf](Technical_Report.pdf). This project is also associated with the AMS conference abstract here: [2025 AMS abstract](https://ui.adsabs.harvard.edu/abs/2025AMS...10556614H/abstract).

## What Is In This Repo

- `implementation/` - simplified Python implementation of the smoke simulation workflow
- `implementation/demo/` - GitHub Pages-compatible Cesium CZML viewer
- `implementation/physics/` - physics-oriented CZML generator with wind, buoyancy, diffusion, and Kessler-style cloud/rain updates
- `demo/` - local copy of the static demo files
- `training/` - smoke plume segmentation training utilities

## Demo

Open the hosted viewer here:

```text
https://githubgg11.github.io/WildfireSmoke/implementation/demo/viewer.html?
```

The demo includes saved camera views for:

- Mosquito: Rock Creek
- Electra: Red Corall
- Summit Fire: Meadow Lakes

To run the demo locally from the project root:

```powershell
python -m http.server 8000 --bind 127.0.0.1
```

Then open:

```text
http://127.0.0.1:8000/implementation/demo/index.html
```

Do not open the HTML directly with `file://`; Cesium needs HTTP requests to load CZML files correctly.

## Running The Implementation

Install the basic Python dependencies:

```powershell
python -m pip install numpy pillow requests
```

Run the simplified smoke simulation:

```powershell
python -m implementation.run_simulation
```

This writes CZML output under:

```text
implementation/output/
```

## Physics CZML Generator

The physics generator lives in `implementation/physics/`.

Run:

```powershell
python -m implementation.physics.generate
```

Expected outputs:

```text
implementation/output/physics_smoke.czml
implementation/output/physics_clouds.czml
```

Those files can be added to `implementation/demo/demos.js` to show a new generated run in the Cesium demo.

## Notes

This repo came from older research code, so the current structure favors a readable demo and a compact implementation over preserving every original experiment exactly. The CZML demo is the best entry point for understanding the visual output.
