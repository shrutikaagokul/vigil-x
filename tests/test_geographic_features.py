"""Tests for geographic features (haversine, travel speed)."""
import pytest
import math
import pandas as pd
import numpy as np
from geo.haversine import haversine_distance, required_travel_speed


def test_haversine_known_distance():
    """NYC to LA should be ~2,451 miles."""
    dist = haversine_distance(40.7128, -74.0060, 34.0522, -118.2437)
    assert 2400 < dist < 2500


def test_haversine_same_point():
    """Same point → 0 distance."""
    dist = haversine_distance(33.75, -84.39, 33.75, -84.39)
    assert dist == pytest.approx(0.0, abs=0.01)


def test_haversine_null():
    """None coordinates → None."""
    assert haversine_distance(None, -84.39, 33.75, -84.39) is None
    assert haversine_distance(33.75, None, 33.75, -84.39) is None
    assert haversine_distance(float('nan'), -84.39, 33.75, -84.39) is None


def test_haversine_invalid_coords():
    """Out-of-range coordinates → None."""
    assert haversine_distance(91, -84.39, 33.75, -84.39) is None
    assert haversine_distance(33.75, -181, 33.75, -84.39) is None


def test_haversine_vectorized():
    """Vectorized version should return Series."""
    lats1 = pd.Series([33.75, 40.71])
    lons1 = pd.Series([-84.39, -74.00])
    lats2 = pd.Series([33.76, 34.05])
    lons2 = pd.Series([-84.38, -118.24])
    result = haversine_distance(lats1, lons1, lats2, lons2)
    assert isinstance(result, pd.Series)
    assert len(result) == 2
    assert result.iloc[0] < 5  # nearby points
    assert result.iloc[1] > 2000  # NYC to LA


def test_travel_speed_normal():
    """100 miles in 2 hours = 50 mph."""
    assert required_travel_speed(100, 2) == pytest.approx(50.0)


def test_travel_speed_zero_time():
    """Zero time → None (not infinite)."""
    assert required_travel_speed(100, 0) is None


def test_travel_speed_negative_time():
    """Negative time → None."""
    assert required_travel_speed(100, -1) is None


def test_travel_speed_null():
    """None inputs → None."""
    assert required_travel_speed(None, 1) is None
    assert required_travel_speed(100, None) is None


def test_travel_speed_vectorized():
    """Vectorized travel speed."""
    dist = pd.Series([100, 200, 50])
    time = pd.Series([2, 0, -1])
    result = required_travel_speed(dist, time)
    assert result.iloc[0] == pytest.approx(50.0)
    assert pd.isna(result.iloc[1])  # zero time
    assert pd.isna(result.iloc[2])  # negative time
