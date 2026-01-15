// Filepath: static/js/chat/unified-chat.js
import { ChatUI } from './ChatUI.js';
import { ChatNetworkManager } from './ChatNetworkManager.js';
import { ChatMessageHandler } from './ChatMessageHandler.js';
import { ChatStateManager } from './ChatStateManager.js';

class UnifiedChat {
    constructor(options = {}) {
        debug.log('Initializing UnifiedChat with options:', options);
        
        try {
            // Check for required options
            if (!options.entityType || !options.entityUuid) {
                throw new Error('Entity type and UUID are required');
            }
            
            if (!options.container || !(options.container instanceof HTMLElement)) {
                throw new Error('Valid container element is required');
            }
            
            if (!options.form || !(options.form instanceof HTMLElement)) {
                throw new Error('Valid form element is required');
            }
            
            // Store basic properties
            this.entityType = options.entityType;
            this.entityUuid = options.entityUuid;
            this.entityName = options.entityName || 'Entity';
            
            // Initialize chat UI
            this.chatUI = new ChatUI({
                container: options.container,
                form: options.form,
                input: options.input || options.form.querySelector('input[type="text"]'),
                submitButton: options.form.querySelector('button[type="submit"]'),
                thoughtProcess: options.thoughtProcess
            });
            
            // Initialize network manager
            this.networkManager = new ChatNetworkManager({
                baseUrl: `/ai/${this.entityType}/${this.entityUuid}`,
                csrfToken: document.querySelector('input[name="csrf_token"]').value,
                entityType: this.entityType,
                entityUuid: this.entityUuid
            });
            
            // Initialize message handler and state manager
            this.messageHandler = new ChatMessageHandler();
            this.stateManager = new ChatStateManager({
                chatUI: this.chatUI,
                networkManager: this.networkManager,
                messageHandler: this.messageHandler,
                entityType: this.entityType,
                entityUuid: this.entityUuid
            });
            
            // Setup event listeners
            this._setupEventListeners();
            
            debug.log('UnifiedChat initialized successfully');
        } catch (error) {
            console.error('Failed to initialize UnifiedChat:', error);
            if (options.container && options.container.appendChild) {
                try {
                    const errorMessage = document.createElement('div');
                    errorMessage.className = 'alert alert-danger mt-3';
                    errorMessage.textContent = 'Failed to initialize chat. Please refresh the page.';
                    options.container.appendChild(errorMessage);
                } catch (e) {
                    console.error('Could not display error message:', e);
                }
            }
        }
    }

    _setupEventListeners() {
        const form = this.chatUI.form;
        if (!form) return;

        // Handle form submission
        form.addEventListener('submit', async (e) => {
            e.preventDefault();
            
            try {
                const input = this.chatUI.input;
                const message = input?.value?.trim();
                
                if (message) {
                    debug.log('Submitting message:', message);
                    await this.stateManager.sendMessage(message);
                }
            } catch (error) {
                console.error('Error handling form submission:', error);
                this.chatUI.showError('Failed to send message. Please try again.');
            }
        });

        // Handle chat container scroll for history loading
        const container = this.chatUI.container;
        if (container) {
            container.addEventListener('scroll', () => {
                // Load more history when scrolling to top
                if (container.scrollTop === 0) {
                    this.stateManager.loadMoreHistory();
                }
            });
        }

        // Handle window resize
        window.addEventListener('resize', () => {
            requestAnimationFrame(() => {
                this.chatUI.scrollToBottom();
            });
        });
    }

    async _loadEntityContext() {
        if (this.entityType === 'group') {
            const groupContext = await this.networkManager.get('/context');
            this.stateManager.updateContext('group', groupContext);
        }
        // Device context loading can be added here if needed
    }

    getState() {
        return {
            isInitialized: !!this.stateManager?.initialized,
            currentState: this.stateManager?.getState(),
            networkState: this.networkManager?.getConversationState()
        };
    }

    destroy() {
        debug.log('Destroying UnifiedChat instance');
        
        try {
            // Cleanup all components
            if (this.stateManager) {
                this.stateManager.destroy();
            }
            if (this.networkManager) {
                this.networkManager.destroy();
            }
            if (this.chatUI) {
                this.chatUI.destroy();
            }
            if (this.messageHandler) {
                this.messageHandler = null;
            }

            // Remove any global references
            if (window.currentChat === this) {
                window.currentChat = null;
            }

        } catch (error) {
            console.error('Error during UnifiedChat cleanup:', error);
        }
    }
}

// Make UnifiedChat available globally
window.UnifiedChat = UnifiedChat;

export { UnifiedChat };