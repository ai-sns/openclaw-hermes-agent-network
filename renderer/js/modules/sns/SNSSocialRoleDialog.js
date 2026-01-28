/**
 * SNS Social Role Configuration Dialog
 */

export class SNSSocialRoleDialog {
    constructor() {
        this.dialog = null;
        this.selectedRole = null;
        this.isEditing = false;
    }

    async show() {
        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsSocialRoleDialog">
                <div class="modal-dialog" style="max-width: 1200px; width: 90vw;">
                    <div class="modal-header">
                        <h3>社交角色配置</h3>
                        <button class="modal-close" onclick="document.getElementById('snsSocialRoleDialog').remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="social-role-container">
                            <div class="role-list-section">
                                <h4>角色列表</h4>
                                <div class="role-list" id="socialRoleList">
                                    <div class="loading">加载中...</div>
                                </div>
                            </div>
                            <div class="role-detail-section">
                                <div class="role-detail-header">
                                    <h4>角色详情</h4>
                                </div>
                                <div class="role-preview" id="rolePreview">
                                    <div class="role-preview-content">
                                        <p class="placeholder">请选择一个社交角色查看详情</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <div class="role-actions" id="roleActions" style="display: none;">
                            <button class="btn btn-secondary" id="editRoleBtn">编辑</button>
                            <button class="btn btn-primary" id="saveRoleBtn" style="display: none;">保存</button>
                            <button class="btn btn-secondary" id="cancelEditBtn" style="display: none;">取消</button>
                        </div>
                        <button class="btn btn-secondary" onclick="document.getElementById('snsSocialRoleDialog').remove()">关闭</button>
                    </div>
                </div>
            </div>
        `;

        // Add styles
        const styles = `
            <style>
                #snsSocialRoleDialog .modal-dialog {
                    max-width: 1200px !important;
                    width: 90vw !important;
                    display: flex;
                    flex-direction: column;
                    max-height: 90vh;
                }
                
                #snsSocialRoleDialog .modal-body {
                    flex: 1;
                    overflow: hidden;
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                }
                
                .social-role-container {
                    display: flex;
                    gap: 20px;
                    flex: 1;
                    min-height: 0;
                }
                
                .role-list-section {
                    flex: 0 0 45%;
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                }
                
                .role-list-section h4 {
                    margin: 0 0 12px 0;
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                }
                
                .role-list {
                    flex: 1;
                    overflow-y: auto;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    background: #fafafa;
                }
                
                .role-item {
                    padding: 12px;
                    border-bottom: 1px solid #e0e0e0;
                    cursor: pointer;
                    transition: background-color 0.2s;
                    background: white;
                }
                
                .role-item:hover {
                    background-color: #f5f5f5;
                }
                
                .role-item.selected {
                    background-color: #e3f2fd;
                    border-left: 3px solid #2196F3;
                }
                
                .role-item-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 6px;
                }
                
                .role-item-header h5 {
                    margin: 0;
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                }
                
                .role-tags {
                    font-size: 11px;
                    color: #666;
                    background: #e0e0e0;
                    padding: 2px 6px;
                    border-radius: 3px;
                }
                
                .role-item-preview {
                    font-size: 12px;
                    color: #666;
                    line-height: 1.4;
                    overflow: hidden;
                    text-overflow: ellipsis;
                    display: -webkit-box;
                    -webkit-line-clamp: 2;
                    -webkit-box-orient: vertical;
                }
                
                .role-detail-section {
                    flex: 0 0 55%;
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                }
                
                .role-detail-header {
                    display: flex;
                    justify-content: space-between;
                    align-items: center;
                    margin-bottom: 12px;
                }
                
                .role-detail-header h4 {
                    margin: 0;
                    font-size: 14px;
                    font-weight: 600;
                    color: #333;
                }
                
                #snsSocialRoleDialog .modal-footer {
                    display: flex;
                    justify-content: flex-end;
                    align-items: center;
                    gap: 8px;
                }
                
                .role-actions {
                    display: flex;
                    gap: 8px;
                }
                
                .role-preview {
                    flex: 1;
                    border: 1px solid #e0e0e0;
                    border-radius: 6px;
                    padding: 16px;
                    overflow: hidden;
                    background: white;
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                }
                
                .role-preview-content {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                    overflow-y: auto;
                }
                
                .role-preview-content .placeholder {
                    text-align: center;
                    color: #999;
                    padding: 40px 20px;
                }
                
                .role-detail {
                    display: flex;
                    flex-direction: column;
                    gap: 16px;
                }
                
                .role-detail-title {
                    font-size: 18px;
                    font-weight: 600;
                    color: #333;
                    margin: 0;
                    padding-bottom: 12px;
                    border-bottom: 2px solid #e0e0e0;
                }
                
                .role-field {
                    display: flex;
                    flex-direction: column;
                    gap: 6px;
                }
                
                .role-field-label {
                    font-size: 13px;
                    font-weight: 600;
                    color: #555;
                }
                
                .role-field-value {
                    font-size: 13px;
                    color: #333;
                    line-height: 1.6;
                    padding: 8px;
                    background: #f9f9f9;
                    border-radius: 4px;
                    white-space: pre-wrap;
                }
                
                .role-field-input,
                .role-field-textarea {
                    font-size: 13px;
                    padding: 8px;
                    border: 1px solid #ddd;
                    border-radius: 4px;
                    font-family: inherit;
                }
                
                .role-field-textarea {
                    flex: 1;
                    resize: vertical;
                }
                
                .role-detail.edit-mode {
                    display: flex;
                    flex-direction: column;
                    height: 100%;
                }
                
                .role-detail.edit-mode .role-field:last-child {
                    flex: 1;
                    display: flex;
                    flex-direction: column;
                    min-height: 0;
                }
                
                .role-detail.edit-mode .role-field:last-child .role-field-textarea {
                    height: 100%;
                }
                
                .btn-sm {
                    padding: 6px 12px;
                    font-size: 13px;
                }
                .role-field-input:focus,
                .role-field-textarea:focus {
                    outline: none;
                    border-color: #2196F3;
                    box-shadow: 0 0 0 2px rgba(33, 150, 243, 0.1);
                }
                
                .loading, .empty-state, .error {
                    text-align: center;
                    padding: 20px;
                    color: #999;
                }
                
                .error {
                    color: #f44336;
                }
            </style>
        `;

        // Add to DOM
        document.head.insertAdjacentHTML('beforeend', styles);
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsSocialRoleDialog');

        // Load social roles
        await this.loadSocialRoles();

        // Setup event listeners
        this.setupEventListeners();
    }

    async loadSocialRoles() {
        try {
            const response = await fetch('http://localhost:8788/api/sns/social-roles');
            const roles = await response.json();

            const roleList = document.getElementById('socialRoleList');
            roleList.innerHTML = '';

            if (roles.length === 0) {
                roleList.innerHTML = '<div class="empty-state">暂无社交角色</div>';
                return;
            }

            roles.forEach(role => {
                const item = document.createElement('div');
                item.className = 'role-item';
                item.dataset.roleId = role.id;
                item.innerHTML = `
                    <div class="role-item-header">
                        <h5>${this.escapeHtml(role.title)}</h5>
                        ${role.tags ? `<span class="role-tags">${this.escapeHtml(role.tags)}</span>` : ''}
                    </div>
                    <div class="role-item-preview">${this.escapeHtml(this.truncateText(role.content, 80))}</div>
                `;
                item.addEventListener('click', () => this.selectRole(item, role));
                roleList.appendChild(item);
            });
        } catch (error) {
            console.error('Error loading social roles:', error);
            document.getElementById('socialRoleList').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    selectRole(element, role) {
        // Remove previous selection
        document.querySelectorAll('.role-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Select current
        element.classList.add('selected');
        this.selectedRole = role;
        this.isEditing = false;

        // Show preview
        this.showRolePreview(role);
        
        // Show action buttons and reset to edit mode
        document.getElementById('roleActions').style.display = 'flex';
        document.getElementById('editRoleBtn').style.display = 'inline-block';
        document.getElementById('saveRoleBtn').style.display = 'none';
        document.getElementById('cancelEditBtn').style.display = 'none';
    }

    showRolePreview(role) {
        const preview = document.querySelector('#rolePreview .role-preview-content');
        preview.innerHTML = `
            <div class="role-detail" style="flex: 1; display: flex; flex-direction: column;">
                <h3 class="role-detail-title">${this.escapeHtml(role.title)}</h3>
                
                <div class="role-field" style="flex: 1; display: flex; flex-direction: column; min-height: 0;">
                    <div class="role-field-label">内容</div>
                    <div class="role-field-value" data-field="content" style="flex: 1; overflow-y: auto;">${this.escapeHtml(role.content)}</div>
                </div>
            </div>
        `;
    }

    showEditMode() {
        if (!this.selectedRole) return;

        this.isEditing = true;
        const preview = document.querySelector('#rolePreview .role-preview-content');
        const role = this.selectedRole;

        preview.innerHTML = `
            <div class="role-detail edit-mode">
                <h3 class="role-detail-title">${this.escapeHtml(role.title)}</h3>
                
                <div class="role-field">
                    <label class="role-field-label" for="editContent">内容</label>
                    <textarea id="editContent" class="role-field-textarea">${this.escapeHtml(role.content)}</textarea>
                </div>
            </div>
        `;

        // Toggle buttons
        document.getElementById('editRoleBtn').style.display = 'none';
        document.getElementById('saveRoleBtn').style.display = 'inline-block';
        document.getElementById('cancelEditBtn').style.display = 'inline-block';
    }

    cancelEdit() {
        this.isEditing = false;
        this.showRolePreview(this.selectedRole);
        
        // Toggle buttons
        document.getElementById('editRoleBtn').style.display = 'inline-block';
        document.getElementById('saveRoleBtn').style.display = 'none';
        document.getElementById('cancelEditBtn').style.display = 'none';
    }

    async saveRole() {
        if (!this.selectedRole) return;

        const content = document.getElementById('editContent').value.trim();

        if (!content) {
            alert('内容不能为空');
            return;
        }

        try {
            const response = await fetch(`http://localhost:8788/api/sns/social-roles/${this.selectedRole.id}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: content
                })
            });

            const result = await response.json();

            if (result.success) {
                // Update local data
                this.selectedRole.content = content;

                // Refresh display
                this.cancelEdit();
                
                // Reload list to show updated preview
                await this.loadSocialRoles();
                
                // Re-select the updated role
                const roleItem = document.querySelector(`.role-item[data-role-id="${this.selectedRole.id}"]`);
                if (roleItem) {
                    roleItem.click();
                }

                alert('保存成功');
            } else {
                alert('保存失败：' + result.message);
            }
        } catch (error) {
            console.error('Error saving role:', error);
            alert('保存失败：' + error.message);
        }
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    setupEventListeners() {
        // Edit button
        document.getElementById('editRoleBtn').addEventListener('click', () => {
            this.showEditMode();
        });

        // Save button
        document.getElementById('saveRoleBtn').addEventListener('click', () => {
            this.saveRole();
        });

        // Cancel button
        document.getElementById('cancelEditBtn').addEventListener('click', () => {
            this.cancelEdit();
        });
    }
}
