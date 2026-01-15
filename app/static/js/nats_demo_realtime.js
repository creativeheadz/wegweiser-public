// Filepath: app/static/js/nats_demo_realtime.js
// NATS Demo Real-time Dashboard JavaScript

class NATSDemoMonitor {
    constructor() {
        this.socket = null;
        this.isConnected = false;
        this.messageCount = 0;
        this.deviceUuid = '510a188e-ca5b-48cc-8fe7-173f14fa8928';
        this.charts = {};
        this.gauges = {};
        this.lastNetworkIn = 0;
        this.lastNetworkOut = 0;
        this.lastNetworkTime = 0;

        this.initializeCharts();
        this.autoStartMonitoring();
        this.updateStatus();
    }
    
    initializeCharts() {
        // Initialize gauges
        this.initializeGauge('cpuGauge', 'CPU', '#007bff');
        this.initializeGauge('memoryGauge', 'Memory', '#17a2b8');
        this.initializeGauge('diskGauge', 'Disk', '#ffc107');
        this.initializeGauge('loadGauge', 'Load', '#dc3545');
        
        // Initialize timeline chart
        // Timeline chart removed for now
    }
    
    initializeGauge(canvasId, label, color) {
        const canvas = document.getElementById(canvasId);
        if (!canvas) return;
        const ctx = canvas.getContext('2d');
        this.gauges[canvasId] = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: [color, '#e9ecef'],
                    borderWidth: 0
                }]
            },
            options: {
                responsive: false,
                maintainAspectRatio: false,
                cutout: '70%',
                plugins: {
                    legend: { display: false },
                    tooltip: { enabled: false }
                }
            }
        });
    }
    
    initializeTimelineChart() {
        // timeline removed
        return;
    }
    
    autoStartMonitoring() {
        // Auto-start monitoring when page loads
        console.log('Auto-starting NATS demo monitoring...');
        this.startPolling();
    }
    
    // Removed startMonitoring method - auto-starts now
    
    // Removed stopMonitoring and connectWebSocket - simplified
    
    startPolling() {
        this.isConnected = true;
        this.updateConnectionStatus('Live', 'success');

        console.log('Starting metrics polling every 2 seconds...');

        // Poll for new data every 2 seconds
        this.pollInterval = setInterval(() => {
            this.fetchLatestMetrics();
        }, 2000);

        // Also fetch immediately
        this.fetchLatestMetrics();
    }
    
    async fetchLatestMetrics() {
        if (!this.isConnected) return;
        
        try {
            const metrics = ['cpu_percent', 'memory_percent', 'disk_percent', 'network_bytes_in', 'network_bytes_out', 'uptime'];
            
            for (const metric of metrics) {
                const response = await fetch(`/admin/nats-demo/api/metrics/${this.deviceUuid}/${metric}?limit=1`);
                const data = await response.json();
                
                if (data.data && data.data.length > 0) {
                    const latestValue = data.data[data.data.length - 1];
                    this.updateMetric(metric, latestValue.value, latestValue.timestamp);
                }
            }

            this.messageCount++;
            const msgEl = document.getElementById('messageCount');
            if (msgEl) msgEl.textContent = this.messageCount;

        } catch (error) {
            console.error('Error fetching metrics:', error);
        }
    }
    
    updateMetric(metricType, value, timestamp) {
        const now = new Date(timestamp);
        const timeStr = now.toLocaleTimeString();
        
        switch (metricType) {
            case 'cpu_percent':
                this.updateGauge('cpuGauge', value);
                const el = document.getElementById('cpuValue');
                if (el) el.textContent = `${value.toFixed(1)}%`;
                // timeline removed
                break;
                
            case 'memory_percent':
                this.updateGauge('memoryGauge', value);
                const mel = document.getElementById('memoryValue');
                if (mel) mel.textContent = `${value.toFixed(1)}%`;
                // timeline removed
                break;
                
            case 'disk_percent':
                this.updateGauge('diskGauge', value);
                const del = document.getElementById('diskValue');
                if (del) del.textContent = `${value.toFixed(1)}%`;
                // timeline removed
                break;
                
            case 'network_bytes_in':
                this.updateNetworkMetric('in', value, timestamp);
                break;
                
            case 'network_bytes_out':
                this.updateNetworkMetric('out', value, timestamp);
                break;
                
            case 'uptime':
                this.updateUptime(value);
                break;
        }
        
        const lu = document.getElementById('lastUpdateValue');
        if (lu) lu.textContent = timeStr;
    }
    
    updateGauge(gaugeId, value) {
        const gauge = this.gauges[gaugeId];
        if (gauge) {
            gauge.data.datasets[0].data = [value, 100 - value];
            gauge.update('none');
        }
    }
    
    addToTimeline(datasetIndex, value, timeLabel) {
        const chart = this.charts.timeline;
        const maxPoints = 50;
        
        // Add new data point if the time changed
        const lastLabel = chart.data.labels[chart.data.labels.length - 1];
        if (lastLabel !== timeLabel) {
            chart.data.labels.push(timeLabel);
            chart.data.datasets[datasetIndex].data.push(value);
        } else {
            // Overwrite the latest value to avoid growing labels
            chart.data.datasets[datasetIndex].data[chart.data.datasets[datasetIndex].data.length - 1] = value;
        }

        // Clamp to maxPoints
        while (chart.data.labels.length > maxPoints) {
            chart.data.labels.shift();
            chart.data.datasets.forEach(dataset => dataset.data.shift());
        }

        chart.update('none');
    }
    
    updateNetworkMetric(direction, bytes, timestamp) {
        const currentTime = timestamp;
        
        if (direction === 'in') {
            if (this.lastNetworkTime > 0) {
                const timeDiff = (currentTime - this.lastNetworkTime) / 1000; // seconds
                const bytesDiff = bytes - this.lastNetworkIn;
                const bytesPerSecond = bytesDiff / timeDiff;
                
                const niv = document.getElementById('networkInValue');
                if (niv) niv.textContent = this.formatBytes(bytesPerSecond) + '/s';
            }
            this.lastNetworkIn = bytes;
        } else {
            if (this.lastNetworkTime > 0) {
                const timeDiff = (currentTime - this.lastNetworkTime) / 1000;
                const bytesDiff = bytes - this.lastNetworkOut;
                const bytesPerSecond = bytesDiff / timeDiff;
                
                const nov = document.getElementById('networkOutValue');
                if (nov) nov.textContent = this.formatBytes(bytesPerSecond) + '/s';
            }
            this.lastNetworkOut = bytes;
        }
        
        this.lastNetworkTime = currentTime;
    }
    
    updateUptime(seconds) {
        const days = Math.floor(seconds / 86400);
        const hours = Math.floor((seconds % 86400) / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        
        const up = document.getElementById('uptimeValue');
        if (up) up.textContent = `${days}d ${hours}h ${minutes}m`;
    }
    
    formatBytes(bytes) {
        if (bytes === 0) return '0 B';
        
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(Math.abs(bytes)) / Math.log(k));
        
        return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
    }
    
    updateConnectionStatus(status, type) {
        const statusElement = document.getElementById('connectionStatus');
        if (statusElement) {
            statusElement.textContent = status;
            statusElement.className = `badge badge-${type}`;
        }
    }
    
    clearMetrics() {
        // Clear all charts
        this.charts.timeline.data.labels = [];
        this.charts.timeline.data.datasets.forEach(dataset => dataset.data = []);
        this.charts.timeline.update();
        
        // Reset gauges
        Object.values(this.gauges).forEach(gauge => {
            gauge.data.datasets[0].data = [0, 100];
            gauge.update();
        });
        
        // Reset values
        document.getElementById('cpuValue').textContent = '0%';
        document.getElementById('memoryValue').textContent = '0%';
        document.getElementById('diskValue').textContent = '0%';
        document.getElementById('loadValue').textContent = '0.0';
        document.getElementById('networkInValue').textContent = '0 B/s';
        document.getElementById('networkOutValue').textContent = '0 B/s';
        document.getElementById('uptimeValue').textContent = 'Unknown';
        
        this.messageCount = 0;
        document.getElementById('messageCount').textContent = '0';
    }
    
    async updateStatus() {
        try {
            const response = await fetch('/admin/nats-demo/api/status');
            const status = await response.json();
            
            const ns = document.getElementById('natsStatus');
            if (ns) {
                ns.textContent = status.running ? 'Running' : 'Stopped';
                ns.className = `badge badge-${status.running ? 'success' : 'secondary'}`;
            }
            const dc = document.getElementById('deviceCount');
            if (dc) dc.textContent = status.devices_monitored;
            const dp = document.getElementById('dataPointsValue');
            if (dp) dp.textContent = status.total_metrics;
            
        } catch (error) {
            console.error('Error updating status:', error);
        }
        
        // Update status every 5 seconds
        setTimeout(() => this.updateStatus(), 5000);
    }
}

// Initialize when page loads
document.addEventListener('DOMContentLoaded', function() {
    window.natsDemo = new NATSDemoMonitor();
});
