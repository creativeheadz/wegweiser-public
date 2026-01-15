// Unified device health score + CPU + memory gauges and history charts

(function () {
    "use strict";

    function getThemeName() {
        return document.documentElement.getAttribute("data-bs-theme") || "light";
    }

    function getGaugeColors() {
        var theme = getThemeName();
        if (theme === "dark") {
            return { startColor: "#7c3aed", endColor: "#06b6d4" };
        }
        return { startColor: "#9333EA", endColor: "#EC4899" };
    }

    function DeviceHealthOverview(deviceUuid) {
        this.deviceUuid = deviceUuid;
        this.gauges = {};
        this.plots = {};
        this.initGauges();
        this.initCharts();
        this.startGaugePolling();
    }

    DeviceHealthOverview.prototype.initGauges = function () {
        // Modern gauges are now HTML-based, no GaugeChart needed
        // Just store references to the elements
        this.gauges.healthValue = document.getElementById("health-score-value");
        this.gauges.healthBar = document.getElementById("health-score-bar");
        this.gauges.cpuValue = document.getElementById("cpu-load-value");
        this.gauges.cpuBar = document.getElementById("cpu-load-bar");
        this.gauges.memoryValue = document.getElementById("memory-usage-value");
        this.gauges.memoryBar = document.getElementById("memory-usage-bar");
    };

    DeviceHealthOverview.prototype.startGaugePolling = function () {
        var self = this;
        if (!this.deviceUuid) {
            return;
        }
        function update() {
            self.updateGauges();
        }
        update();
        this.gaugeInterval = window.setInterval(update, 60000);
    };

    DeviceHealthOverview.prototype.updateGauges = function () {
        var self = this;
        var uuid = this.deviceUuid;
        if (!uuid) {
            return;
        }

        fetch("/widgets/latest-cpu-data?device_uuid=" + uuid)
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (cpu) {
                if (!cpu || !self.gauges.cpuValue || !self.gauges.cpuBar) {
                    return;
                }
                if (cpu.load_percentage == null) {
                    return;
                }
                var val = parseFloat(cpu.load_percentage);
                self.gauges.cpuValue.textContent = val.toFixed(1) + "%";
                self.gauges.cpuBar.style.width = val + "%";
            })
            .catch(function () { /* ignore */ });

        fetch("/widgets/latest-ram-data?device_uuid=" + uuid)
            .then(function (r) { return r.ok ? r.json() : null; })
            .then(function (ram) {
                if (!ram || !self.gauges.memoryValue || !self.gauges.memoryBar) {
                    return;
                }
                if (ram.memory_percentage == null) {
                    return;
                }
                var val = parseFloat(ram.memory_percentage);
                self.gauges.memoryValue.textContent = val.toFixed(1) + "%";
                self.gauges.memoryBar.style.width = val + "%";
            })
            .catch(function () { /* ignore */ });
    };

    DeviceHealthOverview.prototype.initCharts = function () {
        if (typeof uPlot === "undefined" || typeof getUnifiedThemeColors === "undefined" || typeof getUnifiedAxisConfig === "undefined") {
            return;
        }

        if (document.getElementById("device-health-history")) {
            this.plots.health = this.createHistoryChart({
                containerId: "device-health-history",
                endpoint: "/devices/device/" + this.deviceUuid + "/health_history",
                metricType: "healthScore",
                seriesLabel: "Health Score",
                yLabel: "Health Score",
                parse: function (rows) {
                    return {
                        x: rows.map(function (p) { return new Date(p.x).getTime() / 1000; }),
                        y: rows.map(function (p) { return p.y; })
                    };
                }
            });
        }

        if (document.getElementById("cpu-load-history")) {
            this.plots.cpu = this.createHistoryChart({
                containerId: "cpu-load-history",
                endpoint: "/widgets/device/" + this.deviceUuid + "/cpu_history",
                metricType: "cpu",
                seriesLabel: "CPU Load",
                yLabel: "CPU Load (%)",
                parse: function (rows) {
                    return {
                        x: rows.map(function (p) { return p[0] / 1000; }),
                        y: rows.map(function (p) { return p[1]; })
                    };
                }
            });
        }

        if (document.getElementById("memory-load-history")) {
            this.plots.memory = this.createHistoryChart({
                containerId: "memory-load-history",
                endpoint: "/widgets/device/" + this.deviceUuid + "/ram_history",
                metricType: "memory",
                seriesLabel: "Memory Usage",
                yLabel: "Memory Usage (%)",
                parse: function (rows) {
                    return {
                        x: rows.map(function (p) { return p[0] / 1000; }),
                        y: rows.map(function (p) { return p[1]; })
                    };
                }
            });
        }
    };

    DeviceHealthOverview.prototype.createHistoryChart = function (cfg) {
        var container = document.getElementById(cfg.containerId);
        if (!container) {
            return null;
        }

        container.classList.add("loading");

        var colors = getUnifiedThemeColors(cfg.metricType);

        return fetch(cfg.endpoint)
            .then(function (r) { return r.ok ? r.json() : []; })
            .then(function (rows) {
                if (!rows || !rows.length) {
                    container.classList.remove("loading");
                    container.innerHTML = '<div class="text-muted small text-center">No data available yet</div>';
                    return null;
                }

                var parsed = cfg.parse(rows);
                var data = [parsed.x, parsed.y];

                function computeSize() {
                    var rect = container.getBoundingClientRect();
                    var w = rect.width || (container.parentElement ? container.parentElement.clientWidth : 320);

                    // Guard against zero or very small widths (mobile/hidden containers)
                    if (w < 50) {
                        w = 320; // Safe default fallback
                    }

                    // Prefer the actual container height so the chart fills the card body
                    var containerHeight = rect.height || (container.parentElement ? container.parentElement.clientHeight : 0);
                    var h;

                    if (containerHeight && containerHeight > 0) {
                        h = containerHeight;
                    } else {
                        var ratio = typeof cfg.heightRatio === "number" ? cfg.heightRatio : 0.6;
                        var minH = cfg.minHeight || 220;
                        var maxH = cfg.maxHeight || 260;
                        h = Math.max(minH, Math.min(maxH, Math.round(w * ratio)));
                    }

                    return { width: w, height: h };
                }

                // Skip chart creation if container is hidden or has no parent
                if (container.offsetParent === null) {
                    container.classList.remove("loading");
                    container.innerHTML = '<div class="text-muted small text-center">Chart unavailable</div>';
                    return null;
                }

                var size = computeSize();

                var timeAxis = getUnifiedAxisConfig(colors, cfg.yLabel, true);
                var valueAxis = getUnifiedAxisConfig(colors, cfg.yLabel, false);

                var opts = {
                    id: cfg.containerId,
                    width: size.width,
                    height: size.height,
                    scales: {
                        x: { time: true },
                        y: { range: [0, 100] }
                    },
                    series: [
                        { label: "Time" },
                        {
                            label: cfg.seriesLabel,
                            stroke: colors.stroke,
                            width: 2,
                            fill: colors.fill
                        }
                    ],
                    axes: [timeAxis, valueAxis]
                };

                var plot = new uPlot(opts, data, container);

                window.addEventListener("resize", function () {
                    // Only resize if container is visible and has reasonable width
                    if (container.offsetParent !== null) {
                        var newSize = computeSize();
                        if (newSize.width >= 50) {
                            plot.setSize(newSize);
                        }
                    }
                });

                container.classList.remove("loading");
                return plot;
            })
            .catch(function (err) {
                console.error("Failed to load", cfg.metricType, "history", err);
                container.classList.remove("loading");
                container.innerHTML = '<div class="alert alert-danger py-2 mb-0">Failed to load data</div>';
                return null;
            });
    };

    function init() {
        if (!window.device_uuid) {
            return;
        }
        window.deviceHealthOverview = new DeviceHealthOverview(window.device_uuid);
    }

    if (document.readyState === "loading") {
        document.addEventListener("DOMContentLoaded", init);
    } else {
        init();
    }
})();

