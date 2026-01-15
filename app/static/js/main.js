/**
 * Enhanced Main JS for Wegweiser UI
 * Handles sidebar interactions, mobile responsiveness, and micro-animations
 */

/**
 * Initialize Bootstrap tooltips and popovers
 */
function initTooltipsAndPopovers() {
    // Initialize tooltips if Bootstrap is available
    if (typeof bootstrap !== 'undefined') {
        const tooltipTriggerList = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        [...tooltipTriggerList].map(tooltipTriggerEl => new bootstrap.Tooltip(tooltipTriggerEl));

        // Initialize popovers
        const popoverTriggerList = document.querySelectorAll('[data-bs-toggle="popover"]');
        [...popoverTriggerList].map(popoverTriggerEl => new bootstrap.Popover(popoverTriggerEl));
    }
}

/**
 * Add subtle micro-interactions to UI elements
 */
function addMicroInteractions() {
    // Comment out or remove the card hover effect
    /*
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-4px)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = '';
        });
    });
    */

    // Add ripple effect to buttons - optimized for performance with proper cleanup
    document.addEventListener('click', function(e) {
        // Use event delegation instead of multiple listeners
        const button = e.target.closest('.btn');
        if (!button) return;

        // Don't create ripple if button is disabled
        if (button.disabled || button.classList.contains('disabled')) return;

        // Clean up any existing ripples first to prevent accumulation
        const existingRipples = button.querySelectorAll('.ripple-effect');
        existingRipples.forEach(ripple => {
            if (ripple.parentNode === button) {
                button.removeChild(ripple);
            }
        });

        // Create ripple with requestAnimationFrame for better performance
        requestAnimationFrame(() => {
            const rect = button.getBoundingClientRect();
            const x = e.clientX - rect.left;
            const y = e.clientY - rect.top;

            const ripple = document.createElement('span');
            ripple.classList.add('ripple-effect');
            ripple.style.left = (x - 50) + 'px'; // Center the 100px wide ripple
            ripple.style.top = (y - 50) + 'px';  // Center the 100px tall ripple

            button.appendChild(ripple);

            // Use animationend event to clean up ripple
            ripple.addEventListener('animationend', function() {
                if (ripple.parentNode === button) {
                    button.removeChild(ripple);
                }
            });

            // Fallback cleanup in case animationend doesn't fire
            setTimeout(() => {
                if (ripple.parentNode === button) {
                    button.removeChild(ripple);
                }
            }, 700); // Slightly longer than animation duration
        });
    });

    // Handle dropdown z-index for organization cards
    document.addEventListener('shown.bs.dropdown', function(e) {
        const dropdown = e.target;
        const orgCard = dropdown.closest('.org-card');
        if (orgCard) {
            orgCard.classList.add('dropdown-open');
        }
    });

    document.addEventListener('hidden.bs.dropdown', function(e) {
        const dropdown = e.target;
        const orgCard = dropdown.closest('.org-card');
        if (orgCard) {
            orgCard.classList.remove('dropdown-open');
        }
    });
}

/**
 * Initialize sidebar header/footer information
 */
function initSidebarInfo() {
    // Update date/time every second
    function updateDateTime() {
        const now = new Date();

        // Format date
        const dateElement = document.getElementById('current-date');
        if (dateElement) {
            dateElement.textContent = now.toLocaleDateString('en-US', {
                month: 'short',
                day: 'numeric'
            });
        }

        // Format time
        const timeElement = document.getElementById('current-time');
        if (timeElement) {
            timeElement.textContent = now.toLocaleTimeString('en-US', {
                hour: '2-digit',
                minute: '2-digit',
                hour12: false
            });
        }

        // Unix timestamp
        const unixElement = document.getElementById('unix-time');
        if (unixElement) {
            unixElement.textContent = Math.floor(now.getTime() / 1000);
        }
    }

    // Update immediately and then every second
    updateDateTime();
    setInterval(updateDateTime, 1000);

    // Fetch device count
    fetchDeviceCount();
}

/**
 * Fetch and display device count
 */
function fetchDeviceCount() {
    const deviceCountElement = document.getElementById('device-count');
    if (!deviceCountElement) return;

    // Try to fetch from devices endpoint
    fetch('/devices/api/count')
        .then(response => response.json())
        .then(data => {
            deviceCountElement.textContent = data.count || 0;
        })
        .catch(() => {
            // Fallback: try to get from dashboard or use placeholder
            deviceCountElement.textContent = '0';
        });
}

document.addEventListener('DOMContentLoaded', function() {
    // Setup sidebar toggle for mobile
    const sidebarToggleBtn = document.querySelector('.btn-toggle');
    const sidebarCloseBtn = document.querySelector('.sidebar-close');
    const sidebar = document.querySelector('.sidebar-wrapper');
    const overlay = document.querySelector('.overlay');

    // Handle sidebar toggle on mobile
    if (sidebarToggleBtn) {
        sidebarToggleBtn.addEventListener('click', function() {
            sidebar.classList.add('active');
            overlay.classList.add('active');
            document.body.style.overflow = 'hidden'; // Prevent scrolling
        });
    }

    // Handle sidebar close
    if (sidebarCloseBtn) {
        sidebarCloseBtn.addEventListener('click', function() {
            closeSidebar();
        });
    }

    // Close sidebar when clicking overlay
    if (overlay) {
        overlay.addEventListener('click', function() {
            closeSidebar();
        });
    }

    // Helper function to close sidebar
    function closeSidebar() {
        if (sidebar) sidebar.classList.remove('active');
        if (overlay) overlay.classList.remove('active');
        document.body.style.overflow = ''; // Restore scrolling
    }

    // Handle responsive behavior
    function handleResponsive() {
        if (window.innerWidth < 992) {
            document.body.classList.add('mobile-view');
        } else {
            document.body.classList.remove('mobile-view');
            // Always close mobile sidebar when resizing to desktop
            closeSidebar();
            // Also close topbar menu when resizing to desktop
            closeTopbarMenu();
        }
    }

    // Topbar collapsible menu for mobile
    const topbarToggle = document.getElementById('topbarToggle');
    const topbarCollapsible = document.getElementById('topbarCollapsible');
    const topbarOverlay = document.getElementById('topbarOverlay');

    function closeTopbarMenu() {
        if (topbarCollapsible) topbarCollapsible.classList.remove('show');
        if (topbarOverlay) topbarOverlay.classList.remove('show');
    }

    if (topbarToggle) {
        topbarToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            const isOpen = topbarCollapsible && topbarCollapsible.classList.contains('show');
            if (isOpen) {
                closeTopbarMenu();
            } else {
                if (topbarCollapsible) topbarCollapsible.classList.add('show');
                if (topbarOverlay) topbarOverlay.classList.add('show');
            }
        });
    }

    if (topbarOverlay) {
        topbarOverlay.addEventListener('click', function() {
            closeTopbarMenu();
        });
    }

    // Close topbar menu when clicking on a dropdown item (let the dropdown handle it)
    if (topbarCollapsible) {
        topbarCollapsible.querySelectorAll('.dropdown-item').forEach(function(item) {
            item.addEventListener('click', function() {
                // Small delay to allow dropdown action to complete
                setTimeout(closeTopbarMenu, 100);
            });
        });
    }

    // Initial call and add resize listener
    handleResponsive();
    window.addEventListener('resize', handleResponsive);

    // Setup submenu toggle
    const submenuToggles = document.querySelectorAll('.sidebar-nav .has-arrow');
    submenuToggles.forEach(toggle => {
        toggle.addEventListener('click', function(e) {
            e.preventDefault();

            const submenu = this.nextElementSibling;
            const isExpanded = this.getAttribute('aria-expanded') === 'true';

            this.setAttribute('aria-expanded', !isExpanded);
            submenu.classList.toggle('show');
            // Accordion behavior: close sibling submenus
            if (!isExpanded) {
                const parentList = this.closest('ul');
                if (parentList) {
                    parentList.querySelectorAll('.submenu.show').forEach(el => {
                        if (el !== submenu) el.classList.remove('show');
                    });
                    parentList.querySelectorAll('.has-arrow[aria-expanded="true"]').forEach(el => {
                        if (el !== this) el.setAttribute('aria-expanded', 'false');
                    });
                }
            }
        });
    });

    // Setup collapsible sidebar sections - optimized to avoid forced reflows
    const sectionToggles = document.querySelectorAll('.section-toggle');
    sectionToggles.forEach(toggle => {
        toggle.addEventListener('click', function() {
            // Use requestAnimationFrame to batch DOM updates
            requestAnimationFrame(() => {
                const section = toggle.closest('.sidebar-section');
                const content = section ? section.querySelector('ul') : this.nextElementSibling;

                if (content) {
                    // Read state first (batched read)
                    const isExpanded = content.classList.contains('expanded');

                    // Then apply all DOM changes together (batched write)
                    if (isExpanded) {
                        content.classList.remove('expanded');
                        this.classList.remove('active');
                        this.style.transform = 'rotate(0deg)';
                    } else {
                        content.classList.add('expanded');
                        this.classList.add('active');
                        this.style.transform = 'rotate(180deg)';
                    }
                }
            });
        });
    });

    // Initialize tooltips and popovers
    initTooltipsAndPopovers();

    // Initialize sidebar header/footer info
    initSidebarInfo();

    // Add micro-animations to buttons and cards
    addMicroInteractions();

    // ASCII Art - only show in debug mode
    if (typeof debug !== 'undefined' && debug.isEnabled()) {
        debug.log(`

░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░      ░▒▓█▓▒░░▒▓█▓▒░░▒▓█▓▒░
 ░▒▓█████████████▓▒░        ░▒▓█████████████▓▒░



  We love you! https://wegweiser.tech/#Contact
  `);
    }
});