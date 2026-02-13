/**
 * Agent Settings Dialog
 * Agent 配置对话框 - 支持 Google A2A 协议和区块链钱包
 */

const AgentSettingsDialog = {
    currentAgent: null,
    llmConfigs: [],
    roleConfigs: [],

    /**
     * 显示 Agent 配置对话框
     * @param {object} agent - Agent 对象，如果为 null 则创建新 Agent
     */
    async show(agent = null) {
        this.currentAgent = agent;

        // 加载 LLM 和 Role 配置
        await this.loadConfigs();

        const isEdit = agent !== null;
        const title = isEdit ? `编辑 Agent: ${agent.name}` : '创建新 Agent';

        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        // 生成唯一ID，确保每个实例的元素都有唯一标识
        this.formId = 'agent-settings-form-' + Date.now();
        const basicTabId = this.formId + '-basic';
        const a2aTabId = this.formId + '-a2a';
        const walletTabId = this.formId + '-wallet';

        const content = this.renderDialogContent(agent);

        // 显示模态框
        Modal.show({
            title: title,
            content: content,
            confirmText: isEdit ? '保存' : '创建',
            showCancel: true,
            width: '800px',
            onOpen: (modalInstance) => {
                // 绑定事件到当前实例
                this.bindEvents(modalInstance);
            },
            onConfirm: () => this.handleSave()
        });
    },

    /**
     * 加载 LLM 和 Role 配置
     */
    async loadConfigs() {
        try {
            // 加载 LLM 配置
            const llmResponse = await fetch('http://localhost:8788/api/agent/llm-configs');
            const llmResult = await llmResponse.json();
            this.llmConfigs = llmResult.success ? llmResult.data : [];

            // 加载 Role 配置
            const roleResponse = await fetch('http://localhost:8788/api/agent/role-configs');
            const roleResult = await roleResponse.json();
            this.roleConfigs = roleResult.success ? roleResult.data : [];
        } catch (error) {
            console.error('加载配置失败:', error);
            this.llmConfigs = [];
            this.roleConfigs = [];
        }
    },

    /**
     * 渲染对话框内容
     */
    renderDialogContent(agent) {
        // 生成唯一ID，确保每个实例的元素都有唯一标识
        this.formId = 'agent-settings-form-' + Date.now();
        const basicTabId = this.formId + '-basic';
        const a2aTabId = this.formId + '-a2a';
        const walletTabId = this.formId + '-wallet';

        const data = agent || {
            name: '',
            description: '',
            agent_type: 'local',
            model_config_id: '',
            role_id: '',
            url: '',
            version: '1.0.0',
            protocol_version: '0.3',
            provider_organization: 'AI-SNS Platform',
            provider_url: 'https://ai-sns.com',
            documentation_url: '',
            icon_url: '',
            wallet_address: '',
            capabilities: {
                streaming: true,
                pushNotifications: true,
                stateTransitionHistory: false
            },
            default_input_modes: ['text'],
            default_output_modes: ['text']
        };

        const isEdit = agent !== null;
        const agentType = (data.agent_type || 'local').toLowerCase();
        const agentTypeLocked = isEdit && agentType === 'remote';

        return `
            <div class="agent-settings-form" id="${this.formId}">
                <!-- 页签导航 -->
                <div class="settings-tabs">
                    <button class="settings-tab-btn active" data-tab="basic" data-target="${basicTabId}">基本信息</button>
                    <button class="settings-tab-btn" data-tab="a2a" data-target="${a2aTabId}">A2A 协议</button>
                    <button class="settings-tab-btn" data-tab="wallet" data-target="${walletTabId}">区块链钱包</button>
                </div>

                <!-- 基本信息页签 -->
                <div class="settings-tab-pane active" id="${basicTabId}" data-tab="basic">
                    <div class="form-group">
                        <label>Agent 名称 *</label>
                        <input type="text" class="form-input" id="agentName" value="${this.escapeHtml(data.name)}" placeholder="例如: GPT-4 助手">
                    </div>

                    <div class="form-group">
                        <label>描述</label>
                        <textarea class="form-input" id="agentDescription" rows="3" placeholder="简要描述这个 Agent 的功能和用途">${this.escapeHtml(data.description || '')}</textarea>
                    </div>

                    <div class="form-group">
                        <label>Agent Type *</label>
                        <select class="form-input" id="agentType" ${agentTypeLocked ? 'disabled' : ''}>
                            <option value="local" ${agentType === 'local' ? 'selected' : ''}>Local agent</option>
                            <option value="remote" ${agentType === 'remote' ? 'selected' : ''}>Remote agent</option>
                        </select>
                    </div>

                    <div class="form-group agent-local-only">
                        <label>LLM 模型 *</label>
                        <select class="form-input" id="agentModelConfig">
                            <option value="">请选择模型...</option>
                            ${this.llmConfigs.map(config => `
                                <option value="${config.config_id}" ${data.model_config_id === config.config_id ? 'selected' : ''}>
                                    ${config.name}${config.provider ? ` (${config.provider})` : ''}
                                </option>
                            `).join('')}
                        </select>
                    </div>

                    <div class="form-group agent-local-only">
                        <label>角色配置 *</label>
                        <select class="form-input" id="agentRoleConfig">
                            <option value="">请选择角色...</option>
                            ${this.roleConfigs.map(role => `
                                <option value="${role.role_id}" ${data.role_id === role.role_id ? 'selected' : ''}>
                                    ${role.name}${role.category ? ` - ${role.category}` : ''}
                                </option>
                            `).join('')}
                        </select>
                    </div>
                </div>

                <!-- A2A 协议页签 -->
                <div class="settings-tab-pane" id="${a2aTabId}" data-tab="a2a">
                    <div class="form-group">
                        <label>A2A 端点 URL *</label>
                        <input type="text" class="form-input" id="agentUrl" value="${this.escapeHtml(data.url)}" placeholder="http://localhost:8788/a2a">
                        <small class="form-hint">Agent 的 A2A 协议访问地址</small>
                    </div>

                    <div class="agent-local-only">
                        <div class="form-row">
                            <div class="form-group" style="flex: 1;">
                                <label>Agent 版本</label>
                                <input type="text" class="form-input" id="agentVersion" value="${this.escapeHtml(data.version)}" placeholder="1.0.0">
                            </div>
                            <div class="form-group" style="flex: 1;">
                                <label>协议版本</label>
                                <input type="text" class="form-input" id="agentProtocolVersion" value="${this.escapeHtml(data.protocol_version)}" placeholder="0.3">
                            </div>
                        </div>

                        <div class="form-group">
                            <label>能力 (Capabilities)</label>
                            <div class="checkbox-group">
                                <label class="checkbox-label">
                                    <input type="checkbox" id="capStreaming" ${data.capabilities?.streaming ? 'checked' : ''}>
                                    <span>流式响应 (Streaming)</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" id="capPushNotifications" ${data.capabilities?.pushNotifications ? 'checked' : ''}>
                                    <span>推送通知 (Push Notifications)</span>
                                </label>
                                <label class="checkbox-label">
                                    <input type="checkbox" id="capStateHistory" ${data.capabilities?.stateTransitionHistory ? 'checked' : ''}>
                                    <span>状态转换历史 (State Transition History)</span>
                                </label>
                            </div>
                        </div>

                        <div class="form-row">
                            <div class="form-group" style="flex: 1;">
                                <label>输入模式</label>
                                <select class="form-input" id="agentInputModes" multiple size="3">
                                    <option value="text" ${data.default_input_modes?.includes('text') ? 'selected' : ''}>文本 (text)</option>
                                    <option value="image" ${data.default_input_modes?.includes('image') ? 'selected' : ''}>图像 (image)</option>
                                    <option value="audio" ${data.default_input_modes?.includes('audio') ? 'selected' : ''}>音频 (audio)</option>
                                    <option value="video" ${data.default_input_modes?.includes('video') ? 'selected' : ''}>视频 (video)</option>
                                    <option value="file" ${data.default_input_modes?.includes('file') ? 'selected' : ''}>文件 (file)</option>
                                </select>
                                <small class="form-hint">按住 Ctrl 多选</small>
                            </div>
                            <div class="form-group" style="flex: 1;">
                                <label>输出模式</label>
                                <select class="form-input" id="agentOutputModes" multiple size="3">
                                    <option value="text" ${data.default_output_modes?.includes('text') ? 'selected' : ''}>文本 (text)</option>
                                    <option value="image" ${data.default_output_modes?.includes('image') ? 'selected' : ''}>图像 (image)</option>
                                    <option value="audio" ${data.default_output_modes?.includes('audio') ? 'selected' : ''}>音频 (audio)</option>
                                    <option value="video" ${data.default_output_modes?.includes('video') ? 'selected' : ''}>视频 (video)</option>
                                    <option value="file" ${data.default_output_modes?.includes('file') ? 'selected' : ''}>文件 (file)</option>
                                </select>
                                <small class="form-hint">按住 Ctrl 多选</small>
                            </div>
                        </div>

                        <div class="form-group">
                            <label>提供者组织</label>
                            <input type="text" class="form-input" id="agentProviderOrg" value="${this.escapeHtml(data.provider_organization)}" placeholder="AI-SNS Platform">
                        </div>

                        <div class="form-group">
                            <label>提供者 URL</label>
                            <input type="text" class="form-input" id="agentProviderUrl" value="${this.escapeHtml(data.provider_url)}" placeholder="https://ai-sns.com">
                        </div>

                        <div class="form-group">
                            <label>文档 URL</label>
                            <input type="text" class="form-input" id="agentDocUrl" value="${this.escapeHtml(data.documentation_url || '')}" placeholder="https://docs.ai-sns.com">
                        </div>

                        <div class="form-group">
                            <label>图标 URL</label>
                            <input type="text" class="form-input" id="agentIconUrl" value="${this.escapeHtml(data.icon_url || '')}" placeholder="https://ai-sns.com/icon.png">
                        </div>
                    </div>
                </div>

                <!-- 区块链钱包页签 -->
                <div class="settings-tab-pane agent-local-only" id="${walletTabId}" data-tab="wallet">
                    <div class="form-group">
                        <label>钱包地址</label>
                        <div class="input-with-buttons">
                            <input type="text" class="form-input" id="agentWalletAddress" value="${this.escapeHtml(data.wallet_address || '')}" placeholder="0x..." readonly>
                            <button type="button" class="btn-secondary" id="createWalletBtn">创建新钱包</button>
                            <button type="button" class="btn-secondary" id="importWalletBtn">导入钱包</button>
                        </div>
                        <small class="form-hint">用于区块链交易和身份验证的以太坊钱包地址</small>
                    </div>

                    <div id="walletInfo" class="wallet-info" style="display: none;">
                        <div class="info-card">
                            <h4>钱包信息</h4>
                            <div class="info-row">
                                <span class="info-label">地址:</span>
                                <span class="info-value" id="walletAddressDisplay"></span>
                            </div>
                            <div class="info-row">
                                <span class="info-label">公钥:</span>
                                <span class="info-value" id="walletPublicKey"></span>
                            </div>
                            <div class="info-row" id="walletPrivateKeyRow" style="display: none;">
                                <span class="info-label">私钥:</span>
                                <span class="info-value warning" id="walletPrivateKey"></span>
                            </div>
                            <div class="warning-box" id="privateKeyWarning" style="display: none;">
                                ⚠️ 请务必安全保存私钥！私钥丢失将无法恢复钱包！建议复制并保存到安全的地方。
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 绑定事件
     */
    bindEvents(modalInstance) {
        console.log('AgentSettingsDialog: bindEvents called');
        
        // 获取当前实例的容器
        const form = document.getElementById(this.formId);
        if (!form) {
            console.error('Form container not found');
            return;
        }
        
        // 获取当前实例的标签容器
        const tabsContainer = form.querySelector('.settings-tabs');
        if (tabsContainer) {
            // 使用命名函数以便移除
            if (this._tabClickHandler) {
                tabsContainer.removeEventListener('click', this._tabClickHandler);
            }
            
            // 创建新的事件处理器
            this._tabClickHandler = (e) => {
                const target = e.target.closest('.settings-tab-btn');
                if (target) {
                    e.preventDefault();
                    e.stopPropagation();
                    const tab = target.dataset.tab;
                    console.log('Tab clicked:', tab);
                    this.switchTab(tab);
                }
            };
            
            // 绑定事件
            tabsContainer.addEventListener('click', this._tabClickHandler);
            console.log('Tab events bound using event delegation');
        } else {
            console.error('Tabs container not found');
        }

        // 钱包按钮事件（同样方式处理）
        this.bindWalletButtons();

        const agentTypeEl = form.querySelector('#agentType');
        if (agentTypeEl) {
            if (this._agentTypeChangeHandler) {
                agentTypeEl.removeEventListener('change', this._agentTypeChangeHandler);
            }
            this._agentTypeChangeHandler = () => this.applyAgentTypeVisibility();
            agentTypeEl.addEventListener('change', this._agentTypeChangeHandler);
        }

        this.applyAgentTypeVisibility();
    },

    applyAgentTypeVisibility() {
        const form = document.getElementById(this.formId);
        if (!form) return;

        const agentTypeEl = form.querySelector('#agentType');
        const agentType = (agentTypeEl ? agentTypeEl.value : 'local').toLowerCase();
        const isRemote = agentType === 'remote';

        form.querySelectorAll('.agent-local-only').forEach(el => {
            el.style.display = isRemote ? 'none' : '';
        });

        // Hide wallet tab button in remote mode
        const walletTabBtn = form.querySelector('.settings-tab-btn[data-tab="wallet"]');
        if (walletTabBtn) {
            walletTabBtn.style.display = isRemote ? 'none' : '';
        }

        // If current tab is wallet while remote, switch back to basic
        if (isRemote) {
            const activeBtn = form.querySelector('.settings-tab-btn.active');
            if (activeBtn && activeBtn.dataset.tab === 'wallet') {
                this.switchTab('basic');
            }
        }
    },

    /**
     * 绑定钱包按钮事件
     */
    bindWalletButtons() {
        // 获取当前实例的容器
        const form = document.getElementById(this.formId);
        if (!form) {
            console.error('Form container not found for wallet buttons');
            return;
        }
        
        const createBtn = form.querySelector('#createWalletBtn');
        const importBtn = form.querySelector('#importWalletBtn');
        
        if (createBtn) {
            if (this._createWalletHandler) {
                createBtn.removeEventListener('click', this._createWalletHandler);
            }
            this._createWalletHandler = () => this.createWallet();
            createBtn.addEventListener('click', this._createWalletHandler);
        }
        
        if (importBtn) {
            if (this._importWalletHandler) {
                importBtn.removeEventListener('click', this._importWalletHandler);
            }
            this._importWalletHandler = () => this.importWallet();
            importBtn.addEventListener('click', this._importWalletHandler);
        }
        
        console.log('Wallet button events bound successfully');
    },

    /**
     * 切换页签
     */
    switchTab(tab) {
        console.log('switchTab called with tab:', tab);

        // 获取当前表单容器
        const form = document.getElementById(this.formId);
        if (!form) return;

        // 查找当前按钮以获取目标标签页ID
        const clickedBtn = form.querySelector(`[data-tab="${tab}"].settings-tab-btn`);
        if (!clickedBtn) return;
        
        const targetTabId = clickedBtn.getAttribute('data-target');
        if (!targetTabId) return;

        // 隐藏所有标签页
        const tabPanes = form.querySelectorAll('.settings-tab-pane');
        tabPanes.forEach(pane => {
            pane.classList.remove('active');
        });

        // 显示目标标签页
        const targetPane = document.getElementById(targetTabId);
        if (targetPane) {
            targetPane.classList.add('active');
        }

        // 移除所有按钮的激活状态
        const tabBtns = form.querySelectorAll('.settings-tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.remove('active');
        });

        // 激活当前按钮
        clickedBtn.classList.add('active');
    },

    /**
     * 根据上下文切换标签页
     */
    switchTabWithContext(tab, form, tabBtn) {
        console.log('Switching tab with context:', tab);

        // 获取目标标签页ID
        const targetTabId = tabBtn.getAttribute('data-target');
        if (!targetTabId) return;

        // 隐藏所有标签页
        const tabPanes = form.querySelectorAll('.settings-tab-pane');
        tabPanes.forEach(pane => {
            pane.classList.remove('active');
        });

        // 显示目标标签页
        const targetPane = document.getElementById(targetTabId);
        if (targetPane) {
            targetPane.classList.add('active');
        }

        // 移除所有按钮的激活状态
        const tabBtns = form.querySelectorAll('.settings-tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.remove('active');
        });

        // 激活当前按钮
        tabBtn.classList.add('active');
    },

    /**
     * 创建钱包
     */
    async createWallet() {
        try {
            const response = await fetch('http://localhost:8788/api/wallet/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label: 'Agent Wallet' })
            });

            const result = await response.json();

            if (result.success && result.data) {
                const wallet = result.data;

                // 更新钱包地址输入框
                document.getElementById('agentWalletAddress').value = wallet.address;

                // 显示钱包信息
                this.displayWalletInfo(wallet, true);

                if (typeof Notification !== 'undefined') {
                    Notification.success('钱包创建成功！请务必保存私钥。');
                }
            } else {
                throw new Error(result.error || '创建钱包失败');
            }
        } catch (error) {
            console.error('创建钱包失败:', error);
            if (typeof Notification !== 'undefined') {
                Notification.error('创建钱包失败: ' + error.message);
            }
        }
    },

    /**
     * 导入钱包
     */
    importWallet() {
        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        Modal.show({
            title: '导入钱包',
            content: `
                <div class="form-group">
                    <label>私钥 *</label>
                    <input type="password" class="form-input" id="importPrivateKey" placeholder="请输入私钥 (带或不带 0x 前缀)">
                    <small class="form-hint">私钥将用于恢复您的钱包，请确保在安全环境中操作</small>
                </div>
            `,
            confirmText: '导入',
            showCancel: true,
            onConfirm: async () => {
                const privateKey = document.getElementById('importPrivateKey').value.trim();

                if (!privateKey) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('请输入私钥');
                    }
                    return false;
                }

                try {
                    const response = await fetch('http://localhost:8788/api/wallet/import', {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({
                            private_key: privateKey,
                            label: 'Agent Wallet'
                        })
                    });

                    const result = await response.json();

                    if (result.success && result.data) {
                        const wallet = result.data;

                        // 更新钱包地址输入框
                        document.getElementById('agentWalletAddress').value = wallet.address;

                        // 显示钱包信息（不显示私钥）
                        this.displayWalletInfo(wallet, false);

                        if (typeof Notification !== 'undefined') {
                            Notification.success('钱包导入成功！');
                        }

                        return true; // 关闭对话框
                    } else {
                        throw new Error(result.error || '导入钱包失败');
                    }
                } catch (error) {
                    console.error('导入钱包失败:', error);
                    if (typeof Notification !== 'undefined') {
                        Notification.error('导入钱包失败: ' + error.message);
                    }
                    return false; // 保持对话框打开
                }
            }
        });
    },

    /**
     * 显示钱包信息
     */
    displayWalletInfo(wallet, showPrivateKey = false) {
        // 使用 formId 来获取正确的元素
        const form = document.getElementById(this.formId);
        if (!form) return;

        const walletTabId = this.formId + '-wallet';
        const walletInfo = form.querySelector(`#${walletTabId}-info`);
        const addressDisplay = form.querySelector(`#${walletTabId}-address`);
        const publicKey = form.querySelector(`#${walletTabId}-public-key`);
        const privateKeyRow = form.querySelector(`#${walletTabId}-private-key-row`);
        const privateKey = form.querySelector(`#${walletTabId}-private-key`);
        const privateKeyWarning = form.querySelector(`#${walletTabId}-private-key-warning`);

        if (walletInfo) walletInfo.style.display = 'block';
        if (addressDisplay) addressDisplay.textContent = wallet.address;
        if (publicKey) publicKey.textContent = wallet.public_key;

        if (showPrivateKey && wallet.private_key) {
            if (privateKeyRow) privateKeyRow.style.display = 'flex';
            if (privateKey) privateKey.textContent = wallet.private_key;
            if (privateKeyWarning) privateKeyWarning.style.display = 'block';
        } else {
            if (privateKeyRow) privateKeyRow.style.display = 'none';
            if (privateKeyWarning) privateKeyWarning.style.display = 'none';
        }
    },

    /**
     * 保存 Agent 配置
     */
    async handleSave() {
        try {
            // 收集基本信息
            const name = document.getElementById('agentName').value.trim();
            const description = document.getElementById('agentDescription').value.trim();
            const agentType = (document.getElementById('agentType')?.value || 'local').toLowerCase();
            const isRemote = agentType === 'remote';
            const modelConfigId = document.getElementById('agentModelConfig')?.value;
            const roleId = document.getElementById('agentRoleConfig')?.value;

            // 验证必填字段
            if (!name) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('请输入 Agent 名称');
                }
                return false;
            }

            // 收集 A2A 协议字段
            const url = document.getElementById('agentUrl').value.trim();

            if (!url) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('请输入 A2A 端点 URL');
                }
                return false;
            }

            if (!isRemote) {
                if (!modelConfigId) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('请选择 LLM 模型');
                    }
                    return false;
                }

                if (!roleId) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('请选择角色配置');
                    }
                    return false;
                }
            }

            const version = isRemote ? undefined : document.getElementById('agentVersion')?.value?.trim();
            const protocolVersion = isRemote ? undefined : document.getElementById('agentProtocolVersion')?.value?.trim();

            const capabilities = isRemote ? undefined : {
                streaming: document.getElementById('capStreaming')?.checked,
                pushNotifications: document.getElementById('capPushNotifications')?.checked,
                stateTransitionHistory: document.getElementById('capStateHistory')?.checked
            };

            const inputModes = isRemote ? undefined : Array.from(document.getElementById('agentInputModes')?.selectedOptions || []).map(opt => opt.value);
            const outputModes = isRemote ? undefined : Array.from(document.getElementById('agentOutputModes')?.selectedOptions || []).map(opt => opt.value);

            const providerOrg = isRemote ? undefined : document.getElementById('agentProviderOrg')?.value?.trim();
            const providerUrl = isRemote ? undefined : document.getElementById('agentProviderUrl')?.value?.trim();
            const docUrl = isRemote ? undefined : document.getElementById('agentDocUrl')?.value?.trim();
            const iconUrl = isRemote ? undefined : document.getElementById('agentIconUrl')?.value?.trim();

            // 收集钱包地址
            const walletAddress = isRemote ? undefined : document.getElementById('agentWalletAddress')?.value?.trim();

            // 构建请求数据
            const data = {
                name,
                description,
                agent_type: agentType,
                url,
                is_active: true
            };

            if (!isRemote) {
                data.model_config_id = modelConfigId;
                data.role_id = roleId;
                data.version = version;
                data.protocol_version = protocolVersion;
                data.capabilities = capabilities;
                data.default_input_modes = inputModes;
                data.default_output_modes = outputModes;
                data.provider_organization = providerOrg;
                data.provider_url = providerUrl;
                data.documentation_url = docUrl;
                data.icon_url = iconUrl;
                data.wallet_address = walletAddress;
            }

            // 发送请求
            const isEdit = this.currentAgent !== null;
            const endpoint = isEdit
                ? `http://localhost:8788/api/agent/${this.currentAgent.id}`
                : 'http://localhost:8788/api/agent';

            const method = isEdit ? 'PUT' : 'POST';

            const response = await fetch(endpoint, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                if (typeof Notification !== 'undefined') {
                    Notification.success(isEdit ? 'Agent 更新成功' : 'Agent 创建成功');
                }

                const agentId = isEdit ? this.currentAgent.id : result.data?.id;

                // 如果是编辑模式，需要重新加载后端的 agent 实例以应用新配置
                if (isEdit && agentId) {
                    try {
                        // 重新加载后端 agent 实例
                        const reloadResponse = await fetch(`http://localhost:8788/api/agent/${agentId}/reload`, {
                            method: 'POST'
                        });
                        const reloadResult = await reloadResponse.json();
                        if (reloadResult.success) {
                            console.log(`[AgentSettingsDialog] Agent ${agentId} 实例已重新加载`);
                        }

                        // 更新前端的 model-selector 和 role-selector
                        if (window.multiAgentHandlers) {
                            // 重新加载选项并选中新配置
                            await window.multiAgentHandlers.loadModelOptionsForAgent(agentId);
                            await window.multiAgentHandlers.loadRoleOptionsForAgent(agentId);
                            console.log(`[AgentSettingsDialog] Agent ${agentId} 前端选择器已更新`);
                        }
                    } catch (error) {
                        console.error('[AgentSettingsDialog] 重新加载 Agent 配置失败:', error);
                        // 不阻止对话框关闭，但显示警告
                        if (typeof Notification !== 'undefined') {
                            Notification.warning('配置已保存，但重新加载失败，请刷新页面');
                        }
                    }
                }

                // 刷新 Agent 列表（使用新架构的方法）
                if (window.AgentSidebar && window.AgentSidebar.reload) {
                    await window.AgentSidebar.reload();
                } else if (window.agentHandlers && window.agentHandlers.loadAgentList) {
                    // 向后兼容：如果新方法不存在，使用旧方法
                    await window.agentHandlers.loadAgentList();
                }

                // 如果是创建新agent，需要刷新管理界面
                if (!isEdit) {
                    console.log('[AgentSettingsDialog] 刷新管理界面以显示新创建的Agent');
                    // 检查是否有打开的管理界面
                    const agentManageList = document.getElementById('agentManageList');
                    if (agentManageList && window.AgentSidebar && window.AgentSidebar.fetchAllAgentsForManage) {
                        const agents = await window.AgentSidebar.fetchAllAgentsForManage();
                        agentManageList.innerHTML = window.AgentSidebar.renderAgentManageItems(agents);
                    }
                }

                // 如果是创建新agent，需要重新初始化多Agent系统
                if (!isEdit && window.multiAgentHandlers && window.multiAgentHandlers.init) {
                    console.log('[AgentSettingsDialog] 创建了新Agent，重新初始化多Agent系统');
                    await window.multiAgentHandlers.init();
                }

                return true; // 关闭对话框
            } else {
                throw new Error(result.error || '保存失败');
            }
        } catch (error) {
            console.error('保存 Agent 失败:', error);
            if (typeof Notification !== 'undefined') {
                Notification.error('保存失败: ' + error.message);
            }
            return false; // 保持对话框打开
        }
    },

    /**
     * HTML 转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text || '';
        return div.innerHTML;
    }
};

// 导出到全局
if (typeof window !== 'undefined') {
    window.AgentSettingsDialog = AgentSettingsDialog;
}

export default AgentSettingsDialog;