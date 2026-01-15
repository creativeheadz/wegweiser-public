# Filepath: app/utilities/sys_url_obfuscation.py
# app/utilities/sys_url_obfuscation.py

import hashlib
import base64
from functools import wraps
from flask import abort, current_app, request, redirect
import hmac
import time
from typing import Dict, Optional
from urllib.parse import urlparse, urljoin

class URLObfuscator:
    def __init__(self, secret_key: str):
        self.secret_key = secret_key
        self._route_map: Dict[str, str] = {}
        self._reverse_map: Dict[str, str] = {}

    def generate_path(self, original_path: str) -> str:
        """Generate an obfuscated path based on the original path."""
        # Parse the URL and get just the path
        parsed = urlparse(original_path)
        path = parsed.path
        
        # Remove any existing timestamp from the path
        path = path.split(':')[0]
        
        timestamp = str(int(time.time()))
        message = f"{path}:{timestamp}".encode()
        
        # Create an HMAC of the path with timestamp
        h = hmac.new(self.secret_key.encode(), message, hashlib.sha256)
        # Create a URL-safe base64 hash
        hashed = base64.urlsafe_b64encode(h.digest()).decode('utf-8').rstrip('=')
        
        # Take first 12 characters for brevity
        short_hash = hashed[:12]
        
        # Store mapping with timestamp
        self._route_map[short_hash] = f"{path}:{timestamp}"
        self._reverse_map[path] = short_hash
        
        return short_hash

    def get_original_path(self, obfuscated_path: str) -> Optional[str]:
        """Retrieve the original path from an obfuscated path."""
        stored_path = self._route_map.get(obfuscated_path)
        if not stored_path:
            return None

        # Split path and timestamp
        try:
            path, timestamp = stored_path.rsplit(':', 1)
            timestamp = int(timestamp)
            if time.time() - timestamp > 3600:  # 1 hour expiration
                self.clear_expired_routes()
                return None
            return path
        except (ValueError, IndexError):
            return None

    def clear_expired_routes(self, max_age: int = 3600):
        """Clear routes older than max_age seconds."""
        current_time = int(time.time())
        expired = []
        
        for obfuscated, stored_path in self._route_map.items():
            try:
                path, timestamp = stored_path.rsplit(':', 1)
                timestamp = int(timestamp)
                if current_time - timestamp > max_age:
                    expired.append(obfuscated)
                    if path in self._reverse_map:
                        del self._reverse_map[path]
            except (ValueError, IndexError):
                expired.append(obfuscated)
                
        for path in expired:
            if path in self._route_map:
                del self._route_map[path]

def obfuscate_route(f):
    """Decorator to ensure routes are accessed via their obfuscated paths"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not request.path.startswith('/x/'):
            # Only redirect if this is a protected path
            if any(request.path.startswith(prefix) for prefix in ['/dashboard', '/devices', '/groups', '/organisations']):
                obfuscated = current_app.url_obfuscator.generate_path(request.path)
                return redirect(f'/x/{obfuscated}')
        return f(*args, **kwargs)
    return decorated_function