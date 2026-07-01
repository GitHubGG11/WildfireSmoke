import math
import json
from PIL import Image
import requests
import numpy as np


def returnInfo(scale, offset):
    centerCoords = [offset[0] + (scale[0]/2), offset[1] + (scale[1]/2)]
    z = min(20, meterstoZoom(max(scale[0]*111111, scale[1]*111111)))
    x, y = toXY(centerCoords[0], centerCoords[1], z)
    url = f"https://api.mapbox.com/v4/mapbox.terrain-rgb/{z}/{x}/{y}.png?access_token=pk.eyJ1IjoiYmFja3NwYWNlcyIsImEiOiJjanVrbzI4dncwOXl3M3ptcGJtN3oxMmhoIn0.x9iSCrtm0iADEqixVgPwqQ"

    return url, (x,y,z), centerCoords

def returnEleMap(image_raw, discretization, scale, offset, z, center):
    map = [[1 for i in range(discretization[0])] for j in range(discretization[1])]
    # map[y][x] but image[x, y]
    image = image_raw.load()
    for height in range(discretization[1]):
        for width in range(discretization[0]):
            lat, long = (scale[0]/discretization[0] * height + offset[0], scale[1]/discretization[1] * width + offset[1])
            pix_width = 156543.03 / (2**z)
            pix_width /= 111111
            x, y = ((lat - center[0]) / pix_width, (long - center[1]) / pix_width)
            x,y = (int(x + (image_raw.size[0]/2)), int(y + (image_raw.size[1]/2)))
            r, g, b, a = image[x, y]
            map[height][width] = -10000 + ((r * 256**2 + g * 256 + b) * 0.1)
    
    return map

def meterstoZoom(m):
    return math.floor(math.log2(156543.03 * 256/m))

def toXY(lat, long, z):
    x = math.floor((long+180)/360 * (2**z))
    c = (math.log(math.tan(lat * (math.pi/180)) + ((1)/(math.cos(lat*((math.pi)/180)))) )) / (math.pi)
    y = math.floor((1-c) * 2**(z-1))
    return x,y

def eleMap(discretization, scale, offset):
    url, (x,y,z), center = returnInfo(scale, offset)
    im = Image.open(requests.get(url, stream=True).raw)

    return returnEleMap(im, discretization, scale, offset, z, center)