"""shared/utils/haversine.py"""
from math import asin, cos, radians, sin, sqrt


def haversine(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """
    Returns great-circle distance in METRES between two GPS coordinates.
    Uses the Haversine formula. Accurate to within ~0.5% for distances < 200km.
    """
    R = 6_371_000  # Earth radius in metres
    phi1, phi2 = radians(lat1), radians(lat2)
    dphi = radians(lat2 - lat1)
    dlambda = radians(lon2 - lon1)
    a = sin(dphi / 2) ** 2 + cos(phi1) * cos(phi2) * sin(dlambda / 2) ** 2
    return R * 2 * asin(sqrt(a))
