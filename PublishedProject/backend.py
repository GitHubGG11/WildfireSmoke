import numpy as np
from sklearn.decomposition import NMF
from phi.flow import *
import multiprocessing
from shapely.geometry import Point, Polygon, box
import math as pymath
import os
import json

# (2) [-0.1, -0.1] nt {x: -1402508.3639808435, y: -4987167.565078549, z: 3708313.5192438415} nt {x: -1421200.7757084114, y: -4989583.183281137, z: 3701623.3374446365} nt {x: -0.15910593415998445, y: -0.5585926401209432, z: -0.8140390433620449} nt {x: 0.9617473722434992, y: -0.2739379345448971, z: 0} nt {x: -0.22299617417750248, y: -0.7828999108570585, z: 0.5808101547684983} {x: -0.48847446853341153, y: 0.865782419940801, z: -0.10868990253216594}

a = 6378137.0  
e2 = 6.69437999014e-3  

def lla_to_ecef(lat, lon, alt):
    lat = pymath.radians(lat)
    lon = pymath.radians(lon)
    
    n = a / pymath.sqrt(1 - e2 * pymath.sin(lat) ** 2)
    
    x = (n + alt) * pymath.cos(lat) * pymath.cos(lon)
    y = (n + alt) * pymath.cos(lat) * pymath.sin(lon)
    z = (n * (1 - e2) + alt) * pymath.sin(lat)
    
    return [x,y,z]

import numpy as np
from shapely.geometry import Polygon, box
from collections import defaultdict

def points_in_polygon(points, polygon, grid_size=0.5):
    """
    Pre-bin points into grid cells for faster lookup during scoring.

    Args:
        points: List of tuples representing points (x, y).
        polygon: List of tuples defining the vertices of the polygon.
        grid_size: Size of each grid cell (default is 0.5).

    Returns:
        within: Dictionary of TP, FP, TN, FN rates.
        scores: 1D numpy array with scores for each grid cell.
    """
    # Define the bounds of the region
    y_horizon = min([i[1] for i in polygon])
    x_min, x_max, y_min, y_max = -2, 2, y_horizon, 10
    poly = Polygon(polygon)

    # Define grid ranges
    grid_x = np.arange(x_min, x_max, grid_size)
    grid_y = np.arange(y_min, y_max, grid_size)

    # Pre-bin the points into grid cells
    bins = defaultdict(list)
    for px, py in points:
        gx = int((max(x_min, min(px, x_max)) - x_min) // grid_size)
        gy = int((max(y_min, min(py, y_max)) - y_min) // grid_size)
        bins[(gx, gy)].append((px, py))

    # Initialize results
    tp, fp, tn, fn = 0, 0, 0, 0
    scores = []

    # Process each grid cell
    for i, x in enumerate(grid_x):
        for j, y in enumerate(grid_y):
            # Define the grid cell as a Shapely box
            cell = box(x, y, x + grid_size, y + grid_size)
            cell_key = (i, j)

            # Check if the grid cell intersects the polygon
            cell_inside_polygon = cell.intersects(poly)

            # Get the points in the current grid cell
            cell_points = bins.get(cell_key, [])
            points_inside_count = len(cell_points)

            if cell_inside_polygon:
                if points_inside_count > 0:
                    tp += 1  # True positive
                    scores.append(0)  # Perfect score for TP
                else:
                    fn += 1  # False negative
                    # Score based on distance to the nearest point in the polygon
                    scores.append(poly.distance(cell))
            else:
                if points_inside_count > 0:
                    fp += 1  # False positive
                    # Score based on proximity to the polygon
                    scores.append(poly.distance(cell))
                else:
                    tn += 1  # True negative
                    scores.append(0)  # Perfect score for TN

    within = {"TP": tp, "FP": fp, "TN": tn, "FN": fn}
    return within, np.array(scores)


# discretization = (15, 15, 25)
# bounds=Box(x=(0,discretization[0]), y=(0,discretization[1]), z=(0,discretization[2]))
# velocity = StaggeredGrid(0, extrapolation.ZERO, x=discretization[0], y=discretization[1], z=discretization[2], bounds=bounds)

from concurrent.futures import ProcessPoolExecutor

# Top-level function for processing, which is required for pickling
def process_fn(args):
    i, variables, delta, fn, constants, cams = args
    temp = variables.copy()
    temp[i] += delta[i]
    return fn(i, temp, constants, cams)

def levenberg_Marquardt_step(fn, variables, l, processes, delta, constants, cams, step_i):
    jacobian = []
    y = fn(0, variables, constants, cams)
    predicted = np.array([i for i in y[1]])

    # Prepare arguments for process_fn
    tasks = [(i, variables, delta, fn, constants, cams) for i in range(len(variables))]

    with ProcessPoolExecutor(max_workers=processes) as executor:
        # Schedule each call to process_fn with the executor
        results = list(executor.map(process_fn, tasks))

        # Sort results by index
        results.sort()  # Ensure they're ordered correctly if necessary
        # print(len(results))
        # Build the Jacobian matrix using the sorted results
        temp = results[0][1] + [0] * max(0, len(predicted) - len(results[0][1]))
        test = [(temp[i] - predicted[i]) / delta[results[0][0]] for i in range(min(len(predicted), len(temp)))]
        # print(sum(test), test)
        for new_vals in results:
            add = new_vals[1] + [0] * max(0, len(predicted) - len(new_vals[1]))
            jacobian.append(np.array([(add[i] - predicted[i]) / delta[new_vals[0]] for i in range(min(len(predicted), len(add)))]))

    # Finalize the Jacobian matrix calculations
    print(sum(jacobian[0]))

    jacobian = np.transpose(np.array(jacobian))
    transpose = np.transpose(jacobian)
    # print(jacobian)
    hamiltonian = np.matmul(transpose, jacobian)

    inter = hamiltonian + np.identity(len(hamiltonian)) * l
    rs = np.matmul(transpose, -predicted)
    # print(jacobian, hamiltonian, predicted)
    step = np.matmul(np.linalg.inv(inter), rs)

    return step, predicted


def LM(fn, variables, variables_l, l, step, v, threads, delta, delta_l, constants, cams, root):
    step_i = 0
    errors = []
    full_variables = variables + [k for i in variables_l for j in i for k in j]
    print(len(full_variables))
    full_delta = delta + [delta_l[i] for i in range(len(variables_l)) for k in range(len(variables_l[i])) for j in range(len(variables_l[i][k]))]
    total_i = 0
    while step_i < step:
        increment, items = levenberg_Marquardt_step(fn, full_variables, l, threads, full_delta, constants, cams, step_i)
        old_error = sum(items)
        increment = np.concatenate([increment[:5], increment[5:]]) * 2
        full_variables += increment

        final_lm = fn(0, full_variables, constants, cams, show=True, lm_i=step_i)
        new_items = final_lm[1]

        camera_name = cams[0]
        os.makedirs(f'{root}/{camera_name[:-4]}/{step_i}', exist_ok=True)  
        os.makedirs(f'{root}/{camera_name[:-4]}/{step_i}', exist_ok=True)  

        with open(f'{root}/{camera_name[:-4]}/{step_i}/wind.txt', "w") as f:
            json.dump(final_lm[2].tolist(), f)
        with open(f'{root}/{camera_name[:-4]}/{step_i}/variables.txt', "w") as f:
            json.dump(final_lm[3], f)
            
        l /= v
        new_error = sum(new_items)
        print(new_error, old_error, increment)
        if new_error > old_error:
            l *= (v**2)
            full_variables -= increment
            total_i += 1
        else: 
            step_i += 1
            errors.append(new_error)
            total_i = 0
        # MAX 20 iterations

        if total_i > 3:
            break
    return full_variables, errors

def indexMatrices(wind, skip):
    matrix_1 = [[], [], []]
    matrix_2 = [[], [], []]
    for v, vector in enumerate(wind.unstack('vector')):
        array = []
        for i, row in enumerate(vector.unstack('y')):
            array.append(list(row))
            if (i+1) % skip == 0:
                model = NMF(n_components=2, init='random', random_state=0)
                w = model.fit_transform(array)
                h = model.components_
                matrix_1[v].append(w)
                matrix_2[v].append(h)

                array = []

    return matrix_1, matrix_2

def fn(coef):
    error = []
    for i in range(5):
        error.append(coef[0] * i + coef[1])

    return np.array(error)

def rotationMatrix(yaw, pitch, roll):
    z = np.array([[pymath.cos(yaw), -pymath.sin(yaw), 0], 
                  [pymath.sin(yaw), pymath.cos(yaw), 0], 
                  [0, 0, 1]])
    y = np.array([[pymath.cos(pitch), 0, pymath.sin(pitch)], 
                  [0, 1, 0],
                  [-pymath.sin(pitch), 0, pymath.cos(pitch)]])
    x = np.array([[1, 0, 0],
                  [0, pymath.cos(roll), -pymath.sin(roll)],
                  [0, pymath.sin(roll), pymath.cos(roll)]])

    r = np.matmul(z, np.matmul(y, x))
    # print(r, "\n\n",z, "\n\n", y, "\n\n", x)
    return r

def XYZtoUV(rotation, focal, X, aspect):
    r = rotationMatrix(-rotation[1], -rotation[2], -rotation[0])
    X = X/np.linalg.norm(X)
    # print(X, "normalized")
    final = np.matmul(np.linalg.inv(r), X)
    # print(final, "normalized")

    test = final / np.linalg.norm(final)
    # print(test[0], X)
    z,x,y = test / (test[0]/focal)
    # print(x/aspect,y)
    return x/aspect,y

def returnBasis(coord):
    '''Input in terms of lat, long, alt'''

    x,y,z = lla_to_ecef(coord[0], coord[1], coord[2])
    z_n = np.array([x,y,z]) 
    z_n = z_n / np.linalg.norm(z_n)
    y_n = np.cross(z_n, np.array([0, 0, -1]))
    y_n = y_n / np.linalg.norm(y_n)
    x_n = np.cross(y_n, z_n)
    x_n = x_n / np.linalg.norm(x_n)
    # print(x_n, y_n, z_n)

    return [x_n, y_n, z_n], [x,y,z]

def returnTransformMatrix(coord):
    new, old = returnBasis(coord)
    matrix = np.transpose(np.array([i for i in new]))
    return np.linalg.inv(matrix), old

def convertBasis(camera, points):
    matrix, old = returnTransformMatrix(camera)
    old = np.array(old)
    new_points = []
    for point in points:
        final = np.array(lla_to_ecef(point[0], point[1], point[2])) - old
        # approx = np.array(point)-np.array(camera)
        # approx = [approx[0] * 111111, approx[2], approx[1] * 111111]
        new_points.append(np.matmul(matrix, final))
    
    # print(new_points, "new points")
    
    return new_points

def projectPoints(camera, points, rotation, FOV, aspect):
    """rotation = [x,y] VAPIX
    focal in mm"""
    points = convertBasis(camera, points)
    new_points = []
    for point in points:
        # print(point)
        new_points.append(XYZtoUV([rotation[2] / 360 * (2*pymath.pi), rotation[0] / 360 * (2*pymath.pi), rotation[1] / 360 * (2*pymath.pi)], aspect/pymath.tan(FOV/2*(pymath.pi/180)), point, aspect))

    return new_points


# pitch, roll, yaw = (y, 0, x)
# VAPIX: x = left, right; y = up/down;

# r_test = rotationMatrix(-(180 + 63.950055) / (180/pymath.pi), 4.35713 / 360 * (2*pymath.pi), 0)
# coord_test = np.array([0.9977341878431866, 0.058638902650781054, -0.03298438274106435])
# print(r_test, r_test @ coord_test)


# camera = [38.801472, -120.741556, 2507]
# point = [38.99765069068132, -120.69317645872869, 1865.5004217147848]

# approx = np.array(point)-np.array(camera)
# approx = [approx[0] * 111111, approx[2], approx[1] * 111111]
# print(projectPoints(camera, [point], [-11.1, 5.3, 0], 62.5, 1920/1080), approx)


# translate
# x = left/right
# y = up/down
# z = forward/back

# rotate (do the opposite to reverse)
# tve x = clockwise, -ve x = anti-clockwise
# tve y = right, -ve y = left
# tve z = up, -ve z = down


