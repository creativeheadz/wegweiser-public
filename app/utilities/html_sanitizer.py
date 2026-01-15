"""
HTML Sanitizer for AI chat responses
Ensures no malicious content or scripts can be executed while preserving code formatting
"""

import bleach
from markupsafe import Markup

# Define allowed HTML tags and attributes for use with bleach
ALLOWED_TAGS = [
    'p', 'br', 'b', 'i', 'em', 'strong', 'code', 'pre',
    'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
    'ul', 'ol', 'li', 'blockquote', 'a',
    'span', 'div', 'hr'
]

ALLOWED_ATTRIBUTES = {
    'a': ['href', 'title', 'target', 'rel'],
    'code': ['class'],
    'span': ['class', 'style'],
    'div': ['class'],
    'pre': ['class']
}

# Additional attributes for highlight.js
HIGHLIGHT_ATTRIBUTES = {
    'code': ['data-highlighted', 'tabindex']
}

def sanitize_html(html_content, allow_highlight=True):
    """
    Sanitize HTML content while preserving code formatting
    
    Parameters:
        html_content (str): HTML content to sanitize
        allow_highlight (bool): Whether to allow highlight.js attributes
        
    Returns:
        Markup: Safe HTML content
    """
    if not html_content:
        return ""
        
    # Make a copy of allowed attributes
    attributes = {**ALLOWED_ATTRIBUTES}
    
    # Add highlight.js attributes if requested
    if allow_highlight:
        for tag, attrs in HIGHLIGHT_ATTRIBUTES.items():
            if tag in attributes:
                attributes[tag].extend(attrs)
            else:
                attributes[tag] = attrs
    
    # Sanitize the HTML
    clean_html = bleach.clean(
        html_content,
        tags=ALLOWED_TAGS,
        attributes=attributes,
        strip=True,
        strip_comments=True
    )
    
    # Return as safe Markup
    return Markup(clean_html)
