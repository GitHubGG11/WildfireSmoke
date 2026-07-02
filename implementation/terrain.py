import json
import math
from pathlib import Path

from PIL import Image
import requests


def load_worldfile(path: str | Path) -> dict:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def elevation_map(discretization, scale, offset):
    """Fetch a terrain elevation map from Mapbox terrain tiles, or fall back to a synthetic field."""
    center_coords = [offset[0] + (scale[0] / 2), offset[1] + (scale[1] / 2)]
    zoom = min(20, meter_to_zoom(max(scale[0] * 111111, scale[1] * 111111)))
    x, y = to_xy(center_coords[0], center_coords[1], zoom)
    url = (
        f"https://api.mapbox.com/v4/mapbox.terrain-rgb/{zoom}/{x}/{y}.png"
        f"?access_token=pk.eyJ1IjoiYmFja3NwYWNlcyIsImEiOiJjanVrbzI4dncwOXl3M3ptcGJtN3oxMmhoIn0.x9iSCrtm0iADEqixVgPwqQ"
    )
    try:
        image = Image.open(requests.get(url, stream=True, timeout=10).raw)
        return build_elevation_map(image, discretization, scale, offset, zoom, center_coords)
    except Exception:
        return [[100 + (i + j) * 2 for i in range(discretization[0])] for j in range(discretization[1])]


def build_elevation_map(image_raw, discretization, scale, offset, zoom, center):
    map_data = [[1 for _ in range(discretization[0])] for _ in range(discretization[1])]
    image = image_raw.load()
    for height in range(discretization[1]):
        for width in range(discretization[0]):
            lat = scale[0] / discretization[0] * height + offset[0]
            lon = scale[1] / discretization[1] * width + offset[1]
            pixel_width = 156543.03 / (2**zoom) / 111111
            x = int((lat - center[0]) / pixel_width + image_raw.size[0] / 2)
            y = int((lon - center[1]) / pixel_width + image_raw.size[1] / 2)
            r, g, b, _ = image[x, y]
            map_data[height][width] = -10000 + ((r * 256**2 + g * 256 + b) * 0.1)
    return map_data


def meter_to_zoom(meters):
    return math.floor(math.log2(156543.03 * 256 / meters))


def to_xy(lat, lon, zoom):
    x = math.floor((lon + 180) / 360 * (2**zoom))
    c = (math.log(math.tan(lat * (math.pi / 180)) + 1 / math.cos(lat * (math.pi / 180)))) / math.pi
    y = math.floor((1 - c) * 2**(zoom - 1))
    return x, y
