from stormscapes_math import *
import matplotlib.pyplot as plt

DT = 1.5
NU = 0.01
time = 0

def reshape(stack):
    final = []
    for x_list in stack.unstack('x'):
        y = []
        for y_list in x_list.unstack('y'):
            z = []
            for z_val in y_list.unstack('z'):
                z.append(math.tensor(z_val))
            y.append(math.stack(z, spatial('z')))
        final.append(math.stack(y, spatial('y')))

    return CenteredGrid(math.stack(final, spatial('x')))

# def generate_gravity(tensorStack):
#     vectors = []
#     vectors_stack = tensorStack.unstack('vector')
#     for vector in vectors_stack:
#         z = []
#         z_stack = vector.unstack('z')
#         for z_index in range(len(z_stack)):
#             y = []
#             y_stack = z_stack[z_index].unstack('y')
#             for y_index in range(len(y_stack)):
#                 x = []
#                 x_stack = y_stack[y_index].unstack('x')
#                 for x_index in range(len(x_stack)):
#                     x.append(0)
#                 y.append(x)
#             z.append(y)
#         vectors.append(z)
    
#     for x_coord in range(len(vectors[2])):
#         for y_coord in range(len(vectors[2][x_coord])):
#             for z_coord in range(len(vectors[2][x_coord][y_coord])):
#                 vectors[2][x_coord][y_coord][z_coord] = -1
    
#     vector_stack = []
#     for vector in vectors:
#         x_new = []
#         for x_i in range(len(vector)):
#             y_new = []
#             for y_i in range(len(vector[x_i])):
#                 z_new = []
#                 for z_i in range(len(vector[x_i][y_i])):
#                     z_new.append(math.tensor(vector[x_i][y_i][z_i]))
#                 y_new.append(math.stack(z_new, spatial('z')))
#             x_new.append(math.stack(y_new, spatial('y')))
#         vector_stack.append(math.stack(x_new, spatial('x')))
#     return math.stack(vector_stack, channel(vector='x,y,z'))

def plot_alpha(smoke, label):
    # Extract the smoke values as a NumPy array
    smoke_values = np.asarray(smoke.values.numpy('x,y,z'))

    # Set up the figure and 3D axis
    fig = plt.figure(figsize=(10, 8))
    ax = fig.add_subplot(111, projection='3d')

    # Define the grid dimensions
    x_dim, y_dim, z_dim = smoke_values.shape

    # Create a 3D grid of indices
    x, y, z = np.indices((x_dim + 1, y_dim + 1, z_dim + 1))

    # Define the voxel colors based on the smoke density
    # alpha_values = smoke_values / (np.max(smoke_values))  # Normalize to [0, 1]
    alpha_values = smoke_values / 5 # Normalize to [0, 1]

    colors = np.zeros((x_dim, y_dim, z_dim, 4))  # RGBA color array

    # Set the alpha channel based on the normalized smoke density
    colors[..., 3] = alpha_values

    # Display the voxels
    ax.voxels(x, y, z, smoke_values > 0.0, facecolors=colors, edgecolor='k', linewidth=0.1)
    ax.set_title(label)
    # Set labels
    ax.set_xlabel('X')
    ax.set_ylabel('Y')
    ax.set_zlabel('Z')
    
    # Show the plot
discretization = [10, 10, 10]
bounds = ((0,discretization[0]),(0,discretization[1]),(0,discretization[2]))

qr = CenteredGrid(generateRain(discretization), extrapolation.ZERO, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))
qv = CenteredGrid(0, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))
qc = CenteredGrid(0, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))
temperature = CenteredGrid(100, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))

velocity = StaggeredGrid(0, extrapolation.ZERO, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2]))  # sampled in staggered form at face centers 
downwards = CenteredGrid((0,0,-1), extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2])).at(velocity)
gravity = 10

def step(velocity, pressure, qv, qr, qc, dt=1.0):
    qr_c = advect.semi_lagrangian(qr, velocity, dt)
    qv = advect.semi_lagrangian(qv, velocity, dt)
    qc = advect.semi_lagrangian(qc, velocity, dt)

    qr_c, qv, qc = updateFields(qr, qv, qc, discretization[0], discretization[1], discretization[2], temperature)
    # print(list(qr.values))
    buoyancy_force = CenteredGrid((0, 0, 1), extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=Box(x=bounds[0], y=bounds[1], z=bounds[2])).at(velocity)

    velocity = advect.semi_lagrangian(velocity, velocity, dt) + dt * buoyancy_force
    
    velocity = diffuse.explicit(velocity, NU, dt)
    velocity, pressure = fluid.make_incompressible(velocity)

    for i in range(gravity):
        qr = advect.semi_lagrangian(qr, downwards, 1) 
        addition = math.stack([qr.values.unstack("z")[0]] + [qr.values.unstack("z")[0] - qr.values.unstack("z")[0]] * (len(list(qr.values.unstack("z"))) - 1), spatial("z"))
        qr += reshape(addition)
        # plot_alpha(qr, "Rain")
        # plt.show()

    return velocity, pressure, qv, qr, qc

velocity, pressure, qv, qr, qc = step(velocity, None, qv, qr, qc, DT)

for i in range(50):
    velocity, pressure, qv, qr, qc = step(velocity, pressure, qv, qr, qc, DT)
    if i % 5 == 0:
        plot_alpha(qv, "Vapor")
        plot_alpha(qr, "Rain")
        plot_alpha(qc, "Condensation")
        plt.show()

