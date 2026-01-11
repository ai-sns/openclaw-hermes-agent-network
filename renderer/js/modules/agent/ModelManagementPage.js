// ModelManagementPage.js - LLM Model Configuration Management
const ModelManagementPage = {
    state: {
        models: [],
        selectedModel: null,
        editMode: false,
        providers: [
            { value: 'openai', label: 'OpenAI' },
            { value: 'claude', label: 'Claude (Anthropic)' },
            { value: 'gemini', label: 'Gemini (Google)' },
            { value: 'custom', label: '类 OpenAI (自定义)' }
        ]
    },

    async init() {
        await this.loadModels();
        this.bindEvents();
    },

    async loadModels() {
        try {
            const response = await fetch('http://localhost:8788/api/agent/llm-configs');
            const result = await response.json();
            if (result.success) {
                this.state.models = result.data;
                this.render();
            }
        } catch (error) {
            console.error('Failed to load models:', error);
            window.showNotification?.('加载模型配置失败', 'error');
        }
    },

    render() {
        const mainContent = document.getElementById('mainContent');
        if (!mainContent) return;

        // 创建或获取模型管理页面容器
        let pageContainer = mainContent.querySelector('.model-management-page-container');

        if (!pageContainer) {
            // 首次创建页面容器
            pageContainer = document.createElement('div');
            pageContainer.className = 'model-management-page-container page-container';
            mainContent.appendChild(pageContainer);
        }

        // 隐藏其他页面，只显示模型管理页面
        mainContent.querySelectorAll('.page-container').forEach(page => {
            page.style.display = 'none';
        });
        pageContainer.style.display = 'block';

        // 渲染内容
        pageContainer.innerHTML = `
            <div class="model-management-page">
                ${this.renderHeader()}
                ${this.renderModelsList()}
            </div>
        `;

        this.bindPageEvents();
    },

    renderHeader() {
        return `
            <div class="page-header">
                <h2>模型管理</h2>
                <div class="header-actions">
                    <button class="btn btn-secondary" id="importModelsBtn">
                        <span>📥</span> 导入
                    </button>
                    <button class="btn btn-secondary" id="exportModelsBtn">
                        <span>📤</span> 导出
                    </button>
                    <button class="btn btn-primary" id="addModelBtn">
                        <span>+</span> 添加模型
                    </button>
                </div>
            </div>
        `;
    },

    renderModelsList() {
        if (!this.state.models.length) {
            return '<div class="empty-state">暂无模型配置，点击"添加模型"开始配置</div>';
        }

        const modelsHtml = this.state.models.map(model => this.renderModelCard(model)).join('');

        return `
            <div class="models-container">
                <div class="models-list">
                    ${modelsHtml}
                </div>
            </div>
        `;
    },

    renderModelCard(model) {
        const providerLabel = this.state.providers.find(p => p.value === model.provider)?.label || model.provider;

        return `
            <div class="model-card" data-id="${model.config_id}">
                <div class="model-card-header">
                    <div class="model-info">
                        <h3 class="model-name">${model.name}</h3>
                        <span class="model-provider ${model.provider}">${providerLabel}</span>
                        ${model.is_default ? '<span class="badge badge-primary">默认</span>' : ''}
                    </div>
                    <div class="model-actions">
                        <button class="btn-icon" data-action="test" data-id="${model.config_id}" title="测试连接">
                            🔍
                        </button>
                        <button class="btn-icon" data-action="edit" data-id="${model.config_id}" title="编辑">
                            ✏️
                        </button>
                        <button class="btn-icon" data-action="delete" data-id="${model.config_id}" title="删除">
                            🗑️
                        </button>
                    </div>
                </div>
                <div class="model-card-body">
                    <div class="model-detail">
                        <span class="detail-label">模型名称:</span>
                        <span class="detail-value">${model.model_name || 'N/A'}</span>
                    </div>
                    <div class="model-detail">
                        <span class="detail-label">API端点:</span>
                        <span class="detail-value">${model.api_endpoint || 'N/A'}</span>
                    </div>
                    ${model.description ? `<div class="model-description">${model.description}</div>` : ''}
                </div>
            </div>
        `;
    },

    bindPageEvents() {
        document.getElementById('addModelBtn')?.addEventListener('click', () => {
            this.showModelDialog();
        });

        document.getElementById('importModelsBtn')?.addEventListener('click', () => {
            this.showImportDialog();
        });

        document.getElementById('exportModelsBtn')?.addEventListener('click', () => {
            this.exportModels();
        });

        // Delegate events for model cards
        document.querySelectorAll('[data-action]').forEach(button => {
            button.addEventListener('click', (e) => {
                const action = button.dataset.action;
                const id = button.dataset.id;

                switch (action) {
                    case 'edit':
                        this.editModel(id);
                        break;
                    case 'delete':
                        this.deleteModel(id);
                        break;
                    case 'test':
                        this.testConnection(id);
                        break;
                }
            });
        });
    },

    showModelDialog(model = null) {
        const isEdit = !!model;
        const title = isEdit ? '编辑模型' : '添加模型';

        const modalHtml = `
            <div class="modal-overlay" id="modelModal">
                <div class="modal-dialog">
                    <div class="modal-header">
                        <h3>${title}</h3>
                        <button class="modal-close" id="closeModal">×</button>
                    </div>
                    <div class="modal-body">
                        ${this.renderModelForm(model)}
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" id="cancelBtn">取消</button>
                        <button class="btn btn-primary" id="saveBtn">保存</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', modalHtml);

        const modal = document.getElementById('modelModal');

        // Tab switching
        modal.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const tab = btn.dataset.tab;
                modal.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
                modal.querySelectorAll('.tab-content').forEach(c => c.classList.remove('active'));
                btn.classList.add('active');
                modal.querySelector(`[data-tab-content="${tab}"]`).classList.add('active');
            });
        });

        // Modal close
        modal.querySelector('#closeModal').addEventListener('click', () => modal.remove());
        modal.querySelector('#cancelBtn').addEventListener('click', () => modal.remove());

        // Save button
        modal.querySelector('#saveBtn').addEventListener('click', async () => {
            const formData = this.getFormData(modal);
            const success = isEdit
                ? await this.updateModel(model.config_id, formData)
                : await this.createModel(formData);

            if (success) {
                modal.remove();
                await this.loadModels();
            }
        });

        // Test connection button
        modal.querySelector('.test-connection-btn')?.addEventListener('click', async () => {
            const formData = this.getFormData(modal);
            await this.testConnection(null, {
                api_endpoint: formData.api_endpoint,
                api_key: formData.api_key,
                model_name: formData.model_name,
                provider: formData.provider
            });
        });
    },

    renderModelForm(model = null) {
        return `
            <form id="modelForm" class="model-form">
                <div class="form-tabs">
                    <button type="button" class="tab-btn active" data-tab="basic">基础配置</button>
                    <button type="button" class="tab-btn" data-tab="advanced">高级参数</button>
                </div>

                <!-- Basic Config -->
                <div class="tab-content active" data-tab-content="basic">
                    <div class="form-group">
                        <label>显示名称 *</label>
                        <input type="text" name="name" class="form-control"
                               value="${model?.name || ''}" required>
                    </div>

                    <div class="form-group">
                        <label>接口类型 *</label>
                        <select name="provider" class="form-control" required>
                            ${this.state.providers.map(p => `
                                <option value="${p.value}" ${model?.provider === p.value ? 'selected' : ''}>
                                    ${p.label}
                                </option>
                            `).join('')}
                        </select>
                    </div>

                    <div class="form-group">
                        <label>API 端点 *</label>
                        <input type="url" name="api_endpoint" class="form-control"
                               value="${model?.api_endpoint || ''}"
                               placeholder="https://api.openai.com/v1/chat/completions" required>
                    </div>

                    <div class="form-group">
                        <label>API Key *</label>
                        <input type="password" name="api_key" class="form-control"
                               value="${model?.api_key || ''}"
                               placeholder="sk-..." required>
                        <button type="button" class="btn-link test-connection-btn">
                            测试连接
                        </button>
                    </div>

                    <div class="form-group">
                        <label>模型名称 *</label>
                        <input type="text" name="model_name" class="form-control"
                               value="${model?.model_name || ''}"
                               placeholder="gpt-4o" required>
                    </div>

                    <div class="form-group">
                        <label>描述</label>
                        <textarea name="description" class="form-control" rows="3">${model?.description || ''}</textarea>
                    </div>

                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" name="is_default" ${model?.is_default ? 'checked' : ''}>
                            设为默认模型
                        </label>
                    </div>

                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" name="is_active" ${model?.is_active !== false ? 'checked' : ''}>
                            启用此配置
                        </label>
                    </div>
                </div>

                <!-- Advanced Config -->
                <div class="tab-content" data-tab-content="advanced">
                    <div class="form-group">
                        <label>Temperature (0-2)</label>
                        <input type="number" name="temperature" class="form-control"
                               value="${model?.temperature ?? 0.7}"
                               min="0" max="2" step="0.1">
                        <small class="form-text">控制输出的随机性，越高越随机</small>
                    </div>

                    <div class="form-group">
                        <label>Max Tokens</label>
                        <input type="number" name="max_tokens" class="form-control"
                               value="${model?.max_tokens ?? 2048}"
                               min="1">
                        <small class="form-text">最大生成令牌数</small>
                    </div>

                    <div class="form-group">
                        <label>Top P (0-1)</label>
                        <input type="number" name="top_p" class="form-control"
                               value="${model?.top_p ?? 1.0}"
                               min="0" max="1" step="0.1">
                    </div>

                    <div class="form-group">
                        <label>Frequency Penalty (-2 to 2)</label>
                        <input type="number" name="frequency_penalty" class="form-control"
                               value="${model?.frequency_penalty ?? 0}"
                               min="-2" max="2" step="0.1">
                    </div>

                    <div class="form-group">
                        <label>Presence Penalty (-2 to 2)</label>
                        <input type="number" name="presence_penalty" class="form-control"
                               value="${model?.presence_penalty ?? 0}"
                               min="-2" max="2" step="0.1">
                    </div>

                    <div class="form-group">
                        <label class="checkbox-label">
                            <input type="checkbox" name="stream" ${model?.stream !== false ? 'checked' : ''}>
                            启用流式输出
                        </label>
                    </div>
                </div>
            </form>
        `;
    },

    getFormData(modal) {
        const form = modal.querySelector('#modelForm');
        const formData = new FormData(form);
        const data = {};

        for (const [key, value] of formData.entries()) {
            if (key === 'is_default' || key === 'is_active' || key === 'stream') {
                data[key] = form.querySelector(`[name="${key}"]`).checked;
            } else if (key === 'temperature' || key === 'max_tokens' || key === 'top_p' ||
                       key === 'frequency_penalty' || key === 'presence_penalty') {
                data[key] = parseFloat(value) || 0;
            } else {
                data[key] = value;
            }
        }

        return data;
    },

    async createModel(data) {
        try {
            const response = await fetch('http://localhost:8788/api/agent/llm-configs', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('模型创建成功', 'success');
                // 通知主界面刷新模型选项
                if (window.agentHandlers && window.agentHandlers.loadModelOptions) {
                    window.agentHandlers.loadModelOptions();
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

    async updateModel(configId, data) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/llm-configs/${configId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('模型更新成功', 'success');
                // 通知主界面刷新模型选项
                if (window.agentHandlers && window.agentHandlers.loadModelOptions) {
                    window.agentHandlers.loadModelOptions();
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

    editModel(configId) {
        const model = this.state.models.find(m => m.config_id === configId);
        if (model) {
            this.showModelDialog(model);
        }
    },

    async deleteModel(configId) {
        if (!confirm('确定要删除这个模型配置吗？')) {
            return;
        }

        try {
            const response = await fetch(`http://localhost:8788/api/agent/llm-configs/${configId}`, {
                method: 'DELETE'
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('模型删除成功', 'success');
                await this.loadModels();
                // 通知主界面刷新模型选项
                if (window.agentHandlers && window.agentHandlers.loadModelOptions) {
                    window.agentHandlers.loadModelOptions();
                }
            } else {
                window.showNotification?.('删除失败', 'error');
            }
        } catch (error) {
            window.showNotification?.('删除失败: ' + error.message, 'error');
        }
    },

    async testConnection(configId, testData = null) {
        let data;

        if (testData) {
            data = testData;
        } else {
            const model = this.state.models.find(m => m.config_id === configId);
            if (!model) return;
            data = {
                api_endpoint: model.api_endpoint,
                api_key: model.api_key,
                model_name: model.model_name,
                provider: model.provider
            };
        }

        try {
            window.showNotification?.('正在测试连接...', 'info');

            const response = await fetch('http://localhost:8788/api/agent/llm-configs/test', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });
            const result = await response.json();

            if (result.success) {
                window.showNotification?.('连接测试成功！', 'success');
            } else {
                window.showNotification?.('连接测试失败: ' + (result.error || '未知错误'), 'error');
            }
        } catch (error) {
            window.showNotification?.('连接测试失败: ' + error.message, 'error');
        }
    },

    async exportModels() {
        try {
            const response = await fetch('http://localhost:8788/api/agent/llm-configs/export/all');
            const result = await response.json();

            if (result.success) {
                const dataStr = JSON.stringify(result.data, null, 2);
                const blob = new Blob([dataStr], { type: 'application/json' });
                const url = URL.createObjectURL(blob);
                const a = document.createElement('a');
                a.href = url;
                a.download = `llm-configs-${Date.now()}.json`;
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
                        <h3>导入模型配置</h3>
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

                const response = await fetch('http://localhost:8788/api/agent/llm-configs/import', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(configs)
                });
                const result = await response.json();

                if (result.success) {
                    window.showNotification?.(`成功导入 ${result.data.created} 个配置`, 'success');
                    modal.remove();
                    await this.loadModels();
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

        // 隐藏模型管理页面
        const pageContainer = mainContent.querySelector('.model-management-page-container');
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

export default ModelManagementPage;
