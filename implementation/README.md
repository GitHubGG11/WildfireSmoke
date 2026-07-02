# Implementation bundle

This folder contains a simplified, standalone version of the main wildfire smoke simulation workflow from the original project.

## What is included

- Terrain and fire-spread input loading
- Smoke and weather simulation setup
- Time-stepping smoke and climate updates
- CZML export for visualization
- A small runnable entry point

## Directory layout

- `config.py` - shared configuration and paths
- `terrain.py` - terrain/elevation helpers
- `fire_data.py` - fire-spread image loading and inflow generation
- `simulation.py` - core smoke and weather step logic
- `export.py` - CZML file export
- `run_simulation.py` - runnable entry point

## Requirements

The old bundled `my_env` virtual environment may not be portable because it can point at the Python installation path from the original machine. Use your current Python instead.

Install the dependencies used by this implementation:

```powershell
python -m pip install numpy pillow requests
```

## Run the simulation

From the workspace root:

```powershell
python -m implementation.run_simulation
```

This will:

1. Load the mosquito fire world data.
2. Initialize the smoke/weather state.
3. Run a short simulation.
4. Write output to `implementation/output/smoke.czml`.

The legacy direct script form also works:

```powershell
python implementation/run_simulation.py
```

## Example package usage

Run the included example from the workspace root:

```powershell
python -m implementation.example_usage
```

Or import the package in your own code:

```python
from pathlib import Path

from implementation import (
    DEFAULT_FIRE_IMAGE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_WORLD_FILE,
    SimulationConfig,
    elevation_map,
    export_czml,
    load_fire_pixels,
    load_worldfile,
    run_simulation,
)

worldfile = load_worldfile(DEFAULT_WORLD_FILE)
bounds = worldfile["bounds"]
scale = (bounds["height"], bounds["width"], 1)
offset = (bounds["minlat"], bounds["minlon"], 0)

config = SimulationConfig(discretization=(10, 10, 25), iterations=4, seed=7)
elevation = elevation_map(config.discretization, scale, offset)
fire_pixels, image_size = load_fire_pixels(DEFAULT_FIRE_IMAGE)
load = [[1 for _ in range(config.discretization[0])] for _ in range(config.discretization[1])]

history = run_simulation(elevation, fire_pixels, image_size, load, config)
export_czml(history[-1], Path(DEFAULT_OUTPUT_DIR) / "example_smoke.czml")
```

## Notes

This implementation is intentionally simplified compared with the original research code. It keeps the essential workflow intact while making it easier to understand and run.
