"""
Text Formatter Utility for Wegweiser

This module provides utilities for formatting analysis text with Font Awesome icons
and consistent styling to improve readability and aesthetics.
"""
import re
import html
from typing import List, Dict, Tuple, Optional, Any
import logging

class TextFormatter:
    """
    Formats analysis text with Font Awesome icons and consistent styling
    """
    
    # Icon mappings for different content types
    SECTION_ICONS = {
        'summary': 'fa-clipboard-list',
        'overview': 'fa-eye',
        'analysis': 'fa-chart-line',
        'details': 'fa-info-circle',
        'findings': 'fa-search',
        'issues': 'fa-exclamation-triangle',
        'recommendations': 'fa-lightbulb',
        'conclusion': 'fa-check-circle',
        'storage': 'fa-hdd',
        'network': 'fa-network-wired',
        'hardware': 'fa-microchip',
        'software': 'fa-laptop-code',
        'security': 'fa-shield-alt',
        'performance': 'fa-tachometer-alt',
        'configuration': 'fa-cogs',
        'status': 'fa-info-circle',
        'health': 'fa-heartbeat',
        'errors': 'fa-exclamation-circle',
        'warnings': 'fa-exclamation-triangle',
        'critical': 'fa-skull',
        'important': 'fa-exclamation',
        'note': 'fa-sticky-note',
        'tip': 'fa-lightbulb',
        'action': 'fa-bolt',
        'steps': 'fa-list-ol',
        'checklist': 'fa-tasks',
        'default': 'fa-angle-right'
    }
    
    # Status indicators with appropriate icons and colors
    STATUS_INDICATORS = {
        'healthy': {'icon': 'fa-check-circle', 'color': 'text-success'},
        'good': {'icon': 'fa-check-circle', 'color': 'text-success'},
        'optimal': {'icon': 'fa-check-circle', 'color': 'text-success'},
        'normal': {'icon': 'fa-check', 'color': 'text-success'},
        'warning': {'icon': 'fa-exclamation-triangle', 'color': 'text-warning'},
        'caution': {'icon': 'fa-exclamation-triangle', 'color': 'text-warning'},
        'attention': {'icon': 'fa-exclamation', 'color': 'text-warning'},
        'error': {'icon': 'fa-times-circle', 'color': 'text-danger'},
        'critical': {'icon': 'fa-skull', 'color': 'text-danger'},
        'severe': {'icon': 'fa-radiation', 'color': 'text-danger'},
        'failed': {'icon': 'fa-times-circle', 'color': 'text-danger'},
        'unknown': {'icon': 'fa-question-circle', 'color': 'text-secondary'},
        'info': {'icon': 'fa-info-circle', 'color': 'text-info'},
        'note': {'icon': 'fa-sticky-note', 'color': 'text-info'}
    }
    
    @staticmethod
    def format_analysis(text: str) -> str:
        """
        Format analysis text with Font Awesome icons and consistent styling
        
        Args:
            text: The raw analysis text (may contain HTML)
            
        Returns:
            Formatted text with icons and styling
        """
        if not text:
            return ""
            
        # If the text is already well-formatted with our custom classes, return it as is
        if 'analysis-section' in text:
            return text
            
        # Process the text
        formatter = TextFormatter()
        return formatter._process_text(text)
    
    def _process_text(self, text: str) -> str:
        """Process and format the text with icons and styling"""
        # First, check if the text is HTML
        is_html = '<' in text and '>' in text
        
        if is_html:
            # Process HTML text
            return self._process_html(text)
        else:
            # Process plain text
            return self._process_plain_text(text)
    
    def _process_html(self, html_text: str) -> str:
        """Process HTML text to add icons and styling"""
        # Extract and process headings
        html_text = self._enhance_headings(html_text)
        
        # Enhance paragraphs with status indicators
        html_text = self._enhance_paragraphs(html_text)
        
        # Enhance lists
        html_text = self._enhance_lists(html_text)
        
        # Add overall container
        html_text = f'<div class="analysis-content">{html_text}</div>'
        
        return html_text
    
    def _process_plain_text(self, plain_text: str) -> str:
        """Convert plain text to formatted HTML with icons and styling"""
        # Escape HTML characters
        text = html.escape(plain_text)
        
        # Split into lines
        lines = text.split('\n')
        
        # Process lines
        formatted_lines = []
        in_list = False
        list_items = []
        
        for line in lines:
            line = line.strip()
            if not line:
                if in_list and list_items:
                    # End the list
                    formatted_lines.append(self._format_list(list_items))
                    list_items = []
                    in_list = False
                formatted_lines.append('<br>')
                continue
                
            # Check if this is a heading
            if line.endswith(':') or (len(line) < 80 and line.isupper()):
                if in_list and list_items:
                    # End the list
                    formatted_lines.append(self._format_list(list_items))
                    list_items = []
                    in_list = False
                
                # This is likely a heading
                heading = line.rstrip(':')
                formatted_lines.append(self._format_heading(heading, 'h4'))
            elif line.startswith('- ') or line.startswith('* '):
                # This is a list item
                in_list = True
                list_items.append(line[2:])
            elif line.startswith('#'):
                # This is a heading with markdown
                level = 0
                for char in line:
                    if char == '#':
                        level += 1
                    else:
                        break
                heading = line[level:].strip()
                tag = f'h{min(level+2, 6)}'  # h3-h6 based on # level
                
                if in_list and list_items:
                    # End the list
                    formatted_lines.append(self._format_list(list_items))
                    list_items = []
                    in_list = False
                    
                formatted_lines.append(self._format_heading(heading, tag))
            else:
                # Regular paragraph
                if in_list and list_items:
                    # End the list
                    formatted_lines.append(self._format_list(list_items))
                    list_items = []
                    in_list = False
                
                formatted_lines.append(self._format_paragraph(line))
        
        # Handle any remaining list items
        if in_list and list_items:
            formatted_lines.append(self._format_list(list_items))
        
        # Join all formatted lines
        result = '\n'.join(formatted_lines)
        
        # Add overall container
        result = f'<div class="analysis-content">{result}</div>'
        
        return result
    
    def _enhance_headings(self, html_text: str) -> str:
        """Enhance HTML headings with icons"""
        # Regular expression to find headings
        heading_pattern = r'<(h[1-6])>(.*?)</\1>'
        
        def replace_heading(match):
            tag = match.group(1)
            content = match.group(2)
            
            # Find appropriate icon
            icon = self._get_icon_for_text(content)
            
            # Create formatted heading
            return f'<{tag} class="analysis-section"><i class="fas {icon} me-2"></i>{content}</{tag}>'
        
        # Replace headings
        return re.sub(heading_pattern, replace_heading, html_text)
    
    def _enhance_paragraphs(self, html_text: str) -> str:
        """Enhance HTML paragraphs with status indicators"""
        # Regular expression to find paragraphs
        paragraph_pattern = r'<p>(.*?)</p>'
        
        def replace_paragraph(match):
            content = match.group(1)
            
            # Check for status indicators
            for status, info in self.STATUS_INDICATORS.items():
                if re.search(r'\b' + status + r'\b', content.lower()):
                    return f'<p class="analysis-paragraph {info["color"]}"><i class="fas {info["icon"]} me-2"></i>{content}</p>'
            
            # No status found, check for other keywords
            icon = self._get_icon_for_text(content)
            if icon != self.SECTION_ICONS['default']:
                return f'<p class="analysis-paragraph"><i class="fas {icon} me-2"></i>{content}</p>'
            
            # No special formatting needed
            return f'<p class="analysis-paragraph">{content}</p>'
        
        # Replace paragraphs
        return re.sub(paragraph_pattern, replace_paragraph, html_text)
    
    def _enhance_lists(self, html_text: str) -> str:
        """Enhance HTML lists with icons"""
        # Regular expression to find list items
        li_pattern = r'<li>(.*?)</li>'
        
        def replace_li(match):
            content = match.group(1)
            
            # Check for status indicators
            for status, info in self.STATUS_INDICATORS.items():
                if re.search(r'\b' + status + r'\b', content.lower()):
                    return f'<li class="analysis-list-item {info["color"]}"><i class="fas {info["icon"]} me-2"></i>{content}</li>'
            
            # No status found, use default list icon
            return f'<li class="analysis-list-item"><i class="fas fa-angle-right me-2"></i>{content}</li>'
        
        # Replace list items
        return re.sub(li_pattern, replace_li, html_text)
    
    def _format_heading(self, text: str, tag: str) -> str:
        """Format a heading with an appropriate icon"""
        icon = self._get_icon_for_text(text)
        return f'<{tag} class="analysis-section"><i class="fas {icon} me-2"></i>{text}</{tag}>'
    
    def _format_paragraph(self, text: str) -> str:
        """Format a paragraph with appropriate styling and icons"""
        # Check for status indicators
        for status, info in self.STATUS_INDICATORS.items():
            if re.search(r'\b' + status + r'\b', text.lower()):
                return f'<p class="analysis-paragraph {info["color"]}"><i class="fas {info["icon"]} me-2"></i>{text}</p>'
        
        # No status found, check for other keywords
        icon = self._get_icon_for_text(text)
        if icon != self.SECTION_ICONS['default']:
            return f'<p class="analysis-paragraph"><i class="fas {icon} me-2"></i>{text}</p>'
        
        # No special formatting needed
        return f'<p class="analysis-paragraph">{text}</p>'
    
    def _format_list(self, items: List[str]) -> str:
        """Format a list of items with icons"""
        formatted_items = []
        for item in items:
            # Check for status indicators
            icon_class = ""
            for status, info in self.STATUS_INDICATORS.items():
                if re.search(r'\b' + status + r'\b', item.lower()):
                    formatted_items.append(
                        f'<li class="analysis-list-item {info["color"]}"><i class="fas {info["icon"]} me-2"></i>{item}</li>'
                    )
                    break
            else:
                # No status found, use default list icon
                formatted_items.append(
                    f'<li class="analysis-list-item"><i class="fas fa-angle-right me-2"></i>{item}</li>'
                )
        
        return f'<ul class="analysis-list">\n{"".join(formatted_items)}\n</ul>'
    
    def _get_icon_for_text(self, text: str) -> str:
        """Get an appropriate icon for the given text"""
        text_lower = text.lower()
        
        # Check each keyword
        for keyword, icon in self.SECTION_ICONS.items():
            if keyword in text_lower:
                return icon
        
        # Default icon
        return self.SECTION_ICONS['default']

# Create a singleton instance
text_formatter = TextFormatter()
