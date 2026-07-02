from dataclasses import dataclass

import numpy as np


@dataclass
class KesslerConfig:
    autoconversion_rate: float = 0.0012
    accretion_rate: float = 0.0008
    evaporation_rate: float = 0.001
    condensation_rate: float = 0.003
    rain_fall_speed: float = 0.16


def pressure_height(height_km: np.ndarray) -> np.ndarray:
    return np.power(np.maximum(0.2, 1 - 0.0065 * (height_km / 0.280)), 5.2561)


def saturation_mixing_ratio(temperature_c: np.ndarray, height_m: np.ndarray) -> np.ndarray:
    pressure = pressure_height(height_m / 1000.0) * 10000.0
    return 380.16 / pressure * np.exp((17.67 * temperature_c) / (temperature_c + 243.5))


def kessler_step(vapor, cloud, rain, temperature_c, height_m, dt, config=None):
    config = config or KesslerConfig()
    qvs = saturation_mixing_ratio(temperature_c, height_m) * 0.8

    supersaturation = np.maximum(vapor - qvs, 0.0)
    condensation = supersaturation * config.condensation_rate * dt
    vapor = vapor - condensation
    cloud = cloud + condensation

    autoconversion = np.maximum(cloud - 0.001, 0.0) * config.autoconversion_rate * dt
    accretion = cloud * rain * config.accretion_rate * dt
    rain_gain = autoconversion + accretion
    cloud = np.maximum(0.0, cloud - rain_gain)
    rain = rain + rain_gain

    evaporation = np.minimum(rain, np.maximum(qvs - vapor, 0.0) * config.evaporation_rate * dt)
    rain = rain - evaporation
    vapor = vapor + evaporation

    return vapor, cloud, rain, qvs
