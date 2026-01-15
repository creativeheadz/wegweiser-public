$(function () {
    "use strict";

    if ($("#group-health-history").length) {
        const chartContainer = $("#group-health-history");

        // Show loading state
        ChartUtils.showChartLoading(chartContainer);

        $.get('/group/' + window.group_uuid + '/health_history', function (response) {
            try {
                // Hide loading state
                ChartUtils.hideChartLoading(chartContainer);

                // Map the response data to extract timestamps and values
                const timestamps = response.map(data => new Date(data.x).getTime() / 1000);
                const values = response.map(data => data.y);
                const data = [timestamps, values];

                // Get theme colors and dimensions using utilities
                const colors = ChartUtils.getChartThemeColors();
                const dimensions = ChartUtils.calculateChartDimensions(chartContainer);

                // Create chart configuration using utility
                const opts = ChartUtils.createHealthScoreChartConfig({
                    id: "group-health-history",
                    title: "Group Health History",
                    width: dimensions.width,
                    height: dimensions.height,
                    colors: colors
                });

                // Create uPlot instance
                const uplot = new uPlot(opts, data, document.querySelector("#group-health-history"));

                // Setup responsive resizing
                const resizeHandler = ChartUtils.createDebouncedResizeHandler(() => {
                    const newDimensions = ChartUtils.calculateChartDimensions(chartContainer);
                    uplot.setSize({
                        width: newDimensions.width,
                        height: newDimensions.height,
                    });
                });
                $(window).on("resize", resizeHandler);

                // Setup theme change observer
                ChartUtils.setupThemeObserver(uplot, ChartUtils.getChartThemeColors);
            } catch (error) {
                console.error("Error rendering group health history chart:", error);
                ChartUtils.showChartError(chartContainer, "Failed to render chart");
            }
        }).fail(function (jqXHR, textStatus, errorThrown) {
            console.error("Failed to load group health history data:", textStatus, errorThrown);
            ChartUtils.showChartError(chartContainer, "Failed to load health history data");
        });
    }
});
