/**
 * Centralized Highlighting Utility
 * Provides unified code highlighting across all pages
 * Uses the same system as the chat functionality
 */

class HighlightUtility {
    constructor() {
        this.isInitialized = false;
        this.init();
    }

    init() {
        // Wait for hljs to be available
        this.waitForHighlightJS().then(() => {
            this.configureHighlightJS();
            this.setupObservers();
            this.highlightExistingCode();
            this.isInitialized = true;
        });
    }

    async waitForHighlightJS() {
        return new Promise((resolve) => {
            if (window.hljs) {
                resolve();
                return;
            }

            // Check periodically for hljs
            let attempts = 0;
            const maxAttempts = 50; // 5 seconds with 100ms intervals

            const checkInterval = setInterval(() => {
                attempts++;
                if (window.hljs) {
                    clearInterval(checkInterval);
                    debug.log('highlight.js loaded successfully');
                    resolve();
                } else if (attempts >= maxAttempts) {
                    clearInterval(checkInterval);
                    console.warn('highlight.js not found after 5 seconds, code highlighting disabled');
                    resolve();
                }
            }, 100);
        });
    }

    configureHighlightJS() {
        if (!window.hljs) return;

        // Configure highlight.js with the same settings as chat
        window.hljs.configure({
            tabReplace: '    ', // 4 spaces
            ignoreUnescapedHTML: true,
            languages: ['python', 'javascript', 'bash', 'powershell', 'html', 'css', 'sql', 'json', 'yaml', 'xml']
        });
    }

    setupObservers() {
        // Watch for theme changes and re-highlight
        const themeObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.type === 'attributes' && mutation.attributeName === 'data-bs-theme') {
                    // Add a slight delay to allow CSS updates
                    setTimeout(() => this.highlightExistingCode(), 100);
                }
            });
        });

        // Observe theme changes on document element
        const documentElement = document.documentElement;
        if (documentElement) {
            themeObserver.observe(documentElement, {
                attributes: true,
                attributeFilter: ['data-bs-theme']
            });
        }

        // Watch for dynamically added code blocks
        const contentObserver = new MutationObserver((mutations) => {
            mutations.forEach((mutation) => {
                if (mutation.addedNodes.length) {
                    mutation.addedNodes.forEach((node) => {
                        if (node.nodeType === Node.ELEMENT_NODE) {
                            this.highlightCodeInElement(node);
                        }
                    });
                }
            });
        });

        // Observe the entire document for new code blocks
        contentObserver.observe(document.body, {
            childList: true,
            subtree: true
        });
    }

    highlightExistingCode() {
        if (!window.hljs) return;

        // Find all code blocks and highlight them
        const codeBlocks = document.querySelectorAll('pre code, .code-box code, .highlight code');
        codeBlocks.forEach(block => {
            this.highlightCodeBlock(block);
        });
    }

    highlightCodeInElement(element) {
        if (!window.hljs) return;

        // Find code blocks within the given element
        const codeBlocks = element.querySelectorAll('pre code, .code-box code, .highlight code');
        codeBlocks.forEach(block => {
            this.highlightCodeBlock(block);
        });

        // Check if the element itself is a code block
        if (element.matches && element.matches('pre code, .code-box code, .highlight code')) {
            this.highlightCodeBlock(element);
        }
    }

    highlightCodeBlock(codeBlock) {
        if (!window.hljs || !codeBlock) return;

        try {
            // Store original code content before highlighting
            const originalCode = codeBlock.textContent;

            // Remove any existing highlighting
            codeBlock.removeAttribute('data-highlighted');
            codeBlock.className = codeBlock.className.replace(/hljs[^\s]*/g, '').trim();

            // Apply syntax highlighting
            window.hljs.highlightElement(codeBlock);

            // Add copy button if it doesn't exist and this is in a pre tag
            // Skip if the pre element already has a copy button or is marked as having one
            const preElement = codeBlock.closest('pre');
            if (preElement &&
                !preElement.querySelector('.copy-button') &&
                !preElement.classList.contains('has-copy-button') &&
                !preElement.closest('.code-box')?.querySelector('button[data-copy]')) {
                this.addCopyButton(preElement, originalCode);
            }

            // Update existing copy button's data attribute
            const existingCopyButton = preElement?.querySelector('.copy-button, [data-copy="code"]');
            if (existingCopyButton) {
                existingCopyButton.setAttribute('data-copy-text', originalCode);
            }

        } catch (error) {
            console.error('Error highlighting code block:', error);
        }
    }

    addCopyButton(preElement, code) {
        // Create copy button using the centralized copy system
        const copyButton = document.createElement('button');
        copyButton.className = 'copy-button btn btn-sm btn-outline-secondary';
        copyButton.type = 'button';
        copyButton.title = 'Copy to clipboard';
        copyButton.innerHTML = '<i class="fas fa-copy"></i>';

        // Set up for centralized copy utility
        copyButton.setAttribute('data-copy', 'text');
        copyButton.setAttribute('data-copy-text', code);
        copyButton.setAttribute('data-copy-message', 'Code copied to clipboard!');

        // Style the pre element and add the button
        preElement.style.position = 'relative';
        preElement.style.wordWrap = 'break-word';
        preElement.style.whiteSpace = 'pre-wrap';
        preElement.style.overflowWrap = 'break-word';
        preElement.appendChild(copyButton);
    }

    // Public API methods
    static highlightElement(element) {
        if (window.highlightUtility && window.highlightUtility.isInitialized) {
            window.highlightUtility.highlightCodeInElement(element);
        } else {
            // Queue for when utility is ready
            setTimeout(() => HighlightUtility.highlightElement(element), 100);
        }
    }

    static highlightAll() {
        if (window.highlightUtility && window.highlightUtility.isInitialized) {
            window.highlightUtility.highlightExistingCode();
        } else {
            // Queue for when utility is ready
            setTimeout(() => HighlightUtility.highlightAll(), 100);
        }
    }

    static addCodeBlock(container, code, language = '') {
        if (!container) return null;

        // Create code block structure
        const preElement = document.createElement('pre');
        const codeElement = document.createElement('code');

        if (language) {
            codeElement.className = `language-${language}`;
        }

        codeElement.textContent = code;
        preElement.appendChild(codeElement);
        container.appendChild(preElement);

        // Highlight the new code block
        HighlightUtility.highlightElement(preElement);

        return preElement;
    }

    // Enhanced code block creation with styling
    static createStyledCodeBlock(code, language = '', options = {}) {
        const {
            copyable = true,
            className = 'code-box',
            copyMessage = 'Code copied to clipboard!'
        } = options;

        // Create container
        const container = document.createElement('div');
        container.className = className;

        // Create pre and code elements
        const preElement = document.createElement('pre');
        const codeElement = document.createElement('code');

        if (language) {
            codeElement.className = `language-${language}`;
        }

        codeElement.textContent = code;
        preElement.appendChild(codeElement);
        container.appendChild(preElement);

        // Add copy button if requested
        if (copyable) {
            const copyButton = document.createElement('button');
            copyButton.className = 'btn btn-sm btn-outline-secondary mt-2';
            copyButton.type = 'button';
            copyButton.textContent = 'Copy';

            // Set up for centralized copy utility
            copyButton.setAttribute('data-copy', 'text');
            copyButton.setAttribute('data-copy-text', code);
            copyButton.setAttribute('data-copy-message', copyMessage);

            container.appendChild(copyButton);
        }

        // Highlight the code
        HighlightUtility.highlightElement(container);

        return container;
    }
}

// Initialize the highlight utility when the script loads
window.highlightUtility = new HighlightUtility();

// Export for module usage if needed
if (typeof module !== 'undefined' && module.exports) {
    module.exports = HighlightUtility;
}
