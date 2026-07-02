"""Small example showing how to use the implementation package."""

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


def main():
    worldfile = load_worldfile(DEFAULT_WORLD_FILE)
    bounds = worldfile["bounds"]
    scale = (bounds["height"], bounds["width"], 1)
    offset = (bounds["minlat"], bounds["minlon"], 0)

    config = SimulationConfig(discretization=(10, 10, 25), iterations=4, seed=7)
    elevation = elevation_map(config.discretization, scale, offset)
    fire_pixels, image_size = load_fire_pixels(DEFAULT_FIRE_IMAGE)
    load = [[1 for _ in range(config.discretization[0])] for _ in range(config.discretization[1])]

    history = run_simulation(elevation, fire_pixels, image_size, load, config)
    output_path = Path(DEFAULT_OUTPUT_DIR) / "example_smoke.czml"
    export_czml(history[-1], output_path)

    print(f"Wrote {output_path}")
    print(f"Frames: {len(history)}")
    print(f"Final smoke points: {len(history[-1])}")


if __name__ == "__main__":
    main()
