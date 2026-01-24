/**
 * SNS Module - Main Page Content
 * SNS主内容渲染
 */

export default {
    /**
     * 渲染SNS页面主内容
     */
    render() {
        return `
            <div class="sns-page-layout">
                <!-- 地图主区域 -->
                <div class="sns-map-area">
                    <!-- 地图容器 -->
                    <div class="map-container" id="mapContainer">
                        <div class="map-placeholder">
                            <div class="map-placeholder-icon">
                                <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                                </svg>
                            </div>
                            <p class="map-placeholder-text">正在加载地图...</p>
                            <div class="map-placeholder-loader">
                                <div class="loader-dot"></div>
                                <div class="loader-dot"></div>
                                <div class="loader-dot"></div>
                            </div>
                        </div>
                    </div>

                    <!-- 现代化底部功能栏 -->
                    <div class="map-action-bar">
                        <!-- State 1: Default toolbar (menubar001 style) -->
                        <div class="action-bar-state-1" id="actionBarState1">
                            <div class="action-bar-left">
                                <button class="action-btn" data-action="home">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                                        <polyline points="9 22 9 12 15 12 15 22"/>
                                    </svg>
                                    <span>Home</span>
                                </button>
                                <button class="action-btn" data-action="square">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                        <circle cx="9" cy="7" r="4"/>
                                        <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                                    </svg>
                                    <span>Square</span>
                                </button>
                                <button class="action-btn" data-action="ai">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                                        <path d="M19 10H5a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-1a2 2 0 0 0-2-2z"/>
                                        <path d="M12 15v4M8 22h8"/>
                                    </svg>
                                    <span>AI</span>
                                </button>
                            </div>
                            <div class="action-bar-center">
                                <button class="action-btn-primary" id="snsStartBtn">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                        <path d="M8 5v14l11-7z"/>
                                    </svg>
                                    <span>Start</span>
                                </button>
                            </div>
                            <div class="action-bar-right">
                                <button class="action-btn" data-action="control" id="controlBtn">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                        <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                                        <line x1="8" y1="21" x2="16" y2="21"/>
                                        <line x1="12" y1="17" x2="12" y2="21"/>
                                    </svg>
                                    <span>Control</span>
                                </button>
                                <button class="action-btn" data-action="move">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" style="transform: rotate(-45deg)">
                                        <polygon points="3 11 22 2 13 21 11 13 3 11"/>
                                    </svg>
                                    <span>Move</span>
                                </button>
                                <button class="action-btn" data-action="board">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                        <line x1="3" y1="12" x2="21" y2="12"/>
                                        <line x1="3" y1="6" x2="21" y2="6"/>
                                        <line x1="3" y1="18" x2="21" y2="18"/>
                                    </svg>
                                    <span>Board</span>
                                </button>
                            </div>
                        </div>

                        <!-- State 2: Control mode toolbar (menubar002 style) -->
                        <div class="action-bar-state-2" id="actionBarState2" style="display: none;">
                            <div class="action-bar-control-layout">
                                <div class="control-left-menu">
                                    <button class="control-menu-btn" id="appsMenuBtn">
                                        <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor">
                                            <rect x="3" y="3" width="7" height="7"/>
                                            <rect x="14" y="3" width="7" height="7"/>
                                            <rect x="14" y="14" width="7" height="7"/>
                                            <rect x="3" y="14" width="7" height="7"/>
                                        </svg>
                                    </button>
                                    <div class="control-dropdown" id="appsDropdown" style="display: none;">
                                        <button class="dropdown-item" data-action="home">
                                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                                                <polyline points="9 22 9 12 15 12 15 22"/>
                                            </svg>
                                            <span>Home</span>
                                        </button>
                                        <button class="dropdown-item" data-action="square">
                                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                                <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                                <circle cx="9" cy="7" r="4"/>
                                                <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                                            </svg>
                                            <span>Square</span>
                                        </button>
                                        <button class="dropdown-item" data-action="ai">
                                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                                <path d="M12 2a3 3 0 0 0-3 3v1a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3z"/>
                                                <path d="M19 10H5a2 2 0 0 0-2 2v1a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-1a2 2 0 0 0-2-2z"/>
                                                <path d="M12 15v4M8 22h8"/>
                                            </svg>
                                            <span>AI</span>
                                        </button>
                                    </div>
                                </div>
                                <div class="control-center-input">
                                    <button class="control-computer-btn" id="computerBtn">
                                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                            <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
                                            <line x1="8" y1="21" x2="16" y2="21"/>
                                            <line x1="12" y1="17" x2="12" y2="21"/>
                                        </svg>
                                    </button>
                                    <div class="control-input-group">
                                        <div class="control-toggle-group">
                                            <span class="control-label">Talk to</span>
                                            <div class="control-toggle-buttons">
                                                <button class="toggle-btn active" data-mode="ai">AI</button>
                                                <button class="toggle-btn" data-mode="friends">Friends</button>
                                            </div>
                                        </div>
                                        <div class="control-input-wrapper">
                                            <input type="text" class="control-input" placeholder="Human input..." />
                                            <button class="control-send-btn">
                                                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                                    <line x1="22" y1="2" x2="11" y2="13"/>
                                                    <polygon points="22 2 15 22 11 13 2 9 22 2"/>
                                                </svg>
                                            </button>
                                        </div>
                                    </div>
                                </div>
                                <div class="control-right-menu">
                                    <button class="control-menu-btn" id="mapMenuBtn">
                                        <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
                                            <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"/>
                                            <line x1="8" y1="2" x2="8" y2="18"/>
                                            <line x1="16" y1="6" x2="16" y2="22"/>
                                        </svg>
                                    </button>
                                    <div class="control-dropdown control-dropdown-right" id="mapDropdown" style="display: none;">
                                        <button class="dropdown-item" data-action="board">
                                            <span>Board</span>
                                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                                <line x1="3" y1="12" x2="21" y2="12"/>
                                                <line x1="3" y1="6" x2="21" y2="6"/>
                                                <line x1="3" y1="18" x2="21" y2="18"/>
                                            </svg>
                                        </button>
                                        <button class="dropdown-item" data-action="move">
                                            <span>Move</span>
                                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" style="transform: rotate(45deg)">
                                                <polygon points="3 11 22 2 13 21 11 13 3 11"/>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- 地图控制按钮组已移除 -->
                </div>

                <!-- 右侧状态面板收缩条 -->
                <div class="sns-panel-resizer" id="snsPanelResizer">
                    <div class="panel-resizer-handle">
                        <div class="panel-resizer-line"></div>
                    </div>
                    <button class="panel-collapse-btn" id="snsPanelCollapseBtn" title="折叠状态面板">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="9,6 15,12 9,18"/>
                        </svg>
                    </button>
                </div>

                <!-- 右侧状态面板 -->
                <div class="sns-status-panel" id="snsStatusPanel">
                    <!-- 页签内容区域 - 整个面板内容随页签切换 -->
                    <div class="status-tab-content" id="statusTabContent">
                        <!-- Process 页签内容 -->
                        <div class="tab-pane active" data-tab="process">
                            <!-- Configuration Buttons -->
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94L14.4 2.81c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/></svg> Configuration</div>
                                <div class="config-buttons">
                                    <button class="config-btn" id="snsAvatarConfigBtn">
                                        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                            <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                                        </svg>
                                        <span>用户配置</span>
                                    </button>
                                    <button class="config-btn" id="snsProfessionConfigBtn">
                                        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                            <path d="M20 6h-4V4c0-1.11-.89-2-2-2h-4c-1.11 0-2 .89-2 2v2H4c-1.11 0-1.99.89-1.99 2L2 19c0 1.11.89 2 2 2h16c1.11 0 2-.89 2-2V8c0-1.11-.89-2-2-2zm-6 0h-4V4h4v2z"/>
                                        </svg>
                                        <span>职业选择</span>
                                    </button>
                                    <button class="config-btn" id="snsSocialRoleConfigBtn">
                                        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                            <path d="M16 11c1.66 0 2.99-1.34 2.99-3S17.66 5 16 5c-1.66 0-3 1.34-3 3s1.34 3 3 3zm-8 0c1.66 0 2.99-1.34 2.99-3S9.66 5 8 5C6.34 5 5 6.34 5 8s1.34 3 3 3zm0 2c-2.33 0-7 1.17-7 3.5V19h14v-2.5c0-2.33-4.67-3.5-7-3.5zm8 0c-.29 0-.62.02-.97.05 1.16.84 1.97 1.97 1.97 3.45V19h6v-2.5c0-2.33-4.67-3.5-7-3.5z"/>
                                        </svg>
                                        <span>社交角色</span>
                                    </button>
                                    <button class="config-btn" id="snsMapConfigBtn">
                                        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                            <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z"/>
                                        </svg>
                                        <span>地图配置</span>
                                    </button>
                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg> Current Status</div>
                                <div class="status-rows">
                                    <div class="status-row"><span>💰 Money</span><span class="value">: 10,996.61</span></div>
                                    <div class="status-row"><span>❤️ Life</span><span class="value">: 125</span></div>
                                    <div class="status-row"><span>⚡ Energy</span><span class="value">: 150</span></div>
                                    <div class="status-row"><span>👤 Profession</span><span class="value">: 医生 (*需要800元开办费)</span></div>
                                    <div class="status-row"><span>📍 Location</span></div>
                                    <div class="status-row sub"><span>lng</span><span class="value">: 116.36383031947238</span></div>
                                    <div class="status-row sub"><span>lat</span><span class="value">: 39.76458567198844</span></div>
                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2z"/></svg> On Going</div>
                                <div class="status-rows"><span class="na">N/A</span></div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M13 3c-4.97 0-9 4.03-9 9H1l3.89 3.89.07.14L9 12H6c0-3.87 3.13-7 7-7s7 3.13 7 7-3.13 7-7 7c-1.93 0-3.68-.79-4.94-2.06l-1.42 1.42C8.27 19.99 10.51 21 13 21c4.97 0 9-4.03 9-9s-4.03-9-9-9z"/></svg> Process History</div>
                                <div class="status-rows"><span class="na">N/A</span></div>
                            </div>
                        </div>
                        <!-- Resource 页签内容 -->
                        <div class="tab-pane" data-tab="resource">
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-4 14h-2v-4H7v-2h6V7h2v4h4v2h-4v4z"/></svg> Resource Overview</div>
                                <div class="status-rows">
                                    <div class="status-row"><span>🔋 CPU Usage</span><span class="value">: 45%</span></div>
                                    <div class="status-row"><span>💾 Memory</span><span class="value">: 2.3 GB / 8 GB</span></div>
                                    <div class="status-row"><span>💿 Disk</span><span class="value">: 120 GB / 500 GB</span></div>
                                    <div class="status-row"><span>📶 Network</span><span class="value">: Connected</span></div>
                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M4 6h18V4H4c-1.1 0-2 .9-2 2v11H0v3h14v-3H4V6z"/></svg> System Info</div>
                                <div class="status-rows">
                                    <div class="status-row"><span>🖥️ OS</span><span class="value">: Linux 5.15</span></div>
                                    <div class="status-row"><span>⏱️ Uptime</span><span class="value">: 3d 12h 45m</span></div>
                                    <div class="status-row"><span>🌡️ Temperature</span><span class="value">: 42°C</span></div>
                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M15 21h-2v-2h2v2zm-2-7h-2v5h2v-5zm8-2h-2v7h2v-7zm-2-2h-2v2h2v-2zM7 21H3v-6h4v6zm-2-4H5v2h2v-2zm2-6H3v4h4v-4zm-2 2H5v2h2v-2zM3 3v6h4V3H3zm2 4H5V5h2v2z"/></svg> Network Stats</div>
                                <div class="status-rows">
                                    <div class="status-row"><span>⬆️ Upload</span><span class="value">: 1.2 MB/s</span></div>
                                    <div class="status-row"><span>⬇️ Download</span><span class="value">: 5.8 MB/s</span></div>
                                    <div class="status-row"><span>📡 Latency</span><span class="value">: 32ms</span></div>
                                </div>
                            </div>
                        </div>
                        <!-- Think 页签内容 -->
                        <div class="tab-pane" data-tab="think">
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg> AI Model</div>
                                <div class="status-rows">
                                    <div class="status-row"><span>🧠 Model</span><span class="value">: GPT-4</span></div>
                                    <div class="status-row"><span>💭 Status</span><span class="value">: Idle</span></div>
                                    <div class="status-row"><span>🔧 Mode</span><span class="value">: Auto</span></div>
                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg> Thinking Log</div>
                                <div class="status-rows">
                                    <div class="status-row"><span>📝 Last Action</span><span class="value">: N/A</span></div>
                                    <div class="status-row"><span>🕐 Last Update</span><span class="value">: --:--:--</span></div>
                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-7 14l-5-5 1.41-1.41L12 14.17l4.59-4.58L18 11l-6 6z"/></svg> Decision Queue</div>
                                <div class="status-rows"><span class="na">No pending decisions</span></div>
                            </div>
                        </div>
                    </div>
                    <!-- 底部页签按钮 -->
                    <div class="status-tabs" id="statusTabs">
                        <button class="status-tab active" data-tab="process">Process</button>
                        <button class="status-tab" data-tab="resource">Resource</button>
                        <button class="status-tab" data-tab="think">Think</button>
                    </div>
                </div>
            </div>
        `;
    }
};
