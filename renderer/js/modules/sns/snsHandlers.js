/**
 * SNS Module - Event Handlers
 * SNS event handling and initialization
 */

import snsState from './snsState.js';
import snsApi from './snsApi.js';
import { SNSAvatarDialog } from './SNSAvatarDialog.js';
import { SNSProfessionDialog } from './SNSProfessionDialog.js';
import { SNSSocialRoleDialog } from './SNSSocialRoleDialog.js';
import { SNSMapConfigDialog } from './SNSMapConfigDialog.js';
import { SNSPluginDialog } from './SNSPluginDialog.js';
import { SNSGoalsDialog } from './SNSGoalsDialog.js';

export default {
    lastPlaceIntroUrl: '',
    lastPlaceIntroUrl3d: '',
    lastPlaceIntroPosition: null,
    lastPlaceIntroPositionByMap: null,
    _snsLoadedRendererPlugins: new Map(),
    _suppressSnsUpdates: false,
    _snsHumanInputHistoryByMode: { ai: [], target: [] },
    _snsHumanInputHistoryIndexByMode: { ai: -1, target: -1 },

    initSNSUserInfoUpdateListener() {
        if (this._snsUserInfoUpdateListenerInitialized) return;
        this._snsUserInfoUpdateListenerInitialized = true;

        window.addEventListener('sns-user-info-updated', async (event) => {
            const detail = event && event.detail ? event.detail : {};
            if (!detail || typeof detail !== 'object') return;
            if (!('profession' in detail)) return;
            try {
                await this.refreshCurrentStatusSection();
            } catch (e) {
                console.warn('[snsHandlers] refreshCurrentStatusSection failed:', e);
            }
        });
    },

    async refreshCurrentStatusSection() {
        const processPane = document.querySelector('.tab-pane[data-tab="process"]');
        if (!processPane) return;

        const statusSection = processPane.querySelector('.status-section:nth-child(1) .status-rows');
        if (!statusSection) return;

        const overviewResp = await snsApi.getCurrentStatusOverview();
        if (overviewResp && overviewResp.success && (overviewResp.content || '').trim()) {
            this.updateCurrentStatusSection(processPane, overviewResp.content);
            return;
        }

        const userInfoResp = await snsApi.getUserInfo();
        const userStatsResp = await snsApi.getUserStats();
        const userInfo = userInfoResp && userInfoResp.success ? (userInfoResp.data || {}) : {};
        const userStats = userStatsResp && typeof userStatsResp === 'object' ? userStatsResp : {};

        const money = (userStats.money !== undefined && userStats.money !== null)
            ? Number(userStats.money)
            : Number(userInfo.money);
        const life = userStats.life;
        const energy = userStats.energy;
        const profession = userInfo.profession;

        const lines = [];
        if (Number.isFinite(money)) {
            lines.push(`💰 Money      : ${money.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
        }
        if (life !== undefined && life !== null) lines.push(`❤️ Life           : ${life}`);
        if (energy !== undefined && energy !== null) lines.push(`⚡ Energy      : ${energy}`);
        lines.push(`🧑‍️ Profession: ${profession || 'N/A'}`);
        const content = lines.join('\n');
        if (content) this.updateCurrentStatusSection(processPane, content);
    },

    resetSNSStartButtonToStart() {
        const startBtn = document.getElementById('snsStartBtn');
        if (!startBtn) return;

        try {
            startBtn.disabled = false;
        } catch (e) {
        }

        try {
            startBtn.classList.remove('running');
        } catch (e) {
        }

        try {
            startBtn.title = '';
        } catch (e) {
        }

        try {
            startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Start</span>`;
        } catch (e) {
        }
    },

    async stopEngineIfActiveForMapReload(reason = '') {
        let active = false;
        let shouldAttemptStop = false;
        try {
            const status = await snsApi.getEngineStatus();
            const taskStatus = String(status?.task_status || '').toLowerCase();
            active = !!(
                status &&
                status.success &&
                (status.running || status.started || taskStatus === 'started' || taskStatus === 'paused')
            );
            shouldAttemptStop = active;
        } catch (e) {
            console.warn('Failed to query engine status before map reload:', e);
            // Be conservative: if we cannot determine state, still try to stop with a timeout.
            shouldAttemptStop = true;
        }

        try {
            if (shouldAttemptStop) {
                console.log(`Stopping SNS engine before map reload (${reason || 'unknown'})...`);
                const timeoutMs = 3000;
                const timeoutPromise = new Promise((resolve) => {
                    setTimeout(() => resolve({ success: false, message: 'timeout' }), timeoutMs);
                });

                const stopResult = await Promise.race([snsApi.stopEngine(), timeoutPromise]);
                if (stopResult && stopResult.success === false && stopResult.message === 'timeout') {
                    console.warn(`Stop engine request timed out after ${timeoutMs}ms; continuing map reload.`);
                }
            }
        } catch (e) {
            console.warn('Failed to stop engine before map reload:', e);
        } finally {
            try {
                // Map reload implies the engine should not be running afterwards.
                // Reset UI regardless of whether stop succeeds or times out.
                this._suppressSnsUpdates = true;
                this.resetStatusPanelAfterEngineRestart('mapReloadStop');
            } catch (e) {
            }

            try {
                if (typeof this.resetSNSActionBarToDefault === 'function') {
                    this.resetSNSActionBarToDefault();
                }
            } catch (e) {
            }

            try {
                this.resetSNSStartButtonToStart();
            } catch (e) {
            }
        }
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

    _bindClickOnce(el, handler) {
        if (!el) return;
        if (el.dataset && el.dataset.snsClickBound === '1') return;
        if (el.dataset) el.dataset.snsClickBound = '1';
        el.addEventListener('click', handler);
    },

    getMapIframeTargetOrigin() {
        try {
            const iframe = document.querySelector('#mapContainer iframe');
            const src = iframe ? iframe.getAttribute('src') : '';
            if (src) {
                const u = new URL(src, window.location && window.location.href ? window.location.href : undefined);
                return u.origin;
            }
        } catch (e) {
        }
        const agentBase = (window.appConfig && window.appConfig.agent_server) ? String(window.appConfig.agent_server) : '';
        try {
            if (agentBase) {
                return new URL(agentBase).origin;
            }
        } catch (e) {
        }
        return '*';
    },

    safePostMessageToMap(iframe, message, preferredOrigin = '*') {
        if (!iframe || !iframe.contentWindow) return false;
        let origin = preferredOrigin || '*';

        try {
            // If the iframe is blocked or has opaque origin, prefer '*' to avoid mismatches.
            // Accessing contentWindow.location may throw due to cross-origin restrictions.
            const loc = iframe.contentWindow.location;
            if (loc && typeof loc.origin === 'string' && loc.origin === 'null') {
                origin = '*';
            }
        } catch (e) {
            origin = '*';
        }

        try {
            iframe.contentWindow.postMessage(message, origin);
            return true;
        } catch (e) {
            try {
                // Last resort
                iframe.contentWindow.postMessage(message, '*');
                return true;
            } catch (e2) {
                return false;
            }
        }
    },

    /**
     * Initialize SNS page
     */
    init() {
        console.log('Initializing SNS controller');
        this.loadMapIframe();
        this.loadSNSData();
        this.initCurrentStatusOnLoad();
        this.initResourceOnLoad();
        this.initSNSPanelResizer();
        this.initSNSStatusTabs();
        this.initSNSContextMenu();
        this.initSNSStatusTabReloadMenu();
        this.initSNSSearch();
        this.initSNSToolbar();
        this.initSNSSettingsPanel();
        this.initConfigButtons();
        this.initSNSActionBar();
        this.initMapReloadListener();
        this.initSNSUpdateListener();
        this.initSNSUserInfoUpdateListener();
        this.initMapReloadMessageListener();
    },

    initMapReloadMessageListener() {
        if (this._snsMapReloadMessageListenerInitialized) return;
        this._snsMapReloadMessageListenerInitialized = true;

        window.addEventListener('message', (event) => {
            const data = event && event.data;
            if (!data || typeof data !== 'object') return;
            if (data.type !== 'reloadMap') return;

            try {
                window.dispatchEvent(new CustomEvent('reloadMap'));
            } catch (e) {
            }
        });
    },

    resetStatusPanelAfterEngineRestart(reason = '') {
        const statusTabs = document.getElementById('statusTabs');
        const statusTabContent = document.getElementById('statusTabContent');
        if (!statusTabs || !statusTabContent) return;

        const keepTabs = new Set(['process', 'resource', 'think']);

        statusTabs.querySelectorAll('.status-tab').forEach((tabBtn) => {
            const key = tabBtn && tabBtn.dataset ? tabBtn.dataset.tab : '';
            if (key && !keepTabs.has(key)) {
                tabBtn.remove();
            }
        });

        statusTabContent.querySelectorAll('.tab-pane').forEach((pane) => {
            const key = pane && pane.dataset ? pane.dataset.tab : '';
            if (key && !keepTabs.has(key)) {
                pane.remove();
            }
        });

        statusTabs.querySelectorAll('.status-tab').forEach((btn) => {
            btn.classList.toggle('active', btn.dataset.tab === 'process');
        });

        statusTabContent.querySelectorAll('.tab-pane').forEach((pane) => {
            pane.classList.toggle('active', pane.dataset.tab === 'process');
        });

        const processPane = statusTabContent.querySelector('.tab-pane[data-tab="process"]');
        if (processPane) {
            const sections = processPane.querySelectorAll('.status-section .status-rows');
            sections.forEach((el) => {
                el.innerHTML = '<span class="na">N/A</span>';
            });
        }

        const resourcePane = statusTabContent.querySelector('.tab-pane[data-tab="resource"]');
        if (resourcePane) {
            const rows = resourcePane.querySelector('.status-section:nth-child(1) .status-rows');
            if (rows) rows.innerHTML = '';
        }

        const thinkPane = statusTabContent.querySelector('.tab-pane[data-tab="think"]');
        if (thinkPane) {
            const agentValue = document.getElementById('agentValue');
            const providerValue = document.getElementById('providerValue');
            const modelValue = document.getElementById('modelValue');
            if (agentValue) agentValue.textContent = ' Loading...';
            if (providerValue) providerValue.textContent = ' Loading...';
            if (modelValue) modelValue.textContent = ' Loading...';

            const logRows = thinkPane.querySelector('.status-section:nth-child(2) .status-rows');
            if (logRows) {
                logRows.innerHTML = '';
                logRows.textContent = '';
            }
            try {
                thinkPane.querySelectorAll('.thinking-log-entry').forEach((el) => el.remove());
            } catch (e) {
            }

            try {
                const nav = document.getElementById('thinkingLogNavigator');
                if (nav) nav.remove();
            } catch (e) {
            }
        }

        const searchBar = document.getElementById('statusSearchBar');
        const searchInput = document.getElementById('statusSearchInput');
        const searchResultsInfo = document.getElementById('searchResultsInfo');
        if (searchBar) searchBar.style.display = 'none';
        if (searchInput) searchInput.value = '';
        if (searchResultsInfo) searchResultsInfo.style.display = 'none';
        if (typeof this.clearSearchHighlights === 'function') {
            try {
                this.clearSearchHighlights();
            } catch (e) {
            }
        }

        this.lastPlaceIntroUrl = '';
        try {
            if (this._snsLoadedRendererPlugins && typeof this._snsLoadedRendererPlugins.clear === 'function') {
                this._snsLoadedRendererPlugins.clear();
            }
        } catch (e) {
        }

        setTimeout(() => {
            try {
                this.initCurrentStatusOnLoad();
                this.initResourceOnLoad();
                this.refreshModelInfoAfterReset();
            } catch (e) {
            }
        }, 0);
    },

    async refreshModelInfoAfterReset() {
        try {
            const result = await snsApi.getModelInfo();
            const agentValue = document.getElementById('agentValue');
            const providerValue = document.getElementById('providerValue');
            const modelValue = document.getElementById('modelValue');

            if (result && result.success && result.data) {
                const { agent, provider, model } = result.data;
                if (agentValue) agentValue.textContent = ` ${agent}`;
                if (providerValue) providerValue.textContent = ` ${provider}`;
                if (modelValue) modelValue.textContent = ` ${model}`;
                return;
            }

            if (agentValue) agentValue.textContent = ' N/A';
            if (providerValue) providerValue.textContent = ' N/A';
            if (modelValue) modelValue.textContent = ' N/A';
        } catch (e) {
            const agentValue = document.getElementById('agentValue');
            const providerValue = document.getElementById('providerValue');
            const modelValue = document.getElementById('modelValue');
            if (agentValue) agentValue.textContent = ' Error';
            if (providerValue) providerValue.textContent = ' Error';
            if (modelValue) modelValue.textContent = ' Error';
        }
    },

    async restartEngineAndResetUi(reason = '') {
        this._suppressSnsUpdates = true;
        const result = await snsApi.restartEngine();
        if (result && result.success) {
            this.resetStatusPanelAfterEngineRestart(reason);
            this._suppressSnsUpdates = false;
        } else {
            this._suppressSnsUpdates = false;
        }
        return result;
    },

    async maybeRestartEngineForMapReload(reason = '') {
        try {
            await this.stopEngineIfActiveForMapReload(reason);
            return true;
        } catch (e) {
            console.warn('Failed to stop engine for map reload:', e);
            return false;
        }
    },

    async initCurrentStatusOnLoad() {
        const processPane = document.querySelector('.tab-pane[data-tab="process"]');
        if (!processPane) return;

        const statusSection = processPane.querySelector('.status-section:nth-child(1) .status-rows');
        if (!statusSection) return;

        if (!statusSection.querySelector('.na')) return;

        try {
            const overviewResp = await snsApi.getCurrentStatusOverview();
            if (overviewResp && overviewResp.success && (overviewResp.content || '').trim()) {
                this.updateCurrentStatusSection(processPane, overviewResp.content);
                return;
            }

            const userInfoResp = await snsApi.getUserInfo();
            const userStatsResp = await snsApi.getUserStats();

            const userInfo = userInfoResp && userInfoResp.success ? (userInfoResp.data || {}) : {};
            const userStats = userStatsResp && typeof userStatsResp === 'object' ? userStatsResp : {};

            let lng = null;
            let lat = null;
            const rawPos = userInfo.current_position;
            if (rawPos) {
                if (Array.isArray(rawPos) && rawPos.length >= 2) {
                    lng = rawPos[0];
                    lat = rawPos[1];
                } else if (typeof rawPos === 'string') {
                    const trimmed = rawPos.trim();
                    try {
                        const parsed = JSON.parse(trimmed);
                        if (Array.isArray(parsed) && parsed.length >= 2) {
                            lng = parsed[0];
                            lat = parsed[1];
                        } else if (parsed && typeof parsed === 'object') {
                            lng = parsed.lng;
                            lat = parsed.lat;
                        }
                    } catch (e) {
                        const parts = trimmed.split(',').map(v => v.trim()).filter(Boolean);
                        if (parts.length >= 2) {
                            lng = parts[0];
                            lat = parts[1];
                        } else {
                            const matches = trimmed.match(/[-+]?\d*\.?\d+/g);
                            if (matches && matches.length >= 2) {
                                lng = matches[0];
                                lat = matches[1];
                            }
                        }
                    }
                } else if (typeof rawPos === 'object') {
                    lng = rawPos.lng;
                    lat = rawPos.lat;
                }
            }

            const money = (userStats.money !== undefined && userStats.money !== null)
                ? Number(userStats.money)
                : Number(userInfo.money);
            const life = userStats.life;
            const energy = userStats.energy;
            const profession = userInfo.profession;

            const lines = [];
            if (Number.isFinite(money)) {
                lines.push(`💰 Money      : ${money.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`);
            }
            if (life !== undefined && life !== null) lines.push(`❤️ Life           : ${life}`);
            if (energy !== undefined && energy !== null) lines.push(`⚡ Energy      : ${energy}`);
            lines.push(`🧑‍️ Profession: ${profession || 'N/A'}`);

            lines.push('📍 Location');
            lines.push(`   ├─ lng : ${(lng !== null && lng !== undefined && String(lng).trim() !== '') ? lng : 'N/A'}`);
            lines.push(`   └─ lat : ${(lat !== null && lat !== undefined && String(lat).trim() !== '') ? lat : 'N/A'}`);

            const content = lines.join('\n');
            if (content) this.updateCurrentStatusSection(processPane, content);
        } catch (e) {
            console.warn('[snsHandlers] initCurrentStatusOnLoad failed:', e);
            if (!this._currentStatusInitRetried) {
                this._currentStatusInitRetried = true;
                setTimeout(() => this.initCurrentStatusOnLoad(), 800);
            }
        }
    },

    async initResourceOnLoad() {
        const resourcePane = document.querySelector('.tab-pane[data-tab="resource"]');
        if (!resourcePane) return;

        const resourceSection = resourcePane.querySelector('.status-section:nth-child(1) .status-rows');
        if (!resourceSection) return;

        const text = (resourceSection.textContent || '').trim();
        const hasNAPlaceholder = !!resourceSection.querySelector('.na') || text === 'N/A';
        const hasContent = text.length > 0 && !hasNAPlaceholder;
        if (hasContent) return;

        try {
            const resp = await snsApi.getResourceOverview();
            if (!resp || !resp.success) return;
            const content = (resp.content || '').trim();
            if (!content) return;
            this.updateResourceTab(content);
        } catch (e) {
            console.warn('[snsHandlers] initResourceOnLoad failed:', e);
            if (!this._resourceInitRetried) {
                this._resourceInitRetried = true;
                setTimeout(() => this.initResourceOnLoad(), 1000);
            }
        }
    },

    initSNSStatusTabReloadMenu() {
        const statusTabs = document.getElementById('statusTabs');
        const statusTabContent = document.getElementById('statusTabContent');
        if (!statusTabs || !statusTabContent) return;

        if (this._snsTabReloadMenuInitialized) return;
        this._snsTabReloadMenuInitialized = true;

        const existingMenu = document.getElementById('snsTabReloadContextMenu');
        const menu = existingMenu || (() => {
            const el = document.createElement('div');
            el.id = 'snsTabReloadContextMenu';
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

        let currentTabKey = null;
        let removeObserver = null;

        const hideMenu = () => {
            menu.style.display = 'none';
            menu.dataset.tab = '';
            currentTabKey = null;
            if (removeObserver) {
                removeObserver.disconnect();
                removeObserver = null;
            }
        };

        const getCurrentIframeUrl = () => {
            if (!isCurrentTargetAlive()) return '';
            const pane = statusTabContent.querySelector(`.tab-pane[data-tab="${currentTabKey}"]`);
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
            if (!currentTabKey) return false;
            const tabBtn = statusTabs.querySelector(`.status-tab[data-tab="${currentTabKey}"]`);
            const pane = statusTabContent.querySelector(`.tab-pane[data-tab="${currentTabKey}"]`);
            return !!(tabBtn && pane);
        };

        const reloadCurrentIframe = () => {
            if (!isCurrentTargetAlive()) {
                hideMenu();
                return;
            }

            const pane = statusTabContent.querySelector(`.tab-pane[data-tab="${currentTabKey}"]`);
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

        statusTabs.addEventListener('contextmenu', (e) => {
            const tabBtn = e.target.closest('.status-tab');
            if (!tabBtn) return;
            if (e.target.closest('.tab-close-btn')) return;

            const tabKey = tabBtn.dataset.tab;
            if (tabKey !== 'profile' && tabKey !== 'placeIntro') return;

            e.preventDefault();
            e.stopPropagation();

            currentTabKey = tabKey;
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
            if (e.target.closest('#statusTabs .tab-close-btn')) {
                hideMenu();
            }
        });
    },

    /**
     * Destroy SNS page
     */
    destroy() {
        // Clean up event listeners
        this.cleanupMapListeners();

        // Remove SNS update listener
        if (this.snsUpdateListener) {
            window.removeEventListener('websocket-message', this.snsUpdateListener);
        }
    },

    /**
     * Initialize top toolbar collapse/expand
     */
    initSNSToolbar() {
        const toolbar = document.getElementById('snsToolbar');
        const collapseBtn = document.getElementById('toolbarCollapseBtn');
        const expandBtn = document.getElementById('toolbarExpandBtn');
        const mapArea = document.querySelector('.sns-map-area');

        if (!toolbar || !collapseBtn || !expandBtn || !mapArea) return;

        // Restore state from localStorage
        const savedCollapsed = localStorage.getItem('snsToolbarCollapsed') === 'true';
        if (savedCollapsed) {
            toolbar.classList.add('collapsed');
            mapArea.classList.add('toolbar-hidden');
        }

        // Collapse toolbar
        collapseBtn.addEventListener('click', () => {
            toolbar.classList.add('collapsed');
            mapArea.classList.add('toolbar-hidden');
            localStorage.setItem('snsToolbarCollapsed', 'true');
        });

        // Expand toolbar
        expandBtn.addEventListener('click', () => {
            toolbar.classList.remove('collapsed');
            mapArea.classList.remove('toolbar-hidden');
            localStorage.setItem('snsToolbarCollapsed', 'false');
        });
    },

    /**
     * Initialize right-side settings panel collapse/expand
     */
    initSNSSettingsPanel() {
        const panel = document.getElementById('mapSettingsPanel');
        const collapseBtn = document.getElementById('settingsCollapseBtn');
        const expandBtn = document.getElementById('settingsExpandBtn');
        const mapArea = document.querySelector('.sns-map-area');

        if (!panel || !collapseBtn || !expandBtn || !mapArea) return;

        // Restore state from localStorage
        const savedCollapsed = localStorage.getItem('snsSettingsPanelCollapsed') === 'true';
        if (savedCollapsed) {
            panel.classList.add('collapsed');
            mapArea.classList.add('settings-hidden');
        }

        // Collapse settings panel
        collapseBtn.addEventListener('click', () => {
            panel.classList.add('collapsed');
            mapArea.classList.add('settings-hidden');
            localStorage.setItem('snsSettingsPanelCollapsed', 'true');
        });

        // Expand settings panel
        expandBtn.addEventListener('click', () => {
            panel.classList.remove('collapsed');
            mapArea.classList.remove('settings-hidden');
            localStorage.setItem('snsSettingsPanelCollapsed', 'false');
        });

        // Add configuration buttons
        this.initConfigButtons();
    },

    /**
     * Initialize configuration buttons
     */
    initConfigButtons() {
        // Avatar configuration button
        const avatarBtn = document.getElementById('snsAvatarConfigBtn');
        if (avatarBtn) {
            this._bindClickOnce(avatarBtn, async () => {
                const dialog = new SNSAvatarDialog();
                await dialog.show();
            });
        }

        // Profession configuration button
        const professionBtn = document.getElementById('snsProfessionConfigBtn');
        if (professionBtn) {
            this._bindClickOnce(professionBtn, async () => {
                const dialog = new SNSProfessionDialog();
                await dialog.show();
            });
        }

        // Social role configuration button
        const socialRoleBtn = document.getElementById('snsSocialRoleConfigBtn');
        if (socialRoleBtn) {
            this._bindClickOnce(socialRoleBtn, async () => {
                const dialog = new SNSSocialRoleDialog();
                await dialog.show();
            });
        }

        // Map configuration button
        const mapConfigBtn = document.getElementById('snsMapConfigBtn');
        if (mapConfigBtn) {
            this._bindClickOnce(mapConfigBtn, async () => {
                const dialog = new SNSMapConfigDialog();
                await dialog.show();
            });
        }
    },

    /**
     * Initialize map reload listener
     */
    initMapReloadListener() {
        if (this._snsMapReloadListenerInitialized) return;
        this._snsMapReloadListenerInitialized = true;

        window.addEventListener('reloadMap', async () => {
            console.log('Received reloadMap event - reloading map iframe');

            try {
                window.dispatchEvent(new CustomEvent('sns-map-reload-start', {
                    detail: { timestamp: Date.now() }
                }));
            } catch (e) {
            }

            try {
                await this.loadMapIframe(true);
            } catch (e) {
                console.warn('Failed to reload map iframe:', e);
            }
        });
    },

    /**
     * Initialize bottom action bar
     */
    initSNSActionBar() {
        const actionBar = document.querySelector('.map-action-bar');
        if (!actionBar) return;

        const self = this;

        const refreshEngineStatusForStartButton = async () => {
            try {
                const status = await snsApi.getEngineStatus();
                if (status && typeof self.handleSNSEngineStatusUpdate === 'function') {
                    self.handleSNSEngineStatusUpdate(status);
                }
            } catch (e) {
            }
        };

        const state1 = document.getElementById('actionBarState1');
        const state2 = document.getElementById('actionBarState2');
        const controlBtn = document.getElementById('controlBtn');
        const computerBtn = document.getElementById('computerBtn');
        const appsMenuBtn = document.getElementById('appsMenuBtn');
        const mapMenuBtn = document.getElementById('mapMenuBtn');
        const appsDropdown = document.getElementById('appsDropdown');
        const mapDropdown = document.getElementById('mapDropdown');

        const resetActionBarToDefault = () => {
            try {
                // Default mode is NOT Square
                if (actionBar.dataset) {
                    actionBar.dataset.squareMode = 'false';
                }
            } catch (e) {
            }

            // Restore default layout (state 1)
            try {
                if (state1 && state2) {
                    state1.style.display = 'flex';
                    state2.style.display = 'none';
                }
            } catch (e) {
            }

            // Close dropdowns
            try {
                if (appsDropdown) appsDropdown.style.display = 'none';
                if (mapDropdown) mapDropdown.style.display = 'none';
            } catch (e) {
            }

            // Reset control toggle buttons (AI active)
            try {
                const toggleBtns = actionBar.querySelectorAll('.toggle-btn');
                toggleBtns.forEach(b => b.classList.remove('active'));
                const aiToggle = actionBar.querySelector('.toggle-btn[data-mode="ai"]');
                if (aiToggle) aiToggle.classList.add('active');
            } catch (e) {
            }

            // Reset action buttons
            try {
                const moveBtn = actionBar.querySelector('.action-btn[data-action="move"]');
                if (moveBtn) moveBtn.classList.remove('active');
            } catch (e) {
            }

            // Exit control mode in backend to keep UI and state aligned
            try {
                snsApi.setHumanControlState(false, null);
            } catch (e) {
            }

            try {
                refreshEngineStatusForStartButton();
            } catch (e) {
            }
        };

        // Expose reset for map iframe reload hook
        this.resetSNSActionBarToDefault = resetActionBarToDefault;

        // Toggle between state 1 and state 2
        const switchToState2 = () => {
            if (state1 && state2) {
                state1.style.display = 'none';
                state2.style.display = 'block';
            }

            // Enter control mode => backend human_take_over = true
            const activeToggle = actionBar.querySelector('.toggle-btn.active');
            const mode = activeToggle ? activeToggle.dataset.mode : 'ai';
            const humanTalkType = mode === 'ai' ? 0 : 1;
            snsApi.setHumanControlState(true, humanTalkType);

            try {
                refreshEngineStatusForStartButton();
            } catch (e) {
            }
        };

        const switchToState1 = () => {
            if (state1 && state2) {
                state1.style.display = 'flex';
                state2.style.display = 'none';
            }

            // Exit control mode => backend human_take_over = false
            snsApi.setHumanControlState(false, null);

            try {
                refreshEngineStatusForStartButton();
            } catch (e) {
            }
        };

        // Control button click - switch to state 2
        if (controlBtn) {
            controlBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                switchToState2();
            });
        }

        // Computer button click - switch back to state 1
        if (computerBtn) {
            computerBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                switchToState1();
            });
        }

        // Apps menu dropdown toggle
        if (appsMenuBtn && appsDropdown) {
            appsMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isVisible = appsDropdown.style.display === 'block';
                appsDropdown.style.display = isVisible ? 'none' : 'block';
                if (mapDropdown) mapDropdown.style.display = 'none';
            });
        }

        // Map menu dropdown toggle
        if (mapMenuBtn && mapDropdown) {
            mapMenuBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                const isVisible = mapDropdown.style.display === 'block';
                mapDropdown.style.display = isVisible ? 'none' : 'block';
                if (appsDropdown) appsDropdown.style.display = 'none';
            });
        }

        // Close dropdowns when clicking outside
        document.addEventListener('click', () => {
            if (appsDropdown) appsDropdown.style.display = 'none';
            if (mapDropdown) mapDropdown.style.display = 'none';
        });

        // Toggle buttons in control mode
        const toggleBtns = actionBar.querySelectorAll('.toggle-btn');
        toggleBtns.forEach(btn => {
            btn.addEventListener('click', () => {
                toggleBtns.forEach(b => b.classList.remove('active'));
                btn.classList.add('active');

                // Sync backend talk type when toggled
                const mode = btn.dataset.mode || 'ai';
                const humanTalkType = mode === 'ai' ? 0 : 1;
                // Keep take over aligned with current UI state
                const inControlState = state2 && state2.style.display !== 'none';
                snsApi.setHumanControlState(!!inControlState, humanTalkType);
            });
        });

        const getInfoPanelVisibleState = () => {
            try {
                return !!(actionBar.dataset && actionBar.dataset.infoPanelVisible === 'true');
            } catch (e) {
                return false;
            }
        };

        const setInfoPanelVisibleState = (visible) => {
            try {
                if (actionBar.dataset) {
                    actionBar.dataset.infoPanelVisible = visible ? 'true' : 'false';
                }
            } catch (e) {
            }
        };

        const getPreSquareInfoPanelVisibleState = () => {
            try {
                return !!(actionBar.dataset && actionBar.dataset.preSquareInfoPanelVisible === 'true');
            } catch (e) {
                return false;
            }
        };

        const setPreSquareInfoPanelVisibleState = (visible) => {
            try {
                if (actionBar.dataset) {
                    actionBar.dataset.preSquareInfoPanelVisible = visible ? 'true' : 'false';
                }
            } catch (e) {
            }
        };

        const setInfoPanelStateLocked = (locked) => {
            try {
                if (actionBar.dataset) {
                    actionBar.dataset.lockInfoPanelState = locked ? 'true' : 'false';
                }
            } catch (e) {
            }
        };

        const resetPreSquareInfoPanelCapture = () => {
            try {
                if (actionBar.dataset) {
                    actionBar.dataset.preSquareInfoPanelCaptured = 'false';
                }
            } catch (e) {
            }
        };

        // Action button click events
        actionBar.addEventListener('click', async (e) => {
            const btn = e.target.closest('.action-btn, .dropdown-item');
            if (!btn) return;

            const action = btn.dataset.action;
            if (!action) return;

            const inSquareMode = (() => {
                try {
                    return !!(actionBar.dataset && actionBar.dataset.squareMode === 'true');
                } catch (e) {
                    return false;
                }
            })();

            const warnSquareModeUnavailable = () => {
                const msg = 'Info is not available in Square mode. Please click AI to return to normal mode.';
                try {
                    if (window.Toast && typeof window.Toast.warning === 'function') {
                        window.Toast.warning(msg);
                        return;
                    }
                    if (window.Toast && typeof window.Toast.info === 'function') {
                        window.Toast.info(msg);
                        return;
                    }
                } catch (e) {
                }
                this.showToast(msg, 'info');
            };

            if (action === 'help') {
                // Close dropdowns after selection
                if (appsDropdown) appsDropdown.style.display = 'none';
                if (mapDropdown) mapDropdown.style.display = 'none';
                this.showHelpModal();
                return;
            }

            if (action === 'plugin') {
                // Close dropdowns after selection
                if (appsDropdown) appsDropdown.style.display = 'none';
                if (mapDropdown) mapDropdown.style.display = 'none';

                try {
                    const dialog = new SNSPluginDialog({
                        onLoad: async (plugin) => {
                            await this.loadSNSRendererPlugin(plugin);
                        },
                        onDelete: async (pluginId) => {
                            try {
                                this.unloadSNSRendererPlugin(pluginId);
                            } catch (e) {
                            }
                        }
                    });
                    await dialog.open();
                } catch (e) {
                    console.warn('Failed to open plugin dialog:', e);
                }

                return;
            }

            try {
                if (actionBar.dataset) {
                    if (action === 'square') actionBar.dataset.squareMode = 'true';
                    if (action === 'ai') actionBar.dataset.squareMode = 'false';
                }
            } catch (e) {
            }

            if (action === 'square') {
                setPreSquareInfoPanelVisibleState(getInfoPanelVisibleState());
                resetPreSquareInfoPanelCapture();
                setInfoPanelStateLocked(true);
            }
            if (action === 'ai') {
                setInfoPanelStateLocked(false);
            }

            // Active style rules:
            // - square/ai/help: never toggle active style
            // - move: toggle active style independently, not affected by others
            const isToggleSelf = action === 'move';
            if (isToggleSelf) {
                if (btn.classList.contains('action-btn')) {
                    btn.classList.toggle('active');
                } else {
                    const mainBtn = actionBar.querySelector(`.action-btn[data-action="${CSS.escape(action)}"]`);
                    if (mainBtn) {
                        mainBtn.classList.toggle('active');
                    }
                }
            } else if (action === 'square' || action === 'ai') {
                // Ensure these buttons never remain in active style
                btn.classList.remove('active');
            }

            // Close dropdowns after selection
            if (appsDropdown) appsDropdown.style.display = 'none';
            if (mapDropdown) mapDropdown.style.display = 'none';

            // Handle different actions
            console.log('SNS Action:', action);

            // Map actions to map.html button data-title
            const actionToTitleMap = {
                'home': 'home',
                'square': 'plaza',
                'ai': 'AI',
                'move': 'move'
            };

            // For actions like home/square/ai/move, post a message to the map iframe
            const mapActions = ['home', 'square', 'ai', 'move'];
            if (mapActions.includes(action)) {
                const iframe = document.querySelector('#mapContainer iframe');
                if (iframe && iframe.contentWindow) {
                    let willRestoreInfoPanel = false;
                    let captureInfoPanelState = false;
                    let setTopInfoDisabled = null;
                    if (action === 'square') {
                        // Ask iframe to capture current info panel state before it gets hidden.
                        captureInfoPanelState = true;
                        setTopInfoDisabled = true;
                    }
                    if (action === 'ai') {
                        // If user had info panel open before switching to Square, restore it when AI is clicked
                        willRestoreInfoPanel = getPreSquareInfoPanelVisibleState();
                        setTopInfoDisabled = false;
                    }
                    const message = {
                        type: 'mapButtonAction',
                        action: actionToTitleMap[action],  // Convert to the corresponding data-title
                        meta: {
                            restoreInfoPanel: willRestoreInfoPanel,
                            captureInfoPanelState: captureInfoPanelState,
                            setTopInfoDisabled: setTopInfoDisabled
                        }
                    };
                    try {
                        this.safePostMessageToMap(iframe, message, this.getMapIframeTargetOrigin());
                        console.log('Sent mapButtonAction to iframe:', message);
                    } catch (error) {
                        console.error('Failed to send message to iframe:', error);
                    }
                } else {
                    console.warn('Map iframe not found or not ready');
                }
            }
        });

        // Initialize default state
        resetActionBarToDefault();

        // Start button
        const startBtn = document.getElementById('snsStartBtn');
        if (startBtn) {
            const setStartButtonState = (state) => {
                if (state === 'start') {
                    startBtn.classList.remove('running');
                    startBtn.title = '';
                    startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Start</span>`;
                    return;
                }
                if (state === 'pause') {
                    startBtn.classList.add('running');
                    startBtn.title = '';
                    startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Pause</span>`;
                    return;
                }
                if (state === 'resume') {
                    startBtn.classList.remove('running');
                    startBtn.title = '';
                    startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Resume</span>`;
                }
            };

            const pauseEngine = async () => {
                startBtn.disabled = true;
                startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/></svg><span>Pausing...</span>`;

                try {
                    const result = await snsApi.pauseEngine();

                    if (result.success) {
                        setStartButtonState('resume');
                        this.showToast('AI social engine paused', 'success');
                    } else {
                        setStartButtonState('pause');
                        this.showToast(`Pause failed: ${result.message}`, 'error');
                    }
                } catch (error) {
                    console.error('Failed to pause engine:', error);
                    setStartButtonState('pause');
                    this.showToast(`Pause failed: ${error.message}`, 'error');
                } finally {
                    startBtn.disabled = false;
                }
            };

            const stopEngine = async () => {
                startBtn.disabled = true;
                startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/></svg><span>Stopping...</span>`;

                try {
                    this._suppressSnsUpdates = true;
                    const result = await snsApi.stopEngine();
                    if (result.success) {
                        setStartButtonState('start');
                        this.resetStatusPanelAfterEngineRestart('manualStop');
                        this.showToast('AI social engine stopped', 'success');
                    } else {
                        this._suppressSnsUpdates = false;
                        setStartButtonState('pause');
                        this.showToast(`Stop failed: ${result.message}`, 'error');
                    }
                } catch (error) {
                    console.error('Failed to stop engine:', error);
                    this._suppressSnsUpdates = false;
                    setStartButtonState('pause');
                    this.showToast(`Stop failed: ${error.message}`, 'error');
                } finally {
                    startBtn.disabled = false;
                }
            };

            const restartEngine = async () => {
                startBtn.disabled = true;
                startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/></svg><span>Restarting...</span>`;

                try {
                    const result = await this.restartEngineAndResetUi('manualRestart');
                    if (result.success) {
                        this._suppressSnsUpdates = false;
                        setStartButtonState('pause');
                        this.showToast('AI social engine restarted', 'success');
                    } else {
                        setStartButtonState('pause');
                        this.showToast(`Restart failed: ${result.message}`, 'error');
                    }
                } catch (error) {
                    console.error('Failed to restart engine:', error);
                    setStartButtonState('pause');
                    this.showToast(`Restart failed: ${error.message}`, 'error');
                } finally {
                    startBtn.disabled = false;
                }
            };

            // Right-click context menu removed from pause button

            startBtn.addEventListener('click', async () => {
                const isRunning = startBtn.classList.contains('running');
                const buttonText = startBtn.textContent.trim();

                if (!isRunning && buttonText === 'Start') {
                    // Start engine
                    this._suppressSnsUpdates = false;
                    startBtn.disabled = true;
                    startBtn.title = '';
                    startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/></svg><span>Starting...</span>`;

                    try {
                        const result = await snsApi.startEngine();

                        if (result.success) {
                            this._suppressSnsUpdates = false;
                            setStartButtonState('pause');
                            this.showToast('AI social engine started', 'success');
                        } else {
                            setStartButtonState('start');
                            this.showToast(`Start failed: ${result.message}`, 'error');
                        }
                    } catch (error) {
                        console.error('Failed to start engine:', error);
                        setStartButtonState('start');
                        this.showToast(`Start failed: ${error.message}`, 'error');
                    } finally {
                        startBtn.disabled = false;
                    }
                } else if (isRunning && buttonText === 'Pause') {
                    await pauseEngine();
                } else if (!isRunning && buttonText === 'Resume') {
                    // Resume engine
                    startBtn.disabled = true;
                    startBtn.title = '';
                    startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/></svg><span>Resuming...</span>`;

                    try {
                        const result = await snsApi.resumeEngine();

                        if (result.success) {
                            this._suppressSnsUpdates = false;
                            setStartButtonState('pause');
                            this.showToast('AI social engine resumed', 'success');
                        } else {
                            setStartButtonState('resume');
                            this.showToast(`Resume failed: ${result.message}`, 'error');
                        }
                    } catch (error) {
                        console.error('Failed to resume engine:', error);
                        setStartButtonState('resume');
                        this.showToast(`Resume failed: ${error.message}`, 'error');
                    } finally {
                        startBtn.disabled = false;
                    }
                }
            });
        }

        // Control Send button
        const sendBtn = actionBar.querySelector('.control-send-btn');
        const inputField = actionBar.querySelector('.control-input');
        if (sendBtn && inputField) {
            try {
                if (inputField.dataset && inputField.dataset.snsHumanInputEnhanced === 'true') {
                    return;
                }
                if (inputField.dataset) {
                    inputField.dataset.snsHumanInputEnhanced = 'true';
                }
            } catch (e) {
            }

            try {
                inputField.spellcheck = false;
                inputField.setAttribute('spellcheck', 'false');
                inputField.setAttribute('autocomplete', 'off');
                inputField.setAttribute('autocorrect', 'off');
                inputField.setAttribute('autocapitalize', 'off');
            } catch (e) {
            }

            const suggestionCommands = ['go around', 'talk to', 'promote to', 'buy from', 'walk to'];
            const inputWrapper = inputField.closest('.control-input-wrapper');

            let suggestionMenu = null;
            if (inputWrapper) {
                suggestionMenu = inputWrapper.querySelector('.sns-human-input-suggestions');
                if (!suggestionMenu) {
                    suggestionMenu = document.createElement('div');
                    suggestionMenu.className = 'sns-human-input-suggestions';
                    suggestionMenu.style.display = 'none';
                    suggestionMenu.setAttribute('role', 'listbox');
                    suggestionMenu.innerHTML = suggestionCommands.map((command, index) => `
                        <button
                            type="button"
                            class="sns-human-input-suggestion"
                            data-command="${command}"
                            data-index="${index}"
                            role="option"
                        >${command}</button>
                    `).join('');
                    inputWrapper.appendChild(suggestionMenu);
                }
            }

            let activeSuggestionIndex = -1;
            let draftBeforeHistoryBrowse = '';

            const getCurrentMode = () => {
                const activeToggle = actionBar.querySelector('.toggle-btn.active');
                return activeToggle ? activeToggle.dataset.mode : 'ai';
            };

            const toHistoryModeKey = (mode) => {
                return mode === 'ai' ? 'ai' : 'target';
            };

            const getHistoryModeKey = () => toHistoryModeKey(getCurrentMode());

            const ensureHistoryState = () => {
                if (!this._snsHumanInputHistoryByMode || typeof this._snsHumanInputHistoryByMode !== 'object') {
                    this._snsHumanInputHistoryByMode = { ai: [], target: [] };
                }
                if (!Array.isArray(this._snsHumanInputHistoryByMode.ai)) this._snsHumanInputHistoryByMode.ai = [];
                if (!Array.isArray(this._snsHumanInputHistoryByMode.target)) this._snsHumanInputHistoryByMode.target = [];

                if (!this._snsHumanInputHistoryIndexByMode || typeof this._snsHumanInputHistoryIndexByMode !== 'object') {
                    this._snsHumanInputHistoryIndexByMode = { ai: -1, target: -1 };
                }
                if (!Number.isFinite(this._snsHumanInputHistoryIndexByMode.ai)) this._snsHumanInputHistoryIndexByMode.ai = -1;
                if (!Number.isFinite(this._snsHumanInputHistoryIndexByMode.target)) this._snsHumanInputHistoryIndexByMode.target = -1;
            };

            const draftBeforeHistoryBrowseByMode = { ai: '', target: '' };

            const persistHistoryToDisk = async (historyModeKey) => {
                try {
                    if (!window.electronAPI || typeof window.electronAPI.writeSnsHumanInputHistory !== 'function') return;
                    ensureHistoryState();
                    const lines = this._snsHumanInputHistoryByMode[historyModeKey] || [];
                    await window.electronAPI.writeSnsHumanInputHistory(historyModeKey, lines);
                } catch (e) {
                    console.warn('[snsHandlers] Failed to persist human input history:', e);
                }
            };

            const loadHistoryFromDisk = async (historyModeKey) => {
                try {
                    if (!window.electronAPI || typeof window.electronAPI.readSnsHumanInputHistory !== 'function') return;
                    const resp = await window.electronAPI.readSnsHumanInputHistory(historyModeKey);
                    if (!resp || resp.success !== true) return;

                    const raw = (resp.data === undefined || resp.data === null) ? '' : String(resp.data);
                    const lines = raw
                        .split(/\r?\n/)
                        .map(v => String(v || '').trim())
                        .filter(v => !!v);

                    ensureHistoryState();

                    if ((this._snsHumanInputHistoryByMode[historyModeKey] || []).length) {
                        return;
                    }

                    const maxEntries = 30;
                    this._snsHumanInputHistoryByMode[historyModeKey] = lines.length > maxEntries
                        ? lines.slice(lines.length - maxEntries)
                        : lines;
                    this._snsHumanInputHistoryIndexByMode[historyModeKey] = -1;
                } catch (e) {
                    console.warn('[snsHandlers] Failed to load human input history:', e);
                }
            };

            ensureHistoryState();
            loadHistoryFromDisk('ai');
            loadHistoryFromDisk('target');

            const isMyAiMode = () => getCurrentMode() === 'ai';

            const isSuggestionVisible = () => !!(suggestionMenu && suggestionMenu.style.display !== 'none');

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
                if (!isMyAiMode()) {
                    hideSuggestionMenu();
                    return;
                }
                suggestionMenu.style.display = 'block';
                if (activeSuggestionIndex < 0) {
                    activeSuggestionIndex = 0;
                }
                updateSuggestionSelection();
            };

            const shouldShowSuggestionMenu = () => {
                if (!isMyAiMode()) return false;
                return inputField.value === '@';
            };

            const applySuggestion = (command) => {
                inputField.value = `${command} `;
                hideSuggestionMenu();
                inputField.focus();
                try {
                    const pos = inputField.value.length;
                    inputField.setSelectionRange(pos, pos);
                } catch (e) {
                }
            };

            const syncSuggestionMenu = () => {
                if (shouldShowSuggestionMenu()) {
                    showSuggestionMenu();
                } else {
                    hideSuggestionMenu();
                }
            };

            const resetHistoryBrowse = (historyModeKey) => {
                ensureHistoryState();
                const key = historyModeKey || getHistoryModeKey();
                this._snsHumanInputHistoryIndexByMode[key] = -1;
                draftBeforeHistoryBrowseByMode[key] = inputField.value;
            };

            const browseHistory = (direction) => {
                ensureHistoryState();
                const key = getHistoryModeKey();
                const history = this._snsHumanInputHistoryByMode[key] || [];
                if (!history.length) return;

                if (this._snsHumanInputHistoryIndexByMode[key] === -1) {
                    draftBeforeHistoryBrowseByMode[key] = inputField.value;
                }

                if (direction < 0) {
                    const nextIndex = this._snsHumanInputHistoryIndexByMode[key] === -1
                        ? history.length - 1
                        : Math.max(0, this._snsHumanInputHistoryIndexByMode[key] - 1);
                    this._snsHumanInputHistoryIndexByMode[key] = nextIndex;
                    inputField.value = history[nextIndex];
                } else {
                    if (this._snsHumanInputHistoryIndexByMode[key] === -1) return;
                    const nextIndex = this._snsHumanInputHistoryIndexByMode[key] + 1;
                    if (nextIndex >= history.length) {
                        this._snsHumanInputHistoryIndexByMode[key] = -1;
                        inputField.value = draftBeforeHistoryBrowseByMode[key] || '';
                    } else {
                        this._snsHumanInputHistoryIndexByMode[key] = nextIndex;
                        inputField.value = history[nextIndex];
                    }
                }

                hideSuggestionMenu();
                try {
                    const pos = inputField.value.length;
                    inputField.setSelectionRange(pos, pos);
                } catch (e) {
                }
            };

            const pushHistory = (message) => {
                ensureHistoryState();
                const key = getHistoryModeKey();
                const history = this._snsHumanInputHistoryByMode[key] || [];

                if (!history.length || history[history.length - 1] !== message) {
                    history.push(message);
                }

                const maxEntries = 30;
                if (history.length > maxEntries) {
                    this._snsHumanInputHistoryByMode[key] = history.slice(history.length - maxEntries);
                } else {
                    this._snsHumanInputHistoryByMode[key] = history;
                }

                this._snsHumanInputHistoryIndexByMode[key] = -1;
                draftBeforeHistoryBrowseByMode[key] = '';

                persistHistoryToDisk(key);
            };

            const handleSend = async () => {
                const message = inputField.value.trim();
                if (!message) return;

                pushHistory(message);

                const mode = getCurrentMode();

                // Clear input field
                inputField.value = '';
                hideSuggestionMenu();

                try {
                    // Ensure backend state matches UI at send time.
                    // When mode is "friends", backend will route to XmppMixin.sendMessage(content, by_click=True).
                    const humanTalkType = mode === 'ai' ? 0 : 1;
                    await snsApi.setHumanControlState(true, humanTalkType);

                    const result = await snsApi.sendHumanMessage(message);

                    if (!result.success) {
                        const backendMsg = String(result.message || '').trim();
                        if (backendMsg === 'Message send failed: no active conversation.') {
                            this.showToast(backendMsg, 'warning');
                        } else {
                            this.showToast(`Error: ${backendMsg || 'Unknown error'}`, 'error');
                        }
                    }
                } catch (error) {
                    console.error('Failed to send control message:', error);
                    this.showToast(`Send failed: ${error.message}`, 'error');
                }
            };

            sendBtn.addEventListener('click', handleSend);

            if (suggestionMenu) {
                suggestionMenu.addEventListener('click', (event) => {
                    const suggestionButton = event.target.closest('.sns-human-input-suggestion');
                    if (!suggestionButton) return;
                    applySuggestion(suggestionButton.dataset.command || '');
                });
            }

            inputField.addEventListener('input', () => {
                ensureHistoryState();
                const key = getHistoryModeKey();
                this._snsHumanInputHistoryIndexByMode[key] = -1;
                draftBeforeHistoryBrowseByMode[key] = inputField.value;
                syncSuggestionMenu();
            });

            inputField.addEventListener('focus', () => {
                syncSuggestionMenu();
            });

            inputField.addEventListener('blur', () => {
                setTimeout(() => {
                    hideSuggestionMenu();
                }, 120);
            });

            inputField.addEventListener('keydown', (e) => {
                if (e.key === 'ArrowUp') {
                    if (isSuggestionVisible()) {
                        e.preventDefault();
                        activeSuggestionIndex = activeSuggestionIndex <= 0 ? suggestionCommands.length - 1 : activeSuggestionIndex - 1;
                        updateSuggestionSelection();
                        return;
                    }
                    e.preventDefault();
                    browseHistory(-1);
                    return;
                }

                if (e.key === 'ArrowDown') {
                    if (isSuggestionVisible()) {
                        e.preventDefault();
                        activeSuggestionIndex = activeSuggestionIndex >= suggestionCommands.length - 1 ? 0 : activeSuggestionIndex + 1;
                        updateSuggestionSelection();
                        return;
                    }
                    e.preventDefault();
                    browseHistory(1);
                    return;
                }

                if (e.key === 'Escape' && isSuggestionVisible()) {
                    e.preventDefault();
                    hideSuggestionMenu();
                    return;
                }

                if (e.key === 'Enter') {
                    if (isSuggestionVisible() && activeSuggestionIndex >= 0) {
                        e.preventDefault();
                        applySuggestion(suggestionCommands[activeSuggestionIndex]);
                        return;
                    }
                    e.preventDefault();
                    handleSend();
                }
            });

            toggleBtns.forEach(btn => {
                btn.addEventListener('click', () => {
                    hideSuggestionMenu();
                    resetHistoryBrowse(toHistoryModeKey(btn.dataset.mode || 'ai'));
                });
            });

            document.addEventListener('click', (event) => {
                if (inputWrapper && inputWrapper.contains(event.target)) return;
                hideSuggestionMenu();
            });
        }
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
                    <h4>Shortcuts</h4>
                    <ul class="help-list">
                        <li><kbd>Ctrl/Cmd + B</kbd> Toggle sidebar</li>
                        <li><kbd>Ctrl/Cmd + K</kbd> Search</li>
                        <li><kbd>Ctrl/Cmd + ,</kbd> Settings</li>
                        <li><kbd>Ctrl/Cmd + 1-6</kbd> Quick navigation</li>
                    </ul>
                    <h4>Modules</h4>
                    <ul class="help-list">
                        <li><strong>SNS</strong> - Map social exploration</li>
                        <li><strong>Agent</strong> - AI agent chat</li>
                        <li><strong>KM</strong> - Knowledge base management</li>
                        <li><strong>Tools</strong> - Plugin tools</li>
                        <li><strong>Web</strong> - LLM online services</li>
                        <li><strong>Home</strong> - Home page settings</li>
                    </ul>
                </div>
            `,
            showCancel: false,
            confirmText: 'Close'
        });
    },

    /**
     * Initialize right-side panel collapse/expand
     */
    initSNSPanelResizer() {
        const resizer = document.getElementById('snsPanelResizer');
        const collapseBtn = document.getElementById('snsPanelCollapseBtn');
        const statusPanel = document.getElementById('snsStatusPanel');

        if (!resizer || !collapseBtn || !statusPanel) return;

        // Restore panel state from localStorage
        const savedCollapsed = localStorage.getItem('snsPanelCollapsed') === 'true';
        if (savedCollapsed) {
            resizer.classList.add('collapsed');
            statusPanel.classList.add('collapsed');
        }

        // Collapse/expand button click event
        collapseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isCollapsed = statusPanel.classList.toggle('collapsed');
            resizer.classList.toggle('collapsed', isCollapsed);
            localStorage.setItem('snsPanelCollapsed', isCollapsed);
        });

        // Drag to resize panel width
        let isResizing = false;
        let startX = 0;
        let startWidth = 0;

        resizer.addEventListener('mousedown', (e) => {
            if (e.target === collapseBtn || collapseBtn.contains(e.target)) return;
            if (statusPanel.classList.contains('collapsed')) return;

            isResizing = true;
            startX = e.clientX;
            startWidth = statusPanel.offsetWidth;
            resizer.classList.add('resizing');
            document.body.style.cursor = 'col-resize';
            document.body.style.userSelect = 'none';

            // Disable iframe pointer events to avoid lag while dragging
            const iframes = document.querySelectorAll('iframe');
            iframes.forEach(iframe => {
                iframe.style.pointerEvents = 'none';
            });

            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            // Drag left to increase width; drag right to decrease width
            const deltaX = startX - e.clientX;
            const minPanelWidth = 200;
            const minMapWidth = 0;
            const layout = document.querySelector('.sns-page-layout');
            const layoutWidth = layout ? layout.getBoundingClientRect().width : window.innerWidth;
            const resizerWidth = resizer.getBoundingClientRect().width || 8;
            const maxPanelWidth = Math.max(minPanelWidth, Math.floor(layoutWidth - resizerWidth - minMapWidth));
            let newWidth = Math.max(minPanelWidth, Math.min(maxPanelWidth, startWidth + deltaX));
            if (newWidth > maxPanelWidth - 1) newWidth = maxPanelWidth;
            statusPanel.style.width = `${newWidth}px`;
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';

                // Restore iframe pointer events
                const iframes = document.querySelectorAll('iframe');
                iframes.forEach(iframe => {
                    iframe.style.pointerEvents = '';
                });
            }
        });
    },

    /**
     * Initialize status tab switching
     */
    initSNSStatusTabs() {
        const tabsContainer = document.getElementById('statusTabs');
        const tabContent = document.getElementById('statusTabContent');

        if (!tabsContainer || !tabContent) return;

        // Store scroll position for each tab
        const scrollPositions = {};

        const getActiveTab = () => {
            const activeBtn = tabsContainer.querySelector('.status-tab.active');
            return activeBtn ? activeBtn.dataset.tab : null;
        };

        const saveScrollPosition = (tab) => {
            if (!tab) return;
            scrollPositions[tab] = tabContent.scrollTop;
        };

        const restoreScrollPosition = (tab) => {
            if (!tab) return;
            const pos = scrollPositions[tab];
            tabContent.scrollTop = typeof pos === 'number' ? pos : 0;
        };

        const ensureTabButtonVisible = (tabBtn) => {
            if (!tabBtn) return;
            const containerRect = tabsContainer.getBoundingClientRect();
            const btnRect = tabBtn.getBoundingClientRect();

            // Only adjust horizontal scroll of the tabs bar; do not trigger vertical scroll.
            if (btnRect.left < containerRect.left) {
                tabsContainer.scrollLeft -= (containerRect.left - btnRect.left) + 16;
            } else if (btnRect.right > containerRect.right) {
                tabsContainer.scrollLeft += (btnRect.right - containerRect.right) + 16;
            }
        };

        // Tab switching event
        tabsContainer.addEventListener('click', (e) => {
            const tabBtn = e.target.closest('.status-tab');
            if (!tabBtn) return;

            const targetTab = tabBtn.dataset.tab;
            if (!targetTab) return;

            // Save scroll position for the currently active tab
            const currentTab = getActiveTab();
            saveScrollPosition(currentTab);

            // Update active tab button state
            tabsContainer.querySelectorAll('.status-tab').forEach(btn => {
                btn.classList.toggle('active', btn === tabBtn);
            });

            // Switch content panes
            tabContent.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.toggle('active', pane.dataset.tab === targetTab);
            });

            // Restore scroll position for target tab
            requestAnimationFrame(() => {
                restoreScrollPosition(targetTab);
                try {
                    if (typeof this.ensureThinkingLogNavigator === 'function') {
                        this.ensureThinkingLogNavigator();
                    }
                } catch (e) {
                }
            });

            // Only adjust horizontal scroll of the tab buttons container; do not affect content area
            ensureTabButtonVisible(tabBtn);
        });

        // Detect scroll state and add gradient indicators
        const updateScrollIndicators = () => {
            const scrollLeft = tabsContainer.scrollLeft;
            const scrollWidth = tabsContainer.scrollWidth;
            const clientWidth = tabsContainer.clientWidth;
            const maxScroll = scrollWidth - clientWidth;

            // Add/remove scroll indicator classes
            if (scrollLeft > 5) {
                tabsContainer.classList.add('can-scroll-left');
            } else {
                tabsContainer.classList.remove('can-scroll-left');
            }

            if (scrollLeft < maxScroll - 5) {
                tabsContainer.classList.add('can-scroll-right');
            } else {
                tabsContainer.classList.remove('can-scroll-right');
            }
        };

        // Listen for scroll events
        tabsContainer.addEventListener('scroll', updateScrollIndicators);

        // Listen for window resize
        const resizeObserver = new ResizeObserver(updateScrollIndicators);
        resizeObserver.observe(tabsContainer);

        // Initial check
        setTimeout(updateScrollIndicators, 100);
    },

    /**
     * Initialize context menu
     */
    initSNSContextMenu() {
        const tabContent = document.getElementById('statusTabContent');
        const contextMenu = document.getElementById('statusContextMenu');
        const searchBar = document.getElementById('statusSearchBar');
        const searchInput = document.getElementById('statusSearchInput');

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
                console.warn('[snsHandlers] electron clipboard copy failed, falling back', e);
            }

            try {
                if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                    await navigator.clipboard.writeText(v);
                    return { success: true };
                }
            } catch (e) {
                console.warn('[snsHandlers] navigator.clipboard copy failed, falling back', e);
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

        if (!tabContent || !contextMenu) return;

        // Prevent default context menu
        tabContent.addEventListener('contextmenu', (e) => {
            e.preventDefault();

            // Show custom context menu
            contextMenu.style.display = 'block';

            // Calculate menu position
            const menuWidth = 180;
            const menuHeight = 120;
            const viewportWidth = window.innerWidth;
            const viewportHeight = window.innerHeight;

            let x = e.clientX;
            let y = e.clientY;

            // Prevent menu from overflowing the viewport
            if (x + menuWidth > viewportWidth) {
                x = viewportWidth - menuWidth - 10;
            }
            if (y + menuHeight > viewportHeight) {
                y = viewportHeight - menuHeight - 10;
            }

            contextMenu.style.left = x + 'px';
            contextMenu.style.top = y + 'px';
        });

        // Click outside to close menu
        document.addEventListener('click', (e) => {
            if (!contextMenu.contains(e.target)) {
                contextMenu.style.display = 'none';
            }
        });

        // Menu item click event
        contextMenu.addEventListener('click', (e) => {
            const menuItem = e.target.closest('.context-menu-item');
            if (!menuItem) return;

            const action = menuItem.dataset.action;
            const activePane = tabContent.querySelector('.tab-pane.active');

            switch (action) {
                case 'copy':
                    // Copy selected text
                    const selectedText = window.getSelection().toString();
                    if (selectedText) {
                        copyTextToClipboard(selectedText).then((r) => {
                            if (r && r.success) {
                                console.log('[snsHandlers] text copied to clipboard');
                                return;
                            }
                            const errMsg = r && r.error ? String(r.error) : 'Unknown error';
                            console.error('[snsHandlers] clipboard copy failed:', errMsg);
                        }).catch(err => {
                            console.error('[snsHandlers] clipboard copy failed:', err);
                        });
                    }
                    break;

                case 'selectAll':
                    // Select all text in current tab
                    if (activePane) {
                        const range = document.createRange();
                        range.selectNodeContents(activePane);
                        const selection = window.getSelection();
                        selection.removeAllRanges();
                        selection.addRange(range);
                    }
                    break;

                case 'search':
                    // Show search bar
                    if (searchBar) {
                        searchBar.style.display = 'flex';
                        // Focus the search input
                        setTimeout(() => {
                            if (searchInput) {
                                searchInput.focus();
                                // If there is selected text, auto-fill it into the search input
                                const selectedText = window.getSelection().toString();
                                if (selectedText) {
                                    searchInput.value = selectedText;
                                }
                            }
                        }, 100);
                    }
                    break;
            }

            // Close menu
            contextMenu.style.display = 'none';
        });

        // Close menu on ESC
        document.addEventListener('keydown', (e) => {
            if (e.key === 'Escape') {
                contextMenu.style.display = 'none';
            }
        });
    },

    /**
     * Initialize status panel search
     */
    initSNSSearch() {
        const searchInput = document.getElementById('statusSearchInput');
        const searchClear = document.getElementById('statusSearchClear');
        const searchResultsInfo = document.getElementById('searchResultsInfo');
        const searchResultsText = document.getElementById('searchResultsText');
        const searchPrevBtn = document.getElementById('searchPrevBtn');
        const searchNextBtn = document.getElementById('searchNextBtn');
        const tabContent = document.getElementById('statusTabContent');

        if (!searchInput || !tabContent) return;

        let currentMatches = [];
        let currentMatchIndex = -1;
        let _searchJobToken = 0;
        let _lastSearchedText = '';
        let _pendingNavigate = null;

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

            Array.from(activePane.querySelectorAll('.status-section-title')).forEach(pushUnique);

            const thinkingEntries = Array.from(activePane.querySelectorAll('.thinking-log-entry'));
            thinkingEntries.forEach(pushUnique);

            const statusRows = Array.from(activePane.querySelectorAll('.status-row'));
            statusRows.forEach(pushUnique);

            const preBlocks = Array.from(activePane.querySelectorAll('pre'));
            preBlocks.forEach(pushUnique);

            const rowsContainers = Array.from(activePane.querySelectorAll('.status-rows'));
            rowsContainers.forEach((c) => {
                if (!c) return;
                const hasThinkingEntries = c.querySelector('.thinking-log-entry');
                const hasRows = c.querySelector('.status-row');
                const hasPre = c.querySelector('pre');
                if (!hasThinkingEntries && !hasRows && !hasPre) pushUnique(c);
            });

            if (blocks.length > 0) return blocks;

            const sections = Array.from(activePane.querySelectorAll('.status-section'));
            if (sections.length > 0) return sections;

            try {
                const children = Array.from(activePane.children || []).filter(Boolean);
                if (children.length > 0) return children;
            } catch (e) {
            }

            return [activePane];
        };

        const buildMatchesAsync = (searchText) => {
            const token = _searchJobToken;
            clearLocalSearchState();

            const raw = (searchText === undefined || searchText === null) ? '' : String(searchText);
            const normalized = raw.trim();
            _lastSearchedText = normalized;

            if (!normalized) {
                if (searchResultsInfo) searchResultsInfo.style.display = 'none';
                return;
            }

            const activePane = tabContent.querySelector('.tab-pane.active');
            if (!activePane) return;

            const blocks = getSearchBlocks(activePane);
            const query = normalized.toLowerCase();
            const maxMatches = 2000;

            if (searchResultsInfo) searchResultsInfo.style.display = 'flex';
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

                if (searchResultsInfo) searchResultsInfo.style.display = 'flex';
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
                    this.scrollToMatch(currentMatchIndex);
                } else {
                    if (searchResultsText) searchResultsText.textContent = 'No results found';
                    currentMatchIndex = -1;
                }
            };

            requestAnimationFrame(processBatch);
        };

        this.clearSearchHighlights = () => {
            cancelActiveSearchJob();
            clearLocalSearchState();
            _lastSearchedText = '';
            _pendingNavigate = null;
            clearSelectionHighlight();
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

        this.scrollToMatch = (index) => {
            if (index < 0 || index >= currentMatches.length) return;

            const match = currentMatches[index];
            const el = match && match.el;
            if (!el) return;

            // Build a Range for the matched text so we can scroll precisely to it
            const q = String(_lastSearchedText || '');
            const start = Number(match.start);
            const end = start + q.length;
            const range = (q && Number.isFinite(start) && start >= 0)
                ? createRangeFromTextOffsets(el, start, end)
                : null;

            if (range) {
                // Use the Range bounding rect to scroll the matched text into view
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

                // Highlight via native Selection
                requestAnimationFrame(() => {
                    highlightCurrentMatch(match);
                });
            } else if (typeof el.scrollIntoView === 'function') {
                // Fallback: scroll the block element into view
                el.scrollIntoView({ behavior: 'smooth', block: 'center' });
            }

            if (searchResultsText) {
                searchResultsText.textContent = `${index + 1} / ${currentMatches.length}`;
            }
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

        searchInput.addEventListener('input', () => {
            cancelActiveSearchJob();
            clearLocalSearchState();
            if (searchResultsInfo) searchResultsInfo.style.display = 'none';
        });

        // Clear button - clear search and close search bar
        searchClear.addEventListener('click', () => {
            searchInput.value = '';
            this.clearSearchHighlights();
            searchResultsInfo.style.display = 'none';
            // Hide search bar
            const searchBar = document.getElementById('statusSearchBar');
            if (searchBar) {
                searchBar.style.display = 'none';
            }
        });

        // Previous result
        searchPrevBtn.addEventListener('click', () => {
            if (ensureSearchAndNavigate('prev')) return;
            if (currentMatches.length === 0) return;
            currentMatchIndex = (currentMatchIndex - 1 + currentMatches.length) % currentMatches.length;
            this.scrollToMatch(currentMatchIndex);
        });

        // Next result
        searchNextBtn.addEventListener('click', () => {
            if (ensureSearchAndNavigate('next')) return;
            if (currentMatches.length === 0) return;
            currentMatchIndex = (currentMatchIndex + 1) % currentMatches.length;
            this.scrollToMatch(currentMatchIndex);
        });

        // Keyboard shortcut support
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
                    this.scrollToMatch(currentMatchIndex);
                    return;
                }

                if (ensureSearchAndNavigate('next')) return;
                if (currentMatches.length === 0) {
                    ensureSearchAndNavigate('next');
                    return;
                }
                currentMatchIndex = (currentMatchIndex + 1) % currentMatches.length;
                this.scrollToMatch(currentMatchIndex);
            } else if (e.key === 'Escape') {
                searchClear.click();
            }
        });

        const closeSearchUI = () => {
            cancelActiveSearchJob();
            clearLocalSearchState();
            clearSelectionHighlight();
            _lastSearchedText = '';
            _pendingNavigate = null;
            if (searchResultsInfo) searchResultsInfo.style.display = 'none';
            const searchBar = document.getElementById('statusSearchBar');
            if (searchBar) searchBar.style.display = 'none';
            searchInput.value = '';
        };

        // Clear search and hide search bar when switching tabs
        const tabsContainer = document.getElementById('statusTabs');
        if (tabsContainer) {
            tabsContainer.addEventListener('click', (e) => {
                if (e.target.closest('.status-tab')) {
                    closeSearchUI();
                }
            });
        }

        let _lastActivePaneKey = null;
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
    },

    /**
     * Load Baidu map
     */
    async loadMapIframe(forceReload = false) {
        const mapContainer = document.getElementById('mapContainer');
        if (!mapContainer) {
            console.error('Map container not found');
            return;
        }

        const normalizeHttpBaseUrl = (raw) => {
            const v = String(raw || '').trim();
            if (!v) return '';
            const withScheme = /^https?:\/\//i.test(v) ? v : `http://${v}`;
            return withScheme.endsWith('/') ? withScheme.slice(0, -1) : withScheme;
        };

        const getAgentServerBaseUrl = () => {
            const v = (window.appConfig && window.appConfig.agent_server)
                || (window.api && window.api.baseUrl)
                || '';
            return normalizeHttpBaseUrl(v);
        };

        const getAiSnsServerBaseUrl = () => {
            const v = (window.appConfig && window.appConfig.ai_sns_server) || '';
            return normalizeHttpBaseUrl(v);
        };

        console.log('Loading map iframe');

        // Show map content immediately (no loading animation)
        const placeholder = mapContainer.querySelector('.map-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // Check whether the map has already been loaded
        const existingIframe = mapContainer.querySelector('iframe');
        if (existingIframe) {
            if (!forceReload) {
                console.log('Map iframe already exists, skipping reload');
                return;
            }

            try {
                await this.stopEngineIfActiveForMapReload('mapIframeReload');
            } catch (e) {
            }

            console.log('Reloading map iframe');
            try {
                if (existingIframe._messageListener) {
                    window.removeEventListener('message', existingIframe._messageListener);
                }
            } catch (e) {
            }
            try {
                existingIframe.remove();
            } catch (e) {
            }
        }

        // Ensure we do not leak window message listeners across iframe reloads
        if (this._mapMessageListener) {
            try {
                window.removeEventListener('message', this._mapMessageListener);
            } catch (e) {
            }
            this._mapMessageListener = null;
        }

        const agentBaseUrl = getAgentServerBaseUrl();
        const aiSnsBaseUrl = getAiSnsServerBaseUrl();

        const qs = new URLSearchParams();
        if (agentBaseUrl) {
            qs.set('agent_server', agentBaseUrl);
        }
        if (aiSnsBaseUrl) {
            qs.set('ai_sns_server', aiSnsBaseUrl);
        }

        const buildMapUrlByType = (mapType) => {
            const t = String(mapType || '').trim();
            if (t === '0') {
                return agentBaseUrl
                    ? `${agentBaseUrl}/scripts/googlemap3d.html?${qs.toString()}`
                    : `/scripts/googlemap3d.html?${qs.toString()}`;
            }
            return agentBaseUrl
                ? `${agentBaseUrl}/scripts/map.html?${qs.toString()}`
                : `/scripts/map.html?${qs.toString()}`;
        };

        let cachedMapType = '';
        try {
            const v = localStorage.getItem('sns_map_type');
            cachedMapType = (v === null || v === undefined || String(v).trim() === '') ? '0' : String(v).trim();
        } catch (e) {
            cachedMapType = '0';
        }

        // Start loading immediately (do not block on map-config)
        let mapUrl = buildMapUrlByType(cachedMapType);

        // Create iframe to load the map page
        const iframe = document.createElement('iframe');
        iframe.src = mapUrl;
        iframe.style.transform = 'scale(0.8)';
        iframe.style.transformOrigin = '0 0';
        iframe.style.width = '125%';//because scale(0.8)
        iframe.style.height = '125%';
        iframe.style.border = 'none';
        iframe.style.display = 'block';
        iframe.style.backgroundColor = 'white';
        iframe.style.minHeight = '500px';
        iframe.style.zIndex = '1';

        mapContainer.appendChild(iframe);

        // Fetch map configuration asynchronously (best-effort, short timeout)
        Promise.resolve().then(async () => {
            try {
                const controller = (typeof AbortController !== 'undefined') ? new AbortController() : null;
                const timeoutMs = 1200;
                let timeoutId = null;
                if (controller) {
                    timeoutId = setTimeout(() => {
                        try {
                            controller.abort();
                        } catch (e) {
                        }
                    }, timeoutMs);
                }

                const response = await fetch(
                    agentBaseUrl ? `${agentBaseUrl}/api/sns/map-config` : '/api/sns/map-config',
                    controller ? { signal: controller.signal } : undefined
                );
                if (timeoutId) {
                    clearTimeout(timeoutId);
                }
                const result = await response.json();

                console.log('Map config API response:', result);

                if (result && result.success && result.data) {
                    const mapType = String(result.data.map_type).trim();
                    try {
                        localStorage.setItem('sns_map_type', mapType);
                    } catch (e) {
                    }

                    const desiredUrl = buildMapUrlByType(mapType);
                    if (desiredUrl && desiredUrl !== mapUrl) {
                        console.log('Switching map URL after config fetch:', desiredUrl);
                        try {
                            await this.stopEngineIfActiveForMapReload('mapTypeSwitch');
                        } catch (e) {
                        }
                        mapUrl = desiredUrl;
                        try {
                            if (iframe && !iframe.isConnected) {
                                return;
                            }
                            iframe.src = mapUrl;
                        } catch (e) {
                        }
                    }
                }
            } catch (error) {
                console.warn('Failed to fetch map config (non-blocking):', error);
            }
        });

        console.log('Final map URL:', mapUrl);

        // Establish communication after iframe finishes loading
        iframe.onload = () => {
            console.log('Map page loaded');

            try {
                this._suppressSnsUpdates = false;
            } catch (e) {
            }

            try {
                window.dispatchEvent(new CustomEvent('sns-map-iframe-loaded', {
                    detail: {
                        url: mapUrl,
                        timestamp: Date.now()
                    }
                }));
            } catch (e) {
            }

            try {
                if (typeof this.resetSNSActionBarToDefault === 'function') {
                    this.resetSNSActionBarToDefault();
                }
            } catch (e) {
            }

            let targetOrigin = '*';
            try {
                targetOrigin = new URL(mapUrl).origin;
            } catch (e) {
            }

            // Send initial data to iframe
            const initialData = {
                type: 'init',
                data: {
                    message: 'Hello from AI-SNS Electron App!',
                    timestamp: Date.now()
                }
            };

            try {
                this.safePostMessageToMap(iframe, initialData, targetOrigin);
                console.log('Initialization message sent');
            } catch (error) {
                console.error('Failed to send message to map iframe:', error);
            }
        };

        // Listen for iframe load failure
        iframe.onerror = () => {
            console.error('Map page failed to load');

            try {
                this._suppressSnsUpdates = false;
            } catch (e) {
            }

            this.showMapError(mapContainer);
        };

        // Listen for messages from the iframe
        const handleMessage = (event) => {
            // If we have a reference to the iframe, ensure message is from it.
            try {
                if (iframe && iframe.contentWindow && event.source !== iframe.contentWindow) {
                    return;
                }
            } catch (e) {
            }

            let expectedOrigin = '';
            try {
                expectedOrigin = new URL(mapUrl).origin;
            } catch (e) {
            }

            if (!expectedOrigin || event.origin === expectedOrigin) {
                const data = event.data;
                console.log('Received message from map iframe:', data);

                switch (data.type) {
                    case 'received':
                        console.log('Map page receive message:', data.data);
                        break;
                    case 'reloadMap':
                        // Handled by the global reloadMap listener
                        break;
                    case 'infoPanelState':
                        try {
                            const actionBar = document.querySelector('.map-action-bar');
                            if (actionBar && actionBar.dataset) {
                                const lock = actionBar.dataset.lockInfoPanelState === 'true';
                                const alreadyCaptured = actionBar.dataset.preSquareInfoPanelCaptured === 'true';

                                if (!lock) {
                                    actionBar.dataset.infoPanelVisible = data.visible ? 'true' : 'false';
                                } else {
                                    // In Square mode we keep the "preSquare" snapshot stable, and do not allow
                                    // map-side UI changes (which may be forced) to override the restore target.
                                    if (!alreadyCaptured) {
                                        actionBar.dataset.preSquareInfoPanelVisible = data.visible ? 'true' : 'false';
                                        actionBar.dataset.preSquareInfoPanelCaptured = 'true';
                                    }
                                }
                            }
                        } catch (e) {
                        }
                        break;
                    case 'locationUpdate':
                        this.handleLocationUpdate(data.data);
                        break;
                    case 'mapClick':
                        this.handleMapClick(data.data);
                        break;
                    case 'markerAdd':
                        this.handleMarkerAdd(data.data);
                        break;
                    case 'openDialog':
                        this.handleOpenDialog(data.dialogType);
                        break;
                    case 'togglePanels':
                        this.handleTogglePanels(data.action);
                        break;
                    case 'openSNSProfile':
                        this.handleOpenSNSProfile(data.url);
                        break;
                    case 'openPlaceWebAddress':
                        this.handleOpenPlaceWebAddress(data.url, data.url_3d, data.place_position, data.place_position_by_map);
                        break;
                    case 'openUrl':
                        this.handleOpenUrl(data.url);
                        break;
                    case 'closeSNSProfile':
                        this.handleCloseSNSProfile();
                        break;
                    case 'snsUserMeta':
                        try {
                            const meta = (data && data.data && typeof data.data === 'object') ? data.data : {};
                            const nickname = meta.nickname;
                            const membership = meta.membership;
                            const level = meta.level;

                            try {
                                window.dispatchEvent(new CustomEvent('sns-user-info-updated', {
                                    detail: {
                                        nickname: nickname,
                                        membership: membership,
                                        level: level,
                                    }
                                }));
                            } catch (e) {
                            }

                            const payload = {};
                            if (membership !== undefined) payload.membership = membership;
                            if (level !== undefined) payload.level = level;
                            if (nickname !== undefined) payload.nickname = nickname;

                            if (Object.keys(payload).length > 0) {
                                snsApi.updateUserInfo(payload).catch(() => null);
                            }
                        } catch (e) {
                        }
                        break;
                    default:
                        console.log('Unknown message type:', data.type);
                }
            }
        };

        window.addEventListener('message', handleMessage);
        this._mapMessageListener = handleMessage;
        iframe._messageListener = handleMessage;
    },

    /**
     * Show map loading error
     */
    showMapError(mapContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'map-placeholder';
        errorDiv.style.zIndex = '10';

        const agentServer = (window.appConfig && window.appConfig.agent_server)
            || (window.api && window.api.baseUrl)
            || '';
        errorDiv.innerHTML = `
            <div class="map-placeholder-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/>
                </svg>
            </div>
            <p class="map-placeholder-text">Map failed to load</p>
            <p class="map-placeholder-desc">Please check whether the map server is running${agentServer ? ` at ${agentServer}` : ''}</p>
            <button class="map-retry-btn" id="mapRetryBtn">Retry</button>
        `;
        mapContainer.appendChild(errorDiv);

        // Bind retry button
        const retryBtn = errorDiv.querySelector('#mapRetryBtn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.tryLoadMap());
        }
    },

    /**
     * Retry loading map
     */
    async tryLoadMap() {
        const mapContainer = document.getElementById('mapContainer');
        if (!mapContainer) return;

        console.log('Retrying map iframe load');

        // Remove existing iframe
        const existingIframe = mapContainer.querySelector('iframe');
        if (existingIframe) {
            if (existingIframe._messageListener) {
                window.removeEventListener('message', existingIframe._messageListener);
            }
            existingIframe.remove();
        }

        await this.maybeRestartEngineForMapReload('retryLoadMap');

        if (this._mapMessageListener) {
            try {
                window.removeEventListener('message', this._mapMessageListener);
            } catch (e) {
            }
            this._mapMessageListener = null;
        }

        // Remove existing error message
        const existingErrorDiv = mapContainer.querySelector('.map-placeholder');
        if (existingErrorDiv) {
            existingErrorDiv.remove();
        }

        // Create a new loading indicator
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'map-placeholder';
        loadingDiv.innerHTML = `
            <div class="map-placeholder-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/>
                </svg>
            </div>
            <p class="map-placeholder-text">Loading map...</p>
            <div class="map-placeholder-loader">
                <div class="loader-dot"></div>
                <div class="loader-dot"></div>
                <div class="loader-dot"></div>
            </div>
        `;
        mapContainer.appendChild(loadingDiv);

        // Delay calling loadMapIframe
        setTimeout(() => {
            this.loadMapIframe();
        }, 500);
    },

    /**
     * Handle location update
     */
    handleLocationUpdate(data) {
        console.log('Location update:', data);
        const lngElement = document.querySelector('.status-row.sub span[class="value"]');
        const latElement = document.querySelectorAll('.status-row.sub span[class="value"]')[1];
        const lngNum = (data && data.lng !== undefined && data.lng !== null) ? Number(data.lng) : null;
        const latNum = (data && data.lat !== undefined && data.lat !== null) ? Number(data.lat) : null;
        const hasLng = Number.isFinite(lngNum);
        const hasLat = Number.isFinite(latNum);
        if (lngElement && hasLng) {
            lngElement.textContent = `${lngNum}`;
        }
        if (latElement && hasLat) {
            latElement.textContent = `${latNum}`;
        }

        try {
            if (hasLng && hasLat) {
                this._throttledRefreshResourceOverviewOnLocationUpdate();
            }
        } catch (e) {
        }
    },

    _throttledRefreshResourceOverviewOnLocationUpdate() {
        const now = Date.now();
        const minIntervalMs = 1200;
        if (this._lastResourceRefreshOnLocationUpdateAt && (now - this._lastResourceRefreshOnLocationUpdateAt) < minIntervalMs) {
            return;
        }
        if (this._resourceRefreshOnLocationUpdateInFlight) {
            return;
        }

        this._lastResourceRefreshOnLocationUpdateAt = now;
        this._resourceRefreshOnLocationUpdateInFlight = true;

        const doRefresh = async () => {
            try {
                const resp = await snsApi.getResourceOverview();
                if (!resp || !resp.success) return;
                const content = (resp.content || '').trim();
                if (!content) return;
                this.updateResourceTab(content);
            } catch (e) {
            } finally {
                this._resourceRefreshOnLocationUpdateInFlight = false;
            }
        };

        try {
            Promise.resolve().then(doRefresh);
        } catch (e) {
            this._resourceRefreshOnLocationUpdateInFlight = false;
        }
    },

    /**
     * Handle map click event
     */
    handleMapClick(data) {
        console.log('Map click:', data);
    },

    /**
     * Handle marker add event
     */
    handleMarkerAdd(data) {
        console.log('Marker added:', data);
    },

    /**
     * Send message to map page
     */
    sendMessageToMap(type, data) {
        const iframe = document.querySelector('#mapContainer iframe');
        if (iframe && iframe.contentWindow) {
            const message = {
                type: type,
                data: data
            };
            iframe.contentWindow.postMessage(message, this.getMapIframeTargetOrigin());
        }
    },

    /**
     * Load SNS data
     */
    loadSNSData() {
        // Simulate loading SNS data
        const updateValue = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };

        updateValue('onlineNodes', Math.floor(Math.random() * 100) + 50);
        updateValue('activeUsers', Math.floor(Math.random() * 500) + 100);
        updateValue('messageCount', Math.floor(Math.random() * 10000) + 1000);
    },

    /**
     * Clean up map listeners
     */
    cleanupMapListeners() {
        const iframe = document.querySelector('#mapContainer iframe');
        if (iframe && iframe._messageListener) {
            window.removeEventListener('message', iframe._messageListener);
        }

        if (this._mapMessageListener) {
            try {
                window.removeEventListener('message', this._mapMessageListener);
            } catch (e) {
            }
            this._mapMessageListener = null;
        }
    },

    /**
     * Show toast message
     */
    showToast(message, type = 'success') {
        try {
            if (typeof window !== 'undefined' && window.Toast && typeof window.Toast.show === 'function') {
                window.Toast.show(String(message), String(type || 'success'), 3000);
                return;
            }
        } catch (e) {
        }

        // Create toast element
        const toast = document.createElement('div');
        toast.className = `sns-toast sns-toast-${type}`;
        toast.textContent = message;

        // Choose background color by type
        let backgroundColor;
        switch (type) {
            case 'error':
                backgroundColor = '#f44336';
                break;
            case 'info':
                backgroundColor = '#2196f3';
                break;
            case 'success':
            default:
                backgroundColor = '#4caf50';
                break;
        }

        // Apply styles
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${backgroundColor};
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 2000000;
            max-width: 400px;
            word-wrap: break-word;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(toast);

        // Auto-remove after 3 seconds
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    },

    /**
     * Initialize SNS update listener (global WebSocket event)
     */
    initSNSUpdateListener() {
        // Listen for global WebSocket message event
        this.snsUpdateListener = (event) => {
            const message = event.detail;
            if (message.type === 'sns_update') {
                console.log('SNS update received:', message);
                this.handleSNSUpdate(message);
            }
            if (message.type === 'sns_engine_status') {
                try {
                    this.handleSNSEngineStatusUpdate(message);
                } catch (e) {
                }
            }
        };

        window.addEventListener('websocket-message', this.snsUpdateListener);
        console.log('SNS update listener initialized');
    },

    handleSNSEngineStatusUpdate(payload) {
        const startBtn = document.getElementById('snsStartBtn');
        if (!startBtn) return;

        const taskStatus = String(payload?.task_status || '').toLowerCase();
        const running = !!(payload && payload.running);
        const started = !!(payload && payload.started);
        const active = running || started || taskStatus === 'started' || taskStatus === 'paused';

        if (active) {
            try {
                this._suppressSnsUpdates = false;
            } catch (e) {
            }
        }

        const setStartButtonState = (state) => {
            if (state === 'start') {
                startBtn.classList.remove('running');
                startBtn.title = '';
                startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Start</span>`;
                return;
            }
            if (state === 'pause') {
                startBtn.classList.add('running');
                startBtn.title = 'Right click to get more control';
                startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Pause</span>`;
                return;
            }
            if (state === 'resume') {
                startBtn.classList.remove('running');
                startBtn.title = '';
                startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Resume</span>`;
            }
        };

        if (!active) {
            setStartButtonState('start');
            return;
        }
        if (taskStatus === 'paused') {
            setStartButtonState('resume');
            return;
        }
        setStartButtonState('pause');
    },

    /**
     * Handle SNS update message
     */
    handleSNSUpdate(data) {
        console.log('Handling SNS update:', data);
        const { tab, content, section } = data;

        if (this._suppressSnsUpdates && (tab === 'think' || tab === 'process' || tab === 'resource')) {
            return;
        }

        if (tab === 'think') {
            console.log('Updating Think tab with content:', content);
            this.updateThinkTab(content);
        } else if (tab === 'process') {
            console.log('Updating Process tab with content:', content, 'section:', section);
            this.updateProcessTab(content, section);
        } else if (tab === 'resource') {
            console.log('Updating Resource tab with content:', content);
            this.updateResourceTab(content);
        }
    },

    /**
     * Update Think tab content
     */
    updateThinkTab(content) {
        console.log('updateThinkTab called with content:', content);
        // Find the Think tab content area
        const thinkPane = document.querySelector('.tab-pane[data-tab="think"]');
        console.log('Think pane found:', thinkPane);
        if (!thinkPane) return;

        // Find the Thinking Log section
        let thinkingLogSection = thinkPane.querySelector('.status-section:nth-child(2) .status-rows');
        console.log('Thinking log section found:', thinkingLogSection);
        if (!thinkingLogSection) return;

        // Create a new content element
        const contentDiv = document.createElement('div');
        contentDiv.className = 'thinking-log-entry';
        contentDiv.style.cssText = `
            white-space: pre-wrap;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            font-size: 13px;
            line-height: 1.6;
            padding: 8px;
            background: rgba(26, 115, 232, 0.05);
            border-left: 3px solid #1a73e8;
            margin-bottom: 8px;
            border-radius: 4px;
        `;
        try {
            const pad = (n) => String(n).padStart(2, '0');
            const d = new Date();
            const timeText = `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
            const baseText = (content === undefined || content === null) ? '' : String(content);
            const joined = baseText ? `Time: ${timeText}\n${baseText}` : `Time: ${timeText}`;
            contentDiv.textContent = joined;
        } catch (e) {
            contentDiv.textContent = content;
        }

        // If this is the first entry, clear "N/A"
        if (thinkingLogSection.querySelector('.na')) {
            thinkingLogSection.innerHTML = '';
        }

        // Append new content
        thinkingLogSection.appendChild(contentDiv);

        // Keep only the newest 100 log entries to avoid slow rendering
        try {
            while (thinkingLogSection.querySelectorAll('.thinking-log-entry').length > 100) {
                const oldest = thinkingLogSection.querySelector('.thinking-log-entry');
                if (!oldest) break;
                oldest.remove();
            }
        } catch (e) {
        }

        // Scroll to bottom
        thinkingLogSection.scrollTop = thinkingLogSection.scrollHeight;
        thinkingLogSection.scrollTop = thinkingLogSection.scrollHeight;

        try {
            this.ensureThinkingLogNavigator();
        } catch (e) {
        }
    },

    ensureThinkingLogNavigator() {
        const statusPanel = document.getElementById('snsStatusPanel');
        const scrollEl = document.getElementById('statusTabContent');
        const thinkPane = document.querySelector('.tab-pane[data-tab="think"]');
        if (!statusPanel || !scrollEl || !thinkPane) return;

        let nav = document.getElementById('thinkingLogNavigator');
        if (!nav) {
            nav = document.createElement('div');
            nav.id = 'thinkingLogNavigator';
            nav.className = 'thinking-log-navigator';
            nav.style.display = 'none';
            nav.innerHTML = `
                <button type="button" class="thinking-log-nav-btn" data-dir="prev" title="Previous log">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="18 15 12 9 6 15"></polyline>
                    </svg>
                </button>
                <button type="button" class="thinking-log-nav-btn" data-dir="next" title="Next log">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                        <polyline points="6 9 12 15 18 9"></polyline>
                    </svg>
                </button>
            `;
            statusPanel.appendChild(nav);

            nav.addEventListener('click', (e) => {
                const btn = e.target.closest('.thinking-log-nav-btn');
                if (!btn) return;
                const dir = btn.dataset.dir;
                if (dir !== 'prev' && dir !== 'next') return;
                this.scrollThinkingLogByCard(dir);
            });

            const onLayout = () => {
                try {
                    this.updateThinkingLogNavigatorVisibility();
                } catch (e) {
                }
            };

            if (!this._thinkingLogNavigatorBound) {
                this._thinkingLogNavigatorBound = true;
                window.addEventListener('resize', onLayout);
                scrollEl.addEventListener('scroll', onLayout, { passive: true });
            }
        }

        this.updateThinkingLogNavigatorVisibility();
    },

    updateThinkingLogNavigatorVisibility() {
        const nav = document.getElementById('thinkingLogNavigator');
        const scrollEl = document.getElementById('statusTabContent');
        const thinkPane = document.querySelector('.tab-pane[data-tab="think"]');
        if (!nav || !scrollEl || !thinkPane) return;

        const isThinkActive = thinkPane.classList.contains('active');
        let entriesCount = 0;
        try {
            const listEl = thinkPane.querySelector('.status-section:nth-child(2) .status-rows');
            if (listEl) {
                entriesCount = listEl.querySelectorAll('.thinking-log-entry').length;
            }
        } catch (e) {
            entriesCount = 0;
        }

        const canScroll = (scrollEl.scrollHeight - scrollEl.clientHeight) > 4;
        const shouldShow = !!(isThinkActive && canScroll && entriesCount >= 2);
        nav.style.display = shouldShow ? 'flex' : 'none';
    },

    scrollThinkingLogByCard(direction) {
        const scrollEl = document.getElementById('statusTabContent');
        const thinkPane = document.querySelector('.tab-pane[data-tab="think"]');
        if (!scrollEl || !thinkPane) return;
        if (!thinkPane.classList.contains('active')) return;

        const listEl = thinkPane.querySelector('.status-section:nth-child(2) .status-rows');
        if (!listEl) return;

        const entries = Array.from(listEl.querySelectorAll('.thinking-log-entry'));
        if (!entries.length) return;

        const containerRect = scrollEl.getBoundingClientRect();
        const top = containerRect.top;

        let currentIndex = -1;
        let bestDist = Number.POSITIVE_INFINITY;
        for (let i = 0; i < entries.length; i++) {
            const r = entries[i].getBoundingClientRect();
            const dist = Math.abs(r.top - top);
            if (dist < bestDist) {
                bestDist = dist;
                currentIndex = i;
            }
        }
        if (currentIndex < 0) currentIndex = 0;

        let targetIndex = currentIndex;
        if (direction === 'prev') {
            targetIndex = Math.max(0, currentIndex - 1);
        } else {
            targetIndex = Math.min(entries.length - 1, currentIndex + 1);
        }

        const target = entries[targetIndex];
        if (!target) return;
        try {
            target.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } catch (e) {
            try {
                target.scrollIntoView(true);
            } catch (e2) {
            }
        }
    },

    /**
     * Update Process tab content
     */
    updateProcessTab(content, section = null) {
        console.log('updateProcessTab called with content:', content, 'section:', section);
        // Find the Process tab content area
        const processPane = document.querySelector('.tab-pane[data-tab="process"]');
        console.log('Process pane found:', processPane);
        if (!processPane) return;

        // If section is specified, check whether content needs to be split
        if (section === 'ongoing') {
            // Check whether content contains Current Status
            if (content.includes('📊 Current Status')) {
                console.log('Content contains Current Status, parsing...');
                // Split content
                const lines = content.split('\n');
                let currentStatusContent = '';
                let onGoingContent = '';
                let currentSection = '';

                for (const line of lines) {
                    if (line.includes('📊 Current Status')) {
                        currentSection = 'status';
                        continue;
                    } else if (line.includes('⏳ On Going')) {
                        currentSection = 'ongoing';
                        continue;
                    }

                    // Skip divider line
                    if (line.includes('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')) {
                        continue;
                    }

                    if (currentSection === 'status') {
                        currentStatusContent += line + '\n';
                    } else if (currentSection === 'ongoing') {
                        onGoingContent += line + '\n';
                    }
                }

                // Update both sections
                if (currentStatusContent.trim()) {
                    this.updateCurrentStatusSection(processPane, currentStatusContent.trim());
                }
                if (onGoingContent.trim()) {
                    this.updateOnGoingSection(processPane, onGoingContent.trim());
                }
            } else {
                // Only On Going content
                this.updateOnGoingSection(processPane, content);
            }
            return;
        } else if (section === 'history') {
            this.updateHistorySection(processPane, content);
            return;
        } else if (section === 'status') {
            this.updateCurrentStatusSection(processPane, content);
            return;
        }

        // Otherwise, parse content and update three sections
        const lines = content.split('\n');
        let currentStatusContent = '';
        let onGoingContent = '';
        let processHistoryContent = '';
        let currentSection = '';

        for (const line of lines) {
            if (line.includes('📊 Current Status')) {
                currentSection = 'status';
                continue;
            } else if (line.includes('⏳ On Going')) {
                currentSection = 'ongoing';
                continue;
            } else if (line.includes('📜 Process history')) {
                currentSection = 'history';
                continue;
            }

            // Skip divider line
            if (line.includes('━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━')) {
                continue;
            }

            if (currentSection === 'status') {
                currentStatusContent += line + '\n';
            } else if (currentSection === 'ongoing') {
                onGoingContent += line + '\n';
            } else if (currentSection === 'history') {
                processHistoryContent += line + '\n';
            }
        }

        // Update sections
        if (currentStatusContent.trim()) {
            this.updateCurrentStatusSection(processPane, currentStatusContent.trim());
        }

        if (onGoingContent.trim()) {
            this.updateOnGoingSection(processPane, onGoingContent.trim());
        }

        if (processHistoryContent.trim()) {
            this.updateHistorySection(processPane, processHistoryContent.trim());
        }
    },

    /**
     * Update Current Status section
     */
    updateCurrentStatusSection(processPane, content) {
        const statusSection = processPane.querySelector('.status-section:nth-child(1) .status-rows');
        if (!statusSection) {
            console.warn('Current Status section not found');
            return;
        }

        // Clear existing content
        statusSection.innerHTML = '';

        // Parse content and create status rows
        const lines = content.split('\n');
        for (const line of lines) {
            if (!line.trim()) continue;

            // Create status row element
            const statusRow = document.createElement('div');
            statusRow.className = 'status-row';

            // Check whether this is a sub-row (Location lng/lat)
            if (line.trim().startsWith('├─') || line.trim().startsWith('└─')) {
                statusRow.classList.add('sub');
                // Remove tree symbol
                const cleanLine = line.replace(/[├└]─\s*/, '').trim();
                const parts = cleanLine.split(':');
                if (parts.length === 2) {
                    const label = document.createElement('span');
                    label.textContent = parts[0].trim();
                    const value = document.createElement('span');
                    value.className = 'value';
                    value.textContent = parts[1].trim();
                    statusRow.appendChild(label);
                    statusRow.appendChild(value);
                }
            } else {
                // Regular status row
                const parts = line.split(':');
                if (parts.length >= 2) {
                    const label = document.createElement('span');
                    label.textContent = parts[0].trim();
                    const value = document.createElement('span');
                    value.className = 'value';
                    value.textContent = parts.slice(1).join(':').trim();
                    statusRow.appendChild(label);
                    statusRow.appendChild(value);
                } else {
                    // Row with only label and no value (e.g., 📍 Location)
                    const label = document.createElement('span');
                    label.textContent = line.trim();
                    statusRow.appendChild(label);
                }
            }

            statusSection.appendChild(statusRow);
        }

        console.log('Current Status section updated');
    },

    /**
     * Update On Going section
     */
    updateOnGoingSection(processPane, content) {
        const onGoingSection = processPane.querySelector('.status-section:nth-child(2) .status-rows');
        if (!onGoingSection) {
            console.warn('On Going section not found');
            return;
        }

        if (onGoingSection.querySelector('.na')) {
            onGoingSection.innerHTML = '';
        }

        const onGoingDiv = document.createElement('div');
        onGoingDiv.style.cssText = `
            white-space: pre-wrap;
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            font-size: 13px;
            line-height: 1.6;
            color: var(--text-primary);
        `;
        onGoingDiv.textContent = content;
        onGoingSection.innerHTML = '';
        onGoingSection.appendChild(onGoingDiv);
        console.log('On Going section updated');
    },

    /**
     * Update Process History section
     */
    updateHistorySection(processPane, content) {
        const historySection = processPane.querySelector('.status-section:nth-child(3) .status-rows');
        if (!historySection) {
            console.warn('History section not found');
            return;
        }

        if (historySection.querySelector('.na')) {
            historySection.innerHTML = '';
        }

        const formatNow = () => {
            try {
                const pad = (n) => String(n).padStart(2, '0');
                const d = new Date();
                return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}:${pad(d.getSeconds())}`;
            } catch (e) {
                return '';
            }
        };

        const wrapper = document.createElement('div');
        wrapper.style.cssText = `
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            font-size: 13px;
            line-height: 1.6;
            color: var(--text-primary);
        `;

        const text = (content === undefined || content === null) ? '' : String(content);
        const items = text.split('\n').map(s => s.trim()).filter(Boolean);
        if (!items.length) {
            const na = document.createElement('span');
            na.className = 'na';
            na.textContent = 'N/A';
            wrapper.appendChild(na);
        } else {
            for (const item of items) {
                const entry = document.createElement('div');
                entry.style.cssText = `
                    padding: 6px 0;
                    border-bottom: 1px solid rgba(0, 0, 0, 0.06);
                `;

                const timeLine = document.createElement('div');
                timeLine.style.cssText = `
                    font-size: 11px;
                    line-height: 1.2;
                    color: var(--text-secondary, #666);
                    opacity: 0.9;
                    margin-bottom: 2px;
                `;
                timeLine.textContent = formatNow();

                const contentLine = document.createElement('div');
                contentLine.style.cssText = `
                    white-space: pre-wrap;
                    word-break: break-word;
                `;
                contentLine.textContent = item;

                entry.appendChild(timeLine);
                entry.appendChild(contentLine);
                wrapper.appendChild(entry);
            }
        }

        historySection.innerHTML = '';
        historySection.appendChild(wrapper);
        console.log('History section updated');
    },

    /**
     * Update Resource tab content
     */
    updateResourceTab(content) {
        console.log('updateResourceTab called with content:', content);
        // Find the Resource tab content area
        const resourcePane = document.querySelector('.tab-pane[data-tab="resource"]');
        console.log('Resource pane found:', resourcePane);
        if (!resourcePane) return;

        // Find the first status-section (Resource Overview)
        const resourceSection = resourcePane.querySelector('.status-section:nth-child(1) .status-rows');
        console.log('Resource section found:', resourceSection);
        if (!resourceSection) return;

        // Clear N/A marker
        if (resourceSection.querySelector('.na')) {
            resourceSection.innerHTML = '';
        }

        const self = this;
        const wrapper = document.createElement('div');
        wrapper.style.cssText = `
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, "Noto Sans", sans-serif;
            font-size: 13px;
            line-height: 1.6;
            color: var(--text-primary);
        `;

        const text = (content === undefined || content === null) ? '' : String(content);
        const lines = text.split('\n');
        const coordRegex = /(-?\d+(?:\.\d+)?(?:e[-+]?\d+)?)\s*,\s*(-?\d+(?:\.\d+)?(?:e[-+]?\d+)?)/i;
        const urlRegex = /(https?:\/\/[^\s<>"']+)/i;

        let currentSection = '';

        for (const rawLine of lines) {
            const line = (rawLine === undefined || rawLine === null) ? '' : String(rawLine);

            if (line.startsWith('☁️ Services List')) {
                currentSection = 'services';
            } else if (line.startsWith('🧑‍🤝‍🧑 People List')) {
                currentSection = 'people';
            } else if (line.startsWith('🗺️ Place List')) {
                currentSection = 'places';
            }

            const row = document.createElement('div');
            row.style.cssText = `
                display: flex;
                align-items: center;
                flex-wrap: wrap;
                gap: 8px;
                padding: 1px 0;
            `;

            const textSpan = document.createElement('span');
            textSpan.style.cssText = `
                white-space: pre-wrap;
                word-break: break-word;
            `;
            textSpan.textContent = line || ' ';
            row.appendChild(textSpan);

            const hasPinMarker = line.includes('📍');
            const m = hasPinMarker ? coordRegex.exec(line) : null;
            if (m && m.length >= 3) {
                const lng = Number(m[1]);
                const lat = Number(m[2]);
                if (Number.isFinite(lng) && Number.isFinite(lat)) {
                    const btn = document.createElement('button');
                    btn.type = 'button';
                    btn.className = 'sns-go-to-btn';
                    btn.dataset.lng = String(lng);
                    btn.dataset.lat = String(lat);
                    btn.textContent = 'Go';
                    btn.style.cssText = `
                        padding: 4px 10px;
                        font-size: 12px;
                        font-weight: 700;
                        border-radius: 8px;
                        border: 1px solid rgba(0, 0, 0, 0.35);
                        background: #1a73e8;
                        color: #ffffff;
                        cursor: pointer;
                        letter-spacing: 0.2px;
                    `;
                    btn.addEventListener('mouseenter', () => {
                        btn.style.filter = 'brightness(1.08)';
                    });
                    btn.addEventListener('mouseleave', () => {
                        btn.style.filter = '';
                    });
                    btn.addEventListener('mousedown', () => {
                        btn.style.transform = 'translateY(1px)';
                    });
                    btn.addEventListener('mouseup', () => {
                        btn.style.transform = '';
                    });
                    row.appendChild(btn);
                }
            }

            if (currentSection === 'places') {
                const urlMatch = urlRegex.exec(line);
                if (urlMatch && urlMatch[1]) {
                    const url = String(urlMatch[1]).trim();
                    if (url) {
                        const visitBtn = document.createElement('button');
                        visitBtn.type = 'button';
                        visitBtn.className = 'sns-visit-btn';
                        visitBtn.dataset.url = url;

                        const m = coordRegex.exec(line);
                        if (m && m.length >= 3) {
                            const lng = Number(m[1]);
                            const lat = Number(m[2]);
                            if (Number.isFinite(lng) && Number.isFinite(lat)) {
                                visitBtn.dataset.lng = String(lng);
                                visitBtn.dataset.lat = String(lat);
                            }
                        }

                        visitBtn.textContent = 'Visit';
                        visitBtn.style.cssText = `
                            padding: 4px 10px;
                            font-size: 12px;
                            font-weight: 700;
                            border-radius: 8px;
                            border: 1px solid rgba(26, 115, 232, 0.28);
                            background: rgba(26, 115, 232, 0.08);
                            color: var(--color-primary, #1a73e8);
                            cursor: pointer;
                            letter-spacing: 0.2px;
                        `;
                        visitBtn.addEventListener('mouseenter', () => {
                            visitBtn.style.filter = 'brightness(1.06)';
                        });
                        visitBtn.addEventListener('mouseleave', () => {
                            visitBtn.style.filter = '';
                        });
                        visitBtn.addEventListener('mousedown', () => {
                            visitBtn.style.transform = 'translateY(1px)';
                        });
                        visitBtn.addEventListener('mouseup', () => {
                            visitBtn.style.transform = '';
                        });
                        row.appendChild(visitBtn);
                    }
                }
            }

            wrapper.appendChild(row);
        }

        resourceSection.innerHTML = '';
        resourceSection.appendChild(wrapper);

        if (!resourceSection.dataset.snsGoToBound) {
            resourceSection.dataset.snsGoToBound = '1';
            resourceSection.addEventListener('click', (e) => {
                const btn = e.target && e.target.closest ? e.target.closest('.sns-go-to-btn') : null;
                const visitBtn = e.target && e.target.closest ? e.target.closest('.sns-visit-btn') : null;
                if (!btn && !visitBtn) return;

                e.preventDefault();
                e.stopPropagation();

                if (visitBtn) {
                    const url = String(visitBtn.dataset.url || '').trim();
                    if (!url) return;
                    try {
                        const lng = Number(visitBtn.dataset.lng);
                        const lat = Number(visitBtn.dataset.lat);
                        const placePosition = (Number.isFinite(lng) && Number.isFinite(lat)) ? [lng, lat] : null;
                        self.handleOpenPlaceWebAddress(url, undefined, placePosition);
                    } catch (err) {
                        console.warn('Failed to open place intro:', err);
                    }
                    return;
                }

                const lng = Number(btn.dataset.lng);
                const lat = Number(btn.dataset.lat);
                if (!Number.isFinite(lng) || !Number.isFinite(lat)) return;

                const iframe = document.querySelector('#mapContainer iframe');
                if (!iframe || !iframe.contentWindow) {
                    console.warn('Map iframe not found or not ready');
                    return;
                }

                const message = {
                    type: 'mapGoTo',
                    data: {
                        lng,
                        lat,
                        zoom: 17
                    }
                };

                try {
                    self.safePostMessageToMap(iframe, message, self.getMapIframeTargetOrigin());
                } catch (err) {
                    console.warn('Failed to send mapGoTo to iframe:', err);
                }
            });
        }
        console.log('Resource tab updated successfully');
    },

    /**
     * Handle open dialog requests from map.html
     */
    async handleOpenDialog(dialogType) {
        console.log('handleOpenDialog called with dialogType:', dialogType);

        try {
            let dialog;
            switch (dialogType) {
                case 'avatar':
                    dialog = new SNSAvatarDialog();
                    break;
                case 'profession':
                    dialog = new SNSProfessionDialog();
                    break;
                case 'socialRole':
                    dialog = new SNSSocialRoleDialog();
                    break;
                case 'goals':
                    dialog = new SNSGoalsDialog();
                    break;
                case 'mapConfig':
                    dialog = new SNSMapConfigDialog();
                    break;
                default:
                    console.warn('Unknown dialog type:', dialogType);
                    return;
            }

            if (dialog) {
                await dialog.show();
                console.log('Dialog opened successfully:', dialogType);
            }
        } catch (error) {
            console.error('Error opening dialog:', dialogType, error);
            this.showToast(`Failed to open dialog: ${error.message}`, 'error');
        }
    },

    /**
     * Handle panel collapse/expand requests from map.html
     */
    handleTogglePanels(action) {
        console.log('handleTogglePanels called with action:', action);

        // Get sidebar-related elements (secondary sidebar)
        const secondarySidebar = document.getElementById('secondarySidebar');
        const sidebarResizer = document.getElementById('sidebarResizer');
        const mainContent = document.getElementById('mainContent');

        // Get SNS page right-side panel related elements
        const statusPanel = document.getElementById('snsStatusPanel');
        const panelResizer = document.getElementById('snsPanelResizer');

        if (!secondarySidebar || !sidebarResizer || !mainContent) {
            console.warn('Sidebar elements not found');
            return;
        }

        if (action === 'collapse') {
            // Collapse sidebar
            secondarySidebar.classList.add('collapsed');
            sidebarResizer.classList.add('collapsed');
            mainContent.classList.add('sidebar-collapsed');

            console.log('Sidebar collapsed');
        } else if (action === 'expand') {
            // Expand sidebar
            secondarySidebar.classList.remove('collapsed');
            sidebarResizer.classList.remove('collapsed');
            mainContent.classList.remove('sidebar-collapsed');

            console.log('Sidebar expanded');
        }

        // Handle right-side status panel (only on SNS page)
        if (statusPanel && panelResizer) {
            if (action === 'collapse') {
                // Collapse right-side panel
                statusPanel.classList.add('collapsed');
                panelResizer.classList.add('collapsed');
                localStorage.setItem('snsPanelCollapsed', 'true');
                console.log('SNS panel collapsed');
            } else if (action === 'expand') {
                // Expand right-side panel
                statusPanel.classList.remove('collapsed');
                panelResizer.classList.remove('collapsed');
                localStorage.setItem('snsPanelCollapsed', 'false');
                console.log('SNS panel expanded');
            }
        }
    },

    /**
     * Handle open SNS Profile tab request
     */
    handleOpenSNSProfile(url) {
        console.log('handleOpenSNSProfile called with url:', url);

        // URL normalization
        if (!url || typeof url !== 'string') {
            console.error('Invalid URL provided:', url);
            return;
        }

        // Trim whitespace
        url = url.trim();

        // Check whether URL has a scheme
        if (!url.match(/^https?:\/\//i)) {
            // Check whether it's a local address
            if (url.startsWith('localhost') || url.startsWith('127.0.0.1') || url.startsWith('192.168.')) {
                url = 'http://' + url;
                console.log('Added http:// to local URL:', url);
            } else if (url.startsWith('//')) {
                // Protocol-relative URL
                url = 'https:' + url;
                console.log('Added https: to protocol-relative URL:', url);
            } else if (url.startsWith('/')) {
                // Relative path, use current server
                url = this.resolve(url);
                console.log('Converted relative path to absolute URL:', url);
            } else {
                // Default to adding https://
                url = 'https://' + url;
                console.log('Added https:// to URL:', url);
            }
        }

        // Validate URL format
        try {
            new URL(url);
        } catch (e) {
            console.error('Invalid URL format after normalization:', url, e);
            this.showToast('Invalid URL format: ' + url, 'error');
            return;
        }

        const statusTabs = document.getElementById('statusTabs');
        const statusTabContent = document.getElementById('statusTabContent');

        if (!statusTabs || !statusTabContent) {
            console.warn('Status tabs container not found');
            return;
        }

        // Check whether Profile tab already exists
        let profileTab = statusTabs.querySelector('.status-tab[data-tab="profile"]');
        let profilePane = statusTabContent.querySelector('.tab-pane[data-tab="profile"]');

        if (!profileTab) {
            // Create Profile tab button
            profileTab = document.createElement('button');
            profileTab.className = 'status-tab';
            profileTab.dataset.tab = 'profile';
            profileTab.innerHTML = `Profile <span class="tab-close-btn" title="Close">×</span>`;
            statusTabs.appendChild(profileTab);

            // Bind close button event
            const closeBtn = profileTab.querySelector('.tab-close-btn');
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.handleCloseSNSProfile();
            });
        }

        if (!profilePane) {
            // Create Profile tab content
            profilePane = document.createElement('div');
            profilePane.className = 'tab-pane';
            profilePane.dataset.tab = 'profile';
            profilePane.innerHTML = `
                <div class="profile-webview-container">
                    <iframe src="${url}" class="profile-webview" frameborder="0"></iframe>
                </div>
            `;
            statusTabContent.appendChild(profilePane);
        } else {
            // Update URL of existing iframe
            const iframe = profilePane.querySelector('.profile-webview');
            if (iframe) {
                iframe.src = url;
            }
        }

        // Switch to Profile tab
        statusTabs.querySelectorAll('.status-tab').forEach(btn => {
            btn.classList.toggle('active', btn === profileTab);
        });

        statusTabContent.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane === profilePane);
        });

        // Auto-scroll to the Profile tab (ensure it's visible)
        if (profileTab) {
            profileTab.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'center'
            });
        }

        console.log('SNS Profile tab opened with URL:', url);
    },

    /**
     * Handle close SNS Profile tab request
     */
    handleCloseSNSProfile() {
        console.log('handleCloseSNSProfile called');

        const statusTabs = document.getElementById('statusTabs');
        const statusTabContent = document.getElementById('statusTabContent');

        if (!statusTabs || !statusTabContent) {
            console.warn('Status tabs container not found');
            return;
        }

        // Find and remove Profile tab
        const profileTab = statusTabs.querySelector('.status-tab[data-tab="profile"]');
        const profilePane = statusTabContent.querySelector('.tab-pane[data-tab="profile"]');

        if (!profileTab && !profilePane) {
            return;
        }

        const wasActive = !!(profileTab && profileTab.classList.contains('active'));

        if (profileTab) {
            profileTab.remove();
        }

        if (profilePane) {
            profilePane.remove();
        }

        // Switch to the first tab (Process) — use exclusive toggle to avoid
        // leaving stale 'active' class on other tabs (fixes simultaneous
        // Process + Think activation bug).
        if (wasActive) {
            const firstTab = statusTabs.querySelector('.status-tab');
            const firstPane = statusTabContent.querySelector('.tab-pane');

            if (firstTab && firstPane) {
                statusTabs.querySelectorAll('.status-tab').forEach(btn => {
                    btn.classList.toggle('active', btn === firstTab);
                });
                statusTabContent.querySelectorAll('.tab-pane').forEach(pane => {
                    pane.classList.toggle('active', pane === firstPane);
                });
            }
        }

        console.log('SNS Profile tab closed');
    }

    ,

    handleOpenUrl(url) {
        const u = (url === undefined || url === null) ? '' : String(url).trim();
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

    ,

    async loadSNSRendererPlugin(plugin) {
        const statusTabs = document.getElementById('statusTabs');
        const statusTabContent = document.getElementById('statusTabContent');
        if (!statusTabs || !statusTabContent) {
            console.warn('Status tabs container not found');
            return;
        }

        const pluginKey = plugin && (plugin.plugin_id || plugin.id) ? String(plugin.plugin_id || plugin.id) : '';
        if (!pluginKey) {
            console.warn('[snsHandlers] Invalid plugin data:', plugin);
            return;
        }

        const tabId = `plugin-${pluginKey}`;
        const existingTab = statusTabs.querySelector(`.status-tab[data-tab="${tabId}"]`);
        const existingPane = statusTabContent.querySelector(`.tab-pane[data-tab="${tabId}"]`);
        if (existingTab && existingPane) {
            existingTab.click();
            return;
        }

        const pluginName = (plugin && plugin.name) ? String(plugin.name) : pluginKey;
        const entryRaw = (plugin && plugin.filename) ? String(plugin.filename) : '';
        if (!entryRaw) {
            this.showToast('Plugin entry is empty', 'error');
            return;
        }

        const entryUrl = this.resolve(entryRaw);

        let mod;
        try {
            const urlObj = new URL(entryUrl, window.location.href);
            urlObj.searchParams.set('t', String(Date.now()));
            mod = await import(urlObj.toString());
        } catch (e) {
            console.warn('[snsHandlers] Failed to import plugin module:', entryUrl, e);
            this.showToast(`Failed to load plugin: ${pluginName}`, 'error');
            return;
        }

        const pluginInstance = (mod && mod.default) ? mod.default : null;
        if (!pluginInstance || typeof pluginInstance.render !== 'function') {
            this.showToast(`Invalid plugin module: ${pluginName}`, 'error');
            return;
        }

        const tabBtn = document.createElement('button');
        tabBtn.className = 'status-tab';
        tabBtn.dataset.tab = tabId;
        tabBtn.innerHTML = `${pluginName} <span class="tab-close-btn" title="Close">×</span>`;
        statusTabs.appendChild(tabBtn);

        const pane = document.createElement('div');
        pane.className = 'tab-pane';
        pane.dataset.tab = tabId;
        pane.innerHTML = `<div class="status-section"><div class="status-rows"><div class="sns-plugin-host" style="min-height: 120px;"></div></div></div>`;
        statusTabContent.appendChild(pane);

        const hostEl = pane.querySelector('.sns-plugin-host');
        const api = this._createSNSPluginApi();

        try {
            await pluginInstance.render(hostEl, api);
        } catch (e) {
            console.warn('[snsHandlers] Plugin render failed:', pluginName, e);
            this.showToast(`Plugin render failed: ${pluginName}`, 'error');
        }

        this._snsLoadedRendererPlugins.set(pluginKey, {
            plugin: pluginInstance,
            tabId
        });

        const closeBtn = tabBtn.querySelector('.tab-close-btn');
        if (closeBtn) {
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                this.unloadSNSRendererPlugin(pluginKey);
            });
        }

        tabBtn.click();
    }

    ,

    unloadSNSRendererPlugin(pluginKey) {
        const rec = this._snsLoadedRendererPlugins.get(String(pluginKey));
        const tabId = rec && rec.tabId ? String(rec.tabId) : `plugin-${String(pluginKey)}`;

        const statusTabs = document.getElementById('statusTabs');
        const statusTabContent = document.getElementById('statusTabContent');
        if (!statusTabs || !statusTabContent) return;

        try {
            if (rec && rec.plugin && typeof rec.plugin.dispose === 'function') {
                rec.plugin.dispose();
            }
        } catch (e) {
        }

        const tab = statusTabs.querySelector(`.status-tab[data-tab="${tabId}"]`);
        const pane = statusTabContent.querySelector(`.tab-pane[data-tab="${tabId}"]`);
        const wasActive = !!(tab && tab.classList.contains('active'));

        if (tab) tab.remove();
        if (pane) pane.remove();

        this._snsLoadedRendererPlugins.delete(String(pluginKey));

        if (wasActive) {
            const firstTab = statusTabs.querySelector('.status-tab');
            const firstTabKey = firstTab ? String(firstTab.dataset.tab || '') : '';
            statusTabs.querySelectorAll('.status-tab').forEach(btn => {
                btn.classList.toggle('active', btn === firstTab);
            });
            statusTabContent.querySelectorAll('.tab-pane').forEach(p => {
                p.classList.toggle('active', firstTabKey && p.dataset.tab === firstTabKey);
            });
        }
    }

    ,

    _createSNSPluginApi() {
        const resolveBaseUrl = async () => {
            try {
                if (window.electronAPI && typeof window.electronAPI.getApiUrl === 'function') {
                    const raw = await window.electronAPI.getApiUrl();
                    return raw ? String(raw).replace(/\/+$/, '') : '';
                }
            } catch (e) {
            }

            const raw = (window.appConfig && window.appConfig.agent_server) ? String(window.appConfig.agent_server) : '';
            return raw ? raw.replace(/\/+$/, '') : '';
        };

        const ui = {
            toast: (type, message) => {
                const msg = (message === undefined || message === null) ? '' : String(message);
                const t = type ? String(type) : 'info';
                if (window.Toast && typeof window.Toast[t] === 'function') {
                    window.Toast[t](msg);
                    return;
                }
                this.showToast(msg, t);
            },
            openPlaceIntro: (url) => {
                const u = url ? String(url).trim() : '';
                if (!u) return;
                this.handleOpenPlaceWebAddress(u);
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
        };

        const sns = {
            getJson: async (path) => {
                const base = await resolveBaseUrl();
                const resp = await fetch(`${base}${path}`);
                return await resp.json();
            },
            postJson: async (path, body) => {
                const base = await resolveBaseUrl();
                const resp = await fetch(`${base}${path}`, {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify(body || {})
                });
                return await resp.json();
            },
            jsonrpc: async (method, params) => {
                const base = await resolveBaseUrl();
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
        };

        const map = {
            postMessage: (payload) => {
                const iframe = document.querySelector('#mapContainer iframe');
                if (!iframe || !iframe.contentWindow) return false;
                return this.safePostMessageToMap(iframe, payload, this.getMapIframeTargetOrigin());
            }
        };

        return { ui, sns, map };
    }

    ,

    /**
     * Handle open Place intro tab request
     */
    handleOpenPlaceWebAddress(url, url3d, placePosition, placePositionByMap) {
        console.log('handleOpenPlaceWebAddress called with url:', url);

        const normalizedUrl3d = (url3d && typeof url3d === 'string') ? url3d.trim() : '';

        // URL normalization
        if (!url || typeof url !== 'string') {
            console.error('Invalid URL provided:', url);
            return;
        }

        // Trim whitespace
        url = url.trim();

        // Check whether URL has a scheme
        if (!url.match(/^https?:\/\//i)) {
            // Check whether it's a local address
            if (url.startsWith('localhost') || url.startsWith('127.0.0.1') || url.startsWith('192.168.')) {
                url = 'http://' + url;
                console.log('Added http:// to local URL:', url);
            } else if (url.startsWith('//')) {
                // Protocol-relative URL
                url = 'https:' + url;
                console.log('Added https: to protocol-relative URL:', url);
            } else if (url.startsWith('/')) {
                // Relative path, use current server
                url = this.resolve(url);
                console.log('Converted relative path to absolute URL:', url);
            } else {
                // Default to adding https://
                url = 'https://' + url;
                console.log('Added https:// to URL:', url);
            }
        }

        // Validate URL format
        try {
            new URL(url);
        } catch (e) {
            console.error('Invalid URL format after normalization:', url, e);
            this.showToast('Invalid URL format: ' + url, 'error');
            return;
        }

        const statusTabs = document.getElementById('statusTabs');
        const statusTabContent = document.getElementById('statusTabContent');

        if (!statusTabs || !statusTabContent) {
            console.warn('Status tabs container not found');
            return;
        }

        // Check whether Place intro tab already exists
        let placeTab = statusTabs.querySelector('.status-tab[data-tab="placeIntro"]');
        let placePane = statusTabContent.querySelector('.tab-pane[data-tab="placeIntro"]');

        const tabStillOpen = !!(placeTab && placePane);
        const urlUnchanged = (this.lastPlaceIntroUrl || '') === url;
        if (tabStillOpen && urlUnchanged) {
            const url3dUnchanged = (this.lastPlaceIntroUrl3d || '') === normalizedUrl3d;

            if (!url3dUnchanged) {
                try {
                    const mapIframe = document.querySelector('#mapContainer iframe');
                    if (mapIframe && mapIframe.contentWindow) {
                        this.safePostMessageToMap(mapIframe, {
                            type: 'snsPlaceModel',
                            data: {
                                url_3d: normalizedUrl3d,
                                url,
                                place_position: placePosition || this.lastPlaceIntroPosition,
                                place_position_by_map: placePositionByMap || this.lastPlaceIntroPositionByMap
                            }
                        }, this.getMapIframeTargetOrigin());
                    }
                } catch (e) {
                    console.warn('Failed to send snsPlaceModel to map iframe:', e);
                }
                this.lastPlaceIntroUrl3d = normalizedUrl3d;
                if (placePosition) {
                    this.lastPlaceIntroPosition = placePosition;
                }
                if (placePositionByMap) {
                    this.lastPlaceIntroPositionByMap = placePositionByMap;
                }
            }

            // Only switch to the tab without reloading.
            statusTabs.querySelectorAll('.status-tab').forEach(btn => {
                btn.classList.toggle('active', btn === placeTab);
            });

            statusTabContent.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.toggle('active', pane === placePane);
            });

            if (placeTab) {
                placeTab.scrollIntoView({
                    behavior: 'smooth',
                    block: 'nearest',
                    inline: 'center'
                });
            }

            console.log('Place intro tab already open with same URL, switched without reload:', url);
            return;
        }

        if (!placeTab) {
            // Create Place intro tab button
            placeTab = document.createElement('button');
            placeTab.className = 'status-tab';
            placeTab.dataset.tab = 'placeIntro';
            placeTab.innerHTML = `Place intro <span class="tab-close-btn" title="Close">×</span>`;
            statusTabs.appendChild(placeTab);

            // Bind close button event
            const closeBtn = placeTab.querySelector('.tab-close-btn');
            closeBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                if (placeTab) placeTab.remove();
                if (placePane) placePane.remove();

                try {
                    const mapIframe = document.querySelector('#mapContainer iframe');
                    if (mapIframe && mapIframe.contentWindow) {
                        self.safePostMessageToMap(mapIframe, {
                            type: 'snsPlaceModel',
                            data: {
                                url_3d: '',
                                url: ''
                            }
                        }, self.getMapIframeTargetOrigin());
                    }
                } catch (err) {
                    console.warn('Failed to unload snsPlaceModel on close:', err);
                }
                self.lastPlaceIntroUrl3d = '';
                self.lastPlaceIntroPosition = null;
                self.lastPlaceIntroPositionByMap = null;

                // Switch to the first tab (Process) — use exclusive toggle
                // to avoid leaving stale 'active' class on other tabs.
                const firstTab = statusTabs.querySelector('.status-tab');
                const firstPane = statusTabContent.querySelector('.tab-pane');
                if (firstTab && firstPane) {
                    statusTabs.querySelectorAll('.status-tab').forEach(btn => {
                        btn.classList.toggle('active', btn === firstTab);
                    });
                    statusTabContent.querySelectorAll('.tab-pane').forEach(pane => {
                        pane.classList.toggle('active', pane === firstPane);
                    });
                }
            });
        }

        if (!placePane) {
            // Create Place intro tab content
            placePane = document.createElement('div');
            placePane.className = 'tab-pane';
            placePane.dataset.tab = 'placeIntro';
            placePane.innerHTML = `
                <div class="profile-webview-container">
                    <iframe src="${url}" class="profile-webview" frameborder="0"></iframe>
                </div>
            `;
            statusTabContent.appendChild(placePane);
        } else {
            // Update URL of existing iframe
            const iframe = placePane.querySelector('.profile-webview');
            if (iframe) {
                iframe.src = url;
            }
        }

        this.lastPlaceIntroUrl = url;
        this.lastPlaceIntroUrl3d = normalizedUrl3d;
        this.lastPlaceIntroPosition = placePosition || null;
        this.lastPlaceIntroPositionByMap = placePositionByMap || null;

        try {
            const mapIframe = document.querySelector('#mapContainer iframe');
            if (mapIframe && mapIframe.contentWindow) {
                this.safePostMessageToMap(mapIframe, {
                    type: 'snsPlaceModel',
                    data: {
                        url_3d: normalizedUrl3d,
                        url,
                        place_position: placePosition || null,
                        place_position_by_map: placePositionByMap || null
                    }
                }, this.getMapIframeTargetOrigin());
            }
        } catch (e) {
            console.warn('Failed to send snsPlaceModel to map iframe:', e);
        }

        // Switch to Place intro tab
        statusTabs.querySelectorAll('.status-tab').forEach(btn => {
            btn.classList.toggle('active', btn === placeTab);
        });

        statusTabContent.querySelectorAll('.tab-pane').forEach(pane => {
            pane.classList.toggle('active', pane === placePane);
        });

        // Auto-scroll to the Place intro tab (ensure it's visible)
        if (placeTab) {
            placeTab.scrollIntoView({
                behavior: 'smooth',
                block: 'nearest',
                inline: 'center'
            });
        }

        console.log('Place intro tab opened with URL:', url);
    }
};
