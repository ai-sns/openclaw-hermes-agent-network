/**
 * Agent Settings Dialog
 * Agent settings dialog - supports Google A2A protocol
 */

const AgentSettingsDialog = {
    currentAgent: null,
    llmConfigs: [],
    roleConfigs: [],

    /**
     * Resolve URL or path
     */
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text === null || text === undefined ? '' : String(text);
        return div.innerHTML;
    },

    /**
     * Show Agent settings dialog
     * @param {object} agent - Agent object; if null, create a new Agent
     */
    async show(agent = null) {
        this.currentAgent = agent;

        // Load LLM and Role configs
        await this.loadConfigs();

        const isEdit = agent !== null;
        const title = isEdit ? `Edit Agent: ${agent.name}` : 'Create New Agent';

        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        // Generate a unique ID to ensure elements are unique per instance
        this.formId = 'agent-settings-form-' + Date.now();

        const content = this.renderDialogContent(agent);

        // Show modal
        Modal.show({
            title: title,
            content: content,
            confirmText: isEdit ? 'Save' : 'Create',
            showCancel: true,
            width: '600px',
            onOpen: (modalInstance) => {
                // Bind events for current instance
                this.bindEvents(modalInstance);
            },
            onConfirm: () => this.handleSave()
        });
    },

    /**
     * Load LLM and Role configs
     */
    async loadConfigs() {
        try {
            // Load LLM configs
            const llmResponse = await fetch(this.resolve('/api/agent/llm-configs'));
            const llmResult = await llmResponse.json();
            this.llmConfigs = llmResult.success ? llmResult.data : [];

            // Load Role configs
            const roleResponse = await fetch(this.resolve('/api/agent/role-configs'));
            const roleResult = await roleResponse.json();
            this.roleConfigs = roleResult.success ? roleResult.data : [];
        } catch (error) {
            console.error('Failed to load configs:', error);
            this.llmConfigs = [];
            this.roleConfigs = [];
        }
    },

    /**
     * Render dialog content
     */
    renderDialogContent(agent) {
        const data = agent || {
            name: '',
            description: '',
            agent_type: 'local',
            framework: '',
            framework_other: '',
            llm_provider: '',
            model_description: '',
            model_config_id: '',
            role_id: '',
            url: '',
            version: '1.0.0',
            protocol_version: '0.3',
            provider_organization: 'AI-SNS Platform',
            provider_url: 'https://ai-sns.com',
            documentation_url: '',
            icon_url: '',
            capabilities: {
                streaming: true,
                pushNotifications: true,
                stateTransitionHistory: false
            },
            default_input_modes: ['text'],
            default_output_modes: ['text']
        };

        const basicTabId = this.formId + '-basic';
        const a2aTabId = this.formId + '-a2a';

        const isEdit = agent !== null;
        const agentType = (data.agent_type || 'local').toLowerCase();
        const agentTypeLocked = isEdit && agentType === 'remote';

        return `
            <div class="agent-settings-form" id="${this.formId}">
                <!-- Tab navigation -->
                <div class="settings-tabs">
                    <button class="settings-tab-btn active" data-tab="basic" data-target="${basicTabId}">Basic Information</button>
                    <button class="settings-tab-btn" data-tab="a2a" data-target="${a2aTabId}">A2A Protocol</button>
                </div>

                <!-- Basic Information tab -->
                <div class="settings-tab-pane active" id="${basicTabId}" data-tab="basic">
                    <div class="dialog-section">
                        <h4>General</h4>
                        <div class="form-group">
                            <label>Agent Name *</label>
                            <input type="text" class="form-input" id="agentName" value="${this.escapeHtml(data.name)}" placeholder="e.g. GPT-4 Assistant">
                        </div>

                        <div class="form-group">
                            <label>Description</label>
                            <textarea class="form-input" id="agentDescription" rows="3" placeholder="Briefly describe the functionality and purpose of this Agent">${this.escapeHtml(data.description || '')}</textarea>
                        </div>

                        <div class="form-group">
                            <label>Agent Type *</label>
                            <select class="form-input" id="agentType" ${agentTypeLocked ? 'disabled' : ''}>
                                <option value="local" ${agentType === 'local' ? 'selected' : ''}>Local Agent</option>
                                <option value="remote" ${agentType === 'remote' ? 'selected' : ''}>Remote Agent</option>
                            </select>
                        </div>
                    </div>

                    <div class="dialog-section agent-remote-only">
                        <h4>Remote Configuration</h4>
                        <div class="form-group">
                            <label>Framework *</label>
                            <select class="form-input" id="agentFramework">
                                <option value="">Select a framework...</option>
                                <option value="Openclaw" ${String(data.framework || '') === 'Openclaw' ? 'selected' : ''}>Openclaw</option>
                                <option value="Langchain" ${String(data.framework || '') === 'Langchain' ? 'selected' : ''}>Langchain</option>
                                <option value="Autogen" ${String(data.framework || '') === 'Autogen' ? 'selected' : ''}>Autogen</option>
                                <option value="Autogpt" ${String(data.framework || '') === 'Autogpt' ? 'selected' : ''}>Autogpt</option>
                                <option value="Other" ${String(data.framework || '') === 'Other' ? 'selected' : ''}>Other</option>
                            </select>
                        </div>

                        <div class="form-group" id="agentFrameworkOtherGroup" style="display: ${String(data.framework || '') === 'Other' ? '' : 'none'};">
                            <label>Other Framework *</label>
                            <input type="text" class="form-input" id="agentFrameworkOther" value="${this.escapeHtml(data.framework_other || '')}" placeholder="Enter framework name">
                        </div>

                        <div class="form-group">
                            <label>LLM Provider *</label>
                            <input type="text" class="form-input" id="agentLLMProvider" value="${this.escapeHtml(data.llm_provider || '')}" placeholder="e.g. OpenAI">
                        </div>

                        <div class="form-group">
                            <label>Model Description *</label>
                            <input type="text" class="form-input" id="agentModelDescription" value="${this.escapeHtml(data.model_description || '')}" placeholder="Describe the model used by your framework e.g. gpt-4o">
                        </div>
                    </div>

                    <div class="dialog-section agent-local-only">
                        <h4>Configuration</h4>
                        <div class="form-group">
                            <label>LLM Model *</label>
                            <select class="form-input" id="agentModelConfig">
                                <option value="">Select a model...</option>
                                ${this.llmConfigs.map(config => `
                                    <option value="${config.config_id}" ${data.model_config_id === config.config_id ? 'selected' : ''}>
                                        ${config.name}${config.provider ? ` (${config.provider})` : ''}
                                    </option>
                                `).join('')}
                            </select>
                        </div>

                        <div class="form-group">
                            <label>Role Configuration *</label>
                            <select class="form-input" id="agentRoleConfig">
                                <option value="">Select a role...</option>
                                ${this.roleConfigs.map(role => `
                                    <option value="${role.role_id}" ${data.role_id === role.role_id ? 'selected' : ''}>
                                        ${role.name}${role.category ? ` - ${role.category}` : ''}
                                    </option>
                                `).join('')}
                            </select>
                        </div>
                    </div>
                </div>

                <!-- A2A Protocol tab -->
                <div class="settings-tab-pane" id="${a2aTabId}" data-tab="a2a">
                    <div class="dialog-section">
                        <h4>Endpoint</h4>
                        <div class="form-group">
                            <label>A2A Endpoint URL *</label>
                            <input type="text" class="form-input" id="agentUrl" value="${this.escapeHtml(data.url)}" placeholder="">
                            <small class="form-hint">A2A protocol access address for the Agent</small>
                        </div>
                    </div>

                    <div class="agent-local-only">
                        <div class="dialog-section">
                            <h4>Protocol Details</h4>
                            <div class="form-row">
                                <div class="form-group" style="flex: 1;">
                                    <label>Agent Version</label>
                                    <input type="text" class="form-input" id="agentVersion" value="${this.escapeHtml(data.version)}" placeholder="1.0.0">
                                </div>
                                <div class="form-group" style="flex: 1;">
                                    <label>Protocol Version</label>
                                    <input type="text" class="form-input" id="agentProtocolVersion" value="${this.escapeHtml(data.protocol_version)}" placeholder="0.3">
                                </div>
                            </div>
                        </div>

                        <div class="dialog-section">
                            <h4>Capabilities</h4>
                            <div class="form-group">
                                <div class="checkbox-group">
                                    <label class="checkbox-label">
                                        <input type="checkbox" id="capStreaming" ${data.capabilities?.streaming ? 'checked' : ''}>
                                        <span>Streaming</span>
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" id="capPushNotifications" ${data.capabilities?.pushNotifications ? 'checked' : ''}>
                                        <span>Push Notifications</span>
                                    </label>
                                    <label class="checkbox-label">
                                        <input type="checkbox" id="capStateHistory" ${data.capabilities?.stateTransitionHistory ? 'checked' : ''}>
                                        <span>State Transition History</span>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <div class="dialog-section">
                            <h4>Interaction Modes</h4>
                            <div class="form-row">
                                <div class="form-group" style="flex: 1;">
                                    <label>Input Modes</label>
                                    <select class="form-input" id="agentInputModes" multiple size="3">
                                        <option value="text" ${data.default_input_modes?.includes('text') ? 'selected' : ''}>Text</option>
                                        <option value="image" ${data.default_input_modes?.includes('image') ? 'selected' : ''}>Image</option>
                                        <option value="audio" ${data.default_input_modes?.includes('audio') ? 'selected' : ''}>Audio</option>
                                        <option value="video" ${data.default_input_modes?.includes('video') ? 'selected' : ''}>Video</option>
                                        <option value="file" ${data.default_input_modes?.includes('file') ? 'selected' : ''}>File</option>
                                    </select>
                                    <small class="form-hint">Hold Ctrl to select multiple</small>
                                </div>
                                <div class="form-group" style="flex: 1;">
                                    <label>Output Modes</label>
                                    <select class="form-input" id="agentOutputModes" multiple size="3">
                                        <option value="text" ${data.default_output_modes?.includes('text') ? 'selected' : ''}>Text</option>
                                        <option value="image" ${data.default_output_modes?.includes('image') ? 'selected' : ''}>Image</option>
                                        <option value="audio" ${data.default_output_modes?.includes('audio') ? 'selected' : ''}>Audio</option>
                                        <option value="video" ${data.default_output_modes?.includes('video') ? 'selected' : ''}>Video</option>
                                        <option value="file" ${data.default_output_modes?.includes('file') ? 'selected' : ''}>File</option>
                                    </select>
                                    <small class="form-hint">Hold Ctrl to select multiple</small>
                                </div>
                            </div>
                        </div>

                        <div class="dialog-section">
                            <h4>Provider Info</h4>
                            <div class="form-group">
                                <label>Provider Organization</label>
                                <input type="text" class="form-input" id="agentProviderOrg" value="${this.escapeHtml(data.provider_organization)}" placeholder="AI-SNS Platform">
                            </div>

                            <div class="form-group">
                                <label>Provider URL</label>
                                <input type="text" class="form-input" id="agentProviderUrl" value="${this.escapeHtml(data.provider_url)}" placeholder="https://ai-sns.com">
                            </div>

                            <div class="form-group">
                                <label>Documentation URL</label>
                                <input type="text" class="form-input" id="agentDocUrl" value="${this.escapeHtml(data.documentation_url || '')}" placeholder="https://docs.ai-sns.com">
                            </div>

                            <div class="form-group">
                                <label>Icon URL</label>
                                <input type="text" class="form-input" id="agentIconUrl" value="${this.escapeHtml(data.icon_url || '')}" placeholder="https://ai-sns.com/icon.png">
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Bind events
     */
    bindEvents(modalInstance) {
        console.log('AgentSettingsDialog: bindEvents called');

        // Get current instance container
        const form = document.getElementById(this.formId);
        if (!form) {
            console.error('Form container not found');
            return;
        }

        // Get current instance tab container
        const tabsContainer = form.querySelector('.settings-tabs');
        if (tabsContainer) {
            // Use a named function so it can be removed
            if (this._tabClickHandler) {
                tabsContainer.removeEventListener('click', this._tabClickHandler);
            }

            // Create a new event handler
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

            // Bind events
            tabsContainer.addEventListener('click', this._tabClickHandler);
            console.log('Tab events bound using event delegation');
        } else {
            console.error('Tabs container not found');
        }

        const agentTypeEl = form.querySelector('#agentType');
        if (agentTypeEl) {
            if (this._agentTypeChangeHandler) {
                agentTypeEl.removeEventListener('change', this._agentTypeChangeHandler);
            }
            this._agentTypeChangeHandler = () => this.applyAgentTypeVisibility();
            agentTypeEl.addEventListener('change', this._agentTypeChangeHandler);
        }

        const frameworkEl = form.querySelector('#agentFramework');
        if (frameworkEl) {
            if (this._frameworkChangeHandler) {
                frameworkEl.removeEventListener('change', this._frameworkChangeHandler);
            }
            this._frameworkChangeHandler = () => this.applyFrameworkVisibility();
            frameworkEl.addEventListener('change', this._frameworkChangeHandler);
        }

        this.applyAgentTypeVisibility();
        this.applyFrameworkVisibility();
    },

    /**
     * Apply agent type visibility
     */
    applyAgentTypeVisibility() {
        const form = document.getElementById(this.formId);
        if (!form) return;

        const agentTypeEl = form.querySelector('#agentType');
        const agentType = (agentTypeEl ? agentTypeEl.value : 'local').toLowerCase();
        const isRemote = agentType === 'remote';

        form.querySelectorAll('.agent-local-only').forEach(el => {
            el.style.display = isRemote ? 'none' : '';
        });

        form.querySelectorAll('.agent-remote-only').forEach(el => {
            el.style.display = isRemote ? '' : 'none';
        });
    },

    applyFrameworkVisibility() {
        const form = document.getElementById(this.formId);
        if (!form) return;

        const agentTypeEl = form.querySelector('#agentType');
        const agentType = (agentTypeEl ? agentTypeEl.value : 'local').toLowerCase();
        const isRemote = agentType === 'remote';

        const frameworkEl = form.querySelector('#agentFramework');
        const otherGroup = form.querySelector('#agentFrameworkOtherGroup');
        if (!frameworkEl || !otherGroup) return;

        if (!isRemote) {
            otherGroup.style.display = 'none';
            return;
        }

        const framework = String(frameworkEl.value || '');
        otherGroup.style.display = framework === 'Other' ? '' : 'none';
    },

    /**
     * Switch tabs
     */
    switchTab(tab) {
        console.log('switchTab called with tab:', tab);

        // Get current form container
        const form = document.getElementById(this.formId);
        if (!form) return;

        // Find the clicked button to get the target tab ID
        const clickedBtn = form.querySelector(`[data-tab="${tab}"].settings-tab-btn`);
        if (!clickedBtn) return;

        const targetTabId = clickedBtn.getAttribute('data-target');
        if (!targetTabId) return;

        // Hide all tab panes
        const tabPanes = form.querySelectorAll('.settings-tab-pane');
        tabPanes.forEach(pane => {
            pane.classList.remove('active');
        });

        // Show target tab pane
        const targetPane = document.getElementById(targetTabId);
        if (targetPane) {
            targetPane.classList.add('active');
        }

        // Remove active state from all tab buttons
        const tabBtns = form.querySelectorAll('.settings-tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.remove('active');
        });

        // Activate current button
        clickedBtn.classList.add('active');
    },

    /**
     * Switch tabs with explicit context
     */
    switchTabWithContext(tab, form, tabBtn) {
        console.log('Switching tab with context:', tab);

        // Get target tab ID
        const targetTabId = tabBtn.getAttribute('data-target');
        if (!targetTabId) return;

        // Hide all tab panes
        const tabPanes = form.querySelectorAll('.settings-tab-pane');
        tabPanes.forEach(pane => {
            pane.classList.remove('active');
        });

        // Show target tab pane
        const targetPane = document.getElementById(targetTabId);
        if (targetPane) {
            targetPane.classList.add('active');
        }

        // Remove active state from all tab buttons
        const tabBtns = form.querySelectorAll('.settings-tab-btn');
        tabBtns.forEach(btn => {
            btn.classList.remove('active');
        });

        // Activate current button
        tabBtn.classList.add('active');
    },

    /**
     * Save Agent configuration
     */
    async handleSave() {
        try {
            // Collect basic info
            const name = document.getElementById('agentName').value.trim();
            const description = document.getElementById('agentDescription').value.trim();
            const agentType = (document.getElementById('agentType')?.value || 'local').toLowerCase();

            const isRemote = agentType === 'remote';
            const modelConfigId = document.getElementById('agentModelConfig')?.value;
            const roleId = document.getElementById('agentRoleConfig')?.value;

            // Validate required fields
            if (!name) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Please enter Agent name');
                }
                return false;
            }

            // Collect A2A protocol fields
            const url = document.getElementById('agentUrl').value.trim();

            if (!url) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Please enter A2A endpoint URL');
                }
                return false;
            }

            const framework = isRemote ? String(document.getElementById('agentFramework')?.value || '').trim() : '';
            const frameworkOther = isRemote ? String(document.getElementById('agentFrameworkOther')?.value || '').trim() : '';
            const llmProvider = isRemote ? String(document.getElementById('agentLLMProvider')?.value || '').trim() : '';
            const modelDescription = isRemote ? String(document.getElementById('agentModelDescription')?.value || '').trim() : '';

            if (isRemote) {
                if (!framework) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please select framework');
                    }
                    return false;
                }

                if (framework === 'Other' && !frameworkOther) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please enter framework name');
                    }
                    return false;
                }

                if (!llmProvider) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please enter LLM provider');
                    }
                    return false;
                }

                if (!modelDescription) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please enter model description');
                    }
                    return false;
                }
            }

            if (!isRemote) {
                if (!modelConfigId) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please select LLM model');
                    }
                    return false;
                }

                if (!roleId) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please select role configuration');
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

            // Build request data
            const data = {
                name,
                description,

                agent_type: agentType,
                url,
                is_active: true
            };

            if (isRemote) {
                data.framework = framework;
                data.framework_other = framework === 'Other' ? frameworkOther : '';
                data.llm_provider = llmProvider;
                data.model_description = modelDescription;
            }

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
            }

            // Send request
            const isEdit = this.currentAgent !== null;
            const endpoint = isEdit
                ? this.resolve(`/api/agent/${this.currentAgent.id}`)
                : this.resolve('/api/agent');

            const method = isEdit ? 'PUT' : 'POST';

            const response = await fetch(endpoint, {
                method: method,
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(data)
            });

            const result = await response.json();

            if (result.success) {
                if (typeof Notification !== 'undefined') {
                    Notification.success(isEdit ? 'Agent updated successfully' : 'Agent created successfully');
                }

                const agentId = isEdit ? this.currentAgent.id : result.data?.id;

                // In edit mode, reload backend agent instance to apply the new config
                if (isEdit && agentId) {
                    try {
                        // Reload backend agent instance
                        const reloadResponse = await fetch(this.resolve(`/api/agent/${agentId}/reload`), {
                            method: 'POST'
                        });

                        const reloadResult = await reloadResponse.json();
                        if (reloadResult.success) {
                            console.log(`[AgentSettingsDialog] Agent ${agentId} instance reloaded`);
                        }

                        // Update frontend model-selector and role-selector
                        if (window.multiAgentHandlers) {
                            // Reload options and select the new config
                            await window.multiAgentHandlers.loadModelOptionsForAgent(agentId);
                            await window.multiAgentHandlers.loadRoleOptionsForAgent(agentId);
                            console.log(`[AgentSettingsDialog] Agent ${agentId} frontend selectors updated`);
                        }
                    } catch (error) {
                        console.error('[AgentSettingsDialog] Failed to reload Agent configuration:', error);
                        // Do not block closing the dialog, but show warning
                        if (typeof Notification !== 'undefined') {
                            Notification.warning('Configuration saved, but reload failed. Please refresh the page.');
                        }
                    }
                }

                // Refresh Agent list (new architecture)
                if (window.AgentSidebar && window.AgentSidebar.reload) {
                    await window.AgentSidebar.reload();
                } else if (window.agentHandlers && window.agentHandlers.loadAgentList) {
                    // Backwards compatible: if new method does not exist, use legacy method
                    await window.agentHandlers.loadAgentList();
                }

                if (agentId) {
                    window.dispatchEvent(new CustomEvent('agent-updated', {
                        detail: {
                            agentId,
                            name,
                            description,
                            agent: result.data
                        }
                    }));
                }

                // If creating a new agent, refresh management UI
                if (!isEdit) {
                    console.log('[AgentSettingsDialog] Refreshing management UI to display the newly created Agent');
                    // Check whether management UI is open
                    const agentManageList = document.getElementById('agentManageList');
                    if (agentManageList && window.AgentSidebar && window.AgentSidebar.fetchAllAgentsForManage) {
                        const agents = await window.AgentSidebar.fetchAllAgentsForManage();
                        agentManageList.innerHTML = window.AgentSidebar.renderAgentManageItems(agents);
                    }
                }

                // If creating a new agent, re-initialize multi-agent system
                if (!isEdit && window.multiAgentHandlers && window.multiAgentHandlers.init) {
                    console.log('[AgentSettingsDialog] Creating a new Agent, re-initializing multi-agent system');
                    await window.multiAgentHandlers.init();
                }

                return true; // Close dialog
            }

            throw new Error(result.error || 'Failed to save');
        } catch (error) {
            console.error('Failed to save Agent:', error);
            if (typeof Notification !== 'undefined') {
                Notification.error('Failed to save: ' + error.message);
            }
            return false; // Keep dialog open
        }
    },
};

// Export to global
if (typeof window !== 'undefined') {
    window.AgentSettingsDialog = AgentSettingsDialog;
}

export default AgentSettingsDialog;
