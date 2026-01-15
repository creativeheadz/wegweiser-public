# Filepath: app/utilities/ui_time_converter.py
from datetime import datetime

def unix_to_utc(timestamp):
    """
    Convert a Unix timestamp to a UTC datetime string.

    :param timestamp: Unix timestamp (int or float)
    :return: UTC datetime string in the format 'YYYY-MM-DD HH:MM:SS'
    """
    utc_time = datetime.utcfromtimestamp(timestamp)
    return utc_time.strftime('%Y-%m-%d %H:%M:%S')

# Example usage:
# timestamp = 1696340443
# print(unix_to_utc(timestamp))  # Output: '2024-10-03 14:07:23'
