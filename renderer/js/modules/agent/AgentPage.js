/**
 * Agent Page - 主内容渲染（多Agent动态加载版本）
 * AI聊天界面
 */

const AgentPage = {
    /**
     * 渲染主内容区 - 返回基础结构，由init()动态填充
     */
    render() {
        return `<div id="agent-pages-container"></div>`;
    },

    /**
     * 初始化 - 为每个Agent创建page
     */
    async init(agents) {
        console.log('[AgentPage] 开始初始化，agents数量:', agents.length);

        const container = document.getElementById('agent-pages-container');
        if (!container) {
            console.error('[AgentPage] 找不到agent-pages-container');
            return;
        }

        agents.forEach((agent, index) => {
            const pageHTML = this.createAgentPageHTML(agent, index === 0);
            container.insertAdjacentHTML('beforeend', pageHTML);
        });

        console.log('[AgentPage] 所有Agent pages已创建');
    },

    /**
     * 创建单个Agent的page HTML
     */
    createAgentPageHTML(agent, isActive = false) {
        return `
            <div id="page-agent-${agent.id}" class="agent-page-layout" data-agent-id="${agent.id}" style="display: ${isActive ? 'flex' : 'none'}">
                <!-- 聊天主区域 -->
                <div class="agent-chat-area">
                    <!-- 顶部工具栏 -->
                    <div class="agent-chat-toolbar">
                        <div class="toolbar-left">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="#1a73e8">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                            </svg>
                        </div>
                        <div class="toolbar-center">
                            <select class="model-selector" id="modelSelector-${agent.id}" data-agent-id="${agent.id}">
                                <option value="gpt-4o">Baichuan_local:gpt-4o</option>
                                <option value="gpt-4">GPT-4</option>
                                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                <option value="claude-3">Claude 3</option>
                                <option value="deepseek">DeepSeek</option>
                            </select>
                        </div>
                        <div class="toolbar-right">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="#5f6368">
                                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                            </svg>
                            <select class="role-selector" id="roleSelector-${agent.id}" data-agent-id="${agent.id}">
                                <option value="senior-dev">资深的程序员</option>
                                <option value="assistant">通用助手</option>
                                <option value="writer">创意写作</option>
                                <option value="analyst">数据分析师</option>
                            </select>
                        </div>
                    </div>

                    <!-- 消息区域 -->
                    <div class="agent-chat-messages" id="chatMessages-${agent.id}" data-agent-id="${agent.id}">
                        <!-- 欢迎消息 -->
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
                            <h2 class="welcome-title">${agent.name || 'AI Assistant'}</h2>
                            <p class="welcome-subtitle">${agent.description || 'Powered by Azure OpenAI GPT'}</p>
                            <div class="welcome-tips">
                                <div class="tip-item">
                                    <span class="tip-icon">💡</span>
                                    <span>输入问题，按 Enter 发送</span>
                                </div>
                                <div class="tip-item">
                                    <span class="tip-icon">📝</span>
                                    <span>支持 Markdown 格式输出</span>
                                </div>
                                <div class="tip-item">
                                    <span class="tip-icon">🔄</span>
                                    <span>实时流式响应</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 输入区域 -->
                    <div class="agent-chat-input-area">
                        <div class="input-hint">Input @@ to load tools selector; Ctrl+i To load preset question; Ctrl+/ To insert chat template.</div>
                        <div class="input-wrapper">
                            <textarea class="agent-chat-input" id="chatInput-${agent.id}" data-agent-id="${agent.id}" placeholder="输入消息..."></textarea>
                        </div>
                        <div class="input-toolbar">
                            <div class="toolbar-buttons">
                                <button class="toolbar-icon-btn config-tools-btn" title="配置工具" data-agent-id="${agent.id}">
                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                        <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                                    </svg>
                                </button>
                                <button class="toolbar-icon-btn" title="添加" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg></button>
                                <button class="toolbar-icon-btn" title="附件" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/></svg></button>
                                <button class="toolbar-icon-btn" title="图片" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg></button>
                                <button class="toolbar-icon-btn" title="文档" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg></button>
                                <button class="toolbar-icon-btn" title="列表" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M4 10.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zm0-6c-.83 0-1.5.67-1.5 1.5S3.17 7.5 4 7.5 5.5 6.83 5.5 6 4.83 4.5 4 4.5zm0 12c-.83 0-1.5.68-1.5 1.5s.68 1.5 1.5 1.5 1.5-.68 1.5-1.5-.67-1.5-1.5-1.5zM7 19h14v-2H7v2zm0-6h14v-2H7v2zm0-8v2h14V5H7z"/></svg></button>
                                <button class="toolbar-icon-btn" title="屏幕" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M20 18c1.1 0 1.99-.9 1.99-2L22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z"/></svg></button>
                                <button class="toolbar-icon-btn" title="视频" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg></button>
                                <button class="toolbar-icon-btn" title="窗口" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/></svg></button>
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
                    <button class="panel-collapse-btn" id="agentPanelCollapseBtn-${agent.id}" data-agent-id="${agent.id}" title="折叠设置面板">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="9,6 15,12 9,18"/>
                        </svg>
                    </button>
                </div>

                <!-- 右侧设置面板 -->
                <div class="agent-settings-panel" id="agentSettingsPanel-${agent.id}" data-agent-id="${agent.id}">
                    <!-- 页签内容区域 -->
                    <div class="settings-tab-content" id="settingsTabContent-${agent.id}">
                        <!-- Param 页签内容 -->
                        <div class="tab-pane active" data-tab="param">
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                                    </svg>
                                    <span>模型参数</span>
                                </div>
                                <div class="param-group">
                                    <label class="param-label">
                                        <span>Temperature</span>
                                        <input type="number" class="param-input" value="0.7" min="0" max="2" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Max Tokens</span>
                                        <input type="number" class="param-input" value="2048" min="1" max="8192" step="1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Top P</span>
                                        <input type="number" class="param-input" value="0.9" min="0" max="1" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Frequency Penalty</span>
                                        <input type="number" class="param-input" value="0" min="-2" max="2" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Presence Penalty</span>
                                        <input type="number" class="param-input" value="0" min="-2" max="2" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                </div>
                            </div>
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>
                                    </svg>
                                    <span>高级设置</span>
                                </div>
                                <div class="param-group">
                                    <label class="param-toggle">
                                        <span>Stream 模式</span>
                                        <input type="checkbox" checked data-agent-id="${agent.id}">
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <label class="param-toggle">
                                        <span>显示 Token 用量</span>
                                        <input type="checkbox" data-agent-id="${agent.id}">
                                        <span class="toggle-slider"></span>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <!-- Prompt 页签内容 -->
                        <div class="tab-pane" data-tab="prompt">
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                                    </svg>
                                    <span>System Prompt</span>
                                </div>
                                <div class="prompt-editor">
                                    <textarea class="prompt-textarea" id="systemPrompt-${agent.id}" data-agent-id="${agent.id}" placeholder="输入系统提示词...">你是一个资深的程序员，精通多种编程语言和框架。</textarea>
                                    <button class="prompt-save-btn" data-agent-id="${agent.id}">保存</button>
                                </div>
                            </div>
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                                    </svg>
                                    <span>预设 Prompt</span>
                                </div>
                                <div class="preset-list">
                                    <div class="preset-item" data-preset="developer" data-agent-id="${agent.id}">
                                        <span class="preset-name">资深程序员</span>
                                        <button class="preset-use-btn" data-agent-id="${agent.id}">使用</button>
                                    </div>
                                    <div class="preset-item" data-preset="writer" data-agent-id="${agent.id}">
                                        <span class="preset-name">创意写作</span>
                                        <button class="preset-use-btn" data-agent-id="${agent.id}">使用</button>
                                    </div>
                                    <div class="preset-item" data-preset="analyst" data-agent-id="${agent.id}">
                                        <span class="preset-name">数据分析</span>
                                        <button class="preset-use-btn" data-agent-id="${agent.id}">使用</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- File 页签内容 -->
                        <div class="tab-pane" data-tab="file">
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/>
                                    </svg>
                                    <span>聊天文件</span>
                                    <button class="file-upload-btn" title="上传文件" data-agent-id="${agent.id}">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                                        </svg>
                                    </button>
                                </div>
                                <div class="file-list" id="chatFileList-${agent.id}" data-agent-id="${agent.id}">
                                    <div class="empty-state">
                                        <svg viewBox="0 0 24 24" width="48" height="48" fill="#ccc">
                                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                                        </svg>
                                        <p>暂无文件</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- 插件页签将在此处动态添加 -->
                    </div>

                    <!-- 底部页签按钮 -->
                    <div class="settings-tabs" id="settingsTabs-${agent.id}">
                        <button class="settings-tab active" data-tab="param" data-agent-id="${agent.id}">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                                <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                            </svg>
                            <span>Param</span>
                        </button>
                        <button class="settings-tab" data-tab="prompt" data-agent-id="${agent.id}">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                                <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                            </svg>
                            <span>Prompt</span>
                        </button>
                        <button class="settings-tab" data-tab="file" data-agent-id="${agent.id}">
                            <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor">
                                <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                            </svg>
                            <span>File</span>
                        </button>
                    </div>
                </div>

            </div>
        `;
    }
};

export default AgentPage;
