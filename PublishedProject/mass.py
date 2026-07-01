import numpy as np
import matplotlib.pyplot as plt
from scipy.ndimage import gaussian_filter

# Parameters
n = 15  # Grid size
np.random.seed(42)  # For reproducibility

# Generate random mass distribution
mass = np.random.rand(n, n)

# Emphasize some regions as "blobs" by smoothing
mass = gaussian_filter(mass, sigma=3)  # Adjust `sigma` for smoother blobs

# Normalize mass values
mass -= np.min(mass)  # Shift to 0
mass /= np.max(mass)  # Scale to [0, 1]
mass = 10

# Add additional randomness to the rest of the grid
background_noise = np.random.rand(n, n) * 0.9  # Adjust amplitude of noise
mass += background_noise

# Clip to ensure values remain in [0, 1]
mass = np.clip(mass, 0, 10)

# Plot the colormap
plt.figure(figsize=(8, 6))
plt.imshow(mass, cmap='Greens', origin='lower', vmin=0, vmax=10)
plt.colorbar(label='Mass Density (kg/m^2)')
plt.title('Mass Density Per Grid Area')
plt.xlabel('X Grid Coordinate')
plt.ylabel('Y Grid Coordinate')
plt.show()
