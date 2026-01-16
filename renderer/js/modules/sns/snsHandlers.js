/**
 * SNS Module - Event Handlers
 * SNS事件处理和初始化
 */

import snsState from './snsState.js';
import snsApi from './snsApi.js';

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
        this.initSNSActionBar();
    },

    /**
     * 销毁SNS页面
     */
    destroy() {
        // 清理事件监听器
        this.cleanupMapListeners();
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
            startBtn.addEventListener('click', () => {
                startBtn.classList.toggle('running');
                const isRunning = startBtn.classList.contains('running');
                startBtn.innerHTML = isRunning
                    ? `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><rect x="6" y="4" width="4" height="16"/><rect x="14" y="4" width="4" height="16"/></svg><span>Pause</span>`
                    : `<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M8 5v14l11-7z"/></svg><span>Start</span>`;
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
    loadBaiduMap() {
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

        // 创建 iframe 加载地图页面
        const iframe = document.createElement('iframe');
        iframe.src = 'http://localhost:8788/scripts/map.html';
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
    }
};
