from phi.flow import *  # The Dash GUI is not supported on Google colab, ignore the warning
import pylab
from phi.field._point_cloud import distribute_points
import matplotlib.pyplot as plt
import numpy as np
from mpl_toolkits.mplot3d import Axes3D

DT = 1.5
NU = 0.01

bounds = ((0,20),(0,25),(0,20))
discretization = (20, 25, 20)

INFLOW = CenteredGrid(Sphere(center=tensor([10,10,5], channel(vector='x,y,z')), radius=4), extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2],bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2])) * 0.2

smoke = CenteredGrid(0, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))  # sampled at cell centers
velocity = StaggeredGrid(0, extrapolation.ZERO, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))  # sampled in staggered form at face centers 
initial_particles = distribute_points(Sphere(center=tensor([10,10,5], channel(vector='x,y,z')), radius=4), x=discretization[0], y=discretization[1], z=discretization[2],bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))

points = initial_particles

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
        if y_coord > 0 and y_coord < 25:
            if x_coord > 0 and x_coord < 20:
                if z_coord < 20:
                # remember to adjust based on discretization
                    vectors[2][int(x_coord)][int(y_coord)][int(z_coord)] += 0.02
    
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

def step(velocity, smoke, smoke_particles, pressure, dt=1.0, buoyancy_factor=1.0):

    smoke = advect.semi_lagrangian(smoke, velocity, dt) + INFLOW
    smoke_particles = advect.points(smoke_particles, velocity, dt)

    merged_points = math.concat([smoke_particles.points, initial_particles.points], dim='points')
    smoke_particles = PointCloud(merged_points, bounds=smoke_particles.bounds)

    # buoyancy_force = (smoke * (0, 0, buoyancy_factor)).at(velocity)  # resamples smoke to velocity sample points
    buoyancy_force = CenteredGrid(generate_buoyancy, extrapolation.BOUNDARY, x=20, y=25, z=20, bounds=Box(x=(0,20),y=(0,25),z=(0,20))).at(velocity)

    velocity = advect.semi_lagrangian(velocity, velocity, dt) + dt * buoyancy_force
    velocity = diffuse.explicit(velocity, NU, dt)
    velocity, pressure = fluid.make_incompressible(velocity)

    return velocity, smoke, pressure, smoke_particles


def plot_alpha(smoke):
    # Extract the smoke values as a NumPy array
    smoke_values = np.asarray(smoke.values.numpy('x,y,z'))

    # Set up the figure and 3D axis
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Define the grid dimensions
    x_dim, y_dim, z_dim = smoke_values.shape

    # Create a 3D grid of indices
    x, y, z = np.indices((x_dim + 1, y_dim + 1, z_dim + 1))
    print(x, y, z)

    # Define the voxel colors based on the smoke density
    # alpha_values = smoke_values / np.max(smoke_values)  # Normalize to [0, 1]
    alpha_values = smoke_values / 5  # Normalize to [0, 1]

    colors = np.zeros((x_dim, y_dim, z_dim, 4))  # RGBA color array

    # Set the alpha channel based on the normalized smoke density
    colors[..., 3] = alpha_values

    # Display the voxels
    ax.voxels(x, y, z, smoke_values > 0, facecolors=colors, edgecolor='k', linewidth=0.1)
    
    # Set labels
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')

    # Show the plot
    plt.show()

velocity, smoke, pressure, points = step(velocity, smoke, initial_particles, None, dt=DT, buoyancy_factor=2)

for time_step in range(100):
    velocity, smoke, pressure, points = step(velocity, smoke, points, pressure, dt=DT, buoyancy_factor=2)
    print('Computed frame {}, max velocity {}'.format(time_step , np.max(np.asarray(smoke.values.numpy('x,y,z')))))
    if time_step % 5 == 0:
        plot(points, smoke, velocity)
        plt.show()

plot_alpha(smoke)
plt.show()

