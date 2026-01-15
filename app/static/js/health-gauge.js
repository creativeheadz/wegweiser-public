/**
 * Enhanced Health Gauge for Wegweiser
 * Creates beautiful, animated gauges using uPlot
 */

document.addEventListener('DOMContentLoaded', function() {
    // Initialize health gauges - support both data attributes
    const healthElements = document.querySelectorAll('[data-health-score], .health-gauge-container');
    healthElements.forEach(element => {
        const score = parseInt(element.getAttribute('data-health-score') || element.getAttribute('data-value')) || 0;
        const label = element.getAttribute('data-label') || '';
        createHealthGauge(element, score, label);
    });
});

/**
 * Creates a health gauge using uPlot
 * @param {HTMLElement} element - The container element
 * @param {number} score - Health score (0-100)
 * @param {string} label - Optional label for the gauge
 */
function createHealthGauge(element, score, label) {
    // Clear previous content
    element.innerHTML = '';
    
    // Set container size
    const size = parseInt(element.getAttribute('data-size')) || 160;
    element.style.width = `${size}px`;
    element.style.height = `${size}px`;
    
    // Create value display
    const valueDisplay = document.createElement('div');
    valueDisplay.className = 'health-gauge-value';
    
    // Create value element with animation
    const valueEl = document.createElement('div');
    valueEl.className = 'gauge-number';
    valueEl.textContent = '0';
    valueEl.setAttribute('data-target', score);
    valueDisplay.appendChild(valueEl);
    
    // Add % sign
    const percentSign = document.createElement('div');
    percentSign.className = 'gauge-percent';
    percentSign.textContent = '%';
    valueDisplay.appendChild(percentSign);
    
    // Add label if provided
    const labelText = label || element.getAttribute('data-label') || 'Health Score';
    const labelEl = document.createElement('div');
    labelEl.className = 'gauge-label';
    labelEl.textContent = labelText;
    valueDisplay.appendChild(labelEl);
    
    // Create canvas for uPlot
    const canvas = document.createElement('canvas');
    canvas.className = 'gauge-canvas';
    
    // Add elements to container
    element.appendChild(valueDisplay);
    element.appendChild(canvas);
    
    // Get color based on score and theme
    const color = getGaugeColor(score);
    
    // Create and render the gauge
    createUplotGauge(canvas, score, color);
    
    // Animate the value display
    animateGaugeValue(valueEl, score);
}

/**
 * Gets the appropriate color for the gauge based on score and theme
 * @param {number} score - The health score (0-100)
 * @returns {string} - CSS color value
 */
function getGaugeColor(score) {
    // Check if we're in monochrome theme
    const theme = document.documentElement.getAttribute('data-bs-theme');
    
    if (theme === 'monochrome') {
        // In monochrome theme, use white with varying opacity
        return `rgba(255, 255, 255, ${0.3 + (score/100) * 0.7})`;
    }
    
    // Default color scheme based on score
    if (score >= 75) {
        return 'rgb(6, 166, 169)';  // Success/Teal
    } else if (score >= 50) {
        return 'rgb(255, 171, 0)';  // Warning/Amber
    } else if (score >= 25) {
        return 'rgb(255, 149, 0)';  // Orange
    } else {
        return 'rgb(232, 60, 75)';  // Danger/Red
    }
}

/**
 * Creates and renders the uPlot gauge
 * @param {HTMLElement} canvas - Canvas element to render to
 * @param {number} score - Health score value
 * @param {string} color - Color for the gauge
 */
function createUplotGauge(canvas, score, color) {
    const size = parseInt(canvas.parentElement.style.width) || 160;
    const width = size;
    const height = size;
    const thickness = parseInt(canvas.parentElement.getAttribute('data-thickness')) || 10;
    
    // Set canvas dimensions (handle high DPI screens)
    const pixelRatio = window.devicePixelRatio || 1;
    canvas.width = width * pixelRatio;
    canvas.height = height * pixelRatio;
    canvas.style.width = `${width}px`;
    canvas.style.height = `${height}px`;
    
    // Create data series for the gauge
    const data = [
        [0, 1], // x values (angles)
        [0, score/100]  // y values (normalized score)
    ];
    
    // Configure gauge options
    const opts = {
        width,
        height,
        scales: {
            x: {
                time: false,
                range: [0, 1]
            },
            y: {
                range: [0, 1]
            }
        },
        series: [
            {},
            {
                stroke: color,
                width: thickness,
                fill: "transparent",
                paths: getArcPath.bind(null, size, thickness)
            }
        ],
        axes: [],
        legend: {
            show: false
        }
    };
    
    // Create plot
    new uPlot(opts, data, canvas);
}

/**
 * Returns a path function for drawing the gauge arc
 * @param {number} size - Size of the gauge
 * @param {number} thickness - Thickness of the gauge arc
 */
function getArcPath(size, thickness, self, seriesIdx, idx0, idx1, extendGap, buildClip) {
    const r = (size - thickness) / 2;
    const cx = size / 2;
    const cy = size / 2;
    
    // Get data points
    const value = self.data[1][1];
    
    // Draw arc (270deg to value% + 270deg)
    const startAngle = -Math.PI / 2;
    const endAngle = startAngle + (Math.PI * 2 * value);
    
    // Create SVG path
    let path = "";
    
    path += `M ${cx + r * Math.cos(startAngle)},${cy + r * Math.sin(startAngle)} `;
    
    // Add the arc
    const largeArcFlag = value > 0.5 ? 1 : 0;
    path += `A ${r},${r} 0 ${largeArcFlag} 1 ${cx + r * Math.cos(endAngle)},${cy + r * Math.sin(endAngle)} `;
    
    return path;
}

/**
 * Animates the gauge value from 0 to target
 * @param {HTMLElement} element - Element to animate
 * @param {number} target - Target value
 */
function animateGaugeValue(element, target) {
    const duration = 1500;
    const startTime = performance.now();
    let frameId;
    
    const updateValue = (timestamp) => {
        const elapsed = timestamp - startTime;
        const progress = Math.min(elapsed / duration, 1);
        
        // Apply easing function for smoother animation
        const eased = 1 - Math.pow(1 - progress, 3);
        
        // Update the number display
        const current = Math.round(eased * target);
        element.textContent = current;
        
        // Continue animation until done
        if (progress < 1) {
            frameId = requestAnimationFrame(updateValue);
        }
    };
    
    // Start animation
    frameId = requestAnimationFrame(updateValue);
}
    ];
    
    const opts = {
        width: 140,
        height: 140,
        padding: [25, 0, 0, 0],
        scales: {
            x: {
                time: false,
            },
            y: {
                range: [0, 100]
            }
        },
        axes: [
            {}, // x-axis (hidden)
            {
                show: false
            } // y-axis (hidden)
        ],
        series: [
            {}, // x-values (not used)
            {
                stroke: color,
                width: 10,
                dash: [10, 0], // Solid line
                points: {
                    show: false
                },
                spanGaps: false,
                paths: drawGauge
            }
        ]
    };
    
    new uPlot(opts, data, chartElement);
    
    // Custom gauge drawing function for uPlot
    function drawGauge(u, sidx, i0, i1) {
        const s = u.series[sidx];
        const xScale = u.scales.x;
        const yScale = u.scales.y;
        
        const cx = u.bbox.width / 2;
        const cy = u.bbox.height / 2;
        const r = Math.min(cx, cy) * 0.8;
        
        // Draw background arc
        const backgroundPath = new Path2D();
        backgroundPath.arc(cx, cy, r, Math.PI, 2 * Math.PI, false);
        
        const ctx = u.ctx;
        ctx.save();
        
        ctx.lineWidth = 10;
        ctx.lineCap = "round";
        ctx.strokeStyle = "rgba(200, 200, 200, 0.2)";
        ctx.stroke(backgroundPath);
        
        // Calculate angle based on score (0-100% → π to 2π)
        const angle = Math.PI + (score / 100) * Math.PI;
        
        // Draw value arc
        const valuePath = new Path2D();
        valuePath.arc(cx, cy, r, Math.PI, angle, false);
        
        ctx.strokeStyle = color;
        ctx.stroke(valuePath);
        
        ctx.restore();
        
        return null;
    }
}