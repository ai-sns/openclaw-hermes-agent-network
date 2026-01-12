/**
 * Multi-Agent Handlers - 多Agent事件处理扩展
 * 扩展agentHandlers以支持多Agent系统
 */

import agentState from './agentState.js';
import agentApi from './agentApi.js';
import AgentSidebar from './AgentSidebar.js';
import AgentPage from './AgentPage.js';

const multiAgentHandlers = {
    /**
     * 初始化多Agent系统
     */
    async init() {
        console.log('[MultiAgentHandlers] 开始初始化多Agent系统...');

        // 1. 从API加载Agent列表
        const response = await fetch('http://localhost:8788/api/agent');
        const result = await response.json();
        const agents = result.success ? (result.data || []) : [];

        if (agents.length === 0) {
            console.warn('[MultiAgentHandlers] 没有可用的Agent');
            return;
        }

        // 2. 保存到状态
        agentState.setAgents(agents);
        console.log('[MultiAgentHandlers] 已加载agents:', agents.length);

        // 3. 初始化AgentSidebar
        await AgentSidebar.init();

        // 4. 初始化AgentPage
        await AgentPage.init(agents);

        // 5. 设置当前agent为第一个
        if (agents.length > 0) {
            agentState.setCurrentAgent(agents[0].id);
            console.log('[MultiAgentHandlers] 当前agent:', agents[0].id);
        }

        // 6. 绑定全局事件
        this.bindGlobalEvents();

        // 7. 绑定所有agent的UI事件
        this.bindAllAgentEvents();

        // 8. 为当前agent加载聊天列表
        if (agents.length > 0) {
            this.loadChatListForAgent(agents[0].id);
        }

        // 9. 初始化流式监听
        this.initChatStreamListeners();

        console.log('[MultiAgentHandlers] 多Agent系统初始化完成');
    },

    /**
     * 绑定全局事件
     */
    bindGlobalEvents() {
        console.log('[MultiAgentHandlers] 绑定全局事件...');

        // 监听agent切换事件
        window.addEventListener('agent-switched', (e) => {
            const { agentId } = e.detail;
            console.log('[MultiAgentHandlers] Agent切换:', agentId);

            // 更新状态
            agentState.setCurrentAgent(agentId);

            // 加载该agent的聊天列表
            this.loadChatListForAgent(agentId);

            // 加载该agent的模型和角色选项
            this.loadModelOptionsForAgent(agentId);
            this.loadRoleOptionsForAgent(agentId);
        });

        // 监听new chat事件
        window.addEventListener('agent-new-chat', (e) => {
            const { agentId } = e.detail;
            console.log('[MultiAgentHandlers] New Chat:', agentId);

            // 切换到该agent
            agentState.setCurrentAgent(agentId);

            // 处理新建对话
            this.handleNewChatForAgent(agentId);
        });
    },

    /**
     * 绑定所有agent的UI事件
     */
    bindAllAgentEvents() {
        console.log('[MultiAgentHandlers] 绑定所有agent的UI事件...');

        // 1. 发送消息按钮 - 使用事件委托
        document.addEventListener('click', (e) => {
            const sendBtn = e.target.closest('.send-btn[data-agent-id]');
            if (sendBtn) {
                e.preventDefault();
                const agentId = parseInt(sendBtn.dataset.agentId);
                this.sendMessageForAgent(agentId);
            }
        });

        // 2. 输入框Enter键发送
        document.addEventListener('keydown', (e) => {
            const chatInput = e.target.closest('.agent-chat-input[data-agent-id]');
            if (chatInput && e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const agentId = parseInt(chatInput.dataset.agentId);
                this.sendMessageForAgent(agentId);
            }
        });

        // 3. 模型选择器
        document.addEventListener('change', (e) => {
            const modelSelector = e.target.closest('.model-selector[data-agent-id]');
            if (modelSelector) {
                const agentId = parseInt(modelSelector.dataset.agentId);
                const configId = modelSelector.value;
                agentState.setCurrentAgent(agentId);
                agentState.setModel(configId);
                this.loadAndApplyModelConfig(configId, agentId);
            }
        });

        // 4. 角色选择器
        document.addEventListener('change', (e) => {
            const roleSelector = e.target.closest('.role-selector[data-agent-id]');
            if (roleSelector) {
                const agentId = parseInt(roleSelector.dataset.agentId);
                const roleId = roleSelector.value;
                agentState.setCurrentAgent(agentId);
                agentState.setRole(roleId);
                this.loadAndApplyRoleConfig(roleId, agentId);
            }
        });

        // 5. 设置面板页签切换
        document.addEventListener('click', (e) => {
            const tab = e.target.closest('.settings-tab[data-agent-id]');
            if (tab) {
                const agentId = tab.dataset.agentId;
                const targetTab = tab.dataset.tab;

                // 切换同一agent的页签
                const tabs = document.querySelectorAll(`.settings-tab[data-agent-id="${agentId}"]`);
                const panes = document.querySelectorAll(`#settingsTabContent-${agentId} .tab-pane`);

                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                panes.forEach(pane => {
                    if (pane.dataset.tab === targetTab) {
                        pane.classList.add('active');
                    } else {
                        pane.classList.remove('active');
                    }
                });
            }
        });

        // 6. 设置面板折叠按钮
        document.addEventListener('click', (e) => {
            const collapseBtn = e.target.closest('.panel-collapse-btn[data-agent-id]');
            if (collapseBtn) {
                const agentId = collapseBtn.dataset.agentId;
                const panel = document.getElementById(`agentSettingsPanel-${agentId}`);
                const resizer = document.getElementById(`agentPanelResizer-${agentId}`);

                if (panel) {
                    const isCollapsed = panel.classList.toggle('collapsed');
                    if (resizer) {
                        resizer.classList.toggle('collapsed', isCollapsed);
                    }
                }
            }
        });

        // 7. Prompt保存按钮
        document.addEventListener('click', (e) => {
            const saveBtn = e.target.closest('.prompt-save-btn[data-agent-id]');
            if (saveBtn) {
                const agentId = parseInt(saveBtn.dataset.agentId);
                const textarea = document.getElementById(`systemPrompt-${agentId}`);
                if (textarea) {
                    this.saveRolePromptForAgent(textarea.value.trim(), agentId);
                }
            }
        });

        console.log('[MultiAgentHandlers] 所有事件绑定完成');
    },

    /**
     * 为特定agent加载聊天列表
     */
    async loadChatListForAgent(agentId) {
        const chatList = document.getElementById(`chatList-${agentId}`);
        if (!chatList) return;

        try {
            const response = await agentApi.getConversations(50);
            const conversations = response.data || [];

            const treeChildren = chatList.querySelector('.tree-children');
            if (!treeChildren) return;

            if (conversations.length === 0) {
                treeChildren.innerHTML = '<div class="empty-state">暂无对话</div>';
                return;
            }

            treeChildren.innerHTML = conversations.map((conv) => `
                <div class="tree-item" data-conversation-id="${conv.conversation_id}" data-agent-id="${agentId}">
                    <span class="item-text">${this.escapeHtml(conv.title || '新对话')}</span>
                </div>
            `).join('');

            // 绑定点击事件
            treeChildren.querySelectorAll('.tree-item').forEach(item => {
                item.addEventListener('click', () => {
                    const conversationId = item.dataset.conversationId;
                    const itemAgentId = parseInt(item.dataset.agentId);

                    // 移除其他项的active class
                    treeChildren.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
                    item.classList.add('active');

                    // 加载对话
                    this.loadConversationForAgent(conversationId, itemAgentId);
                });
            });

            console.log(`[MultiAgentHandlers] Agent ${agentId} 聊天列表已加载`);
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载聊天列表失败:`, error);
        }
    },

    /**
     * 为特定agent发送消息
     */
    async sendMessageForAgent(agentId) {
        console.log(`[MultiAgentHandlers] Agent ${agentId} 发送消息`);

        // 设置当前agent
        agentState.setCurrentAgent(agentId);

        const input = document.getElementById(`chatInput-${agentId}`);
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        const sendBtn = document.getElementById(`sendMessageBtn-${agentId}`);

        if (!input || !messagesContainer) return;

        const message = input.value.trim();
        if (!message) return;

        // 如果正在进行流式输出，不允许发送新消息
        if (agentState.getRequestId()) {
            return;
        }

        // 禁用发送按钮
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.classList.add('sending');
        }

        // 隐藏欢迎消息
        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.style.display = 'none';
        }

        // 获取当前时间
        const timeStr = new Date().toLocaleString('zh-CN', {
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });

        // 添加用户消息
        const userMessageHtml = `
            <div class="message-item user-message">
                <div class="message-header">
                    <div class="message-avatar user-avatar">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                    </div>
                    <span class="message-sender">You</span>
                    <span class="message-time">${timeStr}</span>
                </div>
                <div class="message-body">${this.escapeHtml(message)}</div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', userMessageHtml);

        input.value = '';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // 保存用户消息到历史
        agentState.addMessage('user', message);

        // 获取或生成 conversation_id
        let conversationId = agentState.getConversationId();
        if (!conversationId) {
            conversationId = agentState.generateConversationId();
            agentState.setConversationId(conversationId);
        }

        // 添加AI回复容器（带思考动画）
        const assistantMessageHtml = `
            <div class="message-item assistant-message streaming">
                <div class="message-header">
                    <div class="message-avatar assistant-avatar">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                    </div>
                    <span class="message-sender">AI Assistant</span>
                    <span class="message-time">${timeStr}</span>
                </div>
                <div class="message-body">
                    <div class="thinking-indicator">
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                        <span class="thinking-text">思考中...</span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', assistantMessageHtml);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // 生成请求ID
        const requestId = 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        agentState.setRequestId(requestId);
        agentState.clearStreamingContent();

        // 构建消息数组
        const messages = [
            { role: 'system', content: agentState.getSystemPrompt() },
            ...agentState.getChatHistory()
        ];

        // 启用发送按钮的函数
        const enableSendBtn = () => {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.classList.remove('sending');
            }
        };

        // 发起流式请求
        try {
            const modelConfig = agentState.currentModelConfig;
            const modelConfigId = modelConfig ? modelConfig.config_id : null;

            // 准备回调函数（绑定agentId）
            const callbacks = {
                onData: (data) => {
                    if (data.requestId === agentState.getRequestId()) {
                        agentState.appendStreamingContent(data.content);
                        this.updateStreamingMessageForAgent(agentState.getStreamingContent(), agentId);
                    }
                },
                onEnd: (data) => {
                    if (data.requestId === agentState.getRequestId()) {
                        this.finalizeStreamingMessageForAgent(agentId);
                        agentState.clearRequestId();
                        enableSendBtn();
                        // 重新加载聊天列表
                        this.loadChatListForAgent(agentId);
                    }
                },
                onError: (data) => {
                    if (data.requestId === agentState.getRequestId()) {
                        this.showStreamErrorForAgent(data.error, agentId);
                        agentState.clearRequestId();
                        enableSendBtn();
                    }
                }
            };

            await agentApi.sendMessageStream(messages, requestId, modelConfigId, modelConfig, conversationId, callbacks);

        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 发送消息失败:`, error);
            this.showStreamErrorForAgent(error.message, agentId);
            agentState.clearRequestId();
            enableSendBtn();
        }
    },

    /**
     * 更新流式消息显示（特定agent）
     */
    updateStreamingMessageForAgent(content, agentId) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        const streamingBody = messagesContainer.querySelector('.message-item.streaming .message-body');
        if (streamingBody) {
            streamingBody.innerHTML = this.renderMarkdown(content, true) + '<span class="cursor-blink"></span>';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    },

    /**
     * 完成流式消息（特定agent）
     */
    finalizeStreamingMessageForAgent(agentId) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        const streamingMsg = messagesContainer.querySelector('.message-item.streaming');
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                const content = agentState.getStreamingContent();
                streamingBody.innerHTML = this.renderMarkdown(content);
                this.highlightCodeBlocks(streamingBody);
            }
        }

        // 保存到历史
        agentState.addMessage('assistant', agentState.getStreamingContent());
        agentState.clearStreamingContent();
    },

    /**
     * 显示流错误（特定agent）
     */
    showStreamErrorForAgent(error, agentId) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        const streamingMsg = messagesContainer.querySelector('.message-item.streaming');
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            streamingMsg.classList.add('error-message');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                streamingBody.innerHTML = `<div class="error-content"><svg viewBox="0 0 24 24" width="16" height="16" fill="#d93025"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg><span>请求失败: ${this.escapeHtml(error)}</span></div>`;
            }
        }
    },

    /**
     * 处理新建对话（特定agent）
     */
    handleNewChatForAgent(agentId) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.style.display = 'block';
        } else {
            messagesContainer.innerHTML = '';
        }

        // 生成新的 conversation_id
        const newConversationId = agentState.generateConversationId();
        agentState.setConversationId(newConversationId);

        // 清空聊天历史
        agentState.clearChatHistory();

        // 取消所有选中状态
        const chatList = document.getElementById(`chatList-${agentId}`);
        if (chatList) {
            chatList.querySelectorAll('.tree-item').forEach(item => {
                item.classList.remove('active');
            });
        }

        console.log(`[MultiAgentHandlers] Agent ${agentId} 新建对话:`, newConversationId);
    },

    /**
     * 加载对话（特定agent）
     */
    async loadConversationForAgent(conversationId, agentId) {
        try {
            console.log(`[MultiAgentHandlers] Agent ${agentId} 加载对话:`, conversationId);

            agentState.setCurrentAgent(agentId);

            const response = await agentApi.getConversationMessages(conversationId);
            const messages = response.data || [];

            const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
            if (!messagesContainer) return;

            messagesContainer.innerHTML = '';

            agentState.setConversationId(conversationId);
            agentState.clearChatHistory();

            for (const msg of messages) {
                if (msg.role === 'system') continue;

                const messageHtml = this.createMessageElement(
                    msg.role,
                    msg.content,
                    this.formatTime(msg.create_time)
                );
                messagesContainer.insertAdjacentHTML('beforeend', messageHtml);
                agentState.addMessage(msg.role, msg.content);
            }

            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            console.log(`[MultiAgentHandlers] Agent ${agentId} 对话加载完成，消息数:`, messages.length);
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载对话失败:`, error);
        }
    },

    /**
     * 为特定agent加载模型选项
     */
    async loadModelOptionsForAgent(agentId) {
        const modelSelector = document.getElementById(`modelSelector-${agentId}`);
        if (!modelSelector) return;

        try {
            const response = await fetch('http://localhost:8788/api/agent/llm-configs');
            const result = await response.json();

            if (result.success && result.data) {
                const models = result.data.filter(m => m.is_active !== false);

                if (models.length > 0) {
                    let defaultModel = models.find(m => m.is_default) || models[0];

                    modelSelector.innerHTML = models.map(model => `
                        <option value="${model.config_id}" ${model.is_default ? 'selected' : ''}>
                            ${model.name}${model.provider ? ` (${model.provider})` : ''}
                        </option>
                    `).join('');

                    if (defaultModel) {
                        agentState.setModel(defaultModel.config_id);
                        await this.loadAndApplyModelConfig(defaultModel.config_id, agentId);
                    }
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载模型列表失败:`, error);
        }
    },

    /**
     * 为特定agent加载角色选项
     */
    async loadRoleOptionsForAgent(agentId) {
        const roleSelector = document.getElementById(`roleSelector-${agentId}`);
        if (!roleSelector) return;

        try {
            const response = await fetch('http://localhost:8788/api/agent/role-configs');
            const result = await response.json();

            if (result.success && result.data) {
                const roles = result.data.filter(r => r.is_active !== false);

                if (roles.length > 0) {
                    let defaultRole = roles.find(r => r.is_default) || roles[0];

                    roleSelector.innerHTML = roles.map(role => `
                        <option value="${role.role_id}" ${role.is_default ? 'selected' : ''}>
                            ${role.name}${role.category ? ` - ${role.category}` : ''}
                        </option>
                    `).join('');

                    if (defaultRole) {
                        agentState.setRole(defaultRole.role_id);
                        await this.loadAndApplyRoleConfig(defaultRole.role_id, agentId);
                    }
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载角色列表失败:`, error);
        }
    },

    /**
     * 加载并应用模型配置
     */
    async loadAndApplyModelConfig(configId, agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/llm-configs/${configId}`);
            const result = await response.json();

            if (result.success && result.data) {
                const modelConfig = result.data;
                agentState.currentModelConfig = modelConfig;
                this.populateParamTabForAgent(modelConfig, agentId);
                console.log(`[MultiAgentHandlers] Agent ${agentId} 模型配置已加载:`, modelConfig.name);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载模型配置失败:`, error);
        }
    },

    /**
     * 加载并应用角色配置
     */
    async loadAndApplyRoleConfig(roleId, agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/role-configs/${roleId}`);
            const result = await response.json();

            if (result.success && result.data) {
                const roleConfig = result.data;
                agentState.currentRoleConfig = roleConfig;
                this.populatePromptTabForAgent(roleConfig, agentId);
                console.log(`[MultiAgentHandlers] Agent ${agentId} 角色配置已加载:`, roleConfig.name);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载角色配置失败:`, error);
        }
    },

    /**
     * 填充Param页签（特定agent）
     */
    populateParamTabForAgent(modelConfig, agentId) {
        if (!modelConfig) return;

        const paramPane = document.querySelector(`#settingsTabContent-${agentId} [data-tab="param"]`);
        if (!paramPane) return;

        const inputs = paramPane.querySelectorAll('.param-input');
        inputs.forEach(input => {
            const label = input.closest('.param-label');
            if (!label) return;

            const labelText = label.querySelector('span')?.textContent.trim();

            if (labelText === 'Temperature' && modelConfig.temperature !== undefined) {
                input.value = modelConfig.temperature;
            } else if (labelText === 'Max Tokens' && modelConfig.max_tokens !== undefined) {
                input.value = modelConfig.max_tokens;
            } else if (labelText === 'Top P' && modelConfig.top_p !== undefined) {
                input.value = modelConfig.top_p;
            } else if (labelText === 'Frequency Penalty' && modelConfig.frequency_penalty !== undefined) {
                input.value = modelConfig.frequency_penalty;
            } else if (labelText === 'Presence Penalty' && modelConfig.presence_penalty !== undefined) {
                input.value = modelConfig.presence_penalty;
            }
        });

        const streamCheckbox = paramPane.querySelector('input[type="checkbox"]');
        if (streamCheckbox && modelConfig.stream !== undefined) {
            streamCheckbox.checked = modelConfig.stream;
        }
    },

    /**
     * 填充Prompt页签（特定agent）
     */
    populatePromptTabForAgent(roleConfig, agentId) {
        if (!roleConfig) return;

        const promptTextarea = document.getElementById(`systemPrompt-${agentId}`);
        if (promptTextarea && roleConfig.system_prompt) {
            promptTextarea.value = roleConfig.system_prompt;
        }
    },

    /**
     * 保存角色提示词（特定agent）
     */
    async saveRolePromptForAgent(prompt, agentId) {
        const currentConfig = agentState.currentRoleConfig;
        if (!currentConfig || !currentConfig.role_id) {
            if (typeof Notification !== 'undefined') {
                Notification.error('没有选择角色配置');
            }
            return;
        }

        try {
            const response = await fetch(`http://localhost:8788/api/agent/role-configs/${currentConfig.role_id}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ system_prompt: prompt })
            });
            const result = await response.json();

            if (result.success) {
                agentState.currentRoleConfig.system_prompt = prompt;
                if (typeof Notification !== 'undefined') {
                    Notification.success('System Prompt 已保存');
                }
                console.log(`[MultiAgentHandlers] Agent ${agentId} 角色提示词已保存`);
            } else {
                if (typeof Notification !== 'undefined') {
                    Notification.error('保存失败: ' + (result.error || '未知错误'));
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 保存角色提示词失败:`, error);
            if (typeof Notification !== 'undefined') {
                Notification.error('保存失败: ' + error.message);
            }
        }
    },

    /**
     * 初始化流式聊天监听器
     */
    initChatStreamListeners() {
        if (window.electronAPI && window.electronAPI.onChatStreamData) {
            // Electron环境下的流式监听
            console.log('[MultiAgentHandlers] 初始化Electron流式监听');
            // TODO: 实现Electron环境下的流式监听
        }
    },

    /**
     * Markdown 渲染
     */
    renderMarkdown(text, isStreaming = false) {
        // 复用agentHandlers的renderMarkdown方法
        if (window.agentHandlers && window.agentHandlers.renderMarkdown) {
            return window.agentHandlers.renderMarkdown(text, isStreaming);
        }
        return text;
    },

    /**
     * 代码高亮
     */
    highlightCodeBlocks(container) {
        // 复用agentHandlers的highlightCodeBlocks方法
        if (window.agentHandlers && window.agentHandlers.highlightCodeBlocks) {
            window.agentHandlers.highlightCodeBlocks(container);
        }
    },

    /**
     * 创建消息元素
     */
    createMessageElement(role, content, time) {
        // 复用agentHandlers的createMessageElement方法
        if (window.agentHandlers && window.agentHandlers.createMessageElement) {
            return window.agentHandlers.createMessageElement(role, content, time);
        }
        return '';
    },

    /**
     * 格式化时间
     */
    formatTime(timestamp) {
        if (!timestamp) return '';
        try {
            const date = new Date(timestamp);
            return date.toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return '';
        }
    },

    /**
     * HTML转义
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }
};

// 导出为全局对象
if (typeof window !== 'undefined') {
    window.multiAgentHandlers = multiAgentHandlers;
}

export default multiAgentHandlers;
