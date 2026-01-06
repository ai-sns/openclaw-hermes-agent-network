/**
 * AI-SNS Main Application
 * 应用程序入口和初始化
 */

const App = {
    currentPage: null,  // 初始为 null，确保首次导航能执行
    initialized: false,
    sidebarCollapsed: false,

    async init() {
        if (this.initialized) return;

        console.log('Initializing AI-SNS...');

        // 初始化主题
        this.initTheme();

        // 绑定导航事件（优先执行，不阻塞）
        this.bindNavigationEvents();

        // 绑定侧边栏折叠事件
        this.bindSidebarToggle();

        // 绑定窗口控制按钮
        this.bindWindowControls();

        // 绑定键盘快捷键
        this.bindKeyboardShortcuts();

        // 监听Electron事件
        this.bindElectronEvents();

        // 默认加载第一个导航项 SNS（优先显示界面）
        this.navigateTo('sns');

        // 异步初始化API客户端（不阻塞UI）
        this.initApiAsync();

        // 修复 Windows 无边框窗口输入框无法编辑的问题
        this.fixInputFocus();

        this.initialized = true;
        console.log('AI-SNS initialized successfully');
    },

    // 修复输入框焦点问题
    fixInputFocus() {
        setTimeout(() => {
            // 创建一个临时输入框获取焦点后移除
            const tempInput = document.createElement('input');
            tempInput.style.position = 'absolute';
            tempInput.style.opacity = '0';
            tempInput.style.pointerEvents = 'none';
            document.body.appendChild(tempInput);
            tempInput.focus();
            tempInput.blur();
            document.body.removeChild(tempInput);
        }, 200);
    },

    // 异步初始化 API（不阻塞 UI）
    initApiAsync() {
        // 使用 Promise 而不是 await，避免阻塞
        Promise.resolve().then(async () => {
            try {
                await api.init();
                await this.checkApiConnection();
                await this.initWebSocket();
            } catch (error) {
                console.warn('API initialization failed:', error);
            }
        });
    },

    async checkApiConnection() {
        try {
            // 设置超时，避免长时间等待
            const timeoutPromise = new Promise((_, reject) =>
                setTimeout(() => reject(new Error('Connection timeout')), 3000)
            );
            await Promise.race([api.healthCheck(), timeoutPromise]);
            console.log('API server connected');
        } catch (error) {
            console.error('API server connection failed:', error);
        }
    },

    async initWebSocket() {
        if (!api.connectWebSocket) return;

        const clientId = this.generateId();
        try {
            await api.connectWebSocket(clientId);

            // 监听聊天响应
            api.onWebSocketMessage('chat_response', (message) => {
                console.log('Received chat response:', message);
            });

            // 监听通知
            api.onWebSocketMessage('notification', (message) => {
                if (typeof Notification !== 'undefined' && Notification.info) {
                    Notification.info(message.content);
                }
            });

        } catch (error) {
            console.warn('WebSocket connection failed:', error);
        }
    },

    generateId() {
        return 'xxxxxxxx-xxxx-4xxx-yxxx-xxxxxxxxxxxx'.replace(/[xy]/g, function(c) {
            const r = Math.random() * 16 | 0;
            const v = c === 'x' ? r : (r & 0x3 | 0x8);
            return v.toString(16);
        });
    },

    bindNavigationEvents() {
        // 左侧图标导航栏点击事件
        document.querySelectorAll('.nav-icon-item').forEach(item => {
            item.addEventListener('click', () => {
                const page = item.dataset.page;
                if (page) {
                    this.navigateTo(page);
                }
            });
        });
    },

    bindSidebarToggle() {
        const resizer = document.getElementById('sidebarResizer');
        const collapseBtn = document.getElementById('sidebarCollapseBtn');
        const sidebar = document.getElementById('secondarySidebar');

        if (!resizer || !sidebar) return;

        // 侧边栏宽度范围
        const minWidth = 200;
        const maxWidth = 450;
        const defaultWidth = 280;
        let currentWidth = defaultWidth;
        let isResizing = false;
        let lastClickTime = 0;

        // 折叠按钮点击
        if (collapseBtn) {
            collapseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleSidebar();
            });
        }

        // 双击折叠
        resizer.addEventListener('dblclick', () => {
            if (!this.sidebarCollapsed) {
                this.toggleSidebar();
            }
        });

        // 折叠状态点击展开
        resizer.addEventListener('click', () => {
            if (this.sidebarCollapsed) {
                this.toggleSidebar();
            }
        });

        // 拖拽调整宽度
        resizer.addEventListener('mousedown', (e) => {
            if (this.sidebarCollapsed) return;
            if (e.target === collapseBtn || collapseBtn.contains(e.target)) return;

            isResizing = true;
            resizer.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            const startX = e.clientX;
            const startWidth = sidebar.offsetWidth;

            const onMouseMove = (e) => {
                if (!isResizing) return;

                const deltaX = e.clientX - startX;
                let newWidth = startWidth + deltaX;

                // 限制宽度范围
                newWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));

                // 如果拖动到很小，自动折叠
                if (newWidth < minWidth + 20 && deltaX < -50) {
                    this.toggleSidebar();
                    onMouseUp();
                    return;
                }

                currentWidth = newWidth;
                sidebar.style.width = `${newWidth}px`;
            };

            const onMouseUp = () => {
                isResizing = false;
                resizer.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        // 保存和恢复侧边栏状态
        this.restoreSidebarState = () => {
            const savedWidth = localStorage.getItem('sidebarWidth');
            const savedCollapsed = localStorage.getItem('sidebarCollapsed');

            if (savedCollapsed === 'true') {
                this.sidebarCollapsed = true;
                sidebar.classList.add('collapsed');
                resizer.classList.add('collapsed');
            } else if (savedWidth) {
                currentWidth = parseInt(savedWidth, 10);
                sidebar.style.width = `${currentWidth}px`;
            }
        };

        this.saveSidebarState = () => {
            localStorage.setItem('sidebarWidth', currentWidth);
            localStorage.setItem('sidebarCollapsed', this.sidebarCollapsed);
        };

        // 初始恢复状态
        this.restoreSidebarState();
    },

    bindWindowControls() {
        // 窗口控制按钮
        const closeBtn = document.getElementById('windowClose');
        const minimizeBtn = document.getElementById('windowMinimize');
        const maximizeBtn = document.getElementById('windowMaximize');

        if (closeBtn && window.electronAPI) {
            closeBtn.addEventListener('click', () => {
                window.electronAPI.windowClose();
            });
        }

        if (minimizeBtn && window.electronAPI) {
            minimizeBtn.addEventListener('click', () => {
                window.electronAPI.windowMinimize();
            });
        }

        if (maximizeBtn && window.electronAPI) {
            maximizeBtn.addEventListener('click', async () => {
                window.electronAPI.windowMaximize();
                // 更新按钮图标状态
                const isMaximized = await window.electronAPI.windowIsMaximized();
                maximizeBtn.classList.toggle('maximized', isMaximized);
            });
        }

        // 主题切换按钮
        const themeToggleBtn = document.getElementById('themeToggleBtn');
        if (themeToggleBtn) {
            themeToggleBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                const currentTheme = this.getCurrentTheme();
                const newTheme = currentTheme === 'dark' ? 'light' : 'dark';
                console.log(`Switching theme from ${currentTheme} to ${newTheme}`);
                this.applyTheme(newTheme);
            });
        }
    },

    toggleSidebar() {
        this.sidebarCollapsed = !this.sidebarCollapsed;
        const sidebar = document.getElementById('secondarySidebar');
        const resizer = document.getElementById('sidebarResizer');
        const mainContent = document.getElementById('mainContent');

        if (this.sidebarCollapsed) {
            sidebar.classList.add('collapsed');
            resizer.classList.add('collapsed');
            mainContent.classList.add('sidebar-collapsed');
        } else {
            sidebar.classList.remove('collapsed');
            resizer.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed');
        }

        // 保存状态
        if (this.saveSidebarState) {
            this.saveSidebarState();
        }
    },

    bindKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + B: 折叠/展开侧边栏
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                this.toggleSidebar();
            }

            // Ctrl/Cmd + K: 搜索
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.showSearchModal();
            }

            // Ctrl/Cmd + ,: 设置
            if ((e.ctrlKey || e.metaKey) && e.key === ',') {
                e.preventDefault();
                this.showSettingsModal();
            }

            // Ctrl/Cmd + 1-6: 快速导航
            if ((e.ctrlKey || e.metaKey) && e.key >= '1' && e.key <= '6') {
                e.preventDefault();
                const pages = ['sns', 'agent', 'km', 'tools', 'web', 'home'];
                const pageIndex = parseInt(e.key) - 1;
                if (pages[pageIndex]) {
                    this.navigateTo(pages[pageIndex]);
                }
            }
        });
    },

    bindElectronEvents() {
        if (!window.electronAPI) return;

        // 监听菜单操作
        window.electronAPI.onMenuAction((action) => {
            switch (action) {
                case 'settings':
                    this.showSettingsModal();
                    break;
                case 'about':
                    this.showAboutModal();
                    break;
                case 'help':
                    this.showHelpModal();
                    break;
            }
        });

        // 监听导航事件
        window.electronAPI.onNavigate((page) => {
            this.navigateTo(page);
        });
    },

    navigateTo(page) {
        if (this.currentPage === page) return;

        console.log(`Navigating to: ${page}`);
        this.currentPage = page;

        // 更新导航栏状态
        document.querySelectorAll('.nav-icon-item').forEach(item => {
            item.classList.toggle('active', item.dataset.page === page);
        });

        // 渲染侧边栏内容
        this.renderSidebar(page);

        // 渲染主内容区
        this.renderMainContent(page);

        // 初始化页面控制器
        this.initPageController(page);
    },

    renderSidebar(page) {
        const sidebar = document.getElementById('secondarySidebar');
        if (!sidebar) return;

        let sidebarContent = '';

        switch (page) {
            case 'home':
                sidebarContent = PageRenderers.renderHomeSidebar();
                break;
            case 'sns':
                sidebarContent = PageRenderers.renderSNSSidebar();
                break;
            case 'agent':
                sidebarContent = PageRenderers.renderAgentSidebar();
                break;
            case 'km':
                sidebarContent = PageRenderers.renderKMSidebar();
                break;
            case 'tools':
                sidebarContent = PageRenderers.renderToolsSidebar();
                break;
            case 'web':
                sidebarContent = PageRenderers.renderWebSidebar();
                break;
            default:
                sidebarContent = PageRenderers.renderHomeSidebar();
        }

        sidebar.innerHTML = sidebarContent;
    },

    renderMainContent(page) {
        const mainContent = document.getElementById('mainContent');
        if (!mainContent) return;

        let pageContent = '';

        switch (page) {
            case 'home':
                pageContent = PageRenderers.renderHomePage();
                break;
            case 'sns':
                pageContent = PageRenderers.renderSNSPage();
                break;
            case 'agent':
                pageContent = PageRenderers.renderAgentPage();
                break;
            case 'km':
                pageContent = PageRenderers.renderKMPage();
                break;
            case 'tools':
                pageContent = PageRenderers.renderToolsPage();
                break;
            case 'web':
                pageContent = PageRenderers.renderWebPage();
                break;
            default:
                pageContent = PageRenderers.renderHomePage();
        }

        mainContent.innerHTML = pageContent;
    },

    initPageController(page) {
        switch (page) {
            case 'home':
                PageControllers.initHomePage();
                break;
            case 'sns':
                PageControllers.initSNSPage();
                break;
            case 'agent':
                PageControllers.initAgentPage();
                break;
            case 'km':
                PageControllers.initKMPage();
                break;
            case 'tools':
                PageControllers.initToolsPage();
                break;
            case 'web':
                PageControllers.initWebPage();
                break;
        }
    },

    showSearchModal() {
        Modal.show({
            title: '搜索',
            content: `
                <div class="search-modal">
                    <input type="text" class="search-input-field" placeholder="搜索Agent、聊天、知识库..." autofocus>
                    <div class="search-results"></div>
                </div>
            `,
            showCancel: false,
            confirmText: '关闭'
        });
    },

    showSettingsModal() {
        const currentTheme = this.getCurrentTheme();
        const currentLang = localStorage.getItem('language') || 'zh';
        const apiServer = localStorage.getItem('apiServer') || 'http://localhost:8000';

        Modal.show({
            title: '设置',
            content: `
                <div class="settings-modal">
                    <div class="setting-group">
                        <label>外观主题</label>
                        <div class="theme-switcher">
                            <button class="theme-option ${currentTheme === 'light' ? 'active' : ''}" data-theme="light">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="5"/>
                                    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                                </svg>
                                <span>亮色</span>
                            </button>
                            <button class="theme-option ${currentTheme === 'dark' ? 'active' : ''}" data-theme="dark">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                                </svg>
                                <span>暗色</span>
                            </button>
                        </div>
                    </div>
                    <div class="setting-group">
                        <label>语言</label>
                        <select class="setting-select" id="languageSelect">
                            <option value="zh" ${currentLang === 'zh' ? 'selected' : ''}>中文</option>
                            <option value="en" ${currentLang === 'en' ? 'selected' : ''}>English</option>
                        </select>
                    </div>
                    <div class="setting-group">
                        <label>API 服务器地址</label>
                        <input type="text" class="setting-input" id="apiServerInput" value="${apiServer}">
                    </div>
                </div>
            `,
            confirmText: '保存',
            onConfirm: () => {
                const lang = document.getElementById('languageSelect').value;
                const apiUrl = document.getElementById('apiServerInput').value;
                localStorage.setItem('language', lang);
                localStorage.setItem('apiServer', apiUrl);
                if (typeof Notification !== 'undefined' && Notification.success) {
                    Notification.success('设置已保存');
                }
            }
        });

        // 绑定主题切换按钮事件
        setTimeout(() => {
            document.querySelectorAll('.theme-option').forEach(btn => {
                btn.addEventListener('click', () => {
                    const theme = btn.dataset.theme;
                    this.applyTheme(theme);
                    // 更新按钮状态
                    document.querySelectorAll('.theme-option').forEach(b => b.classList.remove('active'));
                    btn.classList.add('active');
                });
            });
        }, 100);
    },

    getCurrentTheme() {
        if (document.body.classList.contains('theme-dark')) return 'dark';
        if (document.body.classList.contains('theme-light')) return 'light';
        return localStorage.getItem('theme') || 'light';
    },

    applyTheme(theme) {
        console.log(`Applying theme: ${theme}`);
        document.body.classList.remove('theme-light', 'theme-dark');
        document.body.classList.add(`theme-${theme}`);
        localStorage.setItem('theme', theme);
        console.log(`Body classes: ${document.body.className}`);
    },

    initTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            this.applyTheme(savedTheme);
        } else {
            // 检测系统主题偏好
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                this.applyTheme('dark');
            } else {
                this.applyTheme('light');
            }
        }

        // 监听系统主题变化
        if (window.matchMedia) {
            window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', (e) => {
                if (!localStorage.getItem('theme')) {
                    this.applyTheme(e.matches ? 'dark' : 'light');
                }
            });
        }
    },

    showAboutModal() {
        Modal.show({
            title: '关于 AI-SNS',
            content: `
                <div class="about-modal">
                    <div class="about-logo">
                        <svg viewBox="0 0 24 24" width="64" height="64" fill="#1a73e8">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                    </div>
                    <h2>AI-SNS</h2>
                    <p class="about-subtitle">AI Agent Social Network</p>
                    <p class="about-version">版本: 1.0.0</p>
                    <p class="about-desc">智能社交网络平台，支持AI与AI、AI与人的通讯协作</p>
                    <p class="about-link">
                        <a href="https://www.ai-sns.net" target="_blank">www.ai-sns.net</a>
                    </p>
                </div>
            `,
            showCancel: false,
            confirmText: '关闭'
        });
    },

    showHelpModal() {
        Modal.show({
            title: '帮助',
            content: `
                <div class="help-modal">
                    <h4>快捷键</h4>
                    <ul class="help-list">
                        <li><kbd>Ctrl/Cmd + B</kbd> 折叠/展开侧边栏</li>
                        <li><kbd>Ctrl/Cmd + K</kbd> 搜索</li>
                        <li><kbd>Ctrl/Cmd + ,</kbd> 设置</li>
                        <li><kbd>Ctrl/Cmd + 1-6</kbd> 快速导航</li>
                        <li><kbd>Enter</kbd> 发送消息</li>
                        <li><kbd>Shift + Enter</kbd> 换行</li>
                    </ul>
                    <h4>侧边栏操作</h4>
                    <ul class="help-list">
                        <li><strong>拖拽调整</strong> - 拖动分隔线调整宽度</li>
                        <li><strong>双击折叠</strong> - 双击分隔线快速折叠</li>
                        <li><strong>悬浮按钮</strong> - 悬浮显示折叠按钮</li>
                    </ul>
                    <h4>功能模块</h4>
                    <ul class="help-list">
                        <li><strong>SNS</strong> - 地图社交探索</li>
                        <li><strong>Agent</strong> - AI Agent对话</li>
                        <li><strong>KM</strong> - 知识库管理</li>
                        <li><strong>Tools</strong> - 插件工具</li>
                        <li><strong>Web</strong> - LLM在线服务</li>
                        <li><strong>Home</strong> - 首页设置</li>
                    </ul>
                </div>
            `,
            showCancel: false,
            confirmText: '关闭'
        });
    }
};

// 应用初始化
document.addEventListener('DOMContentLoaded', () => {
    App.init().catch(console.error);
});

// 导出全局访问
window.App = App;
