document.addEventListener("DOMContentLoaded", function () {
    if (!window.tenant_uuid) return;

    // Function to get theme-specific colors
    function getThemeColors() {
        const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';

        switch (theme) {
            case 'dark':
                return {
                    stroke: "#7928ca",
                    fill: "rgba(121, 40, 202, 0.2)",
                    gridStroke: "rgba(255, 255, 255, 0.1)",
                    axisStroke: "rgba(255, 255, 255, 0.7)"
                };
            default:  // light theme
                return {
                    stroke: "#7928ca",
                    fill: "rgba(121, 40, 202, 0.2)",
                    gridStroke: "rgba(0, 0, 0, 0.15)",
                    axisStroke: "rgba(0, 0, 0, 0.7)"
                };
        }
    }

    // Get colors based on current theme
    const colors = getThemeColors();

    fetch('/tenant/' + window.tenant_uuid + '/org_health_history')
        .then(r => r.json())
        .then(data => {
            const points = (data || []).map(p => ({
                x: new Date(p.x).getTime(),
                y: p.y
            }));
            if (!points.length) return;
            const seriesData = [
                points.map(p => p.x / 1000),
                points.map(p => p.y)
            ];
            const opts = {
                width: document.querySelector("#org-health-history").offsetWidth,
                height: 250,
                scales: { x: { time: true }, y: { auto: true } },
                series: [
                    { label: "Time" },
                    {
                        label: "Organisation Health",
                        stroke: colors.stroke,
                        width: 2,
                        fill: colors.fill
                    }
                ],
                axes: [
                    {
                        grid: { stroke: colors.gridStroke, dash: [4, 4] },
                        stroke: colors.axisStroke,
                        values: (u, ts) => ts.map(t =>
                            new Date(t * 1000).toLocaleDateString("en-GB", {
                                day: "2-digit", month: "short"
                            })
                        )
                    },
                    {
                        grid: { stroke: colors.gridStroke, dash: [4, 4] },
                        stroke: colors.axisStroke,
                        values: (u, vals) => vals.map(v => `${v.toFixed(1)}%`)
                    }
                ]
            };
            document.querySelector("#org-health-history").innerHTML = '';
            const uplot = new uPlot(opts, seriesData, document.querySelector("#org-health-history"));

            // Handle responsive resizing
            window.addEventListener("resize", () => {
                const width = document.querySelector("#org-health-history").offsetWidth;
                uplot.setSize({ width, height: 250 });
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
        });
});
