# Phase 3: Audit Collector Refactoring Plan

## Current State
- `fullAudit.py`: 1475 lines, cross-platform with platform conditionals
- `MacAudit.py`: 928 lines, macOS-specific (already exists)
- Both use mix of psutil and OS-specific commands

## Refactoring Strategy

### 1. Create OS-Specific Files
- **WindowsAudit.py**: Windows-specific collector
- **LinuxAudit.py**: Linux-specific collector
- **MacAudit.py**: Already exists, keep as-is

### 2. Shared Utilities Module
- Create `AuditCommon.py` with shared functions:
  - `convertSize()` - size conversion
  - `sendJsonPayloadFlask()` - payload transmission
  - `getPublicIpAddr()` - IP detection
  - `getUserHomePath()` - home directory
  - `getDeviceUuid()` - device UUID retrieval
  - `getAppDirs()` - directory setup
  - `delFile()` - file deletion

### 3. Data Collection Functions (OS-Specific)
Each OS file implements:
- `getDeviceData()` - basic device info
- `getSystemData()` - system info + NEW: comprehensive psutil CPU metrics
- `getDiskStats()` - disk information
- `getNetworkData()` - network interfaces
- `getUserData()` - logged-in users
- `getUptimeData()` - uptime info
- `getBatteryData()` - battery info
- `getMemoryData()` - memory info + NEW: comprehensive psutil memory metrics
- `getCollectorData()` - collector version
- `getManufacturer()` - manufacturer info
- `getOsLang()` - OS language
- `getCpuInfo()` - CPU info + NEW: psutil metrics
- `getGpuInfo()` - GPU info
- `getSmBiosInfo()` - BIOS info (Windows only)
- `getSystemModel()` - system model
- `getPrinters()` - printer info
- `getPciDevices()` - PCI devices (Linux only)
- `getUsbDevices()` - USB devices
- `getPartitionData()` - partition info
- `getDrivers()` - driver info (Windows only)

### 4. New psutil Integration
Each OS file will gather:

**CPU Metrics:**
- `cpu_percent()` - per-CPU usage
- `cpu_count()` - logical/physical cores
- `cpu_freq()` - frequency info
- `cpu_stats()` - context switches, interrupts
- `cpu_times()` - user, system, idle, iowait, irq

**Memory Metrics:**
- `virtual_memory()` - buffers, cached, swap
- `swap_memory()` - swap details
- All percentages and detailed breakdown

### 5. Payload Structure
```json
{
  "data": {
    "cpu": {
      "cpuname": "...",
      "cpu_metrics": {
        "cores_logical": 8,
        "cores_physical": 4,
        "frequency_current": 2.4,
        "frequency_max": 3.5,
        "cpu_percent": [12.5, 15.3, ...],
        "cpu_times": {...},
        "cpu_stats": {...}
      }
    },
    "memory": {
      "total": 16000000000,
      "available": 8000000000,
      "used": 8000000000,
      "free": 4000000000,
      "memory_metrics": {
        "buffers": 1000000000,
        "cached": 2000000000,
        "swap_total": 4000000000,
        "swap_used": 500000000,
        "swap_free": 3500000000
      }
    }
  }
}
```

## Implementation Order
1. Create `AuditCommon.py` with shared functions
2. Create `WindowsAudit.py` with Windows-specific logic
3. Create `LinuxAudit.py` with Linux-specific logic
4. Update `MacAudit.py` to use new psutil metrics
5. Test each collector independently
6. Verify payload structure matches schema
7. Test end-to-end: collection → transmission → storage → rendering

