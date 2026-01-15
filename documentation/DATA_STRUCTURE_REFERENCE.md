# Data Structure Reference: CPU & Memory Metrics

## Payload Structure (From Collector)

```json
{
  "data": {
    "device": {
      "deviceUuid": "uuid-string",
      "systemtime": 1234567890
    },
    "system": {
      "cpuUsage": 25.5,
      "cpuCount": 8
    },
    "cpu": {
      "cpuname": "Intel Core i7-9700K",
      "cpu_metrics": {
        "cores_logical": 8,
        "cores_physical": 8,
        "frequency_current": 3.6,
        "frequency_max": 4.9,
        "cpu_percent": [12.5, 15.3, 10.2, 18.7, 14.1, 16.9, 13.4, 17.2],
        "cpu_times": {
          "user": 1234.5,
          "system": 567.8,
          "idle": 9876.5,
          "iowait": 123.4,
          "irq": 45.6,
          "softirq": 23.4
        },
        "cpu_stats": {
          "ctx_switches": 1234567,
          "interrupts": 9876543,
          "soft_interrupts": 5432109
        }
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
        "shared": 500000000,
        "swap_total": 4000000000,
        "swap_used": 500000000,
        "swap_free": 3500000000,
        "percent": 50.0
      }
    }
  }
}
```

## Database Storage (PostgreSQL)

### DeviceCpu Table
```sql
deviceuuid (UUID, PK)
last_update (INTEGER)
last_json (INTEGER)
cpu_name (VARCHAR 255)
cpu_metrics_json (JSONB) -- Stores entire cpu_metrics object
```

### DeviceMemory Table
```sql
deviceuuid (UUID, PK)
last_update (INTEGER)
last_json (INTEGER)
total_memory (BIGINT)
available_memory (BIGINT)
used_memory (BIGINT)
free_memory (BIGINT)
cache_memory (BIGINT)
mem_used_percent (FLOAT)
mem_free_percent (FLOAT)
memory_metrics_json (JSONB) -- Stores entire memory_metrics object
```

## Template Access (Jinja2)

```jinja2
{# Basic CPU info #}
{{ device.modular_data.cpu.cpu_name }}

{# Extended CPU metrics #}
{{ device.modular_data.cpu.cpu_metrics_json.cores_logical }}
{{ device.modular_data.cpu.cpu_metrics_json.cores_physical }}
{{ device.modular_data.cpu.cpu_metrics_json.frequency_current }}
{{ device.modular_data.cpu.cpu_metrics_json.cpu_percent }}

{# Basic memory info #}
{{ device.modular_data.memory.total_memory_gb }}
{{ device.modular_data.memory.mem_used_percent }}

{# Extended memory metrics #}
{{ device.modular_data.memory.memory_metrics_json.buffers }}
{{ device.modular_data.memory.memory_metrics_json.cached }}
{{ device.modular_data.memory.memory_metrics_json.swap_total }}
```

## Conditional Rendering Example

```jinja2
{% if device.modular_data.cpu.cpu_metrics_json %}
  <div class="cpu-metrics">
    <p>Cores: {{ device.modular_data.cpu.cpu_metrics_json.cores_logical }}</p>
    <p>Frequency: {{ device.modular_data.cpu.cpu_metrics_json.frequency_current }} GHz</p>
  </div>
{% endif %}
```

