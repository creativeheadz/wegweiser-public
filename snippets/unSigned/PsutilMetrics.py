# Filepath: snippets/unSigned/PsutilMetrics.py
"""
Comprehensive psutil metrics collection for all platforms
Used by WindowsAudit, LinuxAudit, MacAudit
"""
import psutil
from logzero import logger

def getCpuMetrics():
    """
    Gather comprehensive CPU metrics using psutil
    
    Returns:
        dict: CPU metrics including cores, frequency, usage, times, stats
    """
    try:
        cpu_metrics = {}
        
        # Core information
        cpu_metrics['cores_logical'] = psutil.cpu_count(logical=True)
        cpu_metrics['cores_physical'] = psutil.cpu_count(logical=False)
        
        # Frequency information
        try:
            freq = psutil.cpu_freq()
            if freq:
                cpu_metrics['frequency_current'] = round(freq.current, 2)
                cpu_metrics['frequency_min'] = round(freq.min, 2)
                cpu_metrics['frequency_max'] = round(freq.max, 2)
        except Exception as e:
            logger.debug(f'Could not get CPU frequency: {e}')
        
        # Per-CPU usage percentage
        try:
            cpu_percent = psutil.cpu_percent(interval=1, percpu=True)
            cpu_metrics['cpu_percent'] = [round(p, 2) for p in cpu_percent]
        except Exception as e:
            logger.debug(f'Could not get per-CPU percent: {e}')
        
        # Overall CPU usage
        try:
            cpu_metrics['cpu_percent_overall'] = round(psutil.cpu_percent(interval=0.1), 2)
        except Exception as e:
            logger.debug(f'Could not get overall CPU percent: {e}')
        
        # CPU times (user, system, idle, iowait, irq, softirq)
        try:
            times = psutil.cpu_times()
            cpu_metrics['cpu_times'] = {
                'user': round(times.user, 2),
                'system': round(times.system, 2),
                'idle': round(times.idle, 2),
                'iowait': round(times.iowait, 2) if hasattr(times, 'iowait') else None,
                'irq': round(times.irq, 2) if hasattr(times, 'irq') else None,
                'softirq': round(times.softirq, 2) if hasattr(times, 'softirq') else None,
            }
        except Exception as e:
            logger.debug(f'Could not get CPU times: {e}')
        
        # CPU statistics (context switches, interrupts)
        try:
            stats = psutil.cpu_stats()
            cpu_metrics['cpu_stats'] = {
                'ctx_switches': stats.ctx_switches,
                'interrupts': stats.interrupts,
                'soft_interrupts': stats.soft_interrupts,
                'syscalls': stats.syscalls if hasattr(stats, 'syscalls') else None,
            }
        except Exception as e:
            logger.debug(f'Could not get CPU stats: {e}')
        
        logger.info(f'Successfully gathered CPU metrics')
        return cpu_metrics
        
    except Exception as e:
        logger.error(f'Error gathering CPU metrics: {e}')
        return {}

def getMemoryMetrics():
    """
    Gather comprehensive memory metrics using psutil
    
    Returns:
        dict: Memory metrics including buffers, cached, swap details
    """
    try:
        memory_metrics = {}
        
        # Virtual memory details
        try:
            vmem = psutil.virtual_memory()
            memory_metrics['buffers'] = vmem.buffers if hasattr(vmem, 'buffers') else None
            memory_metrics['cached'] = vmem.cached if hasattr(vmem, 'cached') else None
            memory_metrics['shared'] = vmem.shared if hasattr(vmem, 'shared') else None
            memory_metrics['percent'] = round(vmem.percent, 2)
        except Exception as e:
            logger.debug(f'Could not get virtual memory details: {e}')
        
        # Swap memory details
        try:
            swap = psutil.swap_memory()
            memory_metrics['swap_total'] = swap.total
            memory_metrics['swap_used'] = swap.used
            memory_metrics['swap_free'] = swap.free
            memory_metrics['swap_percent'] = round(swap.percent, 2)
        except Exception as e:
            logger.debug(f'Could not get swap memory details: {e}')
        
        logger.info(f'Successfully gathered memory metrics')
        return memory_metrics
        
    except Exception as e:
        logger.error(f'Error gathering memory metrics: {e}')
        return {}

