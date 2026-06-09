/**
 * Home Handlers - event handling
 */

import InitializationWizard from './InitializationWizard.js';

const homeHandlers = {
    async init() {
        this.bindEvents();

        await InitializationWizard.show({ auto: true });
    },

    bindEvents() {
        // Bind settings button events
        document.querySelectorAll('.setting-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                const action = btn.dataset.action;
                switch (action) {
                    case 'initialization':
                        this.showConfigurationModal();
                        break;
                    case 'devtools':
                        this.toggleDevTools();
                        break;
                }
            });
        });

        const openUrlInDefaultBrowser = (url) => {
            const u = String(url || '').trim();
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

        if (!this._homeContactLinkClickHandler) {
            this._homeContactLinkClickHandler = (e) => {
                const link = e && e.target && e.target.closest
                    ? e.target.closest('a.contact-link[data-url]')
                    : null;
                if (!link) return;

                try {
                    e.preventDefault();
                    e.stopPropagation();
                } catch (err) {
                }

                const url = link.dataset ? link.dataset.url : link.getAttribute('href');
                openUrlInDefaultBrowser(url);
            };
        }

        document.addEventListener('click', this._homeContactLinkClickHandler);
    },

    showInitializationModal() {
        InitializationWizard.show();
    },

    toggleDevTools() {
        try {
            if (window.electronAPI && typeof window.electronAPI.toggleDevTools === 'function') {
                window.electronAPI.toggleDevTools();
                return;
            }
        } catch (e) {
        }

        // Fallback for non-Electron contexts (e.g. plain browser preview):
        // most browsers do not allow programmatic DevTools toggling.
        if (typeof Notification !== 'undefined' && Notification.warning) {
            Notification.warning('DevTools is only available in the desktop app.');
        } else {
            console.warn('DevTools toggle requested but electronAPI is not available.');
        }
    },

    async showConfigurationModal() {
        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        const openUrlInDefaultBrowser = (url) => {
            const u = String(url || '').trim();
            if (!u) {
                return;
            }
            if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                window.electronAPI.openUrl(u);
            } else {
                window.open(u, '_blank');
            }
        };

        const savedOriginals = { language: '', a2aServerEnabled: false };

        const loadConfigIntoModal = async (modal) => {
            try {
                const localPromise = (window.electronAPI && typeof window.electronAPI.readConfigJson === 'function')
                    ? window.electronAPI.readConfigJson()
                    : Promise.resolve({ success: true, data: {} });

                const remotePromise = (window.api && typeof window.api.get === 'function')
                    ? window.api.get('/api/system/config')
                    : Promise.resolve(null);

                const [localRes, remoteRes] = await Promise.allSettled([localPromise, remotePromise]);

                const localCfg = (localRes.status === 'fulfilled' && localRes.value && localRes.value.success)
                    ? (localRes.value.data || {})
                    : {};

                const remoteData = (remoteRes.status === 'fulfilled') ? remoteRes.value : null;
                const remoteCfg = (remoteData && remoteData.data) ? remoteData.data : (remoteData || {});

                const agentValue = (localCfg.agent_server && String(localCfg.agent_server).trim())
                    ? String(localCfg.agent_server)
                    : (remoteCfg.agent_server || '');

                const snsValue = (localCfg.ai_sns_server && String(localCfg.ai_sns_server).trim())
                    ? String(localCfg.ai_sns_server)
                    : (remoteCfg.ai_sns_server || '');
                const cooldownValue = (remoteCfg && remoteCfg.contact_cooldown_seconds !== undefined && remoteCfg.contact_cooldown_seconds !== null)
                    ? String(remoteCfg.contact_cooldown_seconds)
                    : '300';
                const recentLimitValue = (remoteCfg && remoteCfg.contact_recent_limit !== undefined && remoteCfg.contact_recent_limit !== null)
                    ? String(remoteCfg.contact_recent_limit)
                    : '3';

                const compactEveryValue = (remoteCfg && remoteCfg.process_info_compact_every_n !== undefined && remoteCfg.process_info_compact_every_n !== null)
                    ? String(remoteCfg.process_info_compact_every_n)
                    : '50';
                const planSummaryEveryValue = (remoteCfg && remoteCfg.process_info_plan_summary_every_n !== undefined && remoteCfg.process_info_plan_summary_every_n !== null)
                    ? String(remoteCfg.process_info_plan_summary_every_n)
                    : '5';

                let logRetentionValue = '3';
                if (localCfg && Object.prototype.hasOwnProperty.call(localCfg, 'log_retention_days')) {
                    const v = localCfg.log_retention_days;
                    logRetentionValue = (v === undefined || v === null) ? '' : String(v);
                } else if (remoteCfg && Object.prototype.hasOwnProperty.call(remoteCfg, 'log_retention_days')) {
                    const v = remoteCfg.log_retention_days;
                    logRetentionValue = (v === undefined || v === null) ? '' : String(v);
                }

                const toolCheckEveryValue = (remoteCfg && remoteCfg.tool_check_every_n !== undefined && remoteCfg.tool_check_every_n !== null)
                    ? String(remoteCfg.tool_check_every_n)
                    : '0';
                const toolCheckBeforeReviewValue = (remoteCfg && remoteCfg.tool_check_before_review_enabled !== undefined && remoteCfg.tool_check_before_review_enabled !== null)
                    ? Boolean(remoteCfg.tool_check_before_review_enabled)
                    : false;
                const agentCardBeforeReviewValue = (remoteCfg && remoteCfg.agent_card_before_review_enabled !== undefined && remoteCfg.agent_card_before_review_enabled !== null)
                    ? Boolean(remoteCfg.agent_card_before_review_enabled)
                    : false;

                const memoryEnabledValue = (remoteCfg && remoteCfg.memory_enabled !== undefined && remoteCfg.memory_enabled !== null)
                    ? Boolean(remoteCfg.memory_enabled)
                    : true;

                const memoryEmbeddingEnabledValue = (remoteCfg && remoteCfg.memory_embedding_enabled !== undefined && remoteCfg.memory_embedding_enabled !== null)
                    ? Boolean(remoteCfg.memory_embedding_enabled)
                    : false;

                const languageValue = (remoteCfg && remoteCfg.language) ? String(remoteCfg.language) : 'en';
                const a2aServerEnabledValue = (remoteCfg && remoteCfg.a2a_server_enabled !== undefined && remoteCfg.a2a_server_enabled !== null)
                    ? Boolean(remoteCfg.a2a_server_enabled)
                    : false;
                const debugModeValue = (remoteCfg && remoteCfg.debug_mode !== undefined && remoteCfg.debug_mode !== null)
                    ? String(remoteCfg.debug_mode)
                    : '';

                const agentInput = modal.element?.querySelector('#homeCfgAgentServer');
                const snsInput = modal.element?.querySelector('#homeCfgAiSnsServer');
                const cooldownInput = modal.element?.querySelector('#homeCfgContactCooldownSeconds');
                const recentLimitInput = modal.element?.querySelector('#homeCfgContactRecentLimit');
                const compactEveryInput = modal.element?.querySelector('#homeCfgProcessInfoCompactEveryN');
                const planSummaryEveryInput = modal.element?.querySelector('#homeCfgProcessInfoPlanSummaryEveryN');
                const logRetentionInput = modal.element?.querySelector('#homeCfgLogRetentionDays');
                const toolCheckEveryInput = modal.element?.querySelector('#homeCfgToolCheckEveryN');
                const toolCheckBeforeReviewInput = modal.element?.querySelector('#homeCfgToolCheckBeforeReviewEnabled');
                const agentCardBeforeReviewInput = modal.element?.querySelector('#homeCfgAgentCardBeforeReviewEnabled');
                const agentCardBeforeReviewRow = modal.element?.querySelector('#homeCfgAgentCardBeforeReviewRow');
                const languageSelect = modal.element?.querySelector('#homeCfgLanguage');
                const a2aServerEnabledInput = modal.element?.querySelector('#homeCfgA2aServerEnabled');
                const memoryEnabledInput = modal.element?.querySelector('#homeCfgMemoryEnabled');
                const memoryEmbeddingEnabledInput = modal.element?.querySelector('#homeCfgMemoryEmbeddingEnabled');
                const memoryEmbeddingRow = modal.element?.querySelector('#homeCfgMemoryEmbeddingRow');
                if (agentInput) {
                    agentInput.value = agentValue;
                }
                if (snsInput) {
                    snsInput.value = snsValue;
                }
                if (cooldownInput) {
                    cooldownInput.value = cooldownValue;
                }
                if (recentLimitInput) {
                    recentLimitInput.value = recentLimitValue;
                }
                if (compactEveryInput) {
                    compactEveryInput.value = compactEveryValue;
                }
                if (planSummaryEveryInput) {
                    planSummaryEveryInput.value = planSummaryEveryValue;
                }
                if (logRetentionInput) {
                    logRetentionInput.value = logRetentionValue;
                }
                if (toolCheckEveryInput) {
                    toolCheckEveryInput.value = toolCheckEveryValue;
                }
                if (toolCheckBeforeReviewInput) {
                    toolCheckBeforeReviewInput.checked = !!toolCheckBeforeReviewValue;
                }
                if (agentCardBeforeReviewInput) {
                    agentCardBeforeReviewInput.checked = !!agentCardBeforeReviewValue;
                }
                if (agentCardBeforeReviewRow) {
                    agentCardBeforeReviewRow.style.display = toolCheckBeforeReviewValue ? '' : 'none';
                }
                if (memoryEnabledInput) {
                    memoryEnabledInput.checked = !!memoryEnabledValue;
                }
                if (memoryEmbeddingEnabledInput) {
                    memoryEmbeddingEnabledInput.checked = !!memoryEmbeddingEnabledValue;
                }
                if (memoryEmbeddingRow) {
                    memoryEmbeddingRow.style.display = memoryEnabledValue ? '' : 'none';
                }
                if (languageSelect) {
                    languageSelect.value = languageValue;
                }
                if (a2aServerEnabledInput) {
                    a2aServerEnabledInput.checked = !!a2aServerEnabledValue;
                }
                const debugModeInput = modal.element?.querySelector('#homeCfgDebugMode');
                if (debugModeInput) {
                    debugModeInput.value = debugModeValue;
                }

                savedOriginals.language = languageValue;
                savedOriginals.a2aServerEnabled = !!a2aServerEnabledValue;
            } catch (e) {
                if (typeof Notification !== 'undefined' && Notification.error) {
                    Notification.error(e.message || 'Failed to load configuration');
                }
            }
        };

        Modal.show({
            title: 'Configuration',
            content: `
                <div class="settings-modal">
                    <div class="setting-group">
                        <label>Backend Server</label>
                        <input type="text" class="setting-input" id="homeCfgAgentServer" value="" placeholder="http://..." />
                    </div>
                    <div class="setting-group">
                        <label>AI-SNS Server</label>
                        <input type="text" class="setting-input" id="homeCfgAiSnsServer" value="" placeholder="http://..." />
                    </div>
                    <div class="setting-group">
                        <label>Contact Cooldown (seconds)</label>
                        <input type="number" min="0" max="86400" step="1" class="setting-input" id="homeCfgContactCooldownSeconds" value="" placeholder="300" />
                    </div>
                    <div class="setting-group">
                        <label>Recent Contact Limit</label>
                        <input type="number" min="0" max="50" step="1" class="setting-input" id="homeCfgContactRecentLimit" value="" placeholder="3" />
                    </div>
                    <div class="setting-group">
                        <label>Process Log Compact Every N Rounds</label>
                        <input type="number" min="0" max="100000" step="1" class="setting-input" id="homeCfgProcessInfoCompactEveryN" value="" placeholder="50" />
                    </div>
                    <div class="setting-group">
                        <label>Process Plan Summary Every N Rounds (0 = disabled)</label>
                        <input type="number" min="0" max="100000" step="1" class="setting-input" id="homeCfgProcessInfoPlanSummaryEveryN" value="" placeholder="5" />
                    </div>
                    <div class="setting-group">
                        <label>Log retention days</label>
                        <input type="number" min="0" max="3650" step="1" class="setting-input" id="homeCfgLogRetentionDays" value="" placeholder="Default 3. Leave empty to disable deletion. Deletes folders older than N days." />
                    </div>
                    <div class="setting-group">
                        <label>Run Tool Before Action Decision Every N Rounds (0 = disabled)</label>
                        <input type="number" min="0" max="100000" step="1" class="setting-input" id="homeCfgToolCheckEveryN" value="" placeholder="0" />
                    </div>
                    <div class="setting-group">
                        <label>Debug Mode</label>
                        <input type="text" class="setting-input" id="homeCfgDebugMode" value="" placeholder="Empty=off, * = all tags, or comma-separated tags (e.g. xmpp_session_start,km)" />
                    </div>
                    <div class="setting-group">
                        <label class="setting-checkbox">
                            <input type="checkbox" id="homeCfgToolCheckBeforeReviewEnabled" />
                            <span>Run Tool Before Conversation Review</span>
                        </label>
                    </div>
                    <div class="setting-group" id="homeCfgAgentCardBeforeReviewRow" style="display:none;">
                        <label class="setting-checkbox">
                            <input type="checkbox" id="homeCfgAgentCardBeforeReviewEnabled" />
                            <span>Fetch Peer Agent Card Before Review</span>
                        </label>
                    </div>
                    <div class="setting-group">
                        <label class="setting-checkbox">
                            <input type="checkbox" id="homeCfgMemoryEnabled" />
                            <span>Enable Memory</span>
                        </label>
                    </div>
                    <div class="setting-group" id="homeCfgMemoryEmbeddingRow" style="display:none;">
                        <label class="setting-checkbox">
                            <input type="checkbox" id="homeCfgMemoryEmbeddingEnabled" />
                            <span>Enable Memory Embedding</span>
                        </label>
                    </div>
                    <div class="setting-group">
                        <label class="setting-checkbox">
                            <input type="checkbox" id="homeCfgA2aServerEnabled" />
                            <span>Enable A2A Server (port 8789)</span>
                        </label>
                    </div>
                    <div class="setting-group">
                        <label>Language</label>
                        <select class="setting-input" id="homeCfgLanguage">
                            <option value="en">English</option>
                            <option value="zh">中文</option>
                        </select>
                        <div style="display:flex;justify-content:flex-end;margin-top:18px;">
                            <a href="#" id="homeCfgAgentHelp" style="font-size:12px;">Help</a>
                        </div>
                    </div>
                </div>
            `,
            confirmText: 'Save',
            cancelText: 'Cancel',
            showCancel: true,
            width: '720px',
            onOpen: async (modal) => {
                const agentHelp = modal.element?.querySelector('#homeCfgAgentHelp');
                if (agentHelp) {
                    agentHelp.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const url = 'https://guide.ai-sns.org/docs.html';
                        openUrlInDefaultBrowser(url);
                    });
                }

                await loadConfigIntoModal(modal);

                const toolCheckBeforeReviewInputOnOpen = modal.element?.querySelector('#homeCfgToolCheckBeforeReviewEnabled');
                const agentCardBeforeReviewRowOnOpen = modal.element?.querySelector('#homeCfgAgentCardBeforeReviewRow');
                const agentCardBeforeReviewInputOnOpen = modal.element?.querySelector('#homeCfgAgentCardBeforeReviewEnabled');
                if (toolCheckBeforeReviewInputOnOpen && agentCardBeforeReviewRowOnOpen) {
                    const applyAgentCardRow = () => {
                        const enabled = !!toolCheckBeforeReviewInputOnOpen.checked;
                        agentCardBeforeReviewRowOnOpen.style.display = enabled ? '' : 'none';
                        if (!enabled && agentCardBeforeReviewInputOnOpen) {
                            agentCardBeforeReviewInputOnOpen.checked = false;
                        }
                    };
                    toolCheckBeforeReviewInputOnOpen.addEventListener('change', applyAgentCardRow);
                    applyAgentCardRow();
                }

                const memoryEnabledInput = modal.element?.querySelector('#homeCfgMemoryEnabled');
                const memoryEmbeddingRow = modal.element?.querySelector('#homeCfgMemoryEmbeddingRow');
                const memoryEmbeddingEnabledInput = modal.element?.querySelector('#homeCfgMemoryEmbeddingEnabled');
                if (memoryEnabledInput && memoryEmbeddingRow) {
                    const applyMemoryRow = () => {
                        const enabled = !!memoryEnabledInput.checked;
                        memoryEmbeddingRow.style.display = enabled ? '' : 'none';
                        if (!enabled && memoryEmbeddingEnabledInput) {
                            memoryEmbeddingEnabledInput.checked = false;
                        }
                    };
                    memoryEnabledInput.addEventListener('change', applyMemoryRow);
                    applyMemoryRow();
                }
            },
            onConfirm: async (modal) => {
                try {
                    if (!window.electronAPI || typeof window.electronAPI.writeConfigJson !== 'function') {
                        throw new Error('electronAPI.writeConfigJson not available');
                    }

                    const agent_server = (modal.element?.querySelector('#homeCfgAgentServer')?.value || '').trim();
                    const ai_sns_server = (modal.element?.querySelector('#homeCfgAiSnsServer')?.value || '').trim();

                    const cooldownRaw = (modal.element?.querySelector('#homeCfgContactCooldownSeconds')?.value || '').trim();
                    const recentLimitRaw = (modal.element?.querySelector('#homeCfgContactRecentLimit')?.value || '').trim();

                    const compactEveryRaw = (modal.element?.querySelector('#homeCfgProcessInfoCompactEveryN')?.value || '').trim();
                    const planSummaryEveryRaw = (modal.element?.querySelector('#homeCfgProcessInfoPlanSummaryEveryN')?.value || '').trim();
                    const logRetentionRaw = (modal.element?.querySelector('#homeCfgLogRetentionDays')?.value || '').trim();
                    const toolCheckEveryRaw = (modal.element?.querySelector('#homeCfgToolCheckEveryN')?.value || '').trim();
                    const tool_check_before_review_enabled = !!(modal.element?.querySelector('#homeCfgToolCheckBeforeReviewEnabled')?.checked);
                    let agent_card_before_review_enabled = !!(modal.element?.querySelector('#homeCfgAgentCardBeforeReviewEnabled')?.checked);
                    if (!tool_check_before_review_enabled) {
                        agent_card_before_review_enabled = false;
                    }

                    const memory_enabled = !!(modal.element?.querySelector('#homeCfgMemoryEnabled')?.checked);

                    const contact_cooldown_seconds = cooldownRaw ? parseInt(cooldownRaw, 10) : 300;
                    const contact_recent_limit = recentLimitRaw ? parseInt(recentLimitRaw, 10) : 3;

                    const process_info_compact_every_n = compactEveryRaw ? parseInt(compactEveryRaw, 10) : 50;
                    const process_info_plan_summary_every_n = planSummaryEveryRaw ? parseInt(planSummaryEveryRaw, 10) : 5;
                    const tool_check_every_n = toolCheckEveryRaw ? parseInt(toolCheckEveryRaw, 10) : 0;

                    const log_retention_days = logRetentionRaw ? parseInt(logRetentionRaw, 10) : 3;

                    if (!Number.isFinite(contact_cooldown_seconds) || contact_cooldown_seconds < 0 || contact_cooldown_seconds > 86400) {
                        throw new Error('Contact Cooldown must be between 0 and 86400 seconds');
                    }
                    if (!Number.isFinite(contact_recent_limit) || contact_recent_limit < 0 || contact_recent_limit > 50) {
                        throw new Error('Recent Contact Limit must be between 0 and 50');
                    }
                    if (!Number.isFinite(process_info_compact_every_n) || process_info_compact_every_n < 0 || process_info_compact_every_n > 100000) {
                        throw new Error('Process Log Compact Every N Rounds must be between 0 and 100000');
                    }
                    if (!Number.isFinite(process_info_plan_summary_every_n) || process_info_plan_summary_every_n < 0 || process_info_plan_summary_every_n > 100000) {
                        throw new Error('Process Plan Summary Every N Rounds must be between 0 and 100000');
                    }
                    if (!Number.isFinite(tool_check_every_n) || tool_check_every_n < 0 || tool_check_every_n > 100000) {
                        throw new Error('Tool Check Every N Rounds must be between 0 and 100000');
                    }

                    if (logRetentionRaw) {
                        if (!Number.isFinite(log_retention_days) || log_retention_days < 0 || log_retention_days > 3650) {
                            throw new Error('Log retention days must be between 0 and 3650, or empty to disable deletion');
                        }
                    }

                    let memory_embedding_enabled = !!(modal.element?.querySelector('#homeCfgMemoryEmbeddingEnabled')?.checked);
                    if (!memory_enabled) {
                        memory_embedding_enabled = false;
                    }

                    const language = (modal.element?.querySelector('#homeCfgLanguage')?.value || 'en').trim();
                    const a2a_server_enabled = !!(modal.element?.querySelector('#homeCfgA2aServerEnabled')?.checked);
                    const debug_mode = (modal.element?.querySelector('#homeCfgDebugMode')?.value || '').trim();

                    const localRes = await window.electronAPI.writeConfigJson({
                        agent_server,
                        ai_sns_server,
                        log_retention_days: logRetentionRaw ? String(log_retention_days) : ''
                    });
                    if (!localRes || !localRes.success) {
                        if (typeof Notification !== 'undefined' && Notification.error) {
                            Notification.error(localRes?.error || 'Local save failed');
                        }
                        return false;
                    }

                    let remoteOk = true;
                    if (window.api && typeof window.api.put === 'function') {
                        try {
                            const remoteRes = await window.api.put('/api/system/config', {
                                agent_server,
                                ai_sns_server,
                                contact_cooldown_seconds,
                                contact_recent_limit,
                                process_info_compact_every_n,
                                process_info_plan_summary_every_n,
                                tool_check_every_n,
                                tool_check_before_review_enabled,
                                agent_card_before_review_enabled,
                                memory_enabled,
                                memory_embedding_enabled,
                                language,
                                a2a_server_enabled,
                                debug_mode,
                                log_retention_days: logRetentionRaw ? log_retention_days : null,
                            });
                            remoteOk = !!(remoteRes && remoteRes.success);
                        } catch (e) {
                            remoteOk = false;
                        }
                    }

                    if (typeof Notification !== 'undefined') {
                        if (remoteOk && Notification.success) {
                            Notification.success('Configuration saved');
                        } else if (!remoteOk && Notification.warning) {
                            Notification.warning('Saved to local config.json, but failed to write to database');
                        } else if (!remoteOk && Notification.success) {
                            Notification.success('Saved to local config.json');
                        }
                    }

                    try {
                        const normalize = (raw) => {
                            const v = String(raw || '').trim();
                            if (!v) return '';
                            const withScheme = /^https?:\/\//i.test(v) ? v : `http://${v}`;
                            return withScheme.endsWith('/') ? withScheme.slice(0, -1) : withScheme;
                        };

                        const prevAgent = (window.appConfig && window.appConfig.agent_server) ? String(window.appConfig.agent_server) : '';
                        const prevAiSns = (window.appConfig && window.appConfig.ai_sns_server) ? String(window.appConfig.ai_sns_server) : '';

                        const nextAgent = normalize(agent_server);
                        const nextAiSns = normalize(ai_sns_server);

                        if (!window.appConfig || typeof window.appConfig !== 'object') {
                            window.appConfig = {};
                        }
                        window.appConfig.agent_server = nextAgent;
                        window.appConfig.ai_sns_server = nextAiSns;
                        window.appConfig.language = String(language || 'en').toLowerCase();

                        if (window.api && typeof window.api.normalizeHttpBaseUrl === 'function') {
                            try { window.api.baseUrl = window.api.normalizeHttpBaseUrl(nextAgent || window.api.baseUrl || ''); } catch (e) {}
                        }

                        try {
                            if (window.toolsEditDialog) {
                                const base = nextAgent;
                                window.toolsEditDialog.apiBaseUrl = base ? `${base}/api/tools` : '/api/tools';
                            }
                        } catch (e) {}

                        try {
                            window.dispatchEvent(new CustomEvent('app-config-updated', {
                                detail: { prevAgentServer: prevAgent, agentServer: nextAgent, prevAiSnsServer: prevAiSns, aiSnsServer: nextAiSns, language: window.appConfig.language }
                            }));
                        } catch (e) {}

                        const serverChanged = String(prevAgent || '') !== String(nextAgent || '');
                        if (serverChanged) {
                            if (typeof Notification !== 'undefined' && Notification.info) {
                                Notification.info('Server URL changed. Please refresh the frontend to reconnect WebSocket to the new server.');
                            }
                        }
                        const langChanged = String(language || '') !== String(savedOriginals.language || '');
                        const a2aChanged = !!a2a_server_enabled !== !!savedOriginals.a2aServerEnabled;
                        if (serverChanged || langChanged || a2aChanged) {
                            if (typeof Notification !== 'undefined' && Notification.info) {
                                Notification.info('Some changes may require restarting the backend server or refreshing the page to take full effect.');
                            }
                        }
                    } catch (e) {}

                    return true;
                } catch (e) {
                    if (typeof Notification !== 'undefined' && Notification.error) {
                        Notification.error(e.message || 'Save failed');
                    }
                    return false;
                }
            }
        });
    },

    destroy() {
        // Clean up event listeners
        if (this._homeContactLinkClickHandler) {
            try {
                document.removeEventListener('click', this._homeContactLinkClickHandler);
            } catch (e) {
            }
        }
    }
};

export default homeHandlers;
