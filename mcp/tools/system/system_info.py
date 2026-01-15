"""
System Information Tool - Example of extending MCP framework
Demonstrates how new tools can be added without modifying the framework
"""

import logging
import sys
import os
from pathlib import Path
from typing import Dict, Any

# Add parent directories to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from framework.base_tool import MCPTool

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False

logger = logging.getLogger(__name__)


class SystemInfo(MCPTool):
    """Tool for retrieving system information"""

    def __init__(self):
        """Initialize system info tool"""
        super().__init__()
        self.psutil_available = PSUTIL_AVAILABLE

    def get_metadata(self) -> Dict[str, Any]:
        """Get tool metadata"""
        return {
            "name": "system_info",
            "description": "Get system information including CPU, memory, disk, and uptime",
            "parameters": {
                "type": "object",
                "properties": {
                    "category": {
                        "type": "string",
                        "description": "Category: 'cpu', 'memory', 'disk', 'uptime', or 'all' (default: all)",
                    }
                },
                "required": [],
            },
        }

    async def execute(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute system info collection

        Args:
            parameters: Parameters dict with optional 'category'

        Returns:
            dict: System information
        """
        try:
            category = parameters.get("category", "all").lower().strip() or "all"

            logger.info(f"Collecting system info (category: {category})")

            data = {}

            # Always collect what we can without psutil
            if category in ["cpu", "all"]:
                data["cpu"] = self._get_cpu_info()

            if category in ["memory", "all"]:
                data["memory"] = self._get_memory_info()

            if category in ["disk", "all"]:
                data["disk"] = self._get_disk_info()

            if category in ["uptime", "all"]:
                data["uptime"] = self._get_uptime_info()

            logger.info(f"System info collection successful")

            return {"success": True, "data": data}

        except Exception as e:
            logger.error(f"Error collecting system info: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _get_cpu_info(self) -> Dict[str, Any]:
        """Get CPU information"""
        try:
            if self.psutil_available:
                cpu_percent = psutil.cpu_percent(interval=1)
                cpu_count = psutil.cpu_count()
                return {
                    "status": "available",
                    "percent": cpu_percent,
                    "count": cpu_count,
                    "per_cpu": psutil.cpu_percent(interval=0.1, percpu=True),
                }
            else:
                # Fallback: read from /proc/cpuinfo on Linux
                try:
                    with open("/proc/cpuinfo", "r") as f:
                        cpuinfo = f.read()
                    cpu_count = cpuinfo.count("processor")
                    return {
                        "status": "available",
                        "count": cpu_count,
                        "note": "psutil not available, limited info",
                    }
                except:
                    return {"status": "unavailable", "error": "Cannot read CPU info"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_memory_info(self) -> Dict[str, Any]:
        """Get memory information"""
        try:
            if self.psutil_available:
                mem = psutil.virtual_memory()
                return {
                    "status": "available",
                    "total_gb": round(mem.total / (1024 ** 3), 2),
                    "available_gb": round(mem.available / (1024 ** 3), 2),
                    "used_gb": round(mem.used / (1024 ** 3), 2),
                    "percent": mem.percent,
                }
            else:
                # Fallback: read from /proc/meminfo on Linux
                try:
                    with open("/proc/meminfo", "r") as f:
                        meminfo = f.readlines()
                    info_dict = {}
                    for line in meminfo[:5]:
                        key, value = line.split(":")
                        info_dict[key.strip()] = int(value.split()[0]) / (1024 ** 2)  # Convert to MB
                    return {
                        "status": "available",
                        "memory_mb": info_dict,
                        "note": "psutil not available, limited info",
                    }
                except:
                    return {"status": "unavailable", "error": "Cannot read memory info"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_disk_info(self) -> Dict[str, Any]:
        """Get disk information"""
        try:
            if self.psutil_available:
                disk = psutil.disk_usage("/")
                return {
                    "status": "available",
                    "total_gb": round(disk.total / (1024 ** 3), 2),
                    "used_gb": round(disk.used / (1024 ** 3), 2),
                    "free_gb": round(disk.free / (1024 ** 3), 2),
                    "percent": disk.percent,
                }
            else:
                # Fallback: use os.statvfs on Unix-like systems
                try:
                    stat = os.statvfs("/")
                    total = stat.f_blocks * stat.f_frsize
                    free = stat.f_bavail * stat.f_frsize
                    used = (stat.f_blocks - stat.f_bavail) * stat.f_frsize
                    return {
                        "status": "available",
                        "total_gb": round(total / (1024 ** 3), 2),
                        "used_gb": round(used / (1024 ** 3), 2),
                        "free_gb": round(free / (1024 ** 3), 2),
                        "note": "psutil not available",
                    }
                except:
                    return {"status": "unavailable", "error": "Cannot read disk info"}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    def _get_uptime_info(self) -> Dict[str, Any]:
        """Get system uptime"""
        try:
            if self.psutil_available:
                uptime_seconds = int(psutil.time.time() - psutil.boot_time())
                days = uptime_seconds // 86400
                hours = (uptime_seconds % 86400) // 3600
                minutes = (uptime_seconds % 3600) // 60
                return {
                    "status": "available",
                    "seconds": uptime_seconds,
                    "formatted": f"{days}d {hours}h {minutes}m",
                }
            else:
                # Fallback: read from /proc/uptime on Linux
                try:
                    with open("/proc/uptime", "r") as f:
                        uptime_seconds = int(float(f.read().split()[0]))
                    days = uptime_seconds // 86400
                    hours = (uptime_seconds % 86400) // 3600
                    minutes = (uptime_seconds % 3600) // 60
                    return {
                        "status": "available",
                        "seconds": uptime_seconds,
                        "formatted": f"{days}d {hours}h {minutes}m",
                    }
                except:
                    return {"status": "unavailable", "error": "Cannot read uptime"}
        except Exception as e:
            return {"status": "error", "error": str(e)}
