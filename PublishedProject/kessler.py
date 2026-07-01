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
G = 10

# buoyancy constants
# z0 = 5
# dTemp = -6.5 * 6

# dTemp = -25
T0 = 295
P0 = 1.25
R = 8314
MAIR = 28.96
MW = 18.02
AIREXP = 1.4
VEXP = 1.33

def tempProfile(z, z0, dTemp):
    if z > z0:
        return T0 + z0*dTemp - dTemp*(z-z0)
    return T0 + z*dTemp

def pressureProfile(z, z0, dTemp):
    slope = dTemp if z > z0 else -dTemp
    return P0*(1 - slope/295)**(G/(R*slope))


def Mth(Xv):
    M_th = Xv*MW + (1-Xv)*MAIR
    return sum(list(M_th.values))/len(list(M_th.values))


def buoyancy(z, mth, Xv, z0, dTemp):

    Yv = Xv * (MW/mth)
    Yv = Yv*VEXP + (1-Yv)*AIREXP
    avg_exp = sum(list(Yv.values))/len(list(Yv.values))

    T_th = T0*(pressureProfile(z, z0, dTemp)/P0)**((avg_exp-1)/avg_exp)

    return G*((MAIR/mth * T_th/tempProfile(z, z0, dTemp)) - 1)

def create_buoyancy(discretization, bounds, qv, z0, dTemp):
    layers = []
    Xv = qv / (qv + 1)
    mth = Mth(Xv)

    for z in range(bounds.lower[2],discretization[2]):
        b = buoyancy(z, mth, Xv, z0, dTemp)
        layers.append(math.stack([0,0,b], dim=channel(vector="x,y,z")))

    layers = math.stack(layers, spatial("z"))
    layers = math.stack([layers] * discretization[1], spatial("y"))
    layers = math.stack([layers] * discretization[0], spatial("x"))

    return CenteredGrid(layers, extrapolation.BOUNDARY) 

def pressure_height(h):
    return 1*((1-0.0065*(h/280))**5.2561)

def initialize_points(discretization, bounds, intensity, z_scale=True):
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
    
    grid = math.stack([intensity for i in range(discretization[0])], dim=spatial("x"))
    grid = math.stack([grid for i in range(discretization[1])], dim=spatial("y"))
    if z_scale:
        grid = math.stack([grid for i in range(discretization[2])], dim=spatial("z"))
    else: 
        zeroes = math.stack([0 for i in range(discretization[0])], dim=spatial("x"))
        zeroes = math.stack([zeroes for i in range(discretization[1])], dim=spatial("y"))
        grid = math.stack([grid] + [zeroes] * (discretization[2] - 1), dim=spatial("z"))

    return PointCloud(Point(math.stack(points, dim=spatial('points'))), bounds=bounds), grid

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

def evalqvs(discretization, bounds, temperature):
    pressure_field = []
    for z in range(discretization[2]):
        pressure_field.append(math.stack([math.stack([pressure_height(z/discretization[2]*10)]*discretization[0], spatial('x'))] * discretization[1], spatial('y')))
    ISOpressure = (math.stack(pressure_field, spatial('z'))) * 10000
    qvs = 380.16/ISOpressure * math.exp((17.67*temperature)/(temperature + 243.5))
    qvs *= 0.8

    return qvs

def initializeWeather(discretization, bounds):
    rain, qr = initialize_points(discretization, bounds, 2, False)
    vapor, qv = initialize_points(discretization, bounds, 0.1)
    condensation, qc = initialize_points(discretization, bounds, 0.1)

    temperature = CenteredGrid(generateTemp(discretization, bounds), extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=bounds)
    qvs = evalqvs(discretization, bounds, temperature)

    zeroes = CenteredGrid(0, extrapolation.BOUNDARY, x=discretization[0], y=discretization[1], z=discretization[2], bounds=bounds)
    velocity = StaggeredGrid(0, extrapolation.ZERO, x=discretization[0], y=discretization[1], z=discretization[2], bounds=bounds)

    return rain, vapor, condensation, zeroes, velocity, temperature, qvs, qr


def randomized(items, randint):
    items_copy = [int(i) for i in items]
    # > 0 = 0, < 0 = 1
    for i in range(len(items)):
        if abs(items[i] - int(items_copy[i])) > randint:
            items_copy[i] += 1
            
    return items_copy

def add_points(points, discretization, grid, org, count, gravity=False):
    for p in points: 
        p = list(p)
        p[0] = float(min(max(p[0], 0), discretization[0] - 1))
        p[1] = float(min(max(p[1], 0), discretization[1] - 1))
        p_y = int(p[1])
        p_x = int(p[0])
        if gravity:
            p[2] -= G
        p[2] = float(min(max(p[2], grid[p_y][p_x] + 2), discretization[2] - 1))
        org[p_x][p_y][int(p[2])].append(p)
        count[p_x][p_y][int(p[2])] += 1
        
def updatePoints(qr, qv, qc, discretization, qvs, grid, bounds, world):

    r_points = list(qr.points.points)
    v_points = list(qv.points.points)
    c_points = list(qc.points.points)

    world_scale, world_offset, scale, min_ele, max_ele = world

    rf_points = []
    vf_points = []
    cf_points = []

    cf_lla_points = []

    l_r = len(r_points)
    l_v = len(v_points)
    l_c = len(c_points)
    randint = random.random()

    r_grid = [[[[] for k in range(discretization[2])] for i in range(discretization[1])] for i in range(discretization[0])]
    r_count = [[[0 for k in range(discretization[2])] for j in range(discretization[1])] for i in range(discretization[0])]
    add_points(r_points, discretization, grid, r_grid, r_count, True)

    c_grid = [[[[] for k in range(discretization[2])] for i in range(discretization[1])] for i in range(discretization[0])]
    c_count = [[[0 for k in range(discretization[2])] for j in range(discretization[1])] for i in range(discretization[0])]
    add_points(c_points, discretization, grid, c_grid, c_count)

    v_grid = [[[[] for k in range(discretization[2])] for i in range(discretization[1])] for i in range(discretization[0])]
    v_count = [[[0 for k in range(discretization[2])] for j in range(discretization[1])] for i in range(discretization[0])]
    add_points(v_points, discretization, grid, v_grid, v_count)

    # print(len(rf_points) + len(cf_points) + len(vf_points))

    for z in range(discretization[2]):
        for y in range(discretization[1]):
            for x in range(discretization[0]):
                r_c = r_count[x][y][z]
                if r_c != len(r_grid[x][y][z]):
                    quit()
                v_c = v_count[x][y][z]
                c_c = c_count[x][y][z]
                qvs_l = qvs[x][y][z] / contribution

                # how many points we should remove/add
                # add to vapor, remove from condensation
                EcmCc = min(qvs_l - v_c, c_c)
                # add to vapor, remove from rain
                Er = r_c*w*max(qvs_l-v_c, 0)
                # add to rain, remove from condensation
                AcKc = ba*max(c_c - aT, 0) + bk*c_c*v_c

                EcmCc, Er, AcKc = randomized([EcmCc, Er, AcKc], randint)

                if EcmCc > 0:
                    vf_points += c_grid[x][y][z][:EcmCc]
                    c_grid[x][y][z] = c_grid[x][y][z][EcmCc:]
                else:
                    cf_points += v_grid[x][y][z][:EcmCc]
                    cf_real = [[(j[i]/discretization[i] * world_scale[i]) + world_offset[i] for j in v_grid[x][y][z][:EcmCc]] for i in range(3)]
                    cf_real[2] = [((i - world_offset[2]) * (discretization[2]/world_scale[2])) - 2 for i in cf_real[2]]
                    cf_real[2] = [(i * 5 / (scale * discretization[2]/max_ele)) + min_ele for i in cf_real[2]]
                    cf_lla_points += cf_real
                    v_grid[x][y][z] = v_grid[x][y][z][EcmCc:]

                vf_points += r_grid[x][y][z][:Er]
                r_grid[x][y][z] = r_grid[x][y][z][Er:]
                    
                rf_points += c_grid[x][y][z][:AcKc]
                c_grid[x][y][z] = c_grid[x][y][z][AcKc:]

                rf_points += r_grid[x][y][z]
                cf_points += c_grid[x][y][z]
                cf_real = [[(j[i]/discretization[i] * world_scale[i]) + world_offset[i] for j in c_grid[x][y][z]] for i in range(3)]
                cf_real[2] = [((i - world_offset[2]) * (discretization[2]/world_scale[2])) - 2 for i in cf_real[2]]
                cf_real[2] = [(i * 5 / (scale * discretization[2]/max_ele)) + min_ele for i in cf_real[2]]
                cf_lla_points += cf_real
                vf_points += v_grid[x][y][z]

    placeholder = [i + 1 for i in discretization]

    if len(rf_points) == 0:
        rf_points += [placeholder]
    if len(vf_points) == 0:
        vf_points += [placeholder]
    if len(cf_points) == 0:
        cf_points += [placeholder]

    rf_points = PointCloud(Point(math.stack([math.stack(i, dim=channel(vector="x,y,z")) for i in rf_points], dim=spatial("points"))), bounds=bounds)
    vf_points = PointCloud(Point(math.stack([math.stack(i, dim=channel(vector="x,y,z")) for i in vf_points], dim=spatial("points"))), bounds=bounds)
    cf_points = PointCloud(Point(math.stack([math.stack(i, dim=channel(vector="x,y,z")) for i in cf_points], dim=spatial("points"))), bounds=bounds)
    vapor = CenteredGrid(math.stack([math.stack([math.stack(j, dim=spatial("z")) for j in i], dim=spatial("y")) for i in v_count], dim=spatial("x")))

    return rf_points, vf_points, cf_points, vapor, cf_lla_points, math.stack([math.stack([math.stack(j, dim=spatial("z")) for j in i], dim=spatial("y")) for i in r_count], dim=spatial("x"))

def climateStep(rain, vapor, condensation, velocity, dt, g, zeroes, qvs, bounds, discretization, grid, world, parameters):

    z0, dTemp = parameters

    # print(rain.points[0], rain.resolution)

    # now = datetime.datetime.now()
    qvs_n = qvs.values.numpy("x,y,z")
    rain, vapor, condensation, qv, qc_lla, qr = updatePoints(rain, vapor, condensation, discretization, qvs_n, grid, bounds, world)
    # print("Checkpoint 1:", datetime.datetime.now() - now)

    # now = datetime.datetime.now()
    b = create_buoyancy(discretization, bounds, qv, z0, dTemp).at(velocity) * 5
    # print("Checkpoint 3:", datetime.datetime.now() - now)

    # now = datetime.datetime.now()
    if len(list(vapor.points)) > 0:
        vapor = advect.points(vapor, velocity, dt)
    if len(list(condensation.points)) > 0:
        condensation = advect.points(condensation, velocity, dt)
    # print("Checkpoint 5:", datetime.datetime.now() - now)


    return rain, vapor, condensation, b, qc_lla, qv, qr
