# Phase 2: Payload Processing Analysis & Updates

## Complete Data Flow Architecture

### 1. Audit Collection (Agent)
- Agent collects system data using psutil and OS-specific tools
- Sends JSON payload to `/payload/sendaudit` endpoint
- Payload validated against `includes/payloadAuditSchema.json`
- Valid payloads queued to `payloads/queue/` as `.audit.json` files

### 2. Payload Reception (`/payload/sendaudit`)
- Receives JSON POST request from agent
- Validates against schema (now supports optional `cpu_metrics` and `memory_metrics`)
- Writes to queue directory for async processing
- Returns 200 OK

### 3. Payload Processing (`/payload/processpayloads`)
- Reads queued `.audit.json` files
- Calls sequence of `upsertDevice*` functions:
  - `upsertDeviceStatus()` - system-level CPU/memory usage
  - `upsertDeviceBattery()` - battery info
  - `upsertDeviceMemory()` - memory stats + NEW: memory_metrics_json
  - `upsertDeviceNetworks()` - network interfaces
  - `upsertDeviceUsers()` - logged-in users
  - `upsertDevicePartitions()` - disk partitions
  - `upsertDeviceDrives()` - storage drives
  - `upsertDeviceCpu()` - CPU info + NEW: cpu_metrics_json
  - `upsertDeviceGpu()` - GPU info
  - `upsertDeviceBios()` - BIOS info
  - `upsertDeviceColl()` - collector version
  - `upsertDevicePrinters()` - printers
  - `upsertDeviceDrivers()` - drivers

### 4. Database Storage (Updated)
- **DeviceCpu**: Added `cpu_metrics_json` (JSONB, nullable)
- **DeviceMemory**: Added `memory_metrics_json` (JSONB, nullable)
- Uses PostgreSQL UPSERT pattern (INSERT ... ON CONFLICT DO UPDATE)
- Maintains backward compatibility with existing data

### 5. Data Retrieval & Rendering
- Route: `app/routes/devices/devices_deviceuuid.py`
- Uses `DeviceDataAggregator` to fetch all device data
- Calls individual providers:
  - `DeviceCpuProvider` - fetches CPU data + NEW: cpu_metrics_json
  - `DeviceMemoryProvider` - fetches memory data + NEW: memory_metrics_json
- Flattens data structure for template compatibility
- Passes `device.modular_data` to template

### 6. Template Rendering
- `index-single-device.html` includes component templates
- `cpu_card.html` - displays CPU info (ready for extended metrics)
- `memory_card.html` - displays memory info (ready for extended metrics)
- `battery_card.html` - displays battery (needs conditional rendering)

## Changes Made in Phase 2

### 1. Payload Processing (`app/routes/payload.py`)
- Updated `upsertDeviceCpu()` to extract and store `cpu_metrics_json`
- Updated `upsertDeviceMemory()` to extract and store `memory_metrics_json`
- Both functions now handle optional metrics gracefully

### 2. Data Providers
- Updated `DeviceCpuProvider` to include `cpu_metrics_json` in returned data
- Updated `DeviceMemoryProvider` to include `memory_metrics_json` in returned data
- Data flows through to templates via `device.modular_data`

### 3. Payload Schema (`includes/payloadAuditSchema.json`)
- Added optional `memory_metrics` object to memory section
- Added new `cpu` section with `cpuname` (required) and `cpu_metrics` (optional)
- Maintains backward compatibility

## Next Steps (Phase 3+)

1. **Refactor Collectors**: Split into OS-specific files
2. **Implement psutil Collection**: Gather comprehensive CPU/memory metrics
3. **Update Templates**: Display extended metrics from JSONB
4. **Conditional Rendering**: Hide empty sections (battery, GPU, etc.)

