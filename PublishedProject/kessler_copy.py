from phi.flow import * 
from phi import *
import pylab
from phi.field._point_cloud import distribute_points
import matplotlib.pyplot as plt
from phi.geom import *
import random
import numpy as np
import datetime


contribution = 0.3
rain = []
vapor = []
condensation = []

# kessler constants
aT = 0.005
bk = 0.5
ba = 0.0025
w = 0.2

# wind constants
G = 2

# buoyancy constants
z0 = 5
dTemp = -6.5 * 6
# dTemp = -25
T0 = 295
P0 = 1.25
R = 8314
MAIR = 28.96
MW = 18.02
AIREXP = 1.4
VEXP = 1.33


#TODO: Optimize these functions

def tempProfile(z):
    if z > z0:
        return T0 + z0*dTemp - dTemp*(z-z0)
    return T0 + z*dTemp

def pressureProfile(z):
    slope = dTemp if z > z0 else -dTemp
    return P0*(1 - slope/295)**(G/(R*slope))

def Xi(mass_frac):
    return mass_frac / (mass_frac + 1)

def Mth(qv):
    Xv = Xi(qv)
    M_th = Xv*MW + (1-Xv)*MAIR
    return sum(list(M_th.values))/len(list(M_th.values))

def YV(qv):
    Xv = Xi(qv)
    m_th = Mth(qv)
    return Xv * (MW/m_th)

def TH_EXP(qv):
    Yv = YV(qv)
    return Yv*VEXP + (1-Yv)*AIREXP

def T_th(z, qv):
    Yv = TH_EXP(qv)
    avg_exp = sum(list(Yv.values))/len(list(Yv.values))
    return T0*(pressureProfile(z)/P0)**((avg_exp-1)/avg_exp)

def buoyancy(z, qv):
    return G*((MAIR/Mth(qv) * T_th(z, qv)/tempProfile(z)) - 1)

def create_buoyancy(discretization, bounds, qv):
    layers = []
    for z in range(bounds.lower[2],discretization[2]):
        b = buoyancy(z, qv)
        print("Buoyancy:", b, z)
        layer = math.stack([math.stack([math.stack([0,0,b], dim=channel(vector="x,y,z"))]*discretization[0], spatial('x'))] * discretization[1], spatial("y"))
        layers.append(layer)
    
    return reshape(math.stack(layers, spatial("z")))

def organize_points(points, discretization):
    grid = [[[[] for i in range(discretization[2])] for j in range(discretization[1])] for k in range(discretization[0])]
    for x_coord, y_coord, z_coord in zip(list(points.points[0]), list(points.points[1]), list(points.points[2])):
        if x_coord < discretization[0] and x_coord >= 0:
            if y_coord < discretization[1] and y_coord >= 0:
                if z_coord < discretization[2] and z_coord >= 0:
                    grid[int(x_coord)][int(y_coord)][int(z_coord)].append([x_coord, y_coord, z_coord])
    
    return grid

def unstack_grid(grid):
    return [[list(j) for j in i.unstack('y')] for i in grid.values.unstack('x')]

def stack_grid(grid):
    x_new = []
    for x_i in range(len(grid)):
        y_new = []
        for y_i in range(len(grid[x_i])):
            z_new = []
            for z_i in range(len(grid[x_i][y_i])):
                z_new.append(math.tensor(grid[x_i][y_i][z_i]))
            y_new.append(math.stack(z_new, spatial('z')))
        x_new.append(math.stack(y_new, spatial('y')))
    return CenteredGrid(math.stack(x_new, spatial('x')))

def toPoints(grid, bounds):
    points = []
    hasPoint = False
    for x_i in range(len(grid)):
        for y_i in range(len(grid[x_i])):
            for z_i in range(len(grid[x_i][y_i])):
                for point in grid[x_i][y_i][z_i]:
                    points.append(math.stack([float(j) for j in point], dim=channel(vector='x,y,z')))
                    hasPoint = True
    if not hasPoint:
        return PointCloud(Point(math.stack([math.stack([bounds.upper[0] + 1, bounds.upper[1] + 1, bounds.upper[2] + 1], dim=channel(vector='x,y,z'))], dim=spatial('points'))))
    return PointCloud(Point(math.stack(points, dim=spatial('points'))), bounds=bounds)

def mergePoints(points1, points2):
    return PointCloud(math.concat([points1.points, points2.points], dim='points'), bounds=points1.bounds)

def point_selection(points1, points2, grid, discretization,bounds):
    """+ve = add to 1, -ve = add to 2"""
    org_points1 = organize_points(points1, discretization)
    org_points2 = organize_points(points2, discretization)
    adding1 = []
    adding2 = []
    grid = unstack_grid(grid)

    for x_i in range(len(grid)):
        for y_i in range(len(grid[x_i])):
            for z_i in range(len(grid[x_i][y_i])):
                if grid[x_i][y_i][z_i] > 0:
                    remove_points = abs(int(grid[x_i][y_i][z_i]))
                    if (grid[x_i][y_i][z_i] - remove_points) > random.random():
                        remove_points += 1
                    remove_points = min(len(org_points1[x_i][y_i][z_i]), remove_points)
                    for adding in org_points1[x_i][y_i][z_i][:remove_points]:
                        adding2.append(math.stack([float(adding[0]), float(adding[1]), float(adding[2]) + 0.5], dim=channel(vector='x,y,z')))
                    org_points1[x_i][y_i][z_i] = org_points1[x_i][y_i][z_i][remove_points:]
                else:
                    remove_points = abs(int(grid[x_i][y_i][z_i]))
                    if (grid[x_i][y_i][z_i] - remove_points) > random.random():
                        remove_points += 1
                    remove_points = min(len(org_points2[x_i][y_i][z_i]), remove_points)
                    for adding in org_points2[x_i][y_i][z_i][:remove_points]:
                        adding1.append(math.stack([float(adding[0]), float(adding[1]), float(adding[2]) + 0.5], dim=channel(vector='x,y,z')))
                    org_points2[x_i][y_i][z_i] = org_points2[x_i][y_i][z_i][remove_points:]
    
    org_points1 = toPoints(org_points1, bounds)
    org_points2 = toPoints(org_points2, bounds)

    returned_items = [org_points1, org_points2] 

    if len(adding1) > 0:
        adding1 = PointCloud(Point(math.stack(adding1, dim=spatial('points'))), bounds=bounds)
        returned_items[0] = mergePoints(org_points1, adding1)
    if len(adding2) > 0:
        adding2 = PointCloud(Point(math.stack(adding2, dim=spatial('points'))), bounds=bounds)
        returned_items[1] = mergePoints(org_points2, adding2)
    return returned_items[0], returned_items[1]

def max_grid(grid1, grid2):
    grid1_lst = unstack_grid(grid1)
    grid2_lst = unstack_grid(grid2)
    for row in range(len(grid1_lst)):
        for column in range(len(grid1_lst[row])):
            for value in range(len(grid1_lst[row][column])):
                grid1_lst[row][column][value] = math.tensor(max(grid2_lst[row][column][value], grid1_lst[row][column][value]))
    
    return CenteredGrid(math.stack([math.stack([math.stack(j, spatial('z')) for j in i], spatial('y')) for i in grid1_lst], spatial('x')))

def min_grid(grid1, grid2):
    grid1_lst = unstack_grid(grid1)
    grid2_lst = unstack_grid(grid2)
    for row in range(len(grid1_lst)):
        for column in range(len(grid1_lst[row])):
            for value in range(len(grid1_lst[row][column])):
                grid1_lst[row][column][value] = math.tensor(min(grid2_lst[row][column][value], grid1_lst[row][column][value]))
    
    return CenteredGrid(math.stack([math.stack([math.stack(j, spatial('z')) for j in i], spatial('y')) for i in grid1_lst], spatial('x')))

def pressure_height(h):
    return 1*((1-0.0065*(h/280))**5.2561)

def createGrid(points, contribution, discretization):
    grid = [[[0 for i in range(discretization[2])] for j in range(discretization[1])] for k in range(discretization[0])]
    for x_coord, y_coord, z_coord in zip(list(points.points[0]), list(points.points[1]), list(points.points[2])):
        if x_coord < discretization[0] and x_coord >= 0:
            if y_coord < discretization[1] and y_coord >= 0:
                if z_coord < discretization[2] and z_coord >= 0:
                    grid[int(x_coord)][int(y_coord)][int(z_coord)] += contribution
    
    return stack_grid(grid)

def initialize_points(discretization, bounds,  intensity, z_scale=True):
    points = []
    for x in range(int(discretization[0] * intensity)):
        for y in range(int(discretization[1] * intensity)):
            if z_scale:
                for z in range(int(discretization[2]*intensity)):
                    points.append(math.stack([x/intensity, y/intensity, z/intensity], dim=channel(vector="x,y,z")))
            else:
                points.append(math.stack([x/intensity, y/intensity, 0], dim=channel(vector="x,y,z")))
    if len(points) == 0:
        points.append(math.stack([-1, -1, -1], dim=channel(vector="x,y,z")))
    return PointCloud(Point(math.stack(points, dim=spatial('points'))), bounds=bounds)

def reshape(stack, make_grid=True):
    final = []
    for x_list in stack.unstack('x'):
        y = []
        for y_list in x_list.unstack('y'):
            z = []
            for z_val in y_list.unstack('z'):
                z.append(math.tensor(z_val))
            y.append(math.stack(z, spatial('z')))
        final.append(math.stack(y, spatial('y')))
    
    final = math.stack(final, spatial('x'))
    if make_grid:
        return CenteredGrid(final, extrapolation.BOUNDARY)
    return final

def generateTemp(discretization, bounds):
    layers = []
    for z in range(bounds.lower[2],discretization[2]):
        layer = math.stack([math.stack([32-z*5]*discretization[0], spatial('x'))] * discretization[1], spatial("y"))
        layers.append(layer)
    
    return reshape(math.stack(layers, spatial("z")), make_grid=False)

def gravity(points, gravity, bounds):
    new_points = [math.stack([float(points.points[0][i]), float(points.points[1][i]), float(points.points[2][i] - gravity)], dim=channel(vector="x,y,z")) for i in range(len(points.points[0]))]
    return PointCloud(Point(math.stack(new_points, dim=spatial('points'))), bounds=bounds)

def bound(points, bounds_l, bounds, grid):
    scale = 0.3
    min_ele = min([i for j in grid for i in j])
    max_ele = max([i - min_ele for j in grid for i in j])
    if max_ele == 0:
        max_ele = 1

    new_points = [math.stack([min(max(points.points[0][i], bounds.lower[0]), bounds_l[0]), min(max(points.points[1][i], float(bounds.lower[1])), bounds_l[1]), min(max(points.points[2][i], (grid[int(points.points[1][i])][int(points.points[0][i])] - min_ele) * (scale * bounds_l[2]/max_ele)), bounds_l[2])], dim=channel(vector="x,y,z")) for i in range(len(points.points[0]))]
    return PointCloud(Point(math.stack(new_points, dim=spatial('points'))), bounds=points.bounds)

def evalqvs(discretization, bounds, temperature):
    pressure_field = []
    for z in range(discretization[2]):
        pressure_field.append(math.stack([math.stack([pressure_height(z/discretization[2]*10)]*discretization[0], spatial('x'))] * discretization[1], spatial('y')))
    ISOpressure = (math.stack(pressure_field, spatial('z'))) * 10000
    qvs = 380.16/ISOpressure * math.exp((17.67*temperature)/(temperature + 243.5))
    qvs *= 0.8

    return qvs

def initializeWeather(discretization, bounds):
    rain = initialize_points(discretization, bounds, 4, False)
    vapor = initialize_points(discretization, bounds, 0.1)
    condensation = initialize_points(discretization, bounds, 0.1)

    temperature = CenteredGrid(generateTemp(discretization, bounds), extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=bounds)
    qvs = evalqvs(discretization, bounds, temperature)

    zeroes = CenteredGrid(0, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=bounds)
    velocity = StaggeredGrid(0, extrapolation.ZERO, x=discretization[0], y=discretization[1], z=discretization[2], bounds=bounds)

    return rain, vapor, condensation, zeroes, velocity, temperature, qvs

def climateStep(rain, vapor, condensation, velocity, dt, g, zeroes, qvs, bounds, discretization, grid):

    time_now = datetime.datetime.now()
    qr = createGrid(rain, contribution, discretization)
    qv = createGrid(vapor, contribution, discretization)
    qc = createGrid(condensation, contribution, discretization)

    EcmCc = min_grid(qvs - qv, qc)/contribution
    Er = qr*w*max_grid(qvs-qv, zeroes)/contribution
    Ac = ba*max_grid(qc - aT, zeroes)/contribution
    Kc = bk*qc*qr/contribution

    b = create_buoyancy(discretization, bounds, qv).at(velocity) * 5
    
    rain, vapor = point_selection(rain, vapor, Er, discretization, bounds)
    condensation, vapor = point_selection(condensation, vapor, EcmCc, discretization, bounds) 
    condensation, rain = point_selection(condensation, rain, Ac, discretization, bounds)
    condensation, rain = point_selection(condensation, rain, Kc, discretization, bounds)

    rain = bound(gravity(rain, g, bounds), discretization, bounds, grid)
    vapor = bound(advect.points(vapor, velocity, dt), discretization, bounds, grid)
    condensation = bound(advect.points(condensation, velocity, dt), discretization, bounds, grid)

    return rain, vapor, condensation, b
