/**
 * KM Management Dialog
 * Knowledge base management dialog - create/edit/delete knowledge base
 */

import Toast from '../../utils/toast.js';

const KMManagementDialog = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },
    /**
     * Show create KB dialog
     */
    async showCreateDialog() {
        return new Promise((resolve) => {
            const backdrop = this.createBackdrop();
            const dialog = this.createDialog('Create Knowledge Base', null, (kbData) => {
                backdrop.remove();
                resolve(kbData);
            }, () => {
                backdrop.remove();
                resolve(null);
            });

            backdrop.appendChild(dialog);
            document.body.appendChild(backdrop);

            // Focus on name input
            setTimeout(() => {
                const nameInput = dialog.querySelector('#kmNameInput');
                if (nameInput) nameInput.focus();
            }, 100);
        });
    },

    /**
     * Show edit KB dialog
     */
    async showEditDialog(kb) {
        return new Promise((resolve) => {
            const backdrop = this.createBackdrop();
            const dialog = this.createDialog('Edit Knowledge Base', kb, (kbData) => {
                backdrop.remove();
                resolve(kbData);
            }, () => {
                backdrop.remove();
                resolve(null);
            });

            backdrop.appendChild(dialog);
            document.body.appendChild(backdrop);

            // Focus on name input
            setTimeout(() => {
                const nameInput = dialog.querySelector('#kmNameInput');
                if (nameInput) nameInput.focus();
            }, 100);
        });
    },

    /**
     * Create backdrop
     */
    createBackdrop() {
        const backdrop = document.createElement('div');
        backdrop.className = 'km-dialog-backdrop';
        backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 1000000;
            display: flex;
            align-items: center;
            justify-content: center;
            animation: fadeIn 0.2s ease-out;
        `;
        return backdrop;
    },

    /**
     * Create dialog
     */
    createDialog(title, kb = null, onSave, onCancel) {
        const isEdit = kb !== null;
        const dialog = document.createElement('div');
        dialog.className = 'km-management-dialog';

        dialog.innerHTML = `
            <div class="dialog-header">
                <h2 class="dialog-title">${this.escapeHtml(title)}</h2>
            </div>
            <div class="dialog-body">
                <div class="form-group">
                    <label class="form-label">
                        Knowledge Base Name <span class="required-mark">*</span>
                    </label>
                    <input
                        type="text"
                        id="kmNameInput"
                        class="form-input"
                        placeholder="Enter knowledge base name"
                        value="${this.escapeHtml(kb?.name || '')}"
                    >
                </div>
                <div class="form-group">
                    <label class="form-label">
                        Description
                    </label>
                    <textarea
                        id="kmMemoInput"
                        class="form-textarea"
                        rows="4"
                        placeholder="Enter description (optional)"
                    >${this.escapeHtml(kb?.memo || '')}</textarea>
                </div>
                <div class="form-group">
                    <label class="form-label">
                        Type <span class="required-mark">*</span>
                    </label>
                    ${(() => {
                        const kmTypeNum = isEdit ? Number(kb?.kmtype) : NaN;
                        const typeLabel = kmTypeNum === 1
                            ? 'Note (Rich Text Editor)'
                            : kmTypeNum === 0
                                ? 'File (Document Upload & Vector Search)'
                                : kmTypeNum === 2
                                    ? 'Key-Value (Simple Data Storage)'
                                    : '';
                        if (isEdit) {
                            // Read-only display reflecting the actual KB type
                            return `
                                <input type="hidden" id="kmTypeSelect" value="${Number.isFinite(kmTypeNum) ? kmTypeNum : 1}">
                                <input type="text" class="form-input" value="${this.escapeHtml(typeLabel)}" readonly disabled>
                                <div class="form-hint">Type cannot be changed after creation</div>
                            `;
                        }
                        return `
                            <select id="kmTypeSelect" class="form-select">
                                <option value="1">Note (Rich Text Editor)</option>
                                <option value="0">File (Document Upload & Vector Search)</option>
                                <option value="2">Key-Value (Simple Data Storage)</option>
                            </select>
                        `;
                    })()}
                </div>
            </div>
            <div class="dialog-footer">
                <button id="kmCancelBtn" class="btn-secondary">Cancel</button>
                <button id="kmSaveBtn" class="btn-primary">${isEdit ? 'Save Changes' : 'Create'}</button>
            </div>
        `;

        // Add styles if not exists
        if (!document.getElementById('km-dialog-styles')) {
            const style = document.createElement('style');
            style.id = 'km-dialog-styles';
            style.textContent = `
                .km-management-dialog {
                    background: var(--bg-primary, white);
                    border-radius: 12px;
                    padding: 24px;
                    min-width: 500px;
                    max-width: 600px;
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
                    animation: slideInDown 0.3s ease-out;
                    transition: background 0.3s ease, color 0.3s ease;
                }
                
                body.theme-dark .km-management-dialog {
                    background: var(--bg-sidebar, #1e1e1e);
                    box-shadow: 0 8px 32px rgba(0, 0, 0, 0.5);
                }
                
                .km-management-dialog .dialog-header {
                    margin-bottom: 24px;
                }
                
                .km-management-dialog .dialog-title {
                    margin: 0;
                    font-size: 20px;
                    color: var(--text-primary, #333);
                }
                
                .km-management-dialog .form-group {
                    margin-bottom: 20px;
                }
                
                .km-management-dialog .form-label {
                    display: block;
                    margin-bottom: 8px;
                    font-weight: 500;
                    color: var(--text-secondary, #555);
                }
                
                .km-management-dialog .required-mark {
                    color: #f44336;
                }
                
                .km-management-dialog .form-input,
                .km-management-dialog .form-textarea,
                .km-management-dialog .form-select {
                    width: 100%;
                    padding: 10px 12px;
                    border: 1px solid var(--border-color, #ddd);
                    border-radius: 6px;
                    font-size: 14px;
                    box-sizing: border-box;
                    background: var(--bg-secondary, white);
                    color: var(--text-primary, #333);
                    transition: border-color 0.2s, box-shadow 0.2s;
                }
                
                .km-management-dialog .form-textarea {
                    resize: vertical;
                    font-family: inherit;
                }
                
                .km-management-dialog .form-select {
                    cursor: pointer;
                }
                
                .km-management-dialog .form-select.disabled {
                    background: var(--bg-tertiary, #f5f5f5);
                    cursor: not-allowed;
                }
                
                body.theme-dark .km-management-dialog .form-select.disabled {
                    background: rgba(255, 255, 255, 0.05);
                }
                
                .km-management-dialog .form-input:focus,
                .km-management-dialog .form-textarea:focus,
                .km-management-dialog .form-select:focus {
                    outline: none;
                    border-color: var(--color-primary, #1a73e8);
                    box-shadow: 0 0 0 3px rgba(26, 115, 232, 0.1);
                }
                
                body.theme-dark .km-management-dialog .form-input:focus,
                body.theme-dark .km-management-dialog .form-textarea:focus,
                body.theme-dark .km-management-dialog .form-select:focus {
                    box-shadow: 0 0 0 3px rgba(129, 140, 248, 0.2);
                }
                
                .km-management-dialog .form-hint {
                    font-size: 12px;
                    color: var(--text-muted, #999);
                    margin-top: 4px;
                }
                
                .km-management-dialog .checkbox-label {
                    display: flex;
                    align-items: center;
                    cursor: pointer;
                    color: var(--text-secondary, #555);
                }
                
                .km-management-dialog .checkbox-label input[type="checkbox"] {
                    margin-right: 8px;
                    cursor: pointer;
                }
                
                .km-management-dialog .checkbox-label span {
                    font-weight: 500;
                }
                
                .km-management-dialog .dialog-footer {
                    display: flex;
                    gap: 12px;
                    justify-content: flex-end;
                    margin-top: 24px;
                }
                
                .km-management-dialog .btn-secondary {
                    padding: 10px 20px;
                    border: 1px solid var(--border-color, #ddd);
                    background: var(--bg-secondary, white);
                    color: var(--text-secondary, #666);
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: all 0.2s;
                }
                
                .km-management-dialog .btn-secondary:hover {
                    background: var(--bg-hover, #f5f5f5);
                    border-color: var(--border-color, #ccc);
                }
                
                body.theme-dark .km-management-dialog .btn-secondary:hover {
                    background: rgba(255, 255, 255, 0.1);
                }
                
                .km-management-dialog .btn-primary {
                    padding: 10px 20px;
                    border: none;
                    background: var(--color-primary, #1a73e8);
                    color: white;
                    border-radius: 6px;
                    cursor: pointer;
                    font-size: 14px;
                    transition: all 0.2s;
                }
                
                .km-management-dialog .btn-primary:hover {
                    opacity: 0.9;
                    transform: translateY(-1px);
                    box-shadow: 0 4px 12px rgba(26, 115, 232, 0.3);
                }
                
                body.theme-dark .km-management-dialog .btn-primary:hover {
                    box-shadow: 0 4px 12px rgba(129, 140, 248, 0.4);
                }
            `;
            document.head.appendChild(style);
        }

        // Bind events
        const saveBtn = dialog.querySelector('#kmSaveBtn');
        const cancelBtn = dialog.querySelector('#kmCancelBtn');
        const nameInput = dialog.querySelector('#kmNameInput');
        const memoInput = dialog.querySelector('#kmMemoInput');
        const typeSelect = dialog.querySelector('#kmTypeSelect');

        saveBtn.addEventListener('click', () => {
            const name = nameInput.value.trim();
            if (!name) {
                Toast.warning('Please enter knowledge base name');
                nameInput.focus();
                return;
            }

            const kbData = {
                name,
                memo: memoInput.value.trim(),
                kmtype: parseInt(typeSelect.value),
                // Preserve existing visibility on edit; default to visible on create
                is_show: isEdit ? (kb?.is_show !== false) : true
            };

            if (isEdit) {
                kbData.id = kb.id;
                kbData.km_id = kb.km_id;
            }

            onSave(kbData);
        });

        cancelBtn.addEventListener('click', () => {
            onCancel();
        });

        // Handle ESC key
        const handleEsc = (e) => {
            if (e.key === 'Escape') {
                onCancel();
                document.removeEventListener('keydown', handleEsc);
            }
        };
        document.addEventListener('keydown', handleEsc);

        // Handle Enter key (save)
        const handleEnter = (e) => {
            if (e.key === 'Enter' && e.ctrlKey) {
                saveBtn.click();
            }
        };
        dialog.addEventListener('keydown', handleEnter);

        return dialog;
    },

    /**
     * Confirm delete KB
     */
    async confirmDelete(kb) {
        return Toast.confirm(
            `Are you sure you want to delete "${kb.name}"? This action cannot be undone.`,
            {
                title: 'Delete Knowledge Base',
                confirmText: 'Delete',
                cancelText: 'Cancel',
                type: 'error'
            }
        );
    },

    /**
     * Create knowledge base
     */
    async createKB(kbData) {
        const loading = Toast.loading('Creating knowledge base...');

        try {
            // Generate unique km_id
            kbData.km_id = this.generateKMId();

            const response = await fetch(this.resolve('/api/km'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(kbData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to create knowledge base');
            }

            const result = await response.json();
            loading.close();
            Toast.success('Knowledge base created successfully');
            return result.data;
        } catch (error) {
            console.error('Create KB failed:', error);
            loading.close();
            Toast.error('Failed to create: ' + error.message);
            return null;
        }
    },

    /**
     * Update knowledge base
     */
    async updateKB(kbData) {
        const loading = Toast.loading('Updating knowledge base...');

        try {
            const response = await fetch(this.resolve(`/api/km/${kbData.id}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(kbData)
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to update knowledge base');
            }

            const result = await response.json();
            loading.close();
            Toast.success('Knowledge base updated successfully');
            return result.data;
        } catch (error) {
            console.error('Update KB failed:', error);
            loading.close();
            Toast.error('Failed to update: ' + error.message);
            return null;
        }
    },

    /**
     * Delete knowledge base
     */
    async deleteKB(kbId) {
        const loading = Toast.loading('Deleting knowledge base...');

        try {
            const response = await fetch(this.resolve(`/api/km/${kbId}`), {
                method: 'DELETE'
            });

            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.message || 'Failed to delete knowledge base');
            }

            loading.close();
            Toast.success('Knowledge base deleted successfully');
            return true;
        } catch (error) {
            console.error('Delete KB failed:', error);
            loading.close();
            Toast.error('Failed to delete: ' + error.message);
            return false;
        }
    },

    /**
     * Generate unique KM ID
     */
    generateKMId() {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ';
        const randomChars = Array.from({ length: 2 }, () =>
            chars.charAt(Math.floor(Math.random() * chars.length))
        ).join('');

        const timestamp = Date.now().toString().slice(-15);
        return `${randomChars}${timestamp}`;
    },

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

export default KMManagementDialog;

// Global access
if (typeof window !== 'undefined') {
    window.KMManagementDialog = KMManagementDialog;
}
