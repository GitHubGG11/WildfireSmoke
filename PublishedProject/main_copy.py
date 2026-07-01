# simulation modules
from stormscapes import stepSmoke, initializeSmoke
from kessler import initializeWeather, climateStep, evalqvs, reshape

from phi.flow import * 
from phi import *
import pylab
from phi.field._point_cloud import distribute_points
import matplotlib.pyplot as plt
from phi.geom import *
import random
import numpy as np
from fire_interpolation import *
import json

time = 0
DT = 1.5
G = 2
NU = 0.05

discretization = (15, 15, 25)
bounds=Box(x=(0,discretization[0]), y=(0,discretization[1]), z=(0,discretization[2]))
rain, vapor, condensation, zeroes, velocity, temperature, qvs = initializeWeather(discretization, bounds)
world_scale, world_offset, fire_pixels, smoke_particles, grid, dim, ele_map = initializeSmoke(discretization, bounds)

pressure = None

if __name__ == "__main__":
    for i in range(100):
        smoke_particles, temp_grid = stepSmoke(velocity, smoke_particles, time, discretization, bounds, fire_pixels, dim, DT, ele_map)
        temp_grid = reshape(temp_grid)
        qvs = evalqvs(discretization, bounds, temperature + temp_grid * 20)
        rain, vapor, condensation, b = climateStep(rain, vapor, condensation, velocity, DT, G, zeroes, qvs, bounds, discretization, ele_map)

        velocity = advect.semi_lagrangian(velocity, velocity, DT) + DT * b
        velocity = diffuse.explicit(velocity, NU, DT)
        velocity, pressure = fluid.make_incompressible(velocity)

        if i % 3 == 0:
            plot(smoke_particles, velocity)
            plot(rain, vapor, condensation)
            plt.show()

        time += DT

