/**
 * SNS Module - Main Page Content
 * SNS main content rendering
 */

export default {
    /**
     * Render SNS main content
     */
    render() {
        return `
            <div class="sns-page-layout">
                <!-- Map main area -->
                <div class="sns-map-area">
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

                    <!-- Modern bottom action bar -->
                    <div class="map-action-bar">
                        <!-- State 1: Default toolbar (menubar001 style) -->
                        <div class="action-bar-state-1" id="actionBarState1">
                            <div class="action-bar-left">
                                <button class="action-btn" data-action="square">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                        <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                                        <polyline points="9 22 9 12 15 12 15 22"/>
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
                                <button class="action-btn" data-action="move">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" style="transform: rotate(-45deg)">
                                        <polygon points="3 11 22 2 13 21 11 13 3 11"/>
                                    </svg>
                                    <span>Move</span>
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
                                <button class="action-btn" data-action="plugin">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M19.439 7.85c.157-.24.245-.525.245-.814V3a1 1 0 0 0-1-1h-3.95c-.289 0-.574.088-.814.245a2.5 2.5 0 1 1-3.84 0A1.5 1.5 0 0 0 9.266 2H5.316a1 1 0 0 0-1 1v3.95c0 .289-.088.574-.245.814a2.5 2.5 0 1 1 0 3.84c.157.24.245.525.245.814V20a1 1 0 0 0 1 1h3.95c.289 0 .574-.088.814-.245a2.5 2.5 0 1 1 3.84 0c.24.157.525.245.814.245h3.95a1 1 0 0 0 1-1v-3.95c0-.289.088-.574.245-.814a2.5 2.5 0 1 1 0-3.84Z"/>
                                    </svg>
                                    <span>Plugin</span>
                                </button>
                                <button class="action-btn" data-action="help">
                                    <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                        <circle cx="12" cy="12" r="10"/>
                                        <path d="M9.09 9a3 3 0 1 1 5.82 1c0 2-3 3-3 3"/>
                                        <line x1="12" y1="17" x2="12.01" y2="17"/>
                                    </svg>
                                    <span>Help</span>
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
                                        <button class="dropdown-item" data-action="square">
                                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                                                <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/>
                                                <polyline points="9 22 9 12 15 12 15 22"/>
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
                                        <button class="dropdown-item" data-action="move">                                            
                                            <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" style="transform: rotate(45deg)">
                                                <polygon points="3 11 22 2 13 21 11 13 3 11"/>
                                            </svg>
                                            <span>Move</span>
                                        </button>
                                    </div>
                                </div>
                                <div class="control-center-input">
                                    <button class="control-computer-btn" id="computerBtn">
                                        <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
    <!-- Monitor frame -->
    <rect x="2" y="3" width="20" height="14" rx="2" ry="2"/>
    <line x1="8" y1="21" x2="16" y2="21"/>
    <line x1="12" y1="17" x2="12" y2="21"/>
    <!-- Cross icon -->
    <line x1="9" y1="7" x2="15" y2="13"/>
    <line x1="15" y1="7" x2="9" y2="13"/>
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
                                        <button class="dropdown-item" data-action="help">
                                            <span>Help</span>
                                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                                <circle cx="12" cy="12" r="10"/>
                                                <path d="M9.09 9a3 3 0 1 1 5.82 1c0 2-3 3-3 3"/>
                                                <line x1="12" y1="17" x2="12.01" y2="17"/>
                                            </svg>
                                        </button>
                                        <button class="dropdown-item" data-action="plugin">
                                            <span>Plugin</span>
                                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                                <path d="M19.439 7.85c.157-.24.245-.525.245-.814V3a1 1 0 0 0-1-1h-3.95c-.289 0-.574.088-.814.245a2.5 2.5 0 1 1-3.84 0A1.5 1.5 0 0 0 9.266 2H5.316a1 1 0 0 0-1 1v3.95c0 .289-.088.574-.245.814a2.5 2.5 0 1 1 0 3.84c.157.24.245.525.245.814V20a1 1 0 0 0 1 1h3.95c.289 0 .574-.088.814-.245a2.5 2.5 0 1 1 3.84 0c.24.157.525.245.814.245h3.95a1 1 0 0 0 1-1v-3.95c0-.289.088-.574.245-.814a2.5 2.5 0 1 1 0-3.84Z"/>
                                            </svg>
                                        </button>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>

                    <!-- Map control button group removed -->
                </div>

                <!-- Right status panel resizer -->
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

                <!-- Right status panel -->
                <div class="sns-status-panel" id="snsStatusPanel">
                    <!-- Search bar (hidden by default, opened via context menu) -->
                    <div class="status-search-bar" id="statusSearchBar" style="display: none;">
                        <div class="search-input-wrapper">
                            <svg class="search-icon" viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                <circle cx="11" cy="11" r="8"/>
                                <path d="m21 21-4.35-4.35"/>
                            </svg>
                            <input type="text" class="search-input" id="statusSearchInput" placeholder="Search within the current tab...">
                            <button class="search-clear-btn" id="statusSearchClear" title="Close search">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                            </button>
                        </div>
                        <div class="search-results-info" id="searchResultsInfo" style="display: none;">
                            <span id="searchResultsText">Found 0 results</span>
                            <div class="search-navigation">
                                <button class="search-nav-btn" id="searchPrevBtn" title="Previous">
                                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                                        <polyline points="15 18 9 12 15 6"/>
                                    </svg>
                                </button>
                                <button class="search-nav-btn" id="searchNextBtn" title="Next">
                                    <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                                        <polyline points="9 18 15 12 9 6"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                    </div>
                    
                    <!-- Context menu -->
                    <div class="status-context-menu" id="statusContextMenu" style="display: none;">
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
                    </div>
                    
                    <!-- Tab content area - entire panel content switches with tabs -->
                    <div class="status-tab-content" id="statusTabContent">
                        <!-- Process tab content -->
                        <div class="tab-pane active" data-tab="process">
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/></svg> Current Status</div>
                                <div class="status-rows">
                                    <span class="na">N/A</span>
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
 
                                </div>
                            </div>
                        </div>
                        <!-- Think tab content -->
                        <div class="tab-pane" data-tab="think">
                            <div class="status-section">
                                <div class="status-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/></svg>
                                    AI Model
                                    <button class="refresh-btn" id="refreshModelInfoBtn" title="Refresh model info">
                                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                                            <polyline points="23 4 23 10 17 10"></polyline>
                                            <polyline points="1 20 1 14 7 14"></polyline>
                                            <path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"></path>
                                        </svg>
                                    </button>
                                </div>
                                <div class="status-rows">
                                    <div class="status-row"><span>👤 Agent</span><span class="value" id="agentValue">: Loading...</span></div>
                                    <div class="status-row"><span>🔧 Provider</span><span class="value" id="providerValue">: Loading...</span></div>
                                    <div class="status-row"><span>🧠 Model</span><span class="value" id="modelValue">: Loading...</span></div>

                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8"><path d="M12 3v10.55c-.59-.34-1.27-.55-2-.55-2.21 0-4 1.79-4 4s1.79 4 4 4 4-1.79 4-4V7h4V3h-6z"/></svg> Thinking Log</div>
                                <div class="status-rows">

                                </div>
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

    /**
     * Initialize SNS page
     */
    async init() {
        // Load model info
        await this.loadModelInfo();

        // Setup refresh button event listener
        const refreshBtn = document.getElementById('refreshModelInfoBtn');
        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                await this.loadModelInfo();
            });
        }
    },

    /**
     * Load model info
     */
    async loadModelInfo() {
        try {
            // Import snsApi
            const snsApi = (await import('./snsApi.js')).default;

            // Fetch model info
            const result = await snsApi.getModelInfo();

            if (result.success && result.data) {
                const { agent, provider, model } = result.data;

                // Update UI
                const agentValue = document.getElementById('agentValue');
                const providerValue = document.getElementById('providerValue');
                const modelValue = document.getElementById('modelValue');

                if (agentValue) agentValue.textContent = `: ${agent}`;
                if (providerValue) providerValue.textContent = `: ${provider}`;
                if (modelValue) modelValue.textContent = `: ${model}`;
            } else {
                console.error('Failed to load model info:', result.error);
                // Set error state
                const agentValue = document.getElementById('agentValue');
                const providerValue = document.getElementById('providerValue');
                const modelValue = document.getElementById('modelValue');

                if (agentValue) agentValue.textContent = ': N/A';
                if (providerValue) providerValue.textContent = ': N/A';
                if (modelValue) modelValue.textContent = ': N/A';
            }
        } catch (error) {
            console.error('Error loading model info:', error);
            // Set error state
            const agentValue = document.getElementById('agentValue');
            const providerValue = document.getElementById('providerValue');
            const modelValue = document.getElementById('modelValue');

            if (agentValue) agentValue.textContent = ': Error';
            if (providerValue) providerValue.textContent = ': Error';
            if (modelValue) modelValue.textContent = ': Error';
        }
    }
};
