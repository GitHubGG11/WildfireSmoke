import cv2
import numpy as np
import matplotlib.pyplot as plt
import os
import json

# Load the image
image_path = './images/kelly/wildfrontier.jpg'  # Replace with your image file path
image_name = os.path.basename(image_path)  # Get the image name
image = cv2.imread(image_path)
image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)

# Resize image for display if it's too large
scale_percent = 50  # Adjust scale percent to control the size of the display window
width = int(image.shape[1] * scale_percent / 100)
height = int(image.shape[0] * scale_percent / 100)
dim = (width, height)
resized_image = cv2.resize(image_rgb, dim, interpolation=cv2.INTER_AREA)

# Initialize list to store scaled points
scaled_points = []

# Mouse callback function to capture points
def select_point(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:  # Left mouse button click
        # Scale the coordinates back to the original size
        orig_x = int(x / (scale_percent / 100))
        orig_y = int(y / (scale_percent / 100))
        scaled_points.append((orig_x, orig_y))
        # Display the point on the resized image
        cv2.circle(resized_image, (x, y), 5, (255, 0, 0), -1)
        cv2.imshow("Select Points", resized_image)

# Display the resized image and set the callback function
cv2.imshow("Select Points", resized_image)
cv2.setMouseCallback("Select Points", select_point)
cv2.waitKey(0)
cv2.destroyAllWindows()

# Check if enough points were selected
if len(scaled_points) < 3:
    print("Please select at least 3 points to form a polygon.")
else:
    # JSON file path
    json_file_path = './images/kelly/segmentations.json'

    # Load existing JSON data if the file exists, otherwise create an empty dictionary
    if os.path.exists(json_file_path):
        with open(json_file_path, 'r') as f:
            data = json.load(f)
    else:
        data = {}

    # Save points in the format: <image name>: <list of points in order>
    data[image_name] = [[41.8297, -123.8804, 3711], [101.29, -0.6], 12.7, 1802415, scaled_points]

    # Write the updated data back to the JSON file
    with open(json_file_path, 'w') as f:
        json.dump(data, f, indent=4)

    print(f"Segmentation points saved to {json_file_path}", scaled_points)

    # Create a mask with the same dimensions as the original image
    mask = np.zeros(image.shape[:2], dtype=np.uint8)

    # Convert scaled points to a numpy array
    points_array = np.array(scaled_points, dtype=np.int32)

    # Fill the polygon on the mask
    cv2.fillPoly(mask, [points_array], 255)

    # Apply the mask to the original image
    segmented_image = cv2.bitwise_and(image, image, mask=mask)

    # Display the segmented region
    plt.figure(figsize=(10, 10))
    plt.subplot(1, 2, 1)
    plt.imshow(image_rgb)
    plt.title("Original Image")
    plt.subplot(1, 2, 2)
    plt.imshow(cv2.cvtColor(segmented_image, cv2.COLOR_BGR2RGB))
    plt.title("Segmented Region")
    plt.show()
