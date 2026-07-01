from phi.flow import *  # The Dash GUI is not supported on Google colab, ignore the warning
import pylab
from phi.field._point_cloud import distribute_points
import matplotlib.pyplot as plt

def pressure_height(h):
    return 1*((1-0.0065*(h/280))**5.2561)

def max_grid(grid1, grid2):
    grid1_lst = [[list(j) for j in i.unstack('y')] for i in grid1.values.unstack('x')]
    grid2_lst = [[list(j) for j in i.unstack('y')] for i in grid2.values.unstack('x')]
    for row in range(len(grid1_lst)):
        for column in range(len(grid1_lst[row])):
            for value in range(len(grid1_lst[row][column])):
                grid1_lst[row][column][value] = math.tensor(max(grid2_lst[row][column][value], grid1_lst[row][column][value]))
    
    return math.stack([math.stack([math.stack(j, spatial('z')) for j in i], spatial('y')) for i in grid1_lst], spatial('x'))

def min_grid(grid1, grid2):
    grid1_lst = [[list(j) for j in i.unstack('y')] for i in grid1.values.unstack('x')]
    grid2_lst = [[list(j) for j in i.unstack('y')] for i in grid2.values.unstack('x')]
    for row in range(len(grid1_lst)):
        for column in range(len(grid1_lst[row])):
            for value in range(len(grid1_lst[row][column])):
                grid1_lst[row][column][value] = math.tensor(min(grid2_lst[row][column][value], grid1_lst[row][column][value]))
    
    return math.stack([math.stack([math.stack(j, spatial('z')) for j in i], spatial('y')) for i in grid1_lst], spatial('x'))


def updateFields(qr, qv, qc, x_discr, y_discr, z_discr, temperature):
    aT = 0.001
    bk = 0.5
    ba = 0.0025
    w = 0.4

    pressure_field = []
    for z in range(z_discr):
        pressure_field.append(math.stack([math.stack([pressure_height(z/z_discr*10)]*x_discr, spatial('x'))] * y_discr, spatial('y')))
    ISOpressure = (math.stack(pressure_field, spatial('z'))) * 10000

    zeroes = CenteredGrid(0, extrapolation.BOUNDARY, x=x_discr, y=y_discr, z=z_discr, bounds=Box(x=(0,10),y=(0,10), z=(0,10)))

    qvs = 380.16/ISOpressure * math.exp((17.67*temperature)/(temperature + 243.5))
    qvs *= 0.8

    EcmCc = CenteredGrid(min_grid(qvs - qv, qc))
    Er = qr*w*CenteredGrid(max_grid(qvs-qv, zeroes))
    Ac = ba*CenteredGrid(max_grid(qc - aT, zeroes))
    Kc = bk*qc*qr

    # plot(Er, qvs-qv,EcmCc)

    # print(min(list(qv.values)), max(list(qv.values)), min(list(qvs.values)), max(list(qvs.values)), min(EcmCc.values), max(EcmCc.values))
    # print(list(Kc.values), list(Er.values))
    qv += EcmCc + Er
    qc = qc - Ac - Kc - EcmCc
    qr += Ac + Kc - Er

    return qr, qv, qc

def generateRain(discret):
    items = [[math.tensor(0.8)]*discret[0]]*discret[1]
    items =  [items] + [[([0]*discret[0])]*discret[1]] * (discret[2]-1)
    items = math.stack([math.stack([math.stack(j, spatial('x')) for j in i], spatial('y')) for i in items], spatial('z'))
    # restack :(
    final = []
    for x_list in items.unstack('x'):
        y = []
        for y_list in x_list.unstack('y'):
            z = []
            for z_val in y_list.unstack('z'):
                z.append(math.tensor(z_val))
            y.append(math.stack(z, spatial('z')))
        final.append(math.stack(y, spatial('y')))

    return math.stack(final, spatial('x'))