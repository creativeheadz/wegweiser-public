// ChatMessageHandler.js
export class ChatMessageHandler {
    constructor(options = {}) {
        this.maxRetries = options.maxRetries || 1;
        this.retryCount = 0;
        this.lastMessage = null;

        this.options = {
            maxMessageLength: options.maxMessageLength || 2000,
            messageTypes: {
                AI: 'ai',
                USER: 'user',
                SYSTEM: 'system',
                ERROR: 'error'
            }
        };
    }

    validateMessage(message) {
        if (!message || typeof message !== 'string') {
            throw new Error('Invalid message format');
        }

        if (message.length > this.options.maxMessageLength) {
            throw new Error(`Message exceeds maximum length of ${this.options.maxMessageLength} characters`);
        }

        return message.trim();
    }

    processMessage(message, type) {
        try {
            const validatedMessage = this.validateMessage(message);
            this.lastMessage = validatedMessage;

            return {
                content: validatedMessage,
                type: type,
                timestamp: Date.now(),
                metadata: this._generateMessageMetadata(type)
            };
        } catch (error) {
            console.error('Message processing error:', error);
            throw error;
        }
    }

    processMessages(messages) {
        return messages.map(message => {
            const isAI = Boolean(message.is_ai);
            const content = message.content;
            return {
                content: content,
                is_ai: isAI,
                timestamp: message.timestamp,
                message_uuid: message.message_uuid,
                conversation_uuid: message.conversation_uuid,
                is_formatted: message.is_formatted || false
            };
        });
    }

    handleError(error) {
        const errorMessage = {
            type: this.options.messageTypes.ERROR,
            content: error.message || 'An error occurred while processing your message.',
            canRetry: this.retryCount < this.maxRetries,
            timestamp: Date.now()
        };

        if (errorMessage.canRetry && this.lastMessage) {
            return {
                ...errorMessage,
                retryFunction: () => {
                    this.retryCount++;
                    return this.lastMessage;
                }
            };
        }

        return errorMessage;
    }

    processAIResponse(response) {
        try {
            this.retryCount = 0;

            if (typeof response === 'string') {
                return this._processTextResponse(response);
            } else if (typeof response === 'object') {
                return this._processStructuredResponse(response);
            }

            if (response && response.thoughts) {
                debug.debug('Hidden AI Thoughts:', response.thoughts);
            }

        } catch (error) {
            console.error('AI response processing error:', error);
            throw error;
        }
    }

    _processTextResponse(response) {
        return {
            content: this._formatResponse(response),
            type: this.options.messageTypes.AI,
            timestamp: Date.now()
        };
    }

    _processStructuredResponse(response) {
        const content = response.is_formatted ?
            response.response :
            this._formatResponse(response.response || response.message || '');

        return {
            content,
            type: this.options.messageTypes.AI,
            timestamp: Date.now(),
            tokenUsage: response.token_usage || null,
            wegcoinCost: response.wegcoin_cost || null,
            metadata: response.metadata || {},
            isFormatted: response.is_formatted || false
        };
    }

    _cleanResponse(response) {
        const memoryIndex = response.indexOf("**MEMORY:**");
        if (memoryIndex !== -1) {
            response = response.substring(0, memoryIndex);
        }
        return response.trim();
    }

    _formatResponse(response) {
        // Return the response as-is without additional formatting
        return response;
    }

    _generateMessageMetadata(type) {
        const metadata = {
            messageId: this._generateMessageId(),
            timestamp: Date.now()
        };

        if (type === this.options.messageTypes.USER) {
            metadata.deviceInfo = this._getDeviceInfo();
        }

        return metadata;
    }

    _generateMessageId() {
        return 'msg_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    }

    _getDeviceInfo() {
        return {
            userAgent: navigator.userAgent,
            language: navigator.language,
            platform: navigator.platform,
            screenSize: `${window.screen.width}x${window.screen.height}`
        };
    }
}