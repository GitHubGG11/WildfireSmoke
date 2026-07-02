# Physics CZML Generator

This folder contains a compact, package-friendly physics generator for CZML output.

It includes:

- fire-spread image inflow
- wind, diffusion, heat-driven buoyancy
- Kessler-style vapor/cloud/rain updates
- time-dynamic CZML export for smoke and cloud particles

Run from the workspace root:

```powershell
python -m implementation.physics.generate
```

Outputs:

```text
implementation/output/physics_smoke.czml
implementation/output/physics_clouds.czml
```

Tune the simulation by importing `PhysicsConfig`:

```python
from implementation.physics import PhysicsConfig, generate_czml

config = PhysicsConfig(iterations=24, max_particles=800, buoyancy=0.12)
smoke_path, cloud_path = generate_czml(config=config)
```
