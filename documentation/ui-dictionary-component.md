# Dictionary-Style Component Documentation

## Overview
A reusable dictionary-style design element that can be used across different pages to define terms, concepts, or provide elegant explanations. Originally created for the Wegweiser definition on the index page.

## CSS Component

### Basic Structure
```css
.dictionary-definition {
    margin: 3rem 0;
    padding: 2rem;
    background: rgba(255, 255, 255, 0.05);
    border-radius: 16px;
    border: 1px solid rgba(255, 255, 255, 0.1);
    backdrop-filter: blur(8px);
    -webkit-backdrop-filter: blur(8px);
    max-width: 500px;
    margin-left: auto;
    margin-right: auto;
    text-align: left;
}

.definition-word {
    font-size: 2.5rem;
    font-weight: 700;
    color: #4f46e5;
    margin-bottom: 0.5rem;
    font-family: 'Georgia', serif;
}

.definition-type {
    font-style: italic;
    color: var(--text-secondary);
    margin-bottom: 0.25rem;
    font-size: 1rem;
}

.definition-pronunciation {
    color: var(--text-secondary);
    font-family: monospace;
    font-size: 1.1rem;
    margin-bottom: 1.5rem;
}

.definition-meaning {
    font-size: 1.1rem;
    line-height: 1.6;
    color: var(--text-primary);
    margin-bottom: 1rem;
}

.definition-context {
    font-size: 1rem;
    line-height: 1.5;
    color: var(--text-secondary);
    font-style: italic;
    padding-top: 1rem;
    border-top: 1px solid rgba(255, 255, 255, 0.1);
}

/* Responsive Design */
@media (max-width: 768px) {
    .dictionary-definition {
        margin: 2rem 0;
        padding: 1.5rem;
    }

    .definition-word {
        font-size: 2rem;
    }
}

@media (max-width: 576px) {
    .dictionary-definition {
        padding: 1rem;
    }

    .definition-word {
        font-size: 1.8rem;
    }
}
```

## HTML Structure

### Basic Template
```html
<div class="dictionary-definition">
    <div class="definition-word">[WORD]</div>
    <div class="definition-type">[PART OF SPEECH]</div>
    <div class="definition-pronunciation">[PRONUNCIATION]</div>
    <div class="definition-meaning">
        [LITERAL MEANING OR DEFINITION]
    </div>
    <div class="definition-context">
        [CONTEXTUAL EXPLANATION OR APPLICATION]
    </div>
</div>
```

## Usage Examples

### 1. Wegweiser (Current Implementation)
```html
<div class="dictionary-definition">
    <div class="definition-word">Wegweiser</div>
    <div class="definition-type">noun</div>
    <div class="definition-pronunciation">[ masculine ] /ˈveːkvaɪzɐ/</div>
    <div class="definition-meaning">
        A guide or signpost that shows the way; one who points the direction.
    </div>
    <div class="definition-context">
        The intelligent pathfinder for MSPs, guiding you through complex system landscapes with AI-powered insights and real-time monitoring.
    </div>
</div>
```

### 2. For Imprint/Legal Pages
```html
<div class="dictionary-definition">
    <div class="definition-word">Impressum</div>
    <div class="definition-type">noun</div>
    <div class="definition-pronunciation">[ neuter ] /ɪmˈprɛsʊm/</div>
    <div class="definition-meaning">
        Legal disclosure required by German law; literally "imprint" or "impression".
    </div>
    <div class="definition-context">
        Mandatory information about the publisher, ensuring transparency and legal compliance for digital services.
    </div>
</div>
```

### 3. For Technical Documentation
```html
<div class="dictionary-definition">
    <div class="definition-word">MSP</div>
    <div class="definition-type">acronym</div>
    <div class="definition-pronunciation">[ noun ] /ɛm ɛs piː/</div>
    <div class="definition-meaning">
        Managed Service Provider; a company that remotely manages IT infrastructure and services.
    </div>
    <div class="definition-context">
        Organizations that proactively monitor, maintain, and optimize their clients' technology systems to ensure optimal performance and security.
    </div>
</div>
```

### 4. For Error Pages
```html
<div class="dictionary-definition">
    <div class="definition-word">404</div>
    <div class="definition-type">HTTP status</div>
    <div class="definition-pronunciation">[ error code ] /fɔːr oʊ fɔːr/</div>
    <div class="definition-meaning">
        Not found; the requested resource could not be located on the server.
    </div>
    <div class="definition-context">
        The digital equivalent of a "wrong turn" - the path you're looking for has wandered off the beaten track.
    </div>
</div>
```

## Customization Options

### Size Variants
Add modifier classes for different sizes:

```css
/* Compact version */
.dictionary-definition.compact {
    padding: 1.5rem;
    max-width: 400px;
}

.dictionary-definition.compact .definition-word {
    font-size: 2rem;
}

/* Large version */
.dictionary-definition.large {
    padding: 3rem;
    max-width: 600px;
}

.dictionary-definition.large .definition-word {
    font-size: 3rem;
}
```

### Color Themes
```css
/* Alternative color scheme */
.dictionary-definition.alt-theme .definition-word {
    color: #06b6d4; /* Cyan instead of purple */
}

/* Minimal theme */
.dictionary-definition.minimal {
    background: transparent;
    border: 1px solid rgba(255, 255, 255, 0.2);
    backdrop-filter: none;
}
```

## Implementation Notes

1. **CSS Variables**: The component uses CSS custom properties (`var(--text-primary)`, `var(--text-secondary)`) which should be defined in your main stylesheet.

2. **Font Dependencies**: Uses Georgia serif font for the main word. Ensure fallbacks are available.

3. **Backdrop Filter**: Uses backdrop-filter for the glass effect. Consider fallbacks for older browsers.

4. **Responsive**: Automatically adapts to smaller screens with appropriate font size and padding adjustments.

## Integration

To use this component in any template:

1. Include the CSS in your stylesheet or as a separate component file
2. Use the HTML structure with your specific content
3. Customize colors and sizing as needed for your specific use case

This component maintains the elegant, sophisticated feel while being flexible enough for various contexts throughout the application.
