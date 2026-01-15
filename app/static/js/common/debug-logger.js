/**
 * Debug Logger Utility
 * Provides conditional logging that can be enabled/disabled globally.
 * In production, set window.DEBUG_MODE = false to silence all debug logs.
 * 
 * Usage:
 *   debug.log('message', data);  // Only logs if DEBUG_MODE is true
 *   debug.warn('warning');       // Only logs if DEBUG_MODE is true  
 *   debug.error('error');        // Always logs (errors are important)
 *   debug.info('info');          // Only logs if DEBUG_MODE is true
 */

(function() {
    'use strict';
    
    // Set to false in production to disable verbose logging
    // Can be overridden by setting window.DEBUG_MODE before this script loads
    const DEBUG_MODE = window.DEBUG_MODE !== undefined ? window.DEBUG_MODE : false;
    
    const noop = function() {};
    
    window.debug = {
        // Standard logging - only in debug mode
        log: DEBUG_MODE ? console.log.bind(console) : noop,
        
        // Info logging - only in debug mode
        info: DEBUG_MODE ? console.info.bind(console) : noop,
        
        // Debug logging - only in debug mode
        debug: DEBUG_MODE ? console.debug.bind(console) : noop,
        
        // Warnings - only in debug mode (non-critical)
        warn: DEBUG_MODE ? console.warn.bind(console) : noop,
        
        // Errors - always log (critical issues)
        error: console.error.bind(console),
        
        // Group logging - only in debug mode
        group: DEBUG_MODE ? console.group.bind(console) : noop,
        groupEnd: DEBUG_MODE ? console.groupEnd.bind(console) : noop,
        groupCollapsed: DEBUG_MODE ? console.groupCollapsed.bind(console) : noop,
        
        // Table logging - only in debug mode
        table: DEBUG_MODE ? console.table.bind(console) : noop,
        
        // Check if debug mode is enabled
        isEnabled: function() {
            return DEBUG_MODE;
        }
    };
})();
