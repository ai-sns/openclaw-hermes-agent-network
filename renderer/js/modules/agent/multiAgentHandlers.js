/**
 * Multi-Agent Handlers - multi-agent event handling extensions
 * Extend agentHandlers to support a multi-agent system
 */

import agentState from './agentState.js';
import agentApi from './agentApi.js';
import AgentSidebar from './AgentSidebar.js';
import AgentPage from './AgentPage.js';
import Toast from '../../utils/toast.js';

const multiAgentHandlers = {
    matchesToolbarTitle(el, titles) {
        if (!el) return false;
        const t = String(el.getAttribute('title') || '').trim();
        return (titles || []).some(x => String(x).trim() === t);
    },

    async _deleteRendererPlugin(pluginId, agentId) {
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

            // Unload if currently loaded for this agent
            try {
                this.unloadRendererPluginForAgent(id, agentId);
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
    matchesToolbarAction(el, actions) {
        if (!el || !el.dataset) return false;
        const a = String(el.dataset.action || '').trim();
        if (!a) return false;
        return (actions || []).some(x => String(x).trim() === a);
    },
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
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
            console.warn('[MultiAgentHandlers] Failed to fetch renderer plugins:', e);
            return [];
        }
    },

    async _importRendererPluginZip(file) {
        const base = await this._getApiBaseUrl();
        if (!base) {
            if (typeof Notification !== 'undefined') {
                Notification.error('API base URL not available');
            }
            return false;
        }

        try {
            const form = new FormData();
            form.append('file', file, file.name || 'plugin.zip');
            const resp = await fetch(`${base}/api/tools/plugins/import?used_in_sns=false`, {
                method: 'POST',
                body: form
            });
            if (!resp.ok) {
                const text = await resp.text();
                throw new Error(text || `HTTP ${resp.status}`);
            }
            if (typeof Notification !== 'undefined') {
                Notification.success('Plugin imported');
            }
            return true;
        } catch (e) {
            if (typeof Notification !== 'undefined') {
                Notification.error(`Import failed: ${e && e.message ? e.message : String(e)}`);
            }
            return false;
        }
    },

    _getLoadedRendererPluginsMap(agentId) {
        if (!this._loadedRendererPluginsByAgent || typeof this._loadedRendererPluginsByAgent !== 'object') {
            this._loadedRendererPluginsByAgent = new Map();
        }
        const key = String(agentId || '');
        if (!this._loadedRendererPluginsByAgent.has(key)) {
            this._loadedRendererPluginsByAgent.set(key, new Map());
        }
        return this._loadedRendererPluginsByAgent.get(key);
    },

    async loadRendererPluginForAgent(plugin, agentId) {
        const pluginKey = plugin && (plugin.plugin_id || plugin.id) ? String(plugin.plugin_id || plugin.id) : '';
        const agentKey = String(agentId || '');
        if (!pluginKey || !agentKey) return;

        const settingsTabs = document.getElementById(`settingsTabs-${agentKey}`);
        const tabContent = document.getElementById(`settingsTabContent-${agentKey}`);
        if (!settingsTabs || !tabContent) {
            console.warn('[MultiAgentHandlers] Settings panel not found for renderer plugin');
            return;
        }

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
        tabButton.dataset.agentId = agentKey;
        tabButton.innerHTML = `
            <span>${name}</span>
            <span class="tab-close-btn" title="Close">×</span>
        `;
        const closeBtn = tabButton.querySelector('.tab-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.unloadRendererPluginForAgent(pluginKey, agentKey);
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
                <div class="plugin-content" id="plugin-content-ext-${pluginKey}-${agentKey}"></div>
            </div>
        `;
        tabContent.appendChild(pane);

        tabButton.click();

        const container = pane.querySelector(`#plugin-content-ext-${CSS.escape(pluginKey)}-${CSS.escape(agentKey)}`);
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

        this._getLoadedRendererPluginsMap(agentKey).set(pluginKey, { tabId, pluginInstance });
    },

    unloadRendererPluginForAgent(pluginKey, agentId) {
        const key = String(pluginKey || '');
        const agentKey = String(agentId || '');
        if (!key || !agentKey) return;

        const loaded = this._getLoadedRendererPluginsMap(agentKey);
        const item = loaded.get(key);
        if (!item) return;

        try {
            if (item.pluginInstance && typeof item.pluginInstance.dispose === 'function') {
                item.pluginInstance.dispose();
            }
        } catch (e) {
            console.warn('[MultiAgentHandlers] Plugin dispose failed:', e);
        }

        const settingsTabs = document.getElementById(`settingsTabs-${agentKey}`);
        const tabContent = document.getElementById(`settingsTabContent-${agentKey}`);
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
    /**
     * Initialize multi-agent system
     */
    async init() {
        console.log('[MultiAgentHandlers] Starting multi-agent system initialization...');

        // 1. Load agent list from API
        const response = await fetch(this.resolve('/api/agent'));
        const result = await response.json();
        const agents = result.success ? (result.data || []) : [];

        if (agents.length === 0) {
            console.warn('[MultiAgentHandlers] No available agents');
            return;
        }

        // 2. Save to state
        agentState.setAgents(agents);
        console.log('[MultiAgentHandlers] Loaded agents:', agents.length);

        // 3. Initialize AgentSidebar
        await AgentSidebar.init();

        // 4. Initialize AgentPage
        await AgentPage.init(agents);

        // 5. Set current agent to the first one
        if (agents.length > 0) {
            agentState.setCurrentAgent(agents[0].id);
            console.log('[MultiAgentHandlers] Current agent:', agents[0].id);
        }

        // 6. Bind global events
        this.bindGlobalEvents();

        // 7. Bind UI events for all agents
        this.bindAllAgentEvents();

        // 8. Load model and role options for all agents
        for (const agent of agents) {
            await this.loadModelOptionsForAgent(agent.id);
            await this.loadRoleOptionsForAgent(agent.id);
        }

        // 9. Load chat list for current agent
        if (agents.length > 0) {
            this.loadChatListForAgent(agents[0].id);
        }

        // 10. Initialize stream listeners
        this.initChatStreamListeners();

        console.log('[MultiAgentHandlers] Multi-agent system initialization completed');
    },

    forceActivateSettingsTabForAgent(agentId, targetTab) {
        if (!agentId || !targetTab) return;

        const tabs = document.querySelectorAll(`.settings-tab[data-agent-id="${agentId}"]`);
        const panes = document.querySelectorAll(`#settingsTabContent-${agentId} .tab-pane`);

        tabs.forEach(t => t.classList.remove('active'));
        panes.forEach(p => p.classList.remove('active'));

        const tab = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="${targetTab}"]`);
        const pane = document.querySelector(`#settingsTabContent-${agentId} .tab-pane[data-tab="${targetTab}"]`);
        if (tab) tab.classList.add('active');
        if (pane) pane.classList.add('active');
    },

    async downloadAndOpenAttachment(conversationId, attachmentId, filename) {
        try {
            if (window.electronAPI && typeof window.electronAPI.downloadAndOpen === 'function') {
                const path = `/api/chat/conversations/${encodeURIComponent(conversationId)}/attachments/${encodeURIComponent(attachmentId)}`;
                const url = this.resolve(path);
                const result = await window.electronAPI.downloadAndOpen(url, filename || 'file');
                if (result) {
                    console.error('[MultiAgentHandlers] downloadAndOpen failed:', result);
                    if (typeof Notification !== 'undefined' && Notification.error) {
                        Notification.error(`Failed to open attachment: ${result}`);
                    }
                }
            }
        } catch (e) {
            console.error('[MultiAgentHandlers] downloadAndOpen error:', e);
            if (typeof Notification !== 'undefined' && Notification.error) {
                Notification.error(`Failed to open attachment: ${e && e.message ? e.message : String(e)}`);
            }
        }
    },

    normalizeA2ARpcUrl(url) {
        const u = String(url || '').trim();
        if (!u) return '';

        const normalized = u.endsWith('/') ? u.slice(0, -1) : u;
        if (normalized.endsWith('/rpc')) {
            return normalized;
        }

        return normalized + '/rpc';
    },

    isRemoteAgentType(agentType) {
        const t = String(agentType || 'local').toLowerCase();
        return t === 'remote' || t === 'remote agent' || t === 'remote_agent';
    },

    isRemoteAgentById(agentId) {
        const page = document.getElementById(`page-agent-${agentId}`);
        if (page && page.dataset && page.dataset.agentType) {
            return String(page.dataset.agentType).toLowerCase() === 'remote';
        }

        try {
            const agents = (agentState && typeof agentState.getAgents === 'function') ? agentState.getAgents() : [];
            const a = (agents || []).find(x => String(x.id) === String(agentId));
            return this.isRemoteAgentType(a && a.agent_type);
        } catch (e) {
            return false;
        }
    },

    notifyRemoteAgentFeatureUnavailable(message) {
        const msg = message || 'This feature is not available for Remote agents.';
        if (typeof Notification !== 'undefined' && Notification.error) {
            Notification.error(msg);
        } else {
            alert(msg);
        }
    },

    extractTextFromA2AResponse(rpcResponse) {
        if (!rpcResponse) {
            throw new Error('A2A response is empty');
        }

        if (rpcResponse.error) {
            const msg = rpcResponse.error.message || JSON.stringify(rpcResponse.error);
            throw new Error(msg);
        }

        const result = rpcResponse.result;
        if (!result) {
            throw new Error('A2A response is missing result');
        }

        const message = result?.status?.message;

        if (typeof message === 'string') {
            return message;
        }

        const parts = message?.parts;
        if (Array.isArray(parts) && parts.length > 0) {
            const texts = parts
                .filter(p => p && p.type === 'text' && typeof p.text === 'string')
                .map(p => p.text);
            if (texts.length > 0) {
                return texts.join('');
            }
        }

        const history = result?.history;
        if (Array.isArray(history) && history.length > 0) {
            const last = history[history.length - 1];
            const lastParts = last?.parts;
            if (Array.isArray(lastParts) && lastParts.length > 0) {
                const texts = lastParts
                    .filter(p => p && p.type === 'text' && typeof p.text === 'string')
                    .map(p => p.text);
                if (texts.length > 0) {
                    return texts.join('');
                }
            }
        }

        return JSON.stringify(result);
    },

    applyRemoteUiDisableForAgent(agentId, isRemote) {
        const page = document.getElementById(`page-agent-${agentId}`);
        if (page) {
            page.dataset.agentType = isRemote ? 'remote' : 'local';
        }

        const modelSelector = document.getElementById(`modelSelector-${agentId}`);
        if (modelSelector) {
            modelSelector.disabled = !!isRemote;
        }

        const roleSelector = document.getElementById(`roleSelector-${agentId}`);
        if (roleSelector) {
            roleSelector.disabled = !!isRemote;
        }

        const configToolsBtn = document.querySelector(`.config-tools-btn[data-agent-id="${agentId}"]`);
        if (configToolsBtn) {
            configToolsBtn.disabled = false;
            if (isRemote) {
                configToolsBtn.style.opacity = '0.6';
                configToolsBtn.style.cursor = 'not-allowed';
                configToolsBtn.setAttribute('aria-disabled', 'true');
            } else {
                configToolsBtn.style.opacity = '';
                configToolsBtn.style.cursor = '';
                configToolsBtn.removeAttribute('aria-disabled');
            }
        }

        document.querySelectorAll(`button.toolbar-icon-btn[data-agent-id="${agentId}"]`).forEach(btn => {
            const shouldRemainEnabled = this.matchesToolbarAction(btn, ['kb-config', 'attachment'])
                || this.matchesToolbarTitle(btn, ['配置知识库', 'Configure knowledge base', '附件', 'Attachment', 'Attachments']);
            if (shouldRemainEnabled) {
                btn.disabled = false;
                if (isRemote) {
                    btn.style.opacity = '0.6';
                    btn.style.cursor = 'not-allowed';
                    btn.setAttribute('aria-disabled', 'true');
                } else {
                    btn.style.opacity = '';
                    btn.style.cursor = '';
                    btn.removeAttribute('aria-disabled');
                }
            }
        });

        document.querySelectorAll(`.settings-tab[data-agent-id="${agentId}"]`).forEach(tab => {
            const t = (tab.dataset.tab || '').toLowerCase();
            if (t === 'param' || t === 'prompt' || t === 'file') {
                tab.disabled = !!isRemote;
            }
        });

        const tabContent = document.getElementById(`settingsTabContent-${agentId}`);
        if (tabContent) {
            tabContent.querySelectorAll(`.tab-pane`).forEach(pane => {
                const t = (pane.dataset.tab || '').toLowerCase();
                if (t === 'param' || t === 'prompt' || t === 'file') {
                    if (isRemote) {
                        pane.style.opacity = '0.6';

                        pane.querySelectorAll('input, textarea, select').forEach(el => {
                            el.disabled = true;
                        });

                        pane.querySelectorAll('button').forEach(el => {
                            if (el.classList && el.classList.contains('file-upload-btn')) {
                                el.disabled = false;
                            } else {
                                el.disabled = true;
                            }
                        });
                    } else {
                        pane.style.opacity = '';

                        pane.querySelectorAll('input, textarea, select, button').forEach(el => {
                            el.disabled = false;
                        });
                    }
                }
            });
        }
    },

    createAttachmentBlock(conversationId, attachments) {
        const items = Array.isArray(attachments) ? attachments : [];
        if (items.length === 0) return '';

        const chips = items.map(a => {
            const id = (a && a.id) ? String(a.id) : '';
            const name = (a && a.name) ? a.name : 'file';
            return `<span class="attachment-chip" data-conversation-id="${this.escapeHtml(String(conversationId || ''))}" data-attachment-id="${this.escapeHtml(id)}">${this.escapeHtml(name)}</span>`;
        }).join('');

        return `<div class="message-attachments">${chips}</div>`;
    },

    /**
     * Bind global events
     */
    bindGlobalEvents() {
        console.log('[MultiAgentHandlers] Binding global events...');

        // Listen for agent switch events
        window.addEventListener('agent-switched', (e) => {
            const { agentId } = e.detail;
            console.log('[MultiAgentHandlers] Agent switched:', agentId);

            // Update state
            agentState.setCurrentAgent(agentId);

            // Load chat list for that agent
            this.loadChatListForAgent(agentId);

            // Load model and role options for that agent
            this.loadModelOptionsForAgent(agentId);
            this.loadRoleOptionsForAgent(agentId);
        });

        // Listen for new chat events
        window.addEventListener('agent-new-chat', (e) => {
            const { agentId } = e.detail;
            console.log('[MultiAgentHandlers] New Chat:', agentId);

            // Switch to that agent
            agentState.setCurrentAgent(agentId);

            // Handle new chat
            this.handleNewChatForAgent(agentId);
        });

        window.addEventListener('agent-updated', (e) => {
            const detail = e && e.detail ? e.detail : {};
            const agentId = detail.agentId;
            if (!agentId) return;

            const name = detail.name || detail.agent?.name;
            const description = detail.description || detail.agent?.description;

            if (name) {
                const agents = agentState.getAgents ? agentState.getAgents() : (agentState.agents || []);
                const idx = agents.findIndex(a => a && a.id === agentId);
                if (idx >= 0) {
                    agents[idx] = { ...agents[idx], ...detail.agent, name, description };
                } else {
                    agents.push({ ...(detail.agent || {}), id: agentId, name, description });
                }

                if (agentState.setAgents) {
                    agentState.setAgents(agents);
                } else {
                    agentState.agents = agents;
                }

                this.applyAgentNameToChatUI(agentId, name, description);
            }
        });
    },

    applyAgentNameToChatUI(agentId, name, description) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (messagesContainer) {
            messagesContainer.querySelectorAll('.message-item.assistant-message .message-sender').forEach(el => {
                el.textContent = name;
            });

            const welcomeTitle = messagesContainer.querySelector('.welcome-message .welcome-title');
            if (welcomeTitle) {
                welcomeTitle.textContent = name;
            }

            const welcomeSubtitle = messagesContainer.querySelector('.welcome-message .welcome-subtitle');
            if (welcomeSubtitle && typeof description === 'string' && description.trim()) {
                welcomeSubtitle.textContent = description;
            }
        }

        const singleMessagesContainer = document.getElementById('chatMessages');
        if (singleMessagesContainer && singleMessagesContainer.classList.contains('agent-chat-messages')) {
            singleMessagesContainer.querySelectorAll('.message-item.assistant-message .message-sender').forEach(el => {
                el.textContent = name;
            });
            const welcomeTitle = singleMessagesContainer.querySelector('.welcome-message .welcome-title');
            if (welcomeTitle) {
                welcomeTitle.textContent = name;
            }
        }
    },

    /**
     * Bind UI events for all agents
     */
    bindAllAgentEvents() {
        console.log('[MultiAgentHandlers] Binding UI events for all agents...');

        if (!this._agentTabReloadMenuInitialized) {
            this._agentTabReloadMenuInitialized = true;

            const existingMenu = document.getElementById('agentTabReloadContextMenu');
            const menu = existingMenu || (() => {
                const el = document.createElement('div');
                el.id = 'agentTabReloadContextMenu';
                el.className = 'status-context-menu compact';
                el.innerHTML = `
                    <button type="button" class="context-menu-item" data-action="reload">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <polyline points="23 4 23 10 17 10"></polyline>
                            <polyline points="1 20 1 14 7 14"></polyline>
                            <path d="M3.51 9a9 9 0 0 1 14.13-3.36L23 10"></path>
                            <path d="M20.49 15a9 9 0 0 1-14.13 3.36L1 14"></path>
                        </svg>
                        <span>Refresh</span>
                    </button>
                    <button type="button" class="context-menu-item" data-action="open-browser">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                            <polyline points="15 3 21 3 21 9"/>
                            <line x1="10" y1="14" x2="21" y2="3"/>
                        </svg>
                        <span>Open in Browser</span>
                    </button>
                    <button type="button" class="context-menu-item" data-action="copy-url">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                        <span>Copy URL</span>
                    </button>
                `;
                document.body.appendChild(el);
                return el;
            })();

            let currentAgentId = null;
            let currentTabKey = null;
            let removeObserver = null;

            const hideMenu = () => {
                menu.style.display = 'none';
                menu.dataset.agentId = '';
                menu.dataset.tab = '';
                currentAgentId = null;
                currentTabKey = null;
                if (removeObserver) {
                    removeObserver.disconnect();
                    removeObserver = null;
                }
            };

            const getCurrentIframeUrl = () => {
                if (!isCurrentTargetAlive()) return '';
                const pane = document.querySelector(`#settingsTabContent-${currentAgentId} .tab-pane[data-tab="${currentTabKey}"]`);
                const iframe = pane ? pane.querySelector('iframe') : null;
                const src = iframe && iframe.src ? String(iframe.src) : '';
                if (!src) return '';
                try {
                    const u = new URL(src);
                    u.searchParams.delete('_ts');
                    return u.toString();
                } catch (e) {
                    return src;
                }
            };

            const copyTextToClipboard = async (text) => {
                if (!text) return false;

                try {
                    if (window.electronAPI && typeof window.electronAPI.writeClipboardText === 'function') {
                        const res = await window.electronAPI.writeClipboardText(text);
                        if (res && res.success) return true;
                    }
                } catch (e) {
                }

                try {
                    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                        await navigator.clipboard.writeText(text);
                        return true;
                    }
                } catch (e) {
                }

                try {
                    const textarea = document.createElement('textarea');
                    textarea.value = text;
                    textarea.setAttribute('readonly', '');
                    textarea.style.position = 'fixed';
                    textarea.style.left = '-9999px';
                    textarea.style.top = '-9999px';
                    document.body.appendChild(textarea);
                    textarea.focus();
                    textarea.select();
                    textarea.setSelectionRange(0, textarea.value.length);
                    const ok = document.execCommand('copy');
                    textarea.remove();
                    return !!ok;
                } catch (e) {
                    return false;
                }
            };

            const isCurrentTargetAlive = () => {
                if (!currentAgentId || !currentTabKey) return false;
                const tabBtn = document.querySelector(`#settingsTabs-${currentAgentId} .settings-tab[data-tab="${currentTabKey}"]`);
                const pane = document.querySelector(`#settingsTabContent-${currentAgentId} .tab-pane[data-tab="${currentTabKey}"]`);
                return !!(tabBtn && pane);
            };

            const reloadCurrentIframe = () => {
                if (!isCurrentTargetAlive()) {
                    hideMenu();
                    return;
                }

                const pane = document.querySelector(`#settingsTabContent-${currentAgentId} .tab-pane[data-tab="${currentTabKey}"]`);
                const iframe = pane ? pane.querySelector('iframe') : null;
                if (iframe && iframe.src) {
                    try {
                        if (iframe.contentWindow && iframe.contentWindow.location && typeof iframe.contentWindow.location.reload === 'function') {
                            iframe.contentWindow.location.reload();
                            return;
                        }
                    } catch (e) {
                        // ignore and fallback to src reload
                    }

                    try {
                        const u = new URL(iframe.src);
                        u.searchParams.set('_ts', String(Date.now()));
                        iframe.src = u.toString();
                    } catch (e) {
                        const sep = iframe.src.includes('?') ? '&' : '?';
                        iframe.src = `${iframe.src}${sep}_ts=${Date.now()}`;
                    }
                }
            };

            const showMenuAt = (x, y) => {
                menu.style.display = 'block';
                const menuWidth = menu.offsetWidth || 140;
                const menuHeight = menu.offsetHeight || 38;
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;
                let left = x;
                let top = y;
                if (left + menuWidth > viewportWidth) left = viewportWidth - menuWidth - 10;
                if (top + menuHeight > viewportHeight) top = viewportHeight - menuHeight - 10;
                menu.style.left = left + 'px';
                menu.style.top = top + 'px';
            };

            document.addEventListener('click', (e) => {
                if (!menu.contains(e.target)) hideMenu();
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') hideMenu();
            });

            window.addEventListener('blur', hideMenu);
            window.addEventListener('resize', hideMenu);
            window.addEventListener('scroll', hideMenu, true);

            menu.addEventListener('click', (e) => {
                const item = e.target.closest('.context-menu-item');
                if (!item) return;
                const action = item.dataset.action;
                if (action === 'reload') {
                    reloadCurrentIframe();
                } else if (action === 'open-browser') {
                    const url = getCurrentIframeUrl();
                    if (url) {
                        if (window.electronAPI && window.electronAPI.openUrl) {
                            window.electronAPI.openUrl(url);
                        } else {
                            window.open(url, '_blank');
                        }
                    }
                } else if (action === 'copy-url') {
                    const url = getCurrentIframeUrl();
                    if (url) {
                        copyTextToClipboard(url).then((ok) => {
                            if (ok) console.log('URL copied to clipboard');
                        });
                    }
                }
                hideMenu();
            });

            document.addEventListener('contextmenu', (e) => {
                const tabBtn = e.target.closest('.settings-tab[data-agent-id]');
                if (!tabBtn) return;
                if (e.target.closest('.tab-close-btn')) return;

                const agentId = tabBtn.dataset.agentId;
                const tabKey = tabBtn.dataset.tab;
                if (tabKey !== 'plugin-avatar3d') return;

                e.preventDefault();
                e.stopPropagation();

                currentAgentId = agentId;
                currentTabKey = tabKey;
                menu.dataset.agentId = agentId;
                menu.dataset.tab = tabKey;

                showMenuAt(e.clientX, e.clientY);

                if (removeObserver) {
                    removeObserver.disconnect();
                    removeObserver = null;
                }
                removeObserver = new MutationObserver(() => {
                    if (!isCurrentTargetAlive()) hideMenu();
                });
                removeObserver.observe(document.body, { childList: true, subtree: true });
            });

            document.addEventListener('click', (e) => {
                if (e.target.closest(`#settingsTabs-${currentAgentId || ''} .tab-close-btn`)) {
                    hideMenu();
                }
            });
        }

        // Drag to resize agent right-side settings panel (similar to SNS right-side status panel)
        let isResizingPanel = false;
        let resizingAgentId = null;
        let startX = 0;
        let startWidth = 0;
        let activeResizer = null;
        let activePanel = null;
        let disabledIframes = null;

        const onPanelMouseMove = (e) => {
            if (!isResizingPanel || !activePanel || !activeResizer) return;

            // Drag left to increase width; drag right to decrease width
            const deltaX = startX - e.clientX;
            const minPanelWidth = 200;
            const minChatWidth = 0;
            const layout = activeResizer.closest('.agent-page-layout');
            const layoutWidth = layout ? layout.getBoundingClientRect().width : window.innerWidth;
            const resizerWidth = activeResizer.getBoundingClientRect().width || 8;
            const maxPanelWidth = Math.max(minPanelWidth, Math.floor(layoutWidth - resizerWidth - minChatWidth));

            let newWidth = Math.max(minPanelWidth, Math.min(maxPanelWidth, startWidth + deltaX));
            if (newWidth > maxPanelWidth - 1) newWidth = maxPanelWidth;
            activePanel.style.width = `${newWidth}px`;
        };

        const onPanelMouseUp = () => {
            if (!isResizingPanel) return;

            isResizingPanel = false;
            resizingAgentId = null;
            if (activeResizer) activeResizer.classList.remove('resizing');
            document.body.style.cursor = '';
            document.body.style.userSelect = '';

            if (disabledIframes) {
                disabledIframes.forEach(iframe => {
                    iframe.style.pointerEvents = '';
                });
            }

            activeResizer = null;
            activePanel = null;
            disabledIframes = null;

            document.removeEventListener('mousemove', onPanelMouseMove);
            document.removeEventListener('mouseup', onPanelMouseUp);
        };

        // 1. Send message button - use event delegation
        document.addEventListener('click', (e) => {
            const sendBtn = e.target.closest('.send-btn[data-agent-id]');
            if (sendBtn) {
                e.preventDefault();
                const agentId = parseInt(sendBtn.dataset.agentId);
                this.sendMessageForAgent(agentId);
            }
        });

        // 2. Press Enter in input to send
        document.addEventListener('keydown', (e) => {
            const chatInput = e.target.closest('.agent-chat-input[data-agent-id]');
            if (chatInput && e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const agentId = parseInt(chatInput.dataset.agentId);
                this.sendMessageForAgent(agentId);
            }
        });

        // 3. Model selector
        document.addEventListener('change', async (e) => {
            const modelSelector = e.target.closest('.model-selector[data-agent-id]');
            if (modelSelector) {
                const agentId = parseInt(modelSelector.dataset.agentId);
                const configId = modelSelector.value;

                // Check whether "Please Select" was chosen
                if (!configId) {
                    console.log('[MultiAgentHandlers] Model selector: no valid config selected');
                    return;
                }

                agentState.setCurrentAgent(agentId);
                agentState.setModel(configId);

                // Disable selector to prevent repeated clicks
                modelSelector.disabled = true;

                try {
                    await this.loadAndApplyModelConfig(configId, agentId);
                    console.log(`[MultiAgentHandlers] Agent ${agentId} model config updated`);
                } catch (error) {
                    console.error(`[MultiAgentHandlers] Agent ${agentId} failed to update model config:`, error);
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Failed to update model config: ' + error.message);
                    }
                } finally {
                    // Re-enable selector
                    modelSelector.disabled = false;
                }
            }
        });

        // 4. Role selector
        document.addEventListener('change', async (e) => {
            const roleSelector = e.target.closest('.role-selector[data-agent-id]');
            if (roleSelector) {
                const agentId = parseInt(roleSelector.dataset.agentId);
                const roleId = roleSelector.value;

                // Check whether "Please Select" was chosen
                if (!roleId) {
                    console.log('[MultiAgentHandlers] Role selector: no valid config selected');
                    return;
                }

                agentState.setCurrentAgent(agentId);
                agentState.setRole(roleId);

                // Disable selector to prevent repeated clicks
                roleSelector.disabled = true;

                try {
                    await this.loadAndApplyRoleConfig(roleId, agentId);
                    console.log(`[MultiAgentHandlers] Agent ${agentId} role config updated`);
                } catch (error) {
                    console.error(`[MultiAgentHandlers] Agent ${agentId} failed to update role config:`, error);
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Failed to update role config: ' + error.message);
                    }
                } finally {
                    // Re-enable selector
                    roleSelector.disabled = false;
                }
            }
        });

        // 5. Settings panel tab switching
        document.addEventListener('click', (e) => {
            const tab = e.target.closest('.settings-tab[data-agent-id]');
            if (tab) {
                const agentId = tab.dataset.agentId;
                const targetTab = tab.dataset.tab;

                // Switch tabs for the same agent
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

        // 6. Settings panel collapse button
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

        // 6.1 Drag to resize settings panel width (event delegation, multi-agent)
        document.addEventListener('mousedown', (e) => {
            const resizer = e.target.closest('.agent-panel-resizer[data-agent-id]');
            if (!resizer) return;

            const agentId = resizer.dataset.agentId;
            const collapseBtn = document.getElementById(`agentPanelCollapseBtn-${agentId}`);
            if (collapseBtn && (e.target === collapseBtn || collapseBtn.contains(e.target))) return;

            const panel = document.getElementById(`agentSettingsPanel-${agentId}`);
            if (!panel || panel.classList.contains('collapsed')) return;

            isResizingPanel = true;
            resizingAgentId = agentId;
            activeResizer = resizer;
            activePanel = panel;
            startX = e.clientX;
            startWidth = panel.offsetWidth;
            resizer.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            // Disable iframe pointer events to avoid lag while dragging
            disabledIframes = Array.from(document.querySelectorAll('iframe'));
            disabledIframes.forEach(iframe => {
                iframe.style.pointerEvents = 'none';
            });

            document.addEventListener('mousemove', onPanelMouseMove);
            document.addEventListener('mouseup', onPanelMouseUp);
            e.preventDefault();
        });

        // 7. Prompt save button
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

        // 8. Plugin selection button (toolbar "Add" button)
        document.addEventListener('click', (e) => {
            const addBtn = e.target.closest('.toolbar-icon-btn[data-agent-id]');
            if (addBtn && (this.matchesToolbarAction(addBtn, ['add-plugin']) || this.matchesToolbarTitle(addBtn, ['添加', 'Add']))) {
                const agentId = parseInt(addBtn.dataset.agentId);
                console.log('[MultiAgentHandlers] Clicked Add button (plugin selection) for agent:', agentId);
                this.handleAddPlugin(agentId);
            }
        });

        document.addEventListener('click', (e) => {
            const avatarBtn = e.target.closest('.toolbar-icon-btn[title="3D Avatar"][data-agent-id]');
            if (avatarBtn) {
                const agentId = parseInt(avatarBtn.dataset.agentId);

                const panel = document.getElementById(`agentSettingsPanel-${agentId}`);
                const resizer = document.getElementById(`agentPanelResizer-${agentId}`);
                if (panel) {
                    panel.classList.remove('collapsed');
                }
                if (resizer) {
                    resizer.classList.remove('collapsed');
                }

                this.loadPluginForAgent('avatar3d', agentId);
            }
        });

        document.addEventListener('click', (e) => {
            const attachBtn = e.target.closest('.toolbar-icon-btn[data-agent-id]');
            if (attachBtn && (this.matchesToolbarAction(attachBtn, ['attachment']) || this.matchesToolbarTitle(attachBtn, ['附件', 'Attachment', 'Attachments']))) {
                const agentId = parseInt(attachBtn.dataset.agentId);
                if (this.isRemoteAgentById(agentId)) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.notifyRemoteAgentFeatureUnavailable('Attachments are not available for Remote agents.');
                    return;
                }
                this.openAttachmentPicker(agentId);
            }
        });

        document.addEventListener('click', (e) => {
            const uploadBtn = e.target.closest('.file-upload-btn[data-agent-id]');
            if (uploadBtn) {
                const agentId = parseInt(uploadBtn.dataset.agentId);
                if (this.isRemoteAgentById(agentId)) {
                    e.preventDefault();
                    e.stopPropagation();
                    this.notifyRemoteAgentFeatureUnavailable('Attachments are not available for Remote agents.');
                    return;
                }
                this.openAttachmentPicker(agentId);
            }
        });

        document.addEventListener('click', (e) => {
            const fileItem = e.target.closest('.file-item[data-file-path][data-agent-id]');
            if (fileItem && !e.target.closest('.file-remove-btn')) {
                const filePath = fileItem.dataset.filePath;
                if (filePath) {
                    this.openFilePath(filePath);
                }
            }

            const chip = e.target.closest('.attachment-chip');
            if (chip) {
                const attachmentId = (chip.dataset && chip.dataset.attachmentId) ? chip.dataset.attachmentId : '';
                const conversationId = (chip.dataset && chip.dataset.conversationId) ? chip.dataset.conversationId : '';
                const filePath = (chip.dataset && chip.dataset.filePath) ? chip.dataset.filePath : '';
                const filename = (chip.textContent || '').trim();

                console.log('[MultiAgentHandlers] Clicked attachment chip bubble:', {
                    outerHTML: chip.outerHTML,
                    dataset: { ...chip.dataset },
                    conversationId,
                    attachmentId,
                    filePath,
                    filename,
                    hasElectronAPI: !!window.electronAPI,
                    hasDownloadAndOpen: !!(window.electronAPI && window.electronAPI.downloadAndOpen)
                });

                // Backwards compatible: if there is a local path, open directly
                if (filePath) {
                    this.openFilePath(filePath);
                    return;
                }

                // New logic: download and open from backend by attachment_id
                if (!conversationId || !attachmentId) {
                    console.warn('[MultiAgentHandlers] Attachment missing conversationId or attachmentId; cannot download/open');
                    if (typeof Notification !== 'undefined' && Notification.error) {
                        Notification.error('Attachment info is incomplete. Please reload the conversation or resend, then click again.');
                    }
                    return;
                }

                if (!window.electronAPI || typeof window.electronAPI.downloadAndOpen !== 'function') {
                    console.error('[MultiAgentHandlers] electronAPI.downloadAndOpen is unavailable (restart Electron or check preload)');
                    if (typeof Notification !== 'undefined' && Notification.error) {
                        Notification.error('Failed to open attachment: Electron capability is not ready. Please restart the app.');
                    }
                    return;
                }

                this.downloadAndOpenAttachment(conversationId, attachmentId, filename);
            }
        }, true);

        console.log('[MultiAgentHandlers] All events bound');
    },

    openAttachmentPicker(agentId) {
        if (this.isRemoteAgentById(agentId)) {
            this.notifyRemoteAgentFeatureUnavailable('Attachments are not available for Remote agents.');
            return;
        }
        const input = document.createElement('input');
        input.type = 'file';
        input.multiple = true;
        input.accept = 'image/*,text/*,.pdf,.doc,.docx,.ppt,.pptx,.xls,.xlsx,.md,.markdown';

        input.addEventListener('change', (e) => {
            const files = Array.from(e.target.files || []);
            if (files.length > 0) {
                this.addAttachments(agentId, files);
            }
        });

        input.click();
    },

    addAttachments(agentId, files) {
        const state = agentState.ensureAgentState(agentId);
        state.attachments = state.attachments || [];

        const existingKeys = new Set(state.attachments.map(a => a.key));
        for (const f of files) {
            const key = `${f.name}:${f.size}:${f.lastModified}`;
            if (existingKeys.has(key)) continue;
            state.attachments.push({
                id: 'att_' + Date.now() + '_' + Math.random().toString(36).slice(2, 8),
                key,
                file: f,
                path: f.path || '',
                name: f.name,
                size: f.size,
                type: f.type
            });
        }

        this.renderAttachments(agentId);
        this.showFileTab(agentId);

        if (typeof Notification !== 'undefined' && Notification.success) {
            Notification.success(`Added ${files.length} attachment(s)`);
        }
    },

    removeAttachment(agentId, attachmentId) {
        const state = agentState.ensureAgentState(agentId);
        state.attachments = (state.attachments || []).filter(a => a.id !== attachmentId);
        this.renderAttachments(agentId);
    },

    updateLastUserMessageAttachmentIds(agentId, conversationId, savedAttachments) {
        const list = Array.isArray(savedAttachments) ? savedAttachments : [];
        if (list.length === 0) return;

        const container = document.getElementById(`chatMessages-${agentId}`);
        if (!container) return;

        const userMessages = container.querySelectorAll('.message-item.user-message');
        const last = userMessages.length > 0 ? userMessages[userMessages.length - 1] : null;
        if (!last) return;

        const chips = last.querySelectorAll('.attachment-chip');
        if (!chips || chips.length === 0) return;

        const byName = new Map();
        for (const a of list) {
            const name = String((a && a.name) || '');
            const id = String((a && a.id) || '');
            if (name && id && !byName.has(name)) {
                byName.set(name, id);
            }
        }

        chips.forEach(chip => {
            const label = (chip.textContent || '').trim();
            const id = byName.get(label);
            if (id) {
                chip.dataset.attachmentId = id;
                chip.dataset.conversationId = String(conversationId || '');
            }
        });
    },

    clearAttachments(agentId) {
        const state = agentState.ensureAgentState(agentId);
        state.attachments = [];
        this.renderAttachments(agentId);
    },

    setHistoryAttachments(agentId, attachments) {
        const state = agentState.ensureAgentState(agentId);
        const list = Array.isArray(attachments) ? attachments : [];
        const seen = new Set();
        state.historyAttachments = list.filter(a => {
            const p = String((a && (a.saved_path || a.file_path || a.path)) || '');
            if (!p) return false;
            if (seen.has(p)) return false;
            seen.add(p);
            return true;
        }).map(a => {
            const p = (a && (a.saved_path || a.file_path || a.path)) || '';
            return {
                name: (a && a.name) || 'file',
                size: (a && a.size) || 0,
                type: (a && a.type) || (a && a.content_type) || '',
                path: String(p)
            };
        });
        this.renderAttachments(agentId);
    },

    showFileTab(agentId) {
        const panel = document.getElementById(`agentSettingsPanel-${agentId}`);
        const resizer = document.getElementById(`agentPanelResizer-${agentId}`);
        if (panel) {
            panel.classList.remove('collapsed');
        }
        if (resizer) {
            resizer.classList.remove('collapsed');
        }

        const fileTab = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="file"]`);
        if (fileTab) {
            fileTab.click();
        }
    },

    openFilePath(filePath) {
        try {
            if (window.electronAPI && typeof window.electronAPI.openPath === 'function') {
                window.electronAPI.openPath(filePath);
                return;
            }
        } catch (e) {
        }
    },

    renderAttachments(agentId) {
        const fileList = document.getElementById(`chatFileList-${agentId}`);
        if (!fileList) return;

        const state = agentState.ensureAgentState(agentId);
        const attachments = state.attachments || [];

        if (attachments.length === 0) {
            fileList.innerHTML = `
                <div class="empty-state">
                    <svg viewBox="0 0 24 24" width="48" height="48" fill="#ccc">
                        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                    </svg>
                    <p>No attachments</p>
                </div>
            `;
            return;
        }

        fileList.innerHTML = attachments.map(att => {
            const filePath = String(att.path || '');
            const isPending = true;
            return `
                <div class="file-item" data-attachment-id="${this.escapeHtml(att.id || '')}" data-agent-id="${agentId}" data-file-path="${this.escapeHtml(filePath)}">
                    <div class="file-icon">
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                        </svg>
                    </div>
                    <div class="file-info">
                        <div class="file-name">${this.escapeHtml(att.name)}</div>
                        <div class="file-size">${this.formatFileSize(att.size)}</div>
                    </div>
                    ${isPending ? `
                        <button class="file-remove-btn" title="Remove file" data-attachment-id="${this.escapeHtml(att.id || '')}" data-agent-id="${agentId}">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                        </button>
                    ` : ''}
                </div>
            `;
        }).join('');

        fileList.querySelectorAll('.file-remove-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const aId = btn.dataset.attachmentId;
                const aAgentId = parseInt(btn.dataset.agentId);
                if (aId) {
                    this.removeAttachment(aAgentId, aId);
                }
            });
        });
    },

    formatFileSize(bytes) {
        if (!bytes) return '0 B';
        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(k));
        return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
    },

    /**
     * Load chat list for a specific agent
     */
    async loadChatListForAgent(agentId, query = '') {
        console.log(`[MultiAgentHandlers] Start loading chat list for Agent ${agentId}`);

        const chatList = document.getElementById(`chatList-${agentId}`);
        if (!chatList) {
            console.warn(`[MultiAgentHandlers] Cannot find element chatList-${agentId}. DOM may not be ready yet.`);
            return;
        }

        try {
            // Try to fetch conversations from API with agent_id param
            // If backend supports per-agent filtering, it returns filtered results
            // Otherwise, we filter on the client
            const url = this.resolve(`/api/chat/conversations?limit=50&agent_id=${encodeURIComponent(agentId)}`);
            console.log(`[MultiAgentHandlers] Calling API: ${url}`);
            const response = await fetch(url);
            const result = await response.json();
            let conversations = result.data || [];
            console.log(`[MultiAgentHandlers] API returned ${conversations.length} conversations`);

            // Client-side filtering: only show conversations for current agent
            // If conversation has agent_id field, filter; otherwise show all (backwards compatible)
            if (conversations.length > 0 && conversations[0].agent_id !== undefined) {
                conversations = conversations.filter(conv => conv.agent_id == agentId);
                console.log(`[MultiAgentHandlers] After filtering: ${conversations.length} conversations`);
            }

            const q = String(query || '').trim().toLowerCase();
            if (q) {
                conversations = conversations.filter(conv => {
                    const title = String(conv && conv.title ? conv.title : '').toLowerCase();
                    const first = String(conv && conv.first_message ? conv.first_message : '').toLowerCase();
                    const tag = String(conv && conv.label ? conv.label : '').toLowerCase();
                    return title.includes(q) || first.includes(q) || tag.includes(q);
                });
            }

            const treeChildren = chatList.querySelector('.tree-children');
            if (!treeChildren) {
                console.warn(`[MultiAgentHandlers] Cannot find .tree-children inside chatList-${agentId}`);
                return;
            }

            if (conversations.length === 0) {
                treeChildren.innerHTML = '<div class="empty-state">No conversations</div>';
                return;
            }

            treeChildren.innerHTML = conversations.map((conv) => `
                <div class="tree-item" data-conversation-id="${conv.conversation_id}" data-agent-id="${agentId}">
                    <span class="tree-icon">💬</span>
                    <span class="item-text">${this.escapeHtml(conv.title || 'New conversation')}${conv.stick_time ? ' <span style="color:#ff9800;">📌</span>' : ''}</span>
                </div>
            `).join('');

            // Bind click events
            treeChildren.querySelectorAll('.tree-item').forEach(item => {
                item.addEventListener('click', () => {
                    const conversationId = item.dataset.conversationId;
                    const itemAgentId = parseInt(item.dataset.agentId);

                    // Remove active class from other items
                    treeChildren.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
                    item.classList.add('active');

                    // Load conversation
                    this.loadConversationForAgent(conversationId, itemAgentId);
                });

                item.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    const conversationId = item.dataset.conversationId;
                    const itemAgentId = parseInt(item.dataset.agentId);
                    const conv = (conversations || []).find(c => String(c.conversation_id) === String(conversationId)) || null;
                    this.showChatContextMenu(e, itemAgentId, conversationId, conv);
                });
            });

            console.log(`[MultiAgentHandlers] Agent ${agentId} chat list loaded. Total: ${conversations.length}`);
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to load chat list:`, error);
        }
    },

    async loadTagListForAgent(agentId, query = '') {
        const container = document.getElementById(`tagListContainer-${agentId}`);
        if (!container) return;

        container.innerHTML = '<div class="chat-tree"><div class="tree-children"><div class="empty-state">Loading...</div></div></div>';

        try {
            const url = this.resolve(`/api/chat/conversations?limit=200&agent_id=${encodeURIComponent(agentId)}`);
            const response = await fetch(url);
            const result = await response.json();
            let conversations = (result && result.data) ? result.data : [];

            if (conversations.length > 0 && conversations[0].agent_id !== undefined) {
                conversations = conversations.filter(conv => conv.agent_id == agentId);
            }

            const tagged = (conversations || []).filter(c => c && c.label && String(c.label).trim());
            if (tagged.length === 0) {
                container.innerHTML = '<div class="chat-tree"><div class="tree-children"><div class="empty-state">No tags</div></div></div>';
                return;
            }

            const q = String(query || '').trim().toLowerCase();

            const groups = {};
            for (const conv of tagged) {
                const tag = String(conv.label || '').trim();
                if (!tag) continue;
                if (!groups[tag]) groups[tag] = [];
                groups[tag].push(conv);
            }

            if (q) {
                for (const tag of Object.keys(groups)) {
                    const items = (groups[tag] || []).filter(conv => {
                        const t = String(tag).toLowerCase();
                        const title = String(conv && conv.title ? conv.title : '').toLowerCase();
                        return t.includes(q) || title.includes(q);
                    });
                    if (items.length === 0) {
                        delete groups[tag];
                    } else {
                        groups[tag] = items;
                    }
                }
            }

            const groupTags = Object.keys(groups);
            if (groupTags.length === 0) {
                container.innerHTML = '<div class="chat-tree"><div class="tree-children"><div class="empty-state">No tags</div></div></div>';
                return;
            }

            const tags = groupTags.sort((a, b) => a.localeCompare(b));
            const html = tags.map(tag => {
                const items = groups[tag] || [];
                const itemHtml = items.map(conv => `
                    <div class="tree-item tag-conversation-item" data-conversation-id="${this.escapeHtml(String(conv.conversation_id || ''))}" data-agent-id="${this.escapeHtml(String(agentId))}">
                        <span class="tree-icon">💬</span>
                        <span class="item-text">${this.escapeHtml(conv.title || 'New conversation')}${conv.stick_time ? ' <span style=\"color:#ff9800;\">📌</span>' : ''}</span>
                    </div>
                `).join('');

                return `
                    <div class="tag-group" style="padding: 6px 8px;">
                        <div class="tag-group-header" style="font-weight: 600; color: var(--text-primary, #333); padding: 4px 0;">${this.escapeHtml(tag)}</div>
                        <div class="tree-children">${itemHtml}</div>
                    </div>
                `;
            }).join('');

            container.innerHTML = `<div class="chat-tree"><div class="tree-children">${html}</div></div>`;

            container.querySelectorAll('.tag-conversation-item').forEach(item => {
                item.addEventListener('click', () => {
                    const conversationId = item.dataset.conversationId;
                    const itemAgentId = parseInt(item.dataset.agentId);

                    container.querySelectorAll('.tree-item').forEach(i => i.classList.remove('active'));
                    item.classList.add('active');

                    this.loadConversationForAgent(conversationId, itemAgentId);
                });

                item.addEventListener('contextmenu', (e) => {
                    e.preventDefault();
                    const conversationId = item.dataset.conversationId;
                    const itemAgentId = parseInt(item.dataset.agentId);
                    const conv = (conversations || []).find(c => String(c.conversation_id) === String(conversationId)) || null;
                    this.showChatContextMenu(e, itemAgentId, conversationId, conv);
                });
            });
        } catch (e) {
            console.error('[MultiAgentHandlers] Failed to load tag list:', e);
            container.textContent = 'Failed to load tags';
        }
    },

    showChatContextMenu(event, agentId, conversationId, conversation) {
        const existingMenu = document.querySelector('.chat-context-menu');
        if (existingMenu) existingMenu.remove();

        const title = (conversation && conversation.title) ? conversation.title : 'Conversation';
        const isPinned = !!(conversation && conversation.stick_time);

        const menu = document.createElement('div');
        menu.className = 'status-context-menu chat-context-menu';
        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;
        menu.style.display = 'block';
        menu.style.zIndex = '10001';

        menu.innerHTML = `
            <button type="button" class="context-menu-item" data-action="rename"><span>Rename</span></button>
            <button type="button" class="context-menu-item" data-action="pin"><span>${isPinned ? 'Unpin' : 'Pin'}</span></button>
            <button type="button" class="context-menu-item" data-action="tag"><span>Tag</span></button>
            <button type="button" class="context-menu-item" data-action="delete" style="color: var(--color-danger, #f44336);"><span>Delete</span></button>
        `;

        document.body.appendChild(menu);

        const closeMenu = () => {
            if (menu && menu.parentNode) menu.remove();
            document.removeEventListener('click', closeMenu);
        };

        menu.addEventListener('click', async (e) => {
            const item = e.target.closest('.context-menu-item');
            if (!item) return;

            const action = item.dataset.action;
            try {
                if (action === 'delete') {
                    const confirmed = await Toast.confirm(`Delete conversation "${title}"?`, {
                        title: 'Delete Conversation',
                        confirmText: 'Delete',
                        cancelText: 'Cancel',
                        type: 'warning'
                    });
                    if (!confirmed) return;

                    const resp = await fetch(this.resolve(`/api/chat/conversations/${encodeURIComponent(conversationId)}`), {
                        method: 'DELETE'
                    });
                    if (!resp.ok) throw new Error('Delete failed');
                    Toast.success('Conversation deleted successfully');
                    await this.loadChatListForAgent(agentId);
                    await this.loadTagListForAgent(agentId);
                }

                if (action === 'rename') {
                    const input = await Toast.prompt('Enter a new title:', {
                        title: 'Rename Conversation',
                        defaultValue: (conversation && conversation.title) ? conversation.title : '',
                        confirmText: 'Save',
                        cancelText: 'Cancel',
                        type: 'info'
                    });
                    if (input === null) return;
                    const newTitle = String(input).trim();
                    if (!newTitle) {
                        Toast.warning('Title cannot be empty');
                        return;
                    }

                    const resp = await fetch(this.resolve(`/api/chat/conversations/${encodeURIComponent(conversationId)}/title`), {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: newTitle })
                    });
                    if (!resp.ok) throw new Error('Rename failed');
                    Toast.success('Conversation renamed successfully');
                    await this.loadChatListForAgent(agentId);
                    await this.loadTagListForAgent(agentId);
                }

                if (action === 'pin') {
                    const resp = await fetch(this.resolve(`/api/chat/conversations/${encodeURIComponent(conversationId)}/toggle-pin`), {
                        method: 'POST'
                    });
                    if (!resp.ok) throw new Error('Pin toggle failed');
                    Toast.success(isPinned ? 'Conversation unpinned' : 'Conversation pinned');
                    await this.loadChatListForAgent(agentId);
                    await this.loadTagListForAgent(agentId);
                }

                if (action === 'tag') {
                    const currentTag = (conversation && conversation.label) ? String(conversation.label) : '';
                    const input = await Toast.prompt('Enter tag name (leave blank to clear):', {
                        title: 'Set Tag',
                        defaultValue: currentTag,
                        confirmText: 'Save',
                        cancelText: 'Cancel',
                        type: 'info'
                    });
                    if (input === null) return;
                    const newTag = String(input).trim();

                    const resp = await fetch(this.resolve(`/api/chat/conversations/${encodeURIComponent(conversationId)}/tag`), {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tag: newTag })
                    });
                    if (!resp.ok) throw new Error('Tag update failed');
                    Toast.success(newTag ? 'Tag updated successfully' : 'Tag cleared successfully');
                    await this.loadChatListForAgent(agentId);
                    await this.loadTagListForAgent(agentId);
                }
            } catch (err) {
                console.error('[MultiAgentHandlers] Context menu action failed:', err);
                Toast.error((err && err.message) ? err.message : 'Action failed');
            } finally {
                closeMenu();
            }
        });

        setTimeout(() => {
            document.addEventListener('click', closeMenu);
        }, 0);
    },

    /**
     * Send message for a specific agent
     */
    async sendMessageForAgent(agentId) {
        console.log(`[MultiAgentHandlers] Agent ${agentId} sending message`);

        // Set current agent
        agentState.setCurrentAgent(agentId);

        const input = document.getElementById(`chatInput-${agentId}`);
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        const sendBtn = document.getElementById(`sendMessageBtn-${agentId}`);

        if (!input || !messagesContainer) return;

        const message = input.value.trim();
        if (!message) return;

        // Do not allow sending new messages while streaming is in progress
        if (agentState.getRequestId()) {
            return;
        }

        // Get current agent info
        const currentAgent = agentState.getCurrentAgent();
        if (!currentAgent) {
            console.error('[MultiAgentHandlers] No agent selected');
            if (typeof Notification !== 'undefined') {
                Notification.error('Please select an agent first');
            }
            return;
        }

        const agentType = String(currentAgent.agent_type || 'local').toLowerCase();
        const isRemoteAgent = this.isRemoteAgentType(agentType);

        console.log('[MultiAgentHandlers] Sending message with agent:', currentAgent.name, 'ID:', agentId);

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
            month: '2-digit',
            day: '2-digit',
            hour: '2-digit',
            minute: '2-digit'
        });

        const state = agentState.ensureAgentState(agentId);
        const attachments = state.attachments || [];
        const currentConversationId = agentState.getConversationId();
        const attachmentBlock = attachments.length > 0
            ? `<div class="message-attachments">${attachments.map(a => `<span class="attachment-chip" data-conversation-id="${this.escapeHtml(String(currentConversationId || ''))}" data-attachment-id="">${this.escapeHtml(a.name || 'file')}</span>`).join('')}</div>`
            : '';

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
                <div class="message-body">${this.escapeHtml(message)}${attachmentBlock}</div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', userMessageHtml);

        input.value = '';
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        // Save user message to history
        agentState.addMessage('user', message);

        // Get or generate conversation_id
        let conversationId = currentConversationId;
        if (!conversationId) {
            conversationId = agentState.generateConversationId();
            agentState.setConversationId(conversationId);
            console.log(`[MultiAgentHandlers] Agent ${agentId} sending message, conversation_id=${conversationId}`);
            console.log('[MultiAgentHandlers] Generated new conversation ID:', conversationId);
        }

        // Add AI reply container (with thinking animation, show agent name)
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

        // Generate request ID
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
            if (isRemoteAgent) {
                if (!currentAgent.url) {
                    throw new Error('Remote agent A2A endpoint URL is not configured');
                }

                if (attachments && attachments.length > 0) {
                    throw new Error('Remote agents do not support attachments yet');
                }
            }

            // Prepare callbacks (bound to agentId)
            const callbacks = {
                onData: (content) => {
                    agentState.appendStreamingContent(content);
                    this.updateStreamingMessageForAgent(agentState.getStreamingContent(), agentId);
                },
                onEnd: (savedAttachments) => {
                    this.finalizeStreamingMessageForAgent(agentId);
                    this.clearAttachments(agentId);
                    if (savedAttachments && savedAttachments.length > 0) {
                        this.updateLastUserMessageAttachmentIds(agentId, conversationId, savedAttachments);
                    }
                    agentState.clearRequestId();
                    enableSendBtn();
                    // Reload chat list
                    this.loadChatListForAgent(agentId);
                },
                onError: (error) => {
                    this.showStreamErrorForAgent(error, agentId);
                    agentState.clearRequestId();
                    enableSendBtn();
                }
            };

            // Call agent-specific streaming API
            console.log('[MultiAgentHandlers] Calling agent-specific endpoint:', `/api/agent/${agentId}/chat/stream`);
            const uploadFiles = (attachments || []).filter(a => a && a.file).map(a => a.file);
            if (uploadFiles.length > 0) {
                await agentApi.agentChatStreamWithFiles(
                    agentId,
                    message,
                    conversationId,
                    uploadFiles,
                    callbacks,
                    {
                        use_memory: true,
                        use_knowledge_base: true
                    }
                );
            } else {
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
            }

            // Setup timeout handling
            setTimeout(() => {
                if (agentState.getRequestId() === requestId) {
                    this.showStreamErrorForAgent('Request timed out. Please try again.', agentId);
                    agentState.clearRequestId();
                    enableSendBtn();
                }
            }, 120000); // 2 minute timeout

        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to send message:`, error);
            this.showStreamErrorForAgent(error.message, agentId);
            agentState.clearRequestId();
            enableSendBtn();
        }
    },

    /**
     * Update streaming message display (per-agent)
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
     * Finalize streaming message (per-agent)
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
     * Show streaming error (per-agent)
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
                streamingBody.innerHTML = `<div class="error-content"><svg viewBox="0 0 24 24" width="16" height="16" fill="#d93025"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg><span>Request failed: ${this.escapeHtml(error)}</span></div>`;
            }
        }
    },

    /**
     * Handle new chat (per-agent)
     */
    handleNewChatForAgent(agentId) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        // Save welcome message (if any)
        const welcomeMsg = messagesContainer.querySelector('.welcome-message');
        let welcomeHTML = '';
        if (welcomeMsg) {
            welcomeHTML = welcomeMsg.outerHTML;
        }

        // Clear entire chat container
        messagesContainer.innerHTML = '';

        // Re-add welcome message
        if (welcomeHTML) {
            messagesContainer.innerHTML = welcomeHTML;
        }

        // Generate new conversation_id
        const newConversationId = agentState.generateConversationId();
        agentState.setConversationId(newConversationId);

        // Clear chat history
        agentState.clearChatHistory();

        // Clear all selections
        const chatList = document.getElementById(`chatList-${agentId}`);
        if (chatList) {
            chatList.querySelectorAll('.tree-item').forEach(item => {
                item.classList.remove('active');
            });
        }

        console.log(`[MultiAgentHandlers] Agent ${agentId} new chat:`, newConversationId);
    },

    /**
     * Load conversation (per-agent)
     */
    async loadConversationForAgent(conversationId, agentId) {
        try {
            console.log(`[MultiAgentHandlers] Agent ${agentId} loading conversation:`, conversationId);

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

                if (msg.attachments && Array.isArray(msg.attachments) && msg.attachments.length > 0) {
                    const last = messagesContainer.lastElementChild;
                    const body = last ? last.querySelector('.message-body') : null;
                    if (body) {
                        body.insertAdjacentHTML('beforeend', this.createAttachmentBlock(conversationId, msg.attachments));
                    }
                }
                agentState.addMessage(msg.role, msg.content);
            }

            this.clearAttachments(agentId);

            this.highlightCodeBlocks(messagesContainer);

            if (window.MindmapPlugin) {
                messagesContainer.querySelectorAll('.message-body').forEach(body => {
                    window.MindmapPlugin.renderInMessage(body);
                });
            }

            messagesContainer.scrollTop = messagesContainer.scrollHeight;

            console.log(`[MultiAgentHandlers] Agent ${agentId} conversation loaded. Message count:`, messages.length);
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to load conversation:`, error);
        }
    },

    /**
     * Load model options for a specific agent
     */
    async loadModelOptionsForAgent(agentId) {
        const modelSelector = document.getElementById(`modelSelector-${agentId}`);
        if (!modelSelector) return;

        try {
            // 1. Get agent's current configuration
            const agentResponse = await fetch(this.resolve(`/api/agent/${agentId}`));
            const agentResult = await agentResponse.json();
            const currentAgent = agentResult.success ? agentResult.data : null;
            const agentType = String(currentAgent?.agent_type || 'local').toLowerCase();
            if (this.isRemoteAgentType(agentType)) {
                this.applyRemoteUiDisableForAgent(agentId, true);
                modelSelector.innerHTML = '<option value="">Remote agent</option>';
                modelSelector.disabled = true;
                return;
            }

            this.applyRemoteUiDisableForAgent(agentId, false);
            const currentModelConfigId = currentAgent?.model_config_id || currentAgent?.model;

            // 2. Get all model configs
            const response = await fetch(this.resolve('/api/agent/llm-configs'));
            const result = await response.json();

            if (result.success && result.data) {
                const models = result.data.filter(m => m.is_active !== false);

                if (models.length > 0) {
                    // 3. Determine which model should be selected
                    let selectedModel = null;
                    let shouldShowPleaseSelect = false;

                    if (currentModelConfigId) {
                        // If the agent has a saved config, try to find it in the list
                        selectedModel = models.find(m => m.config_id === currentModelConfigId);

                        // If the agent config is not in the available list, show Please Select
                        if (!selectedModel) {
                            shouldShowPleaseSelect = true;
                        }
                    } else {
                        // If the agent has no config, show Please Select
                        shouldShowPleaseSelect = true;
                    }

                    // 4. Render options
                    let optionsHTML = '';

                    // Add "Please Select" option
                    if (shouldShowPleaseSelect) {
                        optionsHTML = '<option value="" selected>Please Select</option>';
                    }

                    // Add model options
                    optionsHTML += models.map(model => `
                        <option value="${model.config_id}" ${selectedModel && model.config_id === selectedModel.config_id ? 'selected' : ''}>
                            ${model.name}${model.provider ? ` (${model.provider})` : ''}
                        </option>
                    `).join('');

                    modelSelector.innerHTML = optionsHTML;

                    // 5. Load selected model config (only when a valid config exists)
                    if (selectedModel) {
                        agentState.setModel(selectedModel.config_id);
                        await this.loadAndApplyModelConfig(selectedModel.config_id, agentId, false);
                    }
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to load model list:`, error);
        }
    },

    /**
     * Load role options for a specific agent
     */
    async loadRoleOptionsForAgent(agentId) {
        const roleSelector = document.getElementById(`roleSelector-${agentId}`);
        if (!roleSelector) return;

        try {
            // 1. Get agent's current configuration
            const agentResponse = await fetch(this.resolve(`/api/agent/${agentId}`));
            const agentResult = await agentResponse.json();
            const currentAgent = agentResult.success ? agentResult.data : null;
            const agentType = String(currentAgent?.agent_type || 'local').toLowerCase();
            if (this.isRemoteAgentType(agentType)) {
                this.applyRemoteUiDisableForAgent(agentId, true);
                roleSelector.innerHTML = '<option value="">Remote agent</option>';
                roleSelector.disabled = true;
                return;
            }

            this.applyRemoteUiDisableForAgent(agentId, false);
            const currentRoleId = currentAgent?.role_id;

            // 2. Get all role configs
            const response = await fetch(this.resolve('/api/agent/role-configs'));
            const result = await response.json();

            if (result.success && result.data) {
                const roles = result.data.filter(r => r.is_active !== false);

                if (roles.length > 0) {
                    // 3. Determine which role should be selected
                    let selectedRole = null;
                    let shouldShowPleaseSelect = false;

                    if (currentRoleId) {
                        // If the agent has a saved config, try to find it in the list
                        selectedRole = roles.find(r => r.role_id === currentRoleId);

                        // If the agent config is not in the available list, show Please Select
                        if (!selectedRole) {
                            shouldShowPleaseSelect = true;
                        }
                    } else {
                        // If the agent has no config, show Please Select
                        shouldShowPleaseSelect = true;
                    }

                    // 4. Render options
                    let optionsHTML = '';

                    // Add "Please Select" option
                    if (shouldShowPleaseSelect) {
                        optionsHTML = '<option value="" selected>Please Select</option>';
                    }

                    // Add role options
                    optionsHTML += roles.map(role => `
                        <option value="${role.role_id}" ${selectedRole && role.role_id === selectedRole.role_id ? 'selected' : ''}>
                            ${role.name}${role.category ? ` - ${role.category}` : ''}
                        </option>
                    `).join('');

                    roleSelector.innerHTML = optionsHTML;

                    // 5. Load selected role config (only when a valid config exists)
                    if (selectedRole) {
                        agentState.setRole(selectedRole.role_id);
                        await this.loadAndApplyRoleConfig(selectedRole.role_id, agentId, false);
                    }
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to load role list:`, error);
        }
    },

    /**
     * Load and apply model config
     * @param {string} configId - Model config ID
     * @param {number} agentId - Agent ID
     * @param {boolean} saveToDatabase - Whether to save to database (default true)
     */
    async loadAndApplyModelConfig(configId, agentId, saveToDatabase = true) {
        try {
            const response = await fetch(this.resolve(`/api/agent/llm-configs/${configId}`));
            const result = await response.json();

            if (result.success && result.data) {
                const modelConfig = result.data;
                agentState.currentModelConfig = modelConfig;
                this.populateParamTabForAgent(modelConfig, agentId);
                console.log(`[MultiAgentHandlers] Agent ${agentId} model config loaded:`, modelConfig.name);

                // If needed, update agent config in database
                if (saveToDatabase) {
                    await this.updateAgentModelConfig(agentId, configId);
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to load model config:`, error);
        }
    },

    /**
     * Load and apply role config
     * @param {string} roleId - Role ID
     * @param {number} agentId - Agent ID
     * @param {boolean} saveToDatabase - Whether to save to database (default true)
     */
    async loadAndApplyRoleConfig(roleId, agentId, saveToDatabase = true) {
        try {
            const response = await fetch(this.resolve(`/api/agent/role-configs/${roleId}`));
            const result = await response.json();

            if (result.success && result.data) {
                const roleConfig = result.data;
                agentState.currentRoleConfig = roleConfig;
                this.populatePromptTabForAgent(roleConfig, agentId);
                console.log(`[MultiAgentHandlers] Agent ${agentId} role config loaded:`, roleConfig.name);

                // If needed, update agent config in database
                if (saveToDatabase) {
                    await this.updateAgentRoleConfig(agentId, roleId);
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to load role config:`, error);
        }
    },

    /**
     * Update agent's model config in database
     * @param {number} agentId - Agent ID
     * @param {string} configId - Model config ID
     */
    async updateAgentModelConfig(agentId, configId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}`), {
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
                // HTTP error
                console.error(`[MultiAgentHandlers] HTTP ${response.status}:`, result);
                throw new Error(result.detail || `HTTP ${response.status}`);
            }

            if (result.success) {
                console.log(`[MultiAgentHandlers] Agent ${agentId} model config updated in database:`, configId);
                // Reload agent instance to apply the new config
                await this.reloadAgentInstance(agentId);
            } else {
                console.error(`[MultiAgentHandlers] Failed to update agent model config:`, result.error);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Failed to update agent model config:`, error);
            throw error;
        }
    },

    /**
     * Update agent's role config in database
     * @param {number} agentId - Agent ID
     * @param {string} roleId - Role ID
     */
    async updateAgentRoleConfig(agentId, roleId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}`), {
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
                // HTTP error
                console.error(`[MultiAgentHandlers] HTTP ${response.status}:`, result);
                throw new Error(result.detail || `HTTP ${response.status}`);
            }

            if (result.success) {
                console.log(`[MultiAgentHandlers] Agent ${agentId} role config updated in database:`, roleId);
                // Reload agent instance to apply the new config
                await this.reloadAgentInstance(agentId);
            } else {
                console.error(`[MultiAgentHandlers] Failed to update agent role config:`, result.error);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Failed to update agent role config:`, error);
            throw error;
        }
    },

    /**
     * Reload agent instance (let backend reload config from database)
     * @param {number} agentId - Agent ID
     */
    async reloadAgentInstance(agentId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}/reload`), {
                method: 'POST'
            });
            const result = await response.json();
            if (result.success) {
                console.log(`[MultiAgentHandlers] Agent ${agentId} instance reloaded`);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Failed to reload agent instance:`, error);
        }
    },

    /**
     * Populate Param tab (per-agent)
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
     * Populate Prompt tab (per-agent)
     */
    populatePromptTabForAgent(roleConfig, agentId) {
        if (!roleConfig) return;

        const promptTextarea = document.getElementById(`systemPrompt-${agentId}`);
        if (promptTextarea && roleConfig.system_prompt) {
            promptTextarea.value = roleConfig.system_prompt;
        }
    },

    /**
     * Save role system prompt (per-agent)
     */
    async saveRolePromptForAgent(prompt, agentId) {
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
                agentState.currentRoleConfig.system_prompt = prompt;
                if (typeof Notification !== 'undefined') {
                    Notification.success('System prompt saved');
                }
                console.log(`[MultiAgentHandlers] Agent ${agentId} role prompt saved`);
            } else {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Save failed: ' + (result.error || 'Unknown error'));
                }
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to save role prompt:`, error);
            if (typeof Notification !== 'undefined') {
                Notification.error('Save failed: ' + error.message);
            }
        }
    },

    /**
     * Initialize streaming chat listeners
     */
    initChatStreamListeners() {
        if (window.electronAPI && window.electronAPI.onChatStreamData) {
            // Streaming listener in Electron environment
            console.log('[MultiAgentHandlers] Initializing Electron streaming listeners');
            // TODO: Implement streaming listener in Electron environment
        }
    },

    /**
     * Markdown render
     */
    renderMarkdown(text, isStreaming = false) {
        // Reuse agentHandlers.renderMarkdown
        if (window.agentHandlers && window.agentHandlers.renderMarkdown) {
            return window.agentHandlers.renderMarkdown(text, isStreaming);
        }
        return text;
    },

    /**
     * Code highlighting
     */
    highlightCodeBlocks(container) {
        // Reuse agentHandlers.highlightCodeBlocks
        if (window.agentHandlers && window.agentHandlers.highlightCodeBlocks) {
            window.agentHandlers.highlightCodeBlocks(container);
        }
    },

    /**
     * Create message element
     */
    createMessageElement(role, content, time) {
        // Reuse agentHandlers.createMessageElement
        if (window.agentHandlers && window.agentHandlers.createMessageElement) {
            return window.agentHandlers.createMessageElement(role, content, time);
        }
        return '';
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
     * HTML escape
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Handle add plugin (per-agent)
     */
    handleAddPlugin(agentId) {
        if (typeof Modal === 'undefined') {
            console.error('[MultiAgentHandlers] Modal component not loaded');
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

                const builtin = [
                    { id: 'mindmap', name: 'Mind map plugin', description: 'Convert Markdown mindmap syntax in chat messages into a visual mind map' },
                    { id: 'code', name: 'Code execution plugin', description: 'Extract code blocks from chat messages and provide edit/run features (supports JavaScript, Python, HTML/CSS/JS)' },
                    { id: 'calendar', name: 'Calendar plugin', description: 'Display and manage calendar events in chat' },
                    { id: 'chart', name: 'Chart plugin', description: 'Visualize data into charts' },
                    { id: 'avatar3d', name: '3D Avatar', description: 'Open the 3D Avatar page in the right settings panel' }
                ];

                const loadIntoUi = async () => {
                    if (!select) return;
                    select.innerHTML = '<option value="">Please select a plugin...</option>';
                    if (desc) desc.textContent = 'Select a plugin to view details';

                    for (const b of builtin) {
                        const opt = document.createElement('option');
                        opt.value = `builtin:${b.id}`;
                        opt.textContent = b.name;
                        opt.dataset.description = b.description;
                        select.appendChild(opt);
                    }

                    const plugins = await this._fetchRendererPlugins();
                    window.__multiAgentRendererPlugins__ = plugins;
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
                            const plugins = Array.isArray(window.__multiAgentRendererPlugins__) ? window.__multiAgentRendererPlugins__ : [];
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
                        const deleted = await this._deleteRendererPlugin(id, agentId);
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
                    this.loadPluginForAgent(pluginId, agentId);
                    return;
                }

                if (value.startsWith('renderer:')) {
                    const id = value.slice('renderer:'.length);
                    const plugins = Array.isArray(window.__multiAgentRendererPlugins__) ? window.__multiAgentRendererPlugins__ : [];
                    const plugin = plugins.find(p => String(p.plugin_id) === String(id));
                    if (!plugin) {
                        if (typeof Notification !== 'undefined') {
                            Notification.error('Plugin not found');
                        }
                        return false;
                    }

                    await this.loadRendererPluginForAgent(plugin, agentId);
                    return;
                }

                if (typeof Notification !== 'undefined') {
                    Notification.error('Unsupported plugin selection');
                }
                return false;
            }
        });
    },

    /**
     * Load plugin for a specific agent
     */
    loadPluginForAgent(pluginId, agentId) {
        console.log(`[MultiAgentHandlers] Loading plugin for Agent ${agentId}:`, pluginId);

        // Plugin config
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
            },
            'avatar3d': {
                name: '3D Avatar',
                fullName: '3D Avatar',
                description: 'Open the 3D Avatar page in the right settings panel',
                icon: '<path d="M12 2a4 4 0 0 1 4 4c0 1.1-.45 2.1-1.17 2.83A6 6 0 0 1 18 14v2h-2v-2a4 4 0 0 0-8 0v2H6v-2a6 6 0 0 1 3.17-5.17A3.98 3.98 0 0 1 8 6a4 4 0 0 1 4-4zm0 2a2 2 0 1 0 0 4 2 2 0 0 0 0-4z"/>'
            }
        };

        const config = pluginConfigs[pluginId];
        if (!config) {
            console.error('[MultiAgentHandlers] Unknown plugin ID:', pluginId);
            return;
        }

        // Check whether the plugin is already loaded
        const existingTab = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="plugin-${pluginId}"]`);
        if (existingTab) {
            console.log('[MultiAgentHandlers] Plugin already exists; switching to its tab');
            existingTab.click();
            if (typeof Notification !== 'undefined') {
                Notification.info(`${config.fullName} loaded`);
            }
            return;
        }

        // 1. Create tab button
        const settingsTabs = document.getElementById(`settingsTabs-${agentId}`);
        if (!settingsTabs) {
            console.error('[MultiAgentHandlers] Settings tabs container not found');
            return;
        }

        const tabButton = document.createElement('button');
        tabButton.className = 'settings-tab';
        tabButton.dataset.tab = `plugin-${pluginId}`;
        tabButton.dataset.agentId = agentId;
        tabButton.innerHTML = `
            <span>${config.name}</span>
            <span class="tab-close-btn" title="Close">×</span>
        `;

        // Bind close button event
        const closeBtn = tabButton.querySelector('.tab-close-btn');
        closeBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            this.removePluginTabForAgent(pluginId, agentId);
        });

        settingsTabs.appendChild(tabButton);
        console.log('[MultiAgentHandlers] ✓ Tab button created');

        // 2. Create tab content
        const tabContent = document.getElementById(`settingsTabContent-${agentId}`);
        if (!tabContent) {
            console.error('[MultiAgentHandlers] Tab content container not found');
            return;
        }

        const tabPane = document.createElement('div');
        tabPane.className = 'tab-pane';
        tabPane.dataset.tab = `plugin-${pluginId}`;
        if (pluginId === 'avatar3d') {
            tabPane.innerHTML = `
                <div class="plugin-content" id="plugin-content-${pluginId}-${agentId}">
                    <p style="font-size: 11px; color: #999; text-align: center; padding: 20px;">Loading plugin...</p>
                </div>
            `;
        } else {
            tabPane.innerHTML = `
                <div class="settings-section">
                    <div class="settings-section-title">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                            ${config.icon}
                        </svg>
                        <span>${config.fullName}</span>
                    </div>
                    <div class="plugin-content" id="plugin-content-${pluginId}-${agentId}">
                        <p style="font-size: 11px; color: #999; text-align: center; padding: 20px;">Loading plugin...</p>
                    </div>
                </div>
            `;
        }

        tabContent.appendChild(tabPane);
        console.log('[MultiAgentHandlers] ✓ Tab content created');

        // 3. Activate the newly created tab
        tabButton.click();

        // 4. Load plugin content
        this.loadPluginContentForAgent(pluginId, agentId);

        if (typeof Notification !== 'undefined') {
            Notification.success(`${config.fullName} loaded`);
        }

        console.log('[MultiAgentHandlers] ✓ Plugin loaded');
    },

    /**
     * Remove plugin tab for a specific agent
     */
    removePluginTabForAgent(pluginId, agentId) {
        console.log(`[MultiAgentHandlers] Removing plugin for Agent ${agentId}:`, pluginId);

        // Remove tab button
        const tabButton = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="plugin-${pluginId}"]`);
        const wasActive = !!(tabButton && tabButton.classList.contains('active'));
        if (tabButton) {
            tabButton.remove();
        }

        // Remove tab content
        const tabPane = document.querySelector(`#settingsTabContent-${agentId} .tab-pane[data-tab="plugin-${pluginId}"]`);
        if (tabPane) {
            tabPane.remove();
        }

        if (wasActive) {
            const paramTab = document.querySelector(`#settingsTabs-${agentId} .settings-tab[data-tab="param"]`);
            if (paramTab) {
                this.forceActivateSettingsTabForAgent(agentId, 'param');
            } else {
                const anyTab = document.querySelector(`#settingsTabs-${agentId} .settings-tab`);
                if (anyTab && anyTab.dataset && anyTab.dataset.tab) {
                    this.forceActivateSettingsTabForAgent(agentId, anyTab.dataset.tab);
                }
            }
        }

        if (typeof Notification !== 'undefined') {
            Notification.info('Plugin removed');
        }

        console.log('[MultiAgentHandlers] ✓ Plugin removed');
    },

    /**
     * Load plugin content for a specific agent
     */
    loadPluginContentForAgent(pluginId, agentId) {
        const container = document.getElementById(`plugin-content-${pluginId}-${agentId}`);
        if (!container) {
            console.error('[MultiAgentHandlers] Plugin content container not found:', `plugin-content-${pluginId}-${agentId}`);
            return;
        }

        // Load different content by plugin ID
        switch (pluginId) {
            case 'mindmap':
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
                        <button class="preset-use-btn" style="width: 100%; margin-bottom: 6px;" onclick="multiAgentHandlers.showMindmapExample(${agentId})">Fill example code</button>
                        <button class="preset-use-btn" style="width: 100%;" onclick="multiAgentHandlers.askAIForMindmap(${agentId})">Ask AI to generate a mind map</button>
                    </div>
                `;
                break;
            case 'code':
                if (window.CodePlugin) {
                    window.CodePlugin.render(container);
                } else {
                    container.innerHTML = '<p style="text-align: center; padding: 20px; color: var(--text-secondary, #666);">Code execution plugin is not loaded. Please refresh the page.</p>';
                    console.error('[MultiAgentHandlers] CodePlugin not found');
                }
                break;
            case 'avatar3d':
                container.innerHTML = `
                    <div class="profile-webview-container">
                        <iframe src="https://cjragents.ngrok.app/server1/wschat/static/desktop.html" class="profile-webview" frameborder="0" allow="microphone"></iframe>
                    </div>
                `;
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
     * Show mindmap example (per-agent)
     */
    showMindmapExample(agentId) {
        const input = document.getElementById(`chatInput-${agentId}`);
        if (input) {
            input.value = '```mindmap\n- Learning to Program\n  - Fundamentals\n    - Data types\n    - Control flow\n    - Functions\n  - Projects\n    - Web development\n    - Mobile apps\n    - Data analysis\n  - Advanced topics\n    - Algorithms & data structures\n    - Design patterns\n    - System architecture\n```';
            if (typeof Notification !== 'undefined') {
                Notification.info('Example code filled. Send it to see the mind map result.');
            }
            input.focus();
        }
    },

    /**
     * Ask AI to generate a mindmap (per-agent)
     */
    askAIForMindmap(agentId) {
        const input = document.getElementById(`chatInput-${agentId}`);
        if (input) {
            input.value = 'Please generate a mind map about the "History of AI".\n\nPlease strictly follow this format:\n```mindmap\n- Root node\n  - Child node (indent with 2 spaces)\n    - Grandchild node (indent with 4 spaces)\n```\n\nNotes:\n1. The code block language must be mindmap\n2. Each node must start with "- "\n3. Child nodes must be indented with 2 spaces\n4. Do not use the Tab key';
            if (typeof Notification !== 'undefined') {
                Notification.info('AI request filled. Send it and wait for the AI to reply in the correct format.');
            }
            input.focus();
        }
    }
};

// Export as global object
if (typeof window !== 'undefined') {
    window.multiAgentHandlers = multiAgentHandlers;
}

export default multiAgentHandlers;
