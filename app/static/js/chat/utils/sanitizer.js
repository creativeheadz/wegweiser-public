// Filepath: app/static/js/chat/utils/sanitizer.js

/**
 * HTML Sanitizer for safe rendering of code blocks
 * 
 * This sanitizer allows specific HTML tags and attributes
 * needed for code highlighting while preventing XSS attacks
 */

export class HtmlSanitizer {
    constructor(options = {}) {
        this.allowedTags = options.allowedTags || [
            'div', 'span', 'p', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'blockquote', 'pre', 'code',
            'a', 'strong', 'em', 'i', 'b', 'br', 'hr'
        ];

        this.allowedAttributes = options.allowedAttributes || {
            'a': ['href', 'target', 'rel'],
            'code': ['class'],
            'span': ['class', 'style'],
            'div': ['class'],
            'pre': ['class']
        };

        // Additional attributes allowed for highlight.js
        this.highlightJsAttributes = [
            'class', 'data-highlighted', 'tabindex'
        ];
    }

    /**
     * Sanitize HTML string
     * @param {string} html The HTML string to sanitize
     * @param {boolean} allowHighlight Whether to allow highlight.js classes and attributes
     * @returns {string} Sanitized HTML string
     */
    sanitize(html, allowHighlight = true) {
        if (!html) return '';

        // First, escape HTML within code blocks only
        html = this._escapeCodeContent(html);

        // Create a temporary DOM element
        const tempElement = document.createElement('div');
        tempElement.innerHTML = html;

        // Process all nodes recursively
        this._sanitizeNode(tempElement, allowHighlight);

        return tempElement.innerHTML;
    }

    /**
     * Pre-process HTML to escape code block content
     * This prevents highlight.js warnings while preserving syntax highlighting
     */
    _escapeCodeContent(html) {
        // Simple regex to find <code> blocks
        const codeBlockRegex = /<code(?:\s+class="[^"]*")?>([\s\S]*?)<\/code>/gi;

        // Replace each code block with escaped content
        return html.replace(codeBlockRegex, (match, codeContent) => {
            // Only escape content if it contains HTML tags and isn't already escaped
            if (/<[^>]*>/g.test(codeContent) && !codeContent.includes('&lt;')) {
                // Escape < and > but preserve already escaped entities
                const escapedContent = codeContent
                    .replace(/&/g, '&amp;')
                    .replace(/</g, '&lt;')
                    .replace(/>/g, '&gt;')
                    .replace(/&amp;amp;/g, '&amp;')  // Fix double-escaped ampersands
                    .replace(/&amp;lt;/g, '&lt;')    // Fix double-escaped tags
                    .replace(/&amp;gt;/g, '&gt;');

                // Reconstruct the code tag with escaped content
                return match.replace(codeContent, escapedContent);
            }
            return match;
        });
    }

    /**
     * Recursively sanitize a DOM node and its children
     * @param {Node} node The DOM node to sanitize
     * @param {boolean} allowHighlight Whether to allow highlight.js classes and attributes
     */
    _sanitizeNode(node, allowHighlight) {
        // Process all child nodes first (to handle nested elements)
        const childNodes = Array.from(node.childNodes);
        for (const child of childNodes) {
            if (child.nodeType === Node.ELEMENT_NODE) {
                this._sanitizeNode(child, allowHighlight);
            }
        }

        // If this is an element node
        if (node.nodeType === Node.ELEMENT_NODE) {
            const tagName = node.tagName.toLowerCase();

            // Remove node if the tag is not allowed
            if (!this.allowedTags.includes(tagName)) {
                // Convert to text node to preserve content
                const text = document.createTextNode(node.textContent);
                node.parentNode.replaceChild(text, node);
                return;
            }

            // Handle code blocks specially for highlight.js
            const isCodeBlock = (tagName === 'code' || tagName === 'pre' ||
                (tagName === 'span' && node.closest('code')));

            // Remove all attributes first
            const attributes = Array.from(node.attributes);
            for (const attr of attributes) {
                node.removeAttribute(attr.name);
            }

            // Add back allowed attributes
            if (this.allowedAttributes[tagName]) {
                for (const attr of attributes) {
                    if (this.allowedAttributes[tagName].includes(attr.name)) {
                        node.setAttribute(attr.name, attr.value);
                    }
                }
            }

            // Add back highlight.js attributes if allowed
            if (allowHighlight && isCodeBlock) {
                for (const attr of attributes) {
                    if (this.highlightJsAttributes.includes(attr.name)) {
                        node.setAttribute(attr.name, attr.value);
                    } else if (attr.name === 'class' && attr.value.includes('hljs')) {
                        // Special handling for highlight.js classes
                        const classes = attr.value.split(' ').filter(cls =>
                            cls.startsWith('hljs') ||
                            cls === 'language-' ||
                            cls.startsWith('language-')
                        );
                        if (classes.length > 0) {
                            node.setAttribute('class', classes.join(' '));
                        }
                    }
                }
            }
        }
    }
}
