// RoleManagementPage.js - Role/Persona Configuration Management
const RoleManagementPage = {
    state: {
        roles: [],
        presets: [],
        categories: [
            { value: 'developer', label: '开发者' },
            { value: 'writer', label: '写作者' },
            { value: 'analyst', label: '分析师' },
            { value: 'assistant', label: '助手' },
            { value: 'other', label: '其他' }
        ]
    },

    async init() {
        await Promise.all([
            this.loadRoles(),
            this.loadPresets()
        ]);
        this.bindEvents();
    },

    async loadRoles() {
        try {
            const response = await fetch('http://localhost:8788/api/agent/role-configs');
            const result = await response.json();
            if (result.success) {
                this.state.roles = result.data;
                this.render();
            }
        } catch (error) {
            console.error('Failed to load roles:', error);
            window.showNotification?.('加载角色配置失败', 'error');
        }
    },

    async loadPresets() {
        try {
            const response = await fetch('http://localhost:8788/api/agent/role-configs/presets');
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

        // 创建或获取角色管理页面容器
        let pageContainer = mainContent.querySelector('.role-management-page-container');

        if (!pageContainer) {
            // 首次创建页面容器
            pageContainer = document.createElement('div');
            pageContainer.className = 'role-management-page-container page-container';
            mainContent.appendChild(pageContainer);
        }

        // 隐藏其他页面，只显示角色管理页面
        mainContent.querySelectorAll('.page-container').forEach(page => {
            page.style.display = 'none';
        });
        pageContainer.style.display = 'block';

        // 渲染内容
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
                <h2>角色管理</h2>
                <div class="header-actions">
                    <button class="btn btn-secondary" id="importRolesBtn">
                        <span>📥</span> 导入
                    </button>
                    <button class="btn btn-secondary" id="exportRolesBtn">
                        <span>📤</span> 导出
                    </button>
                    <button class="btn btn-secondary" id="fromPresetBtn">
                        <span>📋</span> 从模板创建
                    </button>
                    <button class="btn btn-primary" id="addRoleBtn">
                        <span>+</span> 添加角色
                    </button>
                </div>
            </div>
        `;
    },

    renderRolesList() {
        if (!this.state.roles.length) {
            return '<div class="empty-state">暂无角色配置，点击"添加角色"或"从模板创建"开始配置</div>';
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

        return `
            <div class="role-card" data-id="${role.role_id}">
                <div class="role-card-header">
                    <div class="role-info">
                        <h3 class="role-name">${role.display_name || role.name}</h3>
                        <span class="role-category ${role.category}">${categoryLabel}</span>
                        ${role.is_default ? '<span class="badge badge-primary">默认</span>' : ''}
                        ${role.is_preset ? '<span class="badge badge-info">预设</span>' : ''}
                    </div>
                    <div class="role-actions">
                        <button class="btn-icon" data-action="edit" data-id="${role.role_id}" title="编辑">
                            ✏️
                        </button>
                        ${!role.is_preset ? `
                        <button class="btn-icon" data-action="delete" data-id="${role.role_id}" title="删除">
                            🗑️
                        </button>
                        ` : ''}
                    </div>
                </div>
                <div class="role-card-body">
                    <div class="role-detail">
                        <span class="detail-label">使用次数:</span>
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
                        <h3>选择预设模板</h3>
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
                                        使用此模板
                                    </button>
                                </div>
                            `).join('')}
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="cancelPresetBtn">取消</button>
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
        const title = isEdit ? '编辑角色' : '添加角色';

        const modalHtml = `
            <div class="modal-overlay" id="roleModal">
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h3>${title}</h3>
                        <button class="modal-close" id="closeModal">×</button>
                    </div>
                    <div class="modal-body">
                        ${this.renderRoleForm(role)}
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="cancelBtn">取消</button>
                        <button class="btn btn-primary" id="saveBtn">保存</button>
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
                <div class="form-group">
                    <label>角色名称 *</label>
                    <input type="text" name="name" class="form-control"
                           value="${role?.name || ''}" required>
                </div>

                <div class="form-group">
                    <label>显示名称</label>
                    <input type="text" name="display_name" class="form-control"
                           value="${role?.display_name || ''}">
                    <small class="form-text">留空则使用角色名称</small>
                </div>

                <div class="form-group">
                    <label>分类</label>
                    <select name="category" class="form-control">
                        ${this.state.categories.map(c => `
                            <option value="${c.value}" ${role?.category === c.value ? 'selected' : ''}>
                                ${c.label}
                            </option>
                        `).join('')}
                    </select>
                </div>

                <div class="form-group">
                    <label>系统提示词 *</label>
                    <textarea name="system_prompt" class="form-control" rows="6" required>${role?.system_prompt || ''}</textarea>
                    <small class="form-text">定义角色的行为和特点</small>
                </div>

                <div class="form-group">
                    <label>欢迎消息</label>
                    <textarea name="greeting_message" class="form-control" rows="3">${role?.greeting_message || ''}</textarea>
                    <small class="form-text">用户选择此角色时的欢迎语</small>
                </div>

                <div class="form-group">
                    <label>描述</label>
                    <textarea name="description" class="form-control" rows="3">${role?.description || ''}</textarea>
                </div>

                <div class="form-group">
                    <label>标签</label>
                    <input type="text" name="tags" class="form-control"
                           value="${role?.tags || ''}"
                           placeholder="编程,Python,AI (用逗号分隔)">
                </div>

                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" name="is_default" ${role?.is_default ? 'checked' : ''}>
                        设为默认角色
                    </label>
                </div>

                <div class="form-group">
                    <label class="checkbox-label">
                        <input type="checkbox" name="is_active" ${role?.is_active !== false ? 'checked' : ''}>
                        启用此角色
                    </label>
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
            const response = await fetch('http://localhost:8788/api/agent/role-configs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('角色创建成功', 'success');
                // 通知主界面刷新角色选项
                if (window.agentHandlers && window.agentHandlers.loadRoleOptions) {
                    window.agentHandlers.loadRoleOptions();
                }
                return true;
            } else {
                window.showNotification?.('创建失败: ' + (result.error || '未知错误'), 'error');
                return false;
            }
        } catch (error) {
            window.showNotification?.('创建失败: ' + error.message, 'error');
            return false;
        }
    },

    async updateRole(roleId, data) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/role-configs/${roleId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('角色更新成功', 'success');
                // 通知主界面刷新角色选项
                if (window.agentHandlers && window.agentHandlers.loadRoleOptions) {
                    window.agentHandlers.loadRoleOptions();
                }
                return true;
            } else {
                window.showNotification?.('更新失败: ' + (result.error || '未知错误'), 'error');
                return false;
            }
        } catch (error) {
            window.showNotification?.('更新失败: ' + error.message, 'error');
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
        if (!confirm('确定要删除这个角色配置吗？')) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8788/api/agent/role-configs/${roleId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('角色删除成功', 'success');
                await this.loadRoles();
                // 通知主界面刷新角色选项
                if (window.agentHandlers && window.agentHandlers.loadRoleOptions) {
                    window.agentHandlers.loadRoleOptions();
                }
            } else {
                window.showNotification?.('删除失败: ' + result.detail, 'error');
            }
        } catch (error) {
            window.showNotification?.('删除失败: ' + error.message, 'error');
        }
    },

    async exportRoles() {
        try {
            const response = await fetch('http://localhost:8788/api/agent/role-configs/export/all');
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

                window.showNotification?.('导出成功', 'success');
            }
        } catch (error) {
            window.showNotification?.('导出失败: ' + error.message, 'error');
        }
    },

    showImportDialog() {
        const modalHtml = `
            <div class="modal-overlay" id="importModal">
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h3>导入角色配置</h3>
                        <button class="modal-close" id="closeImportModal">×</button>
                    </div>
                    <div class="modal-body">
                        <div class="import-dialog">
                            <p>选择要导入的配置文件 (JSON 格式)</p>
                            <input type="file" id="importFileInput" accept=".json">
                            <div class="import-preview" id="importPreview"></div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="cancelImportBtn">取消</button>
                        <button class="btn btn-primary" id="confirmImportBtn">导入</button>
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
                    preview.innerHTML = `<p>将导入 ${configs.length} 个配置</p>`;
                } catch (error) {
                    const preview = modal.querySelector('#importPreview');
                    preview.innerHTML = `<p class="error">文件格式错误</p>`;
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
                window.showNotification?.('请选择文件', 'warning');
                return;
            }

            try {
                const text = await file.text();
                const configs = JSON.parse(text);

                const response = await fetch('http://localhost:8788/api/agent/role-configs/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(configs)
                });
                const result = await response.json();

                if (result.success) {
                    window.showNotification?.(`成功导入 ${result.data.created} 个配置`, 'success');
                    modal.remove();
                    await this.loadRoles();
                } else {
                    window.showNotification?.('导入失败', 'error');
                }
            } catch (error) {
                window.showNotification?.('导入失败: ' + error.message, 'error');
            }
        });
    },

    bindEvents() {
        // This is called once on init
    },

    /**
     * 销毁页面 - 在切换到其他页面时调用
     */
    destroy() {
        const mainContent = document.getElementById('mainContent');
        if (!mainContent) return;

        // 隐藏角色管理页面
        const pageContainer = mainContent.querySelector('.role-management-page-container');
        if (pageContainer) {
            pageContainer.style.display = 'none';
        }

        // 显示 Agent 主页面
        const agentPage = mainContent.querySelector('#page-agent, .agent-page-layout');
        if (agentPage) {
            agentPage.style.display = '';
        }
    }
};

export default RoleManagementPage;
