/**
 * AI Insights Handler
 * Manages interaction with hardware component data points to provide AI insights
 */

class AIInsights {
    constructor() {
        this.insightDefinitions = {
            // System OS and Kernel
            'os_platform': {
                label: 'Operating System',
                template: 'Please explain this system identifier and what it tells us as a backend architect',
                icon: 'fas fa-question-circle'
            },
            // BIOS/UEFI
            'bios_vendor': {
                label: 'BIOS Vendor',
                template: 'Explain this BIOS vendor and version - what does it tell us about the system firmware',
                icon: 'fas fa-question-circle'
            },
            'bios_version': {
                label: 'BIOS Version',
                template: 'Explain what this BIOS version indicates about system capabilities and compatibility',
                icon: 'fas fa-question-circle'
            },
            // CPU
            'cpu_name': {
                label: 'Processor',
                template: 'Explain this processor and its characteristics for system performance',
                icon: 'fas fa-question-circle'
            },
            'cpu_cores': {
                label: 'CPU Cores',
                template: 'Explain the significance of this CPU core count for system performance',
                icon: 'fas fa-question-circle'
            },
            // Memory
            'memory_total': {
                label: 'Total Memory',
                template: 'Explain the implications of this amount of total memory for system workloads',
                icon: 'fas fa-question-circle'
            },
            'memory_used': {
                label: 'Memory Usage',
                template: 'Analyze this memory usage pattern and what it indicates about system health',
                icon: 'fas fa-question-circle'
            },
            // GPU
            'gpu_model': {
                label: 'Graphics Card',
                template: 'Explain this GPU and its capabilities for system performance',
                icon: 'fas fa-question-circle'
            },
            // Battery
            'battery_health': {
                label: 'Battery Health',
                template: 'Explain what this battery health status means and what actions might be needed',
                icon: 'fas fa-question-circle'
            },
            // Storage
            'drive_usage': {
                label: 'Storage Usage',
                template: 'Analyze this storage usage level and what it might indicate about system health',
                icon: 'fas fa-question-circle'
            },
            // Network
            'network_interface': {
                label: 'Network Interface',
                template: 'Explain this network interface configuration and its role in system connectivity',
                icon: 'fas fa-question-circle'
            }
        };

        this.initialized = false;
        this.init();
    }

    init() {
        // Prevent multiple initializations
        if (this.initialized) return;
        this.initialized = true;

        // Only attach listeners once, when DOM is ready
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => this.attachInsightListeners(), { once: true });
        } else {
            this.attachInsightListeners();
        }
    }

    /**
     * Attach click listeners to all AI insight icons (only once per icon)
     */
    attachInsightListeners() {
        const insightIcons = document.querySelectorAll('[data-ai-insight]');
        insightIcons.forEach(icon => {
            // Check if already has listener attached
            if (icon.dataset.listenerAttached) return;
            
            const handler = (e) => {
                e.preventDefault();
                e.stopPropagation();
                this.handleInsightClick(icon);
            };
            
            icon.addEventListener('click', handler);
            icon.dataset.listenerAttached = 'true';
            icon.style.cursor = 'pointer';
            icon.title = 'Click for AI insights';
        });
    }

    /**
     * Handle click on an AI insight icon
     */
    async handleInsightClick(iconElement) {
        const insightKey = iconElement.dataset.aiInsight;
        const insightValue = iconElement.dataset.insightValue;

        if (!insightValue) {
            console.warn('No insight value found for:', insightKey);
            return;
        }

        // Open the chat offcanvas
        const chatOffcanvas = document.getElementById('chatOffcanvas');
        if (!chatOffcanvas) {
            console.warn('Chat offcanvas not found');
            return;
        }

        // Show the offcanvas
        const offcanvasInstance = new bootstrap.Offcanvas(chatOffcanvas);
        offcanvasInstance.show();

        // Wait for offcanvas to fully show
        await new Promise(resolve => {
            chatOffcanvas.addEventListener('shown.bs.offcanvas', resolve, { once: true });
        });

        // Small delay to ensure chat is ready
        await new Promise(resolve => setTimeout(resolve, 100));

        // Send the insight request
        this.sendInsightMessage(insightKey, insightValue);
    }

    /**
     * Send an insight request to the chat
     */
    sendInsightMessage(insightKey, insightValue) {
        if (!window.currentChat) {
            console.warn('Chat not initialized yet, retrying...');
            setTimeout(() => this.sendInsightMessage(insightKey, insightValue), 500);
            return;
        }

        const insightDef = this.insightDefinitions[insightKey] || {};
        const template = insightDef.template || 'Please explain this system component';

        // Format the message with the insight value
        const message = `Explain: ${insightValue}\n\n${template}`;

        // Get the message input
        const messageInput = document.getElementById('messageInput');
        if (!messageInput) {
            console.warn('Message input not found');
            return;
        }

        // Only set value once (don't double-set)
        if (messageInput.value !== message) {
            messageInput.value = message;
        }

        messageInput.focus();

        // Wait a tick then submit
        setTimeout(() => {
            const chatForm = document.getElementById('chatForm');
            if (chatForm) {
                const event = new Event('submit', { bubbles: true });
                chatForm.dispatchEvent(event);
            }
        }, 50);
    }

    /**
     * Create an AI insight icon for a data point
     */
    createInsightIcon(insightKey, value) {
        const insightDef = this.insightDefinitions[insightKey] || {};
        const icon = document.createElement('span');
        icon.className = 'ai-insight-icon';
        icon.setAttribute('data-ai-insight', insightKey);
        icon.setAttribute('data-insight-value', String(value));
        icon.innerHTML = `<i class="fas fa-wand-magic-sparkles"></i>`;
        icon.title = `AI insights: ${insightDef.label || 'Get insights'}`;
        
        return icon;
    }
}

// Initialize when script loads (only if not already initialized)
if (!window.aiInsights) {
    window.aiInsights = new AIInsights();
}

// Make it globally available for template-based initialization
window.AIInsights = AIInsights;
