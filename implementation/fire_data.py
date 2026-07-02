import math
from pathlib import Path

import numpy as np
from PIL import Image


def process_image(image_path):
    image = Image.open(image_path).convert("RGB")
    pixels = np.array(image)
    height, width, _ = pixels.shape
    stored_pixels = []
    for y in range(height):
        for x in range(width):
            r, g, b = pixels[y, x]
            if (r, g, b) != (255, 255, 255):
                transformed_x = x - width // 2
                transformed_y = height // 2 - y
                pixel_value = int(r) * 255**2 + int(g) * 255 + int(b)
                stored_pixels.append((pixel_value, (transformed_x, transformed_y), (r, g, b)))
    return stored_pixels, (width, height)


def load_fire_pixels(path):
    return process_image(path)


def build_inflow_points(pixels, elevation_map, discretization, dim, scale, load, factor=100000):
    points = []
    min_elevation = min(value for row in elevation_map for value in row)
    max_elevation = max(value - min_elevation for row in elevation_map for value in row)
    max_elevation = max_elevation or 1

    for pixel in pixels:
        if pixel[0] / factor <= 1:
            x = ((pixel[1][0] / dim[0]) + 0.5) * discretization[0]
            y = ((pixel[1][1] / dim[1]) + 0.5) * discretization[1]
            elevation = (elevation_map[int(math.floor(y))][int(math.floor(x))] - min_elevation) * (scale * discretization[2] / max_elevation)
            if load[int(y)][int(x)] != 0:
                points.append((x, y, elevation + 2))
    return points
