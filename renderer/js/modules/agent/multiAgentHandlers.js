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

        // 8. 为所有agent加载模型和角色选项
        for (const agent of agents) {
            await this.loadModelOptionsForAgent(agent.id);
            await this.loadRoleOptionsForAgent(agent.id);
        }

        // 9. 为当前agent加载聊天列表
        if (agents.length > 0) {
            this.loadChatListForAgent(agents[0].id);
        }

        // 10. 初始化流式监听
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
        document.addEventListener('change', async (e) => {
            const modelSelector = e.target.closest('.model-selector[data-agent-id]');
            if (modelSelector) {
                const agentId = parseInt(modelSelector.dataset.agentId);
                const configId = modelSelector.value;

                // 检查是否选择了 "Please Select"
                if (!configId) {
                    console.log('[MultiAgentHandlers] 模型选择器：未选择有效配置');
                    return;
                }

                agentState.setCurrentAgent(agentId);
                agentState.setModel(configId);

                // 禁用选择器，防止重复点击
                modelSelector.disabled = true;

                try {
                    await this.loadAndApplyModelConfig(configId, agentId);
                    console.log(`[MultiAgentHandlers] Agent ${agentId} 模型配置已更新`);
                } catch (error) {
                    console.error(`[MultiAgentHandlers] Agent ${agentId} 更新模型配置失败:`, error);
                    if (typeof Notification !== 'undefined') {
                        Notification.error('更新模型配置失败: ' + error.message);
                    }
                } finally {
                    // 重新启用选择器
                    modelSelector.disabled = false;
                }
            }
        });

        // 4. 角色选择器
        document.addEventListener('change', async (e) => {
            const roleSelector = e.target.closest('.role-selector[data-agent-id]');
            if (roleSelector) {
                const agentId = parseInt(roleSelector.dataset.agentId);
                const roleId = roleSelector.value;

                // 检查是否选择了 "Please Select"
                if (!roleId) {
                    console.log('[MultiAgentHandlers] 角色选择器：未选择有效配置');
                    return;
                }

                agentState.setCurrentAgent(agentId);
                agentState.setRole(roleId);

                // 禁用选择器，防止重复点击
                roleSelector.disabled = true;

                try {
                    await this.loadAndApplyRoleConfig(roleId, agentId);
                    console.log(`[MultiAgentHandlers] Agent ${agentId} 角色配置已更新`);
                } catch (error) {
                    console.error(`[MultiAgentHandlers] Agent ${agentId} 更新角色配置失败:`, error);
                    if (typeof Notification !== 'undefined') {
                        Notification.error('更新角色配置失败: ' + error.message);
                    }
                } finally {
                    // 重新启用选择器
                    roleSelector.disabled = false;
                }
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

        // 8. 插件选择按钮（工具栏的"添加"按钮）
        document.addEventListener('click', (e) => {
            const addBtn = e.target.closest('.toolbar-icon-btn[title="添加"][data-agent-id]');
            if (addBtn) {
                const agentId = parseInt(addBtn.dataset.agentId);
                console.log('[MultiAgentHandlers] 点击添加按钮（插件选择）for agent:', agentId);
                this.handleAddPlugin(agentId);
            }
        });

        console.log('[MultiAgentHandlers] 所有事件绑定完成');
    },

    /**
     * 为特定agent加载聊天列表
     */
    async loadChatListForAgent(agentId) {
        console.log(`[MultiAgentHandlers] 开始加载Agent ${agentId} 的chat list`);

        const chatList = document.getElementById(`chatList-${agentId}`);
        if (!chatList) {
            console.warn(`[MultiAgentHandlers] 找不到元素 chatList-${agentId}，可能DOM还未准备好`);
            return;
        }

        try {
            // 尝试从API获取conversations，带agent_id参数
            // 如果后端支持按agent筛选，会返回过滤后的结果
            // 如果不支持，我们在客户端进行过滤
            console.log(`[MultiAgentHandlers] 调用API: http://localhost:8788/api/chat/conversations?limit=50&agent_id=${agentId}`);
            const response = await fetch(`http://localhost:8788/api/chat/conversations?limit=50&agent_id=${agentId}`);
            const result = await response.json();
            let conversations = result.data || [];
            console.log(`[MultiAgentHandlers] API返回了 ${conversations.length} 条对话`);

            // 客户端过滤：只显示属于当前agent的对话
            // 如果conversation有agent_id字段，则过滤；否则显示所有（向后兼容）
            if (conversations.length > 0 && conversations[0].agent_id !== undefined) {
                conversations = conversations.filter(conv => conv.agent_id == agentId);
                console.log(`[MultiAgentHandlers] 过滤后剩余 ${conversations.length} 条对话`);
            }

            const treeChildren = chatList.querySelector('.tree-children');
            if (!treeChildren) {
                console.warn(`[MultiAgentHandlers] 找不到 .tree-children 元素在 chatList-${agentId} 中`);
                return;
            }

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

            console.log(`[MultiAgentHandlers] Agent ${agentId} 聊天列表已加载，共 ${conversations.length} 条`);
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

        // 获取当前agent信息
        const currentAgent = agentState.getCurrentAgent();
        if (!currentAgent) {
            console.error('[MultiAgentHandlers] 没有选中的Agent');
            if (typeof Notification !== 'undefined') {
                Notification.error('请先选择一个Agent');
            }
            return;
        }

        console.log('[MultiAgentHandlers] 使用Agent发送消息:', currentAgent.name, 'ID:', agentId);

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
            console.log('[MultiAgentHandlers] 生成新对话ID:', conversationId);
        }

        // 添加AI回复容器（带思考动画，显示Agent名称）
        const assistantMessageHtml = `
            <div class="message-item assistant-message streaming">
                <div class="message-header">
                    <div class="message-avatar assistant-avatar">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                    </div>
                    <span class="message-sender">${this.escapeHtml(currentAgent.name)}</span>
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

        // 启用发送按钮的函数
        const enableSendBtn = () => {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.classList.remove('sending');
            }
        };

        // 发起流式请求 - 使用Agent专属接口
        try {
            // 准备回调函数（绑定agentId）
            const callbacks = {
                onData: (content) => {
                    agentState.appendStreamingContent(content);
                    this.updateStreamingMessageForAgent(agentState.getStreamingContent(), agentId);
                },
                onEnd: () => {
                    this.finalizeStreamingMessageForAgent(agentId);
                    agentState.clearRequestId();
                    enableSendBtn();
                    // 重新加载聊天列表
                    this.loadChatListForAgent(agentId);
                },
                onError: (error) => {
                    this.showStreamErrorForAgent(error, agentId);
                    agentState.clearRequestId();
                    enableSendBtn();
                }
            };

            // 调用Agent专属的流式接口
            console.log('[MultiAgentHandlers] 调用Agent专属接口:', `/api/agent/${agentId}/chat/stream`);
            await agentApi.agentChatStream(
                agentId,
                message,
                conversationId,
                callbacks,
                {
                    use_memory: true,
                    use_knowledge_base: true
                }
            );

            // 设置超时处理
            setTimeout(() => {
                if (agentState.getRequestId() === requestId) {
                    this.showStreamErrorForAgent('请求超时，请重试', agentId);
                    agentState.clearRequestId();
                    enableSendBtn();
                }
            }, 120000); // 2分钟超时

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

                // 渲染思维导图（如果有）
                if (window.MindmapPlugin) {
                    window.MindmapPlugin.renderInMessage(streamingBody);
                }
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
            // 1. 获取agent的当前配置
            const agentResponse = await fetch(`http://localhost:8788/api/agent/${agentId}`);
            const agentResult = await agentResponse.json();
            const currentAgent = agentResult.success ? agentResult.data : null;
            const currentModelConfigId = currentAgent?.model_config_id || currentAgent?.model;

            // 2. 获取所有模型配置
            const response = await fetch('http://localhost:8788/api/agent/llm-configs');
            const result = await response.json();

            if (result.success && result.data) {
                const models = result.data.filter(m => m.is_active !== false);

                if (models.length > 0) {
                    // 3. 确定要选中的模型
                    let selectedModel = null;
                    let shouldShowPleaseSelect = false;

                    if (currentModelConfigId) {
                        // 如果agent有保存的配置，尝试在列表中查找
                        selectedModel = models.find(m => m.config_id === currentModelConfigId);

                        // 如果agent的配置不在可用列表中，显示 Please Select
                        if (!selectedModel) {
                            shouldShowPleaseSelect = true;
                        }
                    } else {
                        // 如果agent没有配置，显示 Please Select
                        shouldShowPleaseSelect = true;
                    }

                    // 4. 渲染选项
                    let optionsHTML = '';

                    // 添加 "Please Select" 选项
                    if (shouldShowPleaseSelect) {
                        optionsHTML = '<option value="" selected>Please Select</option>';
                    }

                    // 添加模型选项
                    optionsHTML += models.map(model => `
                        <option value="${model.config_id}" ${selectedModel && model.config_id === selectedModel.config_id ? 'selected' : ''}>
                            ${model.name}${model.provider ? ` (${model.provider})` : ''}
                        </option>
                    `).join('');

                    modelSelector.innerHTML = optionsHTML;

                    // 5. 加载选中模型的配置（仅当有有效配置时）
                    if (selectedModel) {
                        agentState.setModel(selectedModel.config_id);
                        await this.loadAndApplyModelConfig(selectedModel.config_id, agentId, false);
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
            // 1. 获取agent的当前配置
            const agentResponse = await fetch(`http://localhost:8788/api/agent/${agentId}`);
            const agentResult = await agentResponse.json();
            const currentAgent = agentResult.success ? agentResult.data : null;
            const currentRoleId = currentAgent?.role_id;

            // 2. 获取所有角色配置
            const response = await fetch('http://localhost:8788/api/agent/role-configs');
            const result = await response.json();

            if (result.success && result.data) {
                const roles = result.data.filter(r => r.is_active !== false);

                if (roles.length > 0) {
                    // 3. 确定要选中的角色
                    let selectedRole = null;
                    let shouldShowPleaseSelect = false;

                    if (currentRoleId) {
                        // 如果agent有保存的配置，尝试在列表中查找
                        selectedRole = roles.find(r => r.role_id === currentRoleId);

                        // 如果agent的配置不在可用列表中，显示 Please Select
                        if (!selectedRole) {
                            shouldShowPleaseSelect = true;
                        }
                    } else {
                        // 如果agent没有配置，显示 Please Select
                        shouldShowPleaseSelect = true;
                    }

                    // 4. 渲染选项
                    let optionsHTML = '';

                    // 添加 "Please Select" 选项
                    if (shouldShowPleaseSelect) {
                        optionsHTML = '<option value="" selected>Please Select</option>';
                    }

                    // 添加角色选项
                    optionsHTML += roles.map(role => `
                        <option value="${role.role_id}" ${selectedRole && role.role_id === selectedRole.role_id ? 'selected' : ''}>
                            ${role.name}${role.category ? ` - ${role.category}` : ''}
                        </option>
                    `).join('');

                    roleSelector.innerHTML = optionsHTML;

                    // 5. 加载选中角色的配置（仅当有有效配置时）
                    if (selectedRole) {
                        agentState.setRole(selectedRole.role_id);
                        await this.loadAndApplyRoleConfig(selectedRole.role_id, agentId, false);
                    }
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载角色列表失败:`, error);
        }
    },

    /**
     * 加载并应用模型配置
     * @param {string} configId - 模型配置ID
     * @param {number} agentId - Agent ID
     * @param {boolean} saveToDatabase - 是否保存到数据库（默认true）
     */
    async loadAndApplyModelConfig(configId, agentId, saveToDatabase = true) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/llm-configs/${configId}`);
            const result = await response.json();

            if (result.success && result.data) {
                const modelConfig = result.data;
                agentState.currentModelConfig = modelConfig;
                this.populateParamTabForAgent(modelConfig, agentId);
                console.log(`[MultiAgentHandlers] Agent ${agentId} 模型配置已加载:`, modelConfig.name);

                // 如果需要，更新agent配置到数据库
                if (saveToDatabase) {
                    await this.updateAgentModelConfig(agentId, configId);
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载模型配置失败:`, error);
        }
    },

    /**
     * 加载并应用角色配置
     * @param {string} roleId - 角色ID
     * @param {number} agentId - Agent ID
     * @param {boolean} saveToDatabase - 是否保存到数据库（默认true）
     */
    async loadAndApplyRoleConfig(roleId, agentId, saveToDatabase = true) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/role-configs/${roleId}`);
            const result = await response.json();

            if (result.success && result.data) {
                const roleConfig = result.data;
                agentState.currentRoleConfig = roleConfig;
                this.populatePromptTabForAgent(roleConfig, agentId);
                console.log(`[MultiAgentHandlers] Agent ${agentId} 角色配置已加载:`, roleConfig.name);

                // 如果需要，更新agent配置到数据库
                if (saveToDatabase) {
                    await this.updateAgentRoleConfig(agentId, roleId);
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} 加载角色配置失败:`, error);
        }
    },

    /**
     * 更新Agent的模型配置到数据库
     * @param {number} agentId - Agent ID
     * @param {string} configId - 模型配置ID
     */
    async updateAgentModelConfig(agentId, configId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    model_config_id: configId
                })
            });

            const result = await response.json();

            if (!response.ok) {
                // HTTP错误
                console.error(`[MultiAgentHandlers] HTTP ${response.status}:`, result);
                throw new Error(result.detail || `HTTP ${response.status}`);
            }

            if (result.success) {
                console.log(`[MultiAgentHandlers] Agent ${agentId} 模型配置已更新到数据库:`, configId);
                // 重新加载agent实例以应用新配置
                await this.reloadAgentInstance(agentId);
            } else {
                console.error(`[MultiAgentHandlers] 更新Agent模型配置失败:`, result.error);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] 更新Agent模型配置失败:`, error);
            throw error;
        }
    },

    /**
     * 更新Agent的角色配置到数据库
     * @param {number} agentId - Agent ID
     * @param {string} roleId - 角色ID
     */
    async updateAgentRoleConfig(agentId, roleId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}`, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    role_id: roleId
                })
            });

            const result = await response.json();

            if (!response.ok) {
                // HTTP错误
                console.error(`[MultiAgentHandlers] HTTP ${response.status}:`, result);
                throw new Error(result.detail || `HTTP ${response.status}`);
            }

            if (result.success) {
                console.log(`[MultiAgentHandlers] Agent ${agentId} 角色配置已更新到数据库:`, roleId);
                // 重新加载agent实例以应用新配置
                await this.reloadAgentInstance(agentId);
            } else {
                console.error(`[MultiAgentHandlers] 更新Agent角色配置失败:`, result.error);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] 更新Agent角色配置失败:`, error);
            throw error;
        }
    },

    /**
     * 重新加载Agent实例（让后端重新从数据库加载配置）
     * @param {number} agentId - Agent ID
     */
    async reloadAgentInstance(agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/reload`, {
                method: 'POST'
            });
            const result = await response.json();
            if (result.success) {
                console.log(`[MultiAgentHandlers] Agent ${agentId} 实例已重新加载`);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] 重新加载Agent实例失败:`, error);
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
    },

    /**
     * 处理添加插件（特定agent）
     */
    handleAddPlugin(agentId) {
        if (typeof Modal === 'undefined') {
            console.error('[MultiAgentHandlers] Modal component not loaded');
            return;
        }

        Modal.show({
            title: '添加插件',
            content: `
                <div class="form-group">
                    <label>选择插件</label>
                    <select class="form-input" id="pluginSelect">
                        <option value="">请选择插件...</option>
                        <option value="mindmap">思维导图插件</option>
                        <option value="code">代码执行插件</option>
                        <option value="calendar">日历插件</option>
                        <option value="chart">图表插件</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>插件说明</label>
                    <p style="font-size: 12px; color: #666;" id="pluginDescription">请先选择一个插件</p>
                </div>
            `,
            confirmText: '添加',
            showCancel: true,
            onConfirm: () => {
                const select = document.getElementById('pluginSelect');
                const pluginId = select.value;

                if (!pluginId) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('请选择一个插件');
                    }
                    return false; // 阻止模态框关闭
                }

                this.loadPluginForAgent(pluginId, agentId);
            }
        });

        // 绑定插件选择变化事件
        setTimeout(() => {
            const select = document.getElementById('pluginSelect');
            const descriptionEl = document.getElementById('pluginDescription');

            if (select && descriptionEl) {
                select.addEventListener('change', (e) => {
                    const descriptions = {
                        'mindmap': '将聊天内容中的 Markdown mindmap 语法转换为可视化的思维导图',
                        'code': '从聊天中提取代码块，提供编辑和运行功能（支持 JavaScript、Python、HTML/CSS/JS）',
                        'calendar': '在聊天中显示和管理日历事件',
                        'chart': '将数据可视化为各种图表'
                    };

                    descriptionEl.textContent = descriptions[e.target.value] || '请先选择一个插件';
                });
            }
        }, 100);
    },

    /**
     * 为特定agent加载插件
     */
    loadPluginForAgent(pluginId, agentId) {
        console.log(`[MultiAgentHandlers] 为Agent ${agentId} 加载插件:`, pluginId);

        // 插件配置
        const pluginConfigs = {
            'mindmap': {
                name: '思维导图',
                fullName: '思维导图插件',
                description: '将 Markdown mindmap 转换为可视化思维导图',
                icon: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>'
            },
            'code': {
                name: '代码执行',
                fullName: '代码执行插件',
                description: '从聊天中提取代码并在浏览器中运行',
                icon: '<path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>'
            },
            'calendar': {
                name: '日历',
                fullName: '日历插件',
                description: '在聊天中显示和管理日历事件',
                icon: '<path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>'
            },
            'chart': {
                name: '图表',
                fullName: '图表插件',
                description: '将数据可视化为各种图表',
                icon: '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>'
            }
        };

        const config = pluginConfigs[pluginId];
        if (!config) {
            console.error('[MultiAgentHandlers] 未知的插件ID:', pluginId);
            return;
        }

        // 检查插件是否已加载
        const existingTab = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="plugin-${pluginId}"]`);
        if (existingTab) {
            console.log('[MultiAgentHandlers] 插件已存在，切换到该页签');
            existingTab.click();
            if (typeof Notification !== 'undefined') {
                Notification.info(`${config.fullName} 已加载`);
            }
            return;
        }

        // 1. 创建页签按钮
        const settingsTabs = document.getElementById(`settingsTabs-${agentId}`);
        if (!settingsTabs) {
            console.error('[MultiAgentHandlers] 未找到设置页签容器');
            return;
        }

        const tabButton = document.createElement('button');
        tabButton.className = 'settings-tab';
        tabButton.dataset.tab = `plugin-${pluginId}`;
        tabButton.dataset.agentId = agentId;
        tabButton.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                ${config.icon}
            </svg>
            <span>${config.name}</span>
            <button class="tab-close-btn" title="关闭插件">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
            </button>
        `;

        // 绑定关闭按钮事件
        const closeBtn = tabButton.querySelector('.tab-close-btn');
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removePluginTabForAgent(pluginId, agentId);
        });

        settingsTabs.appendChild(tabButton);
        console.log('[MultiAgentHandlers] ✓ 已创建页签按钮');

        // 2. 创建页签内容
        const tabContent = document.getElementById(`settingsTabContent-${agentId}`);
        if (!tabContent) {
            console.error('[MultiAgentHandlers] 未找到页签内容容器');
            return;
        }

        const tabPane = document.createElement('div');
        tabPane.className = 'tab-pane';
        tabPane.dataset.tab = `plugin-${pluginId}`;
        tabPane.innerHTML = `
            <div class="settings-section">
                <div class="settings-section-title">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                        ${config.icon}
                    </svg>
                    <span>${config.fullName}</span>
                </div>
                <div class="plugin-content" id="plugin-content-${pluginId}-${agentId}">
                    <p style="font-size: 11px; color: #999; text-align: center; padding: 20px;">正在加载插件...</p>
                </div>
            </div>
        `;

        tabContent.appendChild(tabPane);
        console.log('[MultiAgentHandlers] ✓ 已创建页签内容');

        // 3. 激活新创建的页签
        tabButton.click();

        // 4. 加载插件具体内容
        this.loadPluginContentForAgent(pluginId, agentId);

        if (typeof Notification !== 'undefined') {
            Notification.success(`${config.fullName} 已加载`);
        }

        console.log('[MultiAgentHandlers] ✓ 插件加载完成');
    },

    /**
     * 移除特定agent的插件页签
     */
    removePluginTabForAgent(pluginId, agentId) {
        console.log(`[MultiAgentHandlers] 为Agent ${agentId} 移除插件:`, pluginId);

        // 移除页签按钮
        const tabButton = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="plugin-${pluginId}"]`);
        if (tabButton) {
            // 如果当前页签是激活状态，切换到 Param 页签
            if (tabButton.classList.contains('active')) {
                const paramTab = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="param"]`);
                if (paramTab) {
                    paramTab.click();
                }
            }
            tabButton.remove();
        }

        // 移除页签内容
        const tabPane = document.querySelector(`#settingsTabContent-${agentId} .tab-pane[data-tab="plugin-${pluginId}"]`);
        if (tabPane) {
            tabPane.remove();
        }

        if (typeof Notification !== 'undefined') {
            Notification.info('插件已移除');
        }

        console.log('[MultiAgentHandlers] ✓ 插件已移除');
    },

    /**
     * 加载特定agent的插件内容
     */
    loadPluginContentForAgent(pluginId, agentId) {
        const container = document.getElementById(`plugin-content-${pluginId}-${agentId}`);
        if (!container) {
            console.error('[MultiAgentHandlers] 未找到插件内容容器:', `plugin-content-${pluginId}-${agentId}`);
            return;
        }

        // 根据插件 ID 加载不同的内容
        switch (pluginId) {
            case 'mindmap':
                container.innerHTML = `
                    <div style="padding: 12px;">
                        <p style="font-size: 11px; color: var(--text-secondary, #666); margin-bottom: 12px;">
                            思维导图插件已激活。在聊天中发送包含 mindmap 格式的代码块，将自动转换为可视化思维导图。
                        </p>
                        <div style="margin-bottom: 12px;">
                            <p style="font-size: 10px; color: var(--text-secondary, #999); margin-bottom: 6px;">语法格式：</p>
                            <pre style="background: var(--bg-secondary, #f5f5f5); padding: 8px; border-radius: 4px; font-size: 10px; overflow-x: auto; margin-bottom: 8px;">\`\`\`mindmap
- 根节点
  - 子节点1
    - 孙节点1.1
  - 子节点2
\`\`\`</pre>
                        </div>
                        <button class="preset-use-btn" style="width: 100%; margin-bottom: 6px;" onclick="multiAgentHandlers.showMindmapExample(${agentId})">填充示例代码</button>
                        <button class="preset-use-btn" style="width: 100%;" onclick="multiAgentHandlers.askAIForMindmap(${agentId})">让 AI 生成思维导图</button>
                    </div>
                `;
                break;
            case 'code':
                if (window.CodePlugin) {
                    window.CodePlugin.render(container);
                } else {
                    container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">代码执行插件未加载，请刷新页面</p>';
                    console.error('[MultiAgentHandlers] CodePlugin 未找到');
                }
                break;
            case 'calendar':
                container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">日历插件开发中...</p>';
                break;
            case 'chart':
                container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">图表插件开发中...</p>';
                break;
            default:
                container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">未知插件</p>';
        }
    },

    /**
     * 显示思维导图示例（特定agent）
     */
    showMindmapExample(agentId) {
        const input = document.getElementById(`chatInput-${agentId}`);
        if (input) {
            input.value = '```mindmap\n- 学习编程\n  - 基础知识\n    - 数据类型\n    - 控制流程\n    - 函数\n  - 实践项目\n    - Web开发\n    - 移动应用\n    - 数据分析\n  - 进阶学习\n    - 算法与数据结构\n    - 设计模式\n    - 系统架构\n```';
            if (typeof Notification !== 'undefined') {
                Notification.info('已填充示例代码，点击发送按钮即可看到思维导图效果');
            }
            input.focus();
        }
    },

    /**
     * 让AI生成思维导图（特定agent）
     */
    askAIForMindmap(agentId) {
        const input = document.getElementById(`chatInput-${agentId}`);
        if (input) {
            input.value = '请帮我生成一个关于"人工智能发展历程"的思维导图。\n\n请严格使用以下格式：\n```mindmap\n- 根节点\n  - 子节点（用2个空格缩进）\n    - 孙节点（用4个空格缩进）\n```\n\n注意：\n1. 代码块语言必须是 mindmap\n2. 每个节点用 "- " 开头\n3. 子节点用2个空格缩进\n4. 不要使用 Tab 键';
            if (typeof Notification !== 'undefined') {
                Notification.info('已填充 AI 请求，发送后等待 AI 按照正确格式回复');
            }
            input.focus();
        }
    }
};

// 导出为全局对象
if (typeof window !== 'undefined') {
    window.multiAgentHandlers = multiAgentHandlers;
}

export default multiAgentHandlers;
