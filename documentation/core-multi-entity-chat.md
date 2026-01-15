# Unified Multi-Entity Chat System Documentation

## Overview

The Unified Chat System provides a centralized, reusable chat interface that can be integrated with any entity type within the application (devices, groups, organizations, tenants). This modular system separates concerns into distinct components that handle UI rendering, network communication, state management, and message processing.

## Architecture Components

### Frontend Components

1. **UnifiedChat** (`unified-chat.js`)
   - Main controller class that initializes and coordinates all chat components
   - Integrates UI, network, state, and message handling
   - Provides a simple configuration API for entity-specific integration

2. **ChatUI** (`ChatUI.js`)
   - Handles rendering of messages, typing indicators, and error states
   - Manages scrolling behavior and message container interactions
   - Controls loading states and user input handling

3. **ChatNetworkManager** (`ChatNetworkManager.js`)
   - Handles all HTTP communication with the backend
   - Manages conversation history loading and message sending
   - Implements error handling and retry logic for network failures

4. **ChatStateManager** (`ChatStateManager.js`)
   - Maintains conversation state and history
   - Manages message queue for sequential processing
   - Controls thought process display and processing states
   - Handles pagination for conversation history

5. **ChatMessageHandler** (`ChatMessageHandler.js`)
   - Processes incoming and outgoing message content
   - Formats messages for display
   - Handles special message types

6. **Verification Utilities** (`version-check.js`)
   - Validates component availability and compatibility
   - Verifies required DOM elements are present
   - Provides debugging tools for component initialization

### Backend Components

1. **AI Blueprint** (`ai_bp`)
   - Defines API routes for chat functionality
   - Handles entity-specific context retrieval
   - Manages conversation persistence

2. **Entity Memory Manager**
   - Maintains conversation context for each entity
   - Retrieves relevant context based on entity type
   - Persists conversation memory between sessions

3. **AI Response Generator**
   - Processes user inputs with entity context
   - Generates contextually appropriate responses
   - Integrates with language models

## Integration Process

### Template Integration

The chat system is integrated into entity views using the `chat_init.html` component:

```html
{% include 'components/chat_init.html' with context 
   entity_type=entity_type,
   entity_uuid=entity.uuid,
   entity_name=entity.name
%}
```

This component imports all necessary JavaScript modules and initializes the chat with entity-specific configuration.

### HTML Structure Requirements

Any page integrating the chat system must include:

1. A chat container: `<div id="chatContainer"></div>`
2. A chat form: `<form id="chatForm"></form>`
3. An input field: `<input type="text" id="messageInput">`
4. Submit button: `<button type="submit">Send</button>`
5. Offcanvas container: `<div id="chatOffcanvas" class="offcanvas"></div>`
6. Thought process display: `<div id="thoughtProcess" class="d-none"></div>`

## Conversation Flow

1. **Initialization**
   - `chat_init.html` loads required modules
   - `UnifiedChat` instance is created with entity configuration
   - ChatStateManager loads conversation history from the backend
   - UI is rendered with existing messages

2. **Message Sending Process**
   - User submits a message through the chat form
   - ChatUI clears input and displays user message
   - ChatStateManager updates conversation context
   - ChatNetworkManager sends message to backend API
   - Thought process indicators are displayed during processing
   - Backend generates response with entity-specific context
   - AI response is processed and displayed in the UI

3. **History Loading**
   - Initial conversation history is loaded on initialization
   - Additional history is loaded on scroll to top of container
   - Pagination is managed by ChatStateManager
   - Messages are prepended to the conversation view

## API Endpoints

1. `/ai/<entity_type>/<entity_uuid>/chat` (POST)
   - Sends user messages and receives AI responses
   - Requires conversation context and user message

2. `/ai/<entity_type>/<entity_uuid>/chat_history` (GET)
   - Retrieves paginated conversation history
   - Optional page parameter for pagination

3. `/ai/<entity_type>/<entity_uuid>/context` (GET)
   - Retrieves entity-specific context for enhancing AI responses

## Configuration Options

The UnifiedChat class accepts the following configuration options:

```javascript
const chatConfig = {
    container: document.getElementById('chatContainer'),
    form: document.getElementById('chatForm'),
    input: document.getElementById('messageInput'),
    thoughtProcess: document.getElementById('thoughtProcess'),
    entityType: 'device',
    entityUuid: 'abc123',
    entityName: 'Sample Device'
};
```

## Special Features

1. **Thought Process Display**
   - Shows AI processing steps to improve user experience
   - Customizable based on message content
   - Animated sequence of processing steps

2. **Context-Aware Responses**
   - Status queries trigger real-time data refresh
   - Entity-specific context is included with each request
   - Historical conversation context is maintained

3. **Error Handling**
   - Automatic retry mechanism for failed requests
   - User-friendly error messages
   - Graceful degradation when components are missing

## Entity-Specific Context

Different entity types provide specialized context to the AI:

1. **Device Context**
   - Device name, UUID, and health score
   - System metrics (CPU, memory, disk usage)
   - Recent alerts and status changes
   - Connected peripherals and network status

2. **Group Context**
   - Group name and member devices
   - Aggregate health metrics
   - Common issues across devices
   - Performance trends

3. **Organization Context**
   - Organization structure
   - Department relationships
   - User permissions and roles
   - Resource allocation

## Extending the System

### Adding New Entity Types

1. Update `getEntityContext` function to handle new entity type
2. Create backend API handlers for the entity type
3. Ensure proper database models for conversation storage
4. Add entity-specific UI elements if needed

### Customizing Chat Behavior

The chat system is highly configurable through extending base classes:

```javascript
class CustomChatUI extends ChatUI {
    constructor(options) {
        super(options);
        // Custom initialization
    }
    
    // Override methods for custom behavior
    appendMessage(content, isAI, timestamp) {
        // Custom message rendering
        super.appendMessage(content, isAI, timestamp);
    }
}
```

## Troubleshooting

Common issues and solutions:

1. **Chat fails to initialize**
   - Check browser console for component verification errors
   - Ensure all required DOM elements are present
   - Verify script loading order in templates

2. **Messages not sending**
   - Check network tab for API errors
   - Verify CSRF token is being included
   - Check entity UUID format

3. **History not loading**
   - Inspect network requests to history endpoint
   - Verify pagination parameters
   - Check database permissions

4. **Chat components undefined**
   - Ensure modules are being properly imported
   - Check for script loading errors
   - Verify ES module support in browser