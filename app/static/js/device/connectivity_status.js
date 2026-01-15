// Filepath: app/static/js/device/connectivity_status.js
class DeviceConnectivityStatus {
    constructor(options = {}) {
        this.deviceUuid = options.deviceUuid;
        this.statusElement = options.statusElement;
        this.refreshInterval = options.refreshInterval || 30000; // Default 30 seconds
        
        this.statusLabels = {
            online: '<span class="badge bg-success">Online</span>',
            offline: '<span class="badge bg-danger">Offline</span>',
            stale: '<span class="badge bg-warning">Connection Lost</span>',
            unknown: '<span class="badge bg-secondary">Unknown</span>'
        };
        
        // Start automatic refresh if requested
        if (options.autoRefresh) {
            this.startAutoRefresh();
        }
    }
    
    refresh() {
        if (!this.deviceUuid || !this.statusElement) {
            console.error('Device UUID or status element not set');
            return;
        }
        
        // Prefer NATS-aware status (includes staleness), fallback to generic connectivity
        const natsUrl = `/api/nats/device/${this.deviceUuid}/status`;
        const legacyUrl = `/api/agents/${this.deviceUuid}/connectivity`;

        fetch(natsUrl)
            .then(resp => resp.ok ? resp.json() : Promise.reject({fallback: true}))
            .then(data => {
                if (data && data.success) {
                    // Normalize to a common shape expected by updateStatus
                    const normalized = {
                        online_status: (data.status || (data.is_online ? 'Online' : 'Offline')),
                        last_seen_online: data.last_seen_online,
                        last_heartbeat: data.last_heartbeat
                    };
                    this.updateStatus(normalized);
                } else {
                    this.setStatus('unknown');
                }
            })
            .catch(err => {
                // Fallback to legacy connectivity endpoint
                fetch(legacyUrl)
                    .then(response => {
                        if (!response.ok) {
                            throw new Error(`HTTP error ${response.status}`);
                        }
                        return response.json();
                    })
                    .then(data => {
                        if (data.success) {
                            this.updateStatus(data.connectivity);
                        } else {
                            console.error('Error fetching connectivity status:', data.error);
                            this.setStatus('unknown');
                        }
                    })
                    .catch(error => {
                        console.error('Error fetching connectivity status:', error);
                        this.setStatus('unknown');
                    });
            });
    }
    
    updateStatus(connectivity) {
        if (!connectivity) {
            this.setStatus('unknown');
            return;
        }

        const statusText = (connectivity.online_status || connectivity.status || '').toLowerCase();
        const status = ['online', 'offline', 'stale'].includes(statusText) ? statusText : 'unknown';
        this.setStatus(status);

        // Add last seen info for offline/stale
        const lastSeenEpoch = connectivity.last_seen_online || connectivity.last_heartbeat;
        if ((status === 'offline' || status === 'stale') && lastSeenEpoch) {
            const lastSeen = new Date((/^[0-9]{13}$/.test(String(lastSeenEpoch)) ? lastSeenEpoch : lastSeenEpoch * 1000));
            const formattedLastSeen = lastSeen.toLocaleString();
            this.statusElement.setAttribute('data-bs-toggle', 'tooltip');
            this.statusElement.setAttribute('data-bs-placement', 'top');
            this.statusElement.setAttribute('title', `Last seen: ${formattedLastSeen}`);

            // Initialize tooltip if Bootstrap is available
            if (typeof bootstrap !== 'undefined' && bootstrap.Tooltip) {
                new bootstrap.Tooltip(this.statusElement);
            }
        }
    }
    
    setStatus(status) {
        if (this.statusElement) {
            this.statusElement.innerHTML = this.statusLabels[status] || this.statusLabels.unknown;
        }
    }
    
    startAutoRefresh() {
        this.refresh(); // Initial refresh
        this.refreshTimer = setInterval(() => this.refresh(), this.refreshInterval);
    }
    
    stopAutoRefresh() {
        if (this.refreshTimer) {
            clearInterval(this.refreshTimer);
            this.refreshTimer = null;
        }
    }
}
// Make it available globally
window.DeviceConnectivityStatus = DeviceConnectivityStatus;