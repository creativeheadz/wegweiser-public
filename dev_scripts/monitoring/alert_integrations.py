#!/usr/bin/env python3
"""
Alert Integration Helpers for Live Monitoring Tests
Supports: NTFY, n8n, Zabbix, Tactical RMM
"""

import os
import json
import requests
import logging
from typing import Dict, List, Optional
from datetime import datetime, timezone
from enum import Enum

logger = logging.getLogger(__name__)


class AlertSeverity(Enum):
    """Alert severity levels"""
    INFO = "info"
    WARNING = "warning"
    CRITICAL = "critical"


class AlertIntegration:
    """Base alert integration class"""
    
    def send(self, title: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING):
        raise NotImplementedError


class NTFYIntegration(AlertIntegration):
    """NTFY.sh integration"""

    def __init__(self, topic_url: str, token: Optional[str] = None):
        """
        Initialize NTFY integration

        Args:
            topic_url: Full NTFY topic URL (e.g., https://ntfy.sh/wegweiser-alerts)
            token: Optional authentication token for self-hosted NTFY instances
        """
        self.topic_url = topic_url
        self.token = token

    def send(self, title: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING):
        """Send alert via NTFY"""
        try:
            priority_map = {
                AlertSeverity.INFO: 2,
                AlertSeverity.WARNING: 4,
                AlertSeverity.CRITICAL: 5,
            }

            headers = {
                "Title": title,
                "Priority": str(priority_map.get(severity, 3)),
                "Tags": f"wegweiser,{severity.value}"
            }

            # Add authorization header if token is provided
            if self.token:
                headers["Authorization"] = f"Bearer {self.token}"

            response = requests.post(
                self.topic_url,
                data=message,
                headers=headers,
                timeout=10
            )

            if response.status_code == 200:
                logger.info(f"NTFY alert sent: {title}")
                return True
            else:
                logger.error(f"NTFY alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"NTFY integration error: {str(e)}")
            return False


class N8nIntegration(AlertIntegration):
    """n8n webhook integration"""
    
    def __init__(self, webhook_url: str):
        """
        Initialize n8n integration
        
        Args:
            webhook_url: n8n webhook URL
        """
        self.webhook_url = webhook_url
    
    def send(self, title: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING):
        """Send alert via n8n webhook"""
        try:
            payload = {
                "title": title,
                "message": message,
                "severity": severity.value,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "source": "wegweiser-monitoring"
            }
            
            response = requests.post(
                self.webhook_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"n8n alert sent: {title}")
                return True
            else:
                logger.error(f"n8n alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"n8n integration error: {str(e)}")
            return False


class ZabbixIntegration(AlertIntegration):
    """Zabbix integration via API"""
    
    def __init__(self, zabbix_url: str, api_token: str, host_name: str = "Wegweiser"):
        """
        Initialize Zabbix integration
        
        Args:
            zabbix_url: Zabbix API URL (e.g., http://zabbix.local/api_jsonrpc.php)
            api_token: Zabbix API token
            host_name: Host name in Zabbix
        """
        self.zabbix_url = zabbix_url
        self.api_token = api_token
        self.host_name = host_name
    
    def send(self, title: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING):
        """Send alert via Zabbix"""
        try:
            # Zabbix severity: 0=Not classified, 1=Information, 2=Warning, 3=Average, 4=High, 5=Disaster
            severity_map = {
                AlertSeverity.INFO: 1,
                AlertSeverity.WARNING: 2,
                AlertSeverity.CRITICAL: 5,
            }
            
            payload = {
                "jsonrpc": "2.0",
                "method": "event.create",
                "params": {
                    "source": 0,  # Trigger
                    "object": 0,  # Trigger
                    "objectid": 0,
                    "clock": int(datetime.now(timezone.utc).timestamp()),
                    "value": 1,  # Problem
                    "severity": severity_map.get(severity, 2),
                    "acknowledged": 0
                },
                "auth": self.api_token,
                "id": 1
            }
            
            response = requests.post(
                self.zabbix_url,
                json=payload,
                timeout=10
            )
            
            if response.status_code == 200:
                logger.info(f"Zabbix alert sent: {title}")
                return True
            else:
                logger.error(f"Zabbix alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Zabbix integration error: {str(e)}")
            return False


class TacticalRMMIntegration(AlertIntegration):
    """Tactical RMM integration"""
    
    def __init__(self, api_url: str, api_key: str, client_id: int, site_id: int):
        """
        Initialize Tactical RMM integration
        
        Args:
            api_url: Tactical RMM API URL
            api_key: API key
            client_id: Client ID
            site_id: Site ID
        """
        self.api_url = api_url.rstrip('/')
        self.api_key = api_key
        self.client_id = client_id
        self.site_id = site_id
    
    def send(self, title: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING):
        """Send alert via Tactical RMM"""
        try:
            headers = {
                "Authorization": f"Token {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "client": self.client_id,
                "site": self.site_id,
                "alert_type": "custom",
                "severity": severity.value,
                "title": title,
                "description": message
            }
            
            response = requests.post(
                f"{self.api_url}/alerts/",
                json=payload,
                headers=headers,
                timeout=10
            )
            
            if response.status_code in [200, 201]:
                logger.info(f"Tactical RMM alert sent: {title}")
                return True
            else:
                logger.error(f"Tactical RMM alert failed: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"Tactical RMM integration error: {str(e)}")
            return False


class AlertManager:
    """Manages multiple alert integrations"""
    
    def __init__(self):
        self.integrations: List[AlertIntegration] = []
    
    def add_ntfy(self, topic_url: str, token: Optional[str] = None):
        """Add NTFY integration"""
        self.integrations.append(NTFYIntegration(topic_url, token))
    
    def add_n8n(self, webhook_url: str):
        """Add n8n integration"""
        self.integrations.append(N8nIntegration(webhook_url))
    
    def add_zabbix(self, zabbix_url: str, api_token: str, host_name: str = "Wegweiser"):
        """Add Zabbix integration"""
        self.integrations.append(ZabbixIntegration(zabbix_url, api_token, host_name))
    
    def add_tactical_rmm(self, api_url: str, api_key: str, client_id: int, site_id: int):
        """Add Tactical RMM integration"""
        self.integrations.append(TacticalRMMIntegration(api_url, api_key, client_id, site_id))
    
    def send_alert(self, title: str, message: str, severity: AlertSeverity = AlertSeverity.WARNING):
        """Send alert to all configured integrations"""
        results = []
        for integration in self.integrations:
            try:
                result = integration.send(title, message, severity)
                results.append(result)
            except Exception as e:
                logger.error(f"Error sending alert: {str(e)}")
                results.append(False)
        
        return all(results) if results else False


def create_alert_manager_from_env() -> AlertManager:
    """Create AlertManager from environment variables"""
    manager = AlertManager()
    
    # NTFY
    if os.getenv('NTFY_URL'):
        manager.add_ntfy(
            os.getenv('NTFY_URL'),
            os.getenv('NTFY_TOKEN')  # Optional token for self-hosted instances
        )
    
    # n8n
    if os.getenv('N8N_WEBHOOK_URL'):
        manager.add_n8n(os.getenv('N8N_WEBHOOK_URL'))
    
    # Zabbix
    if os.getenv('ZABBIX_URL') and os.getenv('ZABBIX_API_TOKEN'):
        manager.add_zabbix(
            os.getenv('ZABBIX_URL'),
            os.getenv('ZABBIX_API_TOKEN'),
            os.getenv('ZABBIX_HOST_NAME', 'Wegweiser')
        )
    
    # Tactical RMM
    if all([
        os.getenv('TACTICAL_RMM_URL'),
        os.getenv('TACTICAL_RMM_API_KEY'),
        os.getenv('TACTICAL_RMM_CLIENT_ID'),
        os.getenv('TACTICAL_RMM_SITE_ID')
    ]):
        manager.add_tactical_rmm(
            os.getenv('TACTICAL_RMM_URL'),
            os.getenv('TACTICAL_RMM_API_KEY'),
            int(os.getenv('TACTICAL_RMM_CLIENT_ID')),
            int(os.getenv('TACTICAL_RMM_SITE_ID'))
        )
    
    return manager

