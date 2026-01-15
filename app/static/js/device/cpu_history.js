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

    if ($("#cpu-load-history").length) {
        // Skip if container is hidden or has no dimensions
        const chartContainer = $("#cpu-load-history");
        if (chartContainer[0].offsetParent === null) {
            chartContainer.html('<div class="text-muted small text-center">Chart unavailable</div>');
            return;
        }

        $.get('/widgets/device/' + window.device_uuid + '/cpu_history', function (response) {
            try {
                // Split response into timestamps and values
                const timestamps = response.map(data => data[0] / 1000); // Convert milliseconds to seconds
                const values = response.map(data => data[1]);

                const data = [timestamps, values];

                // Get theme-aware colors
                const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
                let chartColors = getThemeColors(currentTheme);

                // Calculate available height dynamically
                const containerHeight = $("#cpu-load-history").parent().height();
                const availableHeight = Math.max(200, containerHeight - 20); // Subtract padding, minimum 200px

                // Guard against zero or very small widths (mobile/hidden containers)
                let containerWidth = $("#cpu-load-history").width();
                if (containerWidth < 50) {
                    containerWidth = 320; // Safe default fallback
                }

                // uPlot configuration
                const opts = {
                    // title: "CPU Load History",
                    id: "cpu-load-history",
                    width: containerWidth,
                    height: availableHeight,
                    scales: {
                        x: { time: true },
                        y: { range: [0, 100] },
                    },
                    series: [
                        { label: "Time" },
                        {
                            label: "CPU Load",
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
                            values: (u, vals) => vals.map(v => `${v.toFixed(0)}%`),
                            label: "CPU Load (%)",
                        },
                    ],
                };

                // Create uPlot instance
                const uplot = new uPlot(opts, data, document.querySelector("#cpu-load-history"));

                $(window).on("resize", function () {
                    // Only resize if container is visible and has reasonable width
                    if ($("#cpu-load-history")[0].offsetParent !== null) {
                        const newWidth = $("#cpu-load-history").width();
                        if (newWidth >= 50) {
                            const newContainerHeight = $("#cpu-load-history").parent().height();
                            const newAvailableHeight = Math.max(200, newContainerHeight - 20);
                            uplot.setSize({
                                width: newWidth,
                                height: newAvailableHeight,
                            });
                        }
                    }
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
                console.error("Error rendering CPU load history chart:", error);
                $("#cpu-load-history").html(
                    '<div class="alert alert-danger">Failed to render chart</div>'
                );
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            console.error("Failed to load CPU history data:", textStatus, errorThrown);
            $("#cpu-load-history").html(
                '<div class="alert alert-danger">Failed to load CPU history data</div>'
            );
        });
    }
});
