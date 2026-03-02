// RoleManagementPage.js - Role/Persona Configuration Management
const RoleManagementPage = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },
    state: {
        roles: [],
        presets: [],
        categories: [
            { value: 'developer', label: 'Developer' },
            { value: 'writer', label: 'Writer' },
            { value: 'analyst', label: 'Analyst' },
            { value: 'assistant', label: 'Assistant' },
            { value: 'other', label: 'Other' }
        ]
    },

    async init() {
        await Promise.all([
            this.loadRoles(),
            this.loadPresets()
        ]);
        this.bindEvents();
        this.bindSidebarClickHandler();
    },

    async loadRoles() {
        try {
            const response = await fetch(this.resolve('/api/agent/role-configs'));
            const result = await response.json();
            if (result.success) {
                this.state.roles = result.data;
                this.render();
            }
        } catch (error) {
            console.error('Failed to load roles:', error);
            window.showNotification?.('Failed to load role configurations', 'error');
        }
    },

    async loadPresets() {
        try {
            const response = await fetch(this.resolve('/api/agent/role-configs/presets'));
            const result = await response.json();
            if (result.success) {
                this.state.presets = result.data;
            }
        } catch (error) {
            console.error('Failed to load presets:', error);
        }
    },

    render() {
        const mainContent = document.getElementById('mainContent');
        if (!mainContent) return;

        // Create or get the role management page container
        let pageContainer = mainContent.querySelector('.role-management-page-container');

        if (!pageContainer) {
            // Create the page container for the first time
            pageContainer = document.createElement('div');
            pageContainer.className = 'role-management-page-container page-container';
            mainContent.appendChild(pageContainer);
        }

        // Hide other pages and only show the role management page
        mainContent.querySelectorAll('.page-container').forEach(page => {
            page.style.display = 'none';
        });
        pageContainer.style.display = 'block';

        // Render content
        pageContainer.innerHTML = `
            <div class="role-management-page">
                ${this.renderHeader()}
                ${this.renderRolesList()}
            </div>
        `;

        this.bindPageEvents();
    },

    renderHeader() {
        return `
            <div class="page-header">
                <div style="display: flex; align-items: center; gap: 12px;">
                    <button class="btn btn-secondary" id="closeRoleManagementBtn" title="Back">
                         <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <path d="M20 12H4M10 18L4 12L10 6" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/>
</svg> Back
                    </button>
                    <h2>Roles</h2>
                </div>
                <div class="header-actions">
                    <button class="btn btn-secondary" id="importRolesBtn">
                        <span>📥</span> Import
                    </button>
                    <button class="btn btn-secondary" id="exportRolesBtn">
                        <span>📤</span> Export
                    </button>
                    <button class="btn btn-secondary" id="fromPresetBtn" style="display:none">
                        <span>📋</span> Template
                    </button>
                    <button class="btn btn-primary" id="addRoleBtn">
                        <span>+</span> New Role
                    </button>
                </div>
            </div>
        `;
    },

    renderRolesList() {
        if (!this.state.roles.length) {
            return '<div class="empty-state">No role configurations yet. Click "New Role" to add one.</div>';
        }

        const rolesHtml = this.state.roles.map(role => this.renderRoleCard(role)).join('');

        return `
            <div class="roles-container">
                <div class="roles-list">
                    ${rolesHtml}
                </div>
            </div>
        `;
    },

    renderRoleCard(role) {
        const categoryLabel = this.state.categories.find(c => c.value === role.category)?.label || role.category;
        const isPreset = role && (
            role.is_preset === true ||
            role.is_preset === 'true' ||
            role.is_preset === 1 ||
            role.is_preset === '1'
        );

        return `
            <div class="role-card" data-id="${role.role_id}">
                <div class="role-card-header">
                    <div class="role-info">
                        <h3 class="role-name">${role.display_name || role.name}</h3>
                        <span class="role-category ${role.category}">${categoryLabel}</span>
                        ${role.is_default ? '<span class="badge badge-primary">Default</span>' : ''}
                        ${isPreset ? '<span class="badge badge-info">Preset</span>' : ''}
                    </div>
                    <div class="role-actions">
                        <button class="btn-icon" data-action="edit" data-id="${role.role_id}" title="Edit">
                            ✏️
                        </button>
                        <button class="btn-icon" data-action="delete" data-id="${role.role_id}" title="${isPreset ? 'Preset roles cannot be deleted' : 'Delete'}" ${isPreset ? 'disabled aria-disabled="true"' : ''}>
                            🗑️
                        </button>
                    </div>
                </div>
                <div class="role-card-body">
                    <div class="role-detail">
                        <span class="detail-label">Usage:</span>
                        <span class="detail-value">${role.usage_count || 0}</span>
                    </div>
                    ${role.description ? `<div class="role-description">${role.description}</div>` : ''}
                    ${role.system_prompt ? `
                    <div class="role-prompt-preview">
                        ${role.system_prompt.substring(0, 100)}${role.system_prompt.length > 100 ? '...' : ''}
                    </div>
                    ` : ''}
                </div>
            </div>
        `;
    },

    bindPageEvents() {
        document.getElementById('addRoleBtn')?.addEventListener('click', () => {
            this.showRoleDialog();
        });

        document.getElementById('fromPresetBtn')?.addEventListener('click', () => {
            this.showPresetDialog();
        });

        document.getElementById('importRolesBtn')?.addEventListener('click', () => {
            this.showImportDialog();
        });

        document.getElementById('exportRolesBtn')?.addEventListener('click', () => {
            this.exportRoles();
        });

        document.getElementById('closeRoleManagementBtn')?.addEventListener('click', () => {
            this.destroy();
        });

        // Delegate events for role cards
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = button.dataset.action;
                const id = button.dataset.id;

                switch (action) {
                    case 'edit':
                        this.editRole(id);
                        break;
                    case 'delete':
                        this.deleteRole(id);
                        break;
                }
            });
        });
    },

    showPresetDialog() {
        const modalHtml = `
            <div class="modal-overlay" id="presetModal">
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h3>Select a preset template</h3>
                        <button class="modal-close" id="closePresetModal">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="preset-list">
                            ${this.state.presets.map(preset => `
                                <div class="preset-item" data-preset-id="${preset.role_id}">
                                    <h4>${preset.display_name || preset.name}</h4>
                                    <p class="preset-category">${preset.category}</p>
                                    <p class="preset-description">${preset.description || ''}</p>
                                    <button class="btn btn-sm btn-primary" data-action="use-preset" data-id="${preset.role_id}">
                                        Use this template
                                    </button>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="cancelPresetBtn">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = document.getElementById('presetModal');

        // Modal close
        modal.querySelector('#closePresetModal').addEventListener('click', () => modal.remove());
        modal.querySelector('#cancelPresetBtn').addEventListener('click', () => modal.remove());

        // Use preset buttons
        modal.querySelectorAll('[data-action="use-preset"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const presetId = btn.dataset.id;
                const preset = this.state.presets.find(p => p.role_id === presetId);
                if (preset) {
                    modal.remove();
                    this.showRoleDialog({
                        ...preset,
                        role_id: null,  // Clear ID to create new
                        is_preset: false
                    });
                }
            });
        });
    },

    showRoleDialog(role = null) {
        const isEdit = !!role?.role_id;
        const title = isEdit ? 'Edit Role' : 'Add Role';

        const modalHtml = `
            <div class="modal-overlay" id="roleModal">
                <div class="modal-dialog" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>${title}</h3>
                        <button class="modal-close" id="closeModal">×</button>
                    </div>
                    <div class="modal-body">
                        ${this.renderRoleForm(role)}
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="cancelBtn">Cancel</button>
                        <button class="btn btn-primary" id="saveBtn">Save</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = document.getElementById('roleModal');

        // Modal close
        modal.querySelector('#closeModal').addEventListener('click', () => modal.remove());
        modal.querySelector('#cancelBtn').addEventListener('click', () => modal.remove());

        // Save button
        modal.querySelector('#saveBtn').addEventListener('click', async () => {
            const formData = this.getFormData(modal);
            const success = isEdit
                ? await this.updateRole(role.role_id, formData)
                : await this.createRole(formData);

            if (success) {
                modal.remove();
                await this.loadRoles();
            }
        });
    },

    renderRoleForm(role = null) {
        return `
            <form id="roleForm" class="role-form">
                <div class="dialog-section">
                    <h4>Basic</h4>
                    <div class="form-row">
                        <div class="form-group" style="flex: 1;">
                            <label>Role ID *</label>
                            <input type="text" name="name" class="form-control"
                                   value="${role?.name || ''}" required placeholder="e.g. python_expert">
                        </div>
                        <div class="form-group" style="flex: 1;">
                            <label>Display Name</label>
                            <input type="text" name="display_name" class="form-control"
                                   value="${role?.display_name || ''}" placeholder="e.g. Python Expert">
                        </div>
                    </div>

                    <div class="form-group">
                        <label>Category</label>
                        <select name="category" class="form-control">
                            ${this.state.categories.map(c => `
                                <option value="${c.value}" ${role?.category === c.value ? 'selected' : ''}>
                                    ${c.label}
                                </option>
                            `).join('')}
                        </select>
                    </div>

                    <div class="form-group">
                        <label>Description</label>
                        <textarea name="description" class="form-control" rows="2" placeholder="Briefly describe what this role does">${role?.description || ''}</textarea>
                    </div>

                    <div class="form-group">
                        <label>Tags</label>
                        <input type="text" name="tags" class="form-control"
                               value="${role?.tags || ''}"
                               placeholder="e.g. coding,Python,AI (comma separated)">
                    </div>
                </div>

                <div class="dialog-section">
                    <h4>Persona</h4>
                    <div class="form-group">
                        <label>System Prompt *</label>
                        <textarea name="system_prompt" class="form-control" rows="8" required placeholder="Define the role's behavior, personality, and capabilities...">${role?.system_prompt || ''}</textarea>
                    </div>

                    <div class="form-group">
                        <label>Greeting Message</label>
                        <textarea name="greeting_message" class="form-control" rows="2" placeholder="Shown when the user starts the first conversation">${role?.greeting_message || ''}</textarea>
                    </div>
                </div>

                <div class="dialog-section">
                    <h4>Status</h4>
                    <div class="checkbox-group">
                        <label class="checkbox-label">
                            <input type="checkbox" name="is_default" ${role?.is_default ? 'checked' : ''}>
                            Set as default
                        </label>
                        <label class="checkbox-label">
                            <input type="checkbox" name="is_active" ${role?.is_active !== false ? 'checked' : ''}>
                            Enable this role
                        </label>
                    </div>
                </div>
            </form>
        `;
    },

    getFormData(modal) {
        const form = modal.querySelector('#roleForm');
        const formData = new FormData(form);
        const data = {};

        for (const [key, value] of formData.entries()) {
            if (key === 'is_default' || key === 'is_active') {
                data[key] = form.querySelector(`[name="${key}"]`).checked;
            } else {
                data[key] = value;
            }
        }

        return data;
    },

    async createRole(data) {
        try {
            const response = await fetch(this.resolve('/api/agent/role-configs'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('Role created', 'success');
                // Notify main UI to refresh role options
                if (window.agentHandlers && window.agentHandlers.loadRoleOptions) {
                    window.agentHandlers.loadRoleOptions();
                }
                return true;
            } else {
                window.showNotification?.('Create failed: ' + (result.error || 'Unknown error'), 'error');
                return false;
            }
        } catch (error) {
            window.showNotification?.('Create failed: ' + error.message, 'error');
            return false;
        }
    },

    async updateRole(roleId, data) {
        try {
            const response = await fetch(this.resolve(`/api/agent/role-configs/${roleId}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('Role updated', 'success');
                // Notify main UI to refresh role options
                if (window.agentHandlers && window.agentHandlers.loadRoleOptions) {
                    window.agentHandlers.loadRoleOptions();
                }
                return true;
            } else {
                window.showNotification?.('Update failed: ' + (result.error || 'Unknown error'), 'error');
                return false;
            }
        } catch (error) {
            window.showNotification?.('Update failed: ' + error.message, 'error');
            return false;
        }
    },

    editRole(roleId) {
        const role = this.state.roles.find(r => r.role_id === roleId);
        if (role) {
            this.showRoleDialog(role);
        }
    },

    async deleteRole(roleId) {
        const confirmed = await (async () => {
            try {
                if (window.Toast && typeof window.Toast.confirm === 'function') {
                    return await window.Toast.confirm('Delete this role configuration?', {
                        title: 'Delete Role',
                        confirmText: 'Delete',
                        cancelText: 'Cancel',
                        type: 'warning'
                    });
                }

                if (window.Modal && typeof window.Modal.show === 'function') {
                    return await new Promise((resolve) => {
                        window.Modal.show({
                            title: 'Delete Role',
                            content: '<p>Delete this role configuration?</p>',
                            confirmText: 'Delete',
                            cancelText: 'Cancel',
                            onConfirm: () => {
                                resolve(true);
                                return true;
                            },
                            onCancel: () => {
                                resolve(false);
                                return true;
                            }
                        });
                    });
                }
            } catch (e) {
                console.error('Failed to show delete role confirmation dialog:', e);
            }
            return false;
        })();

        if (!confirmed) return;

        try {
            const response = await fetch(this.resolve(`/api/agent/role-configs/${roleId}`), {
                method: 'DELETE'
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('Role deleted', 'success');
                await this.loadRoles();
                // Notify main UI to refresh role options
                if (window.agentHandlers && window.agentHandlers.loadRoleOptions) {
                    window.agentHandlers.loadRoleOptions();
                }
            } else {
                window.showNotification?.('Delete failed: ' + result.detail, 'error');
            }
        } catch (error) {
            window.showNotification?.('Delete failed: ' + error.message, 'error');
        }
    },

    async exportRoles() {
        try {
            const response = await fetch(this.resolve('/api/agent/role-configs/export/all'));
            const result = await response.json();

            if (result.success) {
                const dataStr = JSON.stringify(result.data, null, 2);
                const blob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `role-configs-${Date.now()}.json`;
                a.click();
                URL.revokeObjectURL(url);

                window.showNotification?.('Exported successfully', 'success');
            }
        } catch (error) {
            window.showNotification?.('Export failed: ' + error.message, 'error');
        }
    },

    showImportDialog() {
        const modalHtml = `
            <div class="modal-overlay" id="importModal">
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h3>Import role configurations</h3>
                        <button class="modal-close" id="closeImportModal">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="import-dialog">
                            <p>Select a configuration file to import (JSON)</p>
                            <input type="file" id="importFileInput" accept=".json">
                            <div class="import-preview" id="importPreview"></div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="cancelImportBtn">Cancel</button>
                        <button class="btn btn-primary" id="confirmImportBtn">Confirm</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = document.getElementById('importModal');

        // File preview
        modal.querySelector('#importFileInput').addEventListener('change', async (e) => {
            const file = e.target.files[0];
            if (file) {
                try {
                    const text = await file.text();
                    const configs = JSON.parse(text);
                    const preview = modal.querySelector('#importPreview');
                    preview.innerHTML = `<p>Will import ${configs.length} configuration(s)</p>`;
                } catch (error) {
                    const preview = modal.querySelector('#importPreview');
                    preview.innerHTML = `<p class="error">Invalid file format</p>`;
                }
            }
        });

        // Modal close
        modal.querySelector('#closeImportModal').addEventListener('click', () => modal.remove());
        modal.querySelector('#cancelImportBtn').addEventListener('click', () => modal.remove());

        // Confirm import
        modal.querySelector('#confirmImportBtn').addEventListener('click', async () => {
            const file = modal.querySelector('#importFileInput').files[0];
            if (!file) {
                window.showNotification?.('Please select a file', 'warning');
                return;
            }

            try {
                const text = await file.text();
                const configs = JSON.parse(text);

                const response = await fetch(this.resolve('/api/agent/role-configs/import'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(configs)
                });
                const result = await response.json();

                if (result.success) {
                    window.showNotification?.(`Imported ${result.data.created} configuration(s)`, 'success');
                    modal.remove();
                    await this.loadRoles();
                } else {
                    window.showNotification?.('Import failed', 'error');
                }
            } catch (error) {
                window.showNotification?.('Import failed: ' + error.message, 'error');
            }
        });
    },

    bindEvents() {
        // This is called once on init
    },

    /**
     * Bind sidebar click handler - go back when clicking agent or chat list
     */
    bindSidebarClickHandler() {
        // Use event delegation to listen for sidebar clicks
        document.addEventListener('click', (e) => {
            // Check whether an agent item or chat list item was clicked
            const agentItem = e.target.closest('.agent-item[data-agent-id]');
            const chatItem = e.target.closest('.tree-item[data-conversation-id]');

            if (agentItem || chatItem) {
                // If the management page is open, close it
                const mgmtPage = document.querySelector('.role-management-page-container');
                if (mgmtPage && mgmtPage.style.display !== 'none') {
                    this.destroy();
                }
            }
        }, true); // Use capture phase to ensure it runs first
    },

    /**
     * Destroy page - called when switching to other pages
     */
    destroy() {
        const mainContent = document.getElementById('mainContent');
        if (!mainContent) return;

        // Hide role management page
        const pageContainer = mainContent.querySelector('.role-management-page-container');
        if (pageContainer) {
            pageContainer.style.display = 'none';
        }

        // Show Agent main page
        const agentPage = mainContent.querySelector('#page-agent, .agent-page-layout');
        if (agentPage) {
            agentPage.style.display = '';
        }
    }
};

export default RoleManagementPage;
