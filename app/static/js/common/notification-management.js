// Notification Management
        // Get CSRF token from meta tag or cookie
        function getCSRFToken() {
            // Try to get from meta tag first
            const metaToken = document.querySelector('meta[name=csrf-token]');
            if (metaToken) {
                return metaToken.getAttribute('content');
            }

            // Try to get from cookie
            const cookies = document.cookie.split(';');
            for (let cookie of cookies) {
                const [name, value] = cookie.trim().split('=');
                if (name === 'csrf_token') {
                    return decodeURIComponent(value);
                }
            }

            // If no token found, try to get it from a hidden form field
            const hiddenInput = document.querySelector('input[name="csrf_token"]');
            if (hiddenInput) {
                return hiddenInput.value;
            }

            return null;
        }

        function loadNotifications() {
            fetch('/notifications/recent')
                .then(response => response.json())
                .then(data => {
                    updateNotificationBadge(data.unread_count);
                    updateNotificationDropdown(data.notifications, data.has_more);
                })
                .catch(error => {
                    console.error('Error loading notifications:', error);
                    showNotificationError();
                });
        }

        function updateNotificationBadge(count) {
            const badge = document.getElementById('notificationCount');
            if (count > 0) {
                badge.textContent = count > 99 ? '99+' : count;
                badge.style.display = 'flex';
            } else {
                badge.style.display = 'none';
            }
        }

        function updateNotificationDropdown(notifications, hasMore) {
            const notificationList = document.getElementById('notificationList');

            if (notifications.length === 0) {
                notificationList.innerHTML = `
                    <div class="dropdown-item text-center py-3">
                        <i class="fas fa-bell-slash text-muted mb-2" style="font-size: var(--font-size-3xl);"></i>
                        <p class="mb-0 text-muted">No new notifications</p>
                    </div>
                `;
                return;
            }

            let html = '';
            notifications.forEach(notification => {
                html += `
                    <div class="dropdown-item d-flex align-items-start py-2 notification-item"
                         data-notification-id="${notification.uuid}"
                         onclick="handleNotificationClick('${notification.uuid}', '${notification.view_url}')">
                        <div class="me-3 mt-1">
                            <i class="${notification.icon_class}"></i>
                        </div>
                        <div class="flex-grow-1">
                            <h6 class="mb-1 fw-normal">${notification.title}</h6>
                            <p class="mb-0 text-muted small">${notification.content}</p>
                            <small class="text-muted">${notification.timestamp}</small>
                        </div>
                    </div>
                `;
            });

            if (hasMore) {
                html += `
                    <div class="dropdown-item text-center py-2 text-muted">
                        <small>+ more notifications available</small>
                    </div>
                `;
            }

            notificationList.innerHTML = html;
        }

        function showNotificationError() {
            const notificationList = document.getElementById('notificationList');
            notificationList.innerHTML = `
                <div class="dropdown-item text-center py-3">
                    <i class="fas fa-exclamation-triangle text-warning mb-2" style="font-size: var(--font-size-3xl);"></i>
                    <p class="mb-0 text-muted">Failed to load notifications</p>
                    <button class="btn btn-sm btn-outline-primary mt-2" onclick="loadNotifications()">Retry</button>
                </div>
            `;
        }

        function handleNotificationClick(notificationId, viewUrl) {
            // Mark notification as read
            const csrfToken = getCSRFToken();
            const headers = {
                'Content-Type': 'application/json',
            };

            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            fetch(`/notifications/${notificationId}/mark-read`, {
                method: 'POST',
                headers: headers
            }).then(() => {
                // Reload notifications to update count
                loadNotifications();
                // Navigate to the notification
                window.location.href = viewUrl;
            }).catch(error => {
                console.error('Error marking notification as read:', error);
                // Still navigate even if marking as read fails
                window.location.href = viewUrl;
            });
        }

        function markAllAsRead() {
            const csrfToken = getCSRFToken();
            const headers = {
                'Content-Type': 'application/json',
            };

            if (csrfToken) {
                headers['X-CSRFToken'] = csrfToken;
            }

            fetch('/notifications/mark-all-read', {
                method: 'POST',
                headers: headers
            }).then(response => response.json())
            .then(data => {
                if (data.success) {
                    // Reload notifications to update the display
                    loadNotifications();
                    // Show a brief success message (optional)
                    debug.log('All notifications marked as read');
                } else {
                    console.error('Error marking all as read:', data.error);
                }
            }).catch(error => {
                console.error('Error marking all notifications as read:', error);
            });
        }

        // Add CSS for notification hover effect
        const style = document.createElement('style');
        style.textContent = `
            .notification-item {
                cursor: pointer;
                transition: background-color 0.2s ease;
            }
            .notification-item:hover {
                background-color: var(--bs-gray-100);
            }
            [data-bs-theme="dark"] .notification-item:hover {
                background-color: var(--bs-gray-800);
            }
        `;
        document.head.appendChild(style);

        // Load notifications when the page loads
        document.addEventListener('DOMContentLoaded', function() {
            loadNotifications();
        });