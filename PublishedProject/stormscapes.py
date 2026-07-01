import pylab
import matplotlib.pyplot as plt
import numpy as np
from fire_interpolation import *
import json
from czml_creation import *
from requestelevation import eleMap
import random
from temperature import returnMassTemp

def initializeSmoke(discretization, bounds, scale, load, root):
    
    worldfile = json.load(open(f"./images/{root}/worldfiles/worldfile.json"))["bounds"]
    world_scale = (worldfile["height"], worldfile["width"], 1)
    world_offset = (worldfile["minlat"], worldfile["minlon"], 0)

    fire_pixels, dim = returnTimeStamp(f'./images/{root}/worldfiles/png_spread.png')
    ele_map = eleMap(discretization, world_scale, world_offset) 
    smoke_particles = returnInflow(fire_pixels, 0, ele_map, bounds=bounds, discret=discretization, dim=dim, scale=scale, load=load)
    grid, temp = returnInflowGrid(fire_pixels, 0, ele_map, bounds=bounds, discret=discretization, dim=dim, scale=scale)

    return world_scale, world_offset, fire_pixels, smoke_particles, grid, dim, ele_map

def stepSmoke(velocity, smoke_particles, time, discretization, bounds, fire_pixels, dim, dt, ele_map, factor, scale, fuel):
    sur_to_density, density, load, qr, Mx = fuel
    qr_list = []
    x_u = qr.unstack('x')
    for x_list in range(len(x_u)):
        y = []
        y_u = x_u[x_list].unstack("y")
        for y_list in range(len(y_u)):
            z_u = y_u[y_list].unstack('z')
            add = 0
            for z_val in range(len(z_u)):
                if z_u[z_val] != 0:
                    add = z_u[z_val]
            y.append(add)
        qr_list.append(y)
        
    limit = 20000
    qr_list = np.array(qr_list)

    dM, dT = returnMassTemp(sur_to_density, density, load, np.array(qr_list), Mx)

    smoke_particles = advect.points(smoke_particles, velocity, dt)

    grid, floor, temp = returnInflowGrid(fire_pixels, time, ele_map, bounds=bounds, discret=discretization, dim=dim, factor=factor, scale=scale, both=True, temp=dT)
    dM = np.array(floor) * dM
    load = np.subtract(load.astype(float), (dM * factor).astype(float))
    load = np.maximum(0, load)

    inflow = returnInflow(fire_pixels, time, ele_map, bounds=bounds, discret=discretization, dim=dim, factor=factor, scale=scale, load=load)
    
    merged_points = math.concat([smoke_particles.points, inflow.points], dim='points')
    merged_points = math.stack(random.sample(merged_points.unstack('points'), min(len(merged_points.points), limit)), spatial('points'))

    smoke_particles = PointCloud(merged_points, bounds=smoke_particles.bounds)

    # for all points
    return smoke_particles, grid, temp
