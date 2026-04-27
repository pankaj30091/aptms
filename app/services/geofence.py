import math
from flask import current_app


def haversine_distance(lat1, lon1, lat2, lon2):
    """Return distance in metres between two GPS coordinates."""
    R = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2
    return R * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def is_within_geofence(latitude, longitude):
    """
    Returns (allowed: bool, distance_m: float).
    Reads building coordinates from app config (loaded from env / BuildingConfig row).
    """
    building_lat = current_app.config["BUILDING_LATITUDE"]
    building_lon = current_app.config["BUILDING_LONGITUDE"]
    radius = current_app.config["GEOFENCE_RADIUS_M"]

    distance = haversine_distance(latitude, longitude, building_lat, building_lon)
    return distance <= radius, round(distance, 1)
