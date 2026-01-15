// Modern Health Gauge - Unified component for all entity types
// Works with tenant, organisation, group, and device health scores

(function () {
    "use strict";

    function getThemeName() {
        return document.documentElement.getAttribute("data-bs-theme") || "light";
    }

    function getThemeColors() {
        var theme = getThemeName();
        if (theme === "dark") {
            return {
                stroke: "#7c3aed",
                fill: "rgba(124, 58, 237, 0.1)",
                gradient: ["#7c3aed", "#06b6d4"]
            };
        }
        return {
            stroke: "#9333EA",
            fill: "rgba(147, 51, 234, 0.1)",
            gradient: ["#9333EA", "#EC4899"]
        };
    }

    // Initialize a modern health gauge with optional history chart
    function ModernHealthGauge(options) {
        this.entityType = options.entityType;
        this.entityUuid = options.entityUuid;
        this.healthScore = options.healthScore || 0;
        this.historyEndpoint = options.historyEndpoint;
        this.valueElement = document.getElementById("health-score-value-" + this.entityType);
        this.barElement = document.getElementById("health-score-bar-" + this.entityType);
        this.historyContainer = document.getElementById("health-history-" + this.entityType);

        // Initialize gauge display
        this.updateGauge(this.healthScore);

        // Initialize history chart if container exists
        if (this.historyContainer && this.historyEndpoint) {
            this.initHistoryChart();
        }

        // Watch for theme changes
        this.observer = new MutationObserver(this.handleThemeChange.bind(this));
        this.observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-bs-theme']
        });
    }

    ModernHealthGauge.prototype.updateGauge = function (value) {
        if (this.valueElement && this.barElement) {
            this.valueElement.textContent = Math.round(value) + "%";
            this.barElement.style.width = value + "%";
        }
    };

    ModernHealthGauge.prototype.initHistoryChart = function () {
        var self = this;
        
        if (typeof uPlot === "undefined" || typeof getUnifiedThemeColors === "undefined") {
            console.warn("uPlot or theme utilities not loaded");
            return;
        }

        var colors = getUnifiedThemeColors("healthScore");

        fetch(this.historyEndpoint)
            .then(function (r) { return r.ok ? r.json() : []; })
            .then(function (rows) {
                if (!rows || !rows.length) {
                    self.historyContainer.innerHTML = '<div class="text-muted small text-center">No history data available</div>';
                    return;
                }

                // Parse data based on entity type
                var xData, yData;
                if (self.entityType === 'device') {
                    xData = rows.map(function (p) { return new Date(p.x).getTime() / 1000; });
                    yData = rows.map(function (p) { return p.y; });
                } else {
                    xData = rows.map(function (p) { return p[0] / 1000; });
                    yData = rows.map(function (p) { return p[1]; });
                }

                var data = [xData, yData];

                // Guard against zero or very small widths (mobile/hidden containers)
                var containerWidth = self.historyContainer.clientWidth;
                if (containerWidth < 50 || self.historyContainer.offsetParent === null) {
                    self.historyContainer.innerHTML = '<div class="text-muted small text-center">Chart unavailable</div>';
                    return;
                }

                var opts = {
                    width: containerWidth,
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

                self.plot = new uPlot(opts, data, self.historyContainer);

                window.addEventListener("resize", function () {
                    if (self.plot && self.historyContainer && self.historyContainer.offsetParent !== null) {
                        var newWidth = self.historyContainer.clientWidth;
                        if (newWidth >= 50) {
                            self.plot.setSize({ 
                                width: newWidth, 
                                height: 140 
                            });
                        }
                    }
                });
            })
            .catch(function (err) {
                console.error("Failed to load health history:", err);
            });
    };

    ModernHealthGauge.prototype.handleThemeChange = function () {
        // Recreate chart with new theme colors
        if (this.plot && this.historyContainer && this.historyEndpoint) {
            this.plot.destroy();
            this.initHistoryChart();
        }
    };

    ModernHealthGauge.prototype.destroy = function () {
        if (this.observer) {
            this.observer.disconnect();
        }
        if (this.plot) {
            this.plot.destroy();
        }
    };

    // Export to global scope
    window.ModernHealthGauge = ModernHealthGauge;
})();

