# Wegweiser UI Modernization: Dependencies and Implementation Guide

This document outlines the dependencies for the new modernized UI and provides guidance on which elements can be safely removed or replaced.

## CSS Dependencies

| File | Purpose | Required? | Notes |
|------|---------|-----------|-------|
| **bootstrap.min.css** | Core framework | **Yes** | Required for layout and components |
| **base.css** | Core styling and variables | **Yes** | Foundation for the new theme system |
| **themes.css** | Theme variations | **Yes** | Provides dark/light/blue theme support |
| **layout.css** | Structural layout | **Yes** | Controls sidebar, header, and content areas |
| **components.css** | UI components | **Yes** | Styles for cards, tables, buttons, etc. |
| **gauges.css** | Chart styling | **Yes** | Required for health score visualization |
| **chat.css** | Chat interface | **Yes** | If chat functionality is used |
| **fontawesome/css/all.min.css** | Icons | **Yes** | Used throughout the interface |
| **pace.min.css** | Loading indicator | Optional | Can be replaced with simpler custom loader |
| **datatable/css/dataTables.bootstrap5.min.css** | Data tables | Optional | Only needed if using DataTables |
| **metismenu/metisMenu.min.css** | Old menu system | **Disposable** | Completely replaced in new system |
| **perfect-scrollbar/css/perfect-scrollbar.css** | Scrollbar styling | **Disposable** | Replaced with CSS-only scrollbars |
| **other plugin CSS files** | Various plugins | **Disposable** | Review on case-by-case basis |

## JavaScript Dependencies

| File | Purpose | Required? | Notes |
|------|---------|-----------|-------|
| **bootstrap.bundle.min.js** | Core framework | **Yes** | Required for component functionality |
| **jquery.min.js** | DOM manipulation | Recommended | Used by Bootstrap and many components |
| **main.js** | Core functionality | **Yes** | Controls sidebar, responsive behavior |
| **theme-switcher.js** | Theme toggling | **Yes** | For theme selection functionality |
| **health-gauge.js** | Health gauge | **Yes** | If using health score visualizations |
| **uPlot.iife.min.js** | Charts | **Yes** | If using any charts/graphs |
| **datatable/js/jquery.dataTables.min.js** | Data tables | Optional | Only if using DataTables |
| **datatable/js/dataTables.bootstrap5.min.js** | Data tables | Optional | Only if using DataTables |
| **pace.min.js** | Loading indicator | Optional | Can be replaced with simpler loader |
| **metismenu/metisMenu.min.js** | Old menu system | **Disposable** | Completely replaced in new system |
| **perfect-scrollbar/perfect-scrollbar.min.js** | Custom scrollbars | **Disposable** | Replaced with CSS-only scrollbars |

## Font Dependencies

| Resource | Purpose | Required? | Notes |
|----------|---------|-----------|-------|
| **Noto Sans** (Google Fonts) | Primary font | **Yes** | Used throughout the interface |
| **Material Icons Outlined** (Google Fonts) | UI icons | **Yes** | Used alongside Font Awesome |
| **Font Awesome** (self-hosted) | Icon system | **Yes** | Used throughout the interface |

## Implementation Guide

### 1. CSS File Creation

1. Create the new CSS files in your static directory:
   - `/static/css/base.css`
   - `/static/css/themes.css`
   - `/static/css/layout.css`
   - `/static/css/components.css`
   - `/static/css/gauges.css`

2. Keep your existing chat.css file if you're using the chat functionality.

### 2. JavaScript File Updates

1. Create or update the following JavaScript files:
   - `/static/js/main.js` (update existing)
   - `/static/js/theme-switcher.js` (new)
   - `/static/js/health-gauge.js` (new)

2. You can remove these files (and their references):
   - `/static/js/metisMenu.min.js`
   - `/static/js/perfect-scrollbar.min.js`

### 3. Update base.html

1. Replace your current base.html with the new version.
2. Update the include paths if your directory structure differs.
3. Ensure all routes in the navigation are correct for your application.

### 4. Test Common Pages

Test the following pages to ensure compatibility:
- Dashboard
- Device listing
- Device details
- Group listing
- Any forms or input-heavy pages
- Pages with DataTables
- Pages with charts/graphs

### 5. Remove Old Files

After successful testing, you can remove these files:
- metisMenu CSS and JS
- perfect-scrollbar CSS and JS
- Any other custom plugins that have been replaced

## Features of the New UI

1. **Native Bootstrap Navigation**: Uses standard Bootstrap features without MetisMenu
2. **CSS Variable-Based Theming**: Easy theme customization with CSS variables
3. **Optimized Layout**: More compact, better organized navigation
4. **Improved Health Gauge**: More visually appealing gauges using uPlot
5. **Simplified Structure**: Cleaner HTML structure with fewer dependencies
6. **Collapsible Sections**: Progressive disclosure for rarely used menu items
7. **Better Dark Mode**: Proper dark mode implementation with proper contrast
8. **Responsive Design**: Mobile-first approach with optimized sidebar

## Recommendations

1. **Incremental Adoption**: Implement the new UI in stages, starting with the CSS and base.html
2. **Test Thoroughly**: Check all key pages after implementation
3. **Review Custom Components**: Some custom components may need adjustments
4. **Keep uPlot**: Continue using uPlot for charts as it's lightweight and effective
5. **Remove Unnecessary Plugins**: Several plugins can be safely removed

