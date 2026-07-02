import json
from datetime import datetime, timedelta, timezone
from pathlib import Path


def _packet(point_id, samples, color, pixel_size):
    cartographic = []
    for seconds, lon, lat, height in samples:
        cartographic.extend([round(seconds, 3), lon, lat, height])

    return {
        "id": point_id,
        "availability": "2012-08-04T16:00:00Z/2012-08-04T16:20:00Z",
        "position": {
            "epoch": "2012-08-04T16:00:00Z",
            "cartographicDegrees": cartographic,
        },
        "point": {
            "pixelSize": pixel_size,
            "color": {"rgba": color},
            "outlineWidth": 0,
        },
    }


def export_time_dynamic_czml(histories, output_path, color=(55, 55, 55, 130), pixel_size=8, name="Smoke Simulation"):
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    start = datetime(2012, 8, 4, 16, tzinfo=timezone.utc)
    stop = start + timedelta(minutes=20)
    document = {
        "id": "document",
        "name": name,
        "version": "1.0",
        "clock": {
            "interval": f"{start.isoformat().replace('+00:00', 'Z')}/{stop.isoformat().replace('+00:00', 'Z')}",
            "currentTime": start.isoformat().replace("+00:00", "Z"),
            "multiplier": 60,
        },
    }

    packets = [document]
    for index, samples in enumerate(histories):
        if samples:
            packets.append(_packet(f"{name.lower().replace(' ', '_')}_{index}", samples, list(color), pixel_size))

    with open(output_path, "w", encoding="utf-8") as handle:
        json.dump(packets, handle, indent=2)

    return output_path
