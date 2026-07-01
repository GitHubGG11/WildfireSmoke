

from phi.flow import *  # The Dash GUI is not supported on Google colab, ignore the warning
import pylab
from phi.field._point_cloud import distribute_points
import matplotlib.pyplot as plt
import numpy as np
from fire_interpolation import *
import json
from czml_creation import *

DT = 1.5
NU = 0.01
time = 0

discretization = [10, 10, 10]
worldfile = json.load(open("NMSFC_hermits_peak.json"))["bounds"]
world_scale = (worldfile["height"], worldfile["width"], 1)
world_offset = (worldfile["minlat"], worldfile["minlon"], 0)

fire_pixels, dim = returnTimeStamp('NMSFC_hermits_peak.png')

# temperature = CenteredGrid(32, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))
# temperature += grid * 1000

points = initial_particles

czml_data = [
    {
        "id": "document",
        "name": "Particle Simulation",
        "version": "1.0"
    }
]

def generate_buoyancy(tensorStack):
    vectors = []
    vectors_stack = tensorStack.unstack('vector')
    for vector in vectors_stack:
        z = []
        z_stack = vector.unstack('z')
        for z_index in range(len(z_stack)):
            y = []
            y_stack = z_stack[z_index].unstack('y')
            for y_index in range(len(y_stack)):
                x = []
                x_stack = y_stack[y_index].unstack('x')
                for x_index in range(len(x_stack)):
                    x.append(0)
                y.append(x)
            z.append(y)
        vectors.append(z)
    
    for x_coord, y_coord, z_coord in zip(list(points.points[0]), list(points.points[1]), list(points.points[2])):
        if y_coord > 0 and round(y_coord) < discretization[1] - 1:
            if x_coord > 0 and round(x_coord) < discretization[0] - 1:
                if round(z_coord) < discretization[2] - 1 and z_coord > 0:
                # remember to adjust based on discretization
                    vectors[2][round(x_coord)][round(y_coord)][round(z_coord)] += 0.06
                    # vectors[0][round(x_coord)][round(y_coord)][round(z_coord)] = 0.5
    
    vector_stack = []
    for vector in vectors:
        x_new = []
        for x_i in range(len(vector)):
            y_new = []
            for y_i in range(len(vector[x_i])):
                z_new = []
                for z_i in range(len(vector[x_i][y_i])):
                    z_new.append(math.tensor(vector[x_i][y_i][z_i]))
                y_new.append(math.stack(z_new, spatial('z')))
            x_new.append(math.stack(y_new, spatial('y')))
        vector_stack.append(math.stack(x_new, spatial('x')))
    return math.stack(vector_stack, channel(vector='x,y,z'))

def stepSmoke(velocity, smoke_particles, pressure, time, dt=1.0):
    smoke_particles = advect.points(smoke_particles, velocity, dt)

    grid = returnInflowGrid(fire_pixels, 0, bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]), discret=discretization, dim=dim)
    temperature = CenteredGrid(32, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))
    temperature += grid * 1000

    inflow = returnInflow(fire_pixels, time, bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]), discret=discretization, dim=dim)
    
    merged_points = math.concat([smoke_particles.points, inflow.points], dim='points')
    smoke_particles = PointCloud(merged_points, bounds=smoke_particles.bounds)

    buoyancy_force = CenteredGrid(generate_buoyancy, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2])).at(velocity)

    velocity = advect.semi_lagrangian(velocity, velocity, dt) + dt * buoyancy_force
    velocity = diffuse.explicit(velocity, NU, dt)
    velocity, pressure = fluid.make_incompressible(velocity)

    # for all points
    return velocity, pressure, smoke_particles, time+dt

velocity, pressure, points, time = stepSmoke(velocity, initial_particles, None, time, dt=DT)


for time_step in range(15):
    translated_points = [[(j/discretization[i] * world_scale[i]) + world_offset[i] for j in list(points.points.unstack('vector')[i])] for i in range(3)]
    czml_data = recieve_particles(translated_points, czml_data, time-DT)
    velocity, pressure, points, time = step(velocity, initial_particles, pressure, time, dt=DT)
    print('Computed frame {}'.format(time_step))
    if time_step % 1 == 0:
        plot(points, velocity)
        plt.show()

# save_file(czml_data, "smokeData.czml")