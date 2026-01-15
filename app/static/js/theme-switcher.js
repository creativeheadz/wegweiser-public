/**
 * Simplified Theme Switcher for Wegweiser UI
 * Supports light and dark themes with smooth transitions
 */

// setTheme function is defined later in the file with enhanced functionality

/**
 * Send theme preference to server for session storage
 * @param {string} theme - The theme name to save
 */
function sendThemeToServer(theme) {
    // Only proceed if the endpoint is available
    if (typeof fetch !== 'undefined') {
        fetch('/account/set_theme', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCsrfToken() // Get CSRF token if needed
            },
            body: JSON.stringify({ theme: theme }),
            credentials: 'same-origin'
        }).then(response => {
            if (!response.ok) {
                console.warn('Theme could not be saved to session:', response.statusText);
            }
        }).catch(error => {
            console.warn('Theme could not be saved to session:', error);
        });
    }
}

// Make function available globally for other scripts
window.sendThemeToServer = sendThemeToServer;

/**
 * Get CSRF token from cookie
 * @returns {string} - CSRF token value
 */
function getCsrfToken() {
    const name = 'csrf_token=';
    const decodedCookie = decodeURIComponent(document.cookie);
    const cookies = decodedCookie.split(';');

    for (let i = 0; i < cookies.length; i++) {
        let cookie = cookies[i].trim();
        if (cookie.indexOf(name) === 0) {
            return cookie.substring(name.length, cookie.length);
        }
    }
    return '';
}

/**
 * Create theme toggle button in the navbar (legacy function kept for compatibility)
 * Note: This function is no longer used as the toggle button is now directly in the HTML
 */
function createThemeButtons() {
    // This function is kept for backward compatibility
    // The theme toggle button is now directly in the HTML template
    debug.log('Theme toggle button is now directly in the HTML template');
}

document.addEventListener('DOMContentLoaded', function () {
    // Apply saved theme on page load
    const savedTheme = localStorage.getItem('theme') || 'light';
    setTheme(savedTheme);

    // Update checkbox state based on current theme
    updateSwitcherCheckbox();
});

/**
 * Update the theme switcher checkbox state based on current theme
 */
function updateSwitcherCheckbox() {
    const switcherInput = document.getElementById('switcher-input');
    if (switcherInput) {
        const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
        switcherInput.checked = currentTheme === 'dark';
    }
}

// Make function available globally
window.updateSwitcherCheckbox = updateSwitcherCheckbox;

/**
 * Enhanced setTheme function that also updates the checkbox state
 * @param {string} theme - Theme name (light, dark)
 */
function setTheme(theme) {
    // Apply theme to HTML element
    document.documentElement.setAttribute('data-bs-theme', theme);

    // Save to localStorage
    localStorage.setItem('theme', theme);

    // Update checkbox state
    updateSwitcherCheckbox();

    // Update any active states in the UI
    const themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach(opt => opt.classList.remove('active'));

    // Find and mark active theme button
    themeOptions.forEach(option => {
        const themeName = option.getAttribute('data-theme') ||
            option.classList[1]?.replace('theme-', '');
        if (themeName === theme) {
            option.classList.add('active');
        }
    });
}

// Make function available globally for other scripts
window.setTheme = setTheme;