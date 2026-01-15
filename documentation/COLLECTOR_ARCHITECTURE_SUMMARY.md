# Collector Architecture Summary

## File Structure

```
snippets/unSigned/
├── AuditCommon.py          # Shared utilities (all platforms)
├── PsutilMetrics.py        # Comprehensive psutil metrics (all platforms)
├── WindowsAudit.py         # Windows-specific collector
├── LinuxAudit.py           # Linux-specific collector
└── MacAudit.py             # macOS-specific collector (updated)
```

## Module Responsibilities

### AuditCommon.py
Provides shared functions used by all collectors:
- `convertSize()` - Convert bytes to human-readable format
- `sendJsonPayloadFlask()` - Send JSON payload to Flask endpoint
- `getPublicIpAddr()` - Get public IP address
- `getUserHomePath()` - Get user home directory
- `getDeviceUuid()` - Read device UUID from config
- `getAppDirs()` - Setup application directories
- `delFile()` - Delete files
- `ensurePsutil()` - Ensure psutil is installed

### PsutilMetrics.py
Provides comprehensive psutil data collection:
- `getCpuMetrics()` - Gather all CPU metrics
  - Cores (logical/physical)
  - Frequency (current/min/max)
  - Per-CPU usage percentages
  - CPU times (user/system/idle/iowait/irq/softirq)
  - CPU stats (context switches, interrupts)
- `getMemoryMetrics()` - Gather all memory metrics
  - Buffers, cached, shared
  - Swap (total/used/free)
  - Memory percentage

### WindowsAudit.py
Windows-specific collector with 19 functions:
- `getCpuInfo()` - CPU name + psutil metrics
- `getMemoryData()` - Memory info + psutil metrics
- `getSystemData()` - System info
- `getDiskStats()` - Disk information
- `getNetworkData()` - Network interfaces
- `getUserData()` - Logged-in users
- `getBatteryData()` - Battery status
- `getUptimeData()` - Uptime info
- `getCollectorData()` - Collector version
- `getDeviceData()` - Device UUID/timestamp
- `getPartitionData()` - Partition info
- `getGpuInfo()` - GPU info (PowerShell)
- `getManufacturer()` - System manufacturer (WMI)
- `getOsLang()` - OS language (WMI)
- `getSmBiosInfo()` - BIOS info (WMI)
- `getSystemModel()` - System model (WMI)
- `getPrinters()` - Printer list (WMI)
- `getUsbDevices()` - USB devices (WMI)
- `getDrivers()` - Driver list (WMI)

### LinuxAudit.py
Linux-specific collector with 20 functions:
- Same as Windows but with Linux-specific tools:
  - `lscpu` for CPU name
  - `lspci` for GPU/PCI devices
  - `lsusb` for USB devices
  - `dmidecode` for BIOS/manufacturer
  - `lpstat` for printers
  - `locale` for OS language
- Plus `getPciDevices()` for PCI enumeration

### MacAudit.py
macOS-specific collector (updated):
- Uses `sysctl` for CPU name
- Uses `system_profiler` for GPU/display info
- Updated `getCpuInfo()` to use `getCpuMetrics()`
- Updated `getmemoryData()` to use `getMemoryMetrics()`
- Maintains existing macOS-specific functions

## Data Flow

```
Collector (Windows/Linux/macOS)
    ↓
Gather system data using psutil + OS-specific tools
    ↓
Build payload with cpu_metrics and memory_metrics
    ↓
Send to /payload/sendaudit endpoint
    ↓
Validate against payloadAuditSchema.json
    ↓
Queue for processing
    ↓
/payload/processpayloads
    ↓
upsertDeviceCpu() - stores cpu_metrics_json
upsertDeviceMemory() - stores memory_metrics_json
    ↓
PostgreSQL JSONB columns
    ↓
DeviceDataAggregator queries data
    ↓
DeviceCpuProvider/MemoryProvider format data
    ↓
Templates render with extended metrics
```

## Key Features

1. **Comprehensive**: Gathers ALL psutil data available
2. **OS-Specific**: Optimized for each platform
3. **Reusable**: Shared modules reduce duplication
4. **Flexible**: JSONB storage allows variable metrics
5. **Backward Compatible**: Existing payloads still work
6. **Extensible**: Easy to add new metrics
7. **Robust**: Error handling for missing tools
8. **Signed**: Ready for deployment after signing

## Next Steps: Phase 4

Template enhancement to display:
- Extended CPU metrics (cores, frequency, context switches)
- Extended memory metrics (buffers, cached, swap)
- Conditional rendering (hide empty sections)
- Improved data visualization

