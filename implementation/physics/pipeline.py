import math
import random
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

from ..config import DEFAULT_FIRE_IMAGE, DEFAULT_OUTPUT_DIR, DEFAULT_WORLD_FILE
from ..fire_data import load_fire_pixels
from ..terrain import elevation_map, load_worldfile
from .czml import export_time_dynamic_czml
from .kessler import KesslerConfig, kessler_step


@dataclass
class PhysicsConfig:
    discretization: tuple[int, int, int] = (18, 18, 30)
    iterations: int = 18
    dt: float = 1.5
    max_particles: int = 450
    inflow_per_step: int = 45
    seed: int = 11
    wind_east: float = 0.035
    wind_north: float = 0.018
    buoyancy: float = 0.085
    diffusion: float = 0.08
    smoke_color: tuple[int, int, int, int] = (45, 45, 45, 120)
    cloud_color: tuple[int, int, int, int] = (215, 215, 205, 95)
    kessler: KesslerConfig = field(default_factory=KesslerConfig)


def _world_params(worldfile):
    bounds = worldfile["bounds"]
    scale = (bounds["height"], bounds["width"], 1)
    offset = (bounds["minlat"], bounds["minlon"], 0)
    return bounds, scale, offset


def _grid_to_lonlat(point, bounds, discretization, elevation_base=0.0):
    x, y, z = point
    lon = bounds["minlon"] + (x / max(1, discretization[0] - 1)) * bounds["width"]
    lat = bounds["minlat"] + (y / max(1, discretization[1] - 1)) * bounds["height"]
    height = elevation_base + max(0.0, z) * 42.0
    return lon, lat, height


def _fire_candidates(fire_pixels, image_size, discretization, rng):
    width, height = image_size
    candidates = []
    for _, (px, py), _ in fire_pixels:
      x = (px / max(1, width) + 0.5) * (discretization[0] - 1)
      y = (py / max(1, height) + 0.5) * (discretization[1] - 1)
      if 0 <= x < discretization[0] and 0 <= y < discretization[1]:
          candidates.append((x, y, 2.0 + rng.random() * 2.0))
    return candidates


def _sample_fire_points(candidates, limit, rng):
    rng.shuffle(candidates)
    return candidates[:limit]


def _state_fields(discretization):
    shape = discretization
    vapor = np.full(shape, 0.004, dtype=float)
    cloud = np.zeros(shape, dtype=float)
    rain = np.zeros(shape, dtype=float)
    temperature = np.zeros(shape, dtype=float)
    heights = np.zeros(shape, dtype=float)

    for z in range(discretization[2]):
        temperature[:, :, z] = 28.0 - z * 0.55
        heights[:, :, z] = z * 42.0

    return vapor, cloud, rain, temperature, heights


def _deposit_heat_and_moisture(points, temperature, vapor, cloud, discretization):
    for x, y, z in points:
        ix = min(discretization[0] - 1, max(0, int(round(x))))
        iy = min(discretization[1] - 1, max(0, int(round(y))))
        iz = min(discretization[2] - 1, max(0, int(round(z))))
        temperature[ix, iy, iz] += 0.35
        vapor[ix, iy, iz] += 0.0008
        cloud[ix, iy, iz] += 0.0002


def _advance_particles(points, temperature, discretization, config, rng):
    next_points = []
    for x, y, z in points:
        ix = min(discretization[0] - 1, max(0, int(round(x))))
        iy = min(discretization[1] - 1, max(0, int(round(y))))
        iz = min(discretization[2] - 1, max(0, int(round(z))))
        thermal = max(0.0, temperature[ix, iy, iz] - 28.0) * 0.008

        x += config.wind_east * config.dt + (rng.random() - 0.5) * config.diffusion
        y += config.wind_north * config.dt + (rng.random() - 0.5) * config.diffusion
        z += (config.buoyancy + thermal) * config.dt + (rng.random() - 0.35) * config.diffusion

        if 0 <= x < discretization[0] and 0 <= y < discretization[1] and z < discretization[2]:
            next_points.append((x, y, max(1.0, z)))

    return next_points


def run_physics_simulation(fire_image=DEFAULT_FIRE_IMAGE, world_file=DEFAULT_WORLD_FILE, config=None):
    config = config or PhysicsConfig()
    rng = random.Random(config.seed)
    worldfile = load_worldfile(world_file)
    bounds, scale, offset = _world_params(worldfile)
    terrain = elevation_map((config.discretization[0], config.discretization[1], config.discretization[2]), scale, offset)
    min_elevation = min(value for row in terrain for value in row)

    fire_pixels, image_size = load_fire_pixels(fire_image)
    candidates = _fire_candidates(fire_pixels, image_size, config.discretization, rng)
    particles = _sample_fire_points(candidates[:], config.max_particles, rng)
    vapor, cloud, rain, temperature, heights = _state_fields(config.discretization)

    smoke_histories = [[] for _ in range(config.max_particles)]
    cloud_histories = [[] for _ in range(max(1, config.max_particles // 4))]

    for step in range(config.iterations):
        seconds = step * config.dt * 60
        new_inflow = _sample_fire_points(candidates[:], config.inflow_per_step, rng)
        particles = (particles + new_inflow)[-config.max_particles:]

        _deposit_heat_and_moisture(particles, temperature, vapor, cloud, config.discretization)
        vapor, cloud, rain, _ = kessler_step(vapor, cloud, rain, temperature, heights, config.dt, config.kessler)
        particles = _advance_particles(particles, temperature, config.discretization, config, rng)
        temperature *= 0.992

        for index, point in enumerate(particles[: config.max_particles]):
            lon, lat, height = _grid_to_lonlat(point, bounds, config.discretization, min_elevation)
            smoke_histories[index].append((seconds, lon, lat, height))

        cloud_indices = np.argwhere(cloud > np.percentile(cloud, 96))
        for index, cell in enumerate(cloud_indices[: len(cloud_histories)]):
            x, y, z = [float(value) for value in cell]
            lon, lat, height = _grid_to_lonlat((x, y, z + 2), bounds, config.discretization, min_elevation)
            cloud_histories[index].append((seconds, lon, lat, height))

    return smoke_histories, cloud_histories


def generate_czml(output_dir=DEFAULT_OUTPUT_DIR, config=None):
    output_dir = Path(output_dir)
    smoke, clouds = run_physics_simulation(config=config)
    smoke_path = export_time_dynamic_czml(smoke, output_dir / "physics_smoke.czml", name="Physics Smoke", color=(45, 45, 45, 120))
    cloud_path = export_time_dynamic_czml(clouds, output_dir / "physics_clouds.czml", name="Physics Clouds", color=(220, 220, 210, 90))
    return smoke_path, cloud_path
