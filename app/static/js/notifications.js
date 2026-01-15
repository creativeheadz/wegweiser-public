/**
 * Central Notification System for Wegweiser
 * Handles auto-dismiss, animations, and stacking for flash messages
 */

class NotificationManager {
    constructor() {
        this.container = document.getElementById('notification-container');
        this.init();
    }

    init() {
        if (!this.container) return;

        // Auto-show notifications on page load
        this.showNotifications();

        // Set up auto-dismiss timers
        this.setupAutoDismiss();

        // Add stacking support
        this.setupStacking();
    }

    showNotifications() {
        const alerts = this.container.querySelectorAll('.alert');

        alerts.forEach((alert, index) => {
            // Add entrance animation with staggered delay
            setTimeout(() => {
                alert.style.opacity = '0';
                alert.style.transform = 'translateX(100%)';
                alert.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';

                // Trigger animation
                requestAnimationFrame(() => {
                    alert.style.opacity = '1';
                    alert.style.transform = 'translateX(0)';
                });
            }, index * 150); // Stagger by 150ms
        });

        // Show container for auth pages
        if (this.container.classList.contains('auth-notifications')) {
            this.container.style.display = 'block';
        } else {
            // Slide in from right for main app
            this.container.classList.add('show');
        }
    }

    setupAutoDismiss() {
        const alerts = this.container.querySelectorAll('.alert');

        alerts.forEach(alert => {
            // Check if auto-dismiss is disabled
            const autoDismiss = alert.getAttribute('data-auto-dismiss');
            if (autoDismiss === 'false') {
                return; // Skip auto-dismiss for notifications with actions
            }

            const category = this.getAlertCategory(alert);
            const dismissTime = this.getDismissTime(category);

            if (dismissTime > 0) {
                setTimeout(() => {
                    this.dismissAlert(alert);
                }, dismissTime);
            }
        });
    }

    getAlertCategory(alert) {
        const classes = alert.className;
        if (classes.includes('alert-success')) return 'success';
        if (classes.includes('alert-danger')) return 'danger';
        if (classes.includes('alert-warning')) return 'warning';
        if (classes.includes('alert-info')) return 'info';
        return 'default';
    }

    getDismissTime(category) {
        const times = {
            'success': 4000,   // Success messages - 4 seconds
            'info': 5000,      // Info messages - 5 seconds
            'warning': 7000,   // Warnings - 7 seconds
            'danger': 0,       // Errors - manual dismiss only
            'default': 5000    // Default - 5 seconds
        };
        return times[category] || times.default;
    }

    dismissAlert(alert) {
        // Add exit animation
        alert.style.transition = 'all 0.3s cubic-bezier(0.4, 0, 0.2, 1)';
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(100%)';
        alert.style.marginBottom = '0';
        alert.style.maxHeight = '0';
        alert.style.padding = '0';

        // Remove from DOM after animation
        setTimeout(() => {
            if (alert.parentNode) {
                alert.parentNode.removeChild(alert);
            }
            this.checkIfEmpty();
        }, 300);
    }

    setupStacking() {
        const alerts = this.container.querySelectorAll('.alert');

        alerts.forEach((alert, index) => {
            // Add z-index for proper stacking
            alert.style.zIndex = 10000 - index;

            // Add margin for stacking effect
            if (index > 0) {
                alert.style.marginTop = '0.5rem';
            }
        });
    }

    checkIfEmpty() {
        const remainingAlerts = this.container.querySelectorAll('.alert');

        if (remainingAlerts.length === 0) {
            // Hide container when empty
            if (this.container.classList.contains('auth-notifications')) {
                this.container.style.display = 'none';
            } else {
                this.container.classList.remove('show');
            }
        }
    }

    // Public method to add new notifications programmatically
    addNotification(message, category = 'info', imageUrl = null, actions = null) {
        const alertHtml = this.createAlertHtml(message, category, imageUrl, actions);
        const tempDiv = document.createElement('div');
        tempDiv.innerHTML = alertHtml;
        const alert = tempDiv.firstElementChild;

        this.container.appendChild(alert);

        // Animate in
        alert.style.opacity = '0';
        alert.style.transform = 'translateX(100%)';
        alert.style.transition = 'all 0.4s cubic-bezier(0.4, 0, 0.2, 1)';

        requestAnimationFrame(() => {
            alert.style.opacity = '1';
            alert.style.transform = 'translateX(0)';
        });

        // Set up auto-dismiss (only if no actions)
        if (!actions) {
            const dismissTime = this.getDismissTime(category);
            if (dismissTime > 0) {
                setTimeout(() => {
                    this.dismissAlert(alert);
                }, dismissTime);
            }
        }

        // Show container
        if (!this.container.classList.contains('auth-notifications')) {
            this.container.classList.add('show');
        }
    }

    getNotificationIcon(category) {
        const icons = {
            'success': 'fas fa-check-circle',
            'danger': 'fas fa-exclamation-triangle',
            'error': 'fas fa-exclamation-triangle',
            'warning': 'fas fa-exclamation-triangle',
            'info': 'fas fa-info-circle',
            'primary': 'fas fa-info-circle',
            'secondary': 'fas fa-bell',
            'light': 'fas fa-bell',
            'dark': 'fas fa-bell'
        };
        return icons[category] || 'fas fa-bell';
    }

    getNotificationTitle(category) {
        const titles = {
            'success': 'Success',
            'danger': 'Error',
            'error': 'Error',
            'warning': 'Warning',
            'info': 'Information',
            'primary': 'Notice',
            'secondary': 'Notice',
            'light': 'Notice',
            'dark': 'Notice'
        };
        return titles[category] || 'Notice';
    }

    createAlertHtml(message, category, imageUrl, actions) {
        const icon = this.getNotificationIcon(category);
        const title = this.getNotificationTitle(category);

        // Create action buttons HTML
        let actionButtonsHtml = '';
        if (actions && actions.length > 0) {
            actionButtonsHtml = '<div class="notification-actions">';
            actions.forEach(action => {
                const btnClass = action.class || 'btn-outline-primary';
                const btnText = action.text || 'Action';
                const btnOnclick = action.onclick || '';
                const btnHref = action.href || '#';

                if (btnOnclick) {
                    actionButtonsHtml += `<button type="button" class="btn btn-sm ${btnClass}" onclick="${btnOnclick}">${btnText}</button>`;
                } else {
                    actionButtonsHtml += `<a href="${btnHref}" class="btn btn-sm ${btnClass}">${btnText}</a>`;
                }
            });
            actionButtonsHtml += '</div>';
        }

        return `
            <div class="alert alert-${category} alert-dismissible fade show notification-enhanced" role="alert" data-auto-dismiss="${actions ? 'false' : 'true'}">
                <div class="notification-header">
                    <div class="notification-icon">
                        <i class="${icon}"></i>
                    </div>
                    <div class="notification-content">
                        ${imageUrl ? `<img src="${imageUrl}" alt="Notification Image" class="notification-image">` : ''}
                        <div class="notification-text">
                            <strong class="notification-title">${title}</strong>
                            <p class="notification-message">${message}</p>
                            ${actionButtonsHtml}
                        </div>
                    </div>
                </div>
                <button type="button" class="btn-close notification-close" data-bs-dismiss="alert" aria-label="Close"></button>
            </div>
        `;
    }
}

// Initialize when DOM is ready
document.addEventListener('DOMContentLoaded', function () {
    window.notificationManager = new NotificationManager();
});

// Expose global function for AJAX responses
window.showNotification = function (message, category = 'info', imageUrl = null, actions = null) {
    if (window.notificationManager) {
        window.notificationManager.addNotification(message, category, imageUrl, actions);
    }
};
