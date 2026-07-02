"""Standalone implementation of the wildfire smoke simulation workflow."""

from .config import (
    DEFAULT_FIRE_IMAGE,
    DEFAULT_OUTPUT_DIR,
    DEFAULT_WORLD_FILE,
    ensure_output_dir,
)
from .export import export_czml
from .fire_data import build_inflow_points, load_fire_pixels, process_image
from .simulation import SimulationConfig, initialize_state, run_simulation, step_simulation
from .terrain import elevation_map, load_worldfile


def __getattr__(name):
    if name == "run_default_simulation":
        from .run_simulation import run_default_simulation

        return run_default_simulation
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "DEFAULT_FIRE_IMAGE",
    "DEFAULT_OUTPUT_DIR",
    "DEFAULT_WORLD_FILE",
    "SimulationConfig",
    "build_inflow_points",
    "elevation_map",
    "ensure_output_dir",
    "export_czml",
    "initialize_state",
    "load_fire_pixels",
    "load_worldfile",
    "process_image",
    "run_default_simulation",
    "run_simulation",
    "step_simulation",
]
