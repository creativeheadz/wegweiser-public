document.addEventListener('DOMContentLoaded', function() {
    debug.log('DOM fully loaded and parsed');

    // Open delete confirmation modal for organisations
    document.querySelectorAll('.delete-organisation').forEach(button => {
        button.addEventListener('click', function() {
            const orgUUID = button.getAttribute('data-orguuid');
            document.getElementById('deleteOrgUUID').value = orgUUID;
            const deleteModal = new bootstrap.Modal(document.getElementById('deleteOrganisationModal'));
            deleteModal.show();
        });
    });

    // Handle delete confirmation for organisations
    document.getElementById('confirmDelete').addEventListener('click', function() {
        const orgUUID = document.getElementById('deleteOrgUUID').value;
        const deleteFeedback = document.getElementById('deleteFeedback');

        fetch('/organisations/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ orguuid: orgUUID }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                deleteFeedback.classList.remove('d-none', 'alert-success');
                deleteFeedback.classList.add('alert-danger');
                deleteFeedback.textContent = data.error;
            } else {
                deleteFeedback.classList.remove('d-none', 'alert-danger');
                deleteFeedback.classList.add('alert-success');
                deleteFeedback.textContent = data.success;

                setTimeout(() => {
                    location.reload();
                }, 2000);
            }
        })
        .catch(error => {
            deleteFeedback.classList.remove('d-none', 'alert-success');
            deleteFeedback.classList.add('alert-danger');
            deleteFeedback.textContent = 'Error: ' + error;
        });
    });

    // Fetch organisations for creating groups
    fetch('/groups/getorgs', {
        headers: {
            'Accept': 'application/json'
        }
    })
    .then(response => {
        if (!response.ok) {
            throw new Error('Network response was not ok');
        }
        return response.json();
    })
    .then(data => {
        const orgSelect = document.getElementById('groupOrgUUID');
        orgSelect.innerHTML = ''; // Clear existing options
        data.organisations.forEach(org => {
            const option = document.createElement('option');
            option.value = org.orguuid;
            option.textContent = org.orgname;
            orgSelect.appendChild(option);
        });
    })
    .catch(error => console.error('Error fetching organisations:', error));

    // Add event listener for create group form
    document.getElementById('createGroupForm').addEventListener('submit', function(event) {
        event.preventDefault(); // Prevent default form submission

        const orguuid = document.getElementById('groupOrgUUID').value;
        const groupname = document.getElementById('groupNameInput').value;

        debug.log('Creating group with data:', { orguuid, groupname }); // Log data

        fetch('/groups/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ orguuid: orguuid, groupname: groupname })
        })
        .then(response => response.json())
        .then(data => {
            const feedback = document.createElement('div');
            feedback.className = 'mt-3';

            if (data.success) {
                feedback.classList.add('alert', 'alert-success');
                feedback.textContent = data.success;
                document.getElementById('createGroupForm').appendChild(feedback);

                setTimeout(() => {
                    const createModal = bootstrap.Modal.getInstance(document.getElementById('createGroupModal'));
                    createModal.hide();
                    location.reload();
                }, 2000);
            } else {
                feedback.classList.add('alert', 'alert-danger');
                feedback.textContent = data.error;
                document.getElementById('createGroupForm').appendChild(feedback);
            }
        })
        .catch(error => {
            const feedback = document.createElement('div');
            feedback.classList.add('alert', 'alert-danger', 'mt-3');
            feedback.textContent = 'Error: ' + error;
            document.getElementById('createGroupForm').appendChild(feedback);
        });
    });

    // Add event listener for create organisation form
    document.getElementById('createOrganisationForm').addEventListener('submit', function(event) {
        event.preventDefault(); // Prevent default form submission

        const orgname = document.getElementById('orgNameInput').value;
        const groupname = document.getElementById('OrggroupNameInput').value;

        debug.log('Sending data:', { orgname: orgname, groupname: groupname });  // Log the data being sent

        fetch('/organisations/add', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({ orgname: orgname, groupname: groupname }) // Send JSON body
        })
        .then(response => {
            debug.log('Received response:', response);  // Log the response
            if (!response.ok) {
                return response.json().then(err => { throw err });
            }
            return response.json();
        })
        .then(data => {
            debug.log('Received data:', data);  // Log the received data
            const feedbackContainer = document.getElementById('createOrganisationFormFeedback');
            feedbackContainer.innerHTML = ''; // Clear any existing feedback

            const feedback = document.createElement('div');
            feedback.className = 'mt-3';

            if (data.success) {
                feedback.classList.add('alert', 'alert-success');
                feedback.textContent = data.success;
                feedbackContainer.appendChild(feedback);

                setTimeout(() => {
                    const createModal = bootstrap.Modal.getInstance(document.getElementById('createOrganisationModal'));
                    createModal.hide();
                    location.reload();
                }, 2000);
            } else {
                feedback.classList.add('alert', 'alert-danger');
                feedback.textContent = data.error;
                feedbackContainer.appendChild(feedback);
            }
        })
        .catch(error => {
            console.error('Error:', error);  // Log the error
            const feedbackContainer = document.getElementById('createOrganisationFormFeedback');
            feedbackContainer.innerHTML = ''; // Clear any existing feedback

            const feedback = document.createElement('div');
            feedback.classList.add('alert', 'alert-danger', 'mt-3');
            feedback.textContent = 'Error: ' + (error.message || JSON.stringify(error));
            feedbackContainer.appendChild(feedback);
        });
    });

    // Fetch groups when the groups tab is shown
    document.getElementById('groups-tab').addEventListener('shown.bs.tab', function () {
        fetchGroups();
    });

    // Fetch and display devices when the devices tab is selected
    document.getElementById('devices-tab').addEventListener('shown.bs.tab', function () {
        fetchDevices();
    });

    function fetchGroups() {
        debug.log('Fetching groups...');
        fetch('/organisations/groups')
            .then(response => {
                if (!response.ok) {
                    throw new Error(`Network response was not ok: ${response.statusText}`);
                }
                return response.json();
            })
            .then(data => {
                debug.log('Groups data received:', data);
                if (data.organisations) {
                    // Transform the object into an array
                    const organisations = Object.keys(data.organisations).map(orgUUID => {
                        return {
                            orguuid: orgUUID,
                            ...data.organisations[orgUUID]
                        };
                    });
                    populateOrganisationFilter(organisations);
                    populateGroupsTable(organisations);
                } else {
                    console.error('Error fetching groups:', data.error);
                }
            })
            .catch(error => console.error('Error fetching groups:', error));
    }

    function populateOrganisationFilter(organisations) {
        debug.log('Populating organisation filter...');
        const orgFilter = document.getElementById('orgFilterDropdown');
        if (!orgFilter) {
            console.error('orgFilterDropdown element not found');
            return;
        }
        orgFilter.innerHTML = '<option value="">All Organisations</option>'; // Clear existing options

        organisations.forEach(org => {
            const option = document.createElement('option');
            option.value = org.orguuid;
            option.textContent = org.orgname;
            orgFilter.appendChild(option);
        });

        orgFilter.addEventListener('change', function() {
            const selectedOrgUUID = this.value;
            filterGroupsByOrganisation(selectedOrgUUID);
        });
    }

    function populateGroupsTable(organisations) {
        debug.log('Populating groups table...');
        const tbody = document.getElementById('groupsTableBody');
        if (!tbody) {
            console.error('groupsTableBody element not found');
            return;
        }
        tbody.innerHTML = ''; // Clear existing rows

        organisations.forEach(org => {
            const orgRow = document.createElement('tr');
            orgRow.innerHTML = `<td rowspan="${org.groups.length + 1}">${org.orgname}</td>`;
            tbody.appendChild(orgRow);

            org.groups.forEach(group => {
                const groupRow = document.createElement('tr');
                groupRow.innerHTML = `
                    <td>${group.groupname}</td>
                    <td>
                        <button class="btn btn-danger btn-sm" data-groupuuid="${group.groupuuid}" data-bs-toggle="modal" data-bs-target="#deleteGroupModal">Delete</button>
                    </td>
                `;
                tbody.appendChild(groupRow);
            });
        });

        // Add event listeners to delete buttons
        document.querySelectorAll('.btn-danger[data-groupuuid]').forEach(button => {
            button.addEventListener('click', function() {
                const groupUUID = button.getAttribute('data-groupuuid');
                document.getElementById('deleteGroupUUID').value = groupUUID;
            });
        });
    }
    function fetchDeviceDetails(deviceuuid) {
        fetch(`/devices/details/${deviceuuid}`)
            .then(response => response.text())
            .then(data => {
                const deviceDetailsContent = document.getElementById('deviceDetailsContent');
                deviceDetailsContent.innerHTML = data; // Set the fetched HTML as the modal content
                const deviceDetailsModal = new bootstrap.Modal(document.getElementById('deviceDetailsModal'));
                deviceDetailsModal.show();
            })
            .catch(error => {
                console.error('Error fetching device details:', error);
            });
    }

    

    function translateKey(key) {
        const translations = {
            'created_at': 'Created At',
            'devicename': 'Device Name',
            'group': 'Group',
            'hardwareinfo': 'Hardware Info',
            'organisation': 'Organisation',
            'battery_installed': 'Battery Installed',
            'last_json': 'Last JSON',
            'last_update': 'Last Update',
            'on_mains_power': 'On Mains Power',
            'percent_charged': 'Percent Charged',
            'secs_remaining': 'Seconds Remaining',
            'drive_free': 'Drive Free',
            'drive_free_percentage': 'Drive Free Percentage',
            'drive_name': 'Drive Name',
            'drive_total': 'Drive Total',
            'drive_used': 'Drive Used',
            'drive_used_percentage': 'Drive Used Percentage',
            'available_memory': 'Available Memory',
            'cache_memory': 'Cache Memory',
            'free_memory': 'Free Memory',
            'info': 'Info'
        };
        return translations[key] || key;
    }
    
    function formatData(data, level = 0) {
        let formatted = '';
        const indent = ' '.repeat(level * 2);
        for (const key in data) {
            if (typeof data[key] === 'object' && data[key] !== null) {
                formatted += `${indent}${translateKey(key)}:\n`;
                formatted += formatData(data[key], level + 1);
            } else {
                formatted += `${indent}${translateKey(key)}: ${data[key]}\n`;
            }
        }
        return formatted;
    }
    
    function displayDeviceDetails(data) {
        const deviceDetailsContent = document.getElementById('deviceDetailsContent');
        const deviceDetailsModalLabel = document.getElementById('deviceDetailsModalLabel');
        
        // Set the modal title
        if (data.device && data.device.devicename) {
            deviceDetailsModalLabel.textContent = `Device Details for ${data.device.devicename}`;
        } else {
            deviceDetailsModalLabel.textContent = 'Device Details';
        }
        
        // Format and set the device details content
        deviceDetailsContent.textContent = formatData(data);
    }
    
    // This function will be used to rebind event listeners after populating the table
    function bindViewButtons() {
        document.querySelectorAll('.view-device').forEach(button => {
            button.addEventListener('click', function() {
                const deviceuuid = this.getAttribute('data-deviceuuid');
                if (deviceuuid) {
                    fetchDeviceDetails(deviceuuid);
                } else {
                    console.error('Device UUID is not defined');
                }
            });
        });
    }
    
    // Modify the existing populateDevicesTable function to call bindViewButtons after populating the table
    function populateDevicesTable(organisations) {
        const tbody = document.getElementById('deviceTableBody');
        tbody.innerHTML = ''; // Clear existing rows
    
        organisations.forEach(org => {
            org.groups.forEach(group => {
                group.devices.forEach(device => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${org.orgname}</td>
                        <td>${group.groupname}</td>
                        <td>${device.devicename}</td>
                        <td>
                            <button class="btn btn-primary btn-sm view-device" data-deviceuuid="${device.deviceuuid}">View</button>
                            <button class="btn btn-danger btn-sm delete-device" data-deviceuuid="${device.deviceuuid}" data-devicename="${device.devicename}" data-bs-toggle="modal" data-bs-target="#deleteDeviceModal">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            });
        });
    
        // Bind the view buttons after populating the table
        bindViewButtons();
    }
    
    // Call fetchDevices initially to load devices data when the page loads
    fetchDevices();
    
    function filterGroupsByOrganisation(orgUUID) {
        fetch('/organisations/groups')
            .then(response => response.json())
            .then(data => {
                if (data.organisations) {
                    const organisations = Object.keys(data.organisations).map(orgUUID => {
                        return {
                            orguuid: orgUUID,
                            ...data.organisations[orgUUID]
                        };
                    });
                    const filteredOrgs = orgUUID ? organisations.filter(org => org.orguuid === orgUUID) : organisations;
                    populateGroupsTable(filteredOrgs);
                } else {
                    console.error('Error fetching groups:', data.error);
                }
            })
            .catch(error => console.error('Error fetching groups:', error));
    }

    // Handle delete confirmation for groups
    document.getElementById('confirmGroupDelete').addEventListener('click', function() {
        const groupUUID = document.getElementById('deleteGroupUUID').value;
        const deleteFeedback = document.getElementById('deleteGroupFeedback');

        fetch('/organisations/delete_group', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ groupuuid: groupUUID }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.error) {
                deleteFeedback.classList.remove('d-none', 'alert-success');
                deleteFeedback.classList.add('alert-danger');
                deleteFeedback.textContent = data.error;
            } else {
                deleteFeedback.classList.remove('d-none', 'alert-danger');
                deleteFeedback.classList.add('alert-success');
                deleteFeedback.textContent = data.success;

                setTimeout(() => {
                    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteGroupModal'));
                    deleteModal.hide();
                    fetchGroups();
                }, 2000);
            }
        })
        .catch(error => {
            deleteFeedback.classList.remove('d-none', 'alert-success');
            deleteFeedback.classList.add('alert-danger');
            deleteFeedback.textContent = 'Error: ' + error;
        });
    });

    function fetchDevices() {
        fetch('/devices/grouped')
            .then(response => response.json())
            .then(data => {
                if (data.organisations) {
                    populateDevicesTable(data.organisations);
                } else {
                    console.error('Error fetching devices:', data.error);
                }
            })
            .catch(error => console.error('Error fetching devices:', error));
    }

    function populateDevicesTable(organisations) {
        const tbody = document.getElementById('deviceTableBody');
        tbody.innerHTML = ''; // Clear existing rows
    
        organisations.forEach(org => {
            org.groups.forEach(group => {
                group.devices.forEach(device => {
                    const row = document.createElement('tr');
                    row.innerHTML = `
                        <td>${org.orgname}</td>
                        <td>${group.groupname}</td>
                        <td>${device.devicename}</td>
                        <td>
                            <button class="btn btn-primary btn-sm view-device" data-deviceuuid="${device.deviceuuid}">View</button>
                            <button class="btn btn-danger btn-sm delete-device" data-deviceuuid="${device.deviceuuid}" data-devicename="${device.devicename}" data-bs-toggle="modal" data-bs-target="#deleteDeviceModal">Delete</button>
                        </td>
                    `;
                    tbody.appendChild(row);
                });
            });
        });
    
        // Bind the view buttons after populating the table
        bindViewButtons();
    
        // Add event listeners for delete buttons
        document.querySelectorAll('.delete-device').forEach(button => {
            button.addEventListener('click', function() {
                const deviceUUID = this.getAttribute('data-deviceuuid');
                const deviceName = this.getAttribute('data-devicename');
                document.getElementById('deleteDeviceUUID').value = deviceUUID;
                document.getElementById('deleteDeviceName').textContent = deviceName;
            });
        });
    }

    // Handle delete confirmation for devices
    document.getElementById('confirmDeleteDevice').addEventListener('click', function() {
        const deviceUUID = document.getElementById('deleteDeviceUUID').value;
        deleteDevice(deviceUUID);
    });

    function deleteDevice(deviceUUID) {
        fetch('/devices/delete', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ deviceuuids: [deviceUUID] }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.message) {
                // Close the modal
                const deleteModal = bootstrap.Modal.getInstance(document.getElementById('deleteDeviceModal'));
                deleteModal.hide();

                // Show success message (you might want to create a function for this)
                showAlert('success', data.message);

                // Refresh the table
                fetchDevices();
            } else {
                console.error('Error deleting device:', data.error);
                showAlert('danger', 'Error deleting device: ' + data.error);
            }
        })
        .catch(error => {
            console.error('Error deleting device:', error);
            showAlert('danger', 'Error deleting device: ' + error);
        });
    }

    // Helper function to show alerts
    function showAlert(type, message) {
        const alertDiv = document.createElement('div');
        alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
        alertDiv.role = 'alert';
        alertDiv.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
        `;
        document.querySelector('.container').prepend(alertDiv);

        // Automatically remove the alert after 5 seconds
        setTimeout(() => {
            alertDiv.remove();
        }, 5000);
    }

    // Initial fetch
    fetchGroups();
    // Uncomment the following line if you want to load devices data when the page initially loads
    // fetchDevices();
});

// Expose deleteGroup to global scope
window.deleteGroup = function(groupuuid) {
    if (confirm('Are you sure you want to delete this group?')) {
        fetch('/organisations/delete_group', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ groupuuid: groupuuid }),
        })
        .then(response => response.json())
        .then(data => {
            if (data.success) {
                fetchGroups(); // Refresh the table
            } else {
                console.error('Error deleting group:', data.error);
            }
        })
        .catch(error => console.error('Error deleting group:', error));
    }
};


 