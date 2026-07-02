try:
    from .config import DEFAULT_FIRE_IMAGE, DEFAULT_WORLD_FILE, DEFAULT_OUTPUT_DIR, ensure_output_dir
    from .fire_data import load_fire_pixels
    from .simulation import SimulationConfig, run_simulation
    from .terrain import elevation_map, load_worldfile
    from .export import export_czml
except ImportError:
    from config import DEFAULT_FIRE_IMAGE, DEFAULT_WORLD_FILE, DEFAULT_OUTPUT_DIR, ensure_output_dir
    from fire_data import load_fire_pixels
    from simulation import SimulationConfig, run_simulation
    from terrain import elevation_map, load_worldfile
    from export import export_czml


def run_default_simulation(output_path=None, iterations=4, seed=7):
    output_dir = ensure_output_dir(DEFAULT_OUTPUT_DIR)
    output_path = output_path or output_dir / "smoke.czml"
    worldfile = load_worldfile(DEFAULT_WORLD_FILE)
    bounds = worldfile["bounds"]
    scale = (bounds["height"], bounds["width"], 1)
    offset = (bounds["minlat"], bounds["minlon"], 0)

    discretization = (10, 10, 25)
    elevation = elevation_map(discretization, scale, offset)
    fire_pixels, dim = load_fire_pixels(DEFAULT_FIRE_IMAGE)
    load = [[1 for _ in range(discretization[0])] for _ in range(discretization[1])]

    history = run_simulation(
        elevation,
        fire_pixels,
        dim,
        load,
        SimulationConfig(discretization=discretization, iterations=iterations, seed=seed),
    )

    final_points = history[-1]
    export_czml(final_points, output_path)
    return output_path, history


def main():
    output_path, history = run_default_simulation()
    print(f"Simulation complete. Wrote {output_path} with {len(history[-1])} smoke points.")


if __name__ == "__main__":
    main()
