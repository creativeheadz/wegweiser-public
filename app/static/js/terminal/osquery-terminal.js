// Filepath: app/static/js/terminal/osquery-terminal.js
/**
 * Osquery Terminal - Direct SQL query interface for devices
 * Provides a terminal-like interface for executing osquery commands
 */

class OsqueryTerminal {
    constructor(options = {}) {
        this.deviceUuid = options.deviceUuid;
        this.entityName = options.entityName;
        this.container = options.container || document.getElementById('terminalOutput');
        this.form = options.form || document.getElementById('terminalForm');
        this.input = options.input || document.getElementById('terminalInput');
        this.submitButton = options.submitButton || document.getElementById('terminalSubmit');

        // Get CSRF token with debugging
        const csrfInput = document.querySelector('input[name="csrf_token"]');
        debug.log('CSRF input element found:', !!csrfInput);
        if (csrfInput) {
            this.csrfToken = csrfInput.value;
            debug.log('CSRF token retrieved:', this.csrfToken ? 'Yes' : 'No');
        } else {
            console.error('CSRF token input not found');
            this.csrfToken = '';
        }

        // Command history
        this.commandHistory = [];
        this.historyIndex = -1;

        // Table completion cache
        this.availableTables = [];
        this.tablesLoaded = false;

        this._setupEventListeners();
        this._ensureQuickBar();
        this._loadTables();
        this._loadTerminalHistory();

        // Background: prefetch full schema snapshot for NL->SQL (cached ~24h)
        setTimeout(() => {
            try { this._prefetchSchemaIfNeeded(24, 150); } catch (e) { console.warn('Schema prefetch scheduling failed', e); }
        }, 1200);

    }


    _setupEventListeners() {
        debug.log('Setting up terminal event listeners');
        debug.log('Form element:', this.form);
        debug.log('Input element:', this.input);

        // Defensive: if required elements are missing, don't throw and allow other init to continue
        if (!this.form || !this.input) {
            console.error('Osquery Terminal init: missing form or input element');
            return;
        }

        // Form submission
        this.form.addEventListener('submit', (e) => {
            debug.log('Terminal form submitted');
            e.preventDefault();
            this._executeCommand();
        });

        // Input key handling
        this.input.addEventListener('keydown', (e) => {
            switch(e.key) {
                case 'ArrowUp':
                    e.preventDefault();
                    this._navigateHistory(-1);
                    break;
                case 'ArrowDown':
                    e.preventDefault();
                    this._navigateHistory(1);
                    break;
                case 'Tab':
                    e.preventDefault();
                    this._handleTabCompletion();
                    break;
            }
        });

        // Auto-focus input when terminal is shown
        const chatOffcanvas = document.getElementById('chatOffcanvas');
        if (chatOffcanvas) {
            chatOffcanvas.addEventListener('shown.bs.offcanvas', () => {
                // Only focus if terminal mode is active
                const terminalModeContent = document.getElementById('terminalModeContent');
                if (terminalModeContent && terminalModeContent.style.display !== 'none') {
                    this.input.focus();
                }
            });
        }
    }

    async _executeCommand() {
        debug.log('_executeCommand called');
        const command = this.input.value.trim();
        debug.log('Command value:', command);
        if (!command) {
            debug.log('Empty command, returning');
            return;
        }

        // Add to history
        this.commandHistory.push(command);
        this.historyIndex = this.commandHistory.length;
        this._updateRecentChips();

        // Display command in terminal
        this._addToOutput(`<div class="terminal-command">osquery> ${this._escapeHtml(command)}</div>`);

        // Clear input and disable form
        this.input.value = '';
        this._setLoading(true);

        // Debug logging
        debug.log('Executing osquery command:', command);
        debug.log('Device UUID:', this.deviceUuid);
        debug.log('CSRF Token:', this.csrfToken);

        try {
            const url = `/osquery/api/device/${this.deviceUuid}/osquery`;
            debug.log('Request URL:', url);

            const response = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                },
                body: JSON.stringify({
                    query: command
                })
            });

            debug.log('Response status:', response.status);
            debug.log('Response headers:', response.headers);

            const data = await response.json();
            debug.log('Response data:', data);

            if (response.ok && !data.error) {
                this._displayResult(data);
            } else {
                this._displayError(data.error || `HTTP ${response.status}: ${response.statusText}`);
            }

        } catch (error) {
            console.error('Terminal command error:', error);
            this._displayError(`Network error: ${error.message}`);
        } finally {
            this._setLoading(false);
            this.input.focus();
        }
    }

    _displayResult(data) {
        debug.log('_displayResult received:', data);
        let output = '<div class="terminal-result">';

        // Handle different response formats
        // The server returns either the direct result or wrapped in a 'data' object
        const result = data.data || data.result || data;
        debug.log('Extracted result:', result);

        // Check if we have JSON data (from --json flag)
        if (result.data && result.format === 'json' && Array.isArray(result.data)) {
            debug.log('Format: JSON with data array, length:', result.data.length);
            if (result.data.length === 0) {
                output += '<div class="text-muted">No results returned</div>';
            } else {
                output += this._formatAsDataTable(result.data);
            }
        } else if (result.output) {
            debug.log('Format: Text output');
            // Text output from osquery (like .tables)
            output += `<pre>${this._escapeHtml(result.output)}</pre>`;
        } else if (Array.isArray(result)) {
            debug.log('Format: Direct array, length:', result.length);
            if (result.length === 0) {
                output += '<div class="text-muted">No results returned</div>';
            } else {
                output += this._formatAsDataTable(result);
            }
        } else if (result && typeof result === 'object') {
            debug.log('Format: Object (fallback to JSON)');
            output += `<pre>${JSON.stringify(result, null, 2)}</pre>`;
        } else if (result) {
            debug.log('Format: Other value');
            output += `<div>${this._escapeHtml(String(result))}</div>`;
        } else {
            debug.log('Format: Empty/success');
            output += '<div class="text-success">Command executed successfully</div>';
        }

        output += '</div>';
        this._addToOutput(output);
    }

    _formatAsDataTable(data) {
        if (!data || data.length === 0) return '<div class="text-muted">No data</div>';

        const tableId = `osquery-table-${Date.now()}`;
        const columns = Object.keys(data[0]);

        // Store data globally for fullscreen view
        if (!window.osqueryTableData) {
            window.osqueryTableData = {};
        }
        window.osqueryTableData[tableId] = data;

        // Create table HTML with manual rendering (no DataTables for now)
        let html = `
            <div class="table-responsive terminal-data-table-container">
                <table id="${tableId}" class="table table-dark table-sm table-hover table-striped" style="font-size: var(--font-size-sm);">
                    <thead>
                        <tr>${columns.map(col => `<th>${this._escapeHtml(col)}</th>`).join('')}</tr>
                    </thead>
                    <tbody>
        `;

        // Add rows (limit to first 25 for inline view)
        data.slice(0, 25).forEach(row => {
            html += '<tr>';
            columns.forEach(col => {
                let value = row[col];
                // Truncate long values
                if (value && String(value).length > 50) {
                    value = String(value).substring(0, 47) + '...';
                }
                html += `<td>${this._escapeHtml(String(value || ''))}</td>`;
            });
            html += '</tr>';
        });

        html += `
                    </tbody>
                </table>
            </div>
        `;

        if (data.length > 25) {
            html += `<div class="text-muted small">Showing 25 of ${data.length} rows</div>`;
        } else {
            html += `<div class="text-muted small">${data.length} row(s)</div>`;
        }

        html += `<button class="btn btn-sm btn-info mt-2" onclick="expandOsqueryTable('${tableId}')">
            <i class="fas fa-expand"></i> Fullscreen View
        </button>`;

        return html;
    }

    _displayError(error) {
        const output = `<div class="terminal-result terminal-error">
            <i class="fas fa-exclamation-triangle me-2"></i>
            Error: ${this._escapeHtml(error)}
        </div>`;
        this._addToOutput(output);
    }

    _formatTable(data) {
        if (!data || data.length === 0) return '<div class="text-muted">No data</div>';

        const keys = Object.keys(data[0]);
        let table = '<table class="terminal-table">';

        // Header
        table += '<thead><tr>';
        keys.forEach(key => {
            table += `<th>${this._escapeHtml(key)}</th>`;
        });
        table += '</tr></thead>';

        // Body
        table += '<tbody>';
        data.forEach(row => {
            table += '<tr>';
            keys.forEach(key => {
                const value = row[key];
                table += `<td>${this._escapeHtml(String(value || ''))}</td>`;
            });
            table += '</tr>';
        });
        table += '</tbody></table>';

        // Add row count
        table += `<div class="text-muted small mt-2">${data.length} row(s) returned</div>`;

        return table;
    }

    _addToOutput(html) {
        const outputDiv = document.createElement('div');
        outputDiv.innerHTML = html;
        this.container.appendChild(outputDiv);

        // Scroll to bottom
        this.container.scrollTop = this.container.scrollHeight;
    }

    _navigateHistory(direction) {
        if (this.commandHistory.length === 0) return;

        this.historyIndex += direction;

        if (this.historyIndex < 0) {
            this.historyIndex = 0;
        } else if (this.historyIndex >= this.commandHistory.length) {
            this.historyIndex = this.commandHistory.length;
            this.input.value = '';
            return;
        }

        this.input.value = this.commandHistory[this.historyIndex] || '';
    }

    async _loadTables() {
        if (this.tablesLoaded) return;

        // Check device-specific cache
        const cacheKey = `osquery_tables_${this.deviceUuid}`;
        const cached = localStorage.getItem(cacheKey);

        if (cached) {
            try {
                const cacheData = JSON.parse(cached);
                const age = Date.now() - cacheData.cachedAt;

                // Use cache if less than 1 hour old
                if (age < 3600000) {
                    this.availableTables = cacheData.tables;
                    this.tablesLoaded = true;
                    this.devicePlatform = cacheData.platform;
                    debug.log(`Loaded ${cacheData.tables.length} ${cacheData.platform} tables from cache`);
                    this._refreshChips();
                    return;
                }
            } catch (e) {
                console.warn('Failed to parse cached tables:', e);
                localStorage.removeItem(cacheKey);
            }
        }

        // Cache miss or expired - fetch fresh
        try {
            const response = await fetch(`/osquery/api/device/${this.deviceUuid}/osquery/tables`);
            const data = await response.json();

            if (response.ok && data.result) {
                // Extract table names from the result
                let tables = [];
                if (data.result.output) {
                    // Parse from text output
                    tables = this._parseTablesFromOutput(data.result.output);
                } else if (Array.isArray(data.result)) {
                    tables = data.result.map(row => row.name || row.table_name).filter(Boolean);
                }

                this.availableTables = tables;
                this.tablesLoaded = true;

                // Detect platform from table names
                const platform = this._detectPlatform(tables);
                this.devicePlatform = platform;

                // Cache the results (device-specific)
                localStorage.setItem(cacheKey, JSON.stringify({
                    deviceUuid: this.deviceUuid,
                    deviceName: this.entityName,
                    platform: platform,
                    tables: tables,
                    cachedAt: Date.now()
                }));

                debug.log(`Loaded ${tables.length} ${platform} tables (cached for 1 hour)`);
                this._refreshChips();


                // Cleanup old caches (keep last 5 devices)
                this._cleanupOldCaches();
            }
        } catch (error) {
            console.warn('Could not load table list:', error);
        }
    }

    _parseTablesFromOutput(output) {
        // Parse table names from .tables output
        const lines = output.split('\n');
        const tables = [];
        for (const line of lines) {
            const trimmed = (line || '').trim();
            if (!trimmed) continue;
            let name = trimmed;
            // Lines often look like "=> table_name"
            if (name.startsWith('=>')) {
                name = name.slice(2).trim();
            }
            if (name) {
                tables.push(name);
            }
        }
        return tables;
    }


    async _prefetchSchemaIfNeeded(ttlHours = 24, maxTables = 150) {
        try {
            if (!this.deviceUuid) return;
            const url = `/osquery/api/device/${this.deviceUuid}/osquery/schema/prefetch?ttl_hours=${encodeURIComponent(ttlHours)}&max_tables=${encodeURIComponent(maxTables)}`;
            const res = await fetch(url, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': this.csrfToken
                }
            });
            const data = await res.json().catch(() => ({}));
            debug.log('Schema prefetch:', { ok: res.ok, data });
        } catch (err) {
            console.warn('Schema prefetch failed:', err);
        }
    }


    _detectPlatform(tables) {
        // Detect OS platform from table names
        if (tables.some(t => t.includes('windows_') || t === 'registry' || t === 'ie_extensions')) {
            return 'Windows';
        }
        if (tables.some(t => t.includes('apt_') || t.includes('systemd_') || t === 'deb_packages')) {
            return 'Linux';
        }
        if (tables.some(t => t.includes('airport_') || t.includes('homebrew_') || t === 'apps')) {
            return 'macOS';
        }
        return 'Unknown';
    }

    _cleanupOldCaches() {
        const MAX_CACHED_DEVICES = 5;
        const cacheKeys = Object.keys(localStorage)
            .filter(key => key.startsWith('osquery_tables_'));

        if (cacheKeys.length > MAX_CACHED_DEVICES) {
            // Get cache data with timestamps
            const cacheData = cacheKeys.map(key => {
                try {
                    return {
                        key: key,
                        data: JSON.parse(localStorage.getItem(key))
                    };
                } catch (e) {
                    return { key: key, data: { cachedAt: 0 } };
                }
            }).sort((a, b) => a.data.cachedAt - b.data.cachedAt);

            // Remove oldest caches
            cacheData.slice(0, cacheKeys.length - MAX_CACHED_DEVICES)
                .forEach(item => localStorage.removeItem(item.key));

            debug.log(`Cleaned up ${cacheKeys.length - MAX_CACHED_DEVICES} old table caches`);
        }
    }

    _handleTabCompletion() {
        const input = this.input.value;
        const cursorPos = this.input.selectionStart;
        const beforeCursor = input.substring(0, cursorPos);
        const afterCursor = input.substring(cursorPos);

        // Simple table name completion
        const words = beforeCursor.split(/\s+/);
        const lastWord = words[words.length - 1];

        if (lastWord && this.availableTables.length > 0) {
            const matches = this.availableTables.filter(table =>
                table.toLowerCase().startsWith(lastWord.toLowerCase())
            );

            if (matches.length === 1) {
                const completion = matches[0];
                const newValue = beforeCursor.substring(0, beforeCursor.length - lastWord.length) +
                               completion + afterCursor;
                this.input.value = newValue;
                this.input.setSelectionRange(
                    cursorPos - lastWord.length + completion.length,
                    cursorPos - lastWord.length + completion.length
                );
            } else if (matches.length > 1) {
                // Show available completions
                const completionList = matches.join(', ');
                this._addToOutput(`<div class="text-info small">Available tables: ${completionList}</div>`);
            }
        }
    }

    _setLoading(loading) {
        this.submitButton.disabled = loading;
        this.input.disabled = loading;

        if (loading) {
            this.submitButton.innerHTML = '<i class="fas fa-spinner fa-spin"></i>';
        } else {
            this.submitButton.innerHTML = '<i class="fas fa-play"></i>';
        }
    }

    _escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    async _loadTerminalHistory() {
        try {
            const response = await fetch(`/osquery/api/device/${this.deviceUuid}/terminal_history`);
            const data = await response.json();

            if (response.ok && data.history && data.history.length > 0) {
                debug.log(`Loading ${data.history.length} terminal history messages`);

                // Restore last 20 messages (10 query/result pairs)
                data.history.slice(-20).forEach(msg => {
                    if (msg.is_query) {
                        // Display query
                        this._addToOutput(`<div class="terminal-command">osquery> ${this._escapeHtml(msg.content)}</div>`);
                    } else {
                        // Display result
                        try {
                            const result = JSON.parse(msg.content);
                            this._displayResult(result);
                        } catch (e) {
                            // Fallback for non-JSON content
                            this._addToOutput(`<div class="terminal-result"><pre>${this._escapeHtml(msg.content)}</pre></div>`);
                        }
                    }
                });

                debug.log('Terminal history restored');

                // Ensure scroll to bottom after all history is loaded
                // The offcanvas animation takes ~300ms, so we need to wait for that

                // Use setTimeout with longer delay to account for offcanvas animation
                setTimeout(() => {
                    debug.log('Attempting scroll after 350ms delay');
                    this._scrollToBottom();
                }, 350);

                // Also try after paint
                requestAnimationFrame(() => {
                    setTimeout(() => {
                        debug.log('Attempting scroll in next frame');
                        this._scrollToBottom();
                    }, 50);
                });
            }
        } catch (error) {
            debug.log('No terminal history available or error loading:', error);
        }
    }

    _scrollToBottom() {
        // Scroll the container to the bottom
        if (this.container) {
            // Check if container is visible and has content
            const height = this.container.scrollHeight;
            const isVisible = height > 0;

            debug.log('Scrolling terminal to bottom. Container height:', height, 'Is visible:', isVisible, 'Current scroll:', this.container.scrollTop);

            if (isVisible) {
                this.container.scrollTop = height;
                debug.log('After scroll:', this.container.scrollTop);
            } else {
                debug.log('Container not yet visible, deferring scroll');
                // Try again after a delay if container isn't visible yet
                setTimeout(() => {
                    const newHeight = this.container.scrollHeight;
                    if (newHeight > 0) {
                        debug.log('Container now visible, scrolling. Height:', newHeight);
                        this.container.scrollTop = newHeight;
                    }
                }, 200);
            }
        }
    }

    _createTableDropdown() {
        if (!this.tablesLoaded || this.availableTables.length === 0) {
            return null;
        }

        const container = document.createElement('div');
        container.className = 'osq-dropdown-inner d-flex align-items-center gap-2';

        // Platform badge
        if (this.devicePlatform) {
            const badge = document.createElement('span');
            badge.className = 'badge bg-info';
            badge.textContent = this.devicePlatform;
            container.appendChild(badge);
        }

        // Dropdown
        const dropdown = document.createElement('select');
        dropdown.className = 'form-select form-select-sm w-100';
        dropdown.innerHTML = `
            <option value="">Quick Queries (${this.availableTables.length} tables available)</option>
            ${this.availableTables.map(table =>
                `<option value="${this._escapeHtml(table)}">SELECT * FROM ${this._escapeHtml(table)} LIMIT 10;</option>`
            ).join('')}
        `;

        dropdown.addEventListener('change', (e) => {
            if (e.target.value) {
                const tbl = e.target.value.replace(/^=>\s*/, '');
                this.input.value = `SELECT * FROM ${tbl} LIMIT 10;`;
                this.input.focus();
                // Reset dropdown
                e.target.selectedIndex = 0;
            }
        });

        container.appendChild(dropdown);
        return container;
    }


    _ensureQuickBar() {
        if (this.quickBarInitialized) return;
        if (!this.form) return;
        const quickBar = document.createElement('div');
        quickBar.id = 'osqueryQuickBar';
        quickBar.className = 'osq-quickbar mb-2';

        const chipsDiv = document.createElement('div');
        chipsDiv.id = 'osqueryChips';
        chipsDiv.className = 'osq-chips-scroll';

        const recentDiv = document.createElement('div');
        recentDiv.id = 'osqueryRecentChips';
        recentDiv.className = 'osq-recent';

        const dropdownContainer = document.createElement('div');
        dropdownContainer.id = 'tableDropdownContainer';
        dropdownContainer.className = 'osq-dropdown';

        const askBtn = document.createElement('button');
        askBtn.type = 'button';
        askBtn.id = 'askEnglishBtn';
        askBtn.className = 'btn btn-sm btn-outline-primary osq-ask-btn';
        askBtn.innerHTML = '<i class="fas fa-language me-1"></i>Ask in English';
        askBtn.addEventListener('click', () => this._handleAskEnglish());

        // Order for grid layout: row1 -> dropdown + ask btn, row2 -> chips, row3 -> recent
        quickBar.appendChild(dropdownContainer);
        quickBar.appendChild(askBtn);
        quickBar.appendChild(chipsDiv);
        quickBar.appendChild(recentDiv);

        this.form.insertBefore(quickBar, this.form.firstChild);
        this.quickBarInitialized = true;
        this._refreshChips();
    }

    _refreshChips() {
        if (!this.quickBarInitialized) return;
        const chipsDiv = document.getElementById('osqueryChips');
        if (!chipsDiv) return;
        chipsDiv.innerHTML = '';

        const addChip = (label, query) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-sm btn-outline-secondary';
            btn.textContent = label;
            btn.addEventListener('click', () => this.executeQuery(query));
            chipsDiv.appendChild(btn);
        };

        const tables = this.availableTables || [];
        const has = (name) => tables.some(t => (t || '').toLowerCase() === name.toLowerCase());
        const firstAvailable = (names) => names.find(n => has(n));

        // Common chips
        addChip('Processes', "SELECT pid, name, cmdline FROM processes LIMIT 25;");

        // Services/Units/Launchd
        const svc = firstAvailable(['services', 'systemd_units', 'launchd']);
        if (svc === 'services') addChip('Services', "SELECT name, status, start_type, path FROM services LIMIT 25;");
        else if (svc === 'systemd_units') addChip('Services', "SELECT name, load_state, active_state, sub_state FROM systemd_units LIMIT 25;");
        else if (svc === 'launchd') addChip('Services', "SELECT label, program FROM launchd LIMIT 25;");

        // Installed software/packages
        const sw = firstAvailable(['programs', 'deb_packages', 'rpm_packages', 'apps', 'homebrew_packages']);
        if (sw === 'programs') addChip('Installed Software', "SELECT name, version, install_date FROM programs LIMIT 50;");
        else if (sw === 'deb_packages') addChip('Installed Packages', "SELECT name, version FROM deb_packages LIMIT 50;");
        else if (sw === 'rpm_packages') addChip('Installed Packages', "SELECT name, version, release FROM rpm_packages LIMIT 50;");
        else if (sw === 'apps') addChip('Installed Apps', "SELECT name, bundle_identifier, path FROM apps LIMIT 50;");
        else if (sw === 'homebrew_packages') addChip('Brew Packages', "SELECT name, version FROM homebrew_packages LIMIT 50;");

        if (has('logged_in_users')) addChip('Logged-in Users', "SELECT * FROM logged_in_users;");
        if (has('listening_ports')) addChip('Listening Ports', "SELECT pid, address, port, protocol, family FROM listening_ports LIMIT 50;");

        const sched = firstAvailable(['windows_tasks', 'crontab', 'launchd']);
        if (sched === 'windows_tasks') addChip('Scheduled Tasks', "SELECT name, path, enabled, last_run_time FROM windows_tasks LIMIT 50;");
        else if (sched === 'crontab') addChip('Crontab', "SELECT * FROM crontab LIMIT 50;");
        else if (sched === 'launchd') addChip('Launchd Jobs', "SELECT name, label, program FROM launchd LIMIT 50;");

        this._updateRecentChips();
    }

    _updateRecentChips() {
        const recentDiv = document.getElementById('osqueryRecentChips');
        if (!recentDiv) return;
        recentDiv.innerHTML = '';

        const unique = [];
        for (let i = this.commandHistory.length - 1; i >= 0 && unique.length < 3; i--) {
            const q = this.commandHistory[i];
            if (typeof q === 'string' && q.trim() && !unique.includes(q)) {
                unique.push(q);
            }
        }
        if (unique.length === 0) return;

        const label = document.createElement('span');
        label.className = 'text-muted small me-1';
        label.textContent = 'Recent:';
        recentDiv.appendChild(label);

        unique.forEach(q => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'btn btn-sm btn-outline-light';
            btn.textContent = q.length > 30 ? (q.slice(0, 27) + '...') : q;
            btn.title = q;
            btn.addEventListener('click', () => this.executeQuery(q));
            recentDiv.appendChild(btn);
        });
    }

    _handleAskEnglish() {
        this._openPlainEnglishModal();
    }


    _ensurePlainEnglishModal() {
        if (this._nl2sqlModalEl) return;
        const modalEl = document.createElement('div');
        modalEl.id = 'nl2sqlModal';
        modalEl.className = 'modal fade';
        modalEl.tabIndex = -1;
        modalEl.setAttribute('aria-hidden', 'true');
        modalEl.innerHTML = `
            <div class="modal-dialog modal-dialog-centered">
              <div class="modal-content glass-modal">
                <div class="modal-header glass-header">
                  <h5 class="modal-title"><i class="fas fa-language me-2"></i>Ask in English</h5>
                  <button type="button" class="btn-close" data-bs-dismiss="modal" aria-label="Close"></button>
                </div>
                <div class="modal-body glass-body">
                  <div class="mb-3">
                    <label class="form-label small">Describe what you want to query</label>
                    <textarea id="nl2sqlText" class="form-control glass-input" rows="3" placeholder="e.g., who is logged in, installed software"></textarea>
                    <small class="form-text text-muted">Only SELECT statements, CTEs (WITH ...) and meta commands (.tables/.schema) are allowed</small>
                  </div>
                  <div id="nl2sqlError" class="text-warning small d-none"></div>
                  <div class="mb-2 d-flex align-items-center justify-content-between">
                    <label class="form-label small mb-0">Generated SQL</label>
                    <small class="text-muted">Editable before running</small>
                  </div>
                  <textarea id="nl2sqlSql" class="form-control glass-input font-monospace" rows="5" placeholder="SQL will appear here..."></textarea>
                </div>
                <div class="modal-footer glass-footer">
                  <button id="nl2sqlGenerateBtn" type="button" class="btn btn-primary">
                    <span class="gen-label">Generate SQL</span>
                    <span class="spinner-border spinner-border-sm d-none" role="status" aria-hidden="true"></span>
                  </button>
                  <button id="nl2sqlInsertBtn" type="button" class="btn btn-outline-secondary" disabled>Insert</button>
                  <button id="nl2sqlRunBtn" type="button" class="btn btn-success" disabled>Run</button>
                </div>
              </div>
            </div>`;
        document.body.appendChild(modalEl);
        this._nl2sqlModalEl = modalEl;
        this._nl2sqlText = modalEl.querySelector('#nl2sqlText');
        this._nl2sqlSql = modalEl.querySelector('#nl2sqlSql');
        this._nl2sqlError = modalEl.querySelector('#nl2sqlError');
        this._nl2sqlGenerateBtn = modalEl.querySelector('#nl2sqlGenerateBtn');
        this._nl2sqlInsertBtn = modalEl.querySelector('#nl2sqlInsertBtn');
        this._nl2sqlRunBtn = modalEl.querySelector('#nl2sqlRunBtn');

        if (window.bootstrap && window.bootstrap.Modal) {
            this._nl2sqlModal = new bootstrap.Modal(modalEl, { backdrop: true, keyboard: true });
        } else {
            console.warn('Bootstrap Modal not available');
        }
    }

    _openPlainEnglishModal() {
        this._ensurePlainEnglishModal();
        if (!this._nl2sqlModalEl) return;

        // Reset state
        this._nl2sqlText.value = '';
        this._nl2sqlSql.value = '';
        this._nl2sqlError.classList.add('d-none');
        this._nl2sqlInsertBtn.disabled = true;
        this._nl2sqlRunBtn.disabled = true;

        // Wire actions (overwrite to avoid duplicate listeners)
        this._nl2sqlGenerateBtn.onclick = async () => {
            const text = (this._nl2sqlText.value || '').trim();
            if (!text) {
                this._nl2sqlError.textContent = 'Please describe what you want to query.';
                this._nl2sqlError.classList.remove('d-none');
                return;
            }
            this._nl2sqlError.classList.add('d-none');
            const spinner = this._nl2sqlGenerateBtn.querySelector('.spinner-border');
            const label = this._nl2sqlGenerateBtn.querySelector('.gen-label');
            spinner.classList.remove('d-none');
            label.textContent = 'Generating…';
            this._nl2sqlGenerateBtn.disabled = true;
            try {
                const resp = await fetch(`/osquery/api/device/${this.deviceUuid}/osquery/nl2sql`, {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': this.csrfToken
                    },
                    body: JSON.stringify({ text })
                });
                const j = await resp.json();
                if (resp.ok && j && j.sql) {
                    this._nl2sqlSql.value = j.sql;
                    this._nl2sqlInsertBtn.disabled = false;
                    this._nl2sqlRunBtn.disabled = false;
                } else {
                    this._nl2sqlError.textContent = j && j.error ? j.error : 'Failed to translate query';
                    this._nl2sqlError.classList.remove('d-none');
                }
            } catch (e) {
                this._nl2sqlError.textContent = e.message || String(e);
                this._nl2sqlError.classList.remove('d-none');
            } finally {
                spinner.classList.add('d-none');
                label.textContent = 'Generate SQL';
                this._nl2sqlGenerateBtn.disabled = false;
            }
        };

        this._nl2sqlInsertBtn.onclick = () => {
            const sql = (this._nl2sqlSql.value || '').trim();
            if (!sql) return;
            this.input.value = sql;
            this.input.focus();
            if (this._nl2sqlModal) this._nl2sqlModal.hide();
        };

        this._nl2sqlRunBtn.onclick = () => {
            const sql = (this._nl2sqlSql.value || '').trim();
            if (!sql) return;
            this.executeQuery(sql);
            if (this._nl2sqlModal) this._nl2sqlModal.hide();
        };

        // Keyboard shortcuts
        this._nl2sqlSql.onkeydown = (e) => {
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                e.preventDefault();
                this._nl2sqlRunBtn.click();
            }
        };

        if (this._nl2sqlModal) {
            this._nl2sqlModal.show();
            setTimeout(() => this._nl2sqlText.focus(), 200);
        }
    }

    // Public methods
    clear() {
        const welcome = this.container.querySelector('.terminal-welcome');
        this.container.innerHTML = '';
        if (welcome) {
            this.container.appendChild(welcome.cloneNode(true));
        }
    }

    executeQuery(query) {
        this.input.value = query;
        this._executeCommand();
    }
}

// Global terminal instance
let osqueryTerminal = null;

// Initialize terminal when DOM is ready
document.addEventListener('DOMContentLoaded', function() {
    // Wait for chat offcanvas to be available (unified component)
    const chatOffcanvas = document.getElementById('chatOffcanvas');
    debug.log('Chat offcanvas found:', !!chatOffcanvas);

    if (chatOffcanvas) {
        // Initialize when offcanvas is first opened
        chatOffcanvas.addEventListener('shown.bs.offcanvas', function() {
            if (!osqueryTerminal) {
                // Get device info from the page context
                const deviceUuid = chatOffcanvas.dataset.deviceUuid ||
                                 document.querySelector('[data-device-uuid]')?.dataset.deviceUuid;
                const entityName = chatOffcanvas.dataset.entityName ||
                                 document.querySelector('[data-entity-name]')?.dataset.entityName;

                debug.log('Initializing terminal with:', { deviceUuid, entityName });

                if (deviceUuid) {
                    osqueryTerminal = new OsqueryTerminal({
                        deviceUuid: deviceUuid,
                        entityName: entityName
                    });
                    debug.log('Terminal initialized successfully');

                    // Inject table dropdown after tables are loaded
                    setTimeout(() => {
                        const dropdownContainer = document.getElementById('tableDropdownContainer');
                        if (dropdownContainer && osqueryTerminal.tablesLoaded) {
                            const dropdown = osqueryTerminal._createTableDropdown();
                            if (dropdown) {
                                dropdownContainer.innerHTML = '';
                                dropdownContainer.appendChild(dropdown);
                                debug.log('Table dropdown injected');
                            }
                        }
                    }, 1500);  // Wait for tables to load
                } else {
                    console.error('No device UUID found for terminal initialization');
                }
            } else {
                // Terminal already initialized - just scroll to bottom when offcanvas is shown again
                if (osqueryTerminal) {
                    // Wait for offcanvas animation to complete (~300ms)
                    setTimeout(() => {
                        debug.log('Offcanvas shown, scrolling to bottom');
                        osqueryTerminal._scrollToBottom();
                    }, 350);
                }
            }
        }, { once: false });
    }
});

// Global function for clearing terminal (called from template)
function clearTerminal() {
    if (osqueryTerminal) {
        osqueryTerminal.clear();
    }
}
