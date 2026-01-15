document.addEventListener("DOMContentLoaded", function () {
    "use strict";

    // Just map the data to {x: timestamp, y: value}
    function mapRawPoints(data) {
        if (!data || !Array.isArray(data) || data.length === 0) {
            return [];
        }
        return data.map(point => ({
            x: new Date(point.x).getTime(),
            y: point.y
        }));
    }

    // Verify tenant_uuid is available
    if (!window.tenant_uuid) {
        console.error("Missing tenant_uuid variable");
        document.querySelector("#cascading-health-history").innerHTML =
            '<div class="alert alert-danger">Configuration error: Missing tenant ID.</div>';
        return;
    }

    // Show loading indicator
    document.querySelector("#cascading-health-history").innerHTML =
        '<div class="text-center p-3"><i class="fas fa-spinner fa-spin"></i> Loading health history data...</div>';

    // Fetch data for cascading health history
    fetch('/tenant/' + window.tenant_uuid + '/cascading_health_history')
        .then(response => {
            if (!response.ok) throw new Error(`HTTP error! Status: ${response.status}`);
            return response.json();
        })
        .then(data => {
            // Use raw points, no grouping
            const processedData = {
                tenant: mapRawPoints(data.tenant || []),
                organisation: mapRawPoints(data.organisation || []),
                group: mapRawPoints(data.group || [])
            };

            const seriesData = [
                processedData.tenant.map(point => point.x / 1000),
                processedData.tenant.map(point => point.y),
                processedData.organisation.map(point => point.y),
                processedData.group.map(point => point.y)
            ];

            if (seriesData[0].length === 0) {
                document.querySelector("#cascading-health-history").innerHTML =
                    '<div class="alert alert-warning">No health history data available.</div>';
                return;
            }

            const opts = {
                width: document.querySelector("#cascading-health-history").offsetWidth,
                height: 350,
                scales: {
                    x: { time: true },
                    y: { auto: true },
                },
                series: [
                    { label: "Time", value: null },
                    {
                        label: "Tenant",
                        stroke: "#ff0080",
                        width: 2,
                        fill: "rgba(255, 0, 128, 0.2)"
                    },
                    {
                        label: "Organisation",
                        stroke: "#7928ca",
                        width: 2,
                        fill: "rgba(121, 40, 202, 0.2)"
                    },
                    {
                        label: "Group",
                        stroke: "#00f2c3",
                        width: 2,
                        fill: "rgba(0, 242, 195, 0.2)"
                    }
                ],
                axes: [
                    {
                        grid: { stroke: "rgba(0, 0, 0, 0.15)", dash: [4, 4] },
                        values: (u, ts) =>
                            ts.map(t =>
                                new Date(t * 1000).toLocaleDateString("en-GB", {
                                    day: "2-digit",
                                    month: "short",
                                    year: "2-digit"
                                })
                            )
                    },
                    {
                        grid: { stroke: "rgba(0, 0, 0, 0.15)", dash: [4, 4] },
                        values: (u, vals) => vals.map(v => `${v.toFixed(1)}%`)
                    }
                ],
            };

            document.querySelector("#cascading-health-history").innerHTML = '';
            const uplot = new uPlot(opts, seriesData, document.querySelector("#cascading-health-history"));

            window.addEventListener("resize", () => {
                const width = document.querySelector("#cascading-health-history").offsetWidth;
                uplot.setSize({ width, height: 350 });
            });
        })
        .catch(error => {
            console.error("Failed to load cascading health history data:", error);
            document.querySelector("#cascading-health-history").innerHTML =
                '<div class="alert alert-danger">Failed to load health history data: ' + error.message + '</div>';
        });
});
