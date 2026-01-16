/**
 * Agent Sidebar - 侧边栏渲染（多Agent动态加载版本 - 重构架构）
 * 每个Agent有自己的展开/折叠section，直接显示在对应agent列表项下方
 */

const AgentSidebar = {
    /**
     * 渲染侧边栏 - 返回基础结构，由init()动态填充
     */
    render() {
        return `
            <div class="sidebar-section agent-list-section">
                <div class="agent-list" id="agentList"></div>
            </div>
        `;
    },

    /**
     * 初始化 - 从API加载Agent并创建UI
     */
    async init() {
        console.log('[AgentSidebar] 开始初始化...');

        // 1. 从API加载Agent列表
        const agents = await this.loadAgentsFromAPI();
        console.log('[AgentSidebar] 加载到的agents:', agents);

        if (agents.length === 0) {
            console.warn('[AgentSidebar] 没有可用的Agent');
            this.renderEmptyState();
            return;
        }

        // 2. 渲染Agent列表（每个agent包含item + section）
        this.renderAgentList(agents);

        // 3. 绑定事件
        this.bindEvents();

        // 4. 恢复之前选择的agent，或默认展开第一个agent
        if (agents.length > 0) {
            // 检查是否有保存的currentAgentId
            const savedAgentId = window.agentState?.currentAgentId;
            const agentToSelect = savedAgentId && agents.find(a => a.id === savedAgentId)
                ? savedAgentId
                : agents[0].id;

            console.log('[AgentSidebar] 选择Agent:', agentToSelect, savedAgentId ? '(恢复之前的选择)' : '(默认第一个)');

            // 确保agentState设置了currentAgentId
            if (window.agentState) {
                window.agentState.setCurrentAgent(agentToSelect);
            }

            this.switchAgent(agentToSelect);
        }

        console.log('[AgentSidebar] 初始化完成');
    },

    /**
     * 从API加载Agent列表
     */
    async loadAgentsFromAPI() {
        try {
            const response = await fetch('http://localhost:8788/api/agent');
            const result = await response.json();

            if (result.success && result.data) {
                return result.data.filter(agent => agent.is_active !== false);
            }
            return [];
        } catch (error) {
            console.error('[AgentSidebar] 加载Agent列表失败:', error);
            return [];
        }
    },

    /**
     * 渲染Agent列表（新架构：每个agent item后面跟着它的section）
     */
    renderAgentList(agents) {
        const agentList = document.getElementById('agentList');
        if (!agentList) return;

        // 为每个agent创建：item + section
        const agentItemsHTML = agents.map(agent => `
            <!-- Agent列表项 -->
            <div class="agent-item" data-agent-id="${agent.id}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>${agent.name || 'Unnamed Agent'}</span>
            </div>

            <!-- Agent专属的可展开section（初始隐藏）-->
            <div class="agent-section-container" data-agent-id="${agent.id}" style="display: none;">
                ${this.createAgentSectionHTML(agent)}
            </div>
        `).join('');

        // 添加管理按钮
        const managementButtons = `
            <div class="agent-item agent-management" data-page="model-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>模型管理</span>
            </div>
            <div class="agent-item agent-management" data-page="role-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                <span>角色管理</span>
            </div>
            <div class="agent-item agent-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/>
                </svg>
                <span>Agent Management</span>
            </div>
        `;

        agentList.innerHTML = agentItemsHTML + managementButtons;
        console.log('[AgentSidebar] Agent列表已渲染（新架构：item+section模式）');
    },

    /**
     * 创建单个Agent的section HTML内容
     */
    createAgentSectionHTML(agent) {
        return `
            <div class="agent-user-section" data-agent-id="${agent.id}">
                <!-- 大图标按钮 -->
                <div class="agent-action-buttons">
                    <button class="agent-action-btn" data-action="new-chat" data-agent-id="${agent.id}">
                        <div class="action-btn-icon">
                            <svg viewBox="0 0 48 48" width="40" height="40">
                                <rect x="8" y="8" width="32" height="8" rx="2" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="8" y1="22" x2="40" y2="22" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="8" y1="30" x2="32" y2="30" stroke="#1a73e8" stroke-width="2"/>
                                <path d="M8 38 L18 38" stroke="#1a73e8" stroke-width="2"/>
                                <circle cx="12" cy="12" r="2" fill="#1a73e8"/>
                                <path d="M16 10 L16 14 M14 12 L18 12" stroke="#1a73e8" stroke-width="1.5"/>
                            </svg>
                        </div>
                        <span class="action-btn-text">New Chat</span>
                    </button>
                    <button class="agent-action-btn" data-action="settings" data-agent-id="${agent.id}">
                        <div class="action-btn-icon">
                            <svg viewBox="0 0 48 48" width="40" height="40">
                                <circle cx="24" cy="24" r="16" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <path d="M24 8 L24 12 M24 36 L24 40 M8 24 L12 24 M36 24 L40 24 M12 12 L15 15 M33 33 L36 36 M12 36 L15 33 M33 15 L36 12" stroke="#1a73e8" stroke-width="2" stroke-linecap="round"/>
                                <circle cx="24" cy="24" r="6" fill="none" stroke="#1a73e8" stroke-width="2"/>
                            </svg>
                        </div>
                        <span class="action-btn-text">Setting</span>
                    </button>
                </div>
                <div class="sidebar-section">
                    <!-- 搜索框 -->
                    <div class="agent-search">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#9e9e9e">
                            <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                        </svg>
                        <input type="text" class="search-input" placeholder="Keyword+Enter,Blank+Enter to reset" data-agent-id="${agent.id}">
                    </div>
                    <!-- Chat List / Tag List 切换 -->
                    <div class="chat-list-tabs">
                        <button class="chat-tab active" data-tab="chatList" data-agent-id="${agent.id}">Chat List</button>
                        <button class="chat-tab" data-tab="tagList" data-agent-id="${agent.id}">Tag List</button>
                    </div>
                    <!-- 聊天列表 -->
                    <div class="chat-list-container" id="chatListContainer-${agent.id}">
                        <div class="chat-list-header">Chat List</div>
                        <div class="chat-tree" id="chatList-${agent.id}">
                            <div class="tree-node">
                                <span class="tree-toggle">▼</span>
                                <span class="tree-label">All</span>
                            </div>
                            <div class="tree-children">
                                <!-- 聊天列表将在这里动态加载 -->
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 渲染空状态
     */
    renderEmptyState() {
        const agentList = document.getElementById('agentList');
        if (agentList) {
            agentList.innerHTML = `
                <div class="empty-state" style="padding: 20px; text-align: center; color: #999;">
                    <p>暂无可用的Agent</p>
                    <p style="font-size: 12px; margin-top: 10px;">请先在Agent Management中创建Agent</p>
                </div>
            `;
        }
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        console.log('[AgentSidebar] 开始绑定事件...');

        // 1. Agent列表项点击 - 切换Agent（展开/折叠）
        document.querySelectorAll('#agentList .agent-item[data-agent-id]').forEach(item => {
            item.addEventListener('click', () => {
                const agentId = parseInt(item.dataset.agentId);
                console.log('[AgentSidebar] 点击Agent:', agentId);
                this.switchAgent(agentId);
            });
        });

        // 2. New Chat按钮
        document.querySelectorAll('[data-action="new-chat"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const agentId = parseInt(btn.dataset.agentId);
                console.log('[AgentSidebar] 点击New Chat:', agentId);
                this.handleNewChat(agentId);
            });
        });

        // 3. Settings按钮
        document.querySelectorAll('[data-action="settings"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const agentId = parseInt(btn.dataset.agentId);
                console.log('[AgentSidebar] 点击Settings:', agentId);
                this.handleSettings(agentId);
            });
        });

        // 4. 聊天标签切换
        document.querySelectorAll('.chat-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                const agentId = tab.dataset.agentId;
                const tabType = tab.dataset.tab;

                // 找到同一个agent的所有tab
                const sameSectionTabs = document.querySelectorAll(`.chat-tab[data-agent-id="${agentId}"]`);
                sameSectionTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                console.log('[AgentSidebar] 切换tab:', tabType, 'for agent:', agentId);
            });
        });

        // 5. 管理按钮（模型管理、角色管理、Agent Management）
        document.querySelectorAll('.agent-management[data-page]').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                console.log('[AgentSidebar] 点击管理按钮:', page);
                this.navigateToManagementPage(page);
            });
        });

        console.log('[AgentSidebar] 事件绑定完成');
    },

    /**
     * 切换Agent（新架构：展开/折叠对应的section-container）
     */
    switchAgent(agentId) {
        console.log('[AgentSidebar] 切换到Agent:', agentId);

        // 0. 更新agentState
        if (window.agentState) {
            window.agentState.setCurrentAgent(agentId);
            console.log('[AgentSidebar] 已更新agentState.currentAgentId为:', agentId);
        }

        // 1. 折叠所有agent-section-container
        document.querySelectorAll('.agent-section-container').forEach(container => {
            container.style.display = 'none';
        });

        // 2. 展开选中agent的section-container
        const targetContainer = document.querySelector(`.agent-section-container[data-agent-id="${agentId}"]`);
        if (targetContainer) {
            targetContainer.style.display = 'block';
            console.log('[AgentSidebar] 已展开Agent section container:', agentId);
        }

        // 3. 隐藏所有agent-page
        document.querySelectorAll('.agent-page-layout').forEach(page => {
            page.style.display = 'none';
        });

        // 4. 显示选中的agent-page
        const targetPage = document.getElementById(`page-agent-${agentId}`);
        if (targetPage) {
            targetPage.style.display = 'flex'; // 使用flex而不是block以保持布局
            console.log('[AgentSidebar] 已显示Agent page:', agentId);
        }

        // 5. 更新agent列表的active状态
        document.querySelectorAll('#agentList .agent-item[data-agent-id]').forEach(item => {
            item.classList.remove('active');
        });
        const activeItem = document.querySelector(`#agentList .agent-item[data-agent-id="${agentId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }

        // 6. 直接加载chat list（避免依赖事件系统）
        // 添加小延迟确保DOM已经渲染完成
        setTimeout(() => {
            if (window.multiAgentHandlers && typeof window.multiAgentHandlers.loadChatListForAgent === 'function') {
                console.log('[AgentSidebar] 直接加载chat list for agent:', agentId);
                window.multiAgentHandlers.loadChatListForAgent(agentId);
            } else {
                console.error('[AgentSidebar] multiAgentHandlers.loadChatListForAgent 不可用');
            }
        }, 100);  // 100ms延迟确保DOM准备好

        // 7. 触发全局事件（供其他模块监听）
        window.dispatchEvent(new CustomEvent('agent-switched', {
            detail: { agentId }
        }));

        console.log('[AgentSidebar] Agent切换完成');
    },

    /**
     * 处理New Chat
     */
    handleNewChat(agentId) {
        console.log('[AgentSidebar] 处理New Chat for agent:', agentId);

        // 触发全局事件
        window.dispatchEvent(new CustomEvent('agent-new-chat', {
            detail: { agentId }
        }));
    },

    /**
     * 处理Settings
     */
    async handleSettings(agentId) {
        console.log('[AgentSidebar] 处理Settings for agent:', agentId);

        try {
            // 加载agent详情
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}`);
            const result = await response.json();

            if (result.success && result.data) {
                // 打开Settings对话框
                if (typeof AgentSettingsDialog !== 'undefined') {
                    AgentSettingsDialog.show(result.data);
                } else {
                    console.error('[AgentSidebar] AgentSettingsDialog未定义');
                }
            } else {
                console.error('[AgentSidebar] 加载Agent详情失败:', result);
            }
        } catch (error) {
            console.error('[AgentSidebar] 加载Agent详情失败:', error);
        }
    },

    /**
     * 导航到管理页面
     */
    async navigateToManagementPage(page) {
        try {
            console.log('[AgentSidebar] 导航到管理页面:', page);

            // Import management pages dynamically
            const module = await import('./index.js');
            const { ModelManagementPage, RoleManagementPage } = module.default;

            console.log('[AgentSidebar] 已导入管理页面模块');

            if (page === 'model-management' && ModelManagementPage) {
                await ModelManagementPage.init();
                console.log('[AgentSidebar] 模型管理页面已初始化');
            } else if (page === 'role-management' && RoleManagementPage) {
                await RoleManagementPage.init();
                console.log('[AgentSidebar] 角色管理页面已初始化');
            } else {
                console.error('[AgentSidebar] 页面未找到:', page);
            }
        } catch (error) {
            console.error('[AgentSidebar] 导航到管理页面失败:', error);
        }
    },

    /**
     * 重新加载 Agent 列表（保留新架构）
     * 用于在更新 Agent 后刷新侧边栏
     */
    async reload() {
        console.log('[AgentSidebar] 开始重新加载...');

        // 1. 从API重新加载Agent列表
        const agents = await this.loadAgentsFromAPI();
        console.log('[AgentSidebar] 重新加载的agents:', agents);

        if (agents.length === 0) {
            console.warn('[AgentSidebar] 没有可用的Agent');
            this.renderEmptyState();
            return;
        }

        // 2. 保存当前选中的 agent ID (优先使用 agentState 中保存的)
        const currentAgentId = window.agentState?.currentAgentId ||
            (() => {
                const currentExpandedContainer = document.querySelector('.agent-section-container[style*="display: block"]');
                return currentExpandedContainer ? parseInt(currentExpandedContainer.dataset.agentId) : null;
            })();

        // 3. 重新渲染Agent列表
        this.renderAgentList(agents);

        // 4. 重新绑定事件
        this.bindEvents();

        // 5. 恢复之前展开的 agent，如果不存在则展开第一个
        if (currentAgentId && agents.find(a => a.id === currentAgentId)) {
            console.log('[AgentSidebar] 恢复之前选中的agent:', currentAgentId);
            this.switchAgent(currentAgentId);
        } else if (agents.length > 0) {
            console.log('[AgentSidebar] 选择第一个agent');
            this.switchAgent(agents[0].id);
        }

        console.log('[AgentSidebar] 重新加载完成');
    }
};

// 导出到全局（供其他模块使用）
if (typeof window !== 'undefined') {
    window.AgentSidebar = AgentSidebar;
}

export default AgentSidebar;
