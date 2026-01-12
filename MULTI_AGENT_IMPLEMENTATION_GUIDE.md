# 多Agent动态加载实现指南

## 概述
本指南描述如何实现从数据库动态加载多个Agent，并为每个Agent创建独立的UI界面。

## 架构设计

### 1. 状态管理 (agentState.js) ✅ 已完成
- **多Agent状态管理**：每个Agent有独立的聊天历史、配置等
- **当前Agent追踪**：currentAgentId 标识当前活动的Agent
- **Agent状态隔离**：agentStates对象存储每个Agent的独立状态

```javascript
// 状态结构
{
  currentAgentId: 2,
  agents: [{ id: 1, name: "Agent1" }, { id: 2, name: "Agent2" }],
  agentStates: {
    1: { chatHistory: [], conversationId: null, ... },
    2: { chatHistory: [], conversationId: null, ... }
  }
}
```

### 2. 侧边栏结构 (AgentSidebar.js)

#### 当前结构问题：
- Agent列表是静态的
- 只有一个agent-user-section（硬编码为"Altman"）
- 没有动态加载机制

#### 目标结构：
```html
<div class="secondary-sidebar">
  <!-- 为每个Agent动态创建section -->
  <div class="sidebar-section agent-user-section" data-agent-id="1" style="display:block">
    <div class="agent-user-header">
      <span class="agent-username">Agent 1 Name</span>
    </div>
    <div class="agent-action-buttons">
      <button class="agent-action-btn" data-action="new-chat" data-agent-id="1">New Chat</button>
      <button class="agent-action-btn" data-action="settings" data-agent-id="1">Setting</button>
    </div>
    <!-- 搜索框 -->
    <div class="agent-search">...</div>
    <!-- Chat List -->
    <div class="chat-list-container" id="chatListContainer-1">...</div>
  </div>

  <div class="sidebar-section agent-user-section" data-agent-id="2" style="display:none">
    <!-- Agent 2 的section，初始隐藏 -->
  </div>

  <!-- Agent列表 -->
  <div class="sidebar-section agent-list-section">
    <div class="agent-list" id="agentList">
      <!-- 动态加载的Agent项 -->
      <div class="agent-item" data-agent-id="1">Agent 1</div>
      <div class="agent-item" data-agent-id="2">Agent 2</div>
      <!-- 管理按钮 -->
    </div>
  </div>
</div>
```

### 3. 主内容区结构 (AgentPage.js)

#### 目标结构：
```html
<main class="main-content">
  <!-- 为每个Agent创建独立的page -->
  <div id="page-agent-1" class="agent-page-layout" data-agent-id="1" style="display:block">
    <div class="agent-chat-area">
      <!-- Agent 1 的聊天界面 -->
      <div class="agent-chat-toolbar" id="toolbar-1">...</div>
      <div class="agent-chat-messages" id="chatMessages-1">...</div>
      <div class="agent-chat-input-area" id="inputArea-1">...</div>
    </div>
    <div class="agent-settings-panel" id="settingsPanel-1">...</div>
  </div>

  <div id="page-agent-2" class="agent-page-layout" data-agent-id="2" style="display:none">
    <!-- Agent 2 的page，初始隐藏 -->
  </div>
</main>
```

### 4. 核心实现步骤

#### Step 1: 修改 AgentSidebar.js
```javascript
const AgentSidebar = {
    /**
     * 渲染侧边栏 - 动态创建每个Agent的section
     */
    render() {
        // 返回空结构，由init()方法动态填充
        return `
            <div id="agent-sections-container"></div>
            <div class="sidebar-section agent-list-section">
                <div class="agent-list" id="agentList"></div>
            </div>
        `;
    },

    /**
     * 初始化 - 从API加载Agent并创建UI
     */
    async init() {
        // 1. 从API加载Agent列表
        const agents = await this.loadAgentsFromAPI();

        // 2. 创建每个Agent的section
        const container = document.getElementById('agent-sections-container');
        agents.forEach((agent, index) => {
            const section = this.createAgentSection(agent, index === 0);
            container.appendChild(section);
        });

        // 3. 渲染Agent列表
        this.renderAgentList(agents);

        // 4. 绑定事件
        this.bindEvents();
    },

    /**
     * 从API加载Agent列表
     */
    async loadAgentsFromAPI() {
        try {
            const response = await fetch('http://localhost:8788/api/agent');
            const result = await response.json();
            return result.data || [];
        } catch (error) {
            console.error('加载Agent列表失败:', error);
            return [];
        }
    },

    /**
     * 创建单个Agent的section
     */
    createAgentSection(agent, isActive = false) {
        const section = document.createElement('div');
        section.className = 'sidebar-section agent-user-section';
        section.dataset.agentId = agent.id;
        section.style.display = isActive ? 'block' : 'none';

        section.innerHTML = `
            <div class="agent-user-header">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="#5f6368">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 9h-2V9h2v2zm0 4h-2v-2h2v2zM13 9V3.5L18.5 9H13z"/>
                </svg>
                <span class="agent-username">${agent.name}</span>
            </div>
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
            <div class="agent-search">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#9e9e9e">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                </svg>
                <input type="text" class="search-input" placeholder="Keyword+Enter,Blank+Enter to reset" data-agent-id="${agent.id}">
            </div>
            <div class="chat-list-tabs">
                <button class="chat-tab active" data-tab="chatList" data-agent-id="${agent.id}">Chat List</button>
                <button class="chat-tab" data-tab="tagList" data-agent-id="${agent.id}">Tag List</button>
            </div>
            <div class="chat-list-container" id="chatListContainer-${agent.id}">
                <div class="chat-list-header">Chat List</div>
                <div class="chat-tree" id="chatList-${agent.id}">
                    <div class="tree-node">
                        <span class="tree-toggle">▼</span>
                        <span class="tree-label">All</span>
                    </div>
                    <div class="tree-children"></div>
                </div>
            </div>
        `;

        return section;
    },

    /**
     * 渲染Agent列表
     */
    renderAgentList(agents) {
        const agentList = document.getElementById('agentList');
        if (!agentList) return;

        const agentItems = agents.map(agent => `
            <div class="agent-item" data-agent-id="${agent.id}">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>${agent.name}</span>
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

        agentList.innerHTML = agentItems + managementButtons;
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 1. Agent列表项点击 - 切换Agent
        document.querySelectorAll('#agentList .agent-item[data-agent-id]').forEach(item => {
            item.addEventListener('click', () => {
                const agentId = parseInt(item.dataset.agentId);
                this.switchAgent(agentId);
            });
        });

        // 2. New Chat按钮
        document.querySelectorAll('[data-action="new-chat"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const agentId = parseInt(btn.dataset.agentId);
                this.handleNewChat(agentId);
            });
        });

        // 3. Settings按钮
        document.querySelectorAll('[data-action="settings"]').forEach(btn => {
            btn.addEventListener('click', () => {
                const agentId = parseInt(btn.dataset.agentId);
                this.handleSettings(agentId);
            });
        });
    },

    /**
     * 切换Agent
     */
    switchAgent(agentId) {
        // 1. 隐藏所有agent-section
        document.querySelectorAll('.agent-user-section').forEach(section => {
            section.style.display = 'none';
        });

        // 2. 显示选中的agent-section
        const targetSection = document.querySelector(`.agent-user-section[data-agent-id="${agentId}"]`);
        if (targetSection) {
            targetSection.style.display = 'block';
        }

        // 3. 隐藏所有agent-page
        document.querySelectorAll('.agent-page-layout').forEach(page => {
            page.style.display = 'none';
        });

        // 4. 显示选中的agent-page
        const targetPage = document.getElementById(`page-agent-${agentId}`);
        if (targetPage) {
            targetPage.style.display = 'block';
        }

        // 5. 更新状态
        agentState.setCurrentAgent(agentId);

        // 6. 触发事件（供其他模块监听）
        window.dispatchEvent(new CustomEvent('agent-switched', { detail: { agentId } }));
    },

    /**
     * 处理New Chat
     */
    handleNewChat(agentId) {
        agentState.setCurrentAgent(agentId);
        // 调用handler的handleNewChat方法
        if (window.agentHandlers) {
            window.agentHandlers.handleNewChat();
        }
    },

    /**
     * 处理Settings
     */
    handleSettings(agentId) {
        agentState.setCurrentAgent(agentId);
        // 打开Settings对话框，传入agentId
        if (typeof AgentSettingsDialog !== 'undefined') {
            // 加载agent详情
            fetch(`http://localhost:8788/api/agent/${agentId}`)
                .then(res => res.json())
                .then(result => {
                    if (result.success) {
                        AgentSettingsDialog.show(result.data);
                    }
                })
                .catch(error => {
                    console.error('加载Agent详情失败:', error);
                });
        }
    }
};

export default AgentSidebar;
```

#### Step 2: 修改 AgentPage.js
```javascript
const AgentPage = {
    /**
     * 渲染主内容区 - 动态创建每个Agent的page
     */
    render() {
        // 返回空结构，由init()方法动态填充
        return `<div id="agent-pages-container"></div>`;
    },

    /**
     * 初始化 - 为每个Agent创建page
     */
    async init(agents) {
        const container = document.getElementById('agent-pages-container');
        if (!container) return;

        agents.forEach((agent, index) => {
            const page = this.createAgentPage(agent, index === 0);
            container.appendChild(page);
        });
    },

    /**
     * 创建单个Agent的page
     */
    createAgentPage(agent, isActive = false) {
        const page = document.createElement('div');
        page.id = `page-agent-${agent.id}`;
        page.className = 'agent-page-layout';
        page.dataset.agentId = agent.id;
        page.style.display = isActive ? 'block' : 'none';

        page.innerHTML = `
            <div class="agent-chat-area">
                <!-- 工具栏 -->
                <div class="agent-chat-toolbar" id="toolbar-${agent.id}">
                    <div class="toolbar-left">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="#1a73e8">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                    </div>
                    <div class="toolbar-center">
                        <select class="model-selector" id="modelSelector-${agent.id}">
                            <option value="gpt-4o">Baichuan_local:gpt-4o</option>
                        </select>
                    </div>
                    <div class="toolbar-right">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="#5f6368">
                            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                        </svg>
                        <select class="role-selector" id="roleSelector-${agent.id}">
                            <option value="senior-dev">资深的程序员</option>
                        </select>
                    </div>
                </div>

                <!-- 消息区域 -->
                <div class="agent-chat-messages" id="chatMessages-${agent.id}">
                    <div class="welcome-message">
                        <div class="welcome-icon">
                            <svg viewBox="0 0 48 48" width="64" height="64">
                                <defs>
                                    <linearGradient id="welcomeGrad-${agent.id}" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" style="stop-color:#11998e"/>
                                        <stop offset="100%" style="stop-color:#38ef7d"/>
                                    </linearGradient>
                                </defs>
                                <circle cx="24" cy="24" r="22" fill="url(#welcomeGrad-${agent.id})" opacity="0.1"/>
                                <path d="M24 4C12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20S35.05 4 24 4zm-4 30l-10-10 2.82-2.82L20 28.34l15.18-15.18L38 16l-18 18z" fill="url(#welcomeGrad-${agent.id})"/>
                            </svg>
                        </div>
                        <h2 class="welcome-title">${agent.name}</h2>
                        <p class="welcome-subtitle">${agent.description || 'AI Assistant'}</p>
                    </div>
                </div>

                <!-- 输入区域 -->
                <div class="agent-chat-input-area" id="inputArea-${agent.id}">
                    <div class="input-hint">Input @@ to load tools selector; Ctrl+i To load preset question; Ctrl+/ To insert chat template.</div>
                    <div class="input-wrapper">
                        <textarea class="agent-chat-input" id="chatInput-${agent.id}" placeholder="输入消息..." data-agent-id="${agent.id}"></textarea>
                    </div>
                    <div class="input-toolbar">
                        <div class="toolbar-buttons">
                            <button class="toolbar-icon-btn" title="添加"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg></button>
                        </div>
                        <button class="send-btn" id="sendMessageBtn-${agent.id}" data-agent-id="${agent.id}">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
                            </svg>
                        </button>
                    </div>
                </div>
            </div>

            <!-- 右侧面板分隔条 -->
            <div class="agent-panel-resizer" id="agentPanelResizer-${agent.id}">
                <div class="panel-resizer-handle">
                    <div class="panel-resizer-line"></div>
                </div>
                <button class="panel-collapse-btn" id="agentPanelCollapseBtn-${agent.id}" title="折叠设置面板">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
                        <polyline points="9,6 15,12 9,18"/>
                    </svg>
                </button>
            </div>

            <!-- 右侧设置面板 -->
            <div class="agent-settings-panel" id="agentSettingsPanel-${agent.id}">
                <!-- Settings panels content -->
                <div class="settings-tab-content" id="settingsTabContent-${agent.id}">
                    <div class="tab-pane active" data-tab="param">
                        <div class="settings-section">
                            <div class="settings-section-title">
                                <span>模型参数</span>
                            </div>
                            <!-- param inputs -->
                        </div>
                    </div>
                </div>
                <div class="settings-tabs" id="settingsTabs-${agent.id}">
                    <button class="settings-tab active" data-tab="param"><span>Param</span></button>
                    <button class="settings-tab" data-tab="prompt"><span>Prompt</span></button>
                    <button class="settings-tab" data-tab="file"><span>File</span></button>
                </div>
            </div>
        `;

        return page;
    }
};

export default AgentPage;
```

#### Step 3: 修改 agentHandlers.js

关键修改点：
1. 在 `loadAgentList()` 中调用真实API
2. 在 `init()` 中同时初始化sidebar和page
3. 所有操作要基于 `agentState.currentAgentId`
4. 使用agent-specific的DOM ID（如 `chatMessages-${agentId}`）

```javascript
// 在agentHandlers.js中
async init() {
    // 1. 加载并初始化Agent列表
    const agents = await agentApi.getAgents();
    agentState.setAgents(agents.data || []);

    // 2. 初始化sidebar
    await AgentSidebar.init();

    // 3. 初始化page
    await AgentPage.init(agents.data || []);

    // 4. 加载模型和角色选项
    this.loadModelOptions();
    this.loadRoleOptions();

    // 5. 绑定通用事件
    this.bindEvents();

    // 6. 初始化流式监听
    this.initChatStreamListeners();

    // 7. 为当前agent加载聊天列表
    this.loadChatListForAgent(agentState.currentAgentId);
}

// 修改loadChatList为loadChatListForAgent
async loadChatListForAgent(agentId) {
    const chatList = document.getElementById(`chatList-${agentId}`);
    if (!chatList) return;

    try {
        // 调用API加载该agent的对话列表
        // TODO: 后端需要支持按agent_id筛选
        const response = await agentApi.getConversations(50);
        const conversations = response.data || [];

        // ... 渲染逻辑
    } catch (error) {
        console.error('加载聊天列表失败:', error);
    }
}
```

### 5. 后端API修改

#### 需要新增或修改的API：

1. **按Agent筛选对话列表**
```python
# backend/modules/chat/router.py
@router.get("/conversations")
async def get_conversations(
    agent_id: Optional[int] = None,
    limit: int = 50
):
    """Get conversations, optionally filtered by agent_id"""
    # ... implementation
```

2. **保存消息时关联agent_id**
```python
# 在创建消息时添加 agent_id 字段
```

### 6. CSS样式调整

需要确保`.agent-user-section`在隐藏时不占用空间：
```css
.agent-user-section {
    transition: all 0.3s ease;
}

.agent-user-section[style*="display: none"] {
    height: 0;
    overflow: hidden;
}
```

### 7. 测试步骤

1. **创建测试数据**：在数据库中创建多个agent
2. **测试Agent加载**：刷新页面，验证所有agent是否正确显示
3. **测试Agent切换**：点击不同agent，验证界面切换
4. **测试独立对话**：在不同agent中发送消息，验证对话隔离
5. **测试Settings**：点击不同agent的Settings，验证配置独立

## 实现优先级

1. ✅ **P0 - agentState.js 重构**（已完成）
2. **P0 - AgentSidebar.js 动态加载**
3. **P0 - AgentPage.js 多页面支持**
4. **P0 - agentHandlers.js 事件绑定更新**
5. **P1 - 后端API按agent筛选**
6. **P2 - CSS样式优化**
7. **P3 - 测试和调试**

## 注意事项

1. **ID命名规范**：所有动态创建的DOM元素ID都要包含agent_id，避免冲突
2. **事件绑定**：使用事件委托或data-attribute绑定事件
3. **状态同步**：切换agent时确保agentState.currentAgentId正确更新
4. **性能优化**：初始只渲染第一个agent的详细内容，其他agent按需加载
5. **错误处理**：API失败时显示友好的错误提示

## 后续优化

1. **懒加载**：agent section和page按需创建，而不是一次性创建所有
2. **缓存机制**：缓存每个agent的对话列表
3. **虚拟滚动**：如果agent数量很多，使用虚拟滚动优化性能
4. **搜索功能**：在agent列表中添加搜索功能

---

完成这些修改后，系统将支持：
- ✅ 从数据库动态加载agent列表
- ✅ 每个agent有独立的侧边栏section和聊天页面
- ✅ 点击agent时展开该agent，折叠其他agent
- ✅ Settings按钮打开特定agent的配置
- ✅ 每个agent的对话历史完全独立
