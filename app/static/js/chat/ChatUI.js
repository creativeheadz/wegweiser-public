// Filepath: static/js/chat/ChatUI.js
import { HtmlSanitizer } from './utils/sanitizer.js';

export class ChatUI {
    constructor(options = {}) {
        // Store references to DOM elements
        this.container = options.container;
        this.form = options.form;
        this.input = options.input;
        this.submitButton = options.submitButton;
        this.thoughtProcess = options.thoughtProcess;

        // Always use a static FontAwesome icon for the submit button
        this.originalButtonContent = '<i class="fa fa-paper-plane"></i>';

        // Set default icons
        this.userIcon = options.userIcon || 'person';
        this.aiIcon = options.aiIcon || 'smart_toy';
        this.isLoading = false;

        // Create typing indicator
        this.typingIndicator = this._createTypingIndicator();
        
        // Initialize HTML sanitizer
        this.sanitizer = new HtmlSanitizer();

        // Using external CSS instead of injecting styles
        debug.log('Using external chat.css for styling');

        debug.log('ChatUI initialized with:', {
            container: !!this.container,
            form: !!this.form,
            input: !!this.input,
            submitButton: !!this.submitButton
        });

        // Validate essential elements
        if (!this.container) {
            console.error('ChatUI: Container element is required');
            throw new Error('Container element is required for ChatUI');
        }

        if (!this.form) {
            console.error('ChatUI: Form element is required');
            throw new Error('Form element is required for ChatUI');
        }

        // If submitButton exists, set its content to the static icon
        if (this.submitButton) {
            this.submitButton.innerHTML = this.originalButtonContent;
        }

        // Ensure submit button and input are not stuck in loading/disabled state
        this.setLoading(false);

        // Set up event listeners
        this._setupEventListeners();

        // Extra: Ensure loading state is reset after all setup
        this.resetLoadingState();
    }

    // Define the _setupEventListeners method
    _setupEventListeners() {
        debug.log('Setting up ChatUI event listeners');

        // No-op if no form is available
        if (!this.form) return;

        // Prevent form submission on enter if needed
        this.form.addEventListener('submit', (e) => {
            e.preventDefault();
            // Form submission is handled by the UnifiedChat class
        });

        // Add input event listeners if needed
        if (this.input) {
            this.input.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    // Let the form handle submission
                } else if (e.key === 'Enter' && e.shiftKey) {
                    // Allow multi-line input with shift+enter
                    e.stopPropagation();
                }
            });
        }
    }

    // Empty method - styles are now in chat.css
    _addAnimationStyles() {
        // Styles are now in chat.css
        // This method is kept for backward compatibility
    }

    _createTypingIndicator() {
        const indicator = document.createElement('div');
        indicator.className = 'typing-indicator chat-message ai';
        indicator.innerHTML = `
            <div class="message-container">
                <div class="avatar-icon">
                    <i class="${this.aiIcon}"></i>
                </div>
                <div class="message-content">
                    <span></span>
                    <span></span>
                    <span></span>
                </div>
            </div>
        `;
        return indicator;
    }

    _createIconElement(isAI) {
        const iconDiv = document.createElement('div');
        iconDiv.className = 'avatar-icon';
        const icon = document.createElement('i');
        icon.className = isAI ? this.aiIcon : this.userIcon;
        iconDiv.appendChild(icon);
        return iconDiv;
    }

    _formatTimestamp(timestamp) {
        // Convert Unix timestamp (seconds) to milliseconds if needed
        const timestampMs = timestamp < 10000000000 ? timestamp * 1000 : timestamp;
        const date = new Date(timestampMs);
        const now = new Date();
        const isToday = date.toDateString() === now.toDateString();

        if (isToday) {
            return date.toLocaleTimeString('default', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        } else {
            return date.toLocaleString('default', {
                day: '2-digit',
                month: 'short',
                year: 'numeric',
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        }
    }

    _createMessageContent(content, isAI, isFormatted = false) {
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const textDiv = document.createElement('div');
        textDiv.className = 'message-text';

        if (isAI && !isFormatted) {
            // Parse markdown to HTML for AI messages and sanitize the result
            const parsedContent = window.marked ? window.marked.parse(content) : content;
            textDiv.innerHTML = this.sanitizer.sanitize(parsedContent);
        } else if (isAI && isFormatted) {
            // Already HTML/markup - sanitize to prevent XSS
            textDiv.innerHTML = this.sanitizer.sanitize(content);
        } else {
            // For user messages, escape HTML and preserve line breaks
            textDiv.textContent = content;
            textDiv.innerHTML = textDiv.innerHTML.replace(/\n/g, '<br>');
        }

        messageContent.appendChild(textDiv);
        return messageContent;
    }

    appendMessage(content, isAI, timestamp = Date.now(), tokenUsage = null, wegcoinCost = null, isFormatted = false) {
        if (!content) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isAI ? 'ai' : 'user'}`;

        const messageContainer = document.createElement('div');
        messageContainer.className = 'message-container';

        messageContainer.appendChild(this._createIconElement(isAI));

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const textDiv = this._createMessageContent(content, isAI, isFormatted);

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time small text-muted';

        // Add token usage and cost if available
        if (isAI && (tokenUsage !== null || wegcoinCost !== null)) {
            let usageText = '';
            if (tokenUsage !== null) {
                usageText += `${tokenUsage} tokens`;
            }
            if (wegcoinCost !== null) {
                usageText += usageText ? ` | ${wegcoinCost} WC` : `${wegcoinCost} WC`;
            }
            if (usageText) {
                const tokenInfoSpan = document.createElement('span');
                tokenInfoSpan.className = 'token-info ms-2';
                tokenInfoSpan.innerHTML = `<i class="fa-solid fa-gauge-high" style="font-size: var(--font-size-sm); vertical-align: middle;"></i> ${usageText}`;
                timeDiv.appendChild(document.createTextNode(this._formatTimestamp(timestamp) + ' '));
                timeDiv.appendChild(tokenInfoSpan);
            } else {
                timeDiv.textContent = this._formatTimestamp(timestamp);
            }
        } else {
            timeDiv.textContent = this._formatTimestamp(timestamp);
        }

        // Add copy buttons to code blocks and safely apply highlighting
        if (isAI && (isFormatted || window.marked)) {
            textDiv.querySelectorAll('pre code').forEach(codeBlock => {
                // Prevent duplicate buttons
                if (!codeBlock.parentElement.querySelector('.copy-button')) {
                    const copyButton = document.createElement('button');
                    copyButton.className = 'copy-button';
                    copyButton.type = 'button';
                    copyButton.title = 'Copy to clipboard';
                    // Use FontAwesome icon
                    copyButton.innerHTML = '<i class="fa fa-copy"></i>';
                    
                    // Store sanitized code content in a data attribute for copying
                    const cleanCode = codeBlock.textContent;
                    copyButton.setAttribute('data-code', cleanCode);
                    
                    const statusSpan = document.createElement('span');
                    statusSpan.className = 'copy-status';
                    statusSpan.textContent = 'Copy';
                    
                    // Make the copy button work with the sanitized content
                    copyButton.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        
                        // Use the global copyCodeToClipboard function defined in chat_component.html
                        if (typeof window.copyCodeToClipboard === 'function') {
                            window.copyCodeToClipboard(copyButton);
                        } else {
                            navigator.clipboard.writeText(copyButton.getAttribute('data-code'));
                            statusSpan.textContent = 'Copied!';
                            setTimeout(() => statusSpan.textContent = 'Copy', 2000);
                        }
                    });
                    
                    // Position the button and status inside the <pre>
                    codeBlock.parentElement.style.position = 'relative';
                    codeBlock.parentElement.appendChild(copyButton);
                    codeBlock.parentElement.appendChild(statusSpan);
                }
            });
            
            // Safely highlight code blocks
            if (window.hljs) {
                textDiv.querySelectorAll('pre code').forEach(block => {
                    try {
                        // Apply highlight.js safely
                        window.hljs.highlightElement(block);
                    } catch (e) {
                        console.error('Error highlighting code block:', e);
                    }
                });
            }
        }

        messageContent.appendChild(textDiv);
        messageContent.appendChild(timeDiv);
        messageContainer.appendChild(messageContent);
        messageDiv.appendChild(messageContainer);

        this.container.appendChild(messageDiv);
        this.scrollToBottom();

        // Trigger animation
        requestAnimationFrame(() => {
            messageDiv.classList.add('visible');
        });
    }

    prependMessage(content, isAI, timestamp = Date.now()) {
        if (!content) return;

        const messageDiv = document.createElement('div');
        messageDiv.className = `chat-message ${isAI ? 'ai' : 'user'}`;

        const messageContainer = document.createElement('div');
        messageContainer.className = 'message-container';

        messageContainer.appendChild(this._createIconElement(isAI));

        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';

        const textDiv = this._createMessageContent(content, isAI);

        const timeDiv = document.createElement('div');
        timeDiv.className = 'message-time small text-muted';
        timeDiv.textContent = this._formatTimestamp(timestamp);

        messageContent.appendChild(textDiv);
        messageContent.appendChild(timeDiv);
        messageContainer.appendChild(messageContent);
        messageDiv.appendChild(messageContainer);

        if (this.container.firstChild) {
            this.container.insertBefore(messageDiv, this.container.firstChild);
        } else {
            this.container.appendChild(messageDiv);
        }

        requestAnimationFrame(() => {
            messageDiv.classList.add('visible');
        });
    }

    scrollToBottom() {
        if (!this.container) return;

        requestAnimationFrame(() => {
            this.container.scrollTop = this.container.scrollHeight;
        });
    }

    setLoading(loading) {
        this.isLoading = loading;

        if (this.submitButton) {
            this.submitButton.disabled = loading;
            // Always show the static icon, never animate or change content
            this.submitButton.innerHTML = this.originalButtonContent;
        }

        if (this.input) {
            this.input.disabled = loading;
            if (!loading) {
                this.input.focus();
            }
        }
    }

    // Add this method to forcibly reset the loading state
    resetLoadingState() {
        this.isLoading = false;
        if (this.submitButton) {
            this.submitButton.disabled = false;
            this.submitButton.innerHTML = this.originalButtonContent;
        }
        if (this.input) {
            this.input.disabled = false;
        }
    }

    clearInput() {
        if (this.input) {
            this.input.value = '';
            this.input.focus();
        }
    }

    showError(message) {
        // Safety check to ensure container exists
        if (!this.container) {
            console.error('Cannot show error: container is not defined');
            return;
        }

        try {
            const errorMessage = document.createElement('div');
            errorMessage.className = 'chat-message error';
            errorMessage.innerHTML = `
                <div class="message-text">
                    <p>${message}</p>
                </div>
            `;
            this.container.appendChild(errorMessage);
            this.scrollToBottom();
        } catch (error) {
            console.error('Failed to display error message:', error);
        }
    }

    loadMessages(messages) {
        if (!Array.isArray(messages)) {
            console.error('Invalid messages format:', messages);
            return;
        }

        this.container.innerHTML = '';
        messages.forEach(msg => {
            const isAI = Boolean(msg.is_ai);
            let isFormatted = msg.is_formatted || false;
            let content = msg.content;

            // Heuristic: If content looks like Markdown (e.g., starts with ``` or contains Markdown headers), parse it
            const looksLikeMarkdown = (
                typeof content === 'string' &&
                (
                    content.trim().startsWith('```') ||
                    content.includes('\n```') ||
                    content.includes('\n#') ||
                    content.includes('\n- ') ||
                    content.includes('**') ||
                    content.includes('* ') ||
                    content.includes('1. ')
                )
            );

            if (isAI && (!isFormatted || looksLikeMarkdown) && window.marked) {
                // For AI messages that might contain markdown, parse and sanitize
                content = window.marked.parse(content);
                // Sanitize the content to prevent XSS when the theme changes
                content = this.sanitizer.sanitize(content, true);
                isFormatted = true;
            } else if (isAI && isFormatted) {
                // For already formatted AI messages, sanitize
                content = this.sanitizer.sanitize(content, true);
            }

            this.appendMessage(content, isAI, msg.timestamp, null, null, isFormatted);
        });

        this.scrollToBottom();
    }

    showTypingIndicator() {
        if (!this.typingIndicator.parentNode) {
            this.container.appendChild(this.typingIndicator);
        }
        this.typingIndicator.style.display = 'block';
        this.scrollToBottom();
    }

    hideTypingIndicator() {
        if (this.typingIndicator.parentNode) {
            this.typingIndicator.style.display = 'none';
        }
    }

    destroy() {
        if (this.container) {
            this.container.innerHTML = '';
        }
        this.hideTypingIndicator();
        // Ensure UI is reset when destroyed
        this.resetLoadingState();
    }
}