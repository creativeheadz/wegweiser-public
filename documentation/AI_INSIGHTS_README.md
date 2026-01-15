# AI Insights Feature for Hardware Components

## Overview

The AI Insights feature adds interactive sparkle icons next to key hardware component data points in the device management interface. Users can click these icons to get AI-powered explanations of what each component means from a backend architect's perspective.

## Features

### What's Included

1. **Interactive Icons**: Small sparkle icons (`✨`) appear next to important hardware metrics
2. **One-Click Insights**: Click any icon to automatically open the AI chat and inject a contextual question
3. **Smart Templates**: Each component type has a customized explanation template
4. **Visual Feedback**: Hover effects and animations make icons discoverable

### Supported Components

The AI insights system covers the following hardware categories:

#### System
- **Operating System**: System identifier and kernel information (e.g., Linux kernel versions, WSL2 setup)
- **BIOS Vendor**: Firmware vendor information (e.g., American Megatrends Inc.)
- **BIOS Version**: Specific firmware version and capabilities

#### Processors & Memory
- **Processor**: CPU model and capabilities
- **CPU Cores**: Core/thread counts and performance implications
- **Total Memory**: RAM capacity and workload implications
- **Memory Usage**: Current usage patterns and system health

#### Storage & Graphics
- **Graphics Card**: GPU model and capabilities
- **Storage Usage**: Drive utilization levels and system health
- **Battery Health**: Battery status and maintenance indicators

#### Network
- **Network Interface**: Network configuration and connectivity details

## How It Works

### User Flow

1. User views device details page
2. User notices small **sparkle icons** (✨) next to key metrics
3. User hovers over icon → tooltip appears: "Click for AI insights"
4. User clicks icon → Chat panel opens automatically
5. AI-formatted question pre-populated with the component data
6. User reviews AI insights with detailed explanations

### Example Interactions

**Example 1: BIOS Information**
```
User clicks sparkle icon next to "Vendor: American Megatrends Inc."
↓
Chat opens with pre-filled message:
"Explain: Vendor: American Megatrends Inc.
Please explain this BIOS vendor and version - what does it tell us about the system firmware"
↓
AI responds with firmware capabilities, security features, and compatibility notes
```

**Example 2: Linux Kernel**
```
User clicks sparkle icon next to "Linux-5.15.146.1-microsoft-standard-WSL2-x86_64-with-glibc2.39"
↓
Chat opens with pre-filled message:
"Explain: Linux-5.15.146.1-microsoft-standard-WSL2-x86_64-with-glibc2.39
Please explain this system identifier and what it tells us as a backend architect"
↓
AI provides breakdown of kernel version, WSL2 setup, architecture, and compatibility
```

## Files Modified/Created

### New Files

1. **`/opt/wegweiser/app/static/js/ai-insights.js`** (130 lines)
   - Main JavaScript module for AI insights functionality
   - Handles icon interactions and message injection
   - Manages insight definitions and templates

2. **`/opt/wegweiser/app/static/css/ai-insights.css`** (80 lines)
   - Styling for insight icons and animations
   - Theme-aware colors (light/dark mode support)
   - Hover effects and visual feedback

### Modified Files

1. **`/opt/wegweiser/app/templates/devices/components/hardware_components.html`**
   - Added `<link>` to `ai-insights.css`
   - Added `<script>` for `ai-insights.js`
   - Wrapped key metrics with AI insight icons across sections:
     - CPU (Processor name, core count)
     - Memory (Total, Used)
     - GPU (Model)
     - Battery (Health)
     - BIOS (Vendor, Version)
     - Storage (Drive usage)
     - Network (Interface details)

2. **`/opt/wegweiser/app/templates/devices/index-single-device.html`**
   - Added `ai-insights.css` to `<head>`
   - Added `ai-insights.js` to `extra_scripts` block

## Technical Implementation

### JavaScript Architecture

**`AIInsights` Class**

```javascript
class AIInsights {
    constructor()
    init()                          // Initialize listeners when DOM ready
    attachInsightListeners()        // Attach click handlers to icons
    handleInsightClick(element)     // Handle icon click → open chat
    sendInsightMessage(key, value)  // Inject message into chat
    createInsightIcon(key, value)   // Factory method for creating icons
}
```

### Icon HTML Structure

```html
<span class="ai-insight-icon-wrapper">
    Display Value (e.g., "American Megatrends Inc.")
    <span class="ai-insight-icon" 
          data-ai-insight="bios_vendor" 
          data-insight-value="American Megatrends Inc.">
        <i class="fas fa-sparkles"></i>
    </span>
</span>
```

### Styling

- **Idle State**: Semi-transparent purple sparkle (opacity: 0.6)
- **Hover State**: Full opacity, colored background, scale animation
- **Active State**: Scale down for tactile feedback
- **Dark Mode**: Adjusted colors for readability

### Message Flow

1. User clicks icon
2. Icon's `data-ai-insight` and `data-insight-value` attributes read
3. Chat offcanvas opens via Bootstrap
4. `AIInsights` waits for chat to initialize
5. Message constructed using template + value
6. Message injected into chat input
7. Form submitted automatically

## Insight Definitions

Each component type has a definition in `AIInsights.insightDefinitions`:

```javascript
insightDefinitions = {
    'bios_vendor': {
        label: 'BIOS Vendor',
        template: 'Explain this BIOS vendor and version - what does it tell us about the system firmware',
        icon: 'fas fa-question-circle'
    },
    // ... more definitions
}
```

## Integration with Chat System

The feature integrates seamlessly with the existing chat system:

- **Uses existing chat**: Reuses `window.currentChat` and `UnifiedChat` class
- **Respects permissions**: Works with current device context and user permissions
- **Follows UI patterns**: Uses Bootstrap offcanvas already in place
- **Maintains state**: Chat history and context preserved

## Browser Compatibility

- Works in all modern browsers (Chrome, Firefox, Safari, Edge)
- Uses standard DOM APIs (querySelector, event listeners)
- Uses Bootstrap 5 for offcanvas functionality
- Font Awesome icons for consistency

## Performance Considerations

- **Lazy initialization**: Listeners attached only after DOM ready
- **Event delegation**: Could be enhanced to use event delegation if needed
- **Minimal overhead**: Icons added during template rendering, no runtime DOM creation
- **CSS animations**: Use GPU-accelerated transforms for smooth performance

## Customization

### Adding New Insight Types

1. Update `insightDefinitions` in `ai-insights.js`:
```javascript
'my_component': {
    label: 'Component Label',
    template: 'Your explanation template here',
    icon: 'fas fa-your-icon'
}
```

2. Add icon to template in `hardware_components.html`:
```html
<span class="ai-insight-icon" 
      data-ai-insight="my_component" 
      data-insight-value="{{ component_value }}">
    <i class="fas fa-sparkles"></i>
</span>
```

### Customizing Messages

Edit the `template` field in `insightDefinitions` to customize the prompt that gets sent to AI.

### Styling Changes

Modify `/opt/wegweiser/app/static/css/ai-insights.css` to:
- Change colors: Adjust `#6f42c1` to your preferred color
- Change animations: Modify `@keyframes sparkle-hover`
- Change hover scale: Adjust `transform: scale(1.1)`

## Testing

### Manual Testing

1. Navigate to a device detail page
2. Look for sparkle icons (✨) next to hardware metrics
3. Hover over icons → Verify tooltip appears
4. Click icon → Chat should open automatically
5. Verify message is pre-filled with component data
6. Verify message sends correctly to AI

### Test Cases

- [ ] Icons appear on all supported components
- [ ] Hover shows correct tooltip
- [ ] Click opens chat panel
- [ ] Message pre-fills correctly
- [ ] Message sends automatically
- [ ] Works in light and dark themes
- [ ] Works on mobile devices
- [ ] Works with missing component data

## Troubleshooting

### Icons Don't Appear
- Check browser console for JavaScript errors
- Verify `ai-insights.js` is loaded
- Check that component data exists in `device.modular_data`

### Clicking Icon Doesn't Open Chat
- Verify `window.currentChat` is initialized
- Check if chat offcanvas DOM element exists
- Look for errors in browser console

### Message Doesn't Pre-fill
- Verify `messageInput` element ID is correct
- Check if chat form ID matches (`#chatForm`)
- Verify component data contains expected values

### Styling Issues
- Check that `ai-insights.css` is loaded
- Verify theme colors don't conflict with existing styles
- Test in both light and dark modes

## Future Enhancements

1. **AI Insight Caching**: Store frequently requested insights
2. **Custom Prompts**: Allow users to customize insight requests
3. **Insight History**: Track which insights users request
4. **Smart Suggestions**: Recommend insights based on anomalies
5. **Export Insights**: Generate reports from insights
6. **Voice Interaction**: Ask insights via voice commands

## Dependencies

- Bootstrap 5 (for offcanvas)
- Font Awesome 6+ (for icons)
- Existing Chat System (`ChatUI`, `UnifiedChat`)
- jQuery (if used elsewhere in project)

## Notes

- Icons only appear if component data exists
- Template messages use Jinja2 filters for formatting
- All user data is sanitized through chat system
- No external API calls from this module alone
