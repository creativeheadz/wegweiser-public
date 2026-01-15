$(function () {
    "use strict";

    if ($("#tenant-health-history").length) {
        // Add loading state
        const chartContainer = $("#tenant-health-history");
        chartContainer.addClass('loading');

        $.get('/tenant/' + window.tenant_uuid + '/health_history', function (response) {
            try {
                // Remove loading state
                chartContainer.removeClass('loading');

                // Map the response data to extract timestamps and values
                const timestamps = response.map(data => new Date(data.x).getTime() / 1000); // Convert to seconds
                const values = response.map(data => data.y);

                const data = [timestamps, values];

                // Function to get theme-specific colors
                function getThemeColors() {
                    const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';

                    switch (theme) {
                        case 'dark':
                            return {
                                stroke: "#55DFFC",
                                fill: "rgba(79, 123, 255, 0.2)",
                                gridStroke: "rgba(255, 255, 255, 0.1)",
                                textColor: "#FFFFFF",
                                axisStroke: "rgba(255, 255, 255, 0.7)"
                            };
                        default:  // light theme
                            return {
                                stroke: "#ff0080",
                                fill: "rgba(255, 0, 128, 0.2)",
                                gridStroke: "rgba(0, 0, 0, 0.15)",
                                textColor: "#1A1D21",
                                axisStroke: "rgba(0, 0, 0, 0.7)"
                            };
                    }
                }

                // Get initial colors based on theme
                const colors = getThemeColors();

                // Calculate optimal chart dimensions
                function getChartDimensions() {
                    const containerWidth = chartContainer.width();
                    const containerHeight = chartContainer.height();

                    // Use container height if available, otherwise calculate based on width
                    let height = containerHeight > 0
                        ? containerHeight
                        : Math.max(220, Math.min(260, containerWidth * 0.6));

                    return {
                        width: containerWidth,
                        height: height
                    };
                }

                const dimensions = getChartDimensions();

                // uPlot configuration
                const opts = {
                    //title: "Tenant Health Score",
                    id: "tenant-health-history",
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
                            stroke: colors.stroke,
                            width: 2,
                            fill: colors.fill,
                        },
                    ],
                    axes: [
                        {
                            grid: {
                                stroke: colors.gridStroke,
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
                                stroke: colors.gridStroke,
                                dash: [4, 4],
                            },
                            stroke: colors.axisStroke,
                            values: (u, vals) => vals.map(v => `${v.toFixed(0)}`),
                            label: "Health Score",
                        },
                    ],
                };

                // Create uPlot instance
                const uplot = new uPlot(opts, data, document.querySelector("#tenant-health-history"));

                // Handle responsive resizing with debouncing
                let resizeTimeout;
                $(window).on("resize", function () {
                    clearTimeout(resizeTimeout);
                    resizeTimeout = setTimeout(function() {
                        const newDimensions = getChartDimensions();
                        uplot.setSize({
                            width: newDimensions.width,
                            height: newDimensions.height,
                        });
                    }, 150); // Debounce resize events
                });

                // Watch for theme changes
                const observer = new MutationObserver(function(mutations) {
                    for (const mutation of mutations) {
                        if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
                            // Get new colors based on updated theme
                            const newColors = getThemeColors();

                            // Update chart colors
                            uplot.series[1].stroke = newColors.stroke;
                            uplot.series[1].fill = newColors.fill;

                            // Update grid colors
                            uplot.axes[0].grid.stroke = newColors.gridStroke;
                            uplot.axes[1].grid.stroke = newColors.gridStroke;

                            // Update axis label colors
                            uplot.axes[0].stroke = newColors.axisStroke;
                            uplot.axes[1].stroke = newColors.axisStroke;

                            // Redraw the chart
                            uplot.redraw();
                        }
                    }
                });

                observer.observe(document.documentElement, {
                    attributes: true,
                    attributeFilter: ['data-bs-theme']
                });
            } catch (error) {
                console.error("Error rendering tenant health history chart:", error);
                chartContainer.removeClass('loading');
                chartContainer.html(
                    '<div class="alert alert-danger">Failed to render chart</div>'
                );
            }
        }).fail(function () {
            console.error("Failed to load tenant health history data.");
            chartContainer.removeClass('loading');
            chartContainer.html(
                '<div class="alert alert-danger">Failed to load health history data</div>'
            );
        });
    }
});
