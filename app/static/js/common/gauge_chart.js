// Shared GaugeChart class for system gauges and health score

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
        this.currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        this.options = {
            size: 220,  // Reduced from 370 to 220
            lineWidth: 12,  // Slightly reduced from 15
            title: options.title || '',
            startColor: '#9333EA',    // Purple
            endColor: '#EC4899',      // Pink
            fontFamily: getBaseFontFamily(),
            letterSpacing: '0.5px',
            backgroundColor: 'rgba(147, 51, 234, 0.1)', // Light purple background
            ...options
        };
        this.setup();

        // Watch for theme changes
        this.observer = new MutationObserver(this.handleThemeChange.bind(this));
        this.observer.observe(document.documentElement, {
            attributes: true,
            attributeFilter: ['data-bs-theme']
        });
    }

    setup() {
        this.canvas = document.createElement('canvas');
        this.canvas.width = this.options.size;
        this.canvas.height = this.options.size;
        this.element.appendChild(this.canvas);
        this.ctx = this.canvas.getContext('2d');

        // Create gradient with theme-aware colors
        this.updateThemeColors();
    }

    // Handle theme change
    handleThemeChange(mutations) {
        for (const mutation of mutations) {
            if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
                this.currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
                this.updateThemeColors();
                this.draw(this.lastValue, this.lastUpdatedTime);
            }
        }
    }

    // Update colors based on current theme
    updateThemeColors() {
        const ctx = this.ctx;
        const size = this.options.size;

        // Theme-specific colors
        switch (this.currentTheme) {
            case 'dark':
                this.textColor = '#FFFFFF';
                this.titleColor = '#CDD5E0';
                this.timeColor = '#8896AB';
                this.backgroundFill = 'rgba(79, 123, 255, 0.15)';
                this.options.startColor = '#4F7BFF';  // Blue
                this.options.endColor = '#55DFFC';    // Cyan
                break;
            default:  // light theme
                this.textColor = '#1A1D21';
                this.titleColor = '#5B6B86';
                this.timeColor = '#8896AB';
                this.backgroundFill = 'rgba(147, 51, 234, 0.1)';
                this.options.startColor = '#9333EA';  // Purple
                this.options.endColor = '#EC4899';    // Pink
                break;
        }

        // Re-create gradient with new colors
        this.gradient = ctx.createLinearGradient(
            0, size / 2,
            size, size / 2
        );
        this.gradient.addColorStop(0, this.options.startColor);
        this.gradient.addColorStop(1, this.options.endColor);
    }

    draw(value, lastUpdated) {
        const ctx = this.ctx;
        const size = this.options.size;
        const centerX = size / 2;
        const centerY = size / 2;
        const radius = (size * 0.35);  // Adjusted for better proportion

        // Save value and timestamp for theme change updates
        this.lastValue = value;
        this.lastUpdatedTime = lastUpdated;

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
        ctx.strokeStyle = this.backgroundFill || this.options.backgroundColor;
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
        ctx.font = `${cssVarPx('--font-size-2xl')} ${this.options.fontFamily}`;
        ctx.fillStyle = this.textColor || '#000';
        ctx.fillText(`${Math.round(percentage)}%`, centerX, centerY);

        // Draw title below
        ctx.font = `${cssVarPx('--font-size-base')} ${this.options.fontFamily}`;
        ctx.fillStyle = this.titleColor || '#666';
        ctx.fillText(this.options.title, centerX, centerY + 30);

        // Draw last updated timestamp using the smallest canonical size
        if (lastUpdated) {
            const date = new Date(lastUpdated * 1000);
            const formattedDate = date.toLocaleString();
            ctx.font = `${cssVarPx('--font-size-xs')} ${this.options.fontFamily}`;
            ctx.fillStyle = this.timeColor || '#999';
            ctx.textAlign = 'center';
            ctx.fillText(`Last updated: ${formattedDate}`, centerX, size - 8);
        }

        // Apply letter spacing (simulation since Canvas doesn't support it directly)
        ctx.letterSpacing = this.options.letterSpacing;
    }

    update(value, lastUpdated) {
        requestAnimationFrame(() => this.draw(value, lastUpdated));
    }

    // Cleanup method to disconnect observer when needed
    destroy() {
        if (this.observer) {
            this.observer.disconnect();
        }
    }
}
