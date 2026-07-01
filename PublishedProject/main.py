# simulation modules
# 38.8481, -120.5720
from stormscapes import stepSmoke, initializeSmoke
from kessler import initializeWeather, climateStep, evalqvs, reshape
from czml_creation import recieve_particles, save_file

from phi.flow import * 
from phi import *
import matplotlib.pyplot as plt
from phi.geom import *
from fire_interpolation import *
from backend import *
import json
import os
import datetime

roots = ["electra", "fairview", "kelly", "oak", "summitfire"]
current_root = "mosquito"
root = f"./images/{current_root}"
camera_name = None
camera_pos = None
rotation = None
zoom = None
passed = None
above = None
segmentation = None
itemx, itemy = [None, None]

discretization = (10, 10, 25)
bounds=Box(x=(0,discretization[0]), y=(0,discretization[1]), z=(0,discretization[2]))


pressure = None

rgb_clouds = [255, 255, 255, 200]
rgb_smoke = [60, 60, 60, 179]

def k(x, h):
    if h < 20:
        return x * (-0.0175*(h**2)+0.325*h+0.5)
    else: 
        return x * (0.866 * (h-20))

def generate_wind(wind0, scale, max_ele):
    wind_map = [wind0]
    for z in range(1, discretization[2]):
        real_elevation = z * 5 / (scale * 2 * discretization[2]/max_ele) / 1000
        wind_map.append(k(wind0, real_elevation))

    return math.stack(wind_map, spatial('z'))


def generate_wind_save(wind0, scale, max_ele):
    wind_map = [wind0]
    for z in range(1, discretization[2]):
        real_elevation = z * 5 / (scale * discretization[2]/max_ele) / 1000
        wind_map.append(k(wind0, real_elevation))

    return wind_map

def iterate(iterations, opt_inputs, kessler_parameters, wind_profile, fuel, cams, show=False, lm_i=False, count_above=False):

    v = kessler_parameters + fuel

    czml_smoke = [
        {
            "id": "document",
            "name": "Smoke Simulation",
            "version": "1.0"
        }
    ]

    camera_name, camera_pos, rotation, zoom, passed, above, segmentation, itemx, itemy = cams

    czml_clouds = [
        {
            "id": "document",
            "name": "Cloud Simulation",
            "version": "1.0"
        }
    ]

    sur_to_density, density, load = fuel

    shape = (discretization[0], discretization[1])
    sur_to_density = np.full(shape, sur_to_density)
    density = np.full(shape, density)
    load = np.full(shape, load)
    Mx = np.full(shape, 0.3)

    random.seed(10)
    scale = 0.1

    rain, vapor, condensation, zeroes, velocity, temperature, qvs, qr = initializeWeather(discretization, bounds)
    world_scale, world_offset, fire_pixels, smoke_particles, grid, dim, ele_map = initializeSmoke(discretization, bounds, scale, load, current_root)

    w_i = 0

    min_ele = min([i for j in ele_map for i in j])
    max_ele = max([i - min_ele for j in ele_map for i in j])
    bounds_l = 0
    [factor] = opt_inputs
    time = 0
    DT = 1.5
    G = 2
    NU = 0.02
    aspect = 1920/1080

    
    for y in range(len(ele_map)):
        for x in range(len(ele_map[y])):
            ele_map[y][x] = (ele_map[y][x] - min_ele + 2) * (scale * discretization[2]/max_ele)

    f_ext = reshape(generate_wind(wind_profile, scale, max_ele))
    f_np = f_ext.values.numpy("x,y,z,vector")

    now = datetime.datetime.now()

    for i in range(iterations):

        # print(f"Step {i}")
        # updating smoke

        fuel = [sur_to_density, density, load, qr, Mx]

        smoke_particles, grid, temp_grid = stepSmoke(velocity, smoke_particles, time, discretization, bounds, fire_pixels, dim, DT, ele_map, factor, scale, fuel)
        smoke_points = [[(j/discretization[i] * world_scale[i]) + world_offset[i] for j in list(smoke_particles.points.unstack('vector')[i])] for i in range(3)]
        smoke_points[2] = [((i - world_offset[2]) * (discretization[2]/world_scale[2])) - 2 for i in smoke_points[2]]
        smoke_points[2] = [(i * 5 / (scale * discretization[2]/max_ele)) + min_ele for i in smoke_points[2]]

        qvs = evalqvs(discretization, bounds, temperature + temp_grid * 100)
        rain, vapor, condensation, b, qc_lla, qv, qr = climateStep(rain, vapor, condensation, velocity, DT, G, zeroes, qvs, bounds, discretization, ele_map, [world_scale, world_offset, scale, min_ele, max_ele], kessler_parameters)

        velocity = advect.semi_lagrangian(velocity, velocity, DT) + DT * (b+f_ext.at(velocity))
        velocity = diffuse.explicit(velocity, NU, DT)
        velocity, pressure = fluid.make_incompressible(velocity)

        if show:
            czml_smoke = recieve_particles(smoke_points, czml_smoke, time*factor, rgb_smoke)
            czml_clouds = recieve_particles(qc_lla, czml_clouds, time*factor, rgb_clouds)

        time += DT

    print(f"Completed iteration {lm_i} in", datetime.datetime.now() - now)

    if show:
        save_file(czml_smoke, f"{current_root}/{camera_name[:-4]}/{lm_i}/smoke.czml")
        save_file(czml_clouds, f"{current_root}/{camera_name[:-4]}/{lm_i}/clouds.czml")

    final_points = smoke_points + qc_lla
    # b_p = 0
    # pt = [0,0]
    # for pa in range(-50, 50, 10):
    #     for ti in range(-50, 50, 10): 
    #         cam_points = projectPoints(camera_pos, [[final_points[0][i], final_points[1][i], final_points[2][i]] for i in range(len(final_points[0]))], [rotation[0] + pa, rotation[1] + ti] + [0], 62.5/zoom, aspect)
    #         within, percent, distance = points_in_polygon(cam_points, segmentation)
    #         print(percent)
    #         if percent > b_p:
    #             b_p = percent
    #             pt = [pa, ti]

    # for camera in list(camera_data.keys()):
    cam_points = projectPoints(camera_pos, [[final_points[0][i], final_points[1][i], final_points[2][i]] for i in range(len(final_points[0]))], [rotation[0], rotation[1], 0], 62.5/zoom, aspect)
    percent, distance = points_in_polygon(cam_points, segmentation, 0.01)
    #     print(percent, sum(distance))
    #     segmentation = [[(i[0]/1920 - 0.5) * 2, (i[1]/1080 - 0.5) * -2] for i in camera_data[camera][4]]
    #     itemx, itemy = zip(*(segmentation + [segmentation[0]]))

    #     plt.figure()
    #     plt.title(camera)
    #     plt.scatter([i[0] for i in cam_points], [i[1] for i in cam_points])
    #     plt.xlim(-1, 1)
    #     plt.ylim(-1, 1)
    #     plt.plot(itemx, itemy)

    # plot(smoke_particles, velocity)
    # plot(rain, vapor, condensation)
    # plt.show()

    return percent, [i for i in distance if i is not None], f_np, v

n_components = 2
step = 2
components = int(discretization[0]/step)

def recon(c_component):
    recon_lst = []

    x_i = 0
    n = []
    component = []
    while x_i < len(c_component):

        n.append(c_component[x_i])

        if x_i % n_components != 0:
            component.append(np.array(n))
            n = []
        if x_i % (n_components * step) == 0 and x_i != 0:
            recon_lst.append(np.array(component))
            component = []
        x_i += 1
    recon_lst.append(np.array(component))

    return np.array(recon_lst)

def LMWrapper(i, variables, constants, cams, show=False, lm_i=None):
    
    z0, dTemp, sur_to_vol, density, load = variables[:5]
    x_components = variables[5:n_components*step *components + 5]
    y_components = variables[n_components*step*components + 5:]

    #[x,y]
    x_components = [recon(x_components)[i] @ constants[0][i] for i in range(components)]
    x_components = np.concatenate(x_components)

    y_components = [recon(y_components)[i] @ constants[1][i] for i in range(components)]
    y_components = np.concatenate(y_components)

    y_lst = []
    for x in range(len(x_components)):
        x_lst = []
        for y in range(len(x_components[x])):
            x_lst.append(math.stack([x_components[x][y], y_components[x][y], 0], dim=channel(vector="x,y,z")))
        y_lst.append(math.stack(x_lst, dim=spatial("x")))
    
    wind_profile = math.stack(y_lst, dim=spatial("y"))

    iterations = 8
    percent, distance, wind, v = iterate(iterations, [125160/iterations], kessler_parameters=[z0, dTemp], wind_profile=wind_profile, fuel=[sur_to_vol, density, load], show=show, lm_i=lm_i, count_above=above, cams=cams)
    return i, distance, wind, v


if __name__ == "__main__":
    for r in roots:
        current_root = r
        root = f"./images/{current_root}"

        with open(root + "./segmentations.json", 'r') as file:
            camera_data = json.load(file)
        for name in list(camera_data.keys()):
            try:
                camera_name = name
                print(camera_data[camera_name])
                camera_pos = camera_data[camera_name][0]
                rotation = camera_data[camera_name][1]
                zoom = camera_data[camera_name][2]
                passed = camera_data[camera_name][3]
                segmentation = [[(i[0]/1920 - 0.5) * 2, (i[1]/1080 - 0.5) * -2] for i in camera_data[camera_name][4]]
                itemx, itemy = zip(*(segmentation + [segmentation[0]]))
                print(f"Optimizing camera {camera_name}")

                cams = [camera_name, camera_pos, rotation, zoom, passed, above, segmentation, itemx, itemy]

                # initialize wind parameters
                direction, magnitude = [-22.5, 0.01]
                x_wind = magnitude*pymath.cos(pymath.radians(direction))
                y_wind = magnitude*pymath.cos(pymath.radians(direction))

                wind_profile = math.stack([math.stack([x_wind,y_wind,0], dim=channel(vector="x,y,z"))] * discretization[0], spatial("x"))
                wind_profile = math.stack([wind_profile] * discretization[1], spatial("y"))
                matrix1, matrix2 = indexMatrices(wind_profile, step)

                variables, errors = LM(LMWrapper, variables=[4.0, -39, 12240.0, 420.0, 0.313], variables_l=matrix1[0] + matrix1[1], l=1000, step=10, v=2, threads=15, delta=[-0.3, 10, 5, 0.05, 1000.0, 20.0, 0.5], delta_l=[0.05]*int(n_components*components), constants=matrix2, cams=cams, root=current_root)
                with open(f'{current_root}/{camera_name[:-4]}/errors.txt', "w") as f:
                    json.dump(errors, f)
            except:
                print(name, r)

    # camera_name = "saddletimber.jpg"
    # camera_pos = camera_data[camera_name][0]
    # rotation = camera_data[camera_name][1]
    # rotation[1] += 5
    # zoom = camera_data[camera_name][2]
    # passed = camera_data[camera_name][3]
    # above = camera_data[camera_name][4]
    # segmentation = [[(i[0]/1920 - 0.5) * 2, (i[1]/1080 - 0.5) * -2] for i in camera_data[camera_name][5]]
    # itemx, itemy = zip(*(segmentation + [segmentation[0]]))
    # print(f"Optimizing camera {camera_name}")

    # iterations = 5

    # cams = [camera_name, camera_pos, rotation, zoom, passed, above, segmentation, itemx, itemy]

    # direction, magnitude = [-22.5, 0.2]
    # x_wind = magnitude*pymath.cos(pymath.radians(direction))
    # y_wind = magnitude*pymath.cos(pymath.radians(direction))

    # wind_profile = math.stack([math.stack([x_wind,y_wind,0], dim=channel(vector="x,y,z"))] * discretization[0], spatial("x"))
    # wind_profile = math.stack([wind_profile] * discretization[1], spatial("y"))

    # iterate(iterations, [passed/iterations], kessler_parameters=[5, -39], wind_profile=wind_profile, fuel=[12240.0, 420.0, 0.313], show=True, lm_i=0, cams=cams)

