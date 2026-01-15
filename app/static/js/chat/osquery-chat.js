// Filepath: static/js/chat/osquery-chat.js
// Specialized chat interface for osquery functionality

class OSQueryChat {
    constructor(options = {}) {
        this.deviceUuid = options.deviceUuid;
        this.container = options.container;
        this.form = options.form;
        this.input = options.input || this.form.querySelector('input[type="text"]');
        this.submitButton = options.submitButton || this.form.querySelector('button[type="submit"]');
        this.messageContainer = options.messageContainer || this.container.querySelector('.chat-messages');
        this.csrfToken = document.querySelector('input[name="csrf_token"]').value;
        
        this.conversationUuid = options.conversationUuid || null;
        this.pendingMessages = new Map(); // Map of message IDs to pending message elements
        this.pollInterval = options.pollInterval || 2000; // Poll every 2 seconds
        
        this._setupEventListeners();
        this._loadHistory();
    }
    
    _setupEventListeners() {
        // Handle form submission
        this.form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            const message = this.input.value.trim();
            if (!message) return;
            
            try {
                await this.sendMessage(message);
                this.input.value = '';
            } catch (error) {
                console.error('Error sending message:', error);
                this._showError('Failed to send message. Please try again.');
            }
        });
    }
    
    async sendMessage(message) {
        // Add user message to UI
        const userMessageElement = this._createMessageElement(message, 'user');
        this.messageContainer.appendChild(userMessageElement);
        this._scrollToBottom();
        
        // Create a pending message element
        const pendingMessageElement = this._createMessageElement('Processing your request...', 'ai', true);
        this.messageContainer.appendChild(pendingMessageElement);
        this._scrollToBottom();
        
        try {
            // Send message to server
            const response = await fetch(`/ai/device/${this.deviceUuid}/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    message: message,
                    conversation_uuid: this.conversationUuid
                })
            });
            
            const data = await response.json();
            
            // Update conversation UUID if needed
            if (data.conversation_uuid) {
                this.conversationUuid = data.conversation_uuid;
            }
            
            // If the response is immediate, update the pending message
            if (!data.processing) {
                pendingMessageElement.innerHTML = data.response;
                pendingMessageElement.classList.remove('pending');
                return;
            }
            
            // If processing, store the pending message element and start polling
            const messageId = data.message_id;
            this.pendingMessages.set(messageId, pendingMessageElement);
            
            // Start polling for this message
            this._pollForResponse(messageId);
            
        } catch (error) {
            console.error('Error sending message:', error);
            pendingMessageElement.innerHTML = 'Error processing request. Please try again.';
            pendingMessageElement.classList.remove('pending');
            pendingMessageElement.classList.add('error');
        }
    }
    
    async _pollForResponse(messageId) {
        const pendingElement = this.pendingMessages.get(messageId);
        if (!pendingElement) return;
        
        try {
            const response = await fetch(`/ai/device/${this.deviceUuid}/chat/response/${messageId}`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });
            
            const data = await response.json();
            
            // If response is ready, update the UI
            if (data.status === 'complete') {
                pendingElement.innerHTML = data.response;
                pendingElement.classList.remove('pending');
                this.pendingMessages.delete(messageId);
                this._scrollToBottom();
                return;
            }
            
            // If still pending, continue polling
            setTimeout(() => this._pollForResponse(messageId), this.pollInterval);
            
        } catch (error) {
            console.error('Error polling for response:', error);
            pendingElement.innerHTML = 'Error retrieving response. Please try again.';
            pendingElement.classList.remove('pending');
            pendingElement.classList.add('error');
            this.pendingMessages.delete(messageId);
        }
    }
    
    async _loadHistory() {
        try {
            // Load chat history if conversation UUID exists
            if (!this.conversationUuid) return;
            
            const response = await fetch(`/ai/device/${this.deviceUuid}/chat/history/1`, {
                method: 'GET',
                headers: {
                    'X-CSRFToken': this.csrfToken
                }
            });
            
            const data = await response.json();
            
            if (data.messages && data.messages.length > 0) {
                // Clear existing messages
                this.messageContainer.innerHTML = '';
                
                // Add messages to UI
                data.messages.forEach(msg => {
                    const element = this._createMessageElement(
                        msg.content, 
                        msg.is_ai ? 'ai' : 'user',
                        false,
                        msg.is_formatted
                    );
                    this.messageContainer.appendChild(element);
                });
                
                this._scrollToBottom();
            }
            
        } catch (error) {
            console.error('Error loading chat history:', error);
            this._showError('Failed to load chat history.');
        }
    }
    
    _createMessageElement(content, type, isPending = false, isFormatted = false) {
        const element = document.createElement('div');
        element.className = `chat-message ${type}-message`;
        
        if (isPending) {
            element.classList.add('pending');
            element.innerHTML = `<div class="message-content"><div class="loading-indicator"></div>${content}</div>`;
        } else if (isFormatted) {
            element.innerHTML = `<div class="message-content">${content}</div>`;
        } else {
            element.innerHTML = `<div class="message-content">${this._escapeHtml(content)}</div>`;
        }
        
        return element;
    }
    
    _escapeHtml(html) {
        const div = document.createElement('div');
        div.textContent = html;
        return div.innerHTML;
    }
    
    _scrollToBottom() {
        this.messageContainer.scrollTop = this.messageContainer.scrollHeight;
    }
    
    _showError(message) {
        const errorElement = document.createElement('div');
        errorElement.className = 'chat-error';
        errorElement.textContent = message;
        
        this.messageContainer.appendChild(errorElement);
        this._scrollToBottom();
        
        // Remove error after 5 seconds
        setTimeout(() => {
            errorElement.remove();
        }, 5000);
    }
}

// Export the class
export { OSQueryChat };
