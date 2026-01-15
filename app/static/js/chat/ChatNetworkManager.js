export class ChatNetworkManager {
    constructor(options = {}) {
        this.entityType = options.entityType || 'device';
        this.entityUuid = options.entityUuid;
        this.conversationUuid = null;
        this.requestTimeout = 30000; // 30 seconds timeout
        this.retryAttempts = 1;
        this.retryDelay = 1000; // 1 second between retries
        this.conversationContext = null;

        if (!this.entityUuid) {
            console.error('Entity UUID is required');
            throw new Error('Entity UUID is required for ChatNetworkManager');
        }

        debug.log('ChatNetworkManager initialized:', {
            entityType: this.entityType,
            entityUuid: this.entityUuid
        });
    }

    async sendMessage(message, options = {}, attempt = 1) {
        try {
            const endpoint = `/ai/${this.entityType}/${this.entityUuid}/chat`;
            
            const payload = {
                message: message,
                conversation_uuid: this.conversationUuid,
                history: options.conversationHistory || [],
                context: options.conversationContext || this.conversationContext
            };

            debug.log('Sending message payload:', {
                endpoint,
                ...payload,
                attempt
            });

            const response = await this.makeRequest(endpoint, {
                method: 'POST',
                body: JSON.stringify(payload)
            });

            if (response.error) {
                // Handle insufficient funds specially
                if (response.error.includes("Insufficient Wegcoins")) {
                    // Dispatch a custom event
                    window.dispatchEvent(new CustomEvent('insufficient-wegcoins'));
                    throw new Error("Insufficient Wegcoins. Please purchase more to continue.");
                }
                throw new Error(response.error);
            }

            if (response.conversation_uuid) {
                this.conversationUuid = response.conversation_uuid;
                debug.log('Updated conversation UUID:', this.conversationUuid);
            }

            if (response.conversation_context) {
                this.conversationContext = response.conversation_context;
            }

            // Dispatch event that response was received (for balance update)
            window.dispatchEvent(new CustomEvent('ai-response-received'));

            return response;

        } catch (error) {
            console.error(`Error sending message (attempt ${attempt}/${this.retryAttempts}):`, error);
            
            // Only retry on network errors, not on server errors
            if (error.name === 'TypeError' || error.message.includes('timeout')) {
                if (attempt < this.retryAttempts) {
                    debug.log(`Retrying message send in ${this.retryDelay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, this.retryDelay));
                    return this.sendMessage(message, options, attempt + 1);
                }
            }
            
            throw error;
        }
    }

    async loadHistory() {
        try {
            const endpoint = `/ai/${this.entityType}/${this.entityUuid}/chat_history`;
            debug.log('Loading chat history from:', endpoint);
            
            const data = await this.makeRequest(endpoint);
            
            if (data.messages?.length > 0) {
                const lastMessage = data.messages[data.messages.length - 1];
                if (lastMessage.conversation_uuid) {
                    this.conversationUuid = lastMessage.conversation_uuid;
                    debug.log('Set conversation UUID from history:', this.conversationUuid);
                }
            }
            
            return data;
        } catch (error) {
            console.error('Error loading chat history:', error);
            throw new Error('Failed to load chat history: ' + error.message);
        }
    }

    async loadHistoryPage(page) {
        try {
            const endpoint = `/ai/${this.entityType}/${this.entityUuid}/chat/history/${page}`;
            debug.log('Loading chat history page:', page);
            
            return await this.makeRequest(endpoint);
            
        } catch (error) {
            console.error('Error loading chat history page:', error);
            throw new Error('Failed to load chat history page: ' + error.message);
        }
    }

    async makeRequest(endpoint, options = {}) {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), this.requestTimeout);

        try {
            const csrfToken = this._getCsrfToken();
            if (!csrfToken) {
                throw new Error('CSRF token not found');
            }

            const response = await fetch(endpoint, {
                ...options,
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': csrfToken,
                    ...options.headers
                },
                signal: controller.signal
            });

            clearTimeout(timeoutId);

            if (!response.ok) {
                const errorData = await response.text();
                console.error('Server error response:', {
                    status: response.status,
                    statusText: response.statusText,
                    data: errorData
                });
                throw new Error(`Server responded with status: ${response.status} (${response.statusText})`);
            }

            const data = await response.json();
            debug.log('Response data:', data);
            return data;

        } catch (error) {
            if (error.name === 'AbortError') {
                throw new Error('Request timed out. Please try again.');
            }
            throw error;
        } finally {
            clearTimeout(timeoutId);
        }
    }

    _getCsrfToken() {
        const tokenElement = document.querySelector('input[name="csrf_token"]');
        if (!tokenElement) {
            console.error('CSRF token element not found');
            return null;
        }
        return tokenElement.value;
    }

    getConversationState() {
        return {
            entityType: this.entityType,
            entityUuid: this.entityUuid,
            conversationUuid: this.conversationUuid,
            hasActiveConversation: !!this.conversationUuid
        };
    }

    resetConversation() {
        debug.log('Resetting conversation state');
        this.conversationUuid = null;
    }

    destroy() {
        debug.log('Destroying ChatNetworkManager');
        this.resetConversation();
    }
}