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
    _agentChatSuggestionCommands: ['Get the weather of', 'Search the web for'],
    _agentChatInputHistoryByAgentId: new Map(),
    _agentChatInputHistoryIndexByAgentId: new Map(),
    _agentChatDraftBeforeHistoryBrowseByAgentId: new Map(),
    _agentChatSuggestionGlobalClickBound: false,
    _agentChatHistoryLoadedByAgentId: new Set(),

    matchesToolbarTitle(el, titles) {
        if (!el) return false;
        const t = String(el.getAttribute('title') || '').trim();
        return (titles || []).some(x => String(x).trim() === t);
    },

    async _loadAgentChatInputHistoryIfNeeded(agentId) {
        const id = String(agentId);
        if (this._agentChatHistoryLoadedByAgentId && this._agentChatHistoryLoadedByAgentId.has(id)) return;

        if (!this._agentChatHistoryLoadedByAgentId) {
            this._agentChatHistoryLoadedByAgentId = new Set();
        }

        this._agentChatHistoryLoadedByAgentId.add(id);

        try {
            if (!window.electronAPI || typeof window.electronAPI.readAgentChatInputHistory !== 'function') {
                return;
            }

            const resp = await window.electronAPI.readAgentChatInputHistory(agentId);
            if (!resp || resp.success !== true) {
                return;
            }

            const raw = resp.data ? String(resp.data) : '';
            const lines = raw
                .split(/\r?\n/)
                .map(v => String(v || '').trim())
                .filter(v => !!v);

            const maxEntries = 30;
            const trimmed = lines.length > maxEntries ? lines.slice(lines.length - maxEntries) : lines;

            const existing = this._agentChatInputHistoryByAgentId.get(id) || [];
            if (existing.length) {
                return;
            }
            this._agentChatInputHistoryByAgentId.set(id, trimmed);
            this._agentChatInputHistoryIndexByAgentId.set(id, -1);
            this._agentChatDraftBeforeHistoryBrowseByAgentId.set(id, '');
        } catch (e) {
        }
    },

    async _persistAgentChatInputHistory(agentId) {
        try {
            if (!window.electronAPI || typeof window.electronAPI.writeAgentChatInputHistory !== 'function') {
                return;
            }

            const id = String(agentId);
            const history = this._agentChatInputHistoryByAgentId.get(id) || [];
            await window.electronAPI.writeAgentChatInputHistory(agentId, history);
        } catch (e) {
        }
    },

    _ensureAgentChatInputEnhancement(textarea) {
        if (!textarea) return;
        try {
            if (textarea.dataset && textarea.dataset.agentChatInputEnhanced === 'true') {
                return;
            }
            if (textarea.dataset) {
                textarea.dataset.agentChatInputEnhanced = 'true';
            }
        } catch (e) {
        }

        const wrapper = textarea.closest('.input-wrapper');
        if (!wrapper) return;

        try {
            const agentId = textarea.dataset ? parseInt(textarea.dataset.agentId) : NaN;
            if (Number.isFinite(agentId)) {
                this._loadAgentChatInputHistoryIfNeeded(agentId);
            }
        } catch (e) {
        }

        let suggestionMenu = wrapper.querySelector('.sns-human-input-suggestions');
        if (!suggestionMenu) {
            suggestionMenu = document.createElement('div');
            suggestionMenu.className = 'sns-human-input-suggestions';
            suggestionMenu.style.display = 'none';
            suggestionMenu.setAttribute('role', 'listbox');
            suggestionMenu.innerHTML = this._agentChatSuggestionCommands.map((command, index) => `
                <button
                    type="button"
                    class="sns-human-input-suggestion"
                    data-command="${command}"
                    data-index="${index}"
                    role="option"
                >${command}</button>
            `).join('');
            wrapper.appendChild(suggestionMenu);
        }

        let activeSuggestionIndex = -1;

        const isSuggestionVisible = () => suggestionMenu && suggestionMenu.style.display !== 'none';

        const updateSuggestionSelection = () => {
            if (!suggestionMenu) return;
            suggestionMenu.querySelectorAll('.sns-human-input-suggestion').forEach((button, index) => {
                const isActive = index === activeSuggestionIndex;
                button.classList.toggle('active', isActive);
                button.setAttribute('aria-selected', isActive ? 'true' : 'false');
            });
        };

        const hideSuggestionMenu = () => {
            if (!suggestionMenu) return;
            suggestionMenu.style.display = 'none';
            activeSuggestionIndex = -1;
            updateSuggestionSelection();
        };

        const showSuggestionMenu = () => {
            if (!suggestionMenu) return;
            suggestionMenu.style.display = 'block';
            if (activeSuggestionIndex < 0) activeSuggestionIndex = 0;
            updateSuggestionSelection();
        };

        const syncSuggestionMenu = () => {
            if (textarea.value === '@') {
                showSuggestionMenu();
            } else {
                hideSuggestionMenu();
            }
        };

        const applySuggestion = (command) => {
            textarea.value = `${command} `;
            hideSuggestionMenu();
            textarea.focus();
            try {
                const pos = textarea.value.length;
                textarea.setSelectionRange(pos, pos);
            } catch (e) {
            }
        };

        try {
            if (!suggestionMenu.dataset) suggestionMenu.dataset = {};
            if (suggestionMenu.dataset.agentSuggestionHideBound !== 'true') {
                suggestionMenu.dataset.agentSuggestionHideBound = 'true';
                suggestionMenu.addEventListener('agent-chat-hide-suggestions', () => {
                    hideSuggestionMenu();
                });
            }
        } catch (e) {
        }

        const getAgentId = () => {
            try {
                const raw = textarea.dataset ? textarea.dataset.agentId : '';
                const id = parseInt(raw);
                return Number.isFinite(id) ? id : null;
            } catch (e) {
                return null;
            }
        };

        const ensureHistoryState = (agentId) => {
            const id = String(agentId);
            if (!this._agentChatInputHistoryByAgentId.has(id)) {
                this._agentChatInputHistoryByAgentId.set(id, []);
            }
            if (!this._agentChatInputHistoryIndexByAgentId.has(id)) {
                this._agentChatInputHistoryIndexByAgentId.set(id, -1);
            }
            if (!this._agentChatDraftBeforeHistoryBrowseByAgentId.has(id)) {
                this._agentChatDraftBeforeHistoryBrowseByAgentId.set(id, '');
            }
        };

        const browseHistory = (direction) => {
            const agentId = getAgentId();
            if (!agentId) return;
            const id = String(agentId);
            ensureHistoryState(agentId);

            const history = this._agentChatInputHistoryByAgentId.get(id) || [];
            if (!history.length) return;

            const idx = this._agentChatInputHistoryIndexByAgentId.get(id);
            if (idx === -1) {
                this._agentChatDraftBeforeHistoryBrowseByAgentId.set(id, textarea.value);
            }

            if (direction < 0) {
                const nextIndex = idx === -1 ? history.length - 1 : Math.max(0, idx - 1);
                this._agentChatInputHistoryIndexByAgentId.set(id, nextIndex);
                textarea.value = history[nextIndex];
            } else {
                if (idx === -1) return;
                const nextIndex = idx + 1;
                if (nextIndex >= history.length) {
                    this._agentChatInputHistoryIndexByAgentId.set(id, -1);
                    textarea.value = this._agentChatDraftBeforeHistoryBrowseByAgentId.get(id) || '';
                } else {
                    this._agentChatInputHistoryIndexByAgentId.set(id, nextIndex);
                    textarea.value = history[nextIndex];
                }
            }

            hideSuggestionMenu();
            try {
                const pos = textarea.value.length;
                textarea.setSelectionRange(pos, pos);
            } catch (e) {
            }
        };

        const resetHistoryBrowse = () => {
            const agentId = getAgentId();
            if (!agentId) return;
            const id = String(agentId);
            ensureHistoryState(agentId);
            this._agentChatInputHistoryIndexByAgentId.set(id, -1);
            this._agentChatDraftBeforeHistoryBrowseByAgentId.set(id, textarea.value);
        };

        suggestionMenu.addEventListener('click', (event) => {
            const suggestionButton = event.target.closest('.sns-human-input-suggestion');
            if (!suggestionButton) return;
            applySuggestion(suggestionButton.dataset.command || '');
        });

        textarea.addEventListener('input', () => {
            const agentId = getAgentId();
            if (agentId) {
                ensureHistoryState(agentId);
                this._agentChatInputHistoryIndexByAgentId.set(String(agentId), -1);
                this._agentChatDraftBeforeHistoryBrowseByAgentId.set(String(agentId), textarea.value);
            }
            syncSuggestionMenu();
        });

        textarea.addEventListener('focus', () => {
            syncSuggestionMenu();
        });

        textarea.addEventListener('blur', () => {
            setTimeout(() => {
                hideSuggestionMenu();
            }, 120);
        });

        textarea.addEventListener('keydown', (e) => {
            if (e.key === 'ArrowUp') {
                if (isSuggestionVisible()) {
                    e.preventDefault();
                    e.stopPropagation();
                    activeSuggestionIndex = activeSuggestionIndex <= 0
                        ? this._agentChatSuggestionCommands.length - 1
                        : activeSuggestionIndex - 1;
                    updateSuggestionSelection();
                    return;
                }

                const atStart = (() => {
                    try {
                        return typeof textarea.selectionStart === 'number' && textarea.selectionStart === 0 && textarea.selectionEnd === 0;
                    } catch (e) {
                        return textarea.value === '';
                    }
                })();

                if (!atStart && textarea.value) {
                    return;
                }

                e.preventDefault();
                e.stopPropagation();
                browseHistory(-1);
                return;
            }

            if (e.key === 'ArrowDown') {
                if (isSuggestionVisible()) {
                    e.preventDefault();
                    e.stopPropagation();
                    activeSuggestionIndex = activeSuggestionIndex >= this._agentChatSuggestionCommands.length - 1
                        ? 0
                        : activeSuggestionIndex + 1;
                    updateSuggestionSelection();
                    return;
                }

                const atEnd = (() => {
                    try {
                        const end = textarea.value.length;
                        return typeof textarea.selectionStart === 'number' && textarea.selectionStart === end && textarea.selectionEnd === end;
                    } catch (e) {
                        return true;
                    }
                })();

                if (!atEnd) {
                    return;
                }

                e.preventDefault();
                e.stopPropagation();
                browseHistory(1);
                return;
            }

            if (e.key === 'Escape' && isSuggestionVisible()) {
                e.preventDefault();
                e.stopPropagation();
                hideSuggestionMenu();
                return;
            }

            if (e.key === 'Enter' && !e.shiftKey) {
                if (isSuggestionVisible() && activeSuggestionIndex >= 0) {
                    e.preventDefault();
                    e.stopPropagation();
                    applySuggestion(this._agentChatSuggestionCommands[activeSuggestionIndex]);
                    return;
                }
                hideSuggestionMenu();
                resetHistoryBrowse();
                return;
            }
        });

        if (!this._agentChatSuggestionGlobalClickBound) {
            this._agentChatSuggestionGlobalClickBound = true;
            document.addEventListener('click', (event) => {
                const inAgentInputWrapper = event.target && event.target.closest && event.target.closest('.agent-chat-input-area .input-wrapper');
                if (inAgentInputWrapper) return;

                document.querySelectorAll('.agent-chat-input-area .input-wrapper .sns-human-input-suggestions').forEach(menu => {
                    try {
                        menu.dispatchEvent(new Event('agent-chat-hide-suggestions'));
                    } catch (e) {
                    }
                });
            });
        }
    },

    _pushAgentChatInputHistory(agentId, message) {
        if (!agentId || !message) return;
        const id = String(agentId);
        if (!this._agentChatInputHistoryByAgentId) {
            this._agentChatInputHistoryByAgentId = new Map();
        }
        if (!this._agentChatInputHistoryIndexByAgentId) {
            this._agentChatInputHistoryIndexByAgentId = new Map();
        }
        if (!this._agentChatDraftBeforeHistoryBrowseByAgentId) {
            this._agentChatDraftBeforeHistoryBrowseByAgentId = new Map();
        }

        const history = this._agentChatInputHistoryByAgentId.get(id) || [];
        if (!history.length || history[history.length - 1] !== message) {
            history.push(message);
        }

        const maxEntries = 30;
        const trimmed = history.length > maxEntries ? history.slice(history.length - maxEntries) : history;
        this._agentChatInputHistoryByAgentId.set(id, trimmed);
        this._agentChatInputHistoryIndexByAgentId.set(id, -1);
        this._agentChatDraftBeforeHistoryBrowseByAgentId.set(id, '');

        try {
            this._persistAgentChatInputHistory(agentId);
        } catch (e) {
        }
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
        if (pluginKey === 'PL_BUILTIN_LOG_VIEWER') {
            pane.innerHTML = `<div class="status-section"><div class="status-rows"><div class="sns-plugin-host" style="min-height: 120px;"></div></div></div>`;
        } else {
            pane.innerHTML = `
                <div class="settings-section">
                    <div class="settings-section-title">
                        <span>${name}</span>
                    </div>
                    <div class="plugin-content" id="plugin-content-ext-${pluginKey}-${agentKey}"></div>
                </div>
            `;
        }
        tabContent.appendChild(pane);

        tabButton.click();

        const container = (pluginKey === 'PL_BUILTIN_LOG_VIEWER')
            ? pane.querySelector('.sns-plugin-host')
            : pane.querySelector(`#plugin-content-ext-${CSS.escape(pluginKey)}-${CSS.escape(agentKey)}`);
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

        // 1. Load agent list from API and filter out inactive/deleted agents
        const response = await fetch(this.resolve('/api/agent'));
        const result = await response.json();
        const agents = (result.success ? (result.data || []) : [])
            .filter(a => a.is_active !== false);

        if (agents.length === 0) {
            console.warn('[MultiAgentHandlers] No available agents');
            return;
        }

        // 2. Save to state
        agentState.setAgents(agents);
        console.log('[MultiAgentHandlers] Loaded agents:', agents.length);

        // 3. Initialize AgentPage FIRST so that page DOM exists
        await AgentPage.init(agents);

        // 4. Initialize AgentSidebar (switchAgent can now find page elements)
        await AgentSidebar.init();

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

        // Keep the visible/default agent stable after background preload work
        if (agents.length > 0) {
            agentState.setCurrentAgent(agents[0].id);
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
        console.log('[MultiAgentHandlers] === bindAllAgentEvents START ===');
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

        if (!this._agentSettingsContextMenuInitialized) {
            this._agentSettingsContextMenuInitialized = true;

            if (!this._agentSettingsSearchControllers || typeof this._agentSettingsSearchControllers !== 'object') {
                this._agentSettingsSearchControllers = new Map();
            }

            const copyTextToClipboard = async (text) => {
                const v = (text === undefined || text === null) ? '' : String(text);
                if (!v) return { success: false, error: 'Empty text' };

                try {
                    if (window.electronAPI && typeof window.electronAPI.writeClipboardText === 'function') {
                        const result = await window.electronAPI.writeClipboardText(v);
                        if (result && result.success) {
                            return { success: true };
                        }
                        const errMsg = result && result.error ? String(result.error) : 'Unknown error';
                        throw new Error(errMsg);
                    }
                } catch (e) {
                    console.warn('[MultiAgentHandlers] electron clipboard copy failed, falling back', e);
                }

                try {
                    if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                        await navigator.clipboard.writeText(v);
                        return { success: true };
                    }
                } catch (e) {
                    console.warn('[MultiAgentHandlers] navigator.clipboard copy failed, falling back', e);
                }

                try {
                    const ta = document.createElement('textarea');
                    ta.value = v;
                    ta.setAttribute('readonly', '');
                    ta.style.position = 'fixed';
                    ta.style.top = '-9999px';
                    ta.style.left = '-9999px';
                    document.body.appendChild(ta);
                    ta.select();
                    const ok = document.execCommand('copy');
                    document.body.removeChild(ta);
                    return ok ? { success: true } : { success: false, error: 'execCommand(copy) returned false' };
                } catch (e) {
                    return { success: false, error: e && e.message ? e.message : String(e) };
                }
            };

            const ensureSearchBarForAgent = (agentId) => {
                const agentKey = String(agentId || '').trim();
                if (!agentKey) return null;

                const panel = document.getElementById(`agentSettingsPanel-${agentKey}`);
                const tabContent = document.getElementById(`settingsTabContent-${agentKey}`);
                if (!panel || !tabContent) return null;

                const existing = document.getElementById(`agentSettingsSearchBar-${agentKey}`);
                if (existing) return existing;

                const bar = document.createElement('div');
                bar.className = 'status-search-bar';
                bar.id = `agentSettingsSearchBar-${agentKey}`;
                bar.style.display = 'none';
                bar.innerHTML = `
                    <div class="search-input-wrapper">
                        <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="m21 21-4.35-4.35"/>
                        </svg>
                        <input type="text" class="search-input" id="agentSettingsSearchInput-${agentKey}" placeholder="Search within the current tab...">
                        <button class="search-clear-btn" id="agentSettingsSearchClear-${agentKey}" title="Close search">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                    <div class="search-results-info" id="agentSettingsSearchResultsInfo-${agentKey}" style="display: none;">
                        <span id="agentSettingsSearchResultsText-${agentKey}">Found 0 results</span>
                        <div class="search-navigation">
                            <button class="search-nav-btn" id="agentSettingsSearchPrevBtn-${agentKey}" title="Previous">
                                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="15 18 9 12 15 6"/>
                                </svg>
                            </button>
                            <button class="search-nav-btn" id="agentSettingsSearchNextBtn-${agentKey}" title="Next">
                                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="9 18 15 12 9 6"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                `;

                panel.insertBefore(bar, panel.firstChild);
                return bar;
            };

            const ensureSearchControllerForAgent = (agentId) => {
                const agentKey = String(agentId || '').trim();
                if (!agentKey) return null;

                const existingCtrl = this._agentSettingsSearchControllers.get(agentKey);
                if (existingCtrl) return existingCtrl;

                ensureSearchBarForAgent(agentKey);

                const searchInput = document.getElementById(`agentSettingsSearchInput-${agentKey}`);
                const searchClear = document.getElementById(`agentSettingsSearchClear-${agentKey}`);
                const searchResultsInfo = document.getElementById(`agentSettingsSearchResultsInfo-${agentKey}`);
                const searchResultsText = document.getElementById(`agentSettingsSearchResultsText-${agentKey}`);
                const searchPrevBtn = document.getElementById(`agentSettingsSearchPrevBtn-${agentKey}`);
                const searchNextBtn = document.getElementById(`agentSettingsSearchNextBtn-${agentKey}`);
                const tabContent = document.getElementById(`settingsTabContent-${agentKey}`);

                if (!searchInput || !tabContent || !searchClear || !searchResultsInfo || !searchPrevBtn || !searchNextBtn) {
                    return null;
                }

                let currentMatches = [];
                let currentMatchIndex = -1;
                let _searchJobToken = 0;
                let _lastSearchedText = '';
                let _pendingNavigate = null;
                let _lastActivePaneKey = null;

                const clearLocalSearchState = () => {
                    currentMatches = [];
                    currentMatchIndex = -1;
                };

                const clearSelectionHighlight = () => {
                    try {
                        const sel = window.getSelection();
                        if (sel && typeof sel.removeAllRanges === 'function') {
                            sel.removeAllRanges();
                        }
                    } catch (e) {
                    }
                };

                const cancelActiveSearchJob = () => {
                    _searchJobToken += 1;
                };

                const getSearchBlocks = (activePane) => {
                    if (!activePane) return [];

                    const blocks = [];
                    const seen = new Set();
                    const pushUnique = (el) => {
                        if (!el || seen.has(el)) return;
                        seen.add(el);
                        blocks.push(el);
                    };

                    Array.from(activePane.querySelectorAll('.settings-section-title')).forEach(pushUnique);
                    Array.from(activePane.querySelectorAll('.settings-section')).forEach(pushUnique);
                    Array.from(activePane.querySelectorAll('.preset-item')).forEach(pushUnique);
                    Array.from(activePane.querySelectorAll('.param-label')).forEach(pushUnique);
                    Array.from(activePane.querySelectorAll('.param-toggle')).forEach(pushUnique);
                    Array.from(activePane.querySelectorAll('pre')).forEach(pushUnique);

                    if (blocks.length > 0) return blocks;

                    try {
                        const children = Array.from(activePane.children || []).filter(Boolean);
                        if (children.length > 0) return children;
                    } catch (e) {
                    }

                    return [activePane];
                };

                const createRangeFromTextOffsets = (root, start, end) => {
                    if (!root || start < 0 || end <= start) return null;
                    const walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, null);
                    let node = null;
                    let pos = 0;
                    let startNode = null;
                    let startOffset = 0;
                    let endNode = null;
                    let endOffset = 0;

                    while ((node = walker.nextNode())) {
                        const value = node.nodeValue || '';
                        const len = value.length;
                        if (!startNode && pos + len >= start) {
                            startNode = node;
                            startOffset = Math.max(0, start - pos);
                        }
                        if (pos + len >= end) {
                            endNode = node;
                            endOffset = Math.max(0, end - pos);
                            break;
                        }
                        pos += len;
                    }

                    if (!startNode || !endNode) return null;
                    try {
                        const range = document.createRange();
                        range.setStart(startNode, startOffset);
                        range.setEnd(endNode, endOffset);
                        return range;
                    } catch (e) {
                        return null;
                    }
                };

                const highlightCurrentMatch = (match) => {
                    try {
                        if (!match || !match.el) return;
                        const q = String(_lastSearchedText || '');
                        if (!q) return;

                        const start = Number(match.start);
                        const end = start + q.length;
                        if (!Number.isFinite(start) || start < 0) return;

                        clearSelectionHighlight();
                        const range = createRangeFromTextOffsets(match.el, start, end);
                        if (!range) return;

                        const sel = window.getSelection();
                        if (!sel) return;
                        sel.removeAllRanges();
                        sel.addRange(range);
                    } catch (e) {
                    }
                };

                const scrollToMatch = (index) => {
                    if (index < 0 || index >= currentMatches.length) return;

                    const match = currentMatches[index];
                    const el = match && match.el;
                    if (!el) return;

                    const q = String(_lastSearchedText || '');
                    const start = Number(match.start);
                    const end = start + q.length;
                    const range = (q && Number.isFinite(start) && start >= 0)
                        ? createRangeFromTextOffsets(el, start, end)
                        : null;

                    if (range) {
                        const rect = range.getBoundingClientRect();
                        const scrollContainer = tabContent;
                        if (scrollContainer) {
                            const containerRect = scrollContainer.getBoundingClientRect();
                            const offsetTop = rect.top - containerRect.top + scrollContainer.scrollTop;
                            scrollContainer.scrollTo({
                                top: offsetTop - scrollContainer.clientHeight / 2 + rect.height / 2,
                                behavior: 'smooth'
                            });
                        }

                        requestAnimationFrame(() => {
                            highlightCurrentMatch(match);
                        });
                    } else if (typeof el.scrollIntoView === 'function') {
                        el.scrollIntoView({ behavior: 'smooth', block: 'center' });
                    }

                    if (searchResultsText) {
                        searchResultsText.textContent = `${index + 1} / ${currentMatches.length}`;
                    }
                };

                const buildMatchesAsync = (searchText) => {
                    const token = _searchJobToken;
                    clearLocalSearchState();

                    const raw = (searchText === undefined || searchText === null) ? '' : String(searchText);
                    const normalized = raw.trim();
                    _lastSearchedText = normalized;

                    if (!normalized) {
                        searchResultsInfo.style.display = 'none';
                        return;
                    }

                    const activePane = tabContent.querySelector('.tab-pane.active');
                    if (!activePane) return;

                    const blocks = getSearchBlocks(activePane);
                    const query = normalized.toLowerCase();
                    const maxMatches = 2000;

                    searchResultsInfo.style.display = 'flex';
                    if (searchResultsText) searchResultsText.textContent = 'Searching...';

                    let blockIndex = 0;

                    const processBatch = () => {
                        if (token !== _searchJobToken) return;

                        const startMs = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();

                        while (blockIndex < blocks.length) {
                            const el = blocks[blockIndex];
                            blockIndex += 1;

                            if (!el) continue;

                            let text = '';
                            try {
                                text = String(el.textContent || '');
                            } catch (e) {
                                text = '';
                            }

                            if (!text) {
                                const nowMs = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
                                if (nowMs - startMs > 10) break;
                                continue;
                            }

                            const lower = text.toLowerCase();
                            let fromIndex = 0;
                            while (fromIndex < lower.length) {
                                const found = lower.indexOf(query, fromIndex);
                                if (found === -1) break;
                                currentMatches.push({ el, start: found });
                                if (currentMatches.length >= maxMatches) break;
                                fromIndex = found + query.length;
                            }

                            if (currentMatches.length >= maxMatches) {
                                break;
                            }

                            const nowMs = (typeof performance !== 'undefined' && performance.now) ? performance.now() : Date.now();
                            if (nowMs - startMs > 10) {
                                break;
                            }
                        }

                        if (token !== _searchJobToken) return;

                        if (blockIndex < blocks.length && currentMatches.length < maxMatches) {
                            requestAnimationFrame(processBatch);
                            return;
                        }

                        searchResultsInfo.style.display = 'flex';
                        if (currentMatches.length > 0) {
                            if (searchResultsText) {
                                if (currentMatches.length >= maxMatches) {
                                    searchResultsText.textContent = `Found ${currentMatches.length}+ results`;
                                } else {
                                    searchResultsText.textContent = `Found ${currentMatches.length} results`;
                                }
                            }
                            const targetIndex = (_pendingNavigate === 'last') ? (currentMatches.length - 1) : 0;
                            _pendingNavigate = null;
                            currentMatchIndex = targetIndex;
                            scrollToMatch(currentMatchIndex);
                        } else {
                            if (searchResultsText) searchResultsText.textContent = 'No results found';
                            currentMatchIndex = -1;
                        }
                    };

                    requestAnimationFrame(processBatch);
                };

                const ensureSearchAndNavigate = (direction) => {
                    const v = String(searchInput.value || '').trim();
                    const sameQuery = v && _lastSearchedText && v === _lastSearchedText;

                    if (!sameQuery) {
                        cancelActiveSearchJob();
                        _pendingNavigate = (direction === 'prev') ? 'last' : null;
                        buildMatchesAsync(v);
                        return true;
                    }
                    return false;
                };

                const closeSearchUI = () => {
                    cancelActiveSearchJob();
                    clearLocalSearchState();
                    clearSelectionHighlight();
                    _lastSearchedText = '';
                    _pendingNavigate = null;
                    searchResultsInfo.style.display = 'none';
                    const searchBar = document.getElementById(`agentSettingsSearchBar-${agentKey}`);
                    if (searchBar) searchBar.style.display = 'none';
                    searchInput.value = '';
                };

                searchInput.addEventListener('input', () => {
                    cancelActiveSearchJob();
                    clearLocalSearchState();
                    searchResultsInfo.style.display = 'none';
                });

                searchClear.addEventListener('click', () => {
                    searchInput.value = '';
                    cancelActiveSearchJob();
                    clearLocalSearchState();
                    clearSelectionHighlight();
                    searchResultsInfo.style.display = 'none';
                    const searchBar = document.getElementById(`agentSettingsSearchBar-${agentKey}`);
                    if (searchBar) {
                        searchBar.style.display = 'none';
                    }
                });

                searchPrevBtn.addEventListener('click', () => {
                    if (ensureSearchAndNavigate('prev')) return;
                    if (currentMatches.length === 0) return;
                    currentMatchIndex = (currentMatchIndex - 1 + currentMatches.length) % currentMatches.length;
                    scrollToMatch(currentMatchIndex);
                });

                searchNextBtn.addEventListener('click', () => {
                    if (ensureSearchAndNavigate('next')) return;
                    if (currentMatches.length === 0) return;
                    currentMatchIndex = (currentMatchIndex + 1) % currentMatches.length;
                    scrollToMatch(currentMatchIndex);
                });

                searchInput.addEventListener('keydown', (e) => {
                    if (e.key === 'Enter') {
                        e.preventDefault();
                        if (e.shiftKey) {
                            if (ensureSearchAndNavigate('prev')) return;
                            if (currentMatches.length === 0) {
                                ensureSearchAndNavigate('prev');
                                return;
                            }
                            currentMatchIndex = (currentMatchIndex - 1 + currentMatches.length) % currentMatches.length;
                            scrollToMatch(currentMatchIndex);
                            return;
                        }

                        if (ensureSearchAndNavigate('next')) return;
                        if (currentMatches.length === 0) {
                            ensureSearchAndNavigate('next');
                            return;
                        }
                        currentMatchIndex = (currentMatchIndex + 1) % currentMatches.length;
                        scrollToMatch(currentMatchIndex);
                    } else if (e.key === 'Escape') {
                        closeSearchUI();
                    }
                });

                document.addEventListener('click', (e) => {
                    const tab = e.target.closest(`.settings-tab[data-agent-id="${agentKey}"]`);
                    if (tab) {
                        closeSearchUI();
                    }
                });

                try {
                    const observer = new MutationObserver(() => {
                        const pane = tabContent.querySelector('.tab-pane.active');
                        const key = pane ? (pane.getAttribute('data-tab') || '') : '';
                        if (key && key !== _lastActivePaneKey) {
                            _lastActivePaneKey = key;
                            closeSearchUI();
                        }
                    });
                    observer.observe(tabContent, { attributes: true, subtree: true, attributeFilter: ['class', 'style'] });
                } catch (e) {
                }

                const ctrl = {
                    closeSearchUI,
                    buildMatchesAsync
                };

                this._agentSettingsSearchControllers.set(agentKey, ctrl);
                return ctrl;
            };

            const existingMenu = document.getElementById('agentSettingsContextMenu');
            const contextMenu = existingMenu || (() => {
                const el = document.createElement('div');
                el.id = 'agentSettingsContextMenu';
                el.className = 'status-context-menu';
                el.style.display = 'none';
                el.innerHTML = `
                    <button class="context-menu-item" data-action="copy">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                        </svg>
                        <span>Copy</span>
                    </button>
                    <button class="context-menu-item" data-action="selectAll">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 11l3 3L22 4"/>
                            <path d="M21 12v7a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h11"/>
                        </svg>
                        <span>Select All</span>
                    </button>
                    <div class="context-menu-divider"></div>
                    <button class="context-menu-item" data-action="search">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <circle cx="11" cy="11" r="8"/>
                            <path d="m21 21-4.35-4.35"/>
                        </svg>
                        <span>Search</span>
                    </button>
                `;
                document.body.appendChild(el);
                return el;
            })();

            let currentAgentId = null;
            let currentTabContent = null;

            const hideContextMenu = () => {
                contextMenu.style.display = 'none';
                currentAgentId = null;
                currentTabContent = null;
            };

            const showMenuAt = (x, y) => {
                contextMenu.style.display = 'block';

                const menuWidth = 180;
                const menuHeight = 120;
                const viewportWidth = window.innerWidth;
                const viewportHeight = window.innerHeight;

                let left = x;
                let top = y;

                if (left + menuWidth > viewportWidth) {
                    left = viewportWidth - menuWidth - 10;
                }
                if (top + menuHeight > viewportHeight) {
                    top = viewportHeight - menuHeight - 10;
                }

                contextMenu.style.left = left + 'px';
                contextMenu.style.top = top + 'px';
            };

            const getSelectedTextFromActiveElement = () => {
                try {
                    const el = document.activeElement;
                    if (!el) return '';
                    const tag = String(el.tagName || '').toLowerCase();
                    if (tag !== 'textarea' && tag !== 'input') return '';
                    if (tag === 'input' && el.type && String(el.type).toLowerCase() !== 'text') return '';
                    if (typeof el.selectionStart !== 'number' || typeof el.selectionEnd !== 'number') return '';
                    const start = el.selectionStart;
                    const end = el.selectionEnd;
                    if (end <= start) return '';
                    const value = String(el.value || '');
                    return value.slice(start, end);
                } catch (e) {
                    return '';
                }
            };

            document.addEventListener('click', (e) => {
                if (!contextMenu.contains(e.target)) {
                    hideContextMenu();
                }
            });

            document.addEventListener('keydown', (e) => {
                if (e.key === 'Escape') {
                    hideContextMenu();
                }
            });

            window.addEventListener('blur', hideContextMenu);

            contextMenu.addEventListener('click', (e) => {
                const menuItem = e.target.closest('.context-menu-item');
                if (!menuItem) return;

                const action = menuItem.dataset.action;
                const tabContent = currentTabContent;
                const activePane = tabContent ? tabContent.querySelector('.tab-pane.active') : null;

                if (action === 'copy') {
                    const selected = window.getSelection ? window.getSelection().toString() : '';
                    const selectedText = selected || getSelectedTextFromActiveElement();
                    if (selectedText) {
                        copyTextToClipboard(selectedText).catch(() => {
                        });
                    }
                } else if (action === 'selectAll') {
                    if (activePane) {
                        const range = document.createRange();
                        range.selectNodeContents(activePane);
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                    }
                } else if (action === 'search') {
                    if (currentAgentId) {
                        ensureSearchControllerForAgent(currentAgentId);
                        const searchBar = document.getElementById(`agentSettingsSearchBar-${currentAgentId}`);
                        const searchInput = document.getElementById(`agentSettingsSearchInput-${currentAgentId}`);
                        if (searchBar) {
                            searchBar.style.display = 'flex';
                            setTimeout(() => {
                                if (searchInput) {
                                    searchInput.focus();
                                    const selected = window.getSelection ? window.getSelection().toString() : '';
                                    const selectedText = selected || getSelectedTextFromActiveElement();
                                    if (selectedText) {
                                        searchInput.value = selectedText;
                                    }
                                }
                            }, 100);
                        }
                    }
                }

                hideContextMenu();
            });

            document.addEventListener('contextmenu', (e) => {
                const tabContent = e.target.closest('.settings-tab-content');
                if (!tabContent) return;
                const panel = tabContent.closest('.agent-settings-panel[data-agent-id]');
                if (!panel) return;
                const agentId = panel.dataset.agentId;
                if (!agentId) return;

                e.preventDefault();
                e.stopPropagation();

                currentAgentId = String(agentId);
                currentTabContent = tabContent;
                ensureSearchControllerForAgent(currentAgentId);
                showMenuAt(e.clientX, e.clientY);
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
            if (chatInput) {
                this._ensureAgentChatInputEnhancement(chatInput);
            }
            if (chatInput && e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                const agentId = parseInt(chatInput.dataset.agentId);
                this.sendMessageForAgent(agentId);
            }
        });

        document.addEventListener('focusin', (e) => {
            const chatInput = e.target.closest && e.target.closest('.agent-chat-input[data-agent-id]');
            if (!chatInput) return;
            this._ensureAgentChatInputEnhancement(chatInput);
        });

        document.addEventListener('input', (e) => {
            const chatInput = e.target.closest && e.target.closest('.agent-chat-input[data-agent-id]');
            if (!chatInput) return;
            this._ensureAgentChatInputEnhancement(chatInput);
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

        if (!this._paramInputEventsBound) {
            this._paramInputEventsBound = true;
            if (!this._paramSaveTimers) {
                this._paramSaveTimers = new Map();
            }

            const resolveThinkingEffortDocUrl = (agentId) => {
                try {
                    const state = agentState.ensureAgentState(agentId);
                    const cfg = state ? state.currentModelConfig : null;
                    const provider = String((cfg && cfg.provider) ? cfg.provider : '').trim().toLowerCase();
                    if (provider === 'gemini') return 'https://ai.google.dev/gemini-api/docs/openai?authuser=1&hl=zh-cn#thinking';
                    if (provider === 'claude') return 'https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking';
                    return 'https://developers.openai.com/api/docs/models/all';
                } catch (e) {
                    return 'https://developers.openai.com/api/docs/models/all';
                }
            };

            const openExternalUrl = (url) => {
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
            };

            const syncThinkingEffortVisibility = (agentId) => {
                const paramPane = document.querySelector(`#settingsTabContent-${agentId} [data-tab="param"]`);
                if (!paramPane) return;
                const checkboxes = Array.from(paramPane.querySelectorAll('input[type="checkbox"]'));
                let enabled = false;
                for (const cb of checkboxes) {
                    const label = cb.closest('label.param-toggle');
                    const labelText = label ? (label.querySelector('span')?.textContent || '').trim() : '';
                    if (labelText === 'Thinking effort') {
                        enabled = !!cb.checked;
                        break;
                    }
                }

                const wrapper = paramPane.querySelector('.thinking-effort-wrapper');
                if (wrapper) wrapper.style.display = enabled ? '' : 'none';

                const linkBox = paramPane.querySelector('.thinking-effort-doc-link');
                const link = paramPane.querySelector('.thinking-effort-doc-anchor');
                const url = enabled ? resolveThinkingEffortDocUrl(agentId) : '';
                if (link) {
                    link.dataset.externalUrl = url;
                    link.href = url || '#';
                }
                if (linkBox) linkBox.style.display = enabled ? '' : 'none';
            };

            const scheduleParamSave = (agentId) => {
                const key = String(agentId);
                const prev = this._paramSaveTimers.get(key);
                if (prev) clearTimeout(prev);
                const t = setTimeout(() => {
                    this.saveModelParamsForAgent(agentId);
                }, 800);
                this._paramSaveTimers.set(key, t);
            };

            document.addEventListener('click', (e) => {
                const target = e.target;
                if (!target) return;
                const anchor = target.closest('a.thinking-effort-doc-anchor[data-external-url]');
                if (!anchor) return;
                const url = anchor.dataset.externalUrl || anchor.getAttribute('href');
                if (!url || url === '#') return;
                e.preventDefault();
                openExternalUrl(url);
            });

            document.addEventListener('change', (e) => {
                const target = e.target;
                if (!target) return;

                const agentIdRaw = target.dataset ? target.dataset.agentId : null;
                if (!agentIdRaw) return;
                const agentId = parseInt(agentIdRaw);
                if (!agentId) return;

                const paramPane = target.closest(`#settingsTabContent-${agentId} [data-tab="param"]`);
                if (!paramPane) return;

                const toggleLabel = target.closest('label.param-toggle');
                const toggleText = toggleLabel ? (toggleLabel.querySelector('span')?.textContent || '').trim() : '';
                if (target.type === 'checkbox' && toggleText === 'Show token usage') {
                    this.setShowTokenUsageForAgent(agentId, !!target.checked);
                    return;
                }

                if (target.classList && target.classList.contains('param-input')) {
                    scheduleParamSave(agentId);
                    return;
                }

                if (target.type === 'checkbox' && toggleText === 'Stream mode') {
                    scheduleParamSave(agentId);
                    return;
                }

                if (target.type === 'checkbox' && toggleText === 'Thinking effort') {
                    syncThinkingEffortVisibility(agentId);
                    scheduleParamSave(agentId);
                }
            });
        }

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

        // Message bubble right-click context menu for copy functionality
        this.initMessageContextMenu();
        
        // Message copy button click handler
        this.initMessageCopyButtons();
        
        // Auto-resize textarea for input
        this.initAutoResizeTextarea();
        
        // Cancel message button handler
        this.initCancelMessageButton();
        
        console.log('[MultiAgentHandlers] Context menu initialized');
        console.log('[MultiAgentHandlers] === bindAllAgentEvents END ===');
    },

    /**
     * Initialize right-click context menu for message bubbles
     */
    initMessageContextMenu() {
        console.log('[MultiAgentHandlers] initMessageContextMenu called');
        
        // Create context menu element if not exists
        let contextMenu = document.getElementById('messageContextMenu');
        if (!contextMenu) {
            contextMenu = document.createElement('div');
            contextMenu.id = 'messageContextMenu';
            contextMenu.className = 'message-context-menu';
            contextMenu.innerHTML = `
                <div class="context-menu-item" id="copyMessageBtn">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                        <path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/>
                    </svg>
                    <span>Copy</span>
                </div>
            `;
            document.body.appendChild(contextMenu);
            console.log('[MultiAgentHandlers] Context menu DOM element created and appended to body');
        }

        // Copy message text to clipboard
        const copyMessageText = async (text) => {
            try {
                if (window.electronAPI && typeof window.electronAPI.writeClipboardText === 'function') {
                    const result = await window.electronAPI.writeClipboardText(text);
                    if (result && result.success) {
                        console.log('[MultiAgentHandlers] Message copied via electron API');
                        return true;
                    }
                }
            } catch (e) {
                console.warn('[MultiAgentHandlers] Electron clipboard failed, falling back:', e);
            }

            try {
                if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                    await navigator.clipboard.writeText(text);
                    console.log('[MultiAgentHandlers] Message copied via navigator.clipboard');
                    return true;
                }
            } catch (e) {
                console.warn('[MultiAgentHandlers] Navigator clipboard failed, falling back:', e);
            }

            // Fallback method
            try {
                const textarea = document.createElement('textarea');
                textarea.value = text;
                textarea.setAttribute('readonly', '');
                textarea.style.position = 'fixed';
                textarea.style.top = '-9999px';
                textarea.style.left = '-9999px';
                document.body.appendChild(textarea);
                textarea.select();
                const ok = document.execCommand('copy');
                document.body.removeChild(textarea);
                if (ok) {
                    console.log('[MultiAgentHandlers] Message copied via execCommand');
                    return true;
                }
            } catch (e) {
                console.warn('[MultiAgentHandlers] Fallback copy failed:', e);
            }

            return false;
        };

        // Hide context menu
        const hideMenu = () => {
            if (contextMenu) {
                contextMenu.style.display = 'none';
            }
        };

        // Show context menu at position
        const showMenuAt = (x, y) => {
            if (contextMenu) {
                contextMenu.style.display = 'block';
                const rect = contextMenu.getBoundingClientRect();
                const maxX = window.innerWidth - rect.width - 10;
                const maxY = window.innerHeight - rect.height - 10;
                contextMenu.style.left = Math.min(x, maxX) + 'px';
                contextMenu.style.top = Math.min(y, maxY) + 'px';
            }
        };

        // Track current target message body
        let currentTargetMessageBody = null;

        // Show menu on right-click on message-body
        document.addEventListener('contextmenu', (e) => {
            const messageBody = e.target.closest('.message-body');
            if (!messageBody) return;

            e.preventDefault();
            e.stopPropagation();

            currentTargetMessageBody = messageBody;
            showMenuAt(e.clientX, e.clientY);
            console.log('[MultiAgentHandlers] Right-click detected on message body, showing menu at', e.clientX, e.clientY);
        }, true);

        // Handle copy action
        contextMenu.addEventListener('click', async (e) => {
            const copyBtn = e.target.closest('#copyMessageBtn');
            if (!copyBtn || !currentTargetMessageBody) return;

            e.preventDefault();
            e.stopPropagation();

            // Get text content from message body
            const textToCopy = currentTargetMessageBody.innerText || currentTargetMessageBody.textContent || '';
            if (!textToCopy.trim()) {
                hideMenu();
                return;
            }

            const success = await copyMessageText(textToCopy);
            if (success) {
                console.log('[MultiAgentHandlers] Message copied successfully');
            }
            hideMenu();
        });

        // Hide menu on click elsewhere
        document.addEventListener('click', (e) => {
            if (!e.target.closest('#messageContextMenu')) {
                hideMenu();
            }
        }, true);

        // Hide menu on scroll
        document.addEventListener('scroll', () => {
            hideMenu();
        }, true);

        // Hide menu on escape key
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                hideMenu();
            }
        });
    },

    /**
     * Initialize message copy buttons click handlers
     */
    initMessageCopyButtons() {
        console.log('[MultiAgentHandlers] initMessageCopyButtons called');
        
        // Use event delegation to handle copy button clicks
        document.addEventListener('click', async (e) => {
            const copyBtn = e.target.closest('.message-copy-btn');
            if (!copyBtn) return;

            e.preventDefault();
            e.stopPropagation();

            // Find the parent message item
            const messageItem = copyBtn.closest('.message-item');
            if (!messageItem) return;

            // Get the message body content
            const messageBody = messageItem.querySelector('.message-body');
            if (!messageBody) return;

            // Get text content from message body
            const textToCopy = messageBody.innerText || messageBody.textContent || '';
            if (!textToCopy.trim()) return;

            // Copy to clipboard
            const success = await this.copyToClipboard(textToCopy);
            if (success) {
                console.log('[MultiAgentHandlers] Message copied successfully via copy button');
                
                // Show visual feedback
                this.showCopyFeedback(copyBtn);
            }
        }, true);
    },

    /**
     * Copy text to clipboard with multiple fallback strategies
     */
    async copyToClipboard(text) {
        try {
            // Try Electron API first
            if (window.electronAPI && typeof window.electronAPI.writeClipboardText === 'function') {
                const result = await window.electronAPI.writeClipboardText(text);
                if (result && result.success) {
                    console.log('[MultiAgentHandlers] Copied via electron API');
                    return true;
                }
            }
        } catch (e) {
            console.warn('[MultiAgentHandlers] Electron clipboard failed:', e);
        }

        try {
            // Try Navigator Clipboard API
            if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                await navigator.clipboard.writeText(text);
                console.log('[MultiAgentHandlers] Copied via navigator.clipboard');
                return true;
            }
        } catch (e) {
            console.warn('[MultiAgentHandlers] Navigator clipboard failed:', e);
        }

        // Fallback to execCommand
        try {
            const textarea = document.createElement('textarea');
            textarea.value = text;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'fixed';
            textarea.style.top = '-9999px';
            textarea.style.left = '-9999px';
            document.body.appendChild(textarea);
            textarea.select();
            const ok = document.execCommand('copy');
            document.body.removeChild(textarea);
            if (ok) {
                console.log('[MultiAgentHandlers] Copied via execCommand');
                return true;
            }
        } catch (e) {
            console.warn('[MultiAgentHandlers] Fallback copy failed:', e);
        }

        return false;
    },

    /**
     * Show visual feedback after copying
     */
    showCopyFeedback(button) {
        // Add success class to button
        const originalHtml = button.innerHTML;
        
        // Change icon to checkmark
        button.innerHTML = `
            <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                <polyline points="20 6 9 17 4 12"></polyline>
            </svg>
        `;
        button.classList.add('copy-success');
        
        // Reset after 2 seconds
        setTimeout(() => {
            button.innerHTML = originalHtml;
            button.classList.remove('copy-success');
        }, 2000);
    },

    /**
     * Initialize auto-resize textarea for chat input
     */
    initAutoResizeTextarea() {
        console.log('[MultiAgentHandlers] initAutoResizeTextarea called');
        
        // Initialize all existing textareas
        document.querySelectorAll('.agent-chat-input').forEach((textarea) => {
            this.autoResizeTextarea(textarea);
        });
        
        // Use event delegation to handle input events on all chat textareas
        document.addEventListener('input', (e) => {
            const textarea = e.target;
            if (!textarea.classList.contains('agent-chat-input')) return;

            // Auto-resize the textarea
            this.autoResizeTextarea(textarea);
        });

        // Also handle initial resize and focus events
        document.addEventListener('focus', (e) => {
            const textarea = e.target;
            if (!textarea.classList.contains('agent-chat-input')) return;
            
            // Resize on focus to ensure correct height
            this.autoResizeTextarea(textarea);
        }, true);
    },

    /**
     * Auto-resize textarea based on content
     * @param {HTMLTextAreaElement} textarea - The textarea element to resize
     */
    autoResizeTextarea(textarea) {
        if (!textarea) return;

        // Temporarily collapse to get the right scrollHeight
        textarea.style.height = 'auto';

        // Calculate new height
        const newHeight = textarea.scrollHeight;
        
        // Get computed styles for min/max constraints
        const style = window.getComputedStyle(textarea);
        const minHeight = parseFloat(style.minHeight) || 0;
        const maxHeight = parseFloat(style.maxHeight) || Infinity;

        // Apply constraints
        let finalHeight = newHeight;
        if (finalHeight < minHeight) {
            finalHeight = minHeight;
        } else if (finalHeight > maxHeight) {
            finalHeight = maxHeight;
            textarea.style.overflowY = 'auto';
        } else {
            textarea.style.overflowY = 'hidden';
        }

        // Set the new height
        textarea.style.height = finalHeight + 'px';
    },

    /**
     * Initialize cancel message button click handler
     */
    initCancelMessageButton() {
        console.log('[MultiAgentHandlers] initCancelMessageButton called');
        
        // Use event delegation to handle cancel button clicks
        document.addEventListener('click', (e) => {
            const cancelBtn = e.target.closest('.cancel-btn');
            if (!cancelBtn) return;

            e.preventDefault();
            e.stopPropagation();

            const agentId = parseInt(cancelBtn.dataset.agentId);
            if (agentId) {
                console.log('[MultiAgentHandlers] Cancelling message for agent:', agentId);

                const activeRequestId = agentState.getRequestIdForAgent(agentId);
                if (activeRequestId) {
                    agentState.setCancelledRequestIdForAgent(agentId, activeRequestId);
                }
                
                // Cancel the active stream (for streaming mode)
                if (window.agentApi && typeof window.agentApi.cancelActiveStream === 'function') {
                    const cancelled = window.agentApi.cancelActiveStream(agentId);
                    if (cancelled) {
                        console.log('[MultiAgentHandlers] Stream cancelled successfully');
                    }
                }

                // Cancel active non-stream requests
                if (window.agentApi && typeof window.agentApi.cancelActiveNonStream === 'function') {
                    const cancelled = window.agentApi.cancelActiveNonStream(agentId, activeRequestId);
                    if (cancelled) {
                        console.log('[MultiAgentHandlers] Non-stream request cancelled successfully');
                    }
                }
                
                // Immediately update UI to show cancelled message
                const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
                const streamingMsg = (messagesContainer && activeRequestId)
                    ? messagesContainer.querySelector(`.message-item[data-request-id="${String(activeRequestId)}"]`)
                    : (messagesContainer ? messagesContainer.querySelector('.message-item.streaming') : null);
                if (streamingMsg) {
                    streamingMsg.classList.remove('streaming');
                    const streamingBody = streamingMsg.querySelector('.message-body');
                    if (streamingBody) {
                        streamingBody.innerHTML = '<em>Reply cancelled</em>';
                    }
                }
                
                // Clear request ID to reset UI state
                agentState.clearRequestIdForAgent(agentId);
                
                // Re-enable send button
                const sendBtn = document.getElementById(`sendMessageBtn-${agentId}`);
                const inputToolbar = sendBtn?.closest('.input-toolbar');
                if (sendBtn) {
                    sendBtn.disabled = false;
                    sendBtn.classList.remove('sending');
                }
                if (inputToolbar) {
                    inputToolbar.classList.remove('sending');
                }
                
                // Notify user
                if (typeof Notification !== 'undefined' && Notification.info) {
                    Notification.info('Generation cancelled');
                }
            }
        }, true);
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
                const attachmentId = btn.dataset.attachmentId;
                const ownerAgentId = parseInt(btn.dataset.agentId);
                this.removeAttachment(ownerAgentId, attachmentId);
            });
        });
    },

    formatFileSize(bytes) {
        const n = Number(bytes) || 0;
        if (n <= 0) return '0 B';

        const k = 1024;
        const sizes = ['B', 'KB', 'MB', 'GB', 'TB'];
        const i = Math.min(sizes.length - 1, Math.floor(Math.log(n) / Math.log(k)));
        return parseFloat((n / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
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

        const chatListContainer = document.getElementById(`chatListContainer-${agentId}`);

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
                if (chatListContainer) {
                    chatListContainer.classList.add('chat-list-empty');
                }
                treeChildren.innerHTML = '<div class="empty-state">No conversations</div>';
                return;
            }

            if (chatListContainer) {
                chatListContainer.classList.remove('chat-list-empty');
            }

            treeChildren.innerHTML = conversations.map((conv) => `
                <div class="tree-item" data-conversation-id="${conv.conversation_id}" data-agent-id="${agentId}">
                    <span class="tree-icon">            🗨️</span>
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
            const chatListContainer = document.getElementById(`chatListContainer-${agentId}`);
            if (chatListContainer) {
                chatListContainer.classList.add('chat-list-empty');
            }
        }
    },

    async loadTagListForAgent(agentId, query = '') {
        const container = document.getElementById(`tagListContainer-${agentId}`);
        if (!container) return;

        try {
            container.classList.add('chat-list-empty');
        } catch (e) {
        }
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
                try {
                    container.classList.add('chat-list-empty');
                } catch (e) {
                }
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
                try {
                    container.classList.add('chat-list-empty');
                } catch (e) {
                }
                container.innerHTML = '<div class="chat-tree"><div class="tree-children"><div class="empty-state">No tags</div></div></div>';
                return;
            }

            try {
                container.classList.remove('chat-list-empty');
            } catch (e) {
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
            try {
                container.classList.add('chat-list-empty');
            } catch (e2) {
            }
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
        if (agentState.getRequestIdForAgent(agentId)) {
            return;
        }

        try {
            this._pushAgentChatInputHistory(agentId, message);
        } catch (e) {
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

        // Disable send button and show cancel button
        if (sendBtn) {
            sendBtn.disabled = true;
            sendBtn.classList.add('sending');
        }
        
        // Add sending class to toolbar to toggle buttons
        const inputToolbar = sendBtn?.closest('.input-toolbar');
        if (inputToolbar) {
            inputToolbar.classList.add('sending');
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
        const currentModelConfig = state.currentModelConfig;
        const streamEnabled = attachments.length > 0
            ? true
            : (currentModelConfig ? (currentModelConfig.stream !== false) : true);
        const showTokenUsage = this.getShowTokenUsageForAgent(agentId);
        const currentConversationId = agentState.getConversationId();
        const attachmentBlock = attachments.length > 0
            ? `<div class="message-attachments">${attachments.map(a => `<span class="attachment-chip" data-conversation-id="${this.escapeHtml(String(currentConversationId || ''))}" data-attachment-id="">${this.escapeHtml(a.name || 'file')}</span>`).join('')}</div>`
            : '';

        // Add user message
        const copyIconSvg = `
            <button class="message-copy-btn" title="Copy message" aria-label="Copy message">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
            </button>
        `;
        
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
                <div class="message-footer">
                    ${copyIconSvg}
                </div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', userMessageHtml);

        input.value = '';
        // Reset textarea height after sending
        input.style.height = 'auto';
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

        agentState.clearCancelledRequestIdForAgent(agentId);

        // Add AI reply container (with thinking animation, show agent name)
        const requestId = 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        const assistantMessageHtml = `
            <div class="message-item assistant-message streaming" data-request-id="${this.escapeHtml(String(requestId))}">
                <div class="message-header">
                    <div class="message-avatar assistant-avatar">            
                    <svg viewBox="0 0 48 48" width="26" height="26" xmlns="http://www.w3.org/2000/svg"  fill="currentColor"><g transform="translate(4.8, 4.8) scale(0.8)"><path d="M24 7v3 M21 7h6 M16 12h16a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H16a3 3 0 0 1-3-3V15a3 3 0 0 1 3-3z M19 19h2 M27 19h2 M11 34c0-3 3-5 6-5h14c3 0 6 2 6 5v4H11v-4z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="20" cy="19" r="1.5" fill="currentColor"/><circle cx="28" cy="19" r="1.5" fill="currentColor"/></g></svg>
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
                <div class="message-footer">
                    ${copyIconSvg}
                </div>
            </div>
        `;
        messagesContainer.insertAdjacentHTML('beforeend', assistantMessageHtml);
        messagesContainer.scrollTop = messagesContainer.scrollHeight;

        agentState.setRequestIdForAgent(agentId, requestId);
        agentState.clearStreamingContentForAgent(agentId);

        // Helper to re-enable the send button
        const enableSendBtn = () => {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.classList.remove('sending');
            }
            // Remove sending class from toolbar to show send button again
            const inputToolbar = sendBtn?.closest('.input-toolbar');
            if (inputToolbar) {
                inputToolbar.classList.remove('sending');
            }
        };

        // Start request - stream or non-stream based on model config
        try {
            if (isRemoteAgent) {
                if (!currentAgent.url) {
                    throw new Error('Remote agent A2A endpoint URL is not configured');
                }

                if (attachments && attachments.length > 0) {
                    throw new Error('Remote agents do not support attachments yet');
                }
            }

            if (streamEnabled) {
                // Prepare callbacks (bound to agentId)
                const callbacks = {
                    onData: (content) => {
                        // Check if cancelled before appending content
                        if (agentState.getRequestIdForAgent(agentId) !== requestId || agentState.isCancelledRequestForAgent(agentId, requestId)) {
                            return;
                        }
                        agentState.appendStreamingContentForAgent(agentId, content);
                        this.updateStreamingMessageForAgent(agentState.getStreamingContentForAgent(agentId), agentId, requestId);
                    },
                    onEnd: (savedAttachments, usage) => {
                        // Check if cancelled before finalizing
                        if (agentState.getRequestIdForAgent(agentId) !== requestId || agentState.isCancelledRequestForAgent(agentId, requestId)) {
                            console.log('[MultiAgentHandlers] Stream completed but was cancelled, ignoring');
                            return;
                        }
                        this.finalizeStreamingMessageForAgent(agentId, requestId);
                        this.clearAttachments(agentId);
                        if (savedAttachments && savedAttachments.length > 0) {
                            this.updateLastUserMessageAttachmentIds(agentId, conversationId, savedAttachments);
                        }
                        if (usage && showTokenUsage) {
                            this.appendTokenUsageToLastAssistantMessageForAgent(agentId, usage);
                        }
                        if (agentState.getRequestIdForAgent(agentId) === requestId) {
                            agentState.clearRequestIdForAgent(agentId);
                            enableSendBtn();
                        }
                        // Reload chat list
                        this.loadChatListForAgent(agentId);
                    },
                    onError: (error) => {
                        // Check if this is a cancellation error
                        if ((error && (error.name === 'AbortError')) || agentState.isCancelledRequestForAgent(agentId, requestId)) {
                            console.log('[MultiAgentHandlers] Request was cancelled');
                            
                            // Show cancelled message in the bubble
                            const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
                            const streamingMsg = messagesContainer ? messagesContainer.querySelector(`.message-item.streaming[data-request-id="${String(requestId)}"]`) : null;
                            if (streamingMsg) {
                                streamingMsg.classList.remove('streaming');
                                const streamingBody = streamingMsg.querySelector('.message-body');
                                if (streamingBody) {
                                    streamingBody.innerHTML = '<em>Reply cancelled</em>';
                                }
                            }
                        } else {
                            this.showStreamErrorForAgent(error, agentId, requestId);
                        }
                        if (agentState.getRequestIdForAgent(agentId) === requestId) {
                            agentState.clearRequestIdForAgent(agentId);
                            enableSendBtn();
                        }
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
                            use_knowledge_base: true,
                            show_token_usage: showTokenUsage
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
                            use_knowledge_base: true,
                            show_token_usage: showTokenUsage
                        }
                    );
                }
            } else {
                console.log('[MultiAgentHandlers] Calling agent-specific endpoint:', `/api/agent/${agentId}/chat`);

                const result = await agentApi.agentChat(
                    agentId,
                    message,
                    conversationId,
                    {
                        use_memory: true,
                        use_knowledge_base: true,
                        show_token_usage: showTokenUsage,
                        requestId: requestId
                    }
                );

                // Check if cancelled before processing response
                if (agentState.isCancelledRequestForAgent(agentId, requestId)) {
                    console.log('[MultiAgentHandlers] Non-stream request was cancelled, ignoring response');
                    
                    // Update the streaming message to show cancelled
                    const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
                    const streamingMsg = messagesContainer ? messagesContainer.querySelector(`.message-item.streaming[data-request-id="${String(requestId)}"]`) : null;
                    if (streamingMsg) {
                        streamingMsg.classList.remove('streaming');
                        const streamingBody = streamingMsg.querySelector('.message-body');
                        if (streamingBody) {
                            streamingBody.innerHTML = '<em>Reply cancelled</em>';
                        }
                    }
                    
                    // Clear request ID and re-enable send button
                    if (agentState.getRequestIdForAgent(agentId) === requestId) {
                        agentState.clearRequestIdForAgent(agentId);
                        enableSendBtn();
                    }
                    return;
                }
                
                // Verify this response is for the current request (not from an old/cancelled request)
                const latestRequestId = agentState.getRequestIdForAgent(agentId);
                if (latestRequestId !== requestId) {
                    console.log('[MultiAgentHandlers] Ignoring response from old/cancelled request');
                    return;
                }

                const reply = result && result.success && result.data ? (result.data.reply || '') : '';
                const usage = result && result.success && result.data ? result.data.usage : null;

                const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
                const streamingMsg = messagesContainer ? messagesContainer.querySelector(`.message-item.streaming[data-request-id="${String(requestId)}"]`) : null;
                if (streamingMsg) {
                    streamingMsg.classList.remove('streaming');
                    const body = streamingMsg.querySelector('.message-body');
                    if (body) {
                        body.innerHTML = this.renderMarkdown(reply);
                        this.highlightCodeBlocks(body);
                        if (window.MindmapPlugin) {
                            window.MindmapPlugin.renderInMessage(body);
                        }
                    }
                }

                agentState.addMessage('assistant', reply);
                if (usage && showTokenUsage) {
                    this.appendTokenUsageToLastAssistantMessageForAgent(agentId, usage);
                }
                agentState.clearRequestIdForAgent(agentId);
                enableSendBtn();
                this.loadChatListForAgent(agentId);
            }

            // Setup timeout handling
            setTimeout(() => {
                if (agentState.getRequestIdForAgent(agentId) === requestId) {
                    this.showStreamErrorForAgent('Request timed out. Please try again.', agentId, requestId);
                    agentState.clearRequestIdForAgent(agentId);
                    enableSendBtn();
                }
            }, 120000); // 2 minute timeout

        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to send message:`, error);
            const isAbort = error && error.name === 'AbortError';
            const isCancelled = isAbort || agentState.isCancelledRequestForAgent(agentId, requestId);
            if (isCancelled) {
                const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
                const msg = messagesContainer ? messagesContainer.querySelector(`.message-item[data-request-id="${String(requestId)}"]`) : null;
                if (msg) {
                    msg.classList.remove('streaming');
                    const body = msg.querySelector('.message-body');
                    if (body) {
                        body.innerHTML = '<em>Reply cancelled</em>';
                    }
                }
            } else {
                this.showStreamErrorForAgent(error && error.message ? error.message : String(error), agentId, requestId);
            }

            if (agentState.getRequestIdForAgent(agentId) === requestId) {
                agentState.clearRequestIdForAgent(agentId);
                enableSendBtn();
            }
        }
    },

    getShowTokenUsageForAgent(agentId) {
        try {
            const state = agentState.ensureAgentState(agentId);
            if (typeof state.showTokenUsage === 'boolean') return state.showTokenUsage;
            const raw = localStorage.getItem(`agent_show_token_usage_${agentId}`);
            const v = raw === '1' || raw === 'true';
            state.showTokenUsage = v;
            return v;
        } catch (e) {
            return false;
        }
    },

    setShowTokenUsageForAgent(agentId, enabled) {
        try {
            const state = agentState.ensureAgentState(agentId);
            state.showTokenUsage = !!enabled;
            localStorage.setItem(`agent_show_token_usage_${agentId}`, enabled ? '1' : '0');
        } catch (e) {
        }
    },

    appendTokenUsageToLastAssistantMessageForAgent(agentId, usage) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;
        const assistantMessages = messagesContainer.querySelectorAll('.message-item.assistant-message');
        const lastAssistant = assistantMessages && assistantMessages.length > 0
            ? assistantMessages[assistantMessages.length - 1]
            : null;
        const body = lastAssistant ? lastAssistant.querySelector('.message-body') : null;
        if (!body) return;

        const prompt = usage && (usage.prompt_tokens ?? usage.promptTokens);
        const completion = usage && (usage.completion_tokens ?? usage.completionTokens);
        const total = usage && (usage.total_tokens ?? usage.totalTokens);
        const text = `Token usage: prompt=${prompt ?? '-'} completion=${completion ?? '-'} total=${total ?? '-'}`;
        body.insertAdjacentHTML('beforeend', `<div class="token-usage" style="margin-top:8px;opacity:0.75;font-size:12px;">${this.escapeHtml(text)}</div>`);
    },

    /**
     * Update streaming message display (per-agent)
     */
    updateStreamingMessageForAgent(content, agentId, requestId = null) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        const selector = requestId
            ? `.message-item.streaming[data-request-id="${String(requestId)}"] .message-body`
            : '.message-item.streaming .message-body';
        const streamingBody = messagesContainer.querySelector(selector);
        if (streamingBody) {
            streamingBody.innerHTML = this.renderMarkdown(content, true) + '<span class="cursor-blink"></span>';
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    },

    /**
     * Finalize streaming message (per-agent)
     */
    finalizeStreamingMessageForAgent(agentId, requestId = null) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        const selector = requestId
            ? `.message-item.streaming[data-request-id="${String(requestId)}"]`
            : '.message-item.streaming';
        const streamingMsg = messagesContainer.querySelector(selector);
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                const content = agentState.getStreamingContentForAgent(agentId);
                streamingBody.innerHTML = this.renderMarkdown(content);
                this.highlightCodeBlocks(streamingBody);

                // Render mindmap (if available)
                if (window.MindmapPlugin) {
                    window.MindmapPlugin.renderInMessage(streamingBody);
                }
            }
        }

        // Save to history
        agentState.addMessageForAgent(agentId, 'assistant', agentState.getStreamingContentForAgent(agentId));
        agentState.clearStreamingContentForAgent(agentId);
    },

    /**
     * Show streaming error (per-agent)
     */
    showStreamErrorForAgent(error, agentId, requestId = null) {
        const messagesContainer = document.getElementById(`chatMessages-${agentId}`);
        if (!messagesContainer) return;

        const selector = requestId
            ? `.message-item.streaming[data-request-id="${String(requestId)}"]`
            : '.message-item.streaming';
        const streamingMsg = messagesContainer.querySelector(selector);
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
                const framework = String(currentAgent?.framework || '').trim();
                const frameworkOther = String(currentAgent?.framework_other || '').trim();
                const label = (framework === 'Other' ? frameworkOther : framework) || 'Remote agent';
                modelSelector.innerHTML = `<option value="">${this.escapeHtml(label)}</option>`;
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
                        const targetState = agentState.ensureAgentState(agentId);
                        if (!targetState.currentModelConfig) {
                            targetState.currentModelConfig = {};
                        }
                        targetState.currentModelConfig.config_id = selectedModel.config_id;
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
                        const targetState = agentState.ensureAgentState(agentId);
                        if (!targetState.currentRoleConfig) {
                            targetState.currentRoleConfig = {};
                        }
                        targetState.currentRoleConfig.role_id = selectedRole.role_id;
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
                let mergedConfig = { ...modelConfig };
                try {
                    const paramsResp = await fetch(this.resolve(`/api/agent/${agentId}/model-params`));
                    const paramsRes = await paramsResp.json();
                    const overrides = (paramsRes && paramsRes.success && paramsRes.data && typeof paramsRes.data === 'object')
                        ? paramsRes.data
                        : {};
                    mergedConfig = { ...modelConfig, ...overrides };
                } catch (e) {
                }

                const targetState = agentState.ensureAgentState(agentId);
                targetState.currentModelConfig = mergedConfig;
                this.populateParamTabForAgent(mergedConfig, agentId);
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
                const targetState = agentState.ensureAgentState(agentId);
                targetState.currentRoleConfig = roleConfig;
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

        const checkboxes = Array.from(paramPane.querySelectorAll('input[type="checkbox"]'));
        for (const cb of checkboxes) {
            const label = cb.closest('label.param-toggle');
            const labelText = label ? (label.querySelector('span')?.textContent || '').trim() : '';
            if (labelText === 'Stream mode' && modelConfig.stream !== undefined) {
                cb.checked = !!modelConfig.stream;
            }
            if (labelText === 'Show token usage') {
                cb.checked = this.getShowTokenUsageForAgent(agentId);
            }
            if (labelText === 'Thinking effort') {
                cb.checked = !!modelConfig.thinking_effort_enabled;
            }
        }

        const effortSelect = paramPane.querySelector('select.thinking-effort-select');
        if (effortSelect) {
            const v = String(modelConfig.thinking_effort_level || '').trim().toLowerCase();
            if (v) effortSelect.value = v;
        }

        try {
            const checkboxes2 = Array.from(paramPane.querySelectorAll('input[type="checkbox"]'));
            for (const cb of checkboxes2) {
                const label = cb.closest('label.param-toggle');
                const labelText = label ? (label.querySelector('span')?.textContent || '').trim() : '';
                if (labelText === 'Thinking effort') {
                    const enabled = !!cb.checked;
                    const wrapper = paramPane.querySelector('.thinking-effort-wrapper');
                    if (wrapper) wrapper.style.display = enabled ? '' : 'none';
                    const linkBox = paramPane.querySelector('.thinking-effort-doc-link');
                    const link = paramPane.querySelector('.thinking-effort-doc-anchor');
                    let url = '';
                    try {
                        const provider = String(modelConfig.provider || '').trim().toLowerCase();
                        if (provider === 'gemini') url = 'https://ai.google.dev/gemini-api/docs/openai?authuser=1&hl=zh-cn#thinking';
                        else if (provider === 'claude') url = 'https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking';
                        else url = 'https://developers.openai.com/api/docs/models/all';
                    } catch (e) {
                        url = 'https://developers.openai.com/api/docs/models/all';
                    }
                    if (link) {
                        link.dataset.externalUrl = enabled ? url : '';
                        link.href = enabled ? url : '#';
                    }
                    if (linkBox) linkBox.style.display = enabled ? '' : 'none';
                    break;
                }
            }
        } catch (e) {
        }
    },

    async saveModelParamsForAgent(agentId) {
        agentState.setCurrentAgent(agentId);

        const state = agentState.ensureAgentState(agentId);
        const currentConfig = state.currentModelConfig;
        if (!currentConfig || !currentConfig.config_id) {
            console.warn(`[MultiAgentHandlers] Agent ${agentId} has no current model config; cannot save params`);
            return;
        }

        const paramPane = document.querySelector(`#settingsTabContent-${agentId} [data-tab="param"]`);
        if (!paramPane) return;

        const params = {};
        const inputs = paramPane.querySelectorAll('.param-input');
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

        const checkboxes = Array.from(paramPane.querySelectorAll('input[type="checkbox"]'));
        for (const cb of checkboxes) {
            const label = cb.closest('label.param-toggle');
            const labelText = label ? (label.querySelector('span')?.textContent || '').trim() : '';
            if (labelText === 'Stream mode') {
                params.stream = !!cb.checked;
            }
            if (labelText === 'Thinking effort') {
                params.thinking_effort_enabled = !!cb.checked;
            }
        }

        const effortSelect = paramPane.querySelector('select.thinking-effort-select');
        if (effortSelect) {
            params.thinking_effort_level = String(effortSelect.value || '').trim();
        }

        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}/model-params`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(params)
            });
            const result = await response.json();
            if (result.success) {
                Object.assign(state.currentModelConfig, params);
                console.log(`[MultiAgentHandlers] Agent ${agentId} model params saved`);
                await this.reloadAgentInstance(agentId);
            } else {
                console.error(`[MultiAgentHandlers] Agent ${agentId} failed to save model params:`, result.error);
            }
        } catch (error) {
            console.error(`[MultiAgentHandlers] Agent ${agentId} failed to save model params:`, error);
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
                    { id: 'avatar3d', name: '3D Avatar', description: 'Open the 3D Avatar page in the right settings panel' },
                    { id: 'llm-log', name: 'LLM Log', description: 'Browse backend LLM logs by date and file.' }
                ];

                const loadIntoUi = async () => {
                    if (!select) return;
                    select.innerHTML = '<option value="" disabled selected>Please select a plugin...</option>';
                    if (desc) desc.textContent = 'Select a plugin to view details';
                    try {
                        select.classList.add('is-placeholder');
                    } catch (e) {
                    }

                    if (builtin.length) {
                        const group = document.createElement('optgroup');
                        group.label = 'Built-in';
                        for (const b of builtin) {
                            const opt = document.createElement('option');
                            opt.value = `builtin:${b.id}`;
                            opt.textContent = b.name;
                            opt.dataset.description = b.description;
                            group.appendChild(opt);
                        }
                        select.appendChild(group);
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
                        try {
                            if (value) select.classList.remove('is-placeholder');
                            else select.classList.add('is-placeholder');
                        } catch (e) {
                        }
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
            'llm-log': {
                name: 'LLM Log',
                fullName: 'LLM Log',
                description: 'Browse backend LLM logs by date and file.',
                icon: '<path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>'
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

        if (pluginId === 'llm-log') {
            const builtinPlugin = {
                plugin_id: 'PL_BUILTIN_LOG_VIEWER',
                name: 'LLM Log',
                version: '1.0.0',
                alias_name: 'log-viewer',
                description: 'Browse backend LLM logs by date and file.',
                filename: '/scripts/builtin_plugins/log_viewer/index.js',
                plugin_type: 'renderer'
            };
            this.loadRendererPluginForAgent(builtinPlugin, agentId);
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
