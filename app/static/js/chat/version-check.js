/**
 * Chat Component Version Check
 * Verifies that all chat components are loaded and compatible
 */

export function verifyComponents() {
    // Define required components
    const components = [
        { name: 'ChatUI', obj: window.ChatUI },
        { name: 'ChatNetworkManager', obj: window.ChatNetworkManager },
        { name: 'ChatMessageHandler', obj: window.ChatMessageHandler },
        { name: 'ChatStateManager', obj: window.ChatStateManager },
        { name: 'UnifiedChat', obj: window.UnifiedChat }
    ];
    
    // Check if all components are loaded
    let allLoaded = true;
    const missingComponents = [];
    
    components.forEach(component => {
        if (!component.obj) {
            console.error(`${component.name} is not loaded`);
            missingComponents.push(component.name);
            allLoaded = false;
        }
    });
    
    // If not all components are loaded, show an error
    if (!allLoaded) {
        console.error(`Missing components: ${missingComponents.join(', ')}`);
    }
    
    return allLoaded;
}

// Create a function to check DOM elements
export function verifyDomElements(elements) {
    for (const [name, element] of Object.entries(elements)) {
        if (!element) {
            console.error(`Required DOM element not found: ${name}`);
            return false;
        }
    }
    return true;
}

// Add to window object for debugging
window.verifyChatComponents = verifyComponents;
window.verifyChatDomElements = verifyDomElements;
