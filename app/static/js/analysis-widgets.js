// app/static/js/analysis-widgets.js

class AnalysisWidget {
    constructor() {
        this.modal = new bootstrap.Modal(document.getElementById('analysisModal'));
        this.deviceId = document.querySelector('[data-device-id]').dataset.deviceId;
        this.initializeEventListeners();
    }

    initializeEventListeners() {
        // Copy button
        document.getElementById('copyBtn').addEventListener('click', () => this.copyContent());
        
        // Print button
        document.getElementById('printBtn').addEventListener('click', () => this.printAnalysis());
        
        // PDF Export
        document.getElementById('exportBtn').addEventListener('click', () => this.exportToPDF());
    }

    async showAnalysis(analysisType) {
        try {
            const response = await fetch(`/api/device/${this.deviceId}/analysis/${analysisType}`);
            if (!response.ok) throw new Error('Failed to fetch analysis');
            
            const data = await response.json();
            
            // Update modal content
            document.getElementById('modalTitle').textContent = this.getAnalysisName(analysisType);
            document.getElementById('modalScore').textContent = `Health Score: ${data.score}/100`;
            document.getElementById('modalTimestamp').textContent = 
                `Last Updated: ${this.formatTimestamp(data.timestamp)}`;
            document.getElementById('modalContent').innerHTML = data.content;
            
            // Add metadata to modal for other functions
            document.getElementById('analysisModal').dataset.currentType = analysisType;
            
            this.modal.show();
        } catch (error) {
            console.error('Error fetching analysis:', error);
            alert('Failed to load analysis. Please try again.');
        }
    }

    async copyContent() {
        const content = document.getElementById('modalContent').innerText;
        try {
            await navigator.clipboard.writeText(content);
            this.showToast('Analysis copied to clipboard');
        } catch (error) {
            console.error('Copy failed:', error);
            this.showToast('Failed to copy content', 'error');
        }
    }

    printAnalysis() {
        const printWindow = window.open('', '_blank');
        const content = document.getElementById('modalContent').innerHTML;
        const title = document.getElementById('modalTitle').textContent;
        
        printWindow.document.write(`
            <!DOCTYPE html>
            <html>
            <head>
                <title>${title}</title>
                <link href="/static/css/analysis-print.css" rel="stylesheet">
            </head>
            <body>
                <h1>${title}</h1>
                <div class="analysis-content">
                    ${content}
                </div>
            </body>
            </html>
        `);
        
        printWindow.document.close();
        printWindow.focus();
        
        // Print after styles load
        setTimeout(() => {
            printWindow.print();
            printWindow.close();
        }, 250);
    }

    async exportToPDF() {
        try {
            const response = await fetch('/api/export-pdf', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrf-token]').content
                },
                body: JSON.stringify({
                    deviceId: this.deviceId,
                    analysisType: document.getElementById('analysisModal').dataset.currentType
                })
            });
            
            if (!response.ok) throw new Error('PDF export failed');
            
            const blob = await response.blob();
            const url = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = url;
            a.download = 'analysis-report.pdf';
            document.body.appendChild(a);
            a.click();
            window.URL.revokeObjectURL(url);
            document.body.removeChild(a);
            
            this.showToast('PDF exported successfully');
        } catch (error) {
            console.error('PDF export failed:', error);
            this.showToast('Failed to export PDF', 'error');
        }
    }

    showToast(message, type = 'success') {
        const toastEl = document.createElement('div');
        toastEl.className = `toast align-items-center text-white bg-${type === 'success' ? 'success' : 'danger'} border-0`;
        toastEl.setAttribute('role', 'alert');
        toastEl.setAttribute('aria-live', 'assertive');
        toastEl.setAttribute('aria-atomic', 'true');
        
        toastEl.innerHTML = `
            <div class="d-flex">
                <div class="toast-body">${message}</div>
                <button type="button" class="btn-close btn-close-white me-2 m-auto" data-bs-dismiss="toast"></button>
            </div>
        `;
        
        document.getElementById('toastContainer').appendChild(toastEl);
        const toast = new bootstrap.Toast(toastEl);
        toast.show();
        
        // Remove toast after it's hidden
        toastEl.addEventListener('hidden.bs.toast', () => toastEl.remove());
    }

    getAnalysisName(type) {
        const names = {
            // Event Logs
            'journalFiltered': 'Journal Logs',
            'authFiltered': 'Authentication Logs',
            'eventsFiltered-Application': 'Application Events',
            'eventsFiltered-Security': 'Security Events',
            'eventsFiltered-System': 'System Events',
            'syslogFiltered': 'System Logs',
            'kernFiltered': 'Kernel Logs',
            
            // System Information
            'msinfo-InstalledPrograms': 'Installed Programs',
            'msinfo-NetworkConfig': 'Network Configuration',
            'msinfo-StorageInfo': 'Storage Information',
            'msinfo-SystemHardwareConfig': 'Hardware Configuration',
            'msinfo-SystemSoftwareConfig': 'Software Configuration',
            
            // Specific Analyses
            'windrivers': 'Driver Analysis',
            'msinfo-RecentAppCrashes': 'Application Crashes'
        };
        return names[type] || type;
    }

    formatTimestamp(timestamp) {
        return new Intl.DateTimeFormat('en-GB', {
            dateStyle: 'medium',
            timeStyle: 'short'
        }).format(new Date(timestamp * 1000));
    }
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    window.analysisWidget = new AnalysisWidget();
});