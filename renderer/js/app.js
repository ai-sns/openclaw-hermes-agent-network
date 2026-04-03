/**
 * AI-SNS Main Application
 * Application entry point and initialization
 */

const App = {
    currentPage: null,  // Initially null to ensure first navigation runs
    initialized: false,
    sidebarCollapsed: false,
    _snsEngineStartupStopAttempted: false,

    async init() {
        if (this.initialized) return;

        console.log('Initializing AI-SNS...');

        // Initialize theme
        this.initTheme();

        // Bind navigation events (high priority, non-blocking)
        this.bindNavigationEvents();

        // Bind sidebar collapse events
        this.bindSidebarToggle();

        // Bind window control buttons
        this.bindWindowControls();

        // Bind keyboard shortcuts
        this.bindKeyboardShortcuts();

        // Listen for Electron events
        this.bindElectronEvents();

        // Decide initial landing page by system_init.status: not initialized -> Home, initialized -> SNS
        const initialPage = await this.getInitialPage();
        this.navigateTo(initialPage);

        // Initialize API client asynchronously (non-blocking)
        this.initApiAsync();

        // Fix the issue where inputs cannot be edited in Windows frameless windows
        this.fixInputFocus();

        this.initialized = true;
        console.log('AI-SNS initialized successfully');
    },

    // Fix input focus issue
    fixInputFocus() {
        setTimeout(() => {
            // Create a temporary input to capture focus, then remove it
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

    // Initialize API asynchronously (non-blocking)
    initApiAsync() {
        // Use Promise rather than await to avoid blocking
        Promise.resolve().then(async () => {
            try {
                await this.checkApiConnection();
                await this.ensureSnsEngineStoppedOnStartup();
                await this.initWebSocket();
            } catch (error) {
                console.warn('API initialization failed:', error);
            }
        });
    },

    async ensureSnsEngineStoppedOnStartup() {
        if (this._snsEngineStartupStopAttempted) return;
        this._snsEngineStartupStopAttempted = true;

        try {
            if (!window.api || typeof window.api.get !== 'function') {
                return;
            }

            const status = await window.api.get('/api/sns/engine-status');
            const taskStatus = String(status?.task_status || '').toLowerCase();
            const shouldStop = !!(
                status &&
                status.success &&
                (status.running || status.started || taskStatus === 'started' || taskStatus === 'paused')
            );

            if (!shouldStop) return;

            console.log('[App] Backend SNS engine is active on startup, stopping it...');
            await window.api.post('/api/sns/stop-engine', {});
        } catch (e) {
            console.warn('[App] Failed to stop SNS engine on startup:', e);
        }
    },

    async getInitialPage() {
        try {
            if (window.api && typeof window.api.init === 'function') {
                await window.api.init();
            }

            const res = await window.api.get('/api/system/init-wizard/draft');
            const status = Number(res?.data?.status);
            if (res && res.success && status !== 1) {
                return 'home';
            }
        } catch (e) {
            console.warn('[App] Failed to resolve initial page, fallback to sns:', e);
        }
        return 'sns';
    },

    async checkApiConnection() {
        try {
            // Set a timeout to avoid waiting too long
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

            // Listen for chat responses
            api.onWebSocketMessage('chat_response', (message) => {
                console.log('Received chat response:', message);
            });

            // Listen for map chat messages
            api.onWebSocketMessage('map_chat_message', (message) => {
                console.log('Received map chat message:', message);
                // TODO: Handle map chat messages, e.g. show in map chat UI
            });

            // Listen for notifications
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
        // Left navigation bar icon click events
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

        // Sidebar width bounds
        const minWidth = 200;
        const maxWidth = 450;
        const defaultWidth = 280;
        let currentWidth = defaultWidth;
        let isResizing = false;
        let lastClickTime = 0;

        // Collapse button click
        if (collapseBtn) {
            collapseBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.toggleSidebar();
            });
        }

        // Double click to collapse
        resizer.addEventListener('dblclick', () => {
            if (!this.sidebarCollapsed) {
                this.toggleSidebar();
            }
        });

        // Click to expand when collapsed
        resizer.addEventListener('click', () => {
            if (this.sidebarCollapsed) {
                this.toggleSidebar();
            }
        });

        // Drag to resize width
        resizer.addEventListener('mousedown', (e) => {
            if (this.sidebarCollapsed) return;
            if (e.target === collapseBtn || collapseBtn.contains(e.target)) return;

            isResizing = true;
            resizer.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            // Disable iframe pointer events to avoid lag while dragging
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                iframe.style.pointerEvents = 'none';
            });

            const startX = e.clientX;
            const startWidth = sidebar.offsetWidth;

            const onMouseMove = (e) => {
                if (!isResizing) return;

                const deltaX = e.clientX - startX;
                let newWidth = startWidth + deltaX;

                // Clamp width to bounds
                newWidth = Math.max(minWidth, Math.min(maxWidth, newWidth));

                // If dragged small enough, auto-collapse
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

                // Restore iframe pointer events
                iframes.forEach(iframe => {
                    iframe.style.pointerEvents = '';
                });

                document.removeEventListener('mousemove', onMouseMove);
                document.removeEventListener('mouseup', onMouseUp);
            };

            document.addEventListener('mousemove', onMouseMove);
            document.addEventListener('mouseup', onMouseUp);
        });

        // Save and restore sidebar state
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

        // Restore initial state
        this.restoreSidebarState();
    },

    bindWindowControls() {
        // Window control buttons
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
                // Update button icon state
                const isMaximized = await window.electronAPI.windowIsMaximized();
                maximizeBtn.classList.toggle('maximized', isMaximized);
            });
        }

        // Theme toggle button
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

        // Update BrowserView bounds
        if (window.electronAPI && window.electronAPI.updateBrowserViewBounds) {
            window.electronAPI.updateBrowserViewBounds(this.sidebarCollapsed);
        }

        // Save state
        if (this.saveSidebarState) {
            this.saveSidebarState();
        }
    },

    bindKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + B: collapse/expand sidebar
            if ((e.ctrlKey || e.metaKey) && e.key === 'b') {
                e.preventDefault();
                this.toggleSidebar();
            }

            // Ctrl/Cmd + K: search
            if ((e.ctrlKey || e.metaKey) && e.key === 'k') {
                e.preventDefault();
                this.showSearchModal();
            }

            // Ctrl/Cmd + ,: settings
            if ((e.ctrlKey || e.metaKey) && e.key === ',') {
                e.preventDefault();
                this.showSettingsModal();
            }

            // Ctrl/Cmd + 1-6: quick navigation
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

        // Listen for menu actions
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

        // Listen for navigation events
        window.electronAPI.onNavigate((page) => {
            this.navigateTo(page);
        });
    },

    navigateTo(page) {
        if (window.router) {
            window.router.navigateTo(page);
        } else {
            console.error('[App] Router not available, cannot navigate to:', page);
        }
    },

    showSearchModal() {
        Modal.show({
            title: 'Search',
            content: `
                <div class="search-modal">
                    <input type="text" class="search-input-field" placeholder="Search agents, chats, knowledge bases..." autofocus>
                    <div class="search-results"></div>
                </div>
            `,
            showCancel: false,
            confirmText: 'Close'
        });
    },

    showSettingsModal() {
        const currentTheme = this.getCurrentTheme();
        const currentLang = localStorage.getItem('language') || 'zh';
        const apiServer = localStorage.getItem('apiServer') || 'http://localhost:8000';

        Modal.show({
            title: 'Settings',
            content: `
                <div class="settings-modal">
                    <div class="setting-group">
                        <label>Theme</label>
                        <div class="theme-switcher">
                            <button class="theme-option ${currentTheme === 'light' ? 'active' : ''}" data-theme="light">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="12" cy="12" r="5"/>
                                    <path d="M12 1v2M12 21v2M4.22 4.22l1.42 1.42M18.36 18.36l1.42 1.42M1 12h2M21 12h2M4.22 19.78l1.42-1.42M18.36 5.64l1.42-1.42"/>
                                </svg>
                                <span>Light</span>
                            </button>
                            <button class="theme-option ${currentTheme === 'dark' ? 'active' : ''}" data-theme="dark">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"/>
                                </svg>
                                <span>Dark</span>
                            </button>
                        </div>
                    </div>
                    <div class="setting-group">
                        <label>Language</label>
                        <select class="setting-select" id="languageSelect">
                            <option value="zh" ${currentLang === 'zh' ? 'selected' : ''}>Chinese</option>
                            <option value="en" ${currentLang === 'en' ? 'selected' : ''}>English</option>
                        </select>
                    </div>
                    <div class="setting-group">
                        <label>API Server URL</label>
                        <input type="text" class="setting-input" id="apiServerInput" value="${apiServer}">
                    </div>
                </div>
            `,
            confirmText: 'Save',
            onConfirm: () => {
                const lang = document.getElementById('languageSelect').value;
                const apiUrl = document.getElementById('apiServerInput').value;
                localStorage.setItem('language', lang);
                localStorage.setItem('apiServer', apiUrl);
                if (typeof Notification !== 'undefined' && Notification.success) {
                    Notification.success('Settings saved');
                }
            }
        });

        // Bind theme toggle button events
        setTimeout(() => {
            document.querySelectorAll('.theme-option').forEach(btn => {
                btn.addEventListener('click', () => {
                    const theme = btn.dataset.theme;
                    this.applyTheme(theme);
                    // Update button state
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
        window.dispatchEvent(new CustomEvent('theme-changed', { detail: { theme } }));
        console.log(`Body classes: ${document.body.className}`);
    },

    initTheme() {
        const savedTheme = localStorage.getItem('theme');
        if (savedTheme) {
            this.applyTheme(savedTheme);
        } else {
            // Detect system theme preference
            if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
                this.applyTheme('dark');
            } else {
                this.applyTheme('light');
            }
        }

        // Listen for system theme changes
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
            title: 'About AI-SNS',
            content: `
                <div class="about-modal">
                    <div class="about-logo">
                        <svg viewBox="0 0 24 24" width="64" height="64" fill="#1a73e8">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                    </div>
                    <h2>AI-SNS</h2>
                    <p class="about-subtitle">AI Agent Social Network</p>
                    <p class="about-version">Version: 1.0.0</p>
                    <p class="about-desc">An intelligent social network platform enabling collaboration between AI-to-AI and AI-to-human.</p>
                    <p class="about-link">
                        <a href="https://www.ai-sns.net" target="_blank">www.ai-sns.net</a>
                    </p>
                </div>
            `,
            showCancel: false,
            confirmText: 'Close'
        });
    },

    showHelpModal() {
        Modal.show({
            title: 'Help',
            content: `
                <div class="help-modal">
                    <h4>Shortcuts</h4>
                    <ul class="help-list">
                        <li><kbd>Ctrl/Cmd + B</kbd> Collapse/expand sidebar</li>
                        <li><kbd>Ctrl/Cmd + K</kbd> Search</li>
                        <li><kbd>Ctrl/Cmd + ,</kbd> Settings</li>
                        <li><kbd>Ctrl/Cmd + 1-6</kbd> Quick navigation</li>
                        <li><kbd>Enter</kbd> Send message</li>
                        <li><kbd>Shift + Enter</kbd> New line</li>
                    </ul>
                    <h4>Sidebar</h4>
                    <ul class="help-list">
                        <li><strong>Drag to resize</strong> - Drag the divider to adjust width</li>
                        <li><strong>Double-click to collapse</strong> - Double-click the divider to collapse quickly</li>
                        <li><strong>Floating button</strong> - Hover to show the collapse button</li>
                    </ul>
                    <h4>Modules</h4>
                    <ul class="help-list">
                        <li><strong>SNS</strong> - Social exploration on the map</li>
                        <li><strong>Agent</strong> - AI agent chat</li>
                        <li><strong>KM</strong> - Knowledge base management</li>
                        <li><strong>Tools</strong> - Plugins and tools</li>
                        <li><strong>Web</strong> - Online LLM services</li>
                        <li><strong>Home</strong> - Home settings</li>
                    </ul>
                </div>
            `,
            showCancel: false,
            confirmText: 'Close'
        });
    }
};

// App initialization
document.addEventListener('DOMContentLoaded', () => {
    App.init().catch(console.error);
});

// Export for global access
window.App = App;
