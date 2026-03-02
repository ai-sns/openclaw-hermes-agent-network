/**
 * Home Handlers - event handling
 */

import InitializationWizard from './InitializationWizard.js';

const homeHandlers = {
    init() {
        this.bindEvents();

        InitializationWizard.show({ auto: true });
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
                    case 'help':
                        this.showHelpModal();
                        break;
                }
            });
        });
    },

    showInitializationModal() {
        InitializationWizard.show();
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

                const timeoutValue = (remoteCfg && remoteCfg.conversation_timeout_seconds !== undefined && remoteCfg.conversation_timeout_seconds !== null)
                    ? String(remoteCfg.conversation_timeout_seconds)
                    : '60';
                const cooldownValue = (remoteCfg && remoteCfg.contact_cooldown_seconds !== undefined && remoteCfg.contact_cooldown_seconds !== null)
                    ? String(remoteCfg.contact_cooldown_seconds)
                    : '300';
                const recentLimitValue = (remoteCfg && remoteCfg.contact_recent_limit !== undefined && remoteCfg.contact_recent_limit !== null)
                    ? String(remoteCfg.contact_recent_limit)
                    : '3';

                const agentInput = modal.element?.querySelector('#homeCfgAgentServer');
                const snsInput = modal.element?.querySelector('#homeCfgAiSnsServer');
                const timeoutInput = modal.element?.querySelector('#homeCfgConversationTimeoutSeconds');
                const cooldownInput = modal.element?.querySelector('#homeCfgContactCooldownSeconds');
                const recentLimitInput = modal.element?.querySelector('#homeCfgContactRecentLimit');
                if (agentInput) {
                    agentInput.value = agentValue;
                }
                if (snsInput) {
                    snsInput.value = snsValue;
                }
                if (timeoutInput) {
                    timeoutInput.value = timeoutValue;
                }
                if (cooldownInput) {
                    cooldownInput.value = cooldownValue;
                }
                if (recentLimitInput) {
                    recentLimitInput.value = recentLimitValue;
                }
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
                        <label>Agent Server <a href="#" id="homeCfgAgentHelp" style="font-size:12px;">help</a></label>
                        <input type="text" class="setting-input" id="homeCfgAgentServer" value="" placeholder="http://..." />
                    </div>
                    <div class="setting-group">
                        <label>AI-SNS Server <a href="#" id="homeCfgAiSnsHelp" style="font-size:12px;">help</a></label>
                        <input type="text" class="setting-input" id="homeCfgAiSnsServer" value="" placeholder="http://..." />
                    </div>
                    <div class="setting-group">
                        <label>Conversation Timeout (seconds)</label>
                        <input type="number" min="5" max="3600" step="1" class="setting-input" id="homeCfgConversationTimeoutSeconds" value="" placeholder="60" />
                    </div>
                    <div class="setting-group">
                        <label>Contact Cooldown (seconds)</label>
                        <input type="number" min="0" max="86400" step="1" class="setting-input" id="homeCfgContactCooldownSeconds" value="" placeholder="300" />
                    </div>
                    <div class="setting-group">
                        <label>Recent Contact Limit</label>
                        <input type="number" min="0" max="50" step="1" class="setting-input" id="homeCfgContactRecentLimit" value="" placeholder="3" />
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
                        const url = (window.appConfig && window.appConfig.ai_sns_server) ? window.appConfig.ai_sns_server : '';
                        openUrlInDefaultBrowser(url);
                    });
                }
                const snsHelp = modal.element?.querySelector('#homeCfgAiSnsHelp');
                if (snsHelp) {
                    snsHelp.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        const url = (window.appConfig && window.appConfig.ai_sns_server) ? window.appConfig.ai_sns_server : '';
                        openUrlInDefaultBrowser(url);
                    });
                }

                await loadConfigIntoModal(modal);
            },
            onConfirm: async (modal) => {
                try {
                    if (!window.electronAPI || typeof window.electronAPI.writeConfigJson !== 'function') {
                        throw new Error('electronAPI.writeConfigJson not available');
                    }

                    const agent_server = (modal.element?.querySelector('#homeCfgAgentServer')?.value || '').trim();
                    const ai_sns_server = (modal.element?.querySelector('#homeCfgAiSnsServer')?.value || '').trim();

                    const timeoutRaw = (modal.element?.querySelector('#homeCfgConversationTimeoutSeconds')?.value || '').trim();
                    const cooldownRaw = (modal.element?.querySelector('#homeCfgContactCooldownSeconds')?.value || '').trim();
                    const recentLimitRaw = (modal.element?.querySelector('#homeCfgContactRecentLimit')?.value || '').trim();

                    const conversation_timeout_seconds = timeoutRaw ? parseInt(timeoutRaw, 10) : 60;
                    const contact_cooldown_seconds = cooldownRaw ? parseInt(cooldownRaw, 10) : 300;
                    const contact_recent_limit = recentLimitRaw ? parseInt(recentLimitRaw, 10) : 3;

                    if (!Number.isFinite(conversation_timeout_seconds) || conversation_timeout_seconds < 5 || conversation_timeout_seconds > 3600) {
                        throw new Error('Conversation Timeout must be between 5 and 3600 seconds');
                    }
                    if (!Number.isFinite(contact_cooldown_seconds) || contact_cooldown_seconds < 0 || contact_cooldown_seconds > 86400) {
                        throw new Error('Contact Cooldown must be between 0 and 86400 seconds');
                    }
                    if (!Number.isFinite(contact_recent_limit) || contact_recent_limit < 0 || contact_recent_limit > 50) {
                        throw new Error('Recent Contact Limit must be between 0 and 50');
                    }

                    const localRes = await window.electronAPI.writeConfigJson({ agent_server, ai_sns_server });
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
                                conversation_timeout_seconds,
                                contact_cooldown_seconds,
                                contact_recent_limit,
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

    showHelpModal() {
        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        Modal.show({
            title: 'Help',
            content: `
                <div class="help-modal">
                    <h4>Keyboard shortcuts</h4>
                    <ul class="help-list">
                        <li><kbd>Ctrl/Cmd + B</kbd> Collapse/expand sidebar</li>
                        <li><kbd>Ctrl/Cmd + K</kbd> Search</li>
                        <li><kbd>Ctrl/Cmd + ,</kbd> Settings</li>
                        <li><kbd>Ctrl/Cmd + 1-6</kbd> Quick navigation</li>
                    </ul>
                    <h4>Modules</h4>
                    <ul class="help-list">
                        <li><strong>SNS</strong> - Social exploration on the map</li>
                        <li><strong>Agent</strong> - AI agent chat</li>
                        <li><strong>KM</strong> - Knowledge base management</li>
                        <li><strong>Tools</strong> - Tools & plugins</li>
                        <li><strong>Web</strong> - LLM online services</li>
                        <li><strong>Home</strong> - Home settings</li>
                    </ul>
                </div>
            `,
            showCancel: false,
            confirmText: 'Close'
        });
    },

    destroy() {
        // Clean up event listeners
    }
};

export default homeHandlers;
