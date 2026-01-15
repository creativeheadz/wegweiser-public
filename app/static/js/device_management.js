document.addEventListener('DOMContentLoaded', function() {
    $.ajaxSetup({ cache: false });

    function initializeTables() {
        try {
            if ($.fn.DataTable.isDataTable('#example')) {
                $('#example').DataTable().destroy();
            }
            $('#example').DataTable();

            if ($.fn.DataTable.isDataTable('#example2')) {
                $('#example2').DataTable().destroy();
            }
            var table = $('#example2').DataTable({
                lengthChange: true,
                pageLength: 100, // Default number of records per page
                lengthMenu: [[5, 10, 25, 50, 100, -1], [5, 10, 25, 50, 100, "All"]],
                buttons: ['copy', 'excel', 'pdf', 'print']
            });
            table.buttons().container().appendTo('#example2_wrapper .col-md-6:eq(0)');

            // Restore column visibility preferences
            let savedPreferences = JSON.parse(localStorage.getItem('columnPreferences')) || {};
            document.querySelectorAll('.column-toggle').forEach(function(checkbox, index) {
                let columnName = checkbox.value;
                let columnIndex = index; // Use the checkbox index to find the correct column
                let isVisible = savedPreferences[columnName] ?? checkbox.checked;

                checkbox.checked = isVisible;
                table.column(columnIndex).visible(isVisible);

                // Toggle column visibility on checkbox change
                checkbox.addEventListener('change', function() {
                    table.column(columnIndex).visible(this.checked);
                });
            });
        } catch (error) {
            console.error('Error initializing DataTables:', error);
        }
    }

    initializeTables();

    document.getElementById('save-column-preferences')?.addEventListener('click', function() {
        let preferences = {};
        document.querySelectorAll('.column-toggle').forEach(function(checkbox) {
            preferences[checkbox.value] = checkbox.checked;
        });
        localStorage.setItem('columnPreferences', JSON.stringify(preferences));
        showNotification('success', 'Preferences saved!');
    });

    function initializeAIChat(deviceUuid) {
        const chatForm = document.getElementById(`chatForm-${deviceUuid}`);
        const chatInput = document.getElementById(`chatInput-${deviceUuid}`);
        const chatContainer = document.getElementById(`chatContainer-${deviceUuid}`);

        if (chatForm && chatInput && chatContainer) {
            chatForm.addEventListener('submit', function(e) {
                e.preventDefault();
                const message = chatInput.value.trim();
                if (message) {
                    addChatMessage(chatContainer, 'You', message);
                    chatInput.value = '';

                    fetch(`/ai/device/${deviceUuid}/chat`, {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                        },
                        body: JSON.stringify({ message: message }),
                    })
                    .then(response => {
                        if (!response.ok) {
                            throw new Error('Network response was not ok');
                        }
                        return response.json();
                    })
                    .then(data => {
                        addChatMessage(chatContainer, 'AI', data.response);
                    })
                    .catch(error => {
                        console.error('Error:', error);
                        addChatMessage(chatContainer, 'AI', 'Sorry, there was an error processing your request.');
                    });
                }
            });
        }
    }

    function addChatMessage(container, sender, message, isAi = false) {
        const messageElement = document.createElement('div');
        messageElement.className = isAi ? 'ai-message chat-content-leftside' : 'user-message chat-content-rightside';
        messageElement.innerHTML = `
            <div class="d-flex">
                ${isAi ? '<img src="assets/images/avatars/03.png" width="48" height="48" class="rounded-circle" alt="" />' : ''}
                <div class="flex-grow-1 ${isAi ? 'ms-2' : 'me-2'}">
                    <p class="mb-0 chat-time ${isAi ? '' : 'text-end'}">${sender}, ${new Date().toLocaleTimeString()}</p>
                    <p class="${isAi ? 'chat-left-msg' : 'chat-right-msg'}">${message}</p>
                </div>
            </div>
        `;
        container.appendChild(messageElement);
        container.scrollTop = container.scrollHeight;
    }

    function removeDeviceFromUI(deviceUuid) {
        const table = $('#example2').DataTable();
        const row = table.row(`#device-row-${deviceUuid}`);
        if (row) {
            row.remove().draw();
        }
    
        const deviceElements = document.querySelectorAll(`[id$="-${deviceUuid}"]`);
        deviceElements.forEach(el => el.remove());
    
        const storedDevices = JSON.parse(localStorage.getItem('devices') || '[]');
        const updatedDevices = storedDevices.filter(device => device.uuid !== deviceUuid);
        localStorage.setItem('devices', JSON.stringify(updatedDevices));
    
        clearInterval(window.healthScoreIntervals[deviceUuid]);
        delete window.healthScoreIntervals[deviceUuid];
    
        debug.log(`Device ${deviceUuid} removed from UI and local storage`);
    }

    function showNotification(type, message) {
        var notification = document.createElement('div');
        notification.className = `alert alert-${type} alert-dismissible fade show`;
        notification.innerHTML = `
            <strong>${type.charAt(0).toUpperCase() + type.slice(1)}!</strong> ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.getElementById('notification-area')?.appendChild(notification);

        setTimeout(function() {
            notification.remove();
        }, 3000);
    }

    function initTagsInput(deviceUuid) {
        $(`#device-tags-${deviceUuid}`).tagsinput({
            itemValue: 'uuid',
            itemText: 'value'
        }).on('itemAdded', function(event) {
            $.ajax({
                url: '/tags/assign',
                method: 'POST',
                data: JSON.stringify({ tagvalue: event.item, tenantuuid: deviceUuid }),
                contentType: 'application/json',
                success: function(response) {
                    showNotification('success', 'Tag assigned successfully!');
                },
                error: function(error) {
                    showNotification('danger', 'Failed to assign tag.');
                }
            });
        });
    }

    document.querySelectorAll('[id^="device-tags-"]').forEach(el => {
        const deviceUuid = el.id.split('-').pop();
        initTagsInput(deviceUuid);
    });

    function loadChatHistory(deviceUuid) {
        fetch(`/ai/device/${deviceUuid}/chat_history`)
            .then(response => {
                if (!response.ok) {
                    throw new Error('Network response was not ok');
                }
                return response.json();
            })
            .then(data => {
                const chatContainer = document.getElementById(`chatContainer-${deviceUuid}`);
                if (chatContainer) {
                    chatContainer.innerHTML = '';
                    data.messages.forEach(message => {
                        addChatMessage(chatContainer, message.is_ai ? 'AI' : 'You', message.content);
                    });
                }
            })
            .catch(error => console.error('Error loading chat history:', error));
    }

    document.querySelectorAll('[id^="chatForm-"]').forEach(form => {
        const deviceUuid = form.id.substring(9);
        form.addEventListener('focus', function() {
            if (!this.dataset.historyLoaded) {
                loadChatHistory(deviceUuid);
                this.dataset.historyLoaded = 'true';
            }
        }, true);
    });
});
