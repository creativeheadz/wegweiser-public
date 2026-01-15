document.addEventListener('DOMContentLoaded', function () {
    const historyContainer = document.getElementById('organisation-health-history');

    if (!historyContainer) {
        console.error("Health history container not found!");
        return;
    }

    const orgUuid = historyContainer.dataset.orgUuid;

    if (!orgUuid) {
        console.error("Invalid organisation UUID!");
        return;
    }

    // Initialize modern health history chart
    initOrgHealthHistory(orgUuid);

    function initOrgHealthHistory(orgUuid) {
        if (typeof uPlot === "undefined") {
            console.error("uPlot not loaded");
            return;
        }

        const container = document.getElementById("organisation-health-history");
        if (!container) return;

        function getThemeColors() {
            const theme = document.documentElement.getAttribute('data-bs-theme') || 'light';
            if (theme === 'dark') {
                return {
                    stroke: '#7c3aed',
                    fill: 'rgba(124, 58, 237, 0.1)'
                };
            }
            return {
                stroke: '#9333EA',
                fill: 'rgba(147, 51, 234, 0.1)'
            };
        }

        const colors = getThemeColors();

        fetch(`/organisations/${orgUuid}/health_history`)
            .then(r => r.ok ? r.json() : [])
            .then(rows => {
                if (!rows || !rows.length) {
                    container.innerHTML = '<div class="text-muted small text-center">No history data available</div>';
                    return;
                }

                const xData = rows.map(p => p[0] / 1000);
                const yData = rows.map(p => p[1]);
                const data = [xData, yData];

                const opts = {
                    width: container.clientWidth,
                    height: 140,
                    scales: {
                        x: { time: true },
                        y: { range: [0, 100] }
                    },
                    series: [
                        { label: "Time" },
                        {
                            label: "Health Score",
                            stroke: colors.stroke,
                            width: 2,
                            fill: colors.fill
                        }
                    ],
                    axes: [
                        {
                            stroke: colors.stroke,
                            grid: { stroke: colors.stroke, width: 1 / devicePixelRatio },
                            ticks: { stroke: colors.stroke, width: 1 / devicePixelRatio }
                        },
                        {
                            stroke: colors.stroke,
                            grid: { stroke: colors.stroke, width: 1 / devicePixelRatio },
                            ticks: { stroke: colors.stroke, width: 1 / devicePixelRatio }
                        }
                    ]
                };

                const plot = new uPlot(opts, data, container);

                window.addEventListener("resize", function () {
                    plot.setSize({ width: container.clientWidth, height: 140 });
            })
            .catch(err => console.error("Failed to load health history:", err));
    }
});
