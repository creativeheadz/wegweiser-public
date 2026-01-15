"""
Health Monitor - Track agent health and metrics
"""

import logging
import time
from typing import Dict, Any
from datetime import datetime

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Monitor and report agent health"""
    
    def __init__(self, device_uuid: str, agent_version: str = "3.0.0-poc"):
        """Initialize health monitor"""
        self.device_uuid = device_uuid
        self.agent_version = agent_version
        self.start_time = time.time()
        
        # Metrics
        self.total_snippets = 0
        self.successful_snippets = 0
        self.failed_snippets = 0
        self.execution_times = []
        self.last_heartbeat = None
        self.last_error = None
    
    def record_execution(self, status: str, duration_ms: int):
        """Record snippet execution"""
        self.total_snippets += 1
        self.execution_times.append(duration_ms)
        
        if status == 'success':
            self.successful_snippets += 1
        else:
            self.failed_snippets += 1
            self.last_error = f"Execution failed with status: {status}"
        
        logger.debug(f"Execution recorded: {status} ({duration_ms}ms)")
    
    def record_error(self, error: str):
        """Record error"""
        self.last_error = error
        logger.error(f"Error recorded: {error}")
    
    def get_success_rate(self) -> float:
        """Get snippet success rate"""
        if self.total_snippets == 0:
            return 0.0
        return (self.successful_snippets / self.total_snippets) * 100
    
    def get_avg_execution_time(self) -> float:
        """Get average execution time"""
        if not self.execution_times:
            return 0.0
        return sum(self.execution_times) / len(self.execution_times)
    
    def get_uptime_seconds(self) -> int:
        """Get agent uptime"""
        return int(time.time() - self.start_time)
    
    def get_health_report(self) -> Dict[str, Any]:
        """Get comprehensive health report"""
        self.last_heartbeat = int(time.time() * 1000)
        
        return {
            'device_uuid': self.device_uuid,
            'timestamp': self.last_heartbeat,
            'agent_version': self.agent_version,
            'uptime_seconds': self.get_uptime_seconds(),
            'metrics': {
                'total_snippets': self.total_snippets,
                'successful_snippets': self.successful_snippets,
                'failed_snippets': self.failed_snippets,
                'success_rate_percent': self.get_success_rate(),
                'avg_execution_time_ms': self.get_avg_execution_time()
            },
            'status': 'healthy' if self.get_success_rate() > 80 else 'degraded',
            'last_error': self.last_error
        }

