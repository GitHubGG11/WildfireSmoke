import json
import numpy as np
from datetime import datetime, timedelta
import os

def add_seconds(start_time: str, n: int) -> str:
    # Parse the start time string into a datetime object
    dt = datetime.strptime(start_time, "%Y-%m-%dT%H:%M:%SZ")
    
    # Add n seconds using timedelta
    new_time = dt + timedelta(seconds=n)
    
    # Return the new time in the same format
    return new_time.strftime("%Y-%m-%dT%H:%M:%SZ")


def recieve_particles(new_points, czml, dT, rgb):
    # new_points = [sorted(i) for i in new_points]
    czml_c = czml.copy()
    max_length = len(czml)
    for i in range(len(new_points[0])):
        if max_length > i + 1:
            czml_c[i+1]["position"]["cartographicDegrees"] += [dT, new_points[1][i], new_points[0][i], new_points[2][i]]
        else:
            czml_c.append({
                "id": f"point_{i}",
                "availability": "2012-08-04T16:00:00Z/2012-08-04T16:05:00Z",
                "position": {
                    "epoch": "2012-08-04T16:00:00Z",
                    "cartographicDegrees": [dT, new_points[1][i], new_points[0][i], new_points[2][i]]
                },
                "point": {
                    "color": {
                    "rgba": rgb
                    },
                    "outlineColor": {
                    "rgba": [255, 0, 0, 128]
                    },
                    "outlineWidth": 3,
                    "pixelSize": 15
                }
            })
    return czml_c

def save_file(dictionary, filename):
    for i in range(len(dictionary) - 1):
        start = dictionary[i+1]["position"]["epoch"]
        end = add_seconds(start, int(dictionary[i+1]["position"]["cartographicDegrees"][-4]))
        dictionary[i+1]["availability"] = f"{start}/{end}"

    os.makedirs(os.path.dirname(filename), exist_ok=True)


    with open(filename, 'w') as f:
        json.dump(dictionary, f, indent=2)

    print(f"CZML file '{filename}' created successfully.")

