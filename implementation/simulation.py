import math
import random
from dataclasses import dataclass

import numpy as np


@dataclass
class SimulationConfig:
    discretization: tuple[int, int, int] = (10, 10, 25)
    scale: float = 0.1
    dt: float = 1.5
    iterations: int = 6
    seed: int | None = None


def initialize_state(discretization, elevation_map, load, fire_pixels, dim):
    smoke_points = []
    for y in range(discretization[1]):
        for x in range(discretization[0]):
            smoke_points.append((x, y, 2))

    velocity = np.zeros((discretization[0], discretization[1], discretization[2], 3), dtype=float)
    temperature = np.full((discretization[0], discretization[1], discretization[2]), 300.0)
    moisture = np.zeros((discretization[0], discretization[1], discretization[2]), dtype=float)
    return smoke_points, velocity, temperature, moisture


def step_simulation(smoke_points, velocity, temperature, moisture, elevation_map, discretization, config, rng=None):
    rng = rng or random
    next_points = []
    for point in smoke_points:
        x, y, z = point
        x_new = min(discretization[0] - 1, max(0, x + 0.2 + rng.random() * 0.1))
        y_new = min(discretization[1] - 1, max(0, y + 0.1 + rng.random() * 0.1))
        elevation = elevation_map[int(y_new)][int(x_new)]
        z_new = min(discretization[2] - 1, max(2, z + 0.4 + (temperature[int(x_new)][int(y_new)][int(z)] - 300) / 100))
        next_points.append((x_new, y_new, z_new))

    velocity = velocity * 0.95
    temperature = temperature + 0.1
    moisture = np.maximum(0.0, moisture - 0.01)
    return next_points, velocity, temperature, moisture


def run_simulation(elevation_map, fire_pixels, dim, load, config=None):
    config = config or SimulationConfig()
    rng = random.Random(config.seed) if config.seed is not None else random
    smoke_points, velocity, temperature, moisture = initialize_state(config.discretization, elevation_map, load, fire_pixels, dim)

    history = []
    for step in range(config.iterations):
        smoke_points, velocity, temperature, moisture = step_simulation(
            smoke_points,
            velocity,
            temperature,
            moisture,
            elevation_map,
            config.discretization,
            config,
            rng,
        )
        history.append(smoke_points)
    return history
