// Theme toggle functionality
        document.addEventListener('DOMContentLoaded', function () {
            const switcherInput = document.getElementById('switcher-input');
            const switcherLabel = document.querySelector('.switcher-label');

            // Function to update checkbox state based on current theme
            function updateSwitcherState() {
                const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
                if (switcherInput) {
                    switcherInput.checked = currentTheme === 'dark';
                }
                debug.log(`Theme: ${currentTheme}, Checkbox checked: ${switcherInput?.checked}`);
            }

            // Function to toggle theme
            function toggleTheme() {
                const currentTheme = document.documentElement.getAttribute('data-bs-theme') || 'light';
                const newTheme = currentTheme === 'light' ? 'dark' : 'light';

                debug.log('Theme switching from', currentTheme, 'to', newTheme);

                // Use the global setTheme function from theme-switcher.js
                if (typeof window.setTheme === 'function') {
                    window.setTheme(newTheme);
                } else {
                    // Fallback if global function not available
                    document.documentElement.setAttribute('data-bs-theme', newTheme);
                }

                // Use the global sendThemeToServer function if available
                if (typeof window.sendThemeToServer === 'function') {
                    window.sendThemeToServer(newTheme);
                }

                // Save to localStorage
                localStorage.setItem('theme', newTheme);

                // Update checkbox state immediately after theme change
                setTimeout(() => {
                    updateSwitcherState();
                    const actualTheme = document.documentElement.getAttribute('data-bs-theme');
                    debug.log('Theme actually set to:', actualTheme);
                }, 50);
            }

            if (switcherInput) {
                // Update checkbox state on page load
                updateSwitcherState();

                // Add event listener to checkbox
                switcherInput.addEventListener('change', toggleTheme);
            }

            // Also allow clicking on the label to toggle (for better UX)
            if (switcherLabel) {
                switcherLabel.addEventListener('click', function(e) {
                    // Prevent double-triggering since label click also triggers checkbox change
                    if (e.target === switcherLabel || e.target.classList.contains('switcher-toggler')) {
                        // Only handle if clicked on label itself or the toggle circle, not the icons
                        return;
                    }
                });
            }
        });