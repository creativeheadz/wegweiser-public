/**
 * Chart Utilities for Wegweiser
 * Provides common functionality for uPlot charts across the application
 */

/**
 * Calculate optimal chart dimensions based on container and screen size
 * @param {jQuery} container - The chart container element
 * @param {Object} options - Optional configuration
 * @returns {Object} - Width and height dimensions
 */
function calculateChartDimensions(container, options = {}) {
    const defaults = {
        minHeight: 300,
        maxHeight: 500,
        aspectRatio: 0.6,
        useContainerHeight: true
    };
    
    const config = { ...defaults, ...options };
    const containerWidth = container.width();
    const containerHeight = container.height();
    
    let height;
    
    if (config.useContainerHeight && containerHeight > 0) {
        height = containerHeight;
    } else {
        // Calculate based on width and aspect ratio
        height = Math.max(config.minHeight, Math.min(config.maxHeight, containerWidth * config.aspectRatio));
    }
    
    // Ensure minimum height for readability
    height = Math.max(height, config.minHeight);
    
    return {
        width: containerWidth,
        height: height
    };
}

/**
 * Get theme-specific colors for charts
 * @param {string} theme - Theme name ('light' or 'dark')
 * @returns {Object} - Color configuration
 */
function getChartThemeColors(theme = null) {
    const currentTheme = theme || document.documentElement.getAttribute('data-bs-theme') || 'light';
    
    switch (currentTheme) {
        case 'dark':
            return {
                stroke: "#55DFFC",
                fill: "rgba(79, 123, 255, 0.2)",
                gridStroke: "rgba(255, 255, 255, 0.1)",
                grid: "rgba(255, 255, 255, 0.1)",
                textColor: "#FFFFFF",
                axisStroke: "rgba(255, 255, 255, 0.7)"
            };
        default:  // light theme
            return {
                stroke: "#ff0080",
                fill: "rgba(255, 0, 128, 0.2)",
                gridStroke: "rgba(0, 0, 0, 0.15)",
                grid: "rgba(0, 0, 0, 0.15)",
                textColor: "#1A1D21",
                axisStroke: "rgba(0, 0, 0, 0.7)"
            };
    }
}

/**
 * Create a debounced resize handler for charts
 * @param {Function} resizeCallback - Function to call on resize
 * @param {number} delay - Debounce delay in milliseconds
 * @returns {Function} - Debounced resize handler
 */
function createDebouncedResizeHandler(resizeCallback, delay = 150) {
    let resizeTimeout;
    
    return function() {
        clearTimeout(resizeTimeout);
        resizeTimeout = setTimeout(resizeCallback, delay);
    };
}

/**
 * Setup chart loading state
 * @param {jQuery} container - The chart container element
 */
function showChartLoading(container) {
    container.addClass('loading');
}

/**
 * Remove chart loading state
 * @param {jQuery} container - The chart container element
 */
function hideChartLoading(container) {
    container.removeClass('loading');
}

/**
 * Display chart error message
 * @param {jQuery} container - The chart container element
 * @param {string} message - Error message to display
 */
function showChartError(container, message = 'Failed to load chart data') {
    hideChartLoading(container);
    container.html(`<div class="alert alert-danger">${message}</div>`);
}

/**
 * Setup theme change observer for charts
 * @param {Object} uplot - uPlot instance
 * @param {Function} getThemeColors - Function to get theme colors
 * @returns {MutationObserver} - Observer instance
 */
function setupThemeObserver(uplot, getThemeColors) {
    const observer = new MutationObserver(function(mutations) {
        for (const mutation of mutations) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
                // Get new colors based on updated theme
                const newColors = getThemeColors();

                // Update chart colors
                if (uplot.series[1]) {
                    uplot.series[1].stroke = newColors.stroke;
                    uplot.series[1].fill = newColors.fill;
                }

                // Update grid colors
                if (uplot.axes[0] && uplot.axes[0].grid) {
                    uplot.axes[0].grid.stroke = newColors.gridStroke || newColors.grid;
                }
                if (uplot.axes[1] && uplot.axes[1].grid) {
                    uplot.axes[1].grid.stroke = newColors.gridStroke || newColors.grid;
                }

                // Update axis label colors
                if (uplot.axes[0]) {
                    uplot.axes[0].stroke = newColors.axisStroke;
                }
                if (uplot.axes[1]) {
                    uplot.axes[1].stroke = newColors.axisStroke;
                }

                // Redraw the chart
                uplot.redraw();
            }
        }
    });

    observer.observe(document.documentElement, {
        attributes: true,
        attributeFilter: ['data-bs-theme']
    });

    return observer;
}

/**
 * Create standard uPlot configuration for health score charts
 * @param {Object} options - Configuration options
 * @returns {Object} - uPlot configuration
 */
function createHealthScoreChartConfig(options) {
    const {
        id,
        width,
        height,
        colors,
        yAxisLabel = "Health Score"
    } = options;

    return {
        id: id,
        width: width,
        height: height,
        scales: {
            x: { time: true },
            y: { range: [0, 100] },
        },
        series: [
            { label: "Time" },
            {
                label: "Health Score",
                stroke: colors.stroke,
                width: 2,
                fill: colors.fill,
            },
        ],
        axes: [
            {
                grid: {
                    stroke: colors.gridStroke || colors.grid,
                    dash: [4, 4],
                },
                stroke: colors.axisStroke,
                values: (u, ts) =>
                    ts.map(t =>
                        new Date(t * 1000).toLocaleDateString("en-GB", {
                            day: "2-digit",
                            month: "short",
                        })
                    ),
            },
            {
                grid: {
                    stroke: colors.gridStroke || colors.grid,
                    dash: [4, 4],
                },
                stroke: colors.axisStroke,
                values: (u, vals) => vals.map(v => `${v.toFixed(0)}`),
                label: yAxisLabel,
            },
        ],
    };
}

/**
 * Preload chart data to improve performance
 * @param {string} url - Data URL
 * @returns {Promise} - Promise that resolves with chart data
 */
function preloadChartData(url) {
    return fetch(url)
        .then(response => {
            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }
            return response.json();
        })
        .catch(error => {
            console.error('Failed to preload chart data:', error);
            throw error;
        });
}

// Export functions for use in other scripts
window.ChartUtils = {
    calculateChartDimensions,
    getChartThemeColors,
    createDebouncedResizeHandler,
    showChartLoading,
    hideChartLoading,
    showChartError,
    setupThemeObserver,
    createHealthScoreChartConfig,
    preloadChartData
};
