/**
 * SNS Module - Event Handlers
 * SNS事件处理和初始化
 */

import snsState from './snsState.js';
import snsApi from './snsApi.js';
import { SNSAvatarDialog } from './SNSAvatarDialog.js';
import { SNSProfessionDialog } from './SNSProfessionDialog.js';
import { SNSSocialRoleDialog } from './SNSSocialRoleDialog.js';
import { SNSMapConfigDialog } from './SNSMapConfigDialog.js';

export default {
    /**
     * 初始化SNS页面
     */
    init() {
        console.log('SNS 页面控制器初始化');
        this.loadBaiduMap();
        this.loadSNSData();
        this.initSNSPanelResizer();
        this.initSNSStatusTabs();
        this.initSNSToolbar();
        this.initSNSSettingsPanel();
        this.initConfigButtons();
        this.initSNSActionBar();
        this.initMapReloadListener();
        this.initSNSUpdateListener();
    },

    /**
     * 销毁SNS页面
     */
    destroy() {
        // 清理事件监听器
        this.cleanupMapListeners();

        // 移除 SNS 更新监听器
        if (this.snsUpdateListener) {
            window.removeEventListener('websocket-message', this.snsUpdateListener);
        }
    },

    /**
     * 初始化顶部工具栏收缩功能
     */
    initSNSToolbar() {
        const toolbar = document.getElementById('snsToolbar');
        const collapseBtn = document.getElementById('toolbarCollapseBtn');
        const expandBtn = document.getElementById('toolbarExpandBtn');
        const mapArea = document.querySelector('.sns-map-area');

        if (!toolbar || !collapseBtn || !expandBtn || !mapArea) return;

        // 从 localStorage 恢复状态
        const savedCollapsed = localStorage.getItem('snsToolbarCollapsed') === 'true';
        if (savedCollapsed) {
            toolbar.classList.add('collapsed');
            mapArea.classList.add('toolbar-hidden');
        }

        // 收起工具栏
        collapseBtn.addEventListener('click', () => {
            toolbar.classList.add('collapsed');
            mapArea.classList.add('toolbar-hidden');
            localStorage.setItem('snsToolbarCollapsed', 'true');
        });

        // 展开工具栏
        expandBtn.addEventListener('click', () => {
            toolbar.classList.remove('collapsed');
            mapArea.classList.remove('toolbar-hidden');
            localStorage.setItem('snsToolbarCollapsed', 'false');
        });
    },

    /**
     * 初始化右侧设置面板收缩功能
     */
    initSNSSettingsPanel() {
        const panel = document.getElementById('mapSettingsPanel');
        const collapseBtn = document.getElementById('settingsCollapseBtn');
        const expandBtn = document.getElementById('settingsExpandBtn');
        const mapArea = document.querySelector('.sns-map-area');

        if (!panel || !collapseBtn || !expandBtn || !mapArea) return;

        // 从 localStorage 恢复状态
        const savedCollapsed = localStorage.getItem('snsSettingsPanelCollapsed') === 'true';
        if (savedCollapsed) {
            panel.classList.add('collapsed');
            mapArea.classList.add('settings-hidden');
        }

        // 收起设置面板
        collapseBtn.addEventListener('click', () => {
            panel.classList.add('collapsed');
            mapArea.classList.add('settings-hidden');
            localStorage.setItem('snsSettingsPanelCollapsed', 'true');
        });

        // 展开设置面板
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
            avatarBtn.addEventListener('click', async () => {
                const dialog = new SNSAvatarDialog();
                await dialog.show();
            });
        }

        // Profession configuration button
        const professionBtn = document.getElementById('snsProfessionConfigBtn');
        if (professionBtn) {
            professionBtn.addEventListener('click', async () => {
                const dialog = new SNSProfessionDialog();
                await dialog.show();
            });
        }

        // Social role configuration button
        const socialRoleBtn = document.getElementById('snsSocialRoleConfigBtn');
        if (socialRoleBtn) {
            socialRoleBtn.addEventListener('click', async () => {
                const dialog = new SNSSocialRoleDialog();
                await dialog.show();
            });
        }

        // Map configuration button
        const mapConfigBtn = document.getElementById('snsMapConfigBtn');
        if (mapConfigBtn) {
            mapConfigBtn.addEventListener('click', async () => {
                const dialog = new SNSMapConfigDialog();
                await dialog.show();
            });
        }
    },

    /**
     * 初始化地图重新加载监听器
     */
    initMapReloadListener() {
        window.addEventListener('reloadMap', () => {
            console.log('Received reloadMap event - reloading map');
            this.loadBaiduMap();
        });
    },

    /**
     * 初始化底部动作栏
     */
    initSNSActionBar() {
        const actionBar = document.querySelector('.map-action-bar');
        if (!actionBar) return;

        const state1 = document.getElementById('actionBarState1');
        const state2 = document.getElementById('actionBarState2');
        const controlBtn = document.getElementById('controlBtn');
        const computerBtn = document.getElementById('computerBtn');
        const appsMenuBtn = document.getElementById('appsMenuBtn');
        const mapMenuBtn = document.getElementById('mapMenuBtn');
        const appsDropdown = document.getElementById('appsDropdown');
        const mapDropdown = document.getElementById('mapDropdown');

        // Toggle between state 1 and state 2
        const switchToState2 = () => {
            if (state1 && state2) {
                state1.style.display = 'none';
                state2.style.display = 'block';
            }
        };

        const switchToState1 = () => {
            if (state1 && state2) {
                state1.style.display = 'flex';
                state2.style.display = 'none';
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
            });
        });

        // 动作按钮点击事件
        actionBar.addEventListener('click', (e) => {
            const btn = e.target.closest('.action-btn, .dropdown-item');
            if (!btn) return;

            const action = btn.dataset.action;
            if (!action) return;

            // 更新激活状态
            const allBtns = actionBar.querySelectorAll('.action-btn');
            allBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Close dropdowns after selection
            if (appsDropdown) appsDropdown.style.display = 'none';
            if (mapDropdown) mapDropdown.style.display = 'none';

            // 处理不同的动作
            console.log('SNS Action:', action);
        });

        // Start 按钮
        const startBtn = document.getElementById('snsStartBtn');
        if (startBtn) {
            startBtn.addEventListener('click', async () => {
                const isRunning = startBtn.classList.contains('running');

                if (!isRunning) {
                    // 启动引擎
                    startBtn.disabled = true;
                    startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/></svg><span>Starting...</span>`;

                    try {
                        const result = await snsApi.startEngine();

                        if (result.success) {
                            startBtn.classList.add('running');
                            startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Pause</span>`;
                            this.showToast('AI社交引擎已启动', 'success');
                        } else {
                            startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Start</span>`;
                            this.showToast(`启动失败: ${result.message}`, 'error');
                        }
                    } catch (error) {
                        console.error('启动引擎失败:', error);
                        startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Start</span>`;
                        this.showToast(`启动失败: ${error.message}`, 'error');
                    } finally {
                        startBtn.disabled = false;
                    }
                } else {
                    // 停止引擎
                    startBtn.disabled = true;
                    startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><circle cx="12" cy="12" r="10" opacity="0.3"/></svg><span>Stopping...</span>`;

                    try {
                        const result = await snsApi.stopEngine();

                        if (result.success) {
                            startBtn.classList.remove('running');
                            startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Start</span>`;
                            this.showToast('AI社交引擎已停止', 'success');
                        } else {
                            startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Pause</span>`;
                            this.showToast(`停止失败: ${result.message}`, 'error');
                        }
                    } catch (error) {
                        console.error('停止引擎失败:', error);
                        startBtn.innerHTML = `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Pause</span>`;
                        this.showToast(`停止失败: ${error.message}`, 'error');
                    } finally {
                        startBtn.disabled = false;
                    }
                }
            });
        }

        // Control Send 按钮
        const sendBtn = actionBar.querySelector('.control-send-btn');
        const inputField = actionBar.querySelector('.control-input');
        if (sendBtn && inputField) {
            const handleSend = async () => {
                const message = inputField.value.trim();
                if (!message) return;

                // 获取当前模式
                const activeToggle = actionBar.querySelector('.toggle-btn.active');
                const mode = activeToggle ? activeToggle.dataset.mode : 'ai';

                // 清空输入框
                inputField.value = '';

                try {
                    // 调用AI服务 - 使用第一个可用的agent
                    const result = await snsApi.chatWithAI('1', message, mode);

                    if (result.success) {
                        // 显示回复
                        this.showToast(result.reply);
                    } else {
                        this.showToast(`错误: ${result.error || '未知错误'}`, 'error');
                    }
                } catch (error) {
                    console.error('发送消息失败:', error);
                    this.showToast(`发送失败: ${error.message}`, 'error');
                }
            };

            sendBtn.addEventListener('click', handleSend);
            inputField.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') {
                    handleSend();
                }
            });
        }
    },

    /**
     * 初始化右侧面板收缩功能
     */
    initSNSPanelResizer() {
        const resizer = document.getElementById('snsPanelResizer');
        const collapseBtn = document.getElementById('snsPanelCollapseBtn');
        const statusPanel = document.getElementById('snsStatusPanel');

        if (!resizer || !collapseBtn || !statusPanel) return;

        // 从 localStorage 恢复面板状态
        const savedCollapsed = localStorage.getItem('snsPanelCollapsed') === 'true';
        if (savedCollapsed) {
            resizer.classList.add('collapsed');
            statusPanel.classList.add('collapsed');
        }

        // 折叠/展开按钮点击事件
        collapseBtn.addEventListener('click', (e) => {
            e.stopPropagation();
            const isCollapsed = statusPanel.classList.toggle('collapsed');
            resizer.classList.toggle('collapsed', isCollapsed);
            localStorage.setItem('snsPanelCollapsed', isCollapsed);
        });

        // 拖拽调整面板宽度
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
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            // 向左拖拽增加宽度,向右拖拽减少宽度
            const deltaX = startX - e.clientX;
            const newWidth = Math.max(200, Math.min(500, startWidth + deltaX));
            statusPanel.style.width = `${newWidth}px`;
        });

        document.addEventListener('mouseup', () => {
            if (isResizing) {
                isResizing = false;
                resizer.classList.remove('resizing');
                document.body.style.cursor = '';
                document.body.style.userSelect = '';
            }
        });
    },

    /**
     * 初始化状态页签切换
     */
    initSNSStatusTabs() {
        const tabsContainer = document.getElementById('statusTabs');
        const tabContent = document.getElementById('statusTabContent');

        if (!tabsContainer || !tabContent) return;

        tabsContainer.addEventListener('click', (e) => {
            const tabBtn = e.target.closest('.status-tab');
            if (!tabBtn) return;

            const targetTab = tabBtn.dataset.tab;
            if (!targetTab) return;

            // 更新按钮激活状态
            tabsContainer.querySelectorAll('.status-tab').forEach(btn => {
                btn.classList.toggle('active', btn === tabBtn);
            });

            // 切换内容面板
            tabContent.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.toggle('active', pane.dataset.tab === targetTab);
            });
        });
    },

    /**
     * 加载百度地图
     */
    async loadBaiduMap() {
        const mapContainer = document.getElementById('mapContainer');
        if (!mapContainer) {
            console.error('地图容器未找到');
            return;
        }

        console.log('加载地图');

        // 立即显示地图内容，不显示加载动画
        const placeholder = mapContainer.querySelector('.map-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // 检查地图是否已经加载过
        const existingIframe = mapContainer.querySelector('iframe');
        if (existingIframe) {
            console.log('地图已加载，直接显示');
            return;
        }

        // 获取地图配置
        let mapUrl = 'http://localhost:8788/scripts/map.html'; // 默认百度地图
        try {
            const response = await fetch('http://localhost:8788/api/sns/map-config');
            const result = await response.json();

            console.log('Map config API response:', result);

            if (result.success && result.data) {
                const mapType = String(result.data.map_type).trim();
                console.log('Map type:', mapType);

                if (mapType === '0') {
                    mapUrl = 'http://localhost:8788/scripts/googlemap3d.html';
                    console.log('Loading Google Map');
                } else {
                    console.log('Loading Baidu Map');
                }
            }
        } catch (error) {
            console.error('Failed to fetch map config:', error);
        }

        console.log('Final map URL:', mapUrl);

        // 创建 iframe 加载地图页面
        const iframe = document.createElement('iframe');
        iframe.src = mapUrl;
        iframe.style.width = '100%';
        iframe.style.height = '100%';
        iframe.style.border = 'none';
        iframe.style.display = 'block';
        iframe.style.backgroundColor = 'white';
        iframe.style.minHeight = '500px';
        iframe.style.zIndex = '1';

        mapContainer.appendChild(iframe);

        // 等待 iframe 加载完成后建立通信
        iframe.onload = () => {
            console.log('地图页面加载完成');

            // 向 iframe 发送初始数据
            const initialData = {
                type: 'init',
                data: {
                    message: 'Hello from AI-SNS Electron App!',
                    timestamp: Date.now()
                }
            };

            try {
                iframe.contentWindow.postMessage(initialData, 'http://localhost:8788');
                console.log('已发送初始化消息');
            } catch (error) {
                console.error('发送消息到地图页面失败:', error);
            }
        };

        // 监听 iframe 加载失败
        iframe.onerror = () => {
            console.error('地图页面加载失败');
            this.showMapError(mapContainer);
        };

        // 监听来自 iframe 的消息
        const handleMessage = (event) => {
            if (event.origin === 'http://localhost:8788') {
                const data = event.data;
                console.log('收到地图页面消息:', data);

                switch (data.type) {
                    case 'locationUpdate':
                        this.handleLocationUpdate(data.data);
                        break;
                    case 'mapClick':
                        this.handleMapClick(data.data);
                        break;
                    case 'markerAdd':
                        this.handleMarkerAdd(data.data);
                        break;
                    default:
                        console.log('未知消息类型:', data.type);
                }
            }
        };

        window.addEventListener('message', handleMessage);
        iframe._messageListener = handleMessage;
    },

    /**
     * 显示地图加载错误
     */
    showMapError(mapContainer) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'map-placeholder';
        errorDiv.style.zIndex = '10';
        errorDiv.innerHTML = `
            <div class="map-placeholder-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/>
                </svg>
            </div>
            <p class="map-placeholder-text">地图加载失败</p>
            <p class="map-placeholder-desc">请检查地图服务器是否运行在 http://localhost:8788</p>
            <button class="map-retry-btn" id="mapRetryBtn">重试</button>
        `;
        mapContainer.appendChild(errorDiv);

        // 绑定重试按钮
        const retryBtn = errorDiv.querySelector('#mapRetryBtn');
        if (retryBtn) {
            retryBtn.addEventListener('click', () => this.tryLoadMap());
        }
    },

    /**
     * 重试加载地图
     */
    tryLoadMap() {
        const mapContainer = document.getElementById('mapContainer');
        if (!mapContainer) return;

        console.log('尝试重新加载地图');

        // 移除现有的iframe
        const existingIframe = mapContainer.querySelector('iframe');
        if (existingIframe) {
            if (existingIframe._messageListener) {
                window.removeEventListener('message', existingIframe._messageListener);
            }
            existingIframe.remove();
        }

        // 移除现有的错误提示
        const existingErrorDiv = mapContainer.querySelector('.map-placeholder');
        if (existingErrorDiv) {
            existingErrorDiv.remove();
        }

        // 创建新的加载动画
        const loadingDiv = document.createElement('div');
        loadingDiv.className = 'map-placeholder';
        loadingDiv.innerHTML = `
            <div class="map-placeholder-icon">
                <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/>
                </svg>
            </div>
            <p class="map-placeholder-text">正在加载地图...</p>
            <div class="map-placeholder-loader">
                <div class="loader-dot"></div>
                <div class="loader-dot"></div>
                <div class="loader-dot"></div>
            </div>
        `;
        mapContainer.appendChild(loadingDiv);

        // 延迟调用loadBaiduMap
        setTimeout(() => {
            this.loadBaiduMap();
        }, 500);
    },

    /**
     * 处理位置更新
     */
    handleLocationUpdate(data) {
        console.log('位置更新:', data);
        const lngElement = document.querySelector('.status-row.sub span[class="value"]');
        const latElement = document.querySelectorAll('.status-row.sub span[class="value"]')[1];
        if (lngElement && data.lng) {
            lngElement.textContent = `: ${data.lng}`;
        }
        if (latElement && data.lat) {
            latElement.textContent = `: ${data.lat}`;
        }
    },

    /**
     * 处理地图点击事件
     */
    handleMapClick(data) {
        console.log('地图点击:', data);
    },

    /**
     * 处理添加标记事件
     */
    handleMarkerAdd(data) {
        console.log('添加标记:', data);
    },

    /**
     * 向地图页面发送消息
     */
    sendMessageToMap(type, data) {
        const iframe = document.querySelector('#mapContainer iframe');
        if (iframe && iframe.contentWindow) {
            const message = {
                type: type,
                data: data
            };
            iframe.contentWindow.postMessage(message, 'http://localhost:8788');
        }
    },

    /**
     * 加载SNS数据
     */
    loadSNSData() {
        // 模拟加载SNS数据
        const updateValue = (id, value) => {
            const el = document.getElementById(id);
            if (el) el.textContent = value;
        };

        updateValue('onlineNodes', Math.floor(Math.random() * 100) + 50);
        updateValue('activeUsers', Math.floor(Math.random() * 500) + 100);
        updateValue('messageCount', Math.floor(Math.random() * 10000) + 1000);
    },

    /**
     * 清理地图监听器
     */
    cleanupMapListeners() {
        const iframe = document.querySelector('#mapContainer iframe');
        if (iframe && iframe._messageListener) {
            window.removeEventListener('message', iframe._messageListener);
        }
    },

    /**
     * 显示Toast消息
     */
    showToast(message, type = 'success') {
        // 创建toast元素
        const toast = document.createElement('div');
        toast.className = `sns-toast sns-toast-${type}`;
        toast.textContent = message;

        // 添加样式
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${type === 'error' ? '#f44336' : '#4caf50'};
            color: white;
            padding: 16px 24px;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 10000;
            max-width: 400px;
            word-wrap: break-word;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(toast);

        // 3秒后自动移除
        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => {
                document.body.removeChild(toast);
            }, 300);
        }, 3000);
    },

    /**
     * 初始化SNS更新监听器（使用全局 WebSocket 事件）
     */
    initSNSUpdateListener() {
        // 监听全局 WebSocket 消息事件
        this.snsUpdateListener = (event) => {
            const message = event.detail;
            if (message.type === 'sns_update') {
                console.log('SNS update received:', message);
                this.handleSNSUpdate(message);
            }
        };

        window.addEventListener('websocket-message', this.snsUpdateListener);
        console.log('SNS update listener initialized');
    },

    /**
     * 处理SNS更新消息
     */
    handleSNSUpdate(data) {
        console.log('Handling SNS update:', data);
        const { tab, content, section } = data;

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
     * 更新Think页签内容
     */
    updateThinkTab(content) {
        console.log('updateThinkTab called with content:', content);
        // 找到Think页签的内容区域
        const thinkPane = document.querySelector('.tab-pane[data-tab="think"]');
        console.log('Think pane found:', thinkPane);
        if (!thinkPane) return;

        // 找到Thinking Log部分
        let thinkingLogSection = thinkPane.querySelector('.status-section:nth-child(2) .status-rows');
        console.log('Thinking log section found:', thinkingLogSection);
        if (!thinkingLogSection) return;

        // 创建新的内容元素
        const contentDiv = document.createElement('div');
        contentDiv.className = 'thinking-log-entry';
        contentDiv.style.cssText = `
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 12px;
            line-height: 1.5;
            padding: 8px;
            background: rgba(26, 115, 232, 0.05);
            border-left: 3px solid #1a73e8;
            margin-bottom: 8px;
            border-radius: 4px;
        `;
        contentDiv.textContent = content;

        // 如果是第一条内容，清除"N/A"
        if (thinkingLogSection.querySelector('.na')) {
            thinkingLogSection.innerHTML = '';
        }

        // 添加新内容
        thinkingLogSection.appendChild(contentDiv);

        // 滚动到底部
        thinkingLogSection.scrollTop = thinkingLogSection.scrollHeight;
        thinkingLogSection.scrollTop = thinkingLogSection.scrollHeight;
    },

    /**
     * 更新Process页签内容
     */
    updateProcessTab(content, section = null) {
        console.log('updateProcessTab called with content:', content, 'section:', section);
        // 找到Process页签的内容区域
        const processPane = document.querySelector('.tab-pane[data-tab="process"]');
        console.log('Process pane found:', processPane);
        if (!processPane) return;

        // 如果指定了 section，只更新特定部分
        if (section === 'ongoing') {
            this.updateOnGoingSection(processPane, content);
            return;
        } else if (section === 'history') {
            this.updateHistorySection(processPane, content);
            return;
        }

        // 否则，解析内容并更新两个部分
        const lines = content.split('\n');
        let onGoingContent = '';
        let processHistoryContent = '';
        let currentSection = '';

        for (const line of lines) {
            if (line.includes('⏳ On Going')) {
                currentSection = 'ongoing';
                continue;
            } else if (line.includes('📜 Process history')) {
                currentSection = 'history';
                continue;
            }

            if (currentSection === 'ongoing') {
                onGoingContent += line + '\n';
            } else if (currentSection === 'history') {
                processHistoryContent += line + '\n';
            }
        }

        if (onGoingContent.trim()) {
            this.updateOnGoingSection(processPane, onGoingContent.trim());
        }

        if (processHistoryContent.trim()) {
            this.updateHistorySection(processPane, processHistoryContent.trim());
        }
    },

    /**
     * 更新 On Going 部分
     */
    updateOnGoingSection(processPane, content) {
        const onGoingSection = processPane.querySelector('.status-section:nth-child(3) .status-rows');
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
            font-family: monospace;
            font-size: 12px;
            line-height: 1.5;
        `;
        onGoingDiv.textContent = content;
        onGoingSection.innerHTML = '';
        onGoingSection.appendChild(onGoingDiv);
        console.log('On Going section updated');
    },

    /**
     * 更新 Process History 部分
     */
    updateHistorySection(processPane, content) {
        const historySection = processPane.querySelector('.status-section:nth-child(4) .status-rows');
        if (!historySection) {
            console.warn('History section not found');
            return;
        }

        if (historySection.querySelector('.na')) {
            historySection.innerHTML = '';
        }

        const historyDiv = document.createElement('div');
        historyDiv.style.cssText = `
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 12px;
            line-height: 1.5;
        `;
        historyDiv.textContent = content;
        historySection.innerHTML = '';
        historySection.appendChild(historyDiv);
        console.log('History section updated');
    },

    /**
     * 更新 Resource 页签内容
     */
    updateResourceTab(content) {
        console.log('updateResourceTab called with content:', content);
        // 找到Resource页签的内容区域
        const resourcePane = document.querySelector('.tab-pane[data-tab="resource"]');
        console.log('Resource pane found:', resourcePane);
        if (!resourcePane) return;

        // 找到第一个 status-section（Resource Overview）
        const resourceSection = resourcePane.querySelector('.status-section:nth-child(1) .status-rows');
        console.log('Resource section found:', resourceSection);
        if (!resourceSection) return;

        // 清除 N/A 标记
        if (resourceSection.querySelector('.na')) {
            resourceSection.innerHTML = '';
        }

        // 创建内容元素
        const contentDiv = document.createElement('div');
        contentDiv.style.cssText = `
            white-space: pre-wrap;
            font-family: monospace;
            font-size: 12px;
            line-height: 1.5;
            max-height: 600px;
            overflow-y: auto;
        `;
        contentDiv.textContent = content;

        // 更新内容
        resourceSection.innerHTML = '';
        resourceSection.appendChild(contentDiv);
        console.log('Resource tab updated successfully');
    }
};
