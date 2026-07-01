from PIL import Image
import numpy as np
import random
from phi.flow import *
from phi.geom import *
from phi.field._point_cloud import distribute_points
from requestelevation import eleMap

def process_image(image_path):
    # Load the image
    image = Image.open(image_path)
    image = image.convert("RGB")
    pixels = np.array(image)

    # Get the dimensions of the image
    height, width, _ = pixels.shape
    stored_pixels = []

    for y in range(height): 
        for x in range(width): 
            r, g, b = pixels[y, x]
            if random.randint(1, 500) == 100 and (r, g, b) != (255, 255, 255):
                # Transform (x, y) to have (0,0) at the center
                transformed_x = x - width // 2
                transformed_y = height // 2 - y

                pixel_value = int(r) * 255**2 + int(g) * 255 + int(b)
                stored_pixels.append((pixel_value, (transformed_x, transformed_y), (r, g, b)))

    return stored_pixels, (width, height)

def returnTimeStamp(path):
    stored_pixels, dim = process_image(path)
    stored_pixels.sort()
    return stored_pixels, dim

def returnInflow(pixels, time, map, dim, bounds, discret, scale, load, factor=100000):
    # Bounds should have a center at (0,0)
    items = []
    min_ele = min([i for j in map for i in j])
    max_ele = max([i - min_ele for j in map for i in j])
    if max_ele == 0:
        max_ele = 1

    for pixel in pixels:
        if pixel[0]/factor <= time:
            x, y = (((pixel[1][0]/dim[0]) + 0.5) * discret[0], ((pixel[1][1]/dim[1]) + 0.5) * discret[1])
            ele = (map[int(math.floor(y))][int(math.floor(x))] - min_ele) * (scale * discret[2]/max_ele)
            if load[int(y)][int(x)] != 0:
                items.append(math.stack([x, y, ele + 2], dim=channel(vector='x,y,z')))            
    # print(items, "items", load)

    return PointCloud(Point(math.stack(items, dim=spatial('points'))), bounds=bounds)

def returnInflowGrid(pixels, time, map, dim, bounds, discret, scale, temp=False, factor=100000, both=False):
    # Bounds should have a center at (0,0)
    items = [[[0 for i in range(discret[0])] for j in range(discret[1])] for k in range(discret[2])]
    if type(temp) != bool:
        temperature = [[[0 for i in range(discret[0])] for j in range(discret[1])] for k in range(discret[2])]
    if both:
        floor = [[0.0 for i in range(discret[0])] for j in range(discret[1])]
    min_ele = min([i for j in map for i in j])
    max_ele = max([i - min_ele for j in map for i in j])
    if max_ele == 0:
        max_ele = 1

    for pixel in pixels:
        if pixel[0]/factor <= time:
            x, y = (((pixel[1][0]/dim[0]) + 0.5) * discret[0], ((pixel[1][1]/dim[1]) + 0.5) * discret[1])
            ele = (map[int(math.floor(y))][int(math.floor(x))] - min_ele) * (scale * discret[2]/max_ele)
            items[int(ele) + 2][int(y)][int(x)] += 0.1
            if type(temp) != bool:
                temperature[int(ele) + 2][int(y)][int(x)] += 0.1 * temp[int(y)][int(x)]
            if both:
                floor[int(y)][int(x)] = 1.0
    
    if type(temp) != bool:
        temperature = math.stack([math.stack([math.stack(j, spatial('x')) for j in i], spatial('y')) for i in temperature], spatial('z'))
    else:
        temperature = None

    if both: 
        return math.stack([math.stack([math.stack(j, spatial('x')) for j in i], spatial('y')) for i in items], spatial('z')), floor, temperature

    return math.stack([math.stack([math.stack(j, spatial('x')) for j in i], spatial('y')) for i in items], spatial('z')), temperature
