export class ChatStateManager {
    constructor(options = {}) {
        if (!options.chatUI || !options.networkManager || !options.messageHandler) {
            console.error('Missing required components:', options);
            throw new Error('ChatUI, NetworkManager, and MessageHandler are required');
        }

        this.chatUI = options.chatUI;
        this.networkManager = options.networkManager;
        this.messageHandler = options.messageHandler;
        this.isProcessing = false;
        this.initialized = false;
        this.messageQueue = [];
        this.processingRetryCount = 0;
        this.maxRetries = 1;
        this.currentPage = 1;
        this.hasMoreHistory = true;
        this.isLoadingHistory = false;
        this.conversationHistory = [];

        // Add conversation tracking
        this.conversationContext = {
            lastUserMessage: null,
            lastAIMessage: null,
            conversationUuid: null
        };

        this.conversationState = {
            uuid: null,
            lastUserMessage: null,
            lastAIMessage: null,
            messageCount: 0
        };

        debug.log('ChatStateManager initialized with:', {
            chatUI: !!this.chatUI,
            networkManager: !!this.networkManager
        });

        // Initialize chat immediately
        this._initializeChat().catch(error => {
            console.error('Failed to initialize chat:', error);
            this.chatUI.showError('Failed to initialize chat. Please refresh the page.');
        });
    }

    async _initializeChat() {
        if (this.initialized) {
            debug.log('Chat already initialized');
            return;
        }

        try {
            debug.log('Initializing chat...');
            this.chatUI.setLoading(true);

            const history = await this.networkManager.loadHistory();
            
            if (history.messages && Array.isArray(history.messages)) {
                debug.log(`Loading ${history.messages.length} messages from history`);
                const processedMessages = this.messageHandler.processMessages(history.messages);
                this.conversationHistory = processedMessages;
                // Ensure each message has the correct is_ai flag when loading
                this.chatUI.loadMessages(this.conversationHistory.map(msg => ({
                    ...msg,
                    is_ai: Boolean(msg.is_ai)
                })));
            }

            // Load conversation context if available
            if (history.conversation_context) {
                this.conversationContext = history.conversation_context;
            }

            this.initialized = true;
            debug.log('Chat initialization complete');

        } catch (error) {
            console.error('Chat initialization error:', error);
            this.chatUI.showError('Failed to load chat history');
            throw error;
        } finally {
            this.chatUI.setLoading(false);
        }
    }

    async sendMessage(message) {
        if (!message?.trim()) {
            debug.log('Empty message, ignoring');
            return;
        }

        // Check if message is about health or status to force a refresh
        const isStatusQuery = /health|score|status|current|now/i.test(message);
        
        // Show appropriate thought process
        if (isStatusQuery) {
            this.showThoughtProcess([
                "Initializing conversation...",
                "Refreshing current device metrics...",
                "Loading context and memories...",
                "Processing request..."
            ]);
        } else {
            this.showThoughtProcess([
                "Initializing conversation...",
                "Loading context and memories...",
                "Processing request..."
            ]);
        }

        if (this.isProcessing) {
            debug.log('Message processing in progress, queueing message:', message);
            this.messageQueue.push(message);
            return;
        }

        try {
            this.isProcessing = true;
            this.chatUI.setLoading(true);
            
            // Update thought process based on message content
            if (isStatusQuery) {
                this.updateThoughtProcess("Fetching real-time data and updating context...");
            } else {
                this.updateThoughtProcess("Analyzing input and retrieving relevant context...");
            }
            
            // Add user message to history first
            const userMessage = {
                content: message,
                is_ai: false,
                timestamp: Date.now()
            };
            this.conversationHistory.push(userMessage);
            this.chatUI.appendMessage(message, false);
            this.chatUI.clearInput();
            
            // Show typing indicator before AI response
            this.chatUI.showTypingIndicator();
            
            // Update conversation context
            this.conversationContext.lastUserMessage = message;

            // Update thought process
            this.updateThoughtProcess("Generating response...");
            
            // Send message with conversation history and context
            // Include flag for status queries to force refresh on backend
            const response = await this.networkManager.sendMessage(message, {
                conversationHistory: this.conversationHistory,
                conversationContext: this.conversationState,
                forceRefresh: isStatusQuery
            });
            
            // Hide typing indicator
            this.chatUI.hideTypingIndicator();
            
            if (response.response) {
                // Update thought process with completion
                this.updateThoughtProcess("Processing complete!");
                setTimeout(() => this.hideThoughtProcess(), 1000);

                debug.log('Received response:', response);
                await new Promise(resolve => setTimeout(resolve, 300));
                const processedResponse = this.messageHandler.processAIResponse(response);
                
                // Add AI response to history with token usage
                this.conversationHistory.push({
                    content: processedResponse.content,
                    is_ai: true,
                    timestamp: Date.now(),
                    token_usage: response.token_usage,
                    wegcoin_cost: response.wegcoin_cost
                });
                
                // Append message with token info
                this.chatUI.appendMessage(
                    processedResponse.content, 
                    true, 
                    Date.now(), 
                    response.token_usage,
                    response.wegcoin_cost
                );

                // Update conversation context with AI response
                this.conversationContext.lastAIMessage = response.response;
                this.conversationContext.conversationUuid = response.conversation_uuid;

                if (response.conversation_context) {
                    this.conversationState = {
                        ...this.conversationState,
                        uuid: response.conversation_uuid,
                        lastUserMessage: response.conversation_context.lastUserMessage,
                        lastAIMessage: response.conversation_context.lastAIMessage,
                        messageCount: this.conversationState.messageCount + 2
                    };
                }
            } else {
                this.updateThoughtProcess("Error: Empty response received");
                setTimeout(() => this.hideThoughtProcess(), 2000);
                console.warn('Empty response received');
                this.chatUI.showError('Received empty response from server');
            }
            
            this.processingRetryCount = 0; // Reset retry count on success

        } catch (error) {
            this.updateThoughtProcess("Error occurred during processing");
            setTimeout(() => this.hideThoughtProcess(), 2000);
            this.chatUI.hideTypingIndicator();
            console.error('Message sending error:', error);
            this.chatUI.showError('Failed to send message. Please try again.');
            
            // Handle retries
            this.processingRetryCount++;
            if (this.processingRetryCount < this.maxRetries) {
                debug.log(`Retrying message send (attempt ${this.processingRetryCount + 1}/${this.maxRetries})`);
                await new Promise(resolve => setTimeout(resolve, 1000));
                return this.sendMessage(message);
            }

        } finally {
            this.isProcessing = false;
            this.chatUI.setLoading(false);

            // Process any queued messages
            if (this.messageQueue.length > 0) {
                const nextMessage = this.messageQueue.shift();
                debug.log('Processing queued message:', nextMessage);
                await this.sendMessage(nextMessage);
            }
        }
    }

    showThoughtProcess(steps) {
        const thoughtProcess = document.getElementById('thoughtProcess');
        if (thoughtProcess) {
            thoughtProcess.classList.remove('d-none');
            this.updateThoughtProcess(steps[0]);
            let stepIndex = 1;
            
            this.thoughtInterval = setInterval(() => {
                if (stepIndex < steps.length) {
                    this.updateThoughtProcess(steps[stepIndex]);
                    stepIndex++;
                } else {
                    clearInterval(this.thoughtInterval);
                }
            }, 1500);
        }
    }

    updateThoughtProcess(text) {
        const thoughtContent = document.querySelector('.thought-content');
        if (thoughtContent) {
            thoughtContent.textContent = `> ${text}`;
        }
    }

    hideThoughtProcess() {
        const thoughtProcess = document.getElementById('thoughtProcess');
        if (thoughtProcess) {
            thoughtProcess.classList.add('d-none');
        }
        if (this.thoughtInterval) {
            clearInterval(this.thoughtInterval);
        }
    }

    async refreshChat() {
        debug.log('Refreshing chat...');
        this.initialized = false;
        await this._initializeChat();
    }

    async loadMoreHistory() {
        if (!this.initialized || this.isLoadingHistory || !this.hasMoreHistory) {
            return;
        }

        try {
            this.isLoadingHistory = true;
            this.chatUI.setLoading(true);

            const nextPage = this.currentPage + 1;
            debug.log(`Loading history page ${nextPage}`);

            const history = await this.networkManager.loadHistoryPage(nextPage);
            
            if (history.messages?.length) {
                const processedMessages = this.messageHandler.processMessages(history.messages);
                processedMessages.forEach(msg => {
                    this.chatUI.prependMessage(msg.content, msg.is_ai, msg.timestamp);
                });
                
                this.currentPage = nextPage;
                this.hasMoreHistory = history.has_more;
            } else {
                this.hasMoreHistory = false;
            }

        } catch (error) {
            console.error('Error loading more history:', error);
            this.chatUI.showError('Failed to load more messages');
        } finally {
            this.isLoadingHistory = false;
            this.chatUI.setLoading(false);
        }
    }

    destroy() {
        debug.log('Destroying ChatStateManager');
        this.messageQueue = [];
        this.isProcessing = false;
        this.initialized = false;
        this.processingRetryCount = 0;
        this.hideThoughtProcess();
        if (this.thoughtInterval) {
            clearInterval(this.thoughtInterval);
        }
    }

    getState() {
        return {
            initialized: this.initialized,
            isProcessing: this.isProcessing,
            queueLength: this.messageQueue.length,
            retryCount: this.processingRetryCount,
            currentPage: this.currentPage,
            hasMoreHistory: this.hasMoreHistory,
            isLoadingHistory: this.isLoadingHistory
        };
    }
}