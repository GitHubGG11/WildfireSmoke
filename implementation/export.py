import json
from pathlib import Path


def export_czml(points, output_path):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    document = {
        "id": "document",
        "name": "Smoke Simulation",
        "version": "1.0",
        "clock": {
            "interval": "2012-08-04T16:00:00Z/2012-08-04T16:05:00Z",
            "currentTime": "2012-08-04T16:00:00Z",
            "multiplier": 1,
        },
    }

    features = []
    for index, point in enumerate(points):
        x, y, z = point
        features.append(
            {
                "id": f"point_{index}",
                "position": {
                    "cartographicDegrees": [0.0, y, x, z],
                },
                "point": {
                    "pixelSize": 8,
                    "color": {"rgba": [255, 255, 255, 180]},
                },
            }
        )

    payload = [document] + features
    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle, indent=2)
