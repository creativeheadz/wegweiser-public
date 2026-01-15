"""
API Client - HTTP communication with server
"""

import logging
import json
import time
import asyncio
from typing import Dict, Any, Optional
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry
import urllib3

# Disable SSL warnings for self-signed certificates in MSP environment
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

logger = logging.getLogger(__name__)


class APIClient:
    """HTTP client for server communication"""
    
    def __init__(self, server_addr: str, timeout: int = 30, max_retries: int = 3):
        """Initialize API client"""
        self.server_addr = server_addr
        self.timeout = timeout
        self.max_retries = max_retries
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create requests session with retry strategy"""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=self.max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "OPTIONS", "POST"]
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def _build_url(self, endpoint: str) -> str:
        """Build full URL from endpoint"""
        if not endpoint.startswith('/'):
            endpoint = '/' + endpoint
        return f"https://{self.server_addr}{endpoint}"
    
    def get(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """GET request"""
        try:
            url = self._build_url(endpoint)
            logger.debug(f"GET {url}")
            logger.debug(f"Timeout: {self.timeout}s, Max retries: {self.max_retries}")

            response = self.session.get(
                url,
                params=params,
                timeout=self.timeout,
                verify=False  # Disable SSL verification for self-signed certs
            )
            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()

            return response.json()

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Server may be unreachable or not responding")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Server took too long to respond (timeout: {self.timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"GET request failed: {e}")
            logger.error(f"URL: {url}")
            if 'response' in locals():
                logger.error(f"Status code: {response.status_code}")
                logger.error(f"Response: {response.text}")
            raise
    
    def post(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """POST request"""
        try:
            url = self._build_url(endpoint)
            logger.debug(f"POST {url}")
            logger.debug(f"Timeout: {self.timeout}s, Max retries: {self.max_retries}")
            logger.debug(f"Payload keys: {list(data.keys())}")

            response = self.session.post(
                url,
                json=data,
                timeout=self.timeout,
                verify=False,  # Disable SSL verification for self-signed certs
                headers={'Content-Type': 'application/json'}
            )
            logger.debug(f"Response status: {response.status_code}")
            response.raise_for_status()

            return response.json()

        except requests.exceptions.ConnectionError as e:
            logger.error(f"Connection error: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Server may be unreachable or not responding")
            raise
        except requests.exceptions.Timeout as e:
            logger.error(f"Request timeout: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Server took too long to respond (timeout: {self.timeout}s)")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"POST request failed: {e}")
            logger.error(f"URL: {url}")
            logger.error(f"Status Code: {response.status_code if 'response' in locals() else 'N/A'}")
            logger.error(f"Response: {response.text if 'response' in locals() else 'N/A'}")
            raise
    
    def register_device(
        self,
        group_uuid: str,
        device_name: str,
        hardware_info: str,
        agent_pub_pem: str
    ) -> str:
        """Register device with server"""
        logger.info(f"Registering device: {device_name}")
        
        payload = {
            'groupuuid': group_uuid,
            'devicename': device_name,
            'hardwareinfo': hardware_info,
            'agentpubpem': agent_pub_pem
        }
        
        response = self.post('/devices/register', payload)
        device_uuid = response.get('deviceuuid')
        
        if device_uuid:
            logger.info(f"Device registered successfully: {device_uuid}")
            return device_uuid
        
        raise Exception("No device UUID in registration response")
    
    def get_server_public_key(self) -> str:
        """Get server's public key"""
        logger.info("Fetching server public key...")
        
        response = self.get('/diags/getserverpublickey')
        server_pub_pem_b64 = response.get('serverpublickey')
        
        if not server_pub_pem_b64:
            raise Exception("No server public key in response")
        
        import base64
        server_pub_pem = base64.b64decode(server_pub_pem_b64).decode('utf-8')
        logger.info("Server public key fetched successfully")
        
        return server_pub_pem
    
    def get_pending_snippets(self, device_uuid: str) -> list:
        """Get pending snippets for device"""
        logger.info(f"Fetching pending snippets for {device_uuid}")
        
        endpoint = f'/snippets/pendingsnippets/{device_uuid}'
        response = self.get(endpoint)
        
        schedule_list = response.get('data', {}).get('scheduleList', [])
        logger.info(f"Found {len(schedule_list)} pending snippets")
        
        return schedule_list
    
    def get_snippet(self, schedule_uuid: str) -> Dict[str, Any]:
        """Download snippet by schedule UUID"""
        logger.info(f"Downloading snippet: {schedule_uuid}")
        
        endpoint = f'/snippets/getsnippetfromscheduleuuid/{schedule_uuid}'
        response = self.get(endpoint)
        
        return response
    
    def report_snippet_execution(
        self,
        schedule_uuid: str,
        status: str,
        duration_ms: int = 0,
        exit_code: int = 0
    ) -> bool:
        """Report snippet execution result"""
        logger.info(f"Reporting snippet execution: {schedule_uuid} - {status}")

        payload = {
            'scheduleuuid': schedule_uuid,
            'execstatus': status,
            'duration_ms': duration_ms,
            'exit_code': exit_code
        }

        try:
            endpoint = f'/snippets/sendscheduleresult/{schedule_uuid}'
            self.post(endpoint, payload)
            return True

        except Exception as e:
            logger.error(f"Failed to report execution: {e}")
            return False

    # Async methods for NATS integration
    async def get_async(self, endpoint: str, params: Optional[Dict] = None) -> Dict[str, Any]:
        """Async GET request - runs sync request in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.get, endpoint, params)

    async def post_async(self, endpoint: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Async POST request - runs sync request in thread pool"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self.post, endpoint, data)

