// Compact Gauge Implementation for Unified Metric Cards
// Uses Chart.js doughnut charts for mini gauges

class CompactGauge {
    constructor(canvasId, options = {}) {
        this.canvasId = canvasId;
        this.canvas = document.getElementById(canvasId);
        if (!this.canvas) {
            console.warn(`Canvas ${canvasId} not found`);
            return;
        }

        this.options = {
            label: options.label || '',
            color: options.color || 'rgba(40, 81, 231, 1)', // Primary blue
            maxValue: options.maxValue || 100,
            unit: options.unit || '%',
            ...options
        };

        this.currentValue = 0;
        this.init();
    }

    init() {
        const ctx = this.canvas.getContext('2d');
        
        this.chart = new Chart(ctx, {
            type: 'doughnut',
            data: {
                datasets: [{
                    data: [0, 100],
                    backgroundColor: [
                        this.options.color,
                        'rgba(var(--text-secondary), 0.1)'
                    ],
                    borderWidth: 0,
                    cutout: '75%'
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: true,
                plugins: {
                    legend: {
                        display: false
                    },
                    tooltip: {
                        enabled: false
                    }
                },
                animation: {
                    animateRotate: true,
                    animateScale: false,
                    duration: 750,
                    easing: 'easeInOutQuart'
                }
            },
            plugins: [{
                id: 'centerText',
                afterDraw: (chart) => {
                    const ctx = chart.ctx;
                    const centerX = chart.chartArea.left + (chart.chartArea.right - chart.chartArea.left) / 2;
                    const centerY = chart.chartArea.top + (chart.chartArea.bottom - chart.chartArea.top) / 2;

                    ctx.save();
                    ctx.textAlign = 'center';
                    ctx.textBaseline = 'middle';
                    ctx.fillStyle = getComputedStyle(document.documentElement).getPropertyValue('--text-primary') || '#000';
                    ctx.font = 'bold 18px Inter, sans-serif';
                    ctx.fillText(`${this.currentValue.toFixed(1)}${this.options.unit}`, centerX, centerY);
                    ctx.restore();
                }
            }]
        });
    }

    update(value) {
        if (!this.chart) return;
        
        this.currentValue = Math.min(Math.max(value, 0), this.options.maxValue);
        const percentage = (this.currentValue / this.options.maxValue) * 100;
        
        this.chart.data.datasets[0].data = [percentage, 100 - percentage];
        this.chart.update('active');
    }

    destroy() {
        if (this.chart) {
            this.chart.destroy();
        }
    }
}

// Initialize gauges when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait for Chart.js to be available
    if (typeof Chart === 'undefined') {
        console.warn('Chart.js not loaded, retrying...');
        setTimeout(() => {
            document.dispatchEvent(new Event('DOMContentLoaded'));
        }, 100);
        return;
    }

    // Initialize Health Score Gauge
    if (document.getElementById('healthscoreorg')) {
        const healthScoreElement = document.getElementById('healthscoreorg');
        const healthScore = parseFloat(healthScoreElement.dataset.healthScore) || 0;
        
        window.healthGauge = new CompactGauge('healthscoreorg', {
            label: 'Health',
            color: 'rgba(40, 81, 231, 1)',
            maxValue: 100,
            unit: ''
        });
        
        window.healthGauge.update(healthScore);
        
        // Update badge
        const badge = document.getElementById('health-current-value');
        if (badge) {
            badge.textContent = `${healthScore.toFixed(0)}`;
        }
    }

    // Initialize CPU Gauge
    if (document.getElementById('cpu-load-chart')) {
        window.cpuGauge = new CompactGauge('cpu-load-chart', {
            label: 'CPU',
            color: 'rgba(40, 81, 231, 1)',
            maxValue: 100,
            unit: '%'
        });
    }

    // Initialize Memory Gauge
    if (document.getElementById('memory-load-chart')) {
        window.memoryGauge = new CompactGauge('memory-load-chart', {
            label: 'Memory',
            color: 'rgba(40, 81, 231, 1)',
            maxValue: 100,
            unit: '%'
        });
    }
});

