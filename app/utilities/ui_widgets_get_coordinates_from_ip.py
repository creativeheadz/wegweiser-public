# Filepath: app/utilities/ui_widgets_get_coordinates_from_ip.py
import geoip2.database
from flask import current_app
from app.utilities.app_logging_helper import log_with_route
import logging

def get_coordinates_from_ip(ip):
    try:
        with geoip2.database.Reader('/opt/wegweiser/GeoLite2-City.mmdb') as reader:
            response = reader.city(ip)
            latitude, longitude = response.location.latitude, response.location.longitude
            log_with_route(logging.INFO, f"Successfully retrieved coordinates for IP {ip}: (Latitude: {latitude}, Longitude: {longitude})")
            return latitude, longitude
    except Exception as e:
        log_with_route(logging.ERROR, f"Error getting coordinates for IP {ip}: {e}")
        return None, None
