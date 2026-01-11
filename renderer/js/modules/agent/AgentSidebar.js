/**
 * Agent Sidebar - 侧边栏渲染
 * AI助手选择和聊天列表
 */

const AgentSidebar = {
    render() {
        return `
            <div class="sidebar-section agent-user-section">
                <div class="agent-user-header">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#5f6368"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 9h-2V9h2v2zm0 4h-2v-2h2v2zM13 9V3.5L18.5 9H13z"/></svg>
                    <span class="agent-username">Altman (it is me)</span>
                </div>
                <!-- 大图标按钮 -->
                <div class="agent-action-buttons">
                    <button class="agent-action-btn" id="newChatBtn">
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
                    <button class="agent-action-btn" id="settingBtn">
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
            </div>
            <div class="sidebar-section">
                <!-- 搜索框 -->
                <div class="agent-search">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#9e9e9e"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                    <input type="text" class="search-input" placeholder="Keyword+Enter,Blank+Enter to reset">
                </div>
                <!-- Chat List / Tag List 切换 -->
                <div class="chat-list-tabs">
                    <button class="chat-tab active" data-tab="chatList">Chat List</button>
                    <button class="chat-tab" data-tab="tagList">Tag List</button>
                </div>
                <!-- 聊天列表 -->
                <div class="chat-list-container" id="chatListContainer">
                    <div class="chat-list-header">Chat List</div>
                    <div class="chat-tree" id="chatList">
                        <div class="tree-node">
                            <span class="tree-toggle">▼</span>
                            <span class="tree-label">All</span>
                        </div>
                        <div class="tree-children">
                            <div class="tree-item"><span class="item-icon">⭐</span><span class="item-text">introduce me to the functio...</span></div>
                            <div class="tree-item active"><span class="item-text">hello</span></div>
                            <div class="tree-item"><span class="item-text">@upload:go</span></div>
                            <div class="tree-item"><span class="item-text">@download:go</span></div>
                            <div class="tree-item"><span class="item-text">hello</span></div>
                            <div class="tree-item"><span class="item-text">hello</span></div>
                            <div class="tree-item"><span class="item-text">hello</span></div>
                            <div class="tree-item"><span class="item-text">js 如何修改person_data_me的nic...</span></div>
                            <div class="tree-item"><span class="item-text">请分析一下宇徳时代</span></div>
                            <div class="tree-item"><span class="item-text">我想购买苹果特斯拉，intel，微软...</span></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="sidebar-section agent-list-section">
                <!-- Agent 列表 -->
                <div class="agent-list" id="agentList">
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Balabala</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Justin</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Peter</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Musk (Planner)</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Mike (Critic)</span>
                    </div>
                    <!-- Management Buttons -->
                    <div class="agent-item agent-management" data-page="model-management">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>模型管理</span>
                    </div>
                    <div class="agent-item agent-management" data-page="role-management">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>
                        <span>角色管理</span>
                    </div>
                    <div class="agent-item agent-management">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/></svg>
                        <span>Agent Management</span>
                    </div>
                </div>
            </div>
        `;
    }
};

export default AgentSidebar;
