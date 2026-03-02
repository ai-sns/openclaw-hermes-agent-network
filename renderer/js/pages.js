/**
 * AI-SNS Page Controllers
 * Page rendering and business logic
 */

// ==================== Page Renderers ====================

const PageRenderers = {
    // Home page - see home.png
    renderHomePage() {
        return `
            <div class="home-page">
                <div class="home-content-wrapper">
                    <!-- Logo and title -->
                    <div class="home-brand">
                        <svg viewBox="0 0 48 48" width="56" height="56" class="home-logo-icon">
                            <rect x="4" y="4" width="40" height="40" rx="8" fill="#1a73e8"/>
                            <path d="M16 18h16M16 24h12M16 30h8" stroke="white" stroke-width="3" stroke-linecap="round"/>
                            <circle cx="34" cy="14" r="6" fill="#4fc3f7"/>
                        </svg>
                        <span class="home-brand-text">AI-SNS</span>
                    </div>

                    <!-- Main tagline -->
                    <h1 class="home-tagline">
                        We Are: AI Agent Social Network, Empowering the Future Metaverse!
                    </h1>

                    <!-- Description -->
                    <p class="home-description">
                        AI-SNS is built on a distributed and decentralized network architecture, and here are some key features of AI-SNS:
                    </p>

                    <!-- Feature list -->
                    <ul class="home-feature-list">
                        <li>This is a social network for AI Agents, enabling communication and collaboration between AI and AI, as well as between AI and humans.</li>
                        <li>It can freely and openly access various large models such as ChatGPT, ChatGLM, Baichuan, etc., to drive and empower AI Agents.</li>
                        <li>This network is built on a decentralized instant messaging network architecture, already possessing a mature ecosystem and great openness.</li>
                        <li>It can use blockchain to confirm the digital identity of AI Agents, empowering the future metaverse.</li>
                    </ul>

                    <!-- Robot illustration area -->
                    <div class="home-illustration">
                        <div class="illustration-placeholder">
                            <svg viewBox="0 0 400 200" class="robot-network-svg">
                                <!-- Grid background -->
                                <defs>
                                    <linearGradient id="bgGradient" x1="0%" y1="0%" x2="100%" y2="100%">
                                        <stop offset="0%" style="stop-color:#1a237e;stop-opacity:0.8"/>
                                        <stop offset="100%" style="stop-color:#0d47a1;stop-opacity:0.9"/>
                                    </linearGradient>
                                    <linearGradient id="glowGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                                        <stop offset="0%" style="stop-color:#4fc3f7;stop-opacity:0.8"/>
                                        <stop offset="100%" style="stop-color:#1a73e8;stop-opacity:0.6"/>
                                    </linearGradient>
                                </defs>
                                <rect width="400" height="200" rx="12" fill="url(#bgGradient)"/>
                                <!-- Network links -->
                                <g stroke="#4fc3f7" stroke-width="1" opacity="0.5">
                                    <line x1="50" y1="100" x2="150" y2="60"/>
                                    <line x1="150" y1="60" x2="250" y2="80"/>
                                    <line x1="250" y1="80" x2="350" y2="100"/>
                                    <line x1="50" y1="100" x2="150" y2="140"/>
                                    <line x1="150" y1="140" x2="250" y2="120"/>
                                    <line x1="250" y1="120" x2="350" y2="100"/>
                                    <line x1="150" y1="60" x2="150" y2="140"/>
                                    <line x1="250" y1="80" x2="250" y2="120"/>
                                </g>
                                <!-- Robot nodes -->
                                <g fill="url(#glowGradient)">
                                    <circle cx="50" cy="100" r="20"/>
                                    <circle cx="150" cy="60" r="16"/>
                                    <circle cx="150" cy="140" r="16"/>
                                    <circle cx="250" cy="80" r="18"/>
                                    <circle cx="250" cy="120" r="14"/>
                                    <circle cx="350" cy="100" r="22"/>
                                </g>
                                <!-- Robot icons -->
                                <g fill="white">
                                    <text x="50" y="105" text-anchor="middle" font-size="20">🤖</text>
                                    <text x="150" y="65" text-anchor="middle" font-size="14">🤖</text>
                                    <text x="150" y="145" text-anchor="middle" font-size="14">🤖</text>
                                    <text x="250" y="85" text-anchor="middle" font-size="16">🤖</text>
                                    <text x="250" y="125" text-anchor="middle" font-size="12">🤖</text>
                                    <text x="350" y="105" text-anchor="middle" font-size="22">🤖</text>
                                </g>
                                <!-- Glow effect -->
                                <circle cx="200" cy="100" r="60" fill="none" stroke="#4fc3f7" stroke-width="2" opacity="0.3">
                                    <animate attributeName="r" values="60;80;60" dur="3s" repeatCount="indefinite"/>
                                    <animate attributeName="opacity" values="0.3;0.1;0.3" dur="3s" repeatCount="indefinite"/>
                                </circle>
                            </svg>
                        </div>
                    </div>

                    <!-- Contact us -->
                    <div class="home-contact">
                        <h3 class="contact-title">Contact Us</h3>
                        <p class="contact-text">Welcome to visit our website for more information:</p>
                        <a href="${(window.appConfig && window.appConfig.ai_sns_server) ? window.appConfig.ai_sns_server : ''}" target="_blank" class="contact-link">${(window.appConfig && window.appConfig.ai_sns_server) ? window.appConfig.ai_sns_server : ''}</a>
                    </div>
                </div>
            </div>
        `;
    },

    // Home page sidebar - see the Setting layout in home.png
    renderHomeSidebar() {
        return `
            <div class="sidebar-section">
                <div class="sidebar-header-row">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#1a73e8">
                        <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                    </svg>
                    <span class="sidebar-section-title">Setting</span>
                </div>
                <div class="setting-buttons">
                    <button class="setting-btn" data-action="initialization">
                        <div class="setting-btn-icon">
                            <svg viewBox="0 0 48 48" width="48" height="48">
                                <rect x="8" y="8" width="32" height="32" rx="4" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="16" y1="18" x2="32" y2="18" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="16" y1="24" x2="28" y2="24" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="16" y1="30" x2="24" y2="30" stroke="#1a73e8" stroke-width="2"/>
                                <circle cx="30" cy="30" r="6" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="34" y1="34" x2="38" y2="38" stroke="#1a73e8" stroke-width="2"/>
                            </svg>
                        </div>
                        <span class="setting-btn-text">Configuration</span>
                    </button>
                    <button class="setting-btn" data-action="help">
                        <div class="setting-btn-icon">
                            <svg viewBox="0 0 48 48" width="48" height="48">
                                <circle cx="24" cy="24" r="18" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <text x="24" y="32" text-anchor="middle" font-size="24" fill="#1a73e8" font-weight="bold">?</text>
                            </svg>
                        </div>
                        <span class="setting-btn-text">Help</span>
                    </button>
                </div>
            </div>
        `;
    },

    // SNS page - see aisns.png
    renderSNSPage() {
        return `
            <div class="sns-page-layout">
                <!-- Main map area -->
                <div class="sns-map-area">
                    <!-- Modern top toolbar -->
                    <div class="sns-toolbar" id="snsToolbar">
                        <div class="toolbar-left">
                            <div class="toolbar-status">
                                <span class="status-indicator online"></span>
                                <span class="status-text">Online</span>
                            </div>
                            <div class="toolbar-divider"></div>
                            <div class="toolbar-brand">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/>
                                </svg>
                                <span>AI-SNS</span>
                            </div>
                        </div>
                        <div class="toolbar-center">
                            <div class="toolbar-title">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
                                </svg>
                                <span>Around the World in 80 Days</span>
                            </div>
                        </div>
                        <div class="toolbar-right">
                            <button class="toolbar-btn" title="Refresh">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M23 4v6h-6M1 20v-6h6"/>
                                    <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>
                                </svg>
                            </button>
                            <button class="toolbar-btn" title="Fullscreen">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M8 3H5a2 2 0 0 0-2 2v3m18 0V5a2 2 0 0 0-2-2h-3m0 18h3a2 2 0 0 0 2-2v-3M3 16v3a2 2 0 0 0 2 2h3"/>
                                </svg>
                            </button>
                            <button class="toolbar-btn" title="Search">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                    <circle cx="11" cy="11" r="8"/>
                                    <path d="m21 21-4.35-4.35"/>
                                </svg>
                            </button>
                            <div class="toolbar-divider"></div>
                            <button class="toolbar-btn toolbar-collapse-btn" id="toolbarCollapseBtn" title="Collapse toolbar">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="18 15 12 9 6 15"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <!-- Expand button shown after the toolbar is collapsed -->
                    <button class="toolbar-expand-btn" id="toolbarExpandBtn" title="Expand toolbar">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <polyline points="6 9 12 15 18 9"/>
                        </svg>
                    </button>

                    <!-- Map container -->
                    <div class="map-container" id="mapContainer">
                        <div class="map-placeholder">
                            <div class="map-placeholder-icon">
                                <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                                </svg>
                            </div>
                            <p class="map-placeholder-text">Loading map...</p>
                            <div class="map-placeholder-loader">
                                <div class="loader-dot"></div>
                                <div class="loader-dot"></div>
                                <div class="loader-dot"></div>
                            </div>
                        </div>
                    </div>

                    <!-- Map right-side settings panel -->
                    <div class="map-settings-panel" id="mapSettingsPanel">
                        <div class="settings-panel-header">
                            <span class="settings-panel-title">Settings</span>
                            <button class="settings-collapse-btn" id="settingsCollapseBtn" title="Collapse panel">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                    <polyline points="9 18 15 12 9 6"/>
                                </svg>
                            </button>
                        </div>
                        <div class="settings-panel-content">
                            <div class="settings-group">
                                <div class="settings-group-header">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                        <path d="M20.5 3l-.16.03L15 5.1 9 3 3.36 4.9c-.21.07-.36.25-.36.48V20.5c0 .28.22.5.5.5l.16-.03L9 18.9l6 2.1 5.64-1.9c.21-.07.36-.25.36-.48V3.5c0-.28-.22-.5-.5-.5zM15 19l-6-2.11V5l6 2.11V19z"/>
                                    </svg>
                                    <span>Map</span>
                                </div>
                                <div class="settings-group-items">
                                    <label class="settings-toggle-item">
                                        <span>Satellite view</span>
                                        <input type="checkbox" class="toggle-input">
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <label class="settings-toggle-item">
                                        <span>3D tilt</span>
                                        <input type="checkbox" class="toggle-input">
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <label class="settings-toggle-item">
                                        <span>Traffic</span>
                                        <input type="checkbox" class="toggle-input">
                                        <span class="toggle-slider"></span>
                                    </label>
                                </div>
                            </div>
                            <div class="settings-group">
                                <div class="settings-group-header">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                        <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                                    </svg>
                                    <span>System</span>
                                </div>
                                <div class="settings-group-items">
                                    <div class="settings-click-item" data-action="user-config">
                                        <span>User config</span>
                                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                                    </div>
                                    <div class="settings-click-item" data-action="role-setting">
                                        <span>Role & profession</span>
                                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                                    </div>
                                    <div class="settings-click-item" data-action="advanced">
                                        <span>Advanced controls</span>
                                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                                    </div>
                                    <div class="settings-click-item" data-action="task-goal">
                                        <span>Task goals</span>
                                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2"><polyline points="9 18 15 12 9 6"/></svg>
                                    </div>
                                </div>
                            </div>
                            <div class="settings-group">
                                <div class="settings-group-header">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                        <path d="M13.49 5.48c1.1 0 2-.9 2-2s-.9-2-2-2-2 .9-2 2 .9 2 2 2zm-3.6 13.9l1-4.4 2.1 2v6h2v-7.5l-2.1-2 .6-3c1.3 1.5 3.3 2.5 5.5 2.5v-2c-1.9 0-3.5-1-4.3-2.4l-1-1.6c-.4-.6-1-1-1.7-1-.3 0-.5.1-.8.1l-5.2 2.2v4.7h2v-3.4l1.8-.7-1.6 8.1-4.9-1-.4 2 7 1.4z"/>
                                    </svg>
                                    <span>Movement mode</span>
                                </div>
                                <div class="settings-group-items">
                                    <label class="settings-radio-item">
                                        <input type="radio" name="moveMode" value="route">
                                        <span class="radio-mark"></span>
                                        <span>Specified route</span>
                                    </label>
                                    <label class="settings-radio-item">
                                        <input type="radio" name="moveMode" value="free" checked>
                                        <span class="radio-mark"></span>
                                        <span>Free movement</span>
                                    </label>
                                    <label class="settings-radio-item">
                                        <input type="radio" name="moveMode" value="follow">
                                        <span class="radio-mark"></span>
                                        <span>Follow mode</span>
                                    </label>
                                </div>
                            </div>
                        </div>
                    </div>
                    <!-- Expand button shown after the settings panel is collapsed -->
                    <button class="settings-expand-btn" id="settingsExpandBtn" title="Expand settings">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                            <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/>
                        </svg>
                    </button>

                    <!-- Modern bottom action bar -->
                    <div class="map-action-bar">
                        <div class="action-bar-left">
                            <button class="action-btn" data-action="plaza">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <rect x="3" y="3" width="18" height="18" rx="2"/>
                                    <path d="M3 9h18M9 21V9"/>
                                </svg>
                                <span>Plaza</span>
                            </button>
                            <button class="action-btn active" data-action="community">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"/>
                                    <circle cx="9" cy="7" r="4"/>
                                    <path d="M23 21v-2a4 4 0 0 0-3-3.87M16 3.13a4 4 0 0 1 0 7.75"/>
                                </svg>
                                <span>Community</span>
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
                            <button class="action-btn" data-action="navigate">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <polygon points="3 11 22 2 13 21 11 13 3 11"/>
                                </svg>
                                <span>Navigate</span>
                            </button>
                            <button class="action-btn" data-action="weather">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M18 10h-1.26A8 8 0 1 0 9 20h9a5 5 0 0 0 0-10z"/>
                                </svg>
                                <span>Weather</span>
                            </button>
                            <button class="action-btn" data-action="layers">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <polygon points="12 2 2 7 12 12 22 7 12 2"/>
                                    <polyline points="2 17 12 22 22 17"/>
                                    <polyline points="2 12 12 17 22 12"/>
                                </svg>
                                <span>Layers</span>
                            </button>
                        </div>
                    </div>

                    <!-- Map control button group -->
                    <div class="map-controls">
                        <button class="map-control-btn" title="Zoom in">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="5" x2="12" y2="19"/>
                                <line x1="5" y1="12" x2="19" y2="12"/>
                            </svg>
                        </button>
                        <button class="map-control-btn" title="Zoom out">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="5" y1="12" x2="19" y2="12"/>
                            </svg>
                        </button>
                        <div class="map-control-divider"></div>
                        <button class="map-control-btn" title="My location">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="3"/>
                                <path d="M12 2v4M12 18v4M2 12h4M18 12h4"/>
                            </svg>
                        </button>
                        <button class="map-control-btn" title="Compass">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="12" cy="12" r="10"/>
                                <polygon points="16.24 7.76 14.12 14.12 7.76 16.24 9.88 9.88 16.24 7.76"/>
                            </svg>
                        </button>
                    </div>
                </div>

                <!-- Right-side status panel resizer -->
                <div class="sns-panel-resizer" id="snsPanelResizer">
                    <div class="panel-resizer-handle">
                        <div class="panel-resizer-line"></div>
                    </div>
                    <button class="panel-collapse-btn" id="snsPanelCollapseBtn" title="Collapse status panel">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="9,6 15,12 9,18"/>
                        </svg>
                    </button>
                </div>

                <!-- Right-side status panel -->
                <div class="sns-status-panel" id="snsStatusPanel">
                    <!-- Tab content area - the whole panel content changes with the selected tab -->
                    <div class="status-tab-content" id="statusTabContent">
                        <!-- Process tab content -->
                        <div class="tab-pane active" data-tab="process">
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg> Current Status</div>
                                <div class="status-rows">
                                    <div class="status-row"><span>💰 Money</span><span class="value">: 10,996.61</span></div>
                                    <div class="status-row"><span>❤️ Life</span><span class="value">: 125</span></div>
                                    <div class="status-row"><span>⚡ Energy</span><span class="value">: 150</span></div>
                                    <div class="status-row"><span>👤 Profession</span><span class="value">: Doctor (*requires 800 CNY startup fee)</span></div>
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
                        <!-- Resource tab content -->
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
                        <!-- Think tab content -->
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
                    <!-- Bottom tab buttons -->
                    <div class="status-tabs" id="statusTabs">
                        <button class="status-tab active" data-tab="process">Process</button>
                        <button class="status-tab" data-tab="resource">Resource</button>
                        <button class="status-tab" data-tab="think">Think</button>
                    </div>
                </div>
            </div>
        `;
    },

    // SNS page sidebar - see aisns.png
    renderSNSSidebar() {
        return `
            <div class="sidebar-section">
                <div class="sidebar-header-row">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#1a73e8"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/></svg>
                    <span class="sidebar-section-title">Explore the Earth - YBao</span>
                </div>
                <!-- User attributes panel -->
                <div class="user-stats-panel">
                    <div class="user-stat-badges">
                        <span class="stat-badge level">Level3</span>
                        <span class="stat-badge credit">Credit:100</span>
                        <span class="stat-badge money">Money:10,996.61</span>
                    </div>
                    <div class="user-stat-info">
                        <div class="stat-row">Life:125 | IO:70</div>
                        <div class="stat-row">Energy:150 | Move:187.5</div>
                        <div class="stat-row">Exp:30</div>
                        <div class="stat-progress">
                            <div class="progress-track"><div class="progress-fill" style="width: 30%"></div></div>
                            <div class="progress-labels"><span>0</span><span>50</span><span>100</span></div>
                        </div>
                    </div>
                </div>
            </div>
            <div class="sidebar-section">
                <!-- Chat / Trade tabs -->
                <div class="sns-sidebar-tabs">
                    <button class="sidebar-tab active">Chat</button>
                    <button class="sidebar-tab">Trade</button>
                </div>
                <!-- Contact List -->
                <div class="contact-section">
                    <div class="contact-header">Contact List</div>
                    <div class="contact-tree">
                        <div class="tree-item">
                            <span class="tree-toggle">▸</span>
                            <span class="tree-label">Buddies</span>
                        </div>
                    </div>
                </div>
            </div>
            <div class="sidebar-section sns-user-footer">
                <div class="sns-user-item">
                    <div class="user-dot online"></div>
                    <span class="user-label">rongrong</span>
                </div>
            </div>
        `;
    },

    // Agent page - see agent.png
    renderAgentPage() {
        return `
            <div class="agent-page-layout">
                <!-- Main chat area -->
                <div class="agent-chat-area">
                    <!-- Top toolbar -->
                    <div class="agent-chat-toolbar">
                        <div class="toolbar-left">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="#1a73e8">
                                <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                            </svg>
                        </div>
                        <div class="toolbar-center">
                            <select class="model-selector" id="modelSelector">
                                <option value="gpt-4o">Baichuan_local:gpt-4o</option>
                                <option value="gpt-4">GPT-4</option>
                                <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                                <option value="claude-3">Claude 3</option>
                                <option value="deepseek">DeepSeek</option>
                            </select>
                        </div>
                        <div class="toolbar-right">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="#5f6368">
                                <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                            </svg>
                            <select class="role-selector" id="roleSelector">
                                <option value="senior-dev">Senior developer</option>
                                <option value="assistant">General assistant</option>
                                <option value="writer">Creative writing</option>
                                <option value="analyst">Data analyst</option>
                            </select>
                        </div>
                    </div>

                    <!-- Messages area -->
                    <div class="agent-chat-messages" id="chatMessages">
                        <!-- Welcome message -->
                        <div class="welcome-message">
                            <div class="welcome-icon">
                                <svg viewBox="0 0 48 48" width="64" height="64">
                                    <defs>
                                        <linearGradient id="welcomeGrad" x1="0%" y1="0%" x2="100%" y2="100%">
                                            <stop offset="0%" style="stop-color:#11998e"/>
                                            <stop offset="100%" style="stop-color:#38ef7d"/>
                                        </linearGradient>
                                    </defs>
                                    <circle cx="24" cy="24" r="22" fill="url(#welcomeGrad)" opacity="0.1"/>
                                    <path d="M24 4C12.95 4 4 12.95 4 24s8.95 20 20 20 20-8.95 20-20S35.05 4 24 4zm-4 30l-10-10 2.82-2.82L20 28.34l15.18-15.18L38 16l-18 18z" fill="url(#welcomeGrad)"/>
                                </svg>
                            </div>
                            <h2 class="welcome-title">${this.escapeHtml((window.agentState && typeof window.agentState.getCurrentAgent === 'function') ? (window.agentState.getCurrentAgent()?.name || 'AI Assistant') : 'AI Assistant')}</h2>
                            <p class="welcome-subtitle">Powered by Azure OpenAI GPT</p>
                            <div class="welcome-tips">
                                <div class="tip-item">
                                    <span class="tip-icon">💡</span>
                                    <span>Type your question and press Enter to send</span>
                                </div>
                                <div class="tip-item">
                                    <span class="tip-icon">📝</span>
                                    <span>Supports Markdown output</span>
                                </div>
                                <div class="tip-item">
                                    <span class="tip-icon">🔄</span>
                                    <span>Real-time streaming responses</span>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Input area -->
                    <div class="agent-chat-input-area">
                        <div class="input-hint">Input @@ to load tools selector; Ctrl+i To load preset question; Ctrl+/ To insert chat template.</div>
                        <div class="input-wrapper">
                            <textarea class="agent-chat-input" id="chatInput" placeholder="Type a message..."></textarea>
                        </div>
                        <div class="input-toolbar">
                            <div class="toolbar-buttons">
                                <button class="toolbar-icon-btn" title="Add"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/></svg></button>
                                <button class="toolbar-icon-btn" title="Attachment"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/></svg></button>
                                <button class="toolbar-icon-btn" title="Image"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg></button>
                                <button class="toolbar-icon-btn" title="Document"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/></svg></button>
                                <button class="toolbar-icon-btn" title="List"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M4 10.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zm0-6c-.83 0-1.5.67-1.5 1.5S3.17 7.5 4 7.5 5.5 6.83 5.5 6 4.83 4.5 4 4.5zm0 12c-.83 0-1.5.68-1.5 1.5s.68 1.5 1.5 1.5 1.5-.68 1.5-1.5-.67-1.5-1.5-1.5zM7 19h14v-2H7v2zm0-6h14v-2H7v2zm0-8v2h14V5H7z"/></svg></button>
                                <button class="toolbar-icon-btn" title="Screen"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M20 18c1.1 0 1.99-.9 1.99-2L22 6c0-1.1-.9-2-2-2H4c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2H0v2h24v-2h-4zM4 6h16v10H4V6z"/></svg></button>
                                <button class="toolbar-icon-btn" title="Video"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M17 10.5V7c0-.55-.45-1-1-1H4c-.55 0-1 .45-1 1v10c0 .55.45 1 1 1h12c.55 0 1-.45 1-1v-3.5l4 4v-11l-4 4z"/></svg></button>
                                <button class="toolbar-icon-btn" title="Window"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/></svg></button>
                            </div>
                            <button class="send-btn" id="sendMessageBtn">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                    <path d="M12 4l-1.41 1.41L16.17 11H4v2h12.17l-5.58 5.59L12 20l8-8z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // Agent page sidebar - see agent.png
    renderAgentSidebar() {
        return `
            <div class="sidebar-section agent-user-section">
                <div class="agent-user-header">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#5f6368"><path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 9h-2V9h2v2zm0 4h-2v-2h2v2zM13 9V3.5L18.5 9H13z"/></svg>
                    <span class="agent-username">Altman (it is me)</span>
                </div>
                <!-- Large icon buttons -->
                <div class="agent-action-buttons">
                    <button class="agent-action-btn" id="newChatBtn">
                        <div class="action-btn-icon">
                            <svg viewBox="0 0 48 48" width="40" height="40">
                                <rect x="8" y="8" width="32" height="8" rx="2" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="8" y1="22" x2="40" y2="22" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="8" y1="30" x2="32" y2="30" stroke="#1a73e8" stroke-width="2"/>
                                <path d="M8 38 L18 38" stroke="#1a73e8" stroke-width="2"/>
                                <circle cx="12" cy="12" r="2" fill="#1a73e8"/>
                                <path d="M16 10 L16 14 M14 12 L18 12" stroke="#1a73e8" stroke-width="1.5"/>
                            </svg>
                        </div>
                        <span class="action-btn-text">New Chat</span>
                    </button>
                    <button class="agent-action-btn" id="settingBtn">
                        <div class="action-btn-icon">
                            <svg viewBox="0 0 48 48" width="40" height="40">
                                <circle cx="24" cy="24" r="16" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <path d="M24 8 L24 12 M24 36 L24 40 M8 24 L12 24 M36 24 L40 24 M12 12 L15 15 M33 33 L36 36 M12 36 L15 33 M33 15 L36 12" stroke="#1a73e8" stroke-width="2" stroke-linecap="round"/>
                                <circle cx="24" cy="24" r="6" fill="none" stroke="#1a73e8" stroke-width="2"/>
                            </svg>
                        </div>
                        <span class="action-btn-text">Setting</span>
                    </button>
                </div>
            </div>
            <div class="sidebar-section">
                <!-- Search box -->
                <div class="agent-search">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#9e9e9e"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg>
                    <input type="text" class="search-input" placeholder="Keyword+Enter,Blank+Enter to reset">
                </div>
                <!-- Chat List / Tag List switch -->
                <div class="chat-list-tabs">
                    <button class="chat-tab active" data-tab="chatList">Chat List</button>
                    <button class="chat-tab" data-tab="tagList">Tag List</button>
                </div>
                <!-- Chat list -->
                <div class="chat-list-container" id="chatListContainer">
                    <div class="chat-tree" id="chatList">
                        <div class="tree-children">
                        </div>
                    </div>
                </div>
            </div>
            <div class="sidebar-section agent-list-section">
                <!-- Agent list -->
                <div class="agent-list" id="agentList">
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Balabala</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Justin</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Peter</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Musk (Planner)</span>
                    </div>
                    <div class="agent-item">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#5f6368"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                        <span>Mike (Critic)</span>
                    </div>
                    <div class="agent-item agent-management">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/></svg>
                        <span>Agent Management</span>
                    </div>
                </div>
            </div>
        `;
    },

    // KM page - see km.png
    renderKMPage() {
        return `
            <div class="km-page-layout">
                <div class="km-editor-area">
                    <!-- First row toolbar -->
                    <div class="km-toolbar-row">
                        <div class="toolbar-group">
                            <button class="km-tool-btn" title="Save"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M17 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/></svg></button>
                            <button class="km-tool-btn" title="Print"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 8H5c-1.66 0-3 1.34-3 3v6h4v4h12v-4h4v-6c0-1.66-1.34-3-3-3zm-3 11H8v-5h8v5zm3-7c-.55 0-1-.45-1-1s.45-1 1-1 1 .45 1 1-.45 1-1 1zm-1-9H6v4h12V3z"/></svg></button>
                            <button class="km-tool-btn" title="Copy"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg></button>
                        </div>
                        <div class="toolbar-group">
                            <button class="km-tool-btn" title="Cut"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M9.64 7.64c.23-.5.36-1.05.36-1.64 0-2.21-1.79-4-4-4S2 3.79 2 6s1.79 4 4 4c.59 0 1.14-.13 1.64-.36L10 12l-2.36 2.36C7.14 14.13 6.59 14 6 14c-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4c0-.59-.13-1.14-.36-1.64L12 14l7 7h3v-1L9.64 7.64zM6 8c-1.1 0-2-.89-2-2s.9-2 2-2 2 .89 2 2-.9 2-2 2zm0 12c-1.1 0-2-.89-2-2s.9-2 2-2 2 .89 2 2-.9 2-2 2zm6-7.5c-.28 0-.5-.22-.5-.5s.22-.5.5-.5.5.22.5.5-.22.5-.5.5zM19 3l-6 6 2 2 7-7V3z"/></svg></button>
                            <button class="km-tool-btn" title="Paste"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 2h-4.18C14.4.84 13.3 0 12 0c-1.3 0-2.4.84-2.82 2H5c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-7 0c.55 0 1 .45 1 1s-.45 1-1 1-1-.45-1-1 .45-1 1-1zm7 18H5V4h2v3h10V4h2v16z"/></svg></button>
                        </div>
                        <div class="toolbar-group">
                            <button class="km-tool-btn" title="Undo"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12.5 8c-2.65 0-5.05.99-6.9 2.6L2 7v9h9l-3.62-3.62c1.39-1.16 3.16-1.88 5.12-1.88 3.54 0 6.55 2.31 7.6 5.5l2.37-.78C21.08 11.03 17.15 8 12.5 8z"/></svg></button>
                            <button class="km-tool-btn" title="Redo"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M18.4 10.6C16.55 8.99 14.15 8 11.5 8c-4.65 0-8.58 3.03-9.96 7.22L3.9 16c1.05-3.19 4.05-5.5 7.6-5.5 1.95 0 3.73.72 5.12 1.88L13 16h9V7l-3.6 3.6z"/></svg></button>
                        </div>
                        <div class="toolbar-group">
                            <button class="km-tool-btn" title="Search"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/></svg></button>
                            <button class="km-tool-btn" title="Date"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M19 3h-1V1h-2v2H8V1H6v2H5c-1.11 0-2 .9-2 2v14c0 1.1.89 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V8h14v11zM9 10H7v2h2v-2zm4 0h-2v2h2v-2zm4 0h-2v2h2v-2z"/></svg></button>
                            <button class="km-tool-btn" title="Table"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M20 2H4c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h16c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zM8 20H4v-4h4v4zm0-6H4v-4h4v4zm0-6H4V4h4v4zm6 12h-4v-4h4v4zm0-6h-4v-4h4v4zm0-6h-4V4h4v4zm6 12h-4v-4h4v4zm0-6h-4v-4h4v4zm0-6h-4V4h4v4z"/></svg></button>
                            <button class="km-tool-btn" title="Image"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M21 19V5c0-1.1-.9-2-2-2H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2zM8.5 13.5l2.5 3.01L14.5 12l4.5 6H5l3.5-4.5z"/></svg></button>
                            <button class="km-tool-btn" title="Link"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M3.9 12c0-1.71 1.39-3.1 3.1-3.1h4V7H7c-2.76 0-5 2.24-5 5s2.24 5 5 5h4v-1.9H7c-1.71 0-3.1-1.39-3.1-3.1zM8 13h8v-2H8v2zm9-6h-4v1.9h4c1.71 0 3.1 1.39 3.1 3.1s-1.39 3.1-3.1 3.1h-4V17h4c2.76 0 5-2.24 5-5s-2.24-5-5-5z"/></svg></button>
                        </div>
                        <div class="toolbar-group">
                            <button class="km-tool-btn" title="Bullet list"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M4 10.5c-.83 0-1.5.67-1.5 1.5s.67 1.5 1.5 1.5 1.5-.67 1.5-1.5-.67-1.5-1.5-1.5zm0-6c-.83 0-1.5.67-1.5 1.5S3.17 7.5 4 7.5 5.5 6.83 5.5 6 4.83 4.5 4 4.5zm0 12c-.83 0-1.5.68-1.5 1.5s.68 1.5 1.5 1.5 1.5-.68 1.5-1.5-.67-1.5-1.5-1.5zM7 19h14v-2H7v2zm0-6h14v-2H7v2zm0-8v2h14V5H7z"/></svg></button>
                            <button class="km-tool-btn" title="Numbered list"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M2 17h2v.5H3v1h1v.5H2v1h3v-4H2v1zm1-9h1V4H2v1h1v3zm-1 3h1.8L2 13.1v.9h3v-1H3.2L5 10.9V10H2v1zm5-6v2h14V5H7zm0 14h14v-2H7v2zm0-6h14v-2H7v2z"/></svg></button>
                        </div>
                    </div>
                    <!-- Second row toolbar: font and formatting -->
                    <div class="km-toolbar-row km-format-row">
                        <select class="km-font-select" id="fontSelect">
                            <option value="Microsoft YaHei UI">Microsoft YaHei UI</option>
                            <option value="SimSun">宋体</option>
                            <option value="SimHei">黑体</option>
                            <option value="Arial">Arial</option>
                            <option value="Times New Roman">Times New Roman</option>
                        </select>
                        <select class="km-size-select" id="sizeSelect">
                            <option value="10">10pt</option>
                            <option value="12" selected>12pt</option>
                            <option value="14">14pt</option>
                            <option value="16">16pt</option>
                            <option value="18">18pt</option>
                            <option value="24">24pt</option>
                            <option value="36">36pt</option>
                        </select>
                        <div class="toolbar-divider"></div>
                        <button class="km-tool-btn" title="Emoji"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M11.99 2C6.47 2 2 6.48 2 12s4.47 10 9.99 10C17.52 22 22 17.52 22 12S17.52 2 11.99 2zM12 20c-4.42 0-8-3.58-8-8s3.58-8 8-8 8 3.58 8 8-3.58 8-8 8zm3.5-9c.83 0 1.5-.67 1.5-1.5S16.33 8 15.5 8 14 8.67 14 9.5s.67 1.5 1.5 1.5zm-7 0c.83 0 1.5-.67 1.5-1.5S9.33 8 8.5 8 7 8.67 7 9.5 7.67 11 8.5 11zm3.5 6.5c2.33 0 4.31-1.46 5.11-3.5H6.89c.8 2.04 2.78 3.5 5.11 3.5z"/></svg></button>
                        <button class="km-tool-btn" title="Symbols"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg></button>
                        <div class="toolbar-divider"></div>
                        <button class="km-tool-btn format-btn" data-format="bold" title="Bold"><strong>B</strong></button>
                        <button class="km-tool-btn format-btn" data-format="italic" title="Italic"><em>I</em></button>
                        <button class="km-tool-btn format-btn" data-format="underline" title="Underline"><u>U</u></button>
                        <button class="km-tool-btn format-btn" data-format="strikethrough" title="Strikethrough"><s>S</s></button>
                        <button class="km-tool-btn format-btn" title="Superscript">X<sup>1</sup></button>
                        <button class="km-tool-btn format-btn" title="Subscript">X<sub>1</sub></button>
                        <div class="toolbar-divider"></div>
                        <button class="km-tool-btn" data-align="left" title="Align left"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M15 15H3v2h12v-2zm0-8H3v2h12V7zM3 13h18v-2H3v2zm0 8h18v-2H3v2zM3 3v2h18V3H3z"/></svg></button>
                        <button class="km-tool-btn" data-align="center" title="Align center"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M7 15v2h10v-2H7zm-4 6h18v-2H3v2zm0-8h18v-2H3v2zm4-6v2h10V7H7zM3 3v2h18V3H3z"/></svg></button>
                        <button class="km-tool-btn" data-align="right" title="Align right"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M3 21h18v-2H3v2zm6-4h12v-2H9v2zm-6-4h18v-2H3v2zm6-4h12V7H9v2zM3 3v2h18V3H3z"/></svg></button>
                        <button class="km-tool-btn" data-align="justify" title="Justify"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M3 21h18v-2H3v2zm0-4h18v-2H3v2zm0-4h18v-2H3v2zm0-4h18V7H3v2zM3 3v2h18V3H3z"/></svg></button>
                        <div class="toolbar-divider"></div>
                        <button class="km-tool-btn" title="Decrease indent"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M11 17h10v-2H11v2zm-8-5l4 4V8l-4 4zm0 9h18v-2H3v2zM3 3v2h18V3H3zm8 6h10V7H11v2zm0 4h10v-2H11v2z"/></svg></button>
                        <button class="km-tool-btn" title="Increase indent"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M3 21h18v-2H3v2zM3 8v8l4-4-4-4zm8 9h10v-2H11v2zM3 3v2h18V3H3zm8 6h10V7H11v2zm0 4h10v-2H11v2z"/></svg></button>
                    </div>
                    <!-- Editor area -->
                    <div class="km-editor-content" id="noteContent" contenteditable="true">
                        <p></p>
                    </div>
                </div>
            </div>
        `;
    },

    // KM page sidebar - see km.png
    renderKMSidebar() {
        return `
            <!-- Top header area -->
            <div class="km-sidebar-header">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="#1a73e8">
                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
                </svg>
                <span class="km-sidebar-title">My Note</span>
            </div>

            <!-- Action buttons -->
            <div class="km-action-buttons">
                <button class="km-action-btn" id="newNoteBtn">
                    <div class="km-action-icon">
                        <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#1a73e8" stroke-width="1.5">
                            <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"/>
                            <polyline points="14 2 14 8 20 8"/>
                            <line x1="12" y1="11" x2="12" y2="17"/>
                            <line x1="9" y1="14" x2="15" y2="14"/>
                        </svg>
                    </div>
                    <span>New Note</span>
                </button>
                <button class="km-action-btn" id="kmSettingBtn">
                    <div class="km-action-icon">
                        <svg viewBox="0 0 24 24" width="32" height="32" fill="none" stroke="#1a73e8" stroke-width="1.5">
                            <circle cx="12" cy="12" r="3"/>
                            <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                        </svg>
                    </div>
                    <span>Setting</span>
                </button>
            </div>

            <!-- Search box -->
            <div class="km-search-box">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#999">
                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                </svg>
                <input type="text" placeholder="Keyword+Enter,Blank+Enter to reset" class="km-search-input" id="kmSearchInput">
            </div>

            <!-- Tab switch -->
            <div class="km-tabs">
                <button class="km-tab active" data-tab="all">All</button>
                <button class="km-tab" data-tab="tag">Tag</button>
            </div>

            <!-- Note tree -->
            <div class="km-note-tree" id="noteTree">
                <div class="km-tree-node">
                    <div class="km-tree-item">
                        <span class="tree-icon">📋</span>
                        <span class="tree-text">Memo</span>
                    </div>
                </div>
                <div class="km-tree-node">
                    <div class="km-tree-item">
                        <span class="tree-icon">✅</span>
                        <span class="tree-text">Todo</span>
                    </div>
                </div>
                <div class="km-tree-node expandable">
                    <div class="km-tree-item">
                        <span class="tree-expand">▶</span>
                        <span class="tree-icon">📁</span>
                        <span class="tree-text">amazon</span>
                    </div>
                </div>
                <div class="km-tree-node expandable expanded">
                    <div class="km-tree-item">
                        <span class="tree-expand">▼</span>
                        <span class="tree-icon">📁</span>
                        <span class="tree-text">ai coding</span>
                    </div>
                    <div class="km-tree-children">
                        <div class="km-tree-node">
                            <div class="km-tree-item active">
                                <span class="tree-icon">📄</span>
                                <span class="tree-text">codex</span>
                            </div>
                        </div>
                    </div>
                </div>
                <div class="km-tree-node expandable">
                    <div class="km-tree-item">
                        <span class="tree-expand">▶</span>
                        <span class="tree-icon">📁</span>
                        <span class="tree-text">baidu</span>
                    </div>
                </div>
                <div class="km-tree-node expandable">
                    <div class="km-tree-item">
                        <span class="tree-expand">▶</span>
                        <span class="tree-icon">📁</span>
                        <span class="tree-text">Resource</span>
                    </div>
                </div>
                <div class="km-tree-node">
                    <div class="km-tree-item">
                        <span class="tree-icon">📄</span>
                        <span class="tree-text">moonlight stream</span>
                    </div>
                </div>
            </div>

            <!-- Bottom knowledge base list -->
            <div class="km-kb-section">
                <div class="km-kb-item" data-kb="pinecone">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9h-4v4h-2v-4H9V9h4V5h2v4h4v2z"/></svg>
                    <span>KB on Pinecone</span>
                </div>
                <div class="km-kb-item" data-kb="3d-design">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9h-4v4h-2v-4H9V9h4V5h2v4h4v2z"/></svg>
                    <span>3D Design</span>
                </div>
                <div class="km-kb-item" data-kb="code-kb">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9h-4v4h-2v-4H9V9h4V5h2v4h4v2z"/></svg>
                    <span>Code KB</span>
                </div>
                <div class="km-kb-item" data-kb="testpinecone">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M4 6H2v14c0 1.1.9 2 2 2h14v-2H4V6zm16-4H8c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 9h-4v4h-2v-4H9V9h4V5h2v4h4v2z"/></svg>
                    <span>testpinecone</span>
                </div>
                <div class="km-kb-item km-kb-setting" data-kb="setting">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#666"><path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/></svg>
                    <span>KM Setting</span>
                </div>
            </div>
        `;
    },

    // Tools page - full tool management page
    renderToolsPage() {
        return `
            <div class="tools-management-page">
                <!-- Top header bar -->
                <div class="tools-header">
                    <div class="tools-header-left">
                        <h1 class="tools-title">Tools Management</h1>
                        <p class="tools-subtitle">Manage AI tools that can be called by AI agents</p>
                    </div>
                    <div class="tools-header-right">
                        <button class="btn-primary" onclick="PageControllers.showAddToolDialog()">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="12" y1="5" x2="12" y2="19"/>
                                <line x1="5" y1="12" x2="19" y2="12"/>
                            </svg>
                            Add New Tool
                        </button>
                    </div>
                </div>

                <!-- Tab navigation -->
                <div class="tools-tabs">
                    <button class="tools-tab-item active" data-tab="plugins" onclick="PageControllers.switchToolTab('plugins')">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="3" y="3" width="7" height="7" rx="1"/>
                            <rect x="14" y="3" width="7" height="7" rx="1"/>
                            <rect x="3" y="14" width="7" height="7" rx="1"/>
                            <rect x="14" y="14" width="7" height="7" rx="1"/>
                        </svg>
                        <span>Tools Plugin</span>
                    </button>
                    <button class="tools-tab-item" data-tab="mcp" onclick="PageControllers.switchToolTab('mcp')">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="2" y="3" width="20" height="14" rx="2"/>
                            <line x1="8" y1="21" x2="16" y2="21" stroke-width="2"/>
                        </svg>
                        <span>MCP</span>
                    </button>
                    <button class="tools-tab-item" data-tab="functions" onclick="PageControllers.switchToolTab('functions')">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                            <text x="4" y="16" font-size="12" font-family="serif" fill="currentColor">f(x)</text>
                        </svg>
                        <span>Function</span>
                    </button>
                    <button class="tools-tab-item" data-tab="skills" onclick="PageControllers.switchToolTab('skills')">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                            <rect x="2" y="3" width="20" height="14" rx="2"/>
                            <line x1="2" y1="20" x2="22" y2="20" stroke-width="2"/>
                        </svg>
                        <span>Computer Use</span>
                    </button>
                </div>

                <!-- Tools content area -->
                <div class="tools-content" id="toolsContentArea">
                    <div class="tools-loading">Loading tools...</div>
                </div>
            </div>
        `;
    },

    // Render plugin cards - see tools.png
    renderPluginCards() {
        const plugins = [
            { name: 'OpenAI', icon: 'openai', desc: 'OpenAI is an AI research organization known for GPT-4 and GPT-4o, which excel in natural language understanding and generation.', badge: 'LLM Connector' },
            { name: 'Claude', icon: 'claude', desc: 'Claude is an AI language model by Anthropic, featuring Claude 3.5, designed for safe, reliable, and user-friendly communication tasks.', badge: 'LLM Connector' },
            { name: 'DeepSeek', icon: 'deepseek', desc: 'DeepSeek\'s DeepSeek-R1 model excels in reasoning, code generation, and cost efficiency, rivaling OpenAI\'s offerings in performance.', badge: 'LLM Connector' },
            { name: 'Mistral', icon: 'mistral', desc: 'Mistral AI is a Paris-based startup specializing in open-source large language models, founded by ex-Google DeepMind and Meta researchers.', badge: 'LLM Connector' },
            { name: 'Gemini', icon: 'gemini', desc: 'Gemini is Google DeepMind\'s advanced multimodal AI model, designed to intuitively understand and integrate text, code, audio, images, and video.', badge: 'LLM Connector' },
            { name: 'Llama', icon: 'llama', desc: 'Llama is developed by Meta, featuring multiple model sizes for diverse applications, enabling efficient and effective natural language processing tasks.', badge: 'LLM Connector' },
        ];

        return plugins.map(plugin => `
            <div class="plugin-card">
                <div class="plugin-card-header">
                    <div class="plugin-icon-lg">
                        ${this.getPluginIcon(plugin.icon)}
                    </div>
                    <div class="plugin-header-info">
                        <span class="plugin-name">${plugin.name}</span>
                        <span class="plugin-badge-connector">${plugin.badge}</span>
                    </div>
                </div>
                <div class="plugin-author">
                    <span class="author-label">AI-SNS</span>
                    <span class="author-official">Official</span>
                </div>
                <div class="plugin-desc">${plugin.desc}</div>
                <button class="plugin-download-btn">Download</button>
            </div>
        `).join('');
    },

    // Get plugin icon
    getPluginIcon(icon) {
        const icons = {
            'openai': '<svg viewBox="0 0 24 24" width="32" height="32"><path fill="#10a37f" d="M22.2 8.3c-.5-1.4-1.5-2.5-2.7-3.3-.9-.6-1.9-.9-3-1-.3 0-.5 0-.8.1-.5-1.3-1.4-2.4-2.6-3.2C11.9.2 10.5-.1 9.2.1c-1.1.1-2.1.5-2.9 1.1-.8.6-1.5 1.4-1.9 2.3-.8-.2-1.6-.2-2.4 0-1.1.3-2.1.9-2.8 1.8-.6.8-1 1.8-1.1 2.8-.1 1 .1 2 .5 2.9-.8.8-1.3 1.8-1.5 2.9-.2 1.3.1 2.6.7 3.8.5.9 1.2 1.7 2.1 2.2.9.6 1.9.9 3 1 .3 0 .5 0 .8-.1.5 1.3 1.4 2.4 2.6 3.2 1.2.7 2.6 1 4 .8 1.1-.1 2.1-.5 2.9-1.1.8-.6 1.5-1.4 1.9-2.3.8.2 1.6.2 2.4 0 1.1-.3 2.1-.9 2.8-1.8.6-.8 1-1.8 1.1-2.8.1-1-.1-2-.5-2.9.8-.8 1.3-1.8 1.5-2.9.2-1.3-.1-2.7-.7-3.8zM12 18.9c-3.8 0-6.9-3.1-6.9-6.9s3.1-6.9 6.9-6.9 6.9 3.1 6.9 6.9-3.1 6.9-6.9 6.9z"/></svg>',
            'claude': '<svg viewBox="0 0 24 24" width="32" height="32"><rect fill="#d97706" x="2" y="2" width="20" height="20" rx="4"/><text x="12" y="16" text-anchor="middle" font-size="12" font-weight="bold" fill="white">A</text></svg>',
            'deepseek': '<svg viewBox="0 0 24 24" width="32" height="32"><rect fill="#1a73e8" x="2" y="2" width="20" height="20" rx="4"/><path fill="white" d="M7 8h10v2H7zM7 12h8v2H7zM7 16h6v2H7z"/></svg>',
            'mistral': '<svg viewBox="0 0 24 24" width="32" height="32"><rect fill="#ff6b35" x="2" y="2" width="20" height="20" rx="4"/><path fill="white" d="M6 6h4v4H6zM14 6h4v4h-4zM6 10h4v4H6zM10 10h4v4h-4zM14 14h4v4h-4zM6 14h4v4H6z"/></svg>',
            'gemini': '<svg viewBox="0 0 24 24" width="32" height="32"><defs><linearGradient id="gemGrad" x1="0%" y1="0%" x2="100%" y2="100%"><stop offset="0%" style="stop-color:#4285f4"/><stop offset="50%" style="stop-color:#9b72cb"/><stop offset="100%" style="stop-color:#d96570"/></linearGradient></defs><circle fill="url(#gemGrad)" cx="12" cy="12" r="10"/><path fill="white" d="M12 6l2 4h4l-3 3 1 5-4-2-4 2 1-5-3-3h4z"/></svg>',
            'llama': '<svg viewBox="0 0 24 24" width="32" height="32"><circle fill="#1877f2" cx="12" cy="12" r="10"/><text x="12" y="15" text-anchor="middle" font-size="8" font-weight="bold" fill="white">Meta</text></svg>',
            'grok': '<svg viewBox="0 0 24 24" width="32" height="32"><rect fill="#000" x="2" y="2" width="20" height="20" rx="4"/><text x="12" y="16" text-anchor="middle" font-size="12" font-weight="bold" fill="white">X</text></svg>',
            'kimi': '<svg viewBox="0 0 24 24" width="32" height="32"><rect fill="#ff4081" x="2" y="2" width="20" height="20" rx="4"/><text x="12" y="16" text-anchor="middle" font-size="12" font-weight="bold" fill="white">K</text></svg>',
            'aisns': '<svg viewBox="0 0 24 24" width="32" height="32"><path fill="#1a73e8" d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>',
        };
        return icons[icon] || icons['aisns'];
    },

    // Tools page sidebar - see tools.png
    renderToolsSidebar() {
        return `
            <!-- Top title -->
            <div class="tools-sidebar-header">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="#1a73e8">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>Tools Management</span>
            </div>

            <!-- Bottom category list -->
            <div class="tools-category-section">
                <div class="tools-category-item active" data-tab="plugins">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#666">
                        <rect x="3" y="3" width="7" height="7" rx="1"/>
                        <rect x="14" y="3" width="7" height="7" rx="1"/>
                        <rect x="3" y="14" width="7" height="7" rx="1"/>
                        <rect x="14" y="14" width="7" height="7" rx="1"/>
                    </svg>
                    <span>Tools Plugin</span>
                </div>
                <div class="tools-category-item" data-tab="mcp">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#666">
                        <rect x="2" y="3" width="20" height="14" rx="2"/>
                        <line x1="8" y1="21" x2="16" y2="21" stroke="#666" stroke-width="2"/>
                    </svg>
                    <span>MCP</span>
                </div>
                <div class="tools-category-item" data-tab="functions">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#666">
                        <text x="4" y="16" font-size="12" font-family="serif" fill="#666">f(x)</text>
                    </svg>
                    <span>Function</span>
                </div>
                <div class="tools-category-item" data-tab="skills">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#666">
                        <rect x="2" y="3" width="20" height="14" rx="2"/>
                        <line x1="2" y1="20" x2="22" y2="20" stroke="#666" stroke-width="2"/>
                    </svg>
                    <span>Computer Use</span>
                </div>
            </div>
        `;
    },

    // Render LLM icon grid - see tools.png
    renderLLMIcons() {
        const llms = [
            { name: 'OpenAI', icon: 'openai' },
            { name: 'DeepSeek', icon: 'deepseek' },
            { name: 'Claude', icon: 'claude' },
            { name: 'Gemini', icon: 'gemini' },
            { name: 'Mistral', icon: 'mistral' },
            { name: 'Llama', icon: 'llama' },
            { name: 'Grok', icon: 'grok' },
            { name: 'Kimi', icon: 'kimi' },
        ];

        return llms.map(llm => `
            <div class="llm-icon-item" title="${llm.name}">
                <div class="llm-icon-box">
                    ${this.getPluginIcon(llm.icon)}
                </div>
                <span class="llm-name">${llm.name}</span>
            </div>
        `).join('');
    },

    // Web page - see web.png
    renderWebPage() {
        return `
            <div class="web-page">
                <!-- Top navigation bar -->
                <div class="web-top-nav">
                    <div class="web-nav-brand">
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="#fff">
                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
                        </svg>
                        <span>AI-SNS</span>
                    </div>
                    <div class="web-nav-links">
                        <a href="#" class="web-nav-link">About</a>
                        <a href="#" class="web-nav-link">Ecosystem</a>
                        <a href="#" class="web-nav-link">Docs</a>
                        <a href="#" class="web-nav-link">Blog</a>
                        <a href="#" class="web-nav-link">Community</a>
                        <button class="web-nav-btn">Try AI-SNS</button>
                    </div>
                </div>

                <!-- Main content area - AI-SNS introduction -->
                <div class="web-hero-section">
                    <div class="web-hero-content">
                        <h1 class="web-hero-title">Ai-SNS</h1>
                        <p class="web-hero-subtitle">Is an AI self-governing global<br>network, open-source and<br>decentralized.</p>
                        <div class="web-hero-icons">
                            <a href="#" class="hero-icon" title="Website">
                                <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93zm6.9-2.54c-.26-.81-1-1.39-1.9-1.39h-1v-3c0-.55-.45-1-1-1H8v-2h2c.55 0 1-.45 1-1V7h2c1.1 0 2-.9 2-2v-.41c2.93 1.19 5 4.06 5 7.41 0 2.08-.8 3.97-2.1 5.39z"/>
                                </svg>
                            </a>
                            <a href="#" class="hero-icon" title="GitHub">
                                <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                                    <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                                </svg>
                            </a>
                            <a href="#" class="hero-icon" title="Network">
                                <svg viewBox="0 0 24 24" width="32" height="32" fill="currentColor">
                                    <path d="M12 2L2 7l10 5 10-5-10-5zM2 17l10 5 10-5M2 12l10 5 10-5"/>
                                    <circle cx="12" cy="12" r="3" fill="currentColor"/>
                                    <circle cx="5" cy="9" r="2" fill="currentColor"/>
                                    <circle cx="19" cy="9" r="2" fill="currentColor"/>
                                    <circle cx="5" cy="15" r="2" fill="currentColor"/>
                                    <circle cx="19" cy="15" r="2" fill="currentColor"/>
                                </svg>
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    // Web page sidebar
    renderWebSidebar() {
        return `
            <div class="web-sidebar-header">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="12" cy="12" r="10"/>
                    <path d="M2 12h20"/>
                    <path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>
                </svg>
                <span class="web-sidebar-title">LLM Online</span>
            </div>
            <div class="web-search-box">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <circle cx="11" cy="11" r="8"/>
                    <path d="m21 21-4.35-4.35"/>
                </svg>
                <input type="text" placeholder="Search LLM..." class="web-search-input">
            </div>
            <div class="web-action-buttons">
                <button class="web-action-btn primary" id="addLLMBtn">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M12 5v14M5 12h14"/>
                    </svg>
                    Add
                </button>
                <button class="web-action-btn" id="manageLLMBtn">
                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                        <circle cx="12" cy="12" r="3"/>
                        <path d="M19.4 15a1.65 1.65 0 0 0 .33 1.82l.06.06a2 2 0 0 1 0 2.83 2 2 0 0 1-2.83 0l-.06-.06a1.65 1.65 0 0 0-1.82-.33 1.65 1.65 0 0 0-1 1.51V21a2 2 0 0 1-2 2 2 2 0 0 1-2-2v-.09A1.65 1.65 0 0 0 9 19.4a1.65 1.65 0 0 0-1.82.33l-.06.06a2 2 0 0 1-2.83 0 2 2 0 0 1 0-2.83l.06-.06a1.65 1.65 0 0 0 .33-1.82 1.65 1.65 0 0 0-1.51-1H3a2 2 0 0 1-2-2 2 2 0 0 1 2-2h.09A1.65 1.65 0 0 0 4.6 9a1.65 1.65 0 0 0-.33-1.82l-.06-.06a2 2 0 0 1 0-2.83 2 2 0 0 1 2.83 0l.06.06a1.65 1.65 0 0 0 1.82.33H9a1.65 1.65 0 0 0 1-1.51V3a2 2 0 0 1 2-2 2 2 0 0 1 2 2v.09a1.65 1.65 0 0 0 1 1.51 1.65 1.65 0 0 0 1.82-.33l.06-.06a2 2 0 0 1 2.83 0 2 2 0 0 1 0 2.83l-.06.06a1.65 1.65 0 0 0-.33 1.82V9a1.65 1.65 0 0 0 1.51 1H21a2 2 0 0 1 2 2 2 2 0 0 1-2 2h-.09a1.65 1.65 0 0 0-1.51 1z"/>
                    </svg>
                    Manage
                </button>
            </div>
            <div class="web-llm-grid">
                ${this.renderWebLLMIcons()}
            </div>
            <div class="web-tools-category">
                <div class="web-category-header">
                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                        <path d="M14.7 6.3a1 1 0 0 0 0 1.4l1.6 1.6a1 1 0 0 0 1.4 0l3.77-3.77a6 6 0 0 1-7.94 7.94l-6.91 6.91a2.12 2.12 0 0 1-3-3l6.91-6.91a6 6 0 0 1 7.94-7.94l-3.76 3.76z"/>
                    </svg>
                    <span>AI Tools Online</span>
                    <svg viewBox="0 0 24 24" width="12" height="12" fill="none" stroke="currentColor" stroke-width="2" class="chevron">
                        <polyline points="6 9 12 15 18 9"/>
                    </svg>
                </div>
                <div class="web-tools-list">
                    <div class="web-tool-item" data-url="https://www.midjourney.com">
                        <span class="tool-dot"></span>
                        <span>Midjourney</span>
                    </div>
                    <div class="web-tool-item" data-url="https://www.runway.ml">
                        <span class="tool-dot"></span>
                        <span>Runway</span>
                    </div>
                    <div class="web-tool-item" data-url="https://elevenlabs.io">
                        <span class="tool-dot"></span>
                        <span>ElevenLabs</span>
                    </div>
                    <div class="web-tool-item" data-url="https://www.perplexity.ai">
                        <span class="tool-dot"></span>
                        <span>Perplexity</span>
                    </div>
                </div>
            </div>
        `;
    },

    renderWebLLMIcons() {
        const llms = [
            { name: 'DeepSeek', url: 'https://chat.deepseek.com', color: '#1a73e8' },
            { name: 'OpenAI', url: 'https://chat.openai.com', color: '#10a37f' },
            { name: 'Claude', url: 'https://claude.ai', color: '#d97706' },
            { name: 'Gemini', url: 'https://gemini.google.com', color: '#4285f4' },
            { name: 'Llama', url: 'https://llama.meta.com', color: '#0668E1' },
            { name: 'Mistral', url: 'https://chat.mistral.ai', color: '#FF7000' },
            { name: 'Grok', url: 'https://grok.x.ai', color: '#1DA1F2' },
            { name: 'Kimi', url: 'https://kimi.moonshot.cn', color: '#000000' },
            { name: 'Zhipu', url: 'https://chatglm.cn', color: '#4F46E5' },
            { name: 'Tongyi', url: 'https://tongyi.aliyun.com', color: '#FF6A00' }
        ];

        return llms.map(llm => `
            <div class="web-llm-icon-box" data-url="${llm.url}" title="${llm.name}">
                ${this.getWebLLMIcon(llm.name, llm.color)}
            </div>
        `).join('');
    },

    getWebLLMIcon(name, color) {
        const icons = {
            'DeepSeek': `<svg viewBox="0 0 24 24" width="24" height="24"><rect fill="${color}" x="2" y="2" width="20" height="20" rx="4"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="10" font-weight="bold">DS</text></svg>`,
            'OpenAI': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><path d="M12 6v6l4 2" stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>`,
            'Claude': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><path d="M8 12h8M12 8v8" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>`,
            'Gemini': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><circle fill="white" cx="8" cy="10" r="2"/><circle fill="white" cx="16" cy="10" r="2"/><path d="M8 15c2 2 6 2 8 0" stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round"/></svg>`,
            'Llama': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="8" font-weight="bold">🦙</text></svg>`,
            'Mistral': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><path d="M7 8h10M7 12h10M7 16h10" stroke="white" stroke-width="2" stroke-linecap="round"/></svg>`,
            'Grok': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="10" font-weight="bold">X</text></svg>`,
            'Kimi': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><circle fill="white" cx="12" cy="12" r="4"/></svg>`,
            'Zhipu': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="8" font-weight="bold">Z</text></svg>`,
            'Tongyi': `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/><text x="12" y="16" text-anchor="middle" fill="white" font-size="8" font-weight="bold">T</text></svg>`
        };
        return icons[name] || `<svg viewBox="0 0 24 24" width="24" height="24"><circle fill="${color}" cx="12" cy="12" r="10"/></svg>`;
    }
};

// ==================== Page Controllers ====================

const PageControllers = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },

    getMapIframeTargetOrigin(iframe) {
        try {
            const src = iframe ? iframe.getAttribute('src') : '';
            if (src) {
                const u = new URL(src, window.location && window.location.href ? window.location.href : undefined);
                return u.origin;
            }
        } catch (e) {
        }
        const agentBase = (window.appConfig && window.appConfig.agent_server) ? String(window.appConfig.agent_server) : '';
        try {
            if (agentBase) return new URL(agentBase).origin;
        } catch (e) {
        }
        return '*';
    },
    // Home page controller
    initHomePage() {
        this.loadHomeStats();
        this.bindHomeEvents();
    },

    loadHomeStats() {
        // Load statistics
        api.getAgents().then(response => {
            const count = document.getElementById('agentCount');
            if (count) count.textContent = (response.data || []).length;
        }).catch(() => {});

        api.getKnowledgeBases().then(response => {
            const count = document.getElementById('kmCount');
            if (count) count.textContent = (response.data || []).length;
        }).catch(() => {});

        api.getPlugins().then(response => {
            const count = document.getElementById('pluginCount');
            if (count) count.textContent = (response.data || []).length;
        }).catch(() => {});
    },

    bindHomeEvents() {
        document.querySelectorAll('.sidebar-menu-item').forEach(item => {
            item.addEventListener('click', () => {
                const action = item.dataset.action;
                switch (action) {
                    case 'initialization':
                        this.showInitializationModal();
                        break;
                    case 'help':
                        this.showHelpModal();
                        break;
                    case 'new-agent':
                        App.navigateTo('agent');
                        break;
                    case 'new-km':
                        App.navigateTo('km');
                        break;
                }
            });
        });
    },

    showInitializationModal() {
        Modal.show({
            title: 'Initialization',
            content: `
                <div class="init-settings">
                    <div class="setting-group">
                        <label>Default AI model</label>
                        <select class="setting-select">
                            <option value="gpt-4">GPT-4</option>
                            <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                            <option value="claude-3">Claude 3</option>
                            <option value="deepseek">DeepSeek</option>
                        </select>
                    </div>
                    <div class="setting-group">
                        <label>API Key</label>
                        <input type="password" class="setting-input" placeholder="Enter your API key">
                    </div>
                    <div class="setting-group">
                        <label>Language</label>
                        <select class="setting-select">
                            <option value="zh">Chinese</option>
                            <option value="en">English</option>
                        </select>
                    </div>
                </div>
            `,
            confirmText: 'Save',
            onConfirm: () => {
                Notification.success('Settings saved');
            }
        });
    },

    async showConfigurationModal() {
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

                    const localRes = await window.electronAPI.writeConfigJson({ agent_server, ai_sns_server });
                    if (!localRes || !localRes.success) {
                        if (typeof Notification !== 'undefined' && Notification.error) {
                            Notification.error(localRes?.error || 'Failed to save locally');
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
        Modal.show({
            title: 'Help',
            content: `
                <div class="help-content">
                    <h4>Quick start</h4>
                    <p>1. Configure your LLM plugins on the Tools page</p>
                    <p>2. Create an AI Agent on the Agent page and start chatting</p>
                    <p>3. Manage your knowledge base on the KM page</p>
                    <p>4. Explore the social network on the SNS page</p>
                    <h4>Contact us</h4>
                    <p>GitHub: <a href="https://github.com/ai-sns" target="_blank">github.com/ai-sns</a></p>
                </div>
            `,
            showCancel: false
        });
    },

    // SNS page controller
    initSNSPage() {
        console.log('SNS page controller initialized');
        this.loadMapIframe();
        this.loadSNSData();
        this.initSNSPanelResizer();
        this.initSNSStatusTabs();
        this.initSNSToolbar();
        this.initSNSSettingsPanel();
        this.initSNSActionBar();
    },

    // Initialize the SNS top toolbar collapse behavior
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

    // Initialize the SNS right-side settings panel collapse behavior
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
    },

    // Initialize the SNS bottom action bar
    initSNSActionBar() {
        const actionBar = document.querySelector('.map-action-bar');
        if (!actionBar) return;

        // Action button click handler
        actionBar.addEventListener('click', (e) => {
            const btn = e.target.closest('.action-btn');
            if (!btn) return;

            const action = btn.dataset.action;
            if (!action) return;

            // Update active state
            const allBtns = actionBar.querySelectorAll('.action-btn');
            allBtns.forEach(b => b.classList.remove('active'));
            btn.classList.add('active');

            // Handle different actions
            console.log('SNS Action:', action);
        });

        // Start button
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

    // Initialize the SNS right-side panel collapse behavior
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

        // Collapse/expand button click handler
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
            e.preventDefault();
        });

        document.addEventListener('mousemove', (e) => {
            if (!isResizing) return;

            // Drag left to increase width, drag right to decrease width
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
            }
        });
    },

    // Initialize SNS status tab switching
    initSNSStatusTabs() {
        const tabsContainer = document.getElementById('statusTabs');
        const tabContent = document.getElementById('statusTabContent');

        if (!tabsContainer || !tabContent) return;

        tabsContainer.addEventListener('click', (e) => {
            const tabBtn = e.target.closest('.status-tab');
            if (!tabBtn) return;

            const targetTab = tabBtn.dataset.tab;
            if (!targetTab) return;

            // Update active button state
            tabsContainer.querySelectorAll('.status-tab').forEach(btn => {
                btn.classList.toggle('active', btn === tabBtn);
            });

            // Switch content panels
            tabContent.querySelectorAll('.tab-pane').forEach(pane => {
                pane.classList.toggle('active', pane.dataset.tab === targetTab);
            });
        });
    },

    async loadMapIframe() {
        const mapContainer = document.getElementById('mapContainer');
        if (!mapContainer) {
            console.error('Map container not found');
            return;
        }

        console.log('Loading map');

        // Show map content immediately; do not show loading animation
        const placeholder = mapContainer.querySelector('.map-placeholder');
        if (placeholder) {
            placeholder.remove();
        }

        // Check whether the map has already been loaded
        const existingIframe = mapContainer.querySelector('iframe');
        if (existingIframe) {
            console.log('Map already loaded; showing directly');
            return;
        }

        // Get map configuration
        let mapUrl = this.resolve('/scripts/map.html'); // Default: Baidu Map
        try {
            const response = await fetch(this.resolve('/api/sns/map-config'));
            const result = await response.json();

            console.log('Map config API response:', result);

            if (result.success && result.data) {
                const mapType = String(result.data.map_type).trim();
                console.log('Map type:', mapType);

                if (mapType === '0') {
                    mapUrl = this.resolve('/scripts/googlemap3d.html');
                    console.log('Loading Google Map');
                } else {
                    console.log('Loading Baidu Map');
                }
            }
        } catch (error) {
            console.error('Failed to fetch map config:', error);
        }

        console.log('Final map URL:', mapUrl);

        // Create an iframe to load the map page
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

        // Establish communication after the iframe finishes loading
        iframe.onload = () => {
            console.log('Map page loaded');

            // Send initial data to the iframe
            const initialData = {
                type: 'init',
                data: {
                    message: 'Hello from AI-SNS Electron App!',
                    timestamp: Date.now()
                }
            };

            try {
                iframe.contentWindow.postMessage(initialData, this.getMapIframeTargetOrigin(iframe));
                console.log('Initialization message sent');
            } catch (error) {
                console.error('Failed to send message to map page:', error);
            }
        };

        // Listen for iframe load failures
        iframe.onerror = () => {
            console.error('Map page failed to load');
            // Create error display
            const errorDiv = document.createElement('div');
            errorDiv.className = 'map-placeholder';
            errorDiv.style.zIndex = '10';
            errorDiv.innerHTML = `
                <div class="map-placeholder-icon">
                    <svg viewBox="0 0 24 24" width="48" height="48" fill="currentColor">
                        <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/>
                    </svg>
                </div>
                <p class="map-placeholder-text">Failed to load map</p>
                <p class="map-placeholder-desc">Please check whether the map server configuration is correct</p>
                <button class="map-retry-btn" onclick="PageControllers.tryLoadMap()">Retry</button>
            `;
            mapContainer.appendChild(errorDiv);
        };

        // Listen for messages from the iframe
        const handleMessage = (event) => {
            if (event.origin === this.getMapIframeTargetOrigin(iframe)) {
                const data = event.data;
                console.log('Received map page message:', data);

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
                        console.log('Unknown message type:', data.type);
                }
            }
        };

        window.addEventListener('message', handleMessage);
        iframe._messageListener = handleMessage;
    },

    tryLoadMap() {
        const mapContainer = document.getElementById('mapContainer');
        if (!mapContainer) return;

        console.log('Trying to reload the map');

        // Remove the existing iframe (if any)
        const existingIframe = mapContainer.querySelector('iframe');
        if (existingIframe) {
            // Remove event listener
            if (existingIframe._messageListener) {
                window.removeEventListener('message', existingIframe._messageListener);
            }
            existingIframe.remove();
        }

        // Remove existing error message
        const existingErrorDiv = mapContainer.querySelector('.map-placeholder');
        if (existingErrorDiv) {
            existingErrorDiv.remove();
        }

        // Create a new loading animation
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

        // Delay calling initMap to show the loading animation
        setTimeout(() => {
            this.initMap();
        }, 500);
    },
    handleLocationUpdate(data) {
        console.log('Location update:', data);
        // You can update the UI to display the current location
        // For example: update location info in the status panel
        const lngElement = document.querySelector('.status-row.sub span[class="value"]');
        const latElement = document.querySelectorAll('.status-row.sub span[class="value"]')[1];
        if (lngElement && data.lng) {
            lngElement.textContent = `: ${data.lng}`;
        }
        if (latElement && data.lat) {
            latElement.textContent = `: ${data.lat}`;
        }
    },

    // Handle map click events
    handleMapClick(data) {
        console.log('Map click:', data);
        // You can add markers on the map or perform other actions
    },

    // Handle marker add events
    handleMarkerAdd(data) {
        console.log('Marker added:', data);
        // You can add custom markers on the map
    },

    // Send a message to the map page
    sendMessageToMap(type, data) {
        const iframe = document.querySelector('#mapContainer iframe');
        if (iframe && iframe.contentWindow) {
            const message = {
                type: type,
                data: data
            };
            iframe.contentWindow.postMessage(message, this.getMapIframeTargetOrigin(iframe));
        }
    },

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

    // Agent page controller
    initAgentPage() {
        this.loadAgentList();
        this.loadChatList();
        this.bindAgentEvents();
        this.initChatStreamListeners();
        // Initialize chat history
        this.chatHistory = [];
        // Current request ID
        this.currentRequestId = null;
        // Current streaming content
        this.streamingContent = '';
    },

    // Initialize streaming chat listeners
    initChatStreamListeners() {
        if (!window.electronAPI) return;

        // Clear existing listeners
        window.electronAPI.removeChatStreamListeners();

        // Listen for streaming data
        window.electronAPI.onChatStreamData((data) => {
            if (data.requestId === this.currentRequestId) {
                this.streamingContent += data.content;
                this.updateStreamingMessage(this.streamingContent);
            }
        });

        // Listen for stream end
        window.electronAPI.onChatStreamEnd((data) => {
            if (data.requestId === this.currentRequestId) {
                this.finalizeStreamingMessage();
                this.currentRequestId = null;
            }
        });

        // Listen for errors
        window.electronAPI.onChatStreamError((data) => {
            if (data.requestId === this.currentRequestId) {
                this.showStreamError(data.error);
                this.currentRequestId = null;
            }
        });
    },

    // Update streaming message display
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

    // Finalize streaming message
    finalizeStreamingMessage() {
        const streamingMsg = document.querySelector('.message-item.streaming');
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                streamingBody.innerHTML = this.renderMarkdown(this.streamingContent);
                // Highlight code blocks
                this.highlightCodeBlocks(streamingBody);
            }
        }
        // Save to history
        this.chatHistory.push({
            role: 'assistant',
            content: this.streamingContent
        });
        this.streamingContent = '';
    },

    // Show stream error
    showStreamError(error) {
        const streamingMsg = document.querySelector('.message-item.streaming');
        if (streamingMsg) {
            streamingMsg.classList.remove('streaming');
            streamingMsg.classList.add('error-message');
            const streamingBody = streamingMsg.querySelector('.message-body');
            if (streamingBody) {
                streamingBody.innerHTML = `<div class="error-content"><svg viewBox="0 0 24 24" width="16" height="16" fill="#d93025"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm1 15h-2v-2h2v2zm0-4h-2V7h2v6z"/></svg><span>Request failed: ${this.escapeHtml(error)}</span></div>`;
            }
        }
    },

    // Markdown rendering
    renderMarkdown(text, isStreaming = false) {
        if (!text) return '';

        // Preserve code blocks to avoid being processed by other rules
        const codeBlocks = [];

        // Full code block handling (```language\ncode```)
        text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const language = lang || 'plaintext';
            const escapedCode = this.escapeHtml(code.trim());
            const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
            codeBlocks.push(`<div class="code-block"><div class="code-header"><span class="code-lang">${language}</span><button class="copy-code-btn" onclick="PageControllers.copyCode(this)"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg><span>Copy</span></button></div><pre><code class="language-${language}">${escapedCode}</code></pre></div>`);
            return placeholder;
        });

        // Handle incomplete code blocks (during streaming output)
        if (isStreaming) {
            text = text.replace(/```(\w*)\n?([\s\S]*)$/g, (match, lang, code) => {
                // Check whether it has already been handled as a full code block (ends with a placeholder)
                if (match.includes('__CODEBLOCK_')) return match;
                const language = lang || 'plaintext';
                const escapedCode = this.escapeHtml(code);
                const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
                codeBlocks.push(`<div class="code-block streaming-code"><div class="code-header"><span class="code-lang">${language}</span></div><pre><code class="language-${language}">${escapedCode}</code></pre></div>`);
                return placeholder;
            });
        }

        // Inline code (avoid processing code block placeholders)
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

        // Ordered lists
        text = text.replace(/^\d+\. (.+)$/gm, '<li>$1</li>');

        // Links
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

        // Blockquotes
        text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

        // Horizontal rules
        text = text.replace(/^---$/gm, '<hr>');

        // Line break handling
        text = text.replace(/\n\n/g, '</p><p>');
        text = text.replace(/\n/g, '<br>');

        // Wrap in a paragraph
        if (!text.startsWith('<') && !text.startsWith('__CODEBLOCK_')) {
            text = '<p>' + text + '</p>';
        }

        // Restore code blocks
        codeBlocks.forEach((block, index) => {
            text = text.replace(`__CODEBLOCK_${index}__`, block);
        });

        return text;
    },

    // Code highlighting (simple implementation)
    highlightCodeBlocks(container) {
        container.querySelectorAll('pre code').forEach(block => {
            // Skip if already highlighted
            if (block.dataset.highlighted) return;
            block.dataset.highlighted = 'true';

            // Get plain text content
            let code = block.textContent;

            // Save raw code for copying
            block.dataset.rawCode = code;

            // Simple highlighting: only keywords; no complex transformations
            // Escape HTML first
            let highlighted = this.escapeHtml(code);

            // Keyword highlighting (use word boundaries for exact matches)
            const keywords = [
                'function', 'const', 'let', 'var', 'if', 'else', 'for', 'while', 'return',
                'class', 'import', 'export', 'from', 'async', 'await', 'try', 'catch',
                'throw', 'new', 'this', 'true', 'false', 'null', 'undefined',
                'def', 'print', 'self', 'None', 'True', 'False', 'in', 'not', 'and',
                'or', 'is', 'with', 'as', 'break', 'continue', 'pass', 'raise',
                'except', 'finally', 'lambda', 'yield', 'elif', 'range', 'len'
            ];

            // Use a single regex to replace all keywords in one pass
            const keywordPattern = new RegExp(`\\b(${keywords.join('|')})\\b`, 'g');
            highlighted = highlighted.replace(keywordPattern, '<span class="hljs-keyword">$1</span>');

            // Number highlighting
            highlighted = highlighted.replace(/\b(\d+\.?\d*)\b/g, '<span class="hljs-number">$1</span>');

            // String highlighting (simple: match quoted content)
            highlighted = highlighted.replace(/(&quot;[^&]*&quot;|&#39;[^&]*&#39;)/g, '<span class="hljs-string">$1</span>');

            // Comment highlighting
            highlighted = highlighted.replace(/(\/\/.*$|#.*$)/gm, '<span class="hljs-comment">$1</span>');

            block.innerHTML = highlighted;
        });
    },

    // Copy code
    copyCode(btn) {
        const codeBlock = btn.closest('.code-block');
        const codeElement = codeBlock.querySelector('code');
        // Prefer the stored raw code; fallback to textContent
        const code = codeElement.dataset.rawCode || codeElement.textContent;

        navigator.clipboard.writeText(code).then(() => {
            const originalText = btn.querySelector('span').textContent;
            btn.querySelector('span').textContent = 'Copied!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.querySelector('span').textContent = originalText;
                btn.classList.remove('copied');
            }, 2000);
        });
    },

    async loadAgentList() {
        const agentList = document.getElementById('agentList');
        if (!agentList) return;

        try {
            const response = await api.getAgents();
            const agents = response.data || [];

            if (agents.length === 0) {
                agentList.innerHTML = '<div class="empty-state">No agents yet. Click + to create one.</div>';
                return;
            }

            agentList.innerHTML = agents.map(agent => `
                <div class="agent-item" data-id="${agent.id}">
                    <div class="agent-avatar">
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="#1a73e8">
                            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                        </svg>
                    </div>
                    <div class="agent-info">
                        <div class="agent-name">${agent.name}</div>
                        <div class="agent-model">${agent.model || 'GPT-4'}</div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            agentList.innerHTML = '<div class="empty-state error">Load failed</div>';
        }
    },

    async loadChatList() {
        const chatList = document.getElementById('chatList');
        if (!chatList) return;

        try {
            const response = await api.getChatHistory();
            const chats = response.data || [];

            if (chats.length === 0) {
                chatList.innerHTML = '<div class="empty-state">No conversations yet. Click + to create one.</div>';
                return;
            }

            chatList.innerHTML = chats.map(chat => `
                <div class="chat-item" data-id="${chat.id}">
                    <div class="chat-icon">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="#5f6368">
                            <path d="M20 2H4c-1.1 0-2 .9-2 2v18l4-4h14c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm0 14H6l-2 2V4h16v12z"/>
                        </svg>
                    </div>
                    <div class="chat-info">
                        <div class="chat-title">${chat.title || 'New chat'}</div>
                        <div class="chat-preview">${chat.lastMessage || ''}</div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            chatList.innerHTML = '<div class="empty-state">No conversations</div>';
        }
    },

    bindAgentEvents() {
        // New chat button
        const newChatBtn = document.getElementById('newChatBtn');
        if (newChatBtn) {
            newChatBtn.addEventListener('click', () => this.showNewChatModal());
        }

        // New agent button
        const newAgentBtn = document.getElementById('newAgentBtn');
        if (newAgentBtn) {
            newAgentBtn.addEventListener('click', () => this.showNewAgentModal());
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
    },

    showNewChatModal() {
        Modal.show({
            title: 'New chat',
            content: `
                <div class="form-group">
                    <label>Select agent</label>
                    <select class="form-select" id="selectAgent">
                        <option value="">Please select...</option>
                    </select>
                </div>
            `,
            confirmText: 'Start',
            onConfirm: () => {
                Notification.success('Chat created');
            }
        });

        // Load agent options
        api.getAgents().then(response => {
            const select = document.getElementById('selectAgent');
            if (select) {
                (response.data || []).forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.id;
                    option.textContent = agent.name;
                    select.appendChild(option);
                });
            }
        });
    },

    showNewAgentModal() {
        Modal.show({
            title: 'Create agent',
            content: `
                <div class="form-group">
                    <label>Name</label>
                    <input type="text" class="form-input" id="agentName" placeholder="Enter agent name">
                </div>
                <div class="form-group">
                    <label>Model</label>
                    <select class="form-select" id="agentModel">
                        <option value="gpt-4">GPT-4</option>
                        <option value="gpt-3.5-turbo">GPT-3.5 Turbo</option>
                        <option value="claude-3">Claude 3</option>
                        <option value="deepseek">DeepSeek</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <textarea class="form-textarea" id="agentDesc" placeholder="Describe what the agent does"></textarea>
                </div>
            `,
            confirmText: 'Create',
            onConfirm: async () => {
                const name = document.getElementById('agentName').value;
                if (!name) {
                    Notification.error('Please enter an agent name');
                    return false;
                }
                try {
                    await api.createAgent({
                        name,
                        model: document.getElementById('agentModel').value,
                        description: document.getElementById('agentDesc').value
                    });
                    Notification.success('Agent created successfully');
                    this.loadAgentList();
                } catch (error) {
                    Notification.error('Creation failed: ' + error.message);
                    return false;
                }
            }
        });
    },

    async sendMessage() {
        const input = document.getElementById('chatInput');
        const messagesContainer = document.getElementById('chatMessages');
        const sendBtn = document.getElementById('sendMessageBtn');

        if (!input || !messagesContainer) return;

        const message = input.value.trim();
        if (!message) return;

        // If streaming is in progress, do not allow sending a new message
        if (this.currentRequestId) {
            return;
        }

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

        // Get current timestamp
        const now = new Date();
        const timeStr = now.toLocaleString('zh-CN', {
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
        this.chatHistory.push({
            role: 'user',
            content: message
        });

        // Add AI response container (with thinking animation)
        const currentAgentName = (window.agentState && typeof window.agentState.getCurrentAgent === 'function')
            ? (window.agentState.getCurrentAgent()?.name || 'AI Assistant')
            : 'AI Assistant';
        const assistantMessageHtml = `
            <div class="message-item assistant-message streaming">
                <div class="message-header">
                    <div class="message-avatar assistant-avatar">
                        <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg>
                    </div>
                    <span class="message-sender">${this.escapeHtml(currentAgentName)}</span>
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
        this.currentRequestId = 'req_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
        this.streamingContent = '';

        // Get system prompt
        const roleSelector = document.getElementById('roleSelector');
        let systemPrompt = 'You are a helpful AI assistant.';
        if (roleSelector) {
            const role = roleSelector.value;
            switch (role) {
                case 'senior-dev':
                    systemPrompt = 'You are a senior software engineer with over 15 years of experience. You are proficient in multiple programming languages and frameworks, and you write high-quality, maintainable code. Answer in a professional but easy-to-understand way, and provide code examples when necessary.';
                    break;
                case 'assistant':
                    systemPrompt = 'You are a general AI assistant who can help answer a wide range of questions. Respond in a friendly and clear way.';
                    break;
                case 'writer':
                    systemPrompt = 'You are a professional creative writer skilled in many styles, including stories, essays, and poems. Be creative and provide high-quality writing.';
                    break;
                case 'analyst':
                    systemPrompt = 'You are a professional data analyst skilled in data analysis, statistics, and visualization. Analyze problems from a professional perspective and provide data support when needed.';
                    break;
            }
        }

        // Build messages array
        const messages = [
            { role: 'system', content: systemPrompt },
            ...this.chatHistory
        ];

        // Helper to re-enable send button
        const enableSendBtn = () => {
            if (sendBtn) {
                sendBtn.disabled = false;
                sendBtn.classList.remove('sending');
            }
        };

        // Start streaming request
        if (window.electronAPI && window.electronAPI.chatStreamStart) {
            window.electronAPI.chatStreamStart(messages, this.currentRequestId);

            // Timeout handling
            setTimeout(() => {
                if (this.currentRequestId) {
                    this.showStreamError('Request timed out. Please try again.');
                    this.currentRequestId = null;
                    enableSendBtn();
                }
            }, 120000); // 2-minute timeout

            // Poll completion to re-enable button
            const checkComplete = setInterval(() => {
                if (!this.currentRequestId) {
                    enableSendBtn();
                    clearInterval(checkComplete);
                }
            }, 100);
        } else {
            // If electronAPI is not available, use a mock response
            this.simulateStreamResponse(enableSendBtn);
        }
    },

    // Simulate streaming response (for development/testing)
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
                this.streamingContent += chars[index];
                this.updateStreamingMessage(this.streamingContent);
                index++;
            } else {
                clearInterval(streamInterval);
                this.finalizeStreamingMessage();
                this.currentRequestId = null;
                if (enableSendBtn) enableSendBtn();
            }
        }, 20);
    },

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    // KM page controller
    initKMPage() {
        this.loadNoteList();
        this.bindKMEvents();
    },

    async loadNoteList() {
        const noteList = document.getElementById('noteList');
        if (!noteList) return;

        try {
            const response = await api.getKnowledgeBases();
            const notes = response.data || [];

            if (notes.length === 0) {
                noteList.innerHTML = '<div class="empty-state">No notes yet. Click + to create one.</div>';
                return;
            }

            noteList.innerHTML = notes.map(note => `
                <div class="note-item" data-id="${note.id}">
                    <div class="note-icon">
                        <svg viewBox="0 0 24 24" width="18" height="18" fill="#5f6368">
                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                        </svg>
                    </div>
                    <div class="note-info">
                        <div class="note-title">${note.name}</div>
                        <div class="note-date">${note.updated_at || ''}</div>
                    </div>
                </div>
            `).join('');
        } catch (error) {
            noteList.innerHTML = '<div class="empty-state">No notes</div>';
        }
    },

    bindKMEvents() {
        // New note button
        const newNoteBtn = document.getElementById('newNoteBtn');
        if (newNoteBtn) {
            newNoteBtn.addEventListener('click', () => this.showNewNoteModal());
        }

        // New knowledge base button
        const newKMBtn = document.getElementById('newKMBtn');
        if (newKMBtn) {
            newKMBtn.addEventListener('click', () => this.showNewKMModal());
        }

        // Toolbar buttons - fix button class binding
        document.querySelectorAll('.km-tool-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                // Determine action type
                let action = btn.dataset.action;
                if (!action) {
                    // If there is no data-action, infer from button attributes
                    if (btn.classList.contains('format-btn')) {
                        action = btn.dataset.format;
                    } else if (btn.dataset.align) {
                        action = btn.dataset.align;
                    } else {
                        // For buttons without explicit data-action, infer from title
                        const title = btn.getAttribute('title');
                        switch(title) {
                            case '粗体':
                            case 'Bold':
                                action = 'bold';
                                break;
                            case '斜体':
                            case 'Italic':
                                action = 'italic';
                                break;
                            case '下划线':
                            case 'Underline':
                                action = 'underline';
                                break;
                            case '删除线':
                            case 'Strikethrough':
                                action = 'strikethrough';
                                break;
                            case '上标':
                            case 'Superscript':
                                action = 'superscript';
                                break;
                            case '下标':
                            case 'Subscript':
                                action = 'subscript';
                                break;
                            case '左对齐':
                            case 'Align left':
                                action = 'justifyLeft';
                                break;
                            case '居中':
                            case 'Align center':
                                action = 'justifyCenter';
                                break;
                            case '右对齐':
                            case 'Align right':
                                action = 'justifyRight';
                                break;
                            case '两端对齐':
                            case 'Justify':
                                action = 'justifyFull';
                                break;
                            case '无序列表':
                            case 'Bulleted list':
                                action = 'insertUnorderedList';
                                break;
                            case '有序列表':
                            case 'Numbered list':
                                action = 'insertOrderedList';
                                break;
                            case '增加缩进':
                            case 'Increase indent':
                                action = 'indent';
                                break;
                            case '减少缩进':
                            case 'Decrease indent':
                                action = 'outdent';
                                break;
                            case '保存':
                            case 'Save':
                                action = 'save';
                                break;
                            case '打印':
                            case 'Print':
                                action = 'print';
                                break;
                            case '复制':
                            case 'Copy':
                                action = 'copy';
                                break;
                            case '剪切':
                            case 'Cut':
                                action = 'cut';
                                break;
                            case '粘贴':
                            case 'Paste':
                                action = 'paste';
                                break;
                            case '撤销':
                            case 'Undo':
                                action = 'undo';
                                break;
                            case '重做':
                            case 'Redo':
                                action = 'redo';
                                break;
                            case '搜索':
                            case 'Search':
                                action = 'search';
                                break;
                            case '日期':
                            case 'Date':
                                action = 'insertDate';
                                break;
                            case '表格':
                            case 'Table':
                                action = 'insertTable';
                                break;
                            case '图片':
                            case 'Image':
                                action = 'insertImage';
                                break;
                            case '链接':
                            case 'Link':
                                action = 'createLink';
                                break;
                            case '表情':
                            case 'Emoticon':
                                action = 'insertEmoticon';
                                break;
                            case '符号':
                            case 'Symbol':
                                action = 'insertSpecialChar';
                                break;
                        }
                    }
                }

                console.log('KM Editor Action:', action);
                this.executeEditorAction(action);
            });
        });
    },

    showNewNoteModal() {
        Modal.show({
            title: 'New note',
            content: `
                <div class="form-group">
                    <label>Title</label>
                    <input type="text" class="form-input" id="noteTitle" placeholder="Enter note title">
                </div>
            `,
            confirmText: 'Create',
            onConfirm: () => {
                const title = document.getElementById('noteTitle').value;
                if (!title) {
                    Notification.error('Please enter a note title');
                    return false;
                }
                Notification.success('Note created');
            }
        });
    },

    showNewKMModal() {
        Modal.show({
            title: 'New knowledge base',
            content: `
                <div class="form-group">
                    <label>Name</label>
                    <input type="text" class="form-input" id="kmName" placeholder="Enter knowledge base name">
                </div>
                <div class="form-group">
                    <label>Type</label>
                    <select class="form-select" id="kmType">
                        <option value="vector">Vector database</option>
                        <option value="graph">Knowledge graph</option>
                        <option value="document">Document library</option>
                    </select>
                </div>
            `,
            confirmText: 'Create',
            onConfirm: async () => {
                const name = document.getElementById('kmName').value;
                if (!name) {
                    Notification.error('Please enter a knowledge base name');
                    return false;
                }
                try {
                    await api.createKnowledgeBase({
                        name,
                        km_type: document.getElementById('kmType').value
                    });
                    Notification.success('Knowledge base created successfully');
                    this.loadNoteList();
                } catch (error) {
                    Notification.error('Creation failed: ' + error.message);
                    return false;
                }
            }
        });
    },

    // Save note
    saveNote() {
        const noteContent = document.getElementById('noteContent');
        const noteTitle = document.getElementById('noteTitle'); // Assume the title input ID is noteTitle
        if (!noteContent) return;

        const content = noteContent.innerHTML;
        const title = noteTitle ? noteTitle.value : 'Untitled';

        // Add persistence logic here, e.g. send to backend API
        console.log('Saving note:', title, content);
        // Notification.success('Note saved');
    },

    // Show search dialog
    showSearchDialog() {
        const searchTerm = prompt('Enter search text:');
        if (searchTerm) {
            const noteContent = document.getElementById('noteContent');
            if (noteContent) {
                // Simple search implementation
                const text = noteContent.innerText;
                const index = text.indexOf(searchTerm);
                if (index !== -1) {
                    alert(`Found at position ${index}`);
                } else {
                    alert('Not found');
                }
            }
        }
    },

    // Insert table
    insertTable() {
        const rows = prompt('Enter number of rows:');
        const cols = prompt('Enter number of columns:');

        if (rows && cols) {
            let tableHtml = '<table border="1" cellpadding="5" cellspacing="0">';
            for (let i = 0; i < parseInt(rows); i++) {
                tableHtml += '<tr>';
                for (let j = 0; j < parseInt(cols); j++) {
                    tableHtml += '<td>&nbsp;</td>';
                }
                tableHtml += '</tr>';
            }
            tableHtml += '</table>';

            document.execCommand('insertHTML', false, tableHtml);
        }
    },

    // Insert emoticon
    insertEmoticon() {
        const emoticon = prompt('Enter an emoticon:');
        if (emoticon) {
            document.execCommand('insertText', false, emoticon);
        }
    },

    // Insert special character
    insertSpecialChar() {
        const specialChar = prompt('Enter a special character:');
        if (specialChar) {
            document.execCommand('insertText', false, specialChar);
        }
    },

    // Execute editor action
    executeEditorAction(action) {
        const noteContent = document.getElementById('noteContent');
        if (!noteContent) return;

        switch (action) {
            case 'bold':
                document.execCommand('bold', false, null);
                break;
            case 'italic':
                document.execCommand('italic', false, null);
                break;
            case 'underline':
                document.execCommand('underline', false, null);
                break;
            case 'strikethrough':
                document.execCommand('strikeThrough', false, null);
                break;
            case 'superscript':
                document.execCommand('superscript', false, null);
                break;
            case 'subscript':
                document.execCommand('subscript', false, null);
                break;
            case 'justifyLeft':
                document.execCommand('justifyLeft', false, null);
                break;
            case 'justifyCenter':
                document.execCommand('justifyCenter', false, null);
                break;
            case 'justifyRight':
                document.execCommand('justifyRight', false, null);
                break;
            case 'justifyFull':
                document.execCommand('justifyFull', false, null);
                break;
            case 'insertUnorderedList':
                document.execCommand('insertUnorderedList', false, null);
                break;
            case 'insertOrderedList':
                document.execCommand('insertOrderedList', false, null);
                break;
            case 'indent':
                document.execCommand('indent', false, null);
                break;
            case 'outdent':
                document.execCommand('outdent', false, null);
                break;
            case 'h1':
                document.execCommand('formatBlock', false, '<h1>');
                break;
            case 'h2':
                document.execCommand('formatBlock', false, '<h2>');
                break;
            case 'h3':
                document.execCommand('formatBlock', false, '<h3>');
                break;
            case 'link':
                const url = prompt('Enter link URL:');
                if (url) document.execCommand('createLink', false, url);
                break;
            case 'image':
                const imgUrl = prompt('Enter image URL:');
                if (imgUrl) document.execCommand('insertImage', false, imgUrl);
                break;
            case 'code':
                document.execCommand('formatBlock', false, '<pre>');
                break;
            case 'save':
                this.saveNote();
                break;
            case 'print':
                window.print();
                break;
            case 'copy':
                document.execCommand('copy', false, null);
                break;
            case 'cut':
                document.execCommand('cut', false, null);
                break;
            case 'paste':
                document.execCommand('paste', false, null);
                break;
            case 'undo':
                document.execCommand('undo', false, null);
                break;
            case 'redo':
                document.execCommand('redo', false, null);
                break;
            case 'search':
                this.showSearchDialog();
                break;
            case 'insertDate':
                const now = new Date();
                const dateStr = now.toLocaleString('zh-CN');
                document.execCommand('insertText', false, dateStr);
                break;
            case 'insertTable':
                this.insertTable();
                break;
            case 'insertEmoticon':
                this.insertEmoticon();
                break;
            case 'insertSpecialChar':
                this.insertSpecialChar();
                break;
            default:
                console.log('Unknown action:', action);
        }
    },

    // Tools page controller
    initToolsPage() {
        this.toolsManager = new window.ToolsManager();
        this.currentToolTab = 'plugins';
        this.bindToolsEvents();
        this.loadToolsData();
    },

    async loadToolsData() {
        console.log('Loading tools data for tab:', this.currentToolTab);
        try {
            const items = await this.toolsManager.loadCurrentTab();
            console.log('Loaded items:', items);
            this.renderToolsContent(items);
        } catch (error) {
            console.error('Error loading tools data:', error);
            const contentArea = document.getElementById('toolsContentArea');
            if (contentArea) {
                contentArea.innerHTML = `
                    <div class="tools-empty">
                        <p class="tools-empty-title">Error Loading Tools</p>
                        <p class="tools-empty-text">${error.message}</p>
                    </div>
                `;
            }
        }
    },

    renderToolsContent(items) {
        const contentArea = document.getElementById('toolsContentArea');
        if (!contentArea) return;

        // If there is no data, show empty state
        if (!items || items.length === 0) {
            contentArea.innerHTML = `
                <div class="tools-empty">
                    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
                        <rect x="3" y="3" width="18" height="18" rx="2"/>
                        <line x1="9" y1="9" x2="15" y2="15"/>
                        <line x1="15" y1="9" x2="9" y2="15"/>
                    </svg>
                    <h3 class="tools-empty-title">No Tools Found</h3>
                    <p class="tools-empty-text">Click "Add New Tool" to create your first ${this.getToolTypeName(this.currentToolTab)}</p>
                </div>
            `;
            return;
        }

        let html = '<div class="tools-grid">';
        items.forEach(item => {
            html += this.renderToolCard(item);
        });
        html += '</div>';
        contentArea.innerHTML = html;
    },

    renderToolCard(item) {
        const type = this.currentToolTab;
        const id = item.plugin_id || item.mcp_id || item.function_id || item.skill_id;

        return `
            <div class="tool-card" data-id="${id}" data-type="${type}">
                <div class="tool-card-header">
                    <h3 class="tool-card-title">${item.name}</h3>
                    <div class="tool-card-actions">
                        <button class="tool-btn-edit" onclick="PageControllers.editTool('${id}', '${type}')">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M11 4H4a2 2 0 0 0-2 2v14a2 2 0 0 0 2 2h14a2 2 0 0 0 2-2v-7"/>
                                <path d="M18.5 2.5a2.121 2.121 0 0 1 3 3L12 15l-4 1 1-4 9.5-9.5z"/>
                            </svg>
                        </button>
                        <button class="tool-btn-delete" onclick="PageControllers.deleteTool('${id}', '${type}')">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M3 6h18M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2m3 0v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6h14"/>
                            </svg>
                        </button>
                    </div>
                </div>
                <div class="tool-card-body">
                    <p class="tool-card-description">${item.description || 'No description'}</p>
                    ${item.instruction ? `<p class="tool-card-instruction"><strong>Instruction:</strong> ${item.instruction}</p>` : ''}
                </div>
                <div class="tool-card-footer">
                    <span class="tool-card-badge">${this.getToolTypeName(type)}</span>
                    ${item.confirm_needed ? '<span class="tool-card-badge">Confirm Required</span>' : ''}
                </div>
            </div>
        `;
    },

    getToolTypeName(type) {
        const names = {
            'plugins': 'Plugin',
            'mcp': 'MCP',
            'functions': 'Function',
            'skills': 'Computer Use'
        };
        return names[type] || type;
    },

    async switchToolTab(tabName) {
        console.log('Switching tool tab to:', tabName);
        this.currentToolTab = tabName;
        this.toolsManager.switchTab(tabName);

        // Show loading state
        const contentArea = document.getElementById('toolsContentArea');
        if (contentArea) {
            contentArea.innerHTML = '<div class="tools-loading">Loading tools...</div>';
        }

        // Load data
        await this.loadToolsData();

        // Update tab UI
        document.querySelectorAll('.tools-tab-item').forEach(tab => {
            tab.classList.toggle('active', tab.dataset.tab === tabName);
        });

        console.log('Tab switched successfully');
    },

    async editTool(id, type) {
        // Show edit dialog
        console.log('Edit tool:', id, type);
        // TODO: Implement edit dialog
    },

    async deleteTool(id, type) {
        const confirmed = await (async () => {
            try {
                if (window.Toast && typeof window.Toast.confirm === 'function') {
                    return await window.Toast.confirm('Delete this tool?', {
                        title: 'Delete Tool',
                        confirmText: 'Delete',
                        cancelText: 'Cancel',
                        type: 'warning'
                    });
                }

                if (window.Modal && typeof window.Modal.show === 'function') {
                    return await new Promise((resolve) => {
                        window.Modal.show({
                            title: 'Delete Tool',
                            content: '<p>Delete this tool?</p>',
                            confirmText: 'Delete',
                            cancelText: 'Cancel',
                            onConfirm: () => {
                                resolve(true);
                                return true;
                            },
                            onCancel: () => {
                                resolve(false);
                                return true;
                            }
                        });
                    });
                }
            } catch (e) {
                console.error('Failed to show delete confirmation dialog:', e);
            }
            return false;
        })();

        if (!confirmed) return;

        try {
            switch (type) {
                case 'plugins':
                    await this.toolsManager.deletePlugin(id);
                    break;
                case 'mcp':
                    await this.toolsManager.deleteMCP(id);
                    break;
                case 'functions':
                    await this.toolsManager.deleteFunction(id);
                    break;
                case 'skills':
                    await this.toolsManager.deleteSkill(id);
                    break;
            }
            await this.loadToolsData();
        } catch (error) {
            console.error('Error deleting tool:', error);
        }
    },

    showAddToolDialog() {
        const type = this.currentToolTab;
        // TODO: Show add tool dialog based on current tab
        console.log('Add new', this.getToolTypeName(type));
    },

    bindToolsEvents() {
        // Sidebar category click - switch tabs
        const categoryItems = document.querySelectorAll('.tools-category-item');
        categoryItems.forEach((item) => {
            item.addEventListener('click', () => {
                const tabName = item.dataset.tab;
                if (tabName) {
                    console.log('Switching to tab:', tabName); // Debug log
                    this.switchToolTab(tabName);
                    // Update sidebar selected state
                    categoryItems.forEach(ci => ci.classList.remove('active'));
                    item.classList.add('active');
                }
            });
        });

        // Marketplace tab switch
        document.querySelectorAll('.market-tab').forEach(tab => {
            tab.addEventListener('click', () => {
                document.querySelectorAll('.market-tab').forEach(t => t.classList.remove('active'));
                tab.classList.add('active');
                // Optionally filter plugins by tab
            });
        });

        // Import plugin button
        const importBtn = document.getElementById('importPluginBtn');
        if (importBtn) {
            importBtn.addEventListener('click', () => this.showImportPluginModal());
        }

        // LLM icon click
        document.querySelectorAll('.llm-icon-item').forEach(item => {
            item.addEventListener('click', () => {
                document.querySelectorAll('.llm-icon-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            });
        });

        // Download button
        document.querySelectorAll('.plugin-download-btn').forEach(btn => {
            btn.addEventListener('click', () => {
                Notification.info('Plugin download is under development...');
            });
        });
    },

    showImportPluginModal() {
        Modal.show({
            title: 'Import plugin',
            content: `
                <div class="form-group">
                    <label>Plugin file</label>
                    <input type="file" class="form-input" id="pluginFile" accept=".zip,.json">
                </div>
                <p class="form-hint">Supports plugin files in .zip or .json format</p>
            `,
            confirmText: 'Import',
            onConfirm: () => {
                const fileInput = document.getElementById('pluginFile');
                if (!fileInput.files.length) {
                    Notification.error('Please select a plugin file');
                    return false;
                }
                Notification.success('Plugin imported successfully');
            }
        });
    },

    // Web page controller
    initWebPage() {
        this.bindWebEvents();
    },

    bindWebEvents() {
        const addressInput = document.getElementById('addressInput');
        const goBtn = document.getElementById('browserGo');
        const backBtn = document.getElementById('browserBack');
        const forwardBtn = document.getElementById('browserForward');
        const refreshBtn = document.getElementById('browserRefresh');
        const webFrame = document.getElementById('webFrame');

        if (goBtn && addressInput && webFrame) {
            goBtn.addEventListener('click', () => {
                let url = addressInput.value.trim();
                if (url && !url.startsWith('http')) {
                    url = 'https://' + url;
                }
                webFrame.src = url;
            });

            addressInput.addEventListener('keydown', (e) => {
                if (e.key === 'Enter') {
                    goBtn.click();
                }
            });
        }

        if (backBtn) {
            backBtn.addEventListener('click', () => {
                window.history.back();
            });
        }

        if (forwardBtn) {
            forwardBtn.addEventListener('click', () => {
                window.history.forward();
            });
        }

        if (refreshBtn && webFrame) {
            refreshBtn.addEventListener('click', () => {
                webFrame.src = webFrame.src;
            });
        }

        // Service list click
        document.querySelectorAll('.web-service-item').forEach(item => {
            item.addEventListener('click', () => {
                const url = item.dataset.url;
                if (url && addressInput && webFrame) {
                    addressInput.value = url;
                    webFrame.src = url;
                }
                document.querySelectorAll('.web-service-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
            });
        });
    }
};

// ==================== Exports ====================

window.PageRenderers = PageRenderers;
window.PageControllers = PageControllers;
