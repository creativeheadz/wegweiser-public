// filepath: /opt/wegweiser/app/static/js/device/system_gauges.js
// static/js/system_gauges.js
// Import the shared GaugeChart class
// Make sure to include the script file in your HTML before this file
// <script src="/static/js/common/gauge_chart.js"></script>

// Initialize gauges when document is ready
document.addEventListener('DOMContentLoaded', function() {
    const deviceUuid = window.device_uuid;
    const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';

    // Get theme colors for gauges (unified colors)
    function getThemeColors() {
        const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';

        switch (theme) {
            case 'dark':
                return {
                    startColor: '#7c3aed',
                    endColor: '#06b6d4'
                };
            default:
                return {
                    startColor: '#9333EA',
                    endColor: '#EC4899'
                };
        }
    }

    const colors = getThemeColors();

    // CPU Load Gauge
    const cpuGauge = new GaugeChart('cpu-load-chart', {
        title: 'CPU Load',
        startColor: colors.startColor,
        endColor: colors.endColor
    });

    // Memory Usage Gauge
    const memoryGauge = new GaugeChart('memory-load-chart', {
        title: 'Memory Usage',
        startColor: colors.startColor,
        endColor: colors.endColor
    });

    function updateGauges() {
        if (!deviceUuid) {
            return;
        }

        // Suppress console errors
        const originalConsoleError = console.error;
        console.error = () => {};

        // Update CPU Load
        try {
            fetch(`/widgets/latest-cpu-data?device_uuid=${deviceUuid}`)
                .then(response => {
                    if (!response.ok) {
                        return;
                    }
                    return response.json();
                })
                .then(data => {
                    if (data && data.load_percentage) {
                        cpuGauge.update(parseInt(data.load_percentage), data.last_updated);
                    }
                })
                .catch(() => { /* Ignore errors */ });
        } catch (e) { /* Ignore errors */ }

        // Update Memory Usage
        try {
            fetch(`/widgets/latest-ram-data?device_uuid=${deviceUuid}`)
                .then(response => {
                    if (!response.ok) {
                        return;
                    }
                    return response.json();
                })
                .then(data => {
                    if (data && data.memory_percentage) {
                        memoryGauge.update(parseFloat(data.memory_percentage), data.last_updated);
                    }
                })
                .catch(() => { /* Ignore errors */ });
        } catch (e) { /* Ignore errors */ }

        // Restore original console.error
        console.error = originalConsoleError;
    }

    // Initial update
    updateGauges();

    // Update every minute
    setInterval(updateGauges, 60000);
});
