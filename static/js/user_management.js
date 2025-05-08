/**
 * KEMRI Lab Document Management System
 * User Management JavaScript
 * 
 * This script handles all user management interactions including:
 * - User selection and bulk actions
 * - Search and filtering
 * - Modal interactions
 * - AJAX communication with the backend
 */

document.addEventListener('DOMContentLoaded', function() {
    initializeUserManagement();
});

/**
 * Initialize all user management functionality
 */
function initializeUserManagement() {
    initializeSelectAll();
    initializeUserFilters();
    initializeEditUser();
    initializeDeleteUser();
    initializeResetPassword();
    initializeToggleStatus();
    initializeBulkActions();
}

/**
 * Handle select all functionality
 */
function initializeSelectAll() {
    const selectAllCheckbox = document.getElementById('selectAllUsers');
    const userCheckboxes = document.querySelectorAll('.user-checkbox');
    const bulkActionsBtn = document.getElementById('bulkActionsBtn');
    
    if (!selectAllCheckbox) return;
    
    selectAllCheckbox.addEventListener('change', function() {
        userCheckboxes.forEach(checkbox => {
            checkbox.checked = selectAllCheckbox.checked;
        });
        updateBulkActionsButton();
    });
    
    userCheckboxes.forEach(checkbox => {
        checkbox.addEventListener('change', updateBulkActionsButton);
    });
    
    function updateBulkActionsButton() {
        const checkedCheckboxes = document.querySelectorAll('.user-checkbox:checked');
        if (bulkActionsBtn) {
            bulkActionsBtn.disabled = checkedCheckboxes.length === 0;
        }
        
        // Update the hidden input with selected user IDs
        const selectedUserIds = Array.from(checkedCheckboxes).map(checkbox => checkbox.value);
        const bulkUserIdsField = document.getElementById('bulkUserIds');
        if (bulkUserIdsField) {
            bulkUserIdsField.value = selectedUserIds.join(',');
        }
        
        // Update user lists in modals
        updateSelectedUsersList();
    }
}

/**
 * Handle user search and filtering
 */
function initializeUserFilters() {
    const searchForm = document.getElementById('searchForm');
    const filterRole = document.getElementById('filterRole');
    const filterStatus = document.getElementById('filterStatus');
    
    if (!searchForm) return;
    
    searchForm.addEventListener('submit', function(e) {
        e.preventDefault();
        filterUsers();
    });
    
    if (filterRole) filterRole.addEventListener('change', filterUsers);
    if (filterStatus) filterStatus.addEventListener('change', filterUsers);
    
    function filterUsers() {
        const searchQuery = document.getElementById('searchQuery').value.toLowerCase();
        const roleFilter = filterRole ? filterRole.value.toLowerCase() : '';
        const statusFilter = filterStatus ? filterStatus.value.toLowerCase() : '';
        
        const rows = document.querySelectorAll('#usersTable tbody tr');
        
        rows.forEach(row => {
            const username = row.querySelector('td:nth-child(2)').textContent.toLowerCase();
            const email = row.querySelector('td:nth-child(3)').textContent.toLowerCase();
            const department = row.querySelector('td:nth-child(5)').textContent.toLowerCase();
            const role = row.querySelector('td:nth-child(6)').textContent.toLowerCase();
            const status = row.querySelector('td:nth-child(7)').textContent.toLowerCase();
            
            const matchesSearch = searchQuery === '' || 
                username.includes(searchQuery) || 
                email.includes(searchQuery) || 
                department.includes(searchQuery);
                
            const matchesRole = roleFilter === '' || role.includes(roleFilter);
            const matchesStatus = statusFilter === '' || status.includes(statusFilter);
            
            row.style.display = matchesSearch && matchesRole && matchesStatus ? '' : 'none';
        });
    }
}

/**
 * Handle edit user functionality
 */
function initializeEditUser() {
    const editUserBtns = document.querySelectorAll('.edit-user-btn');
    
    editUserBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const username = this.dataset.username;
            const email = this.dataset.email;
            const phone = this.dataset.phone;
            const department = this.dataset.department;
            const role = this.dataset.role;
            
            const editUserIdField = document.getElementById('editUserId');
            const editUsernameField = document.getElementById('editUsername');
            const editEmailField = document.getElementById('editEmail');
            const editPhoneField = document.getElementById('editPhone');
            const editDepartmentField = document.getElementById('editDepartment');
            const editRoleField = document.getElementById('editRole');
            
            if (editUserIdField) editUserIdField.value = userId;
            if (editUsernameField) editUsernameField.value = username;
            if (editEmailField) editEmailField.value = email;
            if (editPhoneField) editPhoneField.value = phone;
            if (editDepartmentField) editDepartmentField.value = department;
            if (editRoleField) editRoleField.value = role;
            
            // Update the form action URL
            const form = document.getElementById('editUserForm');
            if (form) {
                // Replace '0' in the action URL with the actual user ID
                const baseUrl = form.getAttribute('action').split('/');
                baseUrl[baseUrl.length - 1] = userId;
                form.action = baseUrl.join('/');
            }
        });
    });
}

/**
 * Handle delete user functionality
 */
function initializeDeleteUser() {
    const deleteUserBtns = document.querySelectorAll('.delete-user-btn');
    
    deleteUserBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const username = this.dataset.username;
            
            const deleteUserIdField = document.getElementById('deleteUserId');
            const deleteUsernameField = document.getElementById('deleteUsername');
            
            if (deleteUserIdField) deleteUserIdField.value = userId;
            if (deleteUsernameField) deleteUsernameField.textContent = username;
            
            // Update the form action URL
            const form = document.getElementById('deleteUserForm');
            if (form) {
                // Replace '0' in the action URL with the actual user ID
                const baseUrl = form.getAttribute('action').split('/');
                baseUrl[baseUrl.length - 1] = userId;
                form.action = baseUrl.join('/');
            }
        });
    });
}

/**
 * Handle reset password functionality
 */
function initializeResetPassword() {
    const resetPwdBtns = document.querySelectorAll('.reset-pwd-btn');
    
    resetPwdBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const username = this.dataset.username;
            
            const resetPasswordUserIdField = document.getElementById('resetPasswordUserId');
            const resetPasswordUsernameField = document.getElementById('resetPasswordUsername');
            
            if (resetPasswordUserIdField) resetPasswordUserIdField.value = userId;
            if (resetPasswordUsernameField) resetPasswordUsernameField.textContent = username;
            
            // Update the form action URL
            const form = document.getElementById('resetPasswordForm');
            if (form) {
                // Replace '0' in the action URL with the actual user ID
                const baseUrl = form.getAttribute('action').split('/');
                baseUrl[baseUrl.length - 1] = userId;
                form.action = baseUrl.join('/');
            }
        });
    });
    
    // Toggle random password generation
    const generateRandomPasswordsCheckbox = document.getElementById('generateRandomPasswords');
    const bulkPasswordFields = document.getElementById('bulkPasswordFields');
    
    if (generateRandomPasswordsCheckbox && bulkPasswordFields) {
        generateRandomPasswordsCheckbox.addEventListener('change', function() {
            bulkPasswordFields.style.display = this.checked ? 'none' : 'block';
        });
    }
}

/**
 * Handle toggle user status functionality
 */
function initializeToggleStatus() {
    const toggleStatusBtns = document.querySelectorAll('.toggle-status-btn');
    
    toggleStatusBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const userId = this.dataset.userId;
            const username = this.dataset.username;
            const status = this.dataset.status;
            
            const toggleStatusUserIdField = document.getElementById('toggleStatusUserId');
            const toggleStatusUsernameField = document.getElementById('toggleStatusUsername');
            const toggleStatusTitleField = document.getElementById('toggleStatusTitle');
            const toggleStatusMessageField = document.getElementById('toggleStatusMessage');
            const toggleStatusButton = document.getElementById('toggleStatusButton');
            
            if (toggleStatusUserIdField) toggleStatusUserIdField.value = userId;
            if (toggleStatusUsernameField) toggleStatusUsernameField.textContent = username;
            
            // Update title, message and button text based on the action
            const title = status === 'active' ? 'Activate User' : 'Deactivate User';
            const message = `Are you sure you want to ${status === 'active' ? 'activate' : 'deactivate'} user <strong>${username}</strong>?`;
            const buttonText = status === 'active' ? 'Activate' : 'Deactivate';
            const buttonClass = status === 'active' ? 'btn-success' : 'btn-danger';
            
            if (toggleStatusTitleField) toggleStatusTitleField.textContent = title;
            if (toggleStatusMessageField) toggleStatusMessageField.innerHTML = message;
            
            if (toggleStatusButton) {
                toggleStatusButton.textContent = buttonText;
                toggleStatusButton.className = `btn ${buttonClass}`;
            }
            
            // Update the form action URL
            const form = document.getElementById('toggleStatusForm');
            if (form) {
                // Replace '0' in the action URL with the actual user ID
                const baseUrl = form.getAttribute('action').split('/');
                baseUrl[baseUrl.length - 1] = userId;
                form.action = baseUrl.join('/');
            }
        });
    });
}

/**
 * Handle bulk actions functionality
 */
function initializeBulkActions() {
    const confirmBulkDeleteBtn = document.getElementById('confirmBulkDeleteBtn');
    const confirmBulkRoleBtn = document.getElementById('confirmBulkRoleBtn');
    const confirmBulkDepartmentBtn = document.getElementById('confirmBulkDepartmentBtn');
    const confirmBulkResetPasswordBtn = document.getElementById('confirmBulkResetPasswordBtn');
    const confirmExportBtn = document.getElementById('confirmExportBtn');
    const confirmSendCredentialsBtn = document.getElementById('confirmSendCredentialsBtn');
    
    if (confirmBulkDeleteBtn) {
        confirmBulkDeleteBtn.addEventListener('click', function() {
            setActionTypeAndSubmit('delete');
        });
    }
    
    if (confirmBulkRoleBtn) {
        confirmBulkRoleBtn.addEventListener('click', function() {
            const role = document.getElementById('bulkRole').value;
            if (!role) {
                alert('Please select a role');
                return;
            }
            
            setActionTypeAndSubmit('assign_role');
        });
    }
    
    if (confirmBulkDepartmentBtn) {
        confirmBulkDepartmentBtn.addEventListener('click', function() {
            const department = document.getElementById('bulkDepartment').value;
            if (!department) {
                alert('Please select a department');
                return;
            }
            
            setActionTypeAndSubmit('assign_department');
        });
    }
    
    if (confirmBulkResetPasswordBtn) {
        confirmBulkResetPasswordBtn.addEventListener('click', function() {
            setActionTypeAndSubmit('reset-password');
        });
    }
    
    if (confirmExportBtn) {
        confirmExportBtn.addEventListener('click', function() {
            const formatRadios = document.querySelectorAll('input[name="exportFormat"]');
            let selectedFormat = 'csv'; // Default
            
            formatRadios.forEach(radio => {
                if (radio.checked) {
                    selectedFormat = radio.value;
                }
            });
            
            setActionTypeAndSubmit(`export_${selectedFormat}`);
        });
    }
    
    if (confirmSendCredentialsBtn) {
        confirmSendCredentialsBtn.addEventListener('click', function() {
            const resetBeforeSending = document.getElementById('resetBeforeSending').checked;
            setActionTypeAndSubmit(resetBeforeSending ? 'reset_and_send_credentials' : 'send_credentials');
        });
    }
    
    function setActionTypeAndSubmit(action) {
        const bulkActionTypeField = document.getElementById('bulkActionType');
        const bulkActionForm = document.getElementById('bulkActionForm');
        
        if (bulkActionTypeField) bulkActionTypeField.value = action;
        if (bulkActionForm) bulkActionForm.submit();
    }
}

/**
 * Update user lists in bulk action modals
 */
function updateSelectedUsersList() {
    const checkedCheckboxes = document.querySelectorAll('.user-checkbox:checked');
    const selectedUsernames = Array.from(checkedCheckboxes).map(checkbox => checkbox.dataset.username);
    
    updateUserList('selectedUsersList', selectedUsernames);
    updateUserList('bulkRoleUsersList', selectedUsernames);
    updateUserList('bulkDepartmentUsersList', selectedUsernames);
    updateUserList('bulkResetPasswordUsersList', selectedUsernames);
    updateUserList('exportUsersList', selectedUsernames);
    updateUserList('sendCredentialsUsersList', selectedUsernames);
}

/**
 * Update a specific user list element
 */
function updateUserList(elementId, usernames) {
    const element = document.getElementById(elementId);
    if (!element) return;
    
    if (usernames.length > 0) {
        let html = '<ul class="list-group">';
        usernames.forEach(username => {
            html += `<li class="list-group-item">${username}</li>`;
        });
        html += '</ul>';
        element.innerHTML = html;
    } else {
        element.innerHTML = '<p class="text-muted">No users selected</p>';
    }
}

// Initialize DataTable with advanced features
const userTable = new DataTable('#usersTable', {
    order: [[1, 'asc']], // Sort by name initially
    pageLength: 25,
    language: {
        search: "Search users:",
        emptyTable: "No users found",
        info: "Showing _START_ to _END_ of _TOTAL_ users",
        infoEmpty: "Showing 0 to 0 of 0 users",
        infoFiltered: "(filtered from _MAX_ total users)",
        lengthMenu: "Show _MENU_ users per page",
    },
    columnDefs: [
        { orderable: false, targets: [0, 9] }, // Disable sorting on checkbox and actions columns
        { 
            // Format dates
            targets: [7, 8],
            render: function(data, type, row) {
                if (type === 'display' && data && data !== 'Never' && data !== 'Unknown') {
                    // Try to parse the date string
                    try {
                        const date = new Date(data);
                        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                    } catch (e) {
                        return data;
                    }
                }
                return data;
            }
        }
    ],
    dom: 'Bfrtip', // Buttons, filter, processing indicator, table, pagination
    buttons: [
        {
            text: '<i class="fas fa-file-export"></i> Export',
            className: 'btn btn-sm btn-outline-secondary',
            action: function() {
                $('#exportUsersModal').modal('show');
            }
        },
        {
            text: '<i class="fas fa-file-import"></i> Import',
            className: 'btn btn-sm btn-outline-success',
            action: function() {
                $('#importUsersModal').modal('show');
            }
        },
        {
            text: '<i class="fas fa-sync-alt"></i> Refresh',
            className: 'btn btn-sm btn-outline-primary',
            action: function() {
                refreshUserTable();
            }
        }
    ],
    responsive: true
});

// Toggle generate/custom password
document.getElementById('generatePassword').addEventListener('change', function() {
    document.getElementById('customPasswordField').style.display = this.checked ? 'none' : 'block';
});

// Password visibility toggle
document.querySelectorAll('.toggle-password').forEach(button => {
    button.addEventListener('click', function() {
        const targetId = this.getAttribute('data-target');
        const passwordInput = document.getElementById(targetId);
        
        // Toggle password visibility
        if (passwordInput.type === 'password') {
            passwordInput.type = 'text';
            this.innerHTML = '<i class="fas fa-eye-slash"></i>';
            this.setAttribute('title', 'Hide Password');
            this.setAttribute('aria-label', 'Hide Password');
        } else {
            passwordInput.type = 'password';
            this.innerHTML = '<i class="fas fa-eye"></i>';
            this.setAttribute('title', 'Show Password');
            this.setAttribute('aria-label', 'Show Password');
        }
    });
});

// Add password toggle buttons to any password fields that don't have them
document.querySelectorAll('input[type="password"]').forEach(function(input) {
    if (!input.parentElement.classList.contains('input-group')) {
        const inputId = input.getAttribute('id');
        if (!inputId) return; // Skip if no ID
        
        const inputGroup = document.createElement('div');
        inputGroup.classList.add('input-group');
        
        // Clone the input to preserve all its attributes and event listeners
        const newInput = input.cloneNode(true);
        
        // Create the toggle button
        const toggleButton = document.createElement('button');
        toggleButton.classList.add('btn', 'btn-outline-secondary', 'toggle-password');
        toggleButton.setAttribute('type', 'button');
        toggleButton.setAttribute('data-target', inputId);
        toggleButton.setAttribute('title', 'Show Password');
        toggleButton.setAttribute('aria-label', 'Show Password');
        toggleButton.innerHTML = '<i class="fas fa-eye"></i>';
        
        // Add event listener to the new button
        toggleButton.addEventListener('click', function() {
            const targetId = this.getAttribute('data-target');
            const passwordInput = document.getElementById(targetId);
            
            // Toggle password visibility
            if (passwordInput.type === 'password') {
                passwordInput.type = 'text';
                this.innerHTML = '<i class="fas fa-eye-slash"></i>';
                this.setAttribute('title', 'Hide Password');
                this.setAttribute('aria-label', 'Hide Password');
            } else {
                passwordInput.type = 'password';
                this.innerHTML = '<i class="fas fa-eye"></i>';
                this.setAttribute('title', 'Show Password');
                this.setAttribute('aria-label', 'Show Password');
            }
        });
        
        // Replace the input with the input group
        input.parentNode.replaceChild(inputGroup, input);
        inputGroup.appendChild(newInput);
        inputGroup.appendChild(toggleButton);
    }
});

// Handle password matching validation for Add User form
if (document.getElementById('password') && document.getElementById('confirmPassword')) {
    const passwordInput = document.getElementById('password');
    const confirmPasswordInput = document.getElementById('confirmPassword');
    const passwordFeedback = document.getElementById('passwordMatchFeedback');
    const addUserBtn = document.getElementById('addUserBtn');
    
    // Function to check if passwords match
    function checkPasswordsMatch() {
        if (passwordInput.value !== confirmPasswordInput.value) {
            confirmPasswordInput.classList.add('is-invalid');
            if (passwordFeedback) {
                passwordFeedback.style.display = 'block';
            }
            if (addUserBtn) {
                addUserBtn.disabled = true;
            }
            return false;
        } else {
            confirmPasswordInput.classList.remove('is-invalid');
            if (passwordFeedback) {
                passwordFeedback.style.display = 'none';
            }
            if (addUserBtn) {
                addUserBtn.disabled = false;
            }
            return true;
        }
    }
    
    // Add event listeners for password fields
    passwordInput.addEventListener('input', checkPasswordsMatch);
    confirmPasswordInput.addEventListener('input', checkPasswordsMatch);
    
    // Form submission validation
    const addUserForm = document.getElementById('addUserForm');
    if (addUserForm) {
        addUserForm.addEventListener('submit', function(e) {
            if (!checkPasswordsMatch()) {
                e.preventDefault();
            }
        });
    }
}

// Refresh the user table data
function refreshUserTable() {
    try {
        fetch('/api/users/search')
            .then(response => response.json())
            .then(data => {
                userTable.clear();
                data.forEach(user => {
                    // Similar to filterUsers function
                    const row = [/* ... */];
                    userTable.row.add(row);
                });
                userTable.draw();
                attachEventListeners();
            })
            .catch(error => {
                console.error('Error refreshing users:', error);
                // Just reload the page as fallback
                window.location.reload();
            });
    } catch (e) {
        // Fallback to page reload
        window.location.reload();
    }
}

// Generate action buttons HTML for a user
function getActionButtons(user) {
    return `<div class="btn-group">
        <button type="button" class="btn btn-sm btn-outline-secondary edit-user-btn" 
                data-bs-toggle="modal" data-bs-target="#editUserModal"
                data-user-id="${user.id}"
                data-username="${user.username}"
                data-email="${user.email}"
                data-phone="${user.phone || ''}"
                data-department="${user.department || ''}"
                data-role="${user.role || ''}"
                title="Edit ${user.username}"
                aria-label="Edit ${user.username}">
            <i class="fas fa-edit"></i>
        </button>
        <a href="/my-account?user_id=${user.id}" class="btn btn-sm btn-outline-info" title="View user details" aria-label="View user details">
            <i class="fas fa-user"></i>
        </a>
        <button type="button" class="btn btn-sm btn-outline-warning reset-pwd-btn"
                data-bs-toggle="modal" data-bs-target="#singleResetPasswordModal"
                data-user-id="${user.id}"
                data-username="${user.username}"
                title="Reset password for ${user.username}"
                aria-label="Reset password for ${user.username}">
            <i class="fas fa-key"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-${user.is_active ? 'danger' : 'success'} toggle-status-btn"
                data-bs-toggle="modal" 
                data-bs-target="#toggleStatusModal"
                data-user-id="${user.id}"
                data-username="${user.username}"
                data-status="${user.is_active ? 'deactivate' : 'activate'}"
                title="${user.is_active ? 'Deactivate' : 'Activate'} ${user.username}"
                aria-label="${user.is_active ? 'Deactivate' : 'Activate'} ${user.username}">
            <i class="fas fa-${user.is_active ? 'user-slash' : 'user-check'}"></i>
        </button>
        <button type="button" class="btn btn-sm btn-outline-danger delete-user-btn"
                data-bs-toggle="modal" data-bs-target="#deleteUserModal"
                data-user-id="${user.id}"
                data-username="${user.username}"
                title="Delete ${user.username}"
                aria-label="Delete ${user.username}">
            <i class="fas fa-trash"></i>
        </button>
    </div>`;
}

// Attach event listeners to dynamically created elements
function attachEventListeners() {
    // Re-attach all the event listeners from above for dynamically created elements
    document.querySelectorAll('.user-checkbox').forEach(checkbox => {
        checkbox.addEventListener('change', function() {
            updateBulkActionsButton();
            
            if(!this.checked && selectAllCheckbox.checked) {
                selectAllCheckbox.checked = false;
            }
            
            if(document.querySelectorAll('.user-checkbox:checked').length === userCheckboxes.length) {
                selectAllCheckbox.checked = true;
            }
        });
    });
    
    // Re-attach edit user modal setup
    document.querySelectorAll('.edit-user-btn').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            const username = this.getAttribute('data-username');
            const email = this.getAttribute('data-email');
            const phone = this.getAttribute('data-phone');
            const department = this.getAttribute('data-department');
            const role = this.getAttribute('data-role');
            
            document.getElementById('editUserForm').action = `/edit-user/${userId}`;
            document.getElementById('editFullName').value = username;
            document.getElementById('editEmail').value = email;
            document.getElementById('editPhone').value = phone || '';
            document.getElementById('editDepartment').value = department;
            document.getElementById('editRole').value = role;
            document.getElementById('editPassword').value = '';
        });
    });
    
    // Re-attach delete user modal setup
    document.querySelectorAll('.delete-user-btn').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            const username = this.getAttribute('data-username');
            
            document.getElementById('deleteUserForm').action = `/delete-user/${userId}`;
            document.getElementById('deleteUserName').textContent = username;
        });
    });
    
    // Re-attach reset password modal setup
    document.querySelectorAll('.reset-pwd-btn').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            const username = this.getAttribute('data-username');
            
            document.getElementById('singleResetPasswordForm').action = `/reset-password/${userId}`;
            document.getElementById('resetPasswordUsername').textContent = username;
        });
    });
    
    // Re-attach toggle status modal setup
    document.querySelectorAll('.toggle-status-btn').forEach(button => {
        button.addEventListener('click', function() {
            const userId = this.getAttribute('data-user-id');
            const username = this.getAttribute('data-username');
            const newStatus = this.getAttribute('data-status');
            
            const title = newStatus === 'activate' ? 'Activate User' : 'Deactivate User';
            const message = `Are you sure you want to ${newStatus === 'activate' ? 'activate' : 'deactivate'} user <strong>${username}</strong>?`;
            const btnText = newStatus === 'activate' ? 'Activate' : 'Deactivate';
            const btnClass = newStatus === 'activate' ? 'btn-success' : 'btn-danger';
            
            document.getElementById('toggleStatusTitle').textContent = title;
            document.getElementById('toggleStatusMessage').innerHTML = message;
            document.getElementById('toggleStatusAction').value = newStatus;
            document.getElementById('toggleStatusForm').action = `/toggle-user-status/${userId}`;
            
            const confirmBtn = document.getElementById('confirmToggleStatusBtn');
            confirmBtn.textContent = btnText;
            confirmBtn.className = `btn ${btnClass}`;
        });
    });
} 