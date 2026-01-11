/**
 * Agent Handlers - 事件处理
 * 处理用户交互、消息发送、流式响应等
 */

import agentState from './agentState.js';
import agentApi from './agentApi.js';

const agentHandlers = {
    currentManagementPage: null, // 跟踪当前打开的管理页面

    /**
     * 初始化
     */
    init() {
        this.loadAgentList();
        this.loadChatList();
        this.loadModelOptions();
        this.loadRoleOptions();
        this.bindEvents();
        this.initChatStreamListeners();
    },

    /**
     * 绑定事件
     */
    bindEvents() {
        // 新建对话按钮
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => this.handleNewChat());
        }

        // 设置按钮
        const settingBtn = document.getElementById('settingBtn');
        if (settingBtn) {
            settingBtn.addEventListener('click', () => this.handleSettings());
        }

        // 发送消息
        const sendBtn = document.getElementById('sendMessageBtn');
        const chatInput = document.getElementById('chatInput');

        if (sendBtn) {
            sendBtn.addEventListener('click', () => this.sendMessage());
        }

        if (chatInput) {
            chatInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                    e.preventDefault();
                    this.sendMessage();
                }
            });
        }

        // 模型选择器
        const modelSelector = document.getElementById('modelSelector');
        if (modelSelector) {
            modelSelector.addEventListener('change', (e) => {
                agentState.setModel(e.target.value);
            });
        }

        // 角色选择器
        const roleSelector = document.getElementById('roleSelector');
        if (roleSelector) {
            roleSelector.addEventListener('change', (e) => {
                agentState.setRole(e.target.value);
            });
        }

        // 聊天标签切换
        document.querySelectorAll('.chat-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.chat-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
            });
        });

        // 管理页面导航 - 初始绑定（loadAgentList 后会重新绑定）
        this.bindManagementButtonEvents();

        // 右侧设置面板 - 页签切换
        this.initSettingsPanelTabs();

        // 右侧设置面板 - 折叠/展开
        this.initSettingsPanelCollapse();

        // Prompt 相关事件
        this.initPromptEvents();

        // File 相关事件
        this.initFileEvents();

        // Plugin 相关事件
        this.initPluginEvents();
    },

    /**
     * 初始化设置面板页签切换
     */
    initSettingsPanelTabs() {
        // 使用事件委托绑定到父容器，避免缓存问题
        const settingsTabs = document.getElementById('settingsTabs');
        if (!settingsTabs) return;

        settingsTabs.addEventListener('click', (e) => {
            // 查找被点击的页签按钮
            const tab = e.target.closest('.settings-tab');
            if (!tab) return;

            const targetTab = tab.dataset.tab;

            // 每次点击时重新查询所有页签（包括动态添加的插件页签）
            const allTabs = document.querySelectorAll('.settings-tab');
            const allPanes = document.querySelectorAll('.settings-tab-content .tab-pane');

            // 切换激活状态
            allTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // 切换内容显示
            allPanes.forEach(pane => {
                if (pane.dataset.tab === targetTab) {
                    pane.classList.add('active');
                } else {
                    pane.classList.remove('active');
                }
            });
        });
    },

    /**
     * 初始化设置面板折叠/展开（使用SNS的toggle模式）
     */
    initSettingsPanelCollapse() {
        const panel = document.getElementById('agentSettingsPanel');
        const collapseBtn = document.getElementById('agentPanelCollapseBtn');
        const resizer = document.querySelector('.agent-panel-resizer');

        if (collapseBtn && panel) {
            collapseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isCollapsed = panel.classList.toggle('collapsed');
                if (resizer) {
                    resizer.classList.toggle('collapsed', isCollapsed);
                }
                // 保存状态到 localStorage
                localStorage.setItem('agentPanelCollapsed', isCollapsed);
                console.log('Panel toggled, collapsed:', isCollapsed);
            });

            // 从 localStorage 恢复状态
            const savedCollapsed = localStorage.getItem('agentPanelCollapsed') === 'true';
            if (savedCollapsed) {
                panel.classList.add('collapsed');
                if (resizer) {
                    resizer.classList.add('collapsed');
                }
            }
        }
    },

    /**
     * 初始化 Prompt 相关事件
     */
    initPromptEvents() {
        // 保存 System Prompt
        const saveBtns = document.querySelectorAll('.prompt-save-btn');
        saveBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const textarea = document.getElementById('systemPrompt');
                if (textarea) {
                    const prompt = textarea.value.trim();
                    agentState.setSystemPrompt(prompt);
                    if (typeof Notification !== 'undefined') {
                        Notification.success('System Prompt 已保存');
                    }
                }
            });
        });

        // 使用预设 Prompt
        const presetUseBtns = document.querySelectorAll('.preset-use-btn');
        presetUseBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const presetItem = btn.closest('.preset-item');
                const preset = presetItem.dataset.preset;
                const textarea = document.getElementById('systemPrompt');

                if (textarea) {
                    const prompts = {
                        'developer': '你是一个资深的程序员，精通多种编程语言和框架。你擅长编写高质量、可维护的代码，并能够清晰地解释技术概念。',
                        'writer': '你是一个富有创意的写作助手，擅长创作各类文学作品。你的文字优美流畅，富有感染力，能够根据不同主题和风格进行创作。',
                        'analyst': '你是一个专业的数据分析师，擅长从数据中提取洞察。你能够清晰地解释复杂的数据模式，并提供可操作的建议。'
                    };

                    textarea.value = prompts[preset] || '';
                    if (typeof Notification !== 'undefined') {
                        Notification.success('已应用预设 Prompt');
                    }
                }
            });
        });
    },

    /**
     * 初始化 File 相关事件
     */
    initFileEvents() {
        // 上传文件按钮
        const uploadBtn = document.querySelector('.file-upload-btn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                // 创建文件输入元素
                const fileInput = document.createElement('input');
                fileInput.type = 'file';
                fileInput.multiple = true;
                fileInput.accept = '*/*';

                fileInput.addEventListener('change', (e) => {
                    const files = Array.from(e.target.files);
                    if (files.length > 0) {
                        this.handleFileUpload(files);
                    }
                });

                fileInput.click();
            });
        }
    },

    /**
     * 处理文件上传
     */
    handleFileUpload(files) {
        const fileList = document.getElementById('chatFileList');
        if (!fileList) return;

        // 移除空状态
        const emptyState = fileList.querySelector('.empty-state');
        if (emptyState) {
            emptyState.remove();
        }

        files.forEach(file => {
            const fileItem = document.createElement('div');
            fileItem.className = 'file-item';
            fileItem.innerHTML = `
                <div class="file-icon">
                    <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                    </svg>
                </div>
                <div class="file-info">
                    <div class="file-name">${file.name}</div>
                    <div class="file-size">${this.formatFileSize(file.size)}</div>
                </div>
                <button class="file-remove-btn" title="移除文件">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            `;

            // 绑定移除按钮
            const removeBtn = fileItem.querySelector('.file-remove-btn');
            removeBtn.addEventListener('click', () => {
                fileItem.remove();

                // 如果没有文件了，显示空状态
                if (fileList.children.length === 0) {
                    fileList.innerHTML = `
                        <div class="empty-state">
                            <svg viewBox="0 0 24 24" width="48" height="48" fill="#ccc">
                                <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                            </svg>
                            <p>暂无文件</p>
                        </div>
                    `;
                }
            });

            fileList.appendChild(fileItem);
        });

        if (typeof Notification !== 'undefined') {
            Notification.success(`已添加 ${files.length} 个文件`);
        }
    },

    /**
     * 格式化文件大小
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * 初始化 Plugin 相关事件
     */
    initPluginEvents() {
        // 绑定输入区域工具栏的"添加"按钮（第一个 toolbar-icon-btn）
        const toolbarButtons = document.querySelectorAll('.input-toolbar .toolbar-icon-btn');
        const addToolbarBtn = toolbarButtons[0]; // 第一个按钮是"添加"按钮

        const handleAddPlugin = () => {
            if (typeof Modal === 'undefined') {
                console.error('Modal component not loaded');
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

                    this.loadPlugin(pluginId);
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
        };

        // 绑定工具栏"添加"按钮
        if (addToolbarBtn) {
            addToolbarBtn.addEventListener('click', handleAddPlugin);
            console.log('[AgentHandlers] 已绑定工具栏添加按钮到插件选择');
        } else {
            console.warn('[AgentHandlers] 未找到工具栏添加按钮');
        }
    },

    /**
     * 加载插件 - 动态创建页签和内容
     */
    loadPlugin(pluginId) {
        console.log('[AgentHandlers] 开始加载插件:', pluginId);

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
            console.error('[AgentHandlers] 未知的插件ID:', pluginId);
            return;
        }

        // 检查插件是否已加载
        const existingTab = document.querySelector(`.settings-tab[data-tab="plugin-${pluginId}"]`);
        if (existingTab) {
            console.log('[AgentHandlers] 插件已存在，切换到该页签');
            existingTab.click();
            if (typeof Notification !== 'undefined') {
                Notification.info(`${config.fullName} 已加载`);
            }
            return;
        }

        // 1. 创建页签按钮
        const settingsTabs = document.getElementById('settingsTabs');
        if (!settingsTabs) {
            console.error('[AgentHandlers] 未找到设置页签容器');
            return;
        }

        const tabButton = document.createElement('button');
        tabButton.className = 'settings-tab';
        tabButton.dataset.tab = `plugin-${pluginId}`;
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
            this.removePluginTab(pluginId);
        });

        // 注意：页签切换事件由 initSettingsPanelTabs() 的事件委托统一处理，这里不需要单独绑定

        settingsTabs.appendChild(tabButton);
        console.log('[AgentHandlers] ✓ 已创建页签按钮');

        // 2. 创建页签内容
        const tabContent = document.getElementById('settingsTabContent');
        if (!tabContent) {
            console.error('[AgentHandlers] 未找到页签内容容器');
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
                <div class="plugin-content" id="plugin-content-${pluginId}">
                    <p style="font-size: 11px; color: #999; text-align: center; padding: 20px;">正在加载插件...</p>
                </div>
            </div>
        `;

        tabContent.appendChild(tabPane);
        console.log('[AgentHandlers] ✓ 已创建页签内容');

        // 3. 激活新创建的页签
        tabButton.click();

        // 4. 加载插件具体内容
        this.loadPluginContent(pluginId);

        if (typeof Notification !== 'undefined') {
            Notification.success(`${config.fullName} 已加载`);
        }

        console.log('[AgentHandlers] ✓ 插件加载完成');
    },

    /**
     * 移除插件页签
     */
    removePluginTab(pluginId) {
        console.log('[AgentHandlers] 移除插件:', pluginId);

        // 移除页签按钮
        const tabButton = document.querySelector(`.settings-tab[data-tab="plugin-${pluginId}"]`);
        if (tabButton) {
            // 如果当前页签是激活状态，切换到 Param 页签
            if (tabButton.classList.contains('active')) {
                const paramTab = document.querySelector('.settings-tab[data-tab="param"]');
                if (paramTab) {
                    paramTab.click();
                }
            }
            tabButton.remove();
        }

        // 移除页签内容
        const tabPane = document.querySelector(`.tab-pane[data-tab="plugin-${pluginId}"]`);
        if (tabPane) {
            tabPane.remove();
        }

        if (typeof Notification !== 'undefined') {
            Notification.info('插件已移除');
        }

        console.log('[AgentHandlers] ✓ 插件已移除');
    },

    /**
     * 加载插件内容
     */
    loadPluginContent(pluginId) {
        const container = document.getElementById(`plugin-content-${pluginId}`);
        if (!container) {
            console.error('[AgentHandlers] 未找到插件内容容器:', `plugin-content-${pluginId}`);
            return;
        }

        // 根据插件 ID 加载不同的内容
        switch (pluginId) {
            case 'mindmap':
                this.loadMindmapPlugin(container);
                break;
            case 'code':
                this.loadCodePlugin(container);
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
     * 加载思维导图插件
     */
    loadMindmapPlugin(container) {
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
                <button class="preset-use-btn" style="width: 100%; margin-bottom: 6px;" onclick="agentHandlers.showMindmapExample()">填充示例代码</button>
                <button class="preset-use-btn" style="width: 100%;" onclick="agentHandlers.askAIForMindmap()">让 AI 生成思维导图</button>
            </div>
        `;
    },

    /**
     * 显示思维导图示例 - 直接填充可用的代码
     */
    showMindmapExample() {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = '```mindmap\n- 学习编程\n  - 基础知识\n    - 数据类型\n    - 控制流程\n    - 函数\n  - 实践项目\n    - Web开发\n    - 移动应用\n    - 数据分析\n  - 进阶学习\n    - 算法与数据结构\n    - 设计模式\n    - 系统架构\n```';
            if (typeof Notification !== 'undefined') {
                Notification.info('已填充示例代码，点击发送按钮即可看到思维导图效果');
            }
            // 聚焦输入框
            input.focus();
        }
    },

    /**
     * 让 AI 生成思维导图
     */
    askAIForMindmap() {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = '请帮我生成一个关于"人工智能发展历程"的思维导图。\n\n请严格使用以下格式：\n```mindmap\n- 根节点\n  - 子节点（用2个空格缩进）\n    - 孙节点（用4个空格缩进）\n```\n\n注意：\n1. 代码块语言必须是 mindmap\n2. 每个节点用 "- " 开头\n3. 子节点用2个空格缩进\n4. 不要使用 Tab 键';
            if (typeof Notification !== 'undefined') {
                Notification.info('已填充 AI 请求，发送后等待 AI 按照正确格式回复');
            }
            // 聚焦输入框
            input.focus();
        }
    },

    /**
     * 加载代码执行插件
     */
    loadCodePlugin(container) {
        if (window.CodePlugin) {
            window.CodePlugin.render(container);
        } else {
            container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">代码执行插件未加载，请刷新页面</p>';
            console.error('[AgentHandlers] CodePlugin 未找到');
        }
    },

    /**
     * 初始化流式聊天监听器
     */
    initChatStreamListeners() {
        if (!window.electronAPI) return;

        // 清除旧的监听器
        if (window.electronAPI.removeChatStreamListeners) {
            window.electronAPI.removeChatStreamListeners();
        }

        // 监听流式数据
        window.electronAPI.onChatStreamData((data) => {
            if (data.requestId === agentState.getRequestId()) {
                agentState.appendStreamingContent(data.content);
                this.updateStreamingMessage(agentState.getStreamingContent());
            }
        });

        // 监听流结束
        window.electronAPI.onChatStreamEnd((data) => {
            if (data.requestId === agentState.getRequestId()) {
                this.finalizeStreamingMessage();
                agentState.clearRequestId();
            }
        });

        // 监听错误
        window.electronAPI.onChatStreamError((data) => {
            if (data.requestId === agentState.getRequestId()) {
                this.showStreamError(data.error);
                agentState.clearRequestId();
            }
        });
    },

    /**
     * 加载模型选项
     */
    async loadModelOptions() {
        const modelSelector = document.getElementById('modelSelector');
        if (!modelSelector) return;

        try {
            const response = await fetch('http://localhost:8788/api/agent/llm-configs');
            const result = await response.json();

            if (result.success && result.data) {
                const models = result.data.filter(m => m.is_active !== false);

                if (models.length > 0) {
                    // 保存第一个选项，如果没有默认模型
                    let defaultModel = models.find(m => m.is_default) || models[0];

                    modelSelector.innerHTML = models.map(model => `
                        <option value="${model.config_id}" ${model.is_default ? 'selected' : ''}>
                            ${model.name}${model.provider ? ` (${model.provider})` : ''}
                        </option>
                    `).join('');

                    // 设置当前选中的模型
                    if (defaultModel) {
                        agentState.setModel(defaultModel.config_id);
                    }
                } else {
                    modelSelector.innerHTML = '<option value="">暂无可用模型</option>';
                }
            }
        } catch (error) {
            console.error('加载模型列表失败:', error);
            // 保留默认选项
        }
    },

    /**
     * 加载角色选项
     */
    async loadRoleOptions() {
        const roleSelector = document.getElementById('roleSelector');
        if (!roleSelector) return;

        try {
            const response = await fetch('http://localhost:8788/api/agent/role-configs');
            const result = await response.json();

            if (result.success && result.data) {
                const roles = result.data.filter(r => r.is_active !== false);

                if (roles.length > 0) {
                    // 保存第一个选项，如果没有默认角色
                    let defaultRole = roles.find(r => r.is_default) || roles[0];

                    roleSelector.innerHTML = roles.map(role => `
                        <option value="${role.role_id}" ${role.is_default ? 'selected' : ''}>
                            ${role.name}${role.category ? ` - ${role.category}` : ''}
                        </option>
                    `).join('');

                    // 设置当前选中的角色
                    if (defaultRole) {
                        agentState.setRole(defaultRole.role_id);
                    }
                } else {
                    roleSelector.innerHTML = '<option value="">暂无可用角色</option>';
                }
            }
        } catch (error) {
            console.error('加载角色列表失败:', error);
            // 保留默认选项
        }
    },

    /**
     * 加载Agent列表
     */
    async loadAgentList() {
        const agentList = document.getElementById('agentList');
        if (!agentList) return;

        try {
            const response = await agentApi.getAgents();
            const agents = response.data || [];
            agentState.setAgents(agents);

            if (agents.length === 0) {
                agentList.innerHTML = '<div class="empty-state">暂无Agent</div>';
                // 仍然需要添加管理按钮
                this.appendManagementButtons(agentList);
                return;
            }

            // 保留所有管理按钮
            const managementItems = agentList.querySelectorAll('.agent-management');

            agentList.innerHTML = agents.map(agent => `
                <div class="agent-item" data-id="${agent.id}">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    <span>${agent.name}</span>
                </div>
            `).join('');

            // 重新添加所有管理按钮
            managementItems.forEach(item => {
                agentList.appendChild(item.cloneNode(true));
            });

            // 重新绑定管理按钮的事件
            this.bindManagementButtonEvents();
        } catch (error) {
            console.error('加载Agent列表失败:', error);
            agentList.innerHTML = '<div class="empty-state error">加载失败</div>';
            // 加载失败时也添加管理按钮
            this.appendManagementButtons(agentList);
        }
    },

    /**
     * 添加管理按钮
     */
    appendManagementButtons(agentList) {
        const managementButtonsHtml = `
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
                    <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                </svg>
                <span>Agent Management</span>
            </div>
        `;
        agentList.insertAdjacentHTML('beforeend', managementButtonsHtml);
        this.bindManagementButtonEvents();
    },

    /**
     * 绑定管理按钮的事件
     */
    bindManagementButtonEvents() {
        document.querySelectorAll('.agent-management[data-page]').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                this.navigateToManagementPage(page);
            });
        });
    },

    /**
     * 加载聊天列表
     */
    async loadChatList() {
        const chatList = document.getElementById('chatList');
        if (!chatList) return;

        try {
            const response = await agentApi.getChatHistory();
            const chats = response.data || [];
            agentState.setChats(chats);

            const treeChildren = chatList.querySelector('.tree-children');
            if (!treeChildren) return;

            if (chats.length === 0) {
                treeChildren.innerHTML = '<div class="empty-state">暂无对话</div>';
                return;
            }

            treeChildren.innerHTML = chats.map((chat, index) => `
                <div class="tree-item ${index === 1 ? 'active' : ''}" data-id="${chat.id}">
                    ${chat.starred ? '<span class="item-icon">⭐</span>' : ''}
                    <span class="item-text">${chat.title}</span>
                </div>
            `).join('');
        } catch (error) {
            console.error('加载聊天列表失败:', error);
        }
    },

    /**
     * 处理新建对话
     */
    handleNewChat() {
        // 关闭管理页面
        this.closeManagementPage();

        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        Modal.show({
            title: '新建对话',
            content: `
                <div class="form-group">
                    <label>对话标题（可选）</label>
                    <input type="text" class="form-input" id="chatTitle" placeholder="输入对话标题">
                </div>
            `,
            confirmText: '创建',
            showCancel: true,
            onConfirm: () => {
                const title = document.getElementById('chatTitle')?.value || '新对话';
                agentState.reset();
                this.clearChatMessages();
                if (typeof Notification !== 'undefined') {
                    Notification.success(`已创建对话: ${title}`);
                }
            }
        });
    },

    /**
     * 处理设置
     */
    handleSettings() {
        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        Modal.show({
            title: 'Agent设置',
            content: `
                <div class="form-group">
                    <label>温度 (Temperature)</label>
                    <input type="range" class="form-range" id="temperature" min="0" max="1" step="0.1" value="0.7">
                    <span id="temperatureValue">0.7</span>
                </div>
                <div class="form-group">
                    <label>最大令牌数 (Max Tokens)</label>
                    <input type="number" class="form-input" id="maxTokens" value="2000">
                </div>
                <div class="form-group">
                    <label>Top P</label>
                    <input type="range" class="form-range" id="topP" min="0" max="1" step="0.1" value="0.9">
                    <span id="topPValue">0.9</span>
                </div>
            `,
            confirmText: '保存',
            showCancel: true,
            onConfirm: () => {
                if (typeof Notification !== 'undefined') {
                    Notification.success('设置已保存');
                }
            }
        });

        // 绑定滑动条事件
        setTimeout(() => {
            const temperatureSlider = document.getElementById('temperature');
            const temperatureValue = document.getElementById('temperatureValue');
            if (temperatureSlider && temperatureValue) {
                temperatureSlider.addEventListener('input', (e) => {
                    temperatureValue.textContent = e.target.value;
                });
            }

            const topPSlider = document.getElementById('topP');
            const topPValue = document.getElementById('topPValue');
            if (topPSlider && topPValue) {
                topPSlider.addEventListener('input', (e) => {
                    topPValue.textContent = e.target.value;
                });
            }
        }, 100);
    },

    /**
     * 发送消息
     */
    async sendMessage() {
        // 关闭管理页面
        this.closeManagementPage();

        const input = document.getElementById('chatInput');
        const messagesContainer = document.getElementById('chatMessages');
        const sendBtn = document.getElementById('sendMessageBtn');

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
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
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
            if (window.electronAPI && window.electronAPI.chatStreamStart) {
                await agentApi.sendMessageStream(messages, requestId);

                // 设置超时处理
                setTimeout(() => {
                    if (agentState.getRequestId() === requestId) {
                        this.showStreamError('请求超时，请重试');
                        agentState.clearRequestId();
                        enableSendBtn();
                    }
                }, 120000); // 2分钟超时

                // 监听完成事件以启用按钮
                const checkComplete = setInterval(() => {
                    if (!agentState.getRequestId()) {
                        enableSendBtn();
                        clearInterval(checkComplete);
                    }
                }, 100);
            } else {
                // 如果没有 electronAPI，使用模拟响应
                this.simulateStreamResponse(enableSendBtn);
            }
        } catch (error) {
            console.error('发送消息失败:', error);
            this.showStreamError(error.message);
            agentState.clearRequestId();
            enableSendBtn();
        }
    },

    /**
     * 更新流式消息显示
     */
    updateStreamingMessage(content) {
        const streamingBody = document.querySelector('.message-item.streaming .message-body');
        if (streamingBody) {
            streamingBody.innerHTML = this.renderMarkdown(content, true) + '<span class="cursor-blink"></span>';
            const messagesContainer = document.getElementById('chatMessages');
            if (messagesContainer) {
                messagesContainer.scrollTop = messagesContainer.scrollHeight;
            }
        }
    },

    /**
     * 完成流式消息
     */
    finalizeStreamingMessage() {
        const streamingMsg = document.querySelector('.message-item.streaming');
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                const content = agentState.getStreamingContent();
                streamingBody.innerHTML = this.renderMarkdown(content);
                // 高亮代码块
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
     * 显示流错误
     */
    showStreamError(error) {
        const streamingMsg = document.querySelector('.message-item.streaming');
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
     * 模拟流式响应（用于开发测试）
     */
    simulateStreamResponse(enableSendBtn) {
        const mockResponse = `好的，我来回答你的问题。

## 示例代码

这是一个简单的 Python 示例：

\`\`\`python
def hello_world():
    print("Hello, World!")
    return True

# 调用函数
if __name__ == "__main__":
    hello_world()
\`\`\`

### 主要特点：

1. **简洁明了** - 代码结构清晰
2. **易于理解** - 注释完善
3. **可扩展性强** - 便于后续修改

> 提示：这只是一个演示示例，实际使用时请根据需求调整。

如果你有其他问题，欢迎继续提问！`;

        let index = 0;
        const chars = mockResponse.split('');

        const streamInterval = setInterval(() => {
            if (index < chars.length) {
                agentState.appendStreamingContent(chars[index]);
                this.updateStreamingMessage(agentState.getStreamingContent());
                index++;
            } else {
                clearInterval(streamInterval);
                this.finalizeStreamingMessage();
                agentState.clearRequestId();
                if (enableSendBtn) enableSendBtn();
            }
        }, 20);
    },

    /**
     * Markdown 渲染
     */
    renderMarkdown(text, isStreaming = false) {
        if (!text) return '';

        // 保存代码块，避免被其他规则处理
        const codeBlocks = [];

        // 完整的代码块处理
        text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const language = lang || 'plaintext';
            const rawCode = code.trim();
            const escapedCode = this.escapeHtml(rawCode);
            const escapedRawCode = this.escapeHtml(rawCode).replace(/"/g, '&quot;');
            const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
            codeBlocks.push(`<div class="code-block"><div class="code-header"><span class="code-lang">${language}</span><button class="copy-code-btn" onclick="agentHandlers.copyCode(this)"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg><span>复制</span></button></div><pre><code class="language-${language}" data-raw-code="${escapedRawCode}">${escapedCode}</code></pre></div>`);
            return placeholder;
        });

        // 处理不完整的代码块（流式输出中）
        if (isStreaming) {
            text = text.replace(/```(\w*)\n?([\s\S]*)$/g, (match, lang, code) => {
                if (match.includes('__CODEBLOCK_')) return match;
                const language = lang || 'plaintext';
                const escapedCode = this.escapeHtml(code);
                const escapedRawCode = this.escapeHtml(code).replace(/"/g, '&quot;');
                const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
                codeBlocks.push(`<div class="code-block streaming-code"><div class="code-header"><span class="code-lang">${language}</span></div><pre><code class="language-${language}" data-raw-code="${escapedRawCode}">${escapedCode}</code></pre></div>`);
                return placeholder;
            });
        }

        // 行内代码
        text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // 粗体
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // 斜体
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // 标题
        text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');

        // 无序列表
        text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
        text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

        // 链接
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

        // 引用块
        text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

        // 换行处理
        text = text.replace(/\n\n/g, '</p><p>');
        text = text.replace(/\n/g, '<br>');

        // 包裹在段落中
        if (!text.startsWith('<') && !text.startsWith('__CODEBLOCK_')) {
            text = '<p>' + text + '</p>';
        }

        // 还原代码块
        codeBlocks.forEach((block, index) => {
            text = text.replace(`__CODEBLOCK_${index}__`, block);
        });

        return text;
    },

    /**
     * 代码高亮
     */
    highlightCodeBlocks(container) {
        container.querySelectorAll('pre code').forEach(block => {
            if (block.dataset.highlighted) return;
            block.dataset.highlighted = 'true';

            let code = block.textContent;
            block.dataset.rawCode = code;

            let highlighted = this.escapeHtml(code);

            // 关键字高亮
            const keywords = [
                'function', 'const', 'let', 'var', 'if', 'else', 'for', 'while', 'return',
                'class', 'import', 'export', 'from', 'async', 'await', 'try', 'catch',
                'def', 'print', 'self', 'None', 'True', 'False', 'in', 'not', 'and', 'or'
            ];

            const keywordPattern = new RegExp(`\\b(${keywords.join('|')})\\b`, 'g');
            highlighted = highlighted.replace(keywordPattern, '<span class="hljs-keyword">$1</span>');

            // 数字高亮
            highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span class="hljs-number">$1</span>');

            // 字符串高亮
            highlighted = highlighted.replace(/(&quot;[^&]*&quot;|&#39;[^&]*&#39;)/g, '<span class="hljs-string">$1</span>');

            // 注释高亮
            highlighted = highlighted.replace(/(\/\/.*$|#.*$)/gm, '<span class="hljs-comment">$1</span>');

            block.innerHTML = highlighted;
        });
    },

    /**
     * 复制代码
     */
    copyCode(btn) {
        const codeBlock = btn.closest('.code-block');
        const codeElement = codeBlock.querySelector('code');
        const code = codeElement.dataset.rawCode || codeElement.textContent;

        navigator.clipboard.writeText(code).then(() => {
            const originalText = btn.querySelector('span').textContent;
            btn.querySelector('span').textContent = '已复制!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.querySelector('span').textContent = originalText;
                btn.classList.remove('copied');
            }, 2000);
        });
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
     * 清除聊天消息
     */
    clearChatMessages() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            const welcomeMsg = messagesContainer.querySelector('.welcome-message');
            if (welcomeMsg) {
                welcomeMsg.style.display = 'block';
                // 移除其他消息
                messagesContainer.querySelectorAll('.message-item').forEach(item => item.remove());
            }
        }
    },

    /**
     * 导航到管理页面
     */
    async navigateToManagementPage(page) {
        // 先销毁之前打开的管理页面
        if (this.currentManagementPage) {
            if (this.currentManagementPage.destroy) {
                this.currentManagementPage.destroy();
            }
            this.currentManagementPage = null;
        }

        // Import management pages dynamically
        const { ModelManagementPage, RoleManagementPage } = await import('./index.js').then(m => m.default);

        if (page === 'model-management' && ModelManagementPage) {
            this.currentManagementPage = ModelManagementPage;
            await ModelManagementPage.init();
        } else if (page === 'role-management' && RoleManagementPage) {
            this.currentManagementPage = RoleManagementPage;
            await RoleManagementPage.init();
        }
    },

    /**
     * 关闭管理页面，显示主聊天界面
     */
    closeManagementPage() {
        if (this.currentManagementPage) {
            if (this.currentManagementPage.destroy) {
                this.currentManagementPage.destroy();
            }
            this.currentManagementPage = null;

            // 重新加载模型和角色选项（因为可能在管理页面中修改了）
            this.loadModelOptions();
            this.loadRoleOptions();
        }
    },

    /**
     * 销毁
     */
    destroy() {
        // 清理事件监听器
        agentState.reset();
    }
};

// 导出为全局对象，以便在HTML中调用
if (typeof window !== 'undefined') {
    window.agentHandlers = agentHandlers;
}

export default agentHandlers;
