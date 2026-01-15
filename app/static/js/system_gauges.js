// static/js/system_gauges.js

// Local helpers to align JS-rendered typography with CSS variables
function getBaseFontFamily() {
    try {
        const fam = window.getComputedStyle(document.body).fontFamily;
        return fam && fam.trim() ? fam : '"Noto Sans", sans-serif';
    } catch (_) {
        return '"Noto Sans", sans-serif';
    }
}
function cssVarPx(varName) {
    const root = document.documentElement;
    const raw = window.getComputedStyle(root).getPropertyValue(varName).trim();
    if (!raw) return '';
    if (raw.endsWith('rem')) {
        const rem = parseFloat(raw);
        const rootPx = parseFloat(window.getComputedStyle(root).fontSize || '16');
        return `${rem * rootPx}px`;
    }
    if (raw.endsWith('px')) return raw;
    if (/^[0-9.]+$/.test(raw)) return `${raw}px`;
    return raw;
}

class GaugeChart {
    constructor(elementId, options = {}) {
        this.element = document.getElementById(elementId);
        this.options = {
            size: 370,
            lineWidth: 15,
            title: options.title || '',
            startColor: '#9333EA',    // Purple
            endColor: '#EC4899',      // Pink
            fontFamily: getBaseFontFamily(),
            letterSpacing: '0.5px',
            backgroundColor: 'rgba(147, 51, 234, 0.1)', // Light purple background
            ...options
        };
        this.setup();
    }

    setup() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.options.size;
        this.canvas.height = this.options.size;
        this.element.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        // Create gradient
        this.gradient = this.ctx.createLinearGradient(
            0, this.options.size / 2,
            this.options.size, this.options.size / 2
        );
        this.gradient.addColorStop(0, this.options.startColor);
        this.gradient.addColorStop(1, this.options.endColor);
    }

    draw(value) {
        const ctx = this.ctx;
        const size = this.options.size;
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = (size * 0.35);  // Adjusted for better proportion
        
        // Convert value to percentage if needed
        const percentage = Math.min(Math.max(0, value), 100);
        
        // Calculate angles 
        const startAngle = -Math.PI / 2;  // Start at top
        const endAngle = (2 * Math.PI * (percentage / 100)) - Math.PI / 2;

        // Clear canvas
        ctx.clearRect(0, 0, size, size);

        // Draw background circle
        ctx.beginPath();
        ctx.arc(centerX, centerY, radius, 0, 2 * Math.PI);
        ctx.strokeStyle = this.options.backgroundColor;
        ctx.lineWidth = this.options.lineWidth;
        ctx.stroke();

        // Draw value arc
        if (percentage > 0) {
            ctx.beginPath();
            ctx.arc(centerX, centerY, radius, startAngle, endAngle);
            ctx.strokeStyle = this.gradient;
            ctx.lineWidth = this.options.lineWidth;
            ctx.lineCap = 'round';
            ctx.stroke();
        }

        // Draw percentage text
        ctx.textAlign = 'center';
        ctx.textBaseline = 'middle';
        
        // Draw large percentage number
        ctx.font = `${cssVarPx('--font-size-3xl')} ${this.options.fontFamily}`;
        ctx.fillStyle = '#000';
        ctx.fillText(`${Math.round(percentage)}%`, centerX, centerY);

        // Draw title below
        ctx.font = `${cssVarPx('--font-size-md')} ${this.options.fontFamily}`;
        ctx.fillStyle = '#666';
        ctx.fillText(this.options.title, centerX, centerY + 40);

        // Apply letter spacing (simulation since Canvas doesn't support it directly)
        ctx.letterSpacing = this.options.letterSpacing;
    }

    update(value) {
        requestAnimationFrame(() => this.draw(value));
    }
}

// Initialize gauges when document is ready
document.addEventListener('DOMContentLoaded', function() {
    const deviceUuid = window.device_uuid;

    // CPU Load Gauge
    const cpuGauge = new GaugeChart('cpu-load-chart', {
        title: 'CPU Load'
    });

    // Memory Usage Gauge
    const memoryGauge = new GaugeChart('memory-load-chart', {
        title: 'Memory Usage'
    });

    function updateGauges() {
        if (!deviceUuid) {
            console.error('Device UUID not found');
            return;
        }

        // Update CPU Load
        fetch(`/widgets/latest-cpu-data?device_uuid=${deviceUuid}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.load_percentage) {
                    cpuGauge.update(parseInt(data.load_percentage));
                }
            })
            .catch(error => console.error('Error fetching CPU data:', error));

        // Update Memory Usage
        fetch(`/widgets/latest-ram-data?device_uuid=${deviceUuid}`)
            .then(response => response.json())
            .then(data => {
                if (data && data.memory_percentage) {
                    memoryGauge.update(parseFloat(data.memory_percentage));
                }
            })
            .catch(error => console.error('Error fetching memory data:', error));
    }

    // Initial update
    updateGauges();

    // Update every minute
    setInterval(updateGauges, 60000);
});