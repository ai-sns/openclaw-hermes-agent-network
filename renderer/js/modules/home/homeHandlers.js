/**
 * Home Handlers - 事件处理
 */

import InitializationWizard from './InitializationWizard.js';

const homeHandlers = {
    init() {
        this.bindEvents();

        InitializationWizard.show({ auto: true });
    },

    bindEvents() {
        // 绑定设置按钮事件
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

                const agentInput = modal.element?.querySelector('#homeCfgAgentServer');
                const snsInput = modal.element?.querySelector('#homeCfgAiSnsServer');
                if (agentInput) {
                    agentInput.value = agentValue;
                }
                if (snsInput) {
                    snsInput.value = snsValue;
                }
            } catch (e) {
                if (typeof Notification !== 'undefined' && Notification.error) {
                    Notification.error(e.message || '加载配置失败');
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
                </div>
            `,
            confirmText: '保存',
            cancelText: '取消',
            showCancel: true,
            width: '720px',
            onOpen: async (modal) => {
                const agentHelp = modal.element?.querySelector('#homeCfgAgentHelp');
                if (agentHelp) {
                    agentHelp.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        openUrlInDefaultBrowser('https://www.ai-sns.org');
                    });
                }
                const snsHelp = modal.element?.querySelector('#homeCfgAiSnsHelp');
                if (snsHelp) {
                    snsHelp.addEventListener('click', (e) => {
                        e.preventDefault();
                        e.stopPropagation();
                        openUrlInDefaultBrowser('https://www.ai-sns.org');
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

                    const localRes = await window.electronAPI.writeConfigJson({ agent_server, ai_sns_server });
                    if (!localRes || !localRes.success) {
                        if (typeof Notification !== 'undefined' && Notification.error) {
                            Notification.error(localRes?.error || '本地保存失败');
                        }
                        return false;
                    }

                    let remoteOk = true;
                    if (window.api && typeof window.api.put === 'function') {
                        try {
                            const remoteRes = await window.api.put('/api/system/config', { agent_server, ai_sns_server });
                            remoteOk = !!(remoteRes && remoteRes.success);
                        } catch (e) {
                            remoteOk = false;
                        }
                    }

                    if (typeof Notification !== 'undefined') {
                        if (remoteOk && Notification.success) {
                            Notification.success('配置已保存');
                        } else if (!remoteOk && Notification.warning) {
                            Notification.warning('已保存到本地 config.json，但写入数据库失败');
                        } else if (!remoteOk && Notification.success) {
                            Notification.success('已保存到本地 config.json');
                        }
                    }

                    return true;
                } catch (e) {
                    if (typeof Notification !== 'undefined' && Notification.error) {
                        Notification.error(e.message || '保存失败');
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
            title: '帮助',
            content: `
                <div class="help-modal">
                    <h4>快捷键</h4>
                    <ul class="help-list">
                        <li><kbd>Ctrl/Cmd + B</kbd> 折叠/展开侧边栏</li>
                        <li><kbd>Ctrl/Cmd + K</kbd> 搜索</li>
                        <li><kbd>Ctrl/Cmd + ,</kbd> 设置</li>
                        <li><kbd>Ctrl/Cmd + 1-6</kbd> 快速导航</li>
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
    },

    destroy() {
        // 清理事件监听器
    }
};

export default homeHandlers;
