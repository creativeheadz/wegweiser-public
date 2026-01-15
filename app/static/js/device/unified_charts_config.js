// Unified Gauges and Charts Configuration
// Ensures consistent styling, colors, and formatting across all health and system metrics

// Define unified color scheme
const UNIFIED_CHART_COLORS = {
    light: {
        healthScore: {
            stroke: "#9333EA",
            fill: "rgba(147, 51, 234, 0.2)"
        },
        cpu: {
            stroke: "#9333EA",
            fill: "rgba(147, 51, 234, 0.2)"
        },
        memory: {
            stroke: "#9333EA",
            fill: "rgba(147, 51, 234, 0.2)"
        },
        grid: "rgba(0, 0, 0, 0.12)",
        axisStroke: "rgba(0, 0, 0, 0.7)"
    },
    dark: {
        healthScore: {
            stroke: "#7c3aed",
            fill: "rgba(124, 58, 237, 0.2)"
        },
        cpu: {
            stroke: "#7c3aed",
            fill: "rgba(124, 58, 237, 0.2)"
        },
        memory: {
            stroke: "#7c3aed",
            fill: "rgba(124, 58, 237, 0.2)"
        },
        grid: "rgba(255, 255, 255, 0.12)",
        axisStroke: "rgba(255, 255, 255, 0.7)"
    }
};

// Get unified theme-specific colors for charts
function getUnifiedThemeColors(metricType = 'cpu') {
    const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
    const themeColors = UNIFIED_CHART_COLORS[theme];
    
    let colors;
    switch (metricType) {
        case 'healthScore':
            colors = themeColors.healthScore;
            break;
        case 'cpu':
            colors = themeColors.cpu;
            break;
        case 'memory':
            colors = themeColors.memory;
            break;
        default:
            colors = themeColors.cpu;
    }
    
    return {
        ...colors,
        grid: themeColors.grid,
        axisStroke: themeColors.axisStroke
    };
}

// Common uPlot axis configuration
function getUnifiedAxisConfig(chartColors, label, isTimeAxis = false) {
    return {
        grid: {
            stroke: chartColors.grid,
            dash: [4, 4]
        },
        stroke: chartColors.axisStroke,
        ...(isTimeAxis ? {
            values: (u, ts) =>
                ts.map(t =>
                    new Date(t * 1000).toLocaleDateString("en-GB", {
                        day: "2-digit",
                        month: "short",
                    })
                )
        } : {
            values: (u, vals) => vals.map(v => `${v.toFixed(0)}%`),
            label: label
        })
    };
}

// Get optimal chart height
function getChartHeight(container) {
    const containerHeight = $(container).parent().height();
    return Math.max(200, containerHeight - 20);
}

// Initialize all unified gauges and charts
document.addEventListener('DOMContentLoaded', function () {
    // Override the color functions in individual chart scripts
    window.UNIFIED_COLORS = UNIFIED_CHART_COLORS;
    window.getUnifiedThemeColors = getUnifiedThemeColors;
    window.getUnifiedAxisConfig = getUnifiedAxisConfig;
    window.getChartHeight = getChartHeight;
    
    // Set up MutationObserver to handle theme changes
    if (document.documentElement && document.documentElement instanceof Node) {
        const observer = new MutationObserver(function (mutations) {
            mutations.forEach(function (mutation) {
                if (mutation.attributeName === 'data-bs-theme') {
                    location.reload(); // Reload to rerender charts with new theme
                }
            });
        });
        
        observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-bs-theme']
        });
    }
});

// Gauge chart update helper
function updateGaugeWithConsistentStyle(gaugeInstance, value, lastUpdated) {
    if (gaugeInstance && typeof gaugeInstance.update === 'function') {
        gaugeInstance.update(value, lastUpdated);
    }
}
