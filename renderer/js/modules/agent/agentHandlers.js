/**
 * Agent Handlers - event handling
 * Handle user interactions, message sending, streaming responses, etc.
 */

import agentState from './agentState.js';
import agentApi from './agentApi.js';

const agentHandlers = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },

    async _deleteRendererPlugin(pluginId) {
        const base = await this._getApiBaseUrl();
        if (!base) {
            if (typeof Notification !== 'undefined') {
                Notification.error('API base URL not available');
            }
            return false;
        }

        const id = pluginId ? String(pluginId).trim() : '';
        if (!id) return false;

        try {
            const resp = await fetch(`${base}/api/tools/plugins/${encodeURIComponent(id)}`, {
                method: 'DELETE'
            });
            if (!resp.ok) {
                const text = await resp.text();
                throw new Error(text || `HTTP ${resp.status}`);
            }

            // Unload if currently loaded
            try {
                this.unloadAgentRendererPlugin(id);
            } catch (e) {
            }

            if (typeof Notification !== 'undefined') {
                Notification.success('Plugin deleted');
            }
            return true;
        } catch (e) {
            if (typeof Notification !== 'undefined') {
                Notification.error(`Delete failed: ${e && e.message ? e.message : String(e)}`);
            }
            return false;
        }
    },

    async _getApiBaseUrl() {
        try {
            if (window.electronAPI && typeof window.electronAPI.getApiUrl === 'function') {
                const raw = await window.electronAPI.getApiUrl();
                return raw ? String(raw).replace(/\/+$/, '') : '';
            }
        } catch (e) {
        }

        try {
            const raw = (window.appConfig && window.appConfig.agent_server) || '';
            return raw ? String(raw).replace(/\/+$/, '') : '';
        } catch (e) {
        }

        try {
            const u = new URL(this.resolve('/'));
            return u.origin;
        } catch (e) {
        }

        return '';
    },

    async _fetchRendererPlugins() {
        const base = await this._getApiBaseUrl();
        if (!base) return [];

        try {
            const resp = await fetch(`${base}/api/tools/plugins?used_in_sns=false`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            const list = Array.isArray(data) ? data : [];
            return list.filter(p => {
                const pluginType = (p && p.plugin_type) ? String(p.plugin_type) : '';
                return pluginType.toLowerCase() === 'renderer';
            });
        } catch (e) {
            console.warn('[AgentHandlers] Failed to fetch renderer plugins:', e);
            return [];
        }
    },

    _getLoadedRendererPlugins() {
        if (!this._loadedRendererPlugins || typeof this._loadedRendererPlugins !== 'object') {
            this._loadedRendererPlugins = new Map();
        }
        return this._loadedRendererPlugins;
    },

    async loadAgentRendererPlugin(plugin) {
        const settingsTabs = document.getElementById('settingsTabs');
        const tabContent = document.getElementById('settingsTabContent');
        if (!settingsTabs || !tabContent) {
            console.warn('[AgentHandlers] Settings panel not found for renderer plugin');
            return;
        }

        const pluginKey = plugin && (plugin.plugin_id || plugin.id) ? String(plugin.plugin_id || plugin.id) : '';
        if (!pluginKey) return;

        const tabId = `plugin-ext-${pluginKey}`;
        const existingTab = settingsTabs.querySelector(`.settings-tab[data-tab="${CSS.escape(tabId)}"]`);
        const existingPane = tabContent.querySelector(`.tab-pane[data-tab="${CSS.escape(tabId)}"]`);
        if (existingTab && existingPane) {
            existingTab.click();
            return;
        }

        const entryRaw = plugin.filename;
        const entryUrl = this.resolve(entryRaw);
        let mod;
        try {
            mod = await import(entryUrl + '?t=' + Date.now());
        } catch (e) {
            if (typeof Notification !== 'undefined') {
                Notification.error(`Failed to load plugin: ${plugin.name || pluginKey}`);
            }
            return;
        }

        const pluginInstance = mod && mod.default ? mod.default : null;
        if (!pluginInstance || typeof pluginInstance.render !== 'function') {
            if (typeof Notification !== 'undefined') {
                Notification.error(`Invalid plugin module: ${plugin.name || pluginKey}`);
            }
            return;
        }

        const name = plugin.name ? String(plugin.name) : pluginKey;

        const tabButton = document.createElement('button');
        tabButton.className = 'settings-tab';
        tabButton.dataset.tab = tabId;
        tabButton.innerHTML = `
            <span>${name}</span>
            <button class="tab-close-btn" title="Close plugin">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
            </button>
        `;

        const closeBtn = tabButton.querySelector('.tab-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.unloadAgentRendererPlugin(pluginKey);
            });
        }

        settingsTabs.appendChild(tabButton);

        const pane = document.createElement('div');
        pane.className = 'tab-pane';
        pane.dataset.tab = tabId;
        pane.innerHTML = `
            <div class="settings-section">
                <div class="settings-section-title">
                    <span>${name}</span>
                </div>
                <div class="plugin-content" id="plugin-content-ext-${pluginKey}"></div>
            </div>
        `;
        tabContent.appendChild(pane);

        // Activate tab
        tabButton.click();

        const container = pane.querySelector(`#plugin-content-ext-${CSS.escape(pluginKey)}`);
        if (!container) return;

        const api = {
            ui: {
                toast: (type, message) => {
                    const t = type ? String(type) : 'info';
                    const msg = (message === undefined || message === null) ? '' : String(message);
                    if (typeof Notification !== 'undefined' && typeof Notification[t] === 'function') {
                        Notification[t](msg);
                        return;
                    }
                    if (typeof Notification !== 'undefined' && typeof Notification.info === 'function') {
                        Notification.info(msg);
                    }
                },
                openUrl: (url) => {
                    const u = url ? String(url) : '';
                    if (!u) return;
                    try {
                        if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                            window.electronAPI.openUrl(u);
                            return;
                        }
                    } catch (e) {
                    }
                    try {
                        window.open(u, '_blank', 'noopener');
                    } catch (e) {
                    }
                }
            },
            sns: {
                getJson: async (path) => {
                    const base = await this._getApiBaseUrl();
                    const resp = await fetch(`${base}${path}`);
                    return await resp.json();
                },
                postJson: async (path, body) => {
                    const base = await this._getApiBaseUrl();
                    const resp = await fetch(`${base}${path}`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(body || {})
                    });
                    return await resp.json();
                },
                jsonrpc: async (method, params) => {
                    const base = await this._getApiBaseUrl();
                    const payload = {
                        jsonrpc: '2.0',
                        id: Date.now(),
                        method: String(method || ''),
                        params: (params && typeof params === 'object') ? params : {}
                    };
                    const resp = await fetch(`${base}/jsonrpc`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(payload)
                    });
                    return await resp.json();
                }
            }
        };

        try {
            await pluginInstance.render(container, api);
        } catch (e) {
            if (typeof Notification !== 'undefined') {
                Notification.error(`Plugin render failed: ${name}`);
            }
            try {
                container.textContent = `Render failed: ${e && e.message ? e.message : String(e)}`;
            } catch (_) {
            }
        }

        this._getLoadedRendererPlugins().set(pluginKey, {
            plugin,
            pluginInstance,
            tabId
        });
    },

    unloadAgentRendererPlugin(pluginKey) {
        const key = pluginKey ? String(pluginKey) : '';
        if (!key) return;

        const loaded = this._getLoadedRendererPlugins();
        const item = loaded.get(key);
        if (!item) return;

        try {
            if (item.pluginInstance && typeof item.pluginInstance.dispose === 'function') {
                item.pluginInstance.dispose();
            }
        } catch (e) {
            console.warn('[AgentHandlers] Plugin dispose failed:', e);
        }

        const settingsTabs = document.getElementById('settingsTabs');
        const tabContent = document.getElementById('settingsTabContent');
        if (settingsTabs) {
            const tab = settingsTabs.querySelector(`.settings-tab[data-tab="${CSS.escape(item.tabId)}"]`);
            const wasActive = !!(tab && tab.classList && tab.classList.contains('active'));
            if (tab) tab.remove();

            if (wasActive) {
                const fallback = settingsTabs.querySelector('.settings-tab[data-tab="param"]');
                if (fallback) fallback.click();
            }
        }
        if (tabContent) {
            const pane = tabContent.querySelector(`.tab-pane[data-tab="${CSS.escape(item.tabId)}"]`);
            if (pane) pane.remove();
        }

        loaded.delete(key);
    },
    currentManagementPage: null, // Track the currently open management page

    /**
     * Initialization
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
     * Bind events
     */
    bindEvents() {
        // New chat button
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => this.handleNewChat());
        }

        // Settings button
        const settingBtn = document.getElementById('settingBtn');
        if (settingBtn) {
            settingBtn.addEventListener('click', () => this.handleSettings());
        }

        // Send message
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

        // Model selector
        const modelSelector = document.getElementById('modelSelector');
        if (modelSelector) {
            modelSelector.addEventListener('change', async (e) => {
                const configId = e.target.value;
                agentState.setModel(configId);
                // Load and persist the full model configuration
                await this.loadAndApplyModelConfig(configId);
            });
        }

        // Role selector
        const roleSelector = document.getElementById('roleSelector');
        if (roleSelector) {
            roleSelector.addEventListener('change', async (e) => {
                const roleId = e.target.value;
                agentState.setRole(roleId);
                // Load and persist the full role configuration
                await this.loadAndApplyRoleConfig(roleId);
            });
        }

        // Chat tab switching
        document.querySelectorAll('.chat-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.chat-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
            });
        });

        // Management page navigation - initial binding (re-bound after loadAgentList)
        this.bindManagementButtonEvents();

        // Right-side settings panel - tab switching
        this.initSettingsPanelTabs();

        // Right-side settings panel - collapse/expand
        this.initSettingsPanelCollapse();

        // Prompt-related events
        this.initPromptEvents();

        // File-related events
        this.initFileEvents();

        // Plugin-related events
        this.initPluginEvents();

        if (!this._agentUpdatedListenerBound) {
            this._agentUpdatedListenerBound = true;
            window.addEventListener('agent-updated', (e) => {
                const detail = e && e.detail ? e.detail : {};
                const name = detail.name || detail.agent?.name;
                if (!name) return;

                const messagesContainer = document.getElementById('chatMessages');
                if (!messagesContainer) return;

                messagesContainer.querySelectorAll('.message-item.assistant-message .message-sender').forEach(el => {
                    el.textContent = name;
                });

                const welcomeTitle = messagesContainer.querySelector('.welcome-message .welcome-title');
                if (welcomeTitle) {
                    welcomeTitle.textContent = name;
                }
            });
        }
    },

    /**
     * Initialize settings panel tab switching
     */
    initSettingsPanelTabs() {
        // Bind with event delegation on the parent container to avoid caching issues
        const settingsTabs = document.getElementById('settingsTabs');
        if (!settingsTabs) return;

        settingsTabs.addEventListener('click', (e) => {
            // Find the clicked tab button
            const tab = e.target.closest('.settings-tab');
            if (!tab) return;

            const targetTab = tab.dataset.tab;

            // Re-query all tabs on each click (including dynamically added plugin tabs)
            const allTabs = document.querySelectorAll('.settings-tab');
            const allPanes = document.querySelectorAll('.settings-tab-content .tab-pane');

            // Toggle active state
            allTabs.forEach(t => t.classList.remove('active'));
            tab.classList.add('active');

            // Toggle content visibility
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
     * Initialize settings panel collapse/expand (SNS toggle mode)
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
                // Persist state to localStorage
                localStorage.setItem('agentPanelCollapsed', isCollapsed);
                console.log('Panel toggled, collapsed:', isCollapsed);
            });

            // Restore state from localStorage
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
     * Initialize prompt-related events
     */
    initPromptEvents() {
        // Save System Prompt - update into the current role configuration
        const saveBtns = document.querySelectorAll('.prompt-save-btn');
        saveBtns.forEach(btn => {
            btn.addEventListener('click', async () => {
                const textarea = document.getElementById('systemPrompt');
                if (textarea) {
                    const prompt = textarea.value.trim();
                    await this.saveRolePrompt(prompt);
                }
            });
        });

        // Use a preset prompt
        const presetUseBtns = document.querySelectorAll('.preset-use-btn');
        presetUseBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                const presetItem = btn.closest('.preset-item');
                const preset = presetItem.dataset.preset;
                const textarea = document.getElementById('systemPrompt');

                if (textarea) {
                    const prompts = {
                        'developer': 'You are a senior programmer proficient in multiple programming languages and frameworks. You write high-quality, maintainable code and can clearly explain technical concepts.',
                        'writer': 'You are a creative writing assistant skilled at producing various literary works. Your writing is fluent and engaging, and you can adapt to different topics and styles.',
                        'analyst': 'You are a professional data analyst skilled at extracting insights from data. You can explain complex patterns clearly and provide actionable recommendations.'
                    };

                    textarea.value = prompts[preset] || '';
                    if (typeof Notification !== 'undefined') {
                        Notification.success('Preset prompt applied');
                    }
                }
            });
        });

        // Bind parameter input change events - persist to model config in real time
        this.initParamInputListeners();
    },

    /**
     * Initialize file-related events
     */
    initFileEvents() {
        // Upload file button
        const uploadBtn = document.querySelector('.file-upload-btn');
        if (uploadBtn) {
            uploadBtn.addEventListener('click', () => {
                // Create a file input element
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
     * Handle file uploads
     */
    handleFileUpload(files) {
        const fileList = document.getElementById('chatFileList');
        if (!fileList) return;

        // Remove empty state
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
                <button class="file-remove-btn" title="Remove file">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                    </svg>
                </button>
            `;

            // Bind remove button
            const removeBtn = fileItem.querySelector('.file-remove-btn');
            removeBtn.addEventListener('click', () => {
                fileItem.remove();

                // If there are no files left, show the empty state
                if (fileList.children.length === 0) {
                    fileList.innerHTML = `
                        <div class="empty-state">
                            <svg viewBox="0 0 24 24" width="48" height="48" fill="#ccc">
                                <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                            </svg>
                            <p>No files</p>
                        </div>
                    `;
                }
            });

            fileList.appendChild(fileItem);
        });

        if (typeof Notification !== 'undefined') {
            Notification.success(`Added ${files.length} file(s)`);
        }
    },

    /**
     * Format file size
     */
    formatFileSize(bytes) {
        if (bytes === 0) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Initialize plugin-related events
     */
    initPluginEvents() {
        // Bind the input toolbar "add" button (the first toolbar-icon-btn)
        const toolbarButtons = document.querySelectorAll('.input-toolbar .toolbar-icon-btn');
        const addToolbarBtn = toolbarButtons[0]; // The first button is the "add" button

        const handleAddPlugin = () => {
            if (typeof Modal === 'undefined') {
                console.error('Modal component not loaded');
                return;
            }

            Modal.show({
                title: 'Agent Plugins',
                content: `
                    <div style="display:flex; flex-direction:column; gap:12px;">
                        <div class="form-group">
                            <label>Select plugin</label>
                            <select class="form-input" id="agentPluginSelect">
                                <option value="">Loading...</option>
                            </select>
                        </div>
                        <div class="form-group">
                            <label>Description</label>
                            <p style="font-size: 12px; color: var(--text-secondary, #666);" id="agentPluginDescription">Select a plugin to view details</p>
                        </div>
                        <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                            <button type="button" class="btn btn-secondary" id="agentPluginRefreshBtn">Refresh</button>
                            <button type="button" class="btn btn-secondary" id="agentPluginImportBtn">Import zip</button>
                            <button type="button" class="btn btn-secondary" id="agentPluginDeleteBtn" disabled>Delete</button>
                            <input type="file" id="agentPluginImportFile" accept=".zip" style="display:none" />
                        </div>
                    </div>
                `,
                confirmText: 'Load',
                showCancel: true,
                width: '560px',
                onOpen: async () => {
                    const select = document.getElementById('agentPluginSelect');
                    const desc = document.getElementById('agentPluginDescription');
                    const refreshBtn = document.getElementById('agentPluginRefreshBtn');
                    const importBtn = document.getElementById('agentPluginImportBtn');
                    const deleteBtn = document.getElementById('agentPluginDeleteBtn');
                    const importFile = document.getElementById('agentPluginImportFile');

                    const loadIntoUi = async () => {
                        if (!select) return;
                        select.innerHTML = '<option value="">Please select a plugin...</option>';
                        if (desc) desc.textContent = 'Select a plugin to view details';

                        const builtin = [
                            { id: 'mindmap', name: 'Mind map plugin', description: 'Convert Markdown mindmap syntax in chat messages into a visual mind map' },
                            { id: 'code', name: 'Code execution plugin', description: 'Extract code blocks from chat messages and provide edit/run features (supports JavaScript, Python, HTML/CSS/JS)' },
                            { id: 'calendar', name: 'Calendar plugin', description: 'Display and manage calendar events in chat' },
                            { id: 'chart', name: 'Chart plugin', description: 'Visualize data into charts' }
                        ];
                        for (const b of builtin) {
                            const opt = document.createElement('option');
                            opt.value = `builtin:${b.id}`;
                            opt.textContent = b.name;
                            opt.dataset.description = b.description;
                            select.appendChild(opt);
                        }

                        const plugins = await this._fetchRendererPlugins();
                        window.__agentRendererPlugins__ = plugins;
                        if (plugins.length) {
                            const group = document.createElement('optgroup');
                            group.label = 'Imported plugins';
                            for (const p of plugins) {
                                const opt = document.createElement('option');
                                opt.value = `renderer:${p.plugin_id}`;
                                opt.textContent = p.name ? String(p.name) : String(p.plugin_id);
                                group.appendChild(opt);
                            }
                            select.appendChild(group);
                        }
                    };

                    await loadIntoUi();

                    if (select && desc) {
                        select.addEventListener('change', () => {
                            const value = String(select.value || '').trim();
                            if (!value) {
                                desc.textContent = 'Select a plugin to view details';
                                if (deleteBtn) deleteBtn.disabled = true;
                                return;
                            }

                            if (value.startsWith('builtin:')) {
                                const selectedOpt = select.options[select.selectedIndex];
                                const detail = selectedOpt && selectedOpt.dataset && selectedOpt.dataset.description
                                    ? String(selectedOpt.dataset.description)
                                    : '';
                                desc.textContent = detail || 'Select a plugin to view details';

                                if (deleteBtn) deleteBtn.disabled = true;
                                return;
                            }

                            if (value.startsWith('renderer:')) {
                                const id = value.slice('renderer:'.length);
                                const plugins = Array.isArray(window.__agentRendererPlugins__) ? window.__agentRendererPlugins__ : [];
                                const plugin = plugins.find(p => String(p.plugin_id) === String(id));
                                if (!plugin) {
                                    desc.textContent = 'Select a plugin to view details';
                                    if (deleteBtn) deleteBtn.disabled = true;
                                    return;
                                }
                                const name = plugin.name ? String(plugin.name) : 'Unnamed plugin';
                                const version = plugin.version ? String(plugin.version) : '';
                                const detail = plugin.description ? String(plugin.description) : '';
                                desc.textContent = `${name}${version ? ` v${version}` : ''}${detail ? ` - ${detail}` : ''}`;

                                if (deleteBtn) deleteBtn.disabled = false;
                            }
                        });
                    }

                    if (refreshBtn) {
                        refreshBtn.addEventListener('click', async () => {
                            await loadIntoUi();
                        });
                    }

                    if (importBtn && importFile) {
                        importBtn.addEventListener('click', () => {
                            try {
                                importFile.value = '';
                            } catch (e) {
                            }
                            importFile.click();
                        });

                        importFile.addEventListener('change', async () => {
                            const file = importFile.files && importFile.files[0] ? importFile.files[0] : null;
                            if (!file) return;
                            await this._importRendererPluginZip(file);
                            await loadIntoUi();
                        });
                    }

                    if (deleteBtn) {
                        deleteBtn.addEventListener('click', async () => {
                            const value = select ? String(select.value || '').trim() : '';
                            if (!value.startsWith('renderer:')) return;
                            const id = value.slice('renderer:'.length);
                            const ok = window.confirm('Delete selected plugin?');
                            if (!ok) return;
                            const deleted = await this._deleteRendererPlugin(id);
                            if (deleted) {
                                await loadIntoUi();
                                if (desc) desc.textContent = 'Select a plugin to view details';
                                deleteBtn.disabled = true;
                            }
                        });
                    }
                },
                onConfirm: async () => {
                    const select = document.getElementById('agentPluginSelect');
                    const value = select ? String(select.value || '').trim() : '';
                    if (!value) {
                        if (typeof Notification !== 'undefined') {
                            Notification.error('Please select a plugin');
                        }
                        return false;
                    }

                    if (value.startsWith('builtin:')) {
                        const pluginId = value.slice('builtin:'.length);
                        this.loadPlugin(pluginId);
                        return;
                    }

                    if (value.startsWith('renderer:')) {
                        const id = value.slice('renderer:'.length);
                        const plugins = Array.isArray(window.__agentRendererPlugins__) ? window.__agentRendererPlugins__ : [];
                        const plugin = plugins.find(p => String(p.plugin_id) === String(id));
                        if (!plugin) {
                            if (typeof Notification !== 'undefined') {
                                Notification.error('Plugin not found');
                            }
                            return false;
                        }

                        await this.loadAgentRendererPlugin(plugin);
                        return;
                    }

                    if (typeof Notification !== 'undefined') {
                        Notification.error('Unsupported plugin selection');
                    }
                    return false;
                }
            });
        };

        // Bind the toolbar "add" button
        if (addToolbarBtn) {
            addToolbarBtn.addEventListener('click', handleAddPlugin);
            console.log('[AgentHandlers] Toolbar add button bound to plugin selection');
        } else {
            console.warn('[AgentHandlers] Toolbar add button not found');
        }
    },

    /**
     * Load plugin - dynamically create tabs and content
     */
    loadPlugin(pluginId) {
        console.log('[AgentHandlers] Start loading plugin:', pluginId);

        // Plugin configuration
        const pluginConfigs = {
            'mindmap': {
                name: 'Mind map',
                fullName: 'Mind map plugin',
                description: 'Convert Markdown mindmap into a visual mind map',
                icon: '<path d="M12 2l3.09 6.26L22 9.27l-5 4.87 1.18 6.88L12 17.77l-6.18 3.25L7 14.14 2 9.27l6.91-1.01L12 2z"/>'
            },
            'code': {
                name: 'Code execution',
                fullName: 'Code execution plugin',
                description: 'Extract code from chat messages and run it in the browser',
                icon: '<path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>'
            },
            'calendar': {
                name: 'Calendar',
                fullName: 'Calendar plugin',
                description: 'Display and manage calendar events in chat',
                icon: '<path d="M9 11H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2zm2-7h-1V2h-2v2H8V2H6v2H5c-1.11 0-1.99.9-1.99 2L3 20c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V6c0-1.1-.9-2-2-2zm0 16H5V9h14v11z"/>'
            },
            'chart': {
                name: 'Charts',
                fullName: 'Chart plugin',
                description: 'Visualize data into charts',
                icon: '<path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zM9 17H7v-7h2v7zm4 0h-2V7h2v10zm4 0h-2v-4h2v4z"/>'
            }
        };

        const config = pluginConfigs[pluginId];
        if (!config) {
            console.error('[AgentHandlers] Unknown plugin ID:', pluginId);
            return;
        }

        // Check whether the plugin is already loaded
        const existingTab = document.querySelector(`.settings-tab[data-tab="plugin-${pluginId}"]`);
        if (existingTab) {
            console.log('[AgentHandlers] Plugin already exists; switching to its tab');
            existingTab.click();
            if (typeof Notification !== 'undefined') {
                Notification.info(`${config.fullName} loaded`);
            }
            return;
        }

        // 1. Create tab button
        const settingsTabs = document.getElementById('settingsTabs');
        if (!settingsTabs) {
            console.error('[AgentHandlers] Settings tabs container not found');
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
            <button class="tab-close-btn" title="Close plugin">
                <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor">
                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                </svg>
            </button>
        `;

        // Bind close button event
        const closeBtn = tabButton.querySelector('.tab-close-btn');
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removePluginTab(pluginId);
        });

        // Note: tab switching is handled by initSettingsPanelTabs() via event delegation; no extra binding needed here

        settingsTabs.appendChild(tabButton);
        console.log('[AgentHandlers] ✓ Tab button created');

        // 2. Create tab content
        const tabContent = document.getElementById('settingsTabContent');
        if (!tabContent) {
            console.error('[AgentHandlers] Tab content container not found');
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
                    <p style="font-size: 11px; color: #999; text-align: center; padding: 20px;">Loading plugin...</p>
                </div>
            </div>
        `;

        tabContent.appendChild(tabPane);
        console.log('[AgentHandlers] ✓ Tab content created');

        // 3. Activate the newly created tab
        tabButton.click();

        // 4. Load plugin content
        this.loadPluginContent(pluginId);

        if (typeof Notification !== 'undefined') {
            Notification.success(`${config.fullName} loaded`);
        }

        console.log('[AgentHandlers] ✓ Plugin loaded');
    },

    /**
     * Remove plugin tab
     */
    removePluginTab(pluginId) {
        console.log('[AgentHandlers] Remove plugin:', pluginId);

        // Remove tab button
        const tabButton = document.querySelector(`.settings-tab[data-tab="plugin-${pluginId}"]`);
        if (tabButton) {
            // If the tab is currently active, switch to the Param tab
            if (tabButton.classList.contains('active')) {
                const paramTab = document.querySelector('.settings-tab[data-tab="param"]');
                if (paramTab) {
                    paramTab.click();
                }
            }
            tabButton.remove();
        }

        // Remove tab content
        const tabPane = document.querySelector(`.tab-pane[data-tab="plugin-${pluginId}"]`);
        if (tabPane) {
            tabPane.remove();
        }

        if (typeof Notification !== 'undefined') {
            Notification.info('Plugin removed');
        }

        console.log('[AgentHandlers] ✓ Plugin removed');
    },

    /**
     * Load plugin content
     */
    loadPluginContent(pluginId) {
        const container = document.getElementById(`plugin-content-${pluginId}`);
        if (!container) {
            console.error('[AgentHandlers] Plugin content container not found:', `plugin-content-${pluginId}`);
            return;
        }

        // Load different content based on plugin ID
        switch (pluginId) {
            case 'mindmap':
                this.loadMindmapPlugin(container);
                break;
            case 'code':
                this.loadCodePlugin(container);
                break;
            case 'calendar':
                container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">Calendar plugin is under development...</p>';
                break;
            case 'chart':
                container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">Chart plugin is under development...</p>';
                break;
            default:
                container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">Unknown plugin</p>';
        }
    },

    /**
     * Load mindmap plugin
     */
    loadMindmapPlugin(container) {
        container.innerHTML = `
            <div style="padding: 12px;">
                <p style="font-size: 11px; color: var(--text-secondary, #666); margin-bottom: 12px;">
                    The mind map plugin is active. Send a code block with the mindmap format in chat, and it will be automatically converted into a visual mind map.
                </p>
                <div style="margin-bottom: 12px;">
                    <p style="font-size: 10px; color: var(--text-secondary, #999); margin-bottom: 6px;">Syntax:</p>
                    <pre style="background: var(--bg-secondary, #f5f5f5); padding: 8px; border-radius: 4px; font-size: 10px; overflow-x: auto; margin-bottom: 8px;">\`\`\`mindmap
- Root node
  - Child node 1
    - Grandchild node 1.1
  - Child node 2
\`\`\`</pre>
                </div>
                <button class="preset-use-btn" style="width: 100%; margin-bottom: 6px;" onclick="agentHandlers.showMindmapExample()">Fill example code</button>
                <button class="preset-use-btn" style="width: 100%;" onclick="agentHandlers.askAIForMindmap()">Ask AI to generate a mind map</button>
            </div>
        `;
    },

    /**
     * Show mindmap example - directly fill in usable code
     */
    showMindmapExample() {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = '```mindmap\n- Learning to Program\n  - Fundamentals\n    - Data types\n    - Control flow\n    - Functions\n  - Projects\n    - Web development\n    - Mobile apps\n    - Data analysis\n  - Advanced topics\n    - Algorithms & data structures\n    - Design patterns\n    - System architecture\n```';
            if (typeof Notification !== 'undefined') {
                Notification.info('Example code filled. Send it to see the mind map result.');
            }
            // Focus the input
            input.focus();
        }
    },

    /**
     * Ask AI to generate a mindmap
     */
    askAIForMindmap() {
        const input = document.getElementById('chatInput');
        if (input) {
            input.value = 'Please generate a mind map about the "History of AI".\n\nPlease strictly follow this format:\n```mindmap\n- Root node\n  - Child node (indent with 2 spaces)\n    - Grandchild node (indent with 4 spaces)\n```\n\nNotes:\n1. The code block language must be mindmap\n2. Each node must start with "- "\n3. Child nodes must be indented with 2 spaces\n4. Do not use the Tab key';
            if (typeof Notification !== 'undefined') {
                Notification.info('AI request filled. Send it and wait for the AI to reply in the correct format.');
            }
            // Focus the input
            input.focus();
        }
    },

    /**
     * Load code execution plugin
     */
    loadCodePlugin(container) {
        if (window.CodePlugin) {
            window.CodePlugin.render(container);
        } else {
            container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">Code execution plugin is not loaded. Please refresh the page.</p>';
            console.error('[AgentHandlers] CodePlugin not found');
        }
    },

    /**
     * Initialize streaming chat listeners
     */
    initChatStreamListeners() {
        // Create internal handler object to avoid mutating window.electronAPI
        this._streamHandlers = {
            onData: (data) => {
                if (data.requestId === agentState.getRequestId()) {
                    agentState.appendStreamingContent(data.content);
                    this.updateStreamingMessage(agentState.getStreamingContent());
                }
            },
            onEnd: (data) => {
                if (data.requestId === agentState.getRequestId()) {
                    this.finalizeStreamingMessage();
                    agentState.clearRequestId();
                }
            },
            onError: (data) => {
                if (data.requestId === agentState.getRequestId()) {
                    this.showStreamError(data.error);
                    agentState.clearRequestId();
                }
            }
        };

        // If legacy electronAPI listeners exist
        if (window.electronAPI && window.electronAPI.onChatStreamData) {
            // Clear old listeners
            if (window.electronAPI.removeChatStreamListeners) {
                window.electronAPI.removeChatStreamListeners();
            }

            // Listen for streaming data
            window.electronAPI.onChatStreamData(this._streamHandlers.onData);

            // Listen for stream end
            window.electronAPI.onChatStreamEnd(this._streamHandlers.onEnd);

            // Listen for errors
            window.electronAPI.onChatStreamError(this._streamHandlers.onError);
        }
    },

    /**
     * Load model options
     */
    async loadModelOptions() {
        const modelSelector = document.getElementById('modelSelector');
        if (!modelSelector) return;

        try {
            const response = await fetch(this.resolve('/api/agent/llm-configs'));
            const result = await response.json();

            if (result.success && result.data) {
                const models = result.data.filter(m => m.is_active !== false);

                if (models.length > 0) {
                    // Keep the first option if there is no default model
                    let defaultModel = models.find(m => m.is_default) || models[0];

                    modelSelector.innerHTML = models.map(model => `
                        <option value="${model.config_id}" ${model.is_default ? 'selected' : ''}>
                            ${model.name}${model.provider ? ` (${model.provider})` : ''}
                        </option>
                    `).join('');

                    // Set the currently selected model
                    if (defaultModel) {
                        agentState.setModel(defaultModel.config_id);
                        // Load the full configuration for the default model
                        await this.loadAndApplyModelConfig(defaultModel.config_id);
                    }
                } else {
                    modelSelector.innerHTML = '<option value="">No available models</option>';
                }
            }
        } catch (error) {
            console.error('Failed to load model list:', error);
            // Keep default options
        }
    },

    /**
     * Load role options
     */
    async loadRoleOptions() {
        const roleSelector = document.getElementById('roleSelector');
        if (!roleSelector) return;

        try {
            const response = await fetch(this.resolve('/api/agent/role-configs'));
            const result = await response.json();

            if (result.success && result.data) {
                const roles = result.data.filter(r => r.is_active !== false);

                if (roles.length > 0) {
                    // Keep the first option if there is no default role
                    let defaultRole = roles.find(r => r.is_default) || roles[0];

                    roleSelector.innerHTML = roles.map(role => `
                        <option value="${role.role_id}" ${role.is_default ? 'selected' : ''}>
                            ${role.name}${role.category ? ` - ${role.category}` : ''}
                        </option>
                    `).join('');

                    // Set the currently selected role
                    if (defaultRole) {
                        agentState.setRole(defaultRole.role_id);
                        // Load the full configuration for the default role
                        await this.loadAndApplyRoleConfig(defaultRole.role_id);
                    }
                } else {
                    roleSelector.innerHTML = '<option value="">No available roles</option>';
                }
            }
        } catch (error) {
            console.error('Failed to load role list:', error);
            // Keep default options
        }
    },

    /**
     * Load agent list
     */
    async loadAgentList() {
        const agentList = document.getElementById('agentList');
        if (!agentList) return;

        try {
            const response = await agentApi.getAgents();
            const agents = response.data || [];
            agentState.setAgents(agents);

            if (agents.length === 0) {
                agentList.innerHTML = '<div class="empty-state">No agents</div>';
                // Management buttons still need to be added
                this.appendManagementButtons(agentList);
                return;
            }

            // Keep all management buttons
            const managementItems = agentList.querySelectorAll('.agent-management');

            agentList.innerHTML = agents.map(agent => `
                <div class="agent-item" data-id="${agent.id}">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                    </svg>
                    <span>${agent.name}</span>
                </div>
            `).join('');

            // Re-add all management buttons
            managementItems.forEach(item => {
                agentList.appendChild(item.cloneNode(true));
            });

            // Re-bind management button events
            this.bindManagementButtonEvents();
        } catch (error) {
            console.error('Failed to load agent list:', error);
            agentList.innerHTML = '<div class="empty-state error">Load failed</div>';
            // Add management buttons even when loading fails
            this.appendManagementButtons(agentList);
        }
    },

    /**
     * Append management buttons
     */
    appendManagementButtons(agentList) {
        const managementButtonsHtml = `
            <div class="agent-item agent-management" data-page="model-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>LLM Setting</span>
            </div>
            <div class="agent-item agent-management" data-page="role-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                <span>Role Setting</span>
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
     * Bind management button events
     */
    bindManagementButtonEvents() {
        // Remove existing listeners to avoid duplicate bindings
        document.querySelectorAll('.agent-management[data-page]').forEach(btn => {
            // Clone and replace the node to remove old event listeners
            const newBtn = btn.cloneNode(true);
            btn.parentNode.replaceChild(newBtn, btn);

            // Add new event listener
            newBtn.addEventListener('click', () => {
                const page = newBtn.dataset.page;
                console.log('Management button clicked:', page);
                this.navigateToManagementPage(page);
            });
        });
    },

    /**
     * Load chat list
     */
    async loadChatList() {
        const chatList = document.getElementById('chatList');
        if (!chatList) return;

        try {
            // Call real API to load conversation list from the database
            const response = await agentApi.getConversations(50);
            const conversations = response.data || [];

            const treeChildren = chatList.querySelector('.tree-children');
            if (!treeChildren) return;

            if (conversations.length === 0) {
                treeChildren.innerHTML = '<div class="empty-state">No conversations</div>';
                return;
            }

            // Render conversation list
            treeChildren.innerHTML = conversations.map((conv) => `
                <div class="tree-item" data-conversation-id="${conv.conversation_id}">
                    <span class="item-text">${this.escapeHtml(conv.title || 'New chat')}</span>
                </div>
            `).join('');

            // Bind click events
            this.bindChatListItemEvents();
        } catch (error) {
            console.error('Failed to load chat list:', error);
            const treeChildren = chatList.querySelector('.tree-children');
            if (treeChildren) {
                treeChildren.innerHTML = '<div class="empty-state error">Load failed</div>';
            }
        }
    },

    /**
     * Bind chat list item click events
     */
    bindChatListItemEvents() {
        document.querySelectorAll('#chatList .tree-item[data-conversation-id]').forEach(item => {
            // Remove old event listener
            const newItem = item.cloneNode(true);
            item.parentNode.replaceChild(newItem, item);

            // Add new event listener
            newItem.addEventListener('click', () => {
                const conversationId = newItem.dataset.conversationId;
                // Remove active class from other items
                document.querySelectorAll('#chatList .tree-item').forEach(i => i.classList.remove('active'));
                // Add active class to current item
                newItem.classList.add('active');
                // Load conversation
                this.loadConversation(conversationId);
            });
        });
    },

    /**
     * Handle new chat
     */
    handleNewChat() {
        // Close management page
        this.closeManagementPage();

        // Clear current conversation
        const messagesContainer = document.getElementById('chatMessages');
        if (!messagesContainer) return;

        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.style.display = 'block';
        } else {
            // If there is no welcome message, clear all messages
            messagesContainer.innerHTML = '';
        }

        // Generate a new conversation_id
        const newConversationId = agentState.generateConversationId();
        agentState.setConversationId(newConversationId);

        // Clear chat history
        agentState.clearChatHistory();

        // Clear all selections
        document.querySelectorAll('#chatList .tree-item').forEach(item => {
            item.classList.remove('active');
        });

        console.log('[AgentHandlers] New chat, ID:', newConversationId);
    },

    /**
     * Load conversation
     */
    async loadConversation(conversationId) {
        try {
            console.log('[AgentHandlers] Load conversation:', conversationId);

            // Fetch conversation messages
            const response = await agentApi.getConversationMessages(conversationId);
            const messages = response.data || [];

            // Clear current chat area
            const messagesContainer = document.getElementById('chatMessages');
            if (!messagesContainer) return;

            messagesContainer.innerHTML = '';

            // Set current conversation_id
            agentState.setConversationId(conversationId);

            // Clear chat history
            agentState.clearChatHistory();

            // Render message history
            for (const msg of messages) {
                if (msg.role === 'system') continue;

                const messageHtml = this.createMessageElement(
                    msg.role,
                    msg.content,
                    this.formatTime(msg.create_time)
                );
                messagesContainer.insertAdjacentHTML('beforeend', messageHtml);

                // Add to state
                agentState.addMessage(msg.role, msg.content);
            }

            // Scroll to bottom
            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            console.log('[AgentHandlers] Conversation loaded. Message count:', messages.length);
        } catch (error) {
            console.error('Failed to load conversation:', error);
            if (typeof Notification !== 'undefined') {
                Notification.error('Failed to load conversation');
            }
        }
    },

    /**
     * Create message element
     */
    createMessageElement(role, content, time) {
        const isUser = role === 'user';
        const currentAgent = !isUser ? agentState.getCurrentAgent() : null;
        const assistantName = !isUser ? (currentAgent?.name || 'AI Assistant') : null;
        const avatarSvg = isUser ?
            '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>' :
            '<svg viewBox="0 -960 960 960" width="20" height="20" fill="currentColor"><path d="M160-360q-50 0-85-35t-35-85q0-50 35-85t85-35v-80q0-33 23.5-56.5T240-760h120q0-50 35-85t85-35q50 0 85 35t35 85h120q33 0 56.5 23.5T800-680v80q50 0 85 35t35 85q0 50-35 85t-85 35v160q0 33-23.5 56.5T720-120H240q-33 0-56.5-23.5T160-200v-160Zm242.5-97.5Q420-475 420-500t-17.5-42.5Q385-560 360-560t-42.5 17.5Q300-525 300-500t17.5 42.5Q335-440 360-440t42.5-17.5Zm240 0Q660-475 660-500t-17.5-42.5Q625-560 600-560t-42.5 17.5Q540-525 540-500t17.5 42.5Q575-440 600-440t42.5-17.5ZM320-280h320v-80H320v80Zm-80 80h480v-480H240v480Zm240-240Z"/></svg>';

        return `
            <div class="message-item ${isUser ? 'user-message' : 'assistant-message'}">
                <div class="message-header">
                    <div class="message-avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}">
                        ${avatarSvg}
                    </div>
                    <span class="message-sender">${isUser ? 'You' : this.escapeHtml(assistantName)}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-body">${this.renderMarkdown(content)}</div>
            </div>
        `;
    },

    /**
     * Format time
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
     * Handle settings
     */
    handleSettings() {
        // Use the new Agent Settings Dialog
        if (typeof AgentSettingsDialog !== 'undefined') {
            // Pass null to create a new Agent
            // To edit an existing Agent, pass an agent object
            AgentSettingsDialog.show(null);
        } else {
            console.error('AgentSettingsDialog not loaded');
            if (typeof Notification !== 'undefined') {
                Notification.error('Settings dialog is not loaded');
            }
        }
    },

    /**
     * Send message
     */
    async sendMessage() {
        // Close management page
        this.closeManagementPage();

        const input = document.getElementById('chatInput');
        const messagesContainer = document.getElementById('chatMessages');
        const sendBtn = document.getElementById('sendMessageBtn');

        if (!input || !messagesContainer) return;

        const message = input.value.trim();
        if (!message) return;

        // Do not allow sending new messages while streaming is in progress
        if (agentState.getRequestId()) {
            return;
        }

        // Get current agent
        const currentAgent = agentState.getCurrentAgent();
        if (!currentAgent) {
            console.error('[AgentHandlers] No agent selected');
            if (typeof Notification !== 'undefined') {
                Notification.error('Please select an agent first');
            }
            return;
        }

        const agentId = currentAgent.id;
        console.log('[AgentHandlers] Sending message with agent:', currentAgent.name, 'ID:', agentId);

        // Disable send button
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.classList.add('sending');
        }

        // Hide welcome message
        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        if (welcomeMsg) {
            welcomeMsg.style.display = 'none';
        }

        // Get current time
        const timeStr = new Date().toLocaleString('zh-CN', {
            year: 'numeric',
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit',
            second: '2-digit'
        });

        // Add user message
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

        // Save user message to history
        agentState.addMessage('user', message);

        // Get or generate conversation_id
        let conversationId = agentState.getConversationId();
        if (!conversationId) {
            conversationId = agentState.generateConversationId();
            agentState.setConversationId(conversationId);
            console.log('[AgentHandlers] Generated new conversation ID:', conversationId);
        }

        // Add AI reply container (with thinking animation)
        const assistantMessageHtml = `
            <div class="message-item assistant-message streaming">
                <div class="message-header">
                    <div class="message-avatar assistant-avatar">
                        <svg viewBox="0 -960 960 960" width="20" height="20" fill="currentColor"><path d="M160-360q-50 0-85-35t-35-85q0-50 35-85t85-35v-80q0-33 23.5-56.5T240-760h120q0-50 35-85t85-35q50 0 85 35t35 85h120q33 0 56.5 23.5T800-680v80q50 0 85 35t35 85q0 50-35 85t-85 35v160q0 33-23.5 56.5T720-120H240q-33 0-56.5-23.5T160-200v-160Zm242.5-97.5Q420-475 420-500t-17.5-42.5Q385-560 360-560t-42.5 17.5Q300-525 300-500t17.5 42.5Q335-440 360-440t42.5-17.5Zm240 0Q660-475 660-500t-17.5-42.5Q625-560 600-560t-42.5 17.5Q540-525 540-500t17.5 42.5Q575-440 600-440t42.5-17.5ZM320-280h320v-80H320v80Zm-80 80h480v-480H240v480Zm240-240Z"/></svg>
                    </div>
                    <span class="message-sender">${this.escapeHtml(currentAgent.name)}</span>
                    <span class="message-time">${timeStr}</span>
                </div>
                <div class="message-body">
                    <div class="thinking-indicator">
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                        <div class="thinking-dot"></div>
                        <span class="thinking-text">Thinking...</span>
                    </div>
                </div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', assistantMessageHtml);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Generate request ID (for streaming response tracking)
        const requestId = 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        agentState.setRequestId(requestId);
        agentState.clearStreamingContent();

        // Helper to re-enable the send button
        const enableSendBtn = () => {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.classList.remove('sending');
            }
        };

        // Start streaming request - use agent-specific endpoint
        try {
            // Prepare callbacks
            const callbacks = {
                onData: (content) => {
                    agentState.appendStreamingContent(content);
                    this.updateStreamingMessage(agentState.getStreamingContent());
                },
                onEnd: () => {
                    this.finalizeStreamingMessage();
                    agentState.clearRequestId();
                    enableSendBtn();
                    // After streaming completes, reload chat list to show the new conversation
                    this.loadChatList();
                },
                onError: (error) => {
                    this.showStreamError(error);
                    agentState.clearRequestId();
                    enableSendBtn();
                }
            };

            // Call agent-specific streaming API
            console.log('[AgentHandlers] Calling agent-specific endpoint:', `/api/agent/${agentId}/chat/stream`);
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

            // Setup timeout handling
            setTimeout(() => {
                if (agentState.getRequestId() === requestId) {
                    this.showStreamError('Request timed out. Please try again.');
                    agentState.clearRequestId();
                    enableSendBtn();
                }
            }, 120000); // 2 minute timeout

        } catch (error) {
            console.error('Failed to send message:', error);
            this.showStreamError(error.message);
            agentState.clearRequestId();
            enableSendBtn();
        }

    },

    /**
     * Update streaming message display
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
     * Finalize streaming message
     */
    finalizeStreamingMessage() {
        const streamingMsg = document.querySelector('.message-item.streaming');
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                const content = agentState.getStreamingContent();
                streamingBody.innerHTML = this.renderMarkdown(content);
                // Highlight code blocks
                this.highlightCodeBlocks(streamingBody);

                // Render mindmap (if available)
                if (window.MindmapPlugin) {
                    window.MindmapPlugin.renderInMessage(streamingBody);
                }
            }
        }
        // Save to history
        agentState.addMessage('assistant', agentState.getStreamingContent());
        agentState.clearStreamingContent();
    },

    /**
     * Show streaming error
     */
    showStreamError(error) {
        const streamingMsg = document.querySelector('.message-item.streaming');
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            streamingMsg.classList.add('error-message');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                streamingBody.innerHTML = `<div class="error-content"><svg viewBox="0 0 24 24" width="16" height="16" fill="#d93025"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg><span>
Request failed: ${this.escapeHtml(error)}</span></div>`;
            }
        }
    },

    /**
     * Simulate streaming response (for development/testing)
     */
    simulateStreamResponse(enableSendBtn) {
        const mockResponse = `Sure, here is the answer to your question.

## Example code

Here is a simple Python example:

\`\`\`python
def hello_world():
    print("Hello, World!")
    return True

# Call the function
if __name__ == "__main__":
    hello_world()
\`\`\`

### Key features:

1. **Concise** - Clear structure
2. **Easy to understand** - Well-commented
3. **Extensible** - Easy to modify later

> Tip: This is just a demo. Adjust as needed for real use.

If you have more questions, feel free to ask!`;

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
     * Markdown rendering
     */
    renderMarkdown(text, isStreaming = false) {
        if (!text) return '';

        // Preserve code blocks to avoid being processed by other rules
        const codeBlocks = [];

        // Full code block handling
        text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const language = lang || 'plaintext';
            const rawCode = code.trim();
            const escapedCode = this.escapeHtml(rawCode);
            const escapedRawCode = this.escapeHtml(rawCode).replace(/"/g, '&quot;');
            const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
            codeBlocks.push(`<div class="code-block"><div class="code-header"><span class="code-lang">${language}</span><button class="copy-code-btn" onclick="agentHandlers.copyCode(this)"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg><span>Copy</span></button></div><pre><code class="language-${language}" data-raw-code="${escapedRawCode}">${escapedCode}</code></pre></div>`);
            return placeholder;
        });

        // Handle incomplete code blocks (during streaming)
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

        // Inline code
        text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // Bold
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italic
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Headings
        text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');

        // Unordered lists
        text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
        text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

        // Links
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

        // Blockquotes
        text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

        // Newline handling
        text = text.replace(/\n\n/g, '</p><p>');
        text = text.replace(/\n/g, '<br>');

        // Wrap in paragraph
        if (!text.startsWith('<') && !text.startsWith('__CODEBLOCK_')) {
            text = '<p>' + text + '</p>';
        }

        // Restore code blocks
        codeBlocks.forEach((block, index) => {
            text = text.replace(`__CODEBLOCK_${index}__`, block);
        });

        return text;
    },

    /**
     * Code highlighting
     */
    highlightCodeBlocks(container) {
        container.querySelectorAll('pre code').forEach(block => {
            if (block.dataset.highlighted) return;
            block.dataset.highlighted = 'true';

            let code = block.textContent;
            block.dataset.rawCode = code;

            let highlighted = this.escapeHtml(code);

            // Keyword highlighting
            const keywords = [
                'function', 'const', 'let', 'var', 'if', 'else', 'for', 'while', 'return',
                'class', 'import', 'export', 'from', 'async', 'await', 'try', 'catch',
                'def', 'print', 'self', 'None', 'True', 'False', 'in', 'not', 'and', 'or'
            ];

            const keywordPattern = new RegExp(`\\b(${keywords.join('|')})\\b`, 'g');
            highlighted = highlighted.replace(keywordPattern, '<span class="hljs-keyword">$1</span>');

            // Number highlighting
            highlighted = highlighted.replace(/\\b(\\d+\\.?\\d*)\\b/g, '<span class="hljs-number">$1</span>');

            // String highlighting
            highlighted = highlighted.replace(/(&quot;[^&]*&quot;|&#39;[^&]*&#39;)/g, '<span class="hljs-string">$1</span>');

            // Comment highlighting
            highlighted = highlighted.replace(/(\/\/.*$|#.*$)/gm, '<span class="hljs-comment">$1</span>');

            block.innerHTML = highlighted;
        });
    },

    /**
     * Copy code
     */
    copyCode(btn) {
        const codeBlock = btn.closest('.code-block');
        const codeElement = codeBlock.querySelector('code');
        const code = codeElement.dataset.rawCode || codeElement.textContent;

        const showCopiedState = () => {
            const originalText = btn.querySelector('span').textContent;
            btn.querySelector('span').textContent = 'Copied!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.querySelector('span').textContent = originalText;
                btn.classList.remove('copied');
            }, 2000);
        };

        const showFailedState = () => {
            const originalText = btn.querySelector('span').textContent;
            btn.querySelector('span').textContent = 'Copy failed';
            setTimeout(() => {
                btn.querySelector('span').textContent = originalText;
            }, 2000);
        };

        const fallbackCopy = () => {
            const textarea = document.createElement('textarea');
            textarea.value = code;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'fixed';
            textarea.style.top = '-1000px';
            textarea.style.left = '-1000px';
            document.body.appendChild(textarea);
            textarea.select();
            textarea.setSelectionRange(0, textarea.value.length);

            let ok = false;
            try {
                ok = document.execCommand('copy');
            } catch (e) {
                ok = false;
            }

            document.body.removeChild(textarea);
            return ok;
        };

        (async () => {
            try {
                if (window.electronAPI && typeof window.electronAPI.writeClipboardText === 'function') {
                    const res = await window.electronAPI.writeClipboardText(code);
                    if (res && res.success) {
                        showCopiedState();
                        return;
                    }
                }

                if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                    await navigator.clipboard.writeText(code);
                    showCopiedState();
                    return;
                }

                const ok = fallbackCopy();
                if (ok) {
                    showCopiedState();
                    return;
                }

                throw new Error('All copy methods failed');
            } catch (err) {
                console.warn('[AgentHandlers] Failed to copy code to clipboard:', err);
                showFailedState();
            }
        })();
    },

    /**
     * HTML escaping
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Clear chat messages
     */
    clearChatMessages() {
        const messagesContainer = document.getElementById('chatMessages');
        if (messagesContainer) {
            const welcomeMsg = messagesContainer.querySelector('.welcome-message');
            if (welcomeMsg) {
                welcomeMsg.style.display = 'block';
                // Remove other messages
                messagesContainer.querySelectorAll('.message-item').forEach(item => item.remove());
            }
        }
    },

    /**
     * Navigate to management page
     */
    async navigateToManagementPage(page) {
        try {
            console.log('Navigating to management page:', page);

            // Destroy previously opened management page first
            if (this.currentManagementPage) {
                if (this.currentManagementPage.destroy) {
                    this.currentManagementPage.destroy();
                }
                this.currentManagementPage = null;
            }

            // Import management pages dynamically
            const module = await import('./index.js');
            const { ModelManagementPage, RoleManagementPage } = module.default;

            console.log('Imported pages:', { ModelManagementPage, RoleManagementPage });

            if (page === 'model-management' && ModelManagementPage) {
                this.currentManagementPage = ModelManagementPage;
                await ModelManagementPage.init();
                console.log('Model management page initialized');
            } else if (page === 'role-management' && RoleManagementPage) {
                this.currentManagementPage = RoleManagementPage;
                await RoleManagementPage.init();
                console.log('Role management page initialized');
            } else {
                console.error('Page not found:', page);
            }
        } catch (error) {
            console.error('Error navigating to management page:', error);
        }
    },

    /**
     * Load and apply model config
     */
    async loadAndApplyModelConfig(configId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/llm-configs/${configId}`));
            const result = await response.json();

            if (result.success && result.data) {
                const modelConfig = result.data;
                // Save to state
                agentState.currentModelConfig = modelConfig;
                // Update right-side panel Param tab
                this.populateParamTab(modelConfig);
                console.log('[AgentHandlers] Model config loaded:', modelConfig.name);
            }
        } catch (error) {
            console.error('Failed to load model config:', error);
        }
    },

    /**
     * Load and apply role config
     */
    async loadAndApplyRoleConfig(roleId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/role-configs/${roleId}`));
            const result = await response.json();

            if (result.success && result.data) {
                const roleConfig = result.data;
                // Save to state
                agentState.currentRoleConfig = roleConfig;
                // Update right-side panel Prompt tab
                this.populatePromptTab(roleConfig);
                console.log('[AgentHandlers] Role config loaded:', roleConfig.name);
            }
        } catch (error) {
            console.error('Failed to load role config:', error);
        }
    },

    /**
     * Populate Param tab - display parameters for the selected model
     */
    populateParamTab(modelConfig) {
        if (!modelConfig) return;

        // Find inputs in the param tab
        const paramTab = document.querySelector('[data-tab="param"]');
        if (!paramTab) return;

        const inputs = paramTab.querySelectorAll('.param-input');
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

        // Stream mode
        const streamCheckbox = paramTab.querySelector('input[type="checkbox"]');
        if (streamCheckbox && modelConfig.stream !== undefined) {
            streamCheckbox.checked = modelConfig.stream;
        }
    },

    /**
     * Populate Prompt tab - display the selected role prompt
     */
    populatePromptTab(roleConfig) {
        if (!roleConfig) return;

        const promptTextarea = document.getElementById('systemPrompt');
        if (promptTextarea && roleConfig.system_prompt) {
            promptTextarea.value = roleConfig.system_prompt;
        }
    },

    /**
     * Initialize parameter input listeners - persist changes to backend
     */
    initParamInputListeners() {
        const paramTab = document.querySelector('[data-tab="param"]');
        if (!paramTab) return;

        // Use debouncing to avoid frequent saves
        let saveTimeout;
        const debouncedSave = () => {
            clearTimeout(saveTimeout);
            saveTimeout = setTimeout(() => {
                this.saveModelParams();
            }, 1000); // Save after 1 second
        };

        // Listen to all parameter inputs
        const inputs = paramTab.querySelectorAll('.param-input');
        inputs.forEach(input => {
            input.addEventListener('change', debouncedSave);
        });

        // Listen to checkboxes
        const checkboxes = paramTab.querySelectorAll('input[type="checkbox"]');
        checkboxes.forEach(checkbox => {
            checkbox.addEventListener('change', debouncedSave);
        });
    },

    /**
     * Save model params to backend
     */
    async saveModelParams() {
        const currentConfig = agentState.currentModelConfig;
        if (!currentConfig || !currentConfig.config_id) {
            console.warn('[AgentHandlers] No current model config; cannot save');
            return;
        }

        const paramTab = document.querySelector('[data-tab="param"]');
        if (!paramTab) return;

        // Collect params
        const params = {};
        const inputs = paramTab.querySelectorAll('.param-input');
        inputs.forEach(input => {
            const label = input.closest('.param-label');
            if (!label) return;

            const labelText = label.querySelector('span')?.textContent.trim();
            const value = parseFloat(input.value);

            if (labelText === 'Temperature') {
                params.temperature = value;
            } else if (labelText === 'Max Tokens') {
                params.max_tokens = parseInt(input.value);
            } else if (labelText === 'Top P') {
                params.top_p = value;
            } else if (labelText === 'Frequency Penalty') {
                params.frequency_penalty = value;
            } else if (labelText === 'Presence Penalty') {
                params.presence_penalty = value;
            }
        });

        // Stream mode
        const streamCheckbox = paramTab.querySelector('input[type="checkbox"]');
        if (streamCheckbox) {
            params.stream = streamCheckbox.checked;
        }

        try {
            const response = await fetch(this.resolve(`/api/agent/llm-configs/${currentConfig.config_id}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            const result = await response.json();

            if (result.success) {
                // Update config in state
                Object.assign(agentState.currentModelConfig, params);
                console.log('[AgentHandlers] Model params saved');
            } else {
                console.error('[AgentHandlers] Failed to save model params:', result.error);
            }
        } catch (error) {
            console.error('[AgentHandlers] Failed to save model params:', error);
        }
    },

    /**
     * Save role prompt to backend
     */
    async saveRolePrompt(prompt) {
        const currentConfig = agentState.currentRoleConfig;
        if (!currentConfig || !currentConfig.role_id) {
            if (typeof Notification !== 'undefined') {
                Notification.error('No role config selected');
            }
            return;
        }

        try {
            const response = await fetch(this.resolve(`/api/agent/role-configs/${currentConfig.role_id}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ system_prompt: prompt })
            });
            const result = await response.json();

            if (result.success) {
                // Update config in state
                agentState.currentRoleConfig.system_prompt = prompt;
                if (typeof Notification !== 'undefined') {
                    Notification.success('System prompt saved');
                }
                console.log('[AgentHandlers] Role prompt saved');
            } else {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Save failed: ' + (result.error || 'Unknown error'));
                }
            }
        } catch (error) {
            console.error('[AgentHandlers] Failed to save role prompt:', error);
            if (typeof Notification !== 'undefined') {
                Notification.error('Save failed: ' + error.message);
            }
        }
    },

    /**
     * Close management page and show main chat
     */
    closeManagementPage() {
        if (this.currentManagementPage) {
            if (this.currentManagementPage.destroy) {
                this.currentManagementPage.destroy();
            }
            this.currentManagementPage = null;

            // Reload model and role options (they may have been modified in management pages)
            this.loadModelOptions();
            this.loadRoleOptions();
        }
    },

    /**
     * Destroy
     */
    destroy() {
        // Clean up event listeners
        agentState.reset();
    }
};

// Export as a global object to allow calling from HTML
if (typeof window !== 'undefined') {
    window.agentHandlers = agentHandlers;
}

export default agentHandlers;
