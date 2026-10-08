"""
Haversine distance and travel speed calculations for Vigil-X.

All functions handle missing/invalid coordinates safely.
"""
from __future__ import annotations

import math
from typing import Optional, Union

import numpy as np
import pandas as pd

# Earth radius in miles
_EARTH_RADIUS_MI = 3958.8


def haversine_distance(
    lat1: Union[float, np.ndarray, pd.Series],
    lon1: Union[float, np.ndarray, pd.Series],
    lat2: Union[float, np.ndarray, pd.Series],
    lon2: Union[float, np.ndarray, pd.Series],
) -> Union[Optional[float], pd.Series]:
    """
    Calculate haversine distance in miles between two points.

    Handles scalar and vectorized (pandas/numpy) inputs.
    Returns None/NaN for invalid or missing coordinates.
    """
    # --- Check if inputs are vector-like ---
    is_vector = any(isinstance(v, (pd.Series, np.ndarray, list)) for v in [lat1, lon1, lat2, lon2])
    if not is_vector:
        if any(v is None for v in [lat1, lon1, lat2, lon2]):
            return None
        try:
            f_lat1, f_lon1 = float(lat1), float(lon1)
            f_lat2, f_lon2 = float(lat2), float(lon2)
        except (TypeError, ValueError):
            return None
        if any(math.isnan(v) for v in [f_lat1, f_lon1, f_lat2, f_lon2]):
            return None
        if not (-90 <= f_lat1 <= 90 and -90 <= f_lat2 <= 90
                and -180 <= f_lon1 <= 180 and -180 <= f_lon2 <= 180):
            return None
        rlat1, rlat2 = math.radians(f_lat1), math.radians(f_lat2)
        dlat = math.radians(f_lat2 - f_lat1)
        dlon = math.radians(f_lon2 - f_lon1)
        a = (math.sin(dlat / 2) ** 2
             + math.cos(rlat1) * math.cos(rlat2) * math.sin(dlon / 2) ** 2)
        c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
        return _EARTH_RADIUS_MI * c

    # --- Vectorized path (pandas Series / numpy array) ---
    lat1 = pd.Series(lat1, dtype=float)
    lon1 = pd.Series(lon1, dtype=float)
    lat2 = pd.Series(lat2, dtype=float)
    lon2 = pd.Series(lon2, dtype=float)

    # Validate ranges — set invalid coords to NaN
    valid = (
        lat1.between(-90, 90) & lat2.between(-90, 90)
        & lon1.between(-180, 180) & lon2.between(-180, 180)
    )

    rlat1 = np.radians(lat1)
    rlat2 = np.radians(lat2)
    dlat = np.radians(lat2 - lat1)
    dlon = np.radians(lon2 - lon1)
    a = (np.sin(dlat / 2) ** 2
         + np.cos(rlat1) * np.cos(rlat2) * np.sin(dlon / 2) ** 2)
    c = 2 * np.arctan2(np.sqrt(a), np.sqrt(1 - a))
    dist = _EARTH_RADIUS_MI * c
    dist[~valid] = np.nan
    return dist


def required_travel_speed(
    distance_miles: Union[float, pd.Series],
    time_delta_hours: Union[float, pd.Series],
) -> Union[Optional[float], pd.Series]:
    """
    Calculate required travel speed in mph.

    Returns None/NaN for zero or negative time gaps, or missing distance.
    Never produces infinite values — returns NaN instead.
    """
    is_vector = any(isinstance(v, (pd.Series, np.ndarray, list)) for v in [distance_miles, time_delta_hours])
    if not is_vector:
        if distance_miles is None or time_delta_hours is None:
            return None
        try:
            d = float(distance_miles)
            t = float(time_delta_hours)
        except (TypeError, ValueError):
            return None
        if math.isnan(d) or math.isnan(t) or t <= 0:
            return None
        return d / t

    # --- Vectorized ---
    dist = pd.Series(distance_miles, dtype=float)
    time = pd.Series(time_delta_hours, dtype=float)
    speed = pd.Series(np.nan, index=dist.index)
    valid = (time > 0) & dist.notna() & time.notna()
    speed[valid] = dist[valid] / time[valid]
    return speed
