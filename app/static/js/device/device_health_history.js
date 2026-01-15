$(function () {
    "use strict";

    // Function to get theme-specific colors for charts (unified)
    function getThemeColors(theme) {
        switch (theme) {
            case 'dark':
                return {
                    stroke: "#7c3aed",
                    fill: "rgba(124, 58, 237, 0.2)",
                    grid: "rgba(255, 255, 255, 0.12)",
                    axisStroke: "rgba(255, 255, 255, 0.7)"
                };
            default: // light theme
                return {
                    stroke: "#9333EA",
                    fill: "rgba(147, 51, 234, 0.2)",
                    grid: "rgba(0, 0, 0, 0.12)",
                    axisStroke: "rgba(0, 0, 0, 0.7)"
                };
        }
    }

    if ($("#device-health-history").length) {
        // Add loading state
        const chartContainer = $("#device-health-history");
        chartContainer.addClass('loading');

        $.get('/devices/device/' + window.device_uuid + '/health_history', function (response) {
            try {
                // Remove loading state
                chartContainer.removeClass('loading');

                // Map the response data to extract timestamps and values
                const timestamps = response.map(data => new Date(data.x).getTime() / 1000); // Convert to seconds
                const values = response.map(data => data.y);

                const data = [timestamps, values];

                // Get theme-aware colors
                const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
                let chartColors = getThemeColors(currentTheme);

                // Calculate optimal chart dimensions with mobile safeguards
                function getChartDimensions() {
                    let containerWidth = chartContainer.width();
                    const containerHeight = chartContainer.height();

                    // Guard against zero or very small widths (mobile/hidden containers)
                    if (containerWidth < 50) {
                        containerWidth = 320; // Safe default fallback
                    }

                    // Use container height if available, otherwise calculate based on width
                    let height = containerHeight > 0 ? containerHeight : Math.max(300, Math.min(400, containerWidth * 0.6));

                    // Ensure minimum height for readability
                    height = Math.max(height, 300);

                    return {
                        width: containerWidth,
                        height: height
                    };
                }

                // Skip chart creation if container is hidden
                if (chartContainer[0].offsetParent === null) {
                    chartContainer.removeClass('loading');
                    chartContainer.html('<div class="text-muted small text-center">Chart unavailable</div>');
                    return;
                }

                const dimensions = getChartDimensions();

                // uPlot configuration
                const opts = {
                    id: "device-health-history",
                    width: dimensions.width,
                    height: dimensions.height,
                    scales: {
                        x: { time: true },
                        y: { range: [0, 100] },
                    },
                    series: [
                        { label: "Time" },
                        {
                            label: "Health Score",
                            stroke: chartColors.stroke,
                            width: 2,
                            fill: chartColors.fill,
                        },
                    ],
                    axes: [
                        {
                            grid: {
                                stroke: chartColors.grid,
                                dash: [4, 4],
                            },
                            stroke: chartColors.axisStroke,
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
                                stroke: chartColors.grid,
                                dash: [4, 4],
                            },
                            stroke: chartColors.axisStroke,
                            values: (u, vals) => vals.map(v => `${v.toFixed(0)}`),
                            label: "Health Score",
                        },
                    ],
                };

                // Create uPlot instance
                const uplot = new uPlot(opts, data, document.querySelector("#device-health-history"));

                // Handle responsive resizing with debouncing
                let resizeTimeout;
                $(window).on("resize", function () {
                    clearTimeout(resizeTimeout);
                    resizeTimeout = setTimeout(function() {
                        // Only resize if container is visible and has reasonable width
                        if (chartContainer[0].offsetParent !== null) {
                            const newDimensions = getChartDimensions();
                            if (newDimensions.width >= 50) {
                                uplot.setSize({
                                    width: newDimensions.width,
                                    height: newDimensions.height,
                                });
                            }
                        }
                    }, 150); // Debounce resize events
                });

                // Add theme change observer to update chart colors
                const themeObserver = new MutationObserver(function(mutations) {
                    mutations.forEach(function(mutation) {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
                            const newTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
                            const newColors = getThemeColors(newTheme);

                            // Update series colors
                            uplot.setSeries(1, {
                                stroke: newColors.stroke,
                                fill: newColors.fill
                            });

                            // Force redraw
                            uplot.redraw();
                        }
                    });
                });

                themeObserver.observe(document.documentElement, {
                    attributes: true,
                    attributeFilter: ['data-bs-theme']
                });
            } catch (error) {
                console.error("Error rendering device health history chart:", error);
                chartContainer.removeClass('loading');
                chartContainer.html(
                    '<div class="alert alert-danger">Failed to render chart</div>'
                );
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            console.error("Failed to load device health history data:", textStatus, errorThrown);
            chartContainer.removeClass('loading');
            chartContainer.html(
                '<div class="alert alert-danger">Failed to load health history data</div>'
            );
        });
    }
});
