/**
 * Centralized Copy Utility
 * Provides unified copy functionality across all pages
 * Prevents duplication and AI-induced omissions during iterations
 */

class CopyUtility {
    constructor() {
        this.init();
    }

    init() {
        // Set up event delegation for copy buttons
        this.setupEventDelegation();

        // Initialize existing copy elements on page load
        document.addEventListener('DOMContentLoaded', () => {
            this.initializeExistingElements();
        });
    }

    setupEventDelegation() {
        // Use event delegation to handle all copy buttons
        document.addEventListener('click', (event) => {
            const copyBtn = event.target.closest('[data-copy]');
            if (copyBtn) {
                event.preventDefault();
                event.stopPropagation();
                this.handleCopyClick(copyBtn);
            }
        });
    }

    initializeExistingElements() {
        // Convert existing copy buttons to use the new system
        this.convertLegacyUUIDButtons();
        this.convertLegacyCodeButtons();
    }

    convertLegacyUUIDButtons() {
        // Convert UUID copy buttons
        const uuidButtons = document.querySelectorAll('#copyUUIDBtn');
        uuidButtons.forEach(btn => {
            const uuidInput = document.querySelector('#groupUUID, #orgUUID, #deviceUUID');
            if (uuidInput) {
                btn.setAttribute('data-copy', 'input');
                btn.setAttribute('data-copy-target', uuidInput.id);
                btn.setAttribute('data-copy-message', 'UUID copied to clipboard!');
            }
        });
    }

    convertLegacyCodeButtons() {
        // Convert code block copy buttons
        const codeButtons = document.querySelectorAll('.code-box button, .btn-outline-secondary');
        codeButtons.forEach(btn => {
            const codeElement = btn.parentElement?.querySelector('code');
            if (codeElement && codeElement.id) {
                btn.setAttribute('data-copy', 'code');
                btn.setAttribute('data-copy-target', codeElement.id);
                btn.setAttribute('data-copy-message', 'Installation command copied to clipboard!');
            }
        });
    }

    async handleCopyClick(button) {
        const copyType = button.getAttribute('data-copy');
        const target = button.getAttribute('data-copy-target');
        const message = button.getAttribute('data-copy-message') || 'Content copied to clipboard!';

        let textToCopy = '';

        try {
            switch (copyType) {
                case 'input':
                    textToCopy = this.getInputValue(target);
                    break;
                case 'code':
                    textToCopy = this.getCodeContent(target);
                    break;
                case 'text':
                    textToCopy = button.getAttribute('data-copy-text') || '';
                    break;
                case 'element':
                    textToCopy = this.getElementContent(target);
                    break;
                default:
                    console.error('Unknown copy type:', copyType);
                    return;
            }

            if (textToCopy) {
                await this.copyToClipboard(textToCopy);
                this.showSuccessToast(message);
                this.updateButtonState(button, 'success');
            } else {
                throw new Error('No content to copy');
            }
        } catch (error) {
            console.error('Copy failed:', error);
            this.showErrorToast('Failed to copy content');
            this.updateButtonState(button, 'error');
        }
    }

    getInputValue(targetId) {
        const input = document.getElementById(targetId);
        return input ? input.value.trim() : '';
    }

    getCodeContent(targetId) {
        const codeElement = document.getElementById(targetId);
        return codeElement ? codeElement.textContent.trim() : '';
    }

    getElementContent(targetId) {
        const element = document.getElementById(targetId);
        return element ? element.textContent.trim() : '';
    }

    async copyToClipboard(text) {
        if (navigator.clipboard && window.isSecureContext) {
            await navigator.clipboard.writeText(text);
        } else {
            // Fallback for older browsers or non-secure contexts
            const textArea = document.createElement('textarea');
            textArea.value = text;
            textArea.style.position = 'fixed';
            textArea.style.left = '-999999px';
            textArea.style.top = '-999999px';
            document.body.appendChild(textArea);
            textArea.focus();
            textArea.select();

            try {
                document.execCommand('copy');
            } finally {
                textArea.remove();
            }
        }
    }

    showSuccessToast(message) {
        // Use the new centralized notification system instead of Bootstrap toasts
        if (window.showNotification) {
            window.showNotification(message, 'success');
        } else {
            // Fallback to console if notification system isn't available
            debug.log('Copy success:', message);
        }
    }

    showErrorToast(message) {
        // Use the new centralized notification system instead of Bootstrap toasts
        if (window.showNotification) {
            window.showNotification(message, 'danger');
        } else {
            // Fallback to console if notification system isn't available
            console.error('Copy error:', message);
        }
    }

    updateButtonState(button, state) {
        const originalText = button.textContent;
        const originalHTML = button.innerHTML;

        if (state === 'success') {
            button.innerHTML = '<i class="fas fa-check me-1"></i>Copied!';
            button.classList.add('btn-success');
            button.disabled = true;

            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.classList.remove('btn-success');
                button.disabled = false;
            }, 2000);
        } else if (state === 'error') {
            button.innerHTML = '<i class="fas fa-times me-1"></i>Error';
            button.classList.add('btn-danger');

            setTimeout(() => {
                button.innerHTML = originalHTML;
                button.classList.remove('btn-danger');
            }, 2000);
        }
    }

    // Public API methods for manual usage
    static copyText(text, message = 'Text copied to clipboard!') {
        return window.copyUtility.copyToClipboard(text).then(() => {
            window.copyUtility.showSuccessToast(message);
        }).catch(error => {
            console.error('Copy failed:', error);
            window.copyUtility.showErrorToast('Failed to copy text');
        });
    }

    static copyElement(elementId, message = 'Content copied to clipboard!') {
        const element = document.getElementById(elementId);
        if (element) {
            const text = element.textContent.trim();
            return CopyUtility.copyText(text, message);
        } else {
            console.error('Element not found:', elementId);
            return Promise.reject(new Error('Element not found'));
        }
    }
}

// Initialize the copy utility when the script loads
window.copyUtility = new CopyUtility();

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = CopyUtility;
}
