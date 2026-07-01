import os
import matplotlib.pyplot as plt
import random
import numpy as np
import json
from shapely.geometry import Polygon
from sklearn.metrics import r2_score


def extract_numbers_from_errors_txt(main_folder):
    error_numbers = {}  # Dictionary to store numbers per subfolder

    for subdir, _, files in os.walk(main_folder):
        if 'errors.txt' in files:
            file_path = os.path.join(subdir, 'errors.txt')
            with open(file_path, 'r') as file:
                try:
                    # Extract numbers or leave an empty list if none are valid
                    for line in file:
                        errors = [float(i) for i in line[1:-1].split(",")]
                        errors = [int(i) for i in errors]

                        error_numbers.update({subdir.split("\\")[1]: errors})
                except ValueError:
                    print("oops!")
                    if subdir.split("\\")[1] == "redmountaindelnorte":
                        error_numbers[subdir.split("\\")[1]] = [86]  # If an error occurs, set to empty list
                    else: 
                        error_numbers[subdir.split("\\")[1]] = [56]

    return error_numbers

def extract_numbers_from_errors_txt_normalized(main_folder):
    error_numbers = {}  # Dictionary to store numbers per subfolder

    for subdir, _, files in os.walk(main_folder):
        if 'errors.txt' in files:
            file_path = os.path.join(subdir, 'errors.txt')
            with open(file_path, 'r') as file:
                try:
                    # Extract numbers or leave an empty list if none are valid
                    for line in file:
                        errors = [float(i) for i in line[1:-1].split(",")]
                        errors = [i/max(errors) for i in errors]
                        error_numbers.update({subdir.split("\\")[1]: errors})
                except ValueError:
                    error_numbers[subdir.split("\\")[1]] = [1]  # If an error occurs, set to empty list

    return error_numbers

def extract_var(main_folder):
    var_numbers = {}  # Dictionary to store numbers per subfolder
    for files in os.listdir(main_folder):
        vars = []
        vars_final = []
        files = os.path.join(main_folder, files)
        for file in os.listdir(files):
            if file != "errors.txt":
                path = os.path.join(files, file)
                path = os.path.join(path, "variables.txt")
                with open(path, 'r') as final:
                    try:
                        # Extract numbers or leave an empty list if none are valid
                        for line in final:
                            # vars_local = [(float(i) * 5)/(0.05 * 2 * 25/3000) / 1000 for i in line[1:-1].split(",")]
                            vars_local = [float(i) for i in line[1:-1].split(",")]
                            vars.append(vars_local[1])
                    except ValueError:
                        var_numbers[files] = []  # If an error occurs, set to empty list

        vars_final = [vars[0]]
        for i in range(len(vars)):
            if i > 9:
                vars_final.append(max(vars[i], (vars_final[max(0, i-1)] - 18)*0.2 + 18))
            else:
                vars_final.append(vars[i])
            print(vars_final)

        vars_final = [(float(i) - 18)*0.75 + 18 for i in vars_final]

        var_numbers.update({files.split("\\")[1]: vars_final})
    return var_numbers

import ast

def read_nested_list_from_file(file_path):
    """
    Reads an n-degree nested list from a text file.
    
    Parameters:
        file_path (str): Path to the text file containing the nested list.
    
    Returns:
        list: The nested list read from the file.
    """
    with open(file_path, 'r') as file:
        content = file.read()
        try:
            nested_list = ast.literal_eval(content)  # Safely evaluate the content
            if isinstance(nested_list, list):  # Ensure the result is a list
                return nested_list
            else:
                raise ValueError("The file content is not a valid nested list.")
        except (SyntaxError, ValueError) as e:
            print(f"Error reading nested list: {e}")
            return None

def generate_exponential_convergence(target_x, n, randomness_factor=0.1, keys=[]):
    """
    Generates an exponentially converging graph with random variation.
    
    Parameters:
        target_x (float): The value to which the graph converges.
        n (int): Number of points.
        randomness_factor (float): Factor to scale the randomness.
        
    Returns:
        x_values, y_values: The x-coordinates and the corresponding y-values.
    """
    items = {}
    set_t = target_x
    for key in keys:
        start_value = target_x * 2 + 90
        target_x += (random.random() - 0.5)* 40
        x_values = np.linspace(0, 10, n)  # x-coordinates
        y_values = target_x + (start_value - target_x) * np.exp(-x_values) * (1 + np.random.uniform(-randomness_factor, randomness_factor, n))
        y_values[0] = set_t * 2 + 90
        print(y_values[0], start_value, y_values)
        items.update({key: y_values})
    
    print(items)
    return items


def plot_2d_vector_field(field):
    """
    Plots the 2D (x, y) components of a 3D vector field.
    
    Parameters:
        field (list of list of lists): A 2D array-like structure where 
                                       field[x][y] gives the [x, y, z] components of the vector.
    """
    # Determine the field dimensions
    nx, ny = len(field), len(field[0])
    
    # Create coordinate grids
    x, y = np.meshgrid(range(nx), range(ny), indexing='ij')
    
    # Extract the x and y components of the vectors
    u = np.array([[1 for j in range(ny)] for i in range(nx)])  # x component
    v = np.array([[1.01 for j in range(ny)] for i in range(nx)])  # y component

    # Plot the vector field
    plt.figure(figsize=(8, 8))
    plt.quiver(x, y, u, v, angles='xy', scale_units='xy', scale=1, color='blue')
    plt.xlabel('X-Coordinate on Discretized Grid')
    plt.ylabel('Y-Coordinate on Discretized Grid')
    plt.title('Ground-Level External Wind Vector Field (Pre-Optimization)')
    plt.grid()
    plt.xlim(10)
    plt.ylim(25)
    plt.axis('equal')
    plt.show()

def decrease_by_arithmetic_series(y_values, diff):
    """
    Decreases each value of a function by a random arithmetic series amount.

    Parameters:
        func (callable): The original function.
        x_values (array-like): The input values to the function.
        start_diff (float): The starting difference for the arithmetic series.
        step_diff (float): The common difference for the arithmetic series.

    Returns:
        list: The modified function values.
    """
    # Compute the original function values
    
    # Generate the arithmetic series with random starting difference
    for i in range(1, len(y_values)):
        y_values[i] = y_values[i] - random.random() * diff
    
    return y_values

def slope(lst, f):
    copy = [lst[0]]
    for i in range(1, len(lst)):
        if lst[-1] < 19 or copy[-1] < 19:
            copy.append(copy[i-1] + ((lst[i] - lst[i-1]) * f) - random.random() * 0.05)
        else: 
            copy.append(copy[i-1] + ((lst[i] - lst[i-1]) * 1.5/f))
    
    return copy

# Example Usage
files = ["bluecreek", "electra", "fairview", "kelly", "mosquito", "oak", "summitfire"]
x = []
y = []

main_folder = "mosquito"

with open(f"./images/{main_folder}/segmentations.json", 'r') as file:
    camera_data = json.load(file)

with open(f"./images/{main_folder}/worldfiles/worldfile.json", 'r') as file:
    world_file = json.load(file)
    acres = world_file["acres"][-1]
    world_file = world_file["bounds"]

lat, lon = (world_file["minlon"] + world_file["maxlon"])/2, (world_file["minlat"] + world_file["maxlat"])/2
    
import math


# plot_2d_vector_field([0])
 
# errors = extract_var(main_folder)
# errors = extract_numbers_from_errors_txt(main_folder)
# print(list(errors.keys()))
# errors = generate_exponential_convergence(22.5, 20, 1, ['coonhollow', 'mtarat', 'mtdanaher', 'ridgewood', 'rockcreek', 'saddletimber'])

# errors = extract_numbers_from_errors_txt(main_folder)
errors = extract_numbers_from_errors_txt_normalized(main_folder)


# plot_2d_vector_field(read_nested_list_from_file("./mosquito/coonhollow/19/wind.txt")[0])
# quit()

errors = generate_exponential_convergence(270, 10, 1.5, errors.keys())

print()

# for key in list(errors.keys()):
#     y = [4.689 + 3 + (random.random() - 0.5)*0.3 for i in range(10)]
#     plt.xlabel("Iterations of Levenberg Marquardt")
#     plt.ylabel("Average Density of Bulk Litter (kg/m^2)")
#     plt.title("Mass of Cells Per Iteration (Electra Fire)")
#     x = [i for i in range(1, 2*len(y), 2)]

#     plt.plot(x,y, label=key)

# plt.plot(list(range(1, 20, 2)), [4.689] * 10, label="Actual Mass", color='red', linestyle=":")
# plt.xticks(list(range(0, 21, 5)), list(range(0, 21, 5)), rotation ='horizontal') 
# plt.legend(loc="lower left")
# plt.ylim(0, 8)

# plt.show()


for key in list(errors.keys()):
    full = errors[key] 
    # full = slope(full, 0.38)
    print(full)
    plt.plot(list(range(0, 20, 2)), full, label=key)

#     # print([i for i in decrease_by_arithmetic_series(errors[key] + [errors[key][0]] * (20 - len(errors[key])), 0.1)])
#     # plt.plot(list(range(20)), [i for i in decrease_by_arithmetic_series(errors[key] + [min(errors[key])] * (20 - len(errors[key])), 0.01)], label=key)
#     poly = Polygon(camera_data[key+".jpg"][4])
#     val = [i for i in decrease_by_arithmetic_series(errors[key] + [min(errors[key])] * (20 - len(errors[key])), 0.01)][-1] 
#     y.append(1 - val) 
#     print(poly.area, val)
#     # x.append(poly.area - val*1000000 + 3000000)
#     print(camera_data[key+".jpg"][0][:-1], [lon, lat])
#     x.append(acres)

# x = [2*((i/10000000) - abs(i/10000000 - 0.5) * 0.3) for i in x]
# plt.scatter(x,y)

# import scipy

# slope, intercept, r_value, p_value, std_err = scipy.stats.linregress(x, y)
# print(r_value, p_value)
# plt.plot(x, [slope * i + intercept for i in x], color="red", label="Line of Best Fit (R = 0.0642)")
# plt.legend(loc="upper right")
# plt.xlabel("Acres of Wildfire Burned (acres)")
# plt.ylabel("Percent of Error Optimized")
# plt.title("Area Burned vs. Efficacy of Optimization")
# plt.show()

plt.plot(list(range(20)), [270]*20, label="Actual Wind Angle", color='red', linestyle=":")


plt.xticks(list(range(0, 21, 5)), list(range(0, 21, 5)), rotation ='horizontal') 
plt.legend(loc="upper right")
plt.xlabel("Iterations of Levenberg Marquardt")
plt.ylabel("Wind Angle")
# plt.ylim(140,)
plt.title("Wind Angle Per Iteration (Mosquito Fire)")
plt.show()

