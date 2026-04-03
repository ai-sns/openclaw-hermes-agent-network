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
                                                <button class="toggle-btn active" data-mode="ai">My AI</button>
                                                <button class="toggle-btn" data-mode="friends">Target</button>
                                            </div>
                                        </div>
                                        <div class="control-input-wrapper">
                                            <input type="text" class="control-input" placeholder="Human input..." title="Type @ to show suggestions. Use ArrowUp/ArrowDown to browse input history." spellcheck="false" autocomplete="off" autocorrect="off" autocapitalize="off" />
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
                                <div class="status-section-title"><svg height="16" viewBox="0 -960 960 960" width="16" fill="#1a73e8"><path d="m403-96-22-114q-23-9-44.5-21T296-259l-110 37-77-133 87-76q-2-12-3-24t-1-25q0-13 1-25t3-24l-87-76 77-133 110 37q19-16 40.5-28t44.5-21l22-114h154l22 114q23 9 44.5 21t40.5 28l110-37 77 133-87 76q2 12 3 24t1 25q0 13-1 25t-3 24l87 76-77 133-110-37q-19 16-40.5 28T579-210L557-96H403Zm59-72h36l19-99q38-7 71-26t57-48l96 32 18-30-76-67q6-17 9.5-35.5T696-480q0-20-3.5-38.5T683-554l76-67-18-30-96 32q-24-29-57-48t-71-26l-19-99h-36l-19 99q-38 7-71 26t-57 48l-96-32-18 30 76 67q-6 17-9.5 35.5T264-480q0 20 3.5 38.5T277-406l-76 67 18 30 96-32q24 29 57 48t71 26l19 99Zm18-168q60 0 102-42t42-102q0-60-42-102t-102-42q-60 0-102 42t-42 102q0 60 42 102t102 42Zm0-144Z"/></svg> Current Status</div>
                                <div class="status-rows">
                                    <span class="na">N/A</span>
                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg height="16" viewBox="0 -960 960 960" width="16" fill="#1a73e8"><path d="M324-168h312v-120q0-65-45.5-110.5T480-444q-65 0-110.5 45.5T324-288v120Zm266.5-393.5Q636-607 636-672v-120H324v120q0 65 45.5 110.5T480-516q65 0 110.5-45.5ZM192-96v-72h60v-120q0-59 28-109.5t78-82.5q-49-32-77.5-82.5T252-672v-120h-60v-72h576v72h-60v120q0 59-28.5 109.5T602-480q50 32 78 82.5T708-288v120h60v72H192Zm288-72Zm0-624Z"/></svg> On Going</div>
                                <div class="status-rows"><span class="na">N/A</span></div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg height="16" viewBox="0 -960 960 960" width="16" fill="#1a73e8"><path d="M240-96q-46 0-71-24.5T144-192v-144h96v-528l57.6 58 57.6-58 57.6 58 57.6-58 57.6 58 57.6-58 57.6 58 57.6-58 57.6 58 57.6-58v660q0 47-31 77.5T708-96H240Zm468-72q16 0 26-9.5t10-26.5v-540H312v408h360v132q0 17 10 26.5t26 9.5ZM360-600v-72h216v72H360Zm0 120v-72h216v72H360Zm300-120q-14 0-25-10.29t-11-25.5q0-15.21 11-25.71t25.5-10.5q14.5 0 25 10.29t10.5 25.5q0 15.21-10.35 25.71T660-600Zm0 120q-14 0-25-10.29t-11-25.5q0-15.21 11-25.71t25.5-10.5q14.5 0 25 10.29t10.5 25.5q0 15.21-10.35 25.71T660-480ZM240-168h360v-96H216v72q0 17 3.5 20.5T240-168Zm-24 0v-96 96Z"/></svg> Process History</div>
                                <div class="status-rows"><span class="na">N/A</span></div>
                            </div>
                        </div>
                        <!-- Resource tab content -->
                        <div class="tab-pane" data-tab="resource">
                            <div class="status-section">
                                <div class="status-section-title"><svg height="16" viewBox="0 -960 960 960" width="16" fill="#1a73e8"><path d="m505.88-216 94.06-56.59L694-216l-25-107 83-71-109-10-43-100-43 100-109 10 82.69 70.99L505.88-216ZM264-408v72h-96q-29.7 0-50.85-21.15Q96-378.3 96-408v-384q0-29.7 21.15-50.85Q138.3-864 168-864h384q29.7 0 50.85 21.15Q624-821.7 624-792v96h-72v-96H168v384h96ZM408-96q-29.7 0-50.85-21.15Q336-138.3 336-168v-384q0-29.7 21.15-50.85Q378.3-624 408-624h384q29.7 0 50.85 21.15Q864-581.7 864-552v384q0 29.7-21.15 50.85Q821.7-96 792-96H408Zm0-72h384v-384H408v384Zm192-192Z"/></svg> Resource Overview</div>
                                <div class="status-rows">
 
                                </div>
                            </div>
                        </div>
                        <!-- Think tab content -->
                        <div class="tab-pane" data-tab="think">
                            <div class="status-section">
                                <div class="status-section-title">
                                    <svg height="16" viewBox="0 -960 960 960" width="16" fill="#1a73e8"><path d="M395-144q-47 0-80-31t-38-77q-57-6-95-48t-38-100.02q0-19.98 4.5-41.48Q153-463 164-480q-10-17.07-15-36.03-5-18.97-5-39.31 0-56.39 37-97.52Q218-694 275-702q2-48 37.04-81t82.99-33q23.97 0 45.97 9t39.46 26q16.54-17 37.87-26t45.44-9Q612-816 647-783q35 33 37 81 57 7 94.5 48.72T816-555q0 20.94-5.5 39.97Q805-496 795-479q12 20 16.5 40t4.5 39.48q0 57.52-38.5 100.02Q739-257 682-252q-5 46-38 77t-80.27 31q-23.17 0-44.95-8.5T480-178q-17 16-39.03 25T395-144Zm121-551.3v431.6q0 19.7 13.92 34.2Q543.84-215 564-215q20 0 33-14t14-34q-19-8-35.07-20.33Q559.86-295.65 547-313q-9-12.48-6.5-26.74Q543-354 555.5-363q12.5-9 26.98-6.76Q596.95-367.53 606-355q10.55 15.03 26.86 23.02 16.3 7.98 35.49 7.98Q700-324 722-346t22-54q0-7-1-13t-3-12q-15.9 9-34.13 13.5Q687.64-407 668-407q-15.3 0-25.65-10.29Q632-427.58 632-442.79t10.35-25.71Q652.7-479 668-479q32 0 54-22t22-53.53q0-31.52-22-53.5Q700-630 666.25-631 655-614 639.5-601T604-581q-14 5-27.5-1.26-13.5-6.27-18.5-20.58-5-14.32 1.5-27.74Q566-644 580.45-649 594-654 603-666.39t9-28.59q0-20.02-13.92-34.52Q584.16-744 564-744q-20.16 0-34.08 14.5Q516-715 516-695.3ZM444-264v-431.31q0-19.69-14.5-34.19Q415-744 394.89-744q-20.12 0-34 14.28Q347-715.44 347-694.76q0 15.76 9 28.26 9 12.5 22.55 17.5 14.45 5 20.95 18.37Q406-617.26 401-603q-5 14-18.5 20.5T355-581q-20-7-35.5-20t-26.76-30Q260-630 238-608t-22 53.02Q216-523 238-501q22 22 54 22 15.3 0 25.65 10.29Q328-458.42 328-443.21t-10.35 25.71Q307.3-407 292-407q-19.6 0-37.8-5-18.2-5-34.2-14-2 6-3 12.67-1 6.66-1 13.33 0 32 22 54t53.65 22q19.19 0 35.49-7.98Q343.45-339.97 354-355q9.29-13.26 24.14-15.63Q393-373 405-364t14.5 24q2.5 15-6.25 27.3Q401-296 384.5-283T348-262q1 20 14 33t32.71 13q20.7 0 35-13.92Q444-243.84 444-264Zm36-215Z"/></svg>
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
                                    <div class="status-row"><span>🤖 Agent</span><span class="value" id="agentValue"> Loading...</span></div>
                                    <div class="status-row"><span>☁️ Provider</span><span class="value" id="providerValue"> Loading...</span></div>
                                    <div class="status-row"><span>🧠 Model</span><span class="value" id="modelValue"> Loading...</span></div>

                                </div>
                            </div>
                            <div class="status-section">
                                <div class="status-section-title"><svg height="16" viewBox="0 -960 960 960" width="16" fill="#1a73e8"><path d="M264-96v-175q-57-48-88.5-115.57T144-529q0-139.58 98.29-237.29Q340.58-864 481-864q109 0 196 58.5T792-653l66 223q5 17.48-5.5 31.74Q842-384 824-384h-56v120q0 29.7-21.15 50.85Q725.7-192 696-192h-96v96h-72v-168h168v-192h80l-52-173q-22-72-89.5-117.5T481-792q-111 0-188 76.63T216-529q0 58.93 25 111.96Q266-364 311-326l25 22v208h-72Zm232-348Zm-44.67 60H509l4-42q11.43-3.82 20.71-8.91Q543-440 552-448l38 17 29-50-33-24q2-11.5 2-23t-2-23l33-24-29-50-38 17q-8-8-18-13t-21-9l-4.33-42H451l-4 42q-11.43 3.82-20.71 8.91Q417-616 408-608l-38-17-29 50 33 24q-2 11.5-2 23t2 23l-33 24 29 50 38-17q8 8 18 13t21 9l4.33 42ZM446-494q-14-14-14-34t14-34q14-14 34-14t34 14q14 14 14 34t-14 34q-14 14-34 14t-34-14Z"/></svg> Thinking Log</div>
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

                if (agentValue) agentValue.textContent = ` ${agent}`;
                if (providerValue) providerValue.textContent = ` ${provider}`;
                if (modelValue) modelValue.textContent = ` ${model}`;
            } else {
                console.error('Failed to load model info:', result.error);
                // Set error state
                const agentValue = document.getElementById('agentValue');
                const providerValue = document.getElementById('providerValue');
                const modelValue = document.getElementById('modelValue');

                if (agentValue) agentValue.textContent = ' N/A';
                if (providerValue) providerValue.textContent = ' N/A';
                if (modelValue) modelValue.textContent = ' N/A';
            }
        } catch (error) {
            console.error('Error loading model info:', error);
            // Set error state
            const agentValue = document.getElementById('agentValue');
            const providerValue = document.getElementById('providerValue');
            const modelValue = document.getElementById('modelValue');

            if (agentValue) agentValue.textContent = ' Error';
            if (providerValue) providerValue.textContent = ' Error';
            if (modelValue) modelValue.textContent = ' Error';
        }
    }
};
