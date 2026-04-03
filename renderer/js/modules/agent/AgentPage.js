/**
 * Agent Page - main content rendering (multi-agent dynamic loading version)
 * AI chat UI
 */

const AgentPage = {
    /**
     * Render main content area - returns base structure; init() fills it dynamically
     */
    render() {
        return `<div id="agent-pages-container"></div>`;
    },

    /**
     * Initialize - create a page for each Agent
     */
    async init(agents) {
        console.log('[AgentPage] Initializing, agents count:', agents.length);

        const container = document.getElementById('agent-pages-container');
        if (!container) {
            console.error('[AgentPage] agent-pages-container not found');
            return;
        }

        agents.forEach((agent, index) => {
            const pageHTML = this.createAgentPageHTML(agent, index === 0);
            container.insertAdjacentHTML('beforeend', pageHTML);
        });

        console.log('[AgentPage] All agent pages created');
    },

    /**
     * Create page HTML for a single Agent
     */
    createAgentPageHTML(agent, isActive = false) {
        const rawAgentType = String(agent.agent_type || 'local').toLowerCase();
        const isRemote = rawAgentType === 'remote' || rawAgentType === 'remote agent' || rawAgentType === 'remote_agent';
        const agentType = isRemote ? 'remote' : 'local';
        return `
            <div id="page-agent-${agent.id}" class="agent-page-layout" data-agent-id="${agent.id}" data-agent-type="${agentType}" style="display: ${isActive ? 'flex' : 'none'}">
                <!-- Main chat area -->
                <div class="agent-chat-area">
                    <!-- Top toolbar -->
                    <div class="agent-chat-toolbar">
                        <div class="toolbar-left">
                            <svg width="20" height="20" viewBox="0 0 100 100" fill="none" xmlns="http://www.w3.org/2000/svg">
                              <defs>
                                <style>
                                  .z-icon-stroke { stroke: #1a73e8; stroke-width: 8; stroke-linecap: round; stroke-linejoin: round; }
                                  .z-icon-circle { fill: none; stroke: #1a73e8; stroke-width: 8; }
                                </style>
                              </defs>
                              <g class="z-icon-stroke">
                                <!-- Middle horizontal line (left -> right) -->
                                <path d="M18 50 H82" />
                                
                                <!-- "Z" main strokes (top-left -> top-right -> bottom-left -> bottom-right) -->
                                <path d="M28 22 H72 L28 78 H72" />
                                
                                <!-- Short stroke at top-left (toward center) -->
                                <path d="M28 22 L42 36" />
                                
                                <!-- Short stroke at bottom-right (toward center) -->
                                <path d="M72 78 L58 64" />
                              </g>
                              <g class="z-icon-circle">
                                <!-- Center circle -->
                                <circle cx="50" cy="50" r="7" />
                                
                                <!-- Left circle -->
                                <circle cx="18" cy="50" r="7" />
                                <!-- Right circle -->
                                <circle cx="82" cy="50" r="7" />
                                
                                <!-- Top-left circle -->
                                <circle cx="28" cy="22" r="7" />
                                <!-- Top-right circle -->
                                <circle cx="72" cy="22" r="7" />
                                
                                <!-- Bottom-left circle -->
                                <circle cx="28" cy="78" r="7" />
                                <!-- Bottom-right circle -->
                                <circle cx="72" cy="78" r="7" />
                              </g>
                            </svg>
                            <select class="model-selector" id="modelSelector-${agent.id}" data-agent-id="${agent.id}" ${isRemote ? 'disabled' : ''}>
                            </select>
                        </div>

                        <div class="toolbar-right">
            <svg viewBox="0 0 100 100" xmlns="http://www.w3.org/2000/svg" width="20" height="20" stroke="#1a73e8" fill="#1a73e8">
       
                <circle cx="50" cy="50" r="45" fill="1a73e8" stroke="#1a73e8" stroke-width="2" stroke-dasharray="4 4" opacity="0.2"/>
               
                <g class="char-spark">
                    <circle cx="50" cy="35" r="15" />
                    <path d="M50,55 C30,55 20,70 20,90 L80,90 C80,70 70,55 50,55 Z" />
                
                    <path d="M80,20 L82,28 L90,30 L82,32 L80,40 L78,32 L70,30 L78,28 Z" />
                </g>
            </svg>
                            <select class="role-selector" id="roleSelector-${agent.id}" data-agent-id="${agent.id}" ${isRemote ? 'disabled' : ''}>
                                <option value="senior-dev">Senior Developer</option>
                                <option value="assistant">General Assistant</option>
                                <option value="writer">Creative Writing</option>
                                <option value="analyst">Data Analyst</option>
                            </select>
                        </div>
                    </div>

                    <!-- Messages area -->
                    <div class="agent-chat-messages" id="chatMessages-${agent.id}" data-agent-id="${agent.id}">
                        <!-- Welcome message -->
                        <div class="welcome-message">
                            <div class="welcome-icon">
<svg viewBox="0 0 48 48" width="64" height="64" xmlns="http://www.w3.org/2000/svg">
    <defs>
        <linearGradient id="robotGrad-${agent.id}" x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" style="stop-color:#11998e"/>
            <stop offset="100%" style="stop-color:#38ef7d"/>
        </linearGradient>
    </defs>
    <circle cx="24" cy="24" r="22" fill="url(#robotGrad-${agent.id})" opacity="0.1"/>
    <g transform="translate(4.8, 4.8) scale(0.8)">       
        <path d="
            M24 7v3 M21 7h6 
            M16 12h16a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H16a3 3 0 0 1-3-3V15a3 3 0 0 1 3-3z
            M19 19h2 M27 19h2
            M11 34c0-3 3-5 6-5h14c3 0 6 2 6 5v4H11v-4z
        " fill="none" stroke="url(#robotGrad-${agent.id})" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/>              
        <circle cx="20" cy="19" r="1.5" fill="url(#robotGrad-${agent.id})"/>
        <circle cx="28" cy="19" r="1.5" fill="url(#robotGrad-${agent.id})"/>
    </g>
</svg>
                            </div>
                            <h2 class="welcome-title">${agent.name || 'AI Assistant'}</h2>
                            <p class="welcome-subtitle">${agent.description || 'Powered by OpenAI GPT'}</p>
                        </div>
                    </div>

                    <!-- Input area -->
                    <div class="agent-chat-input-area">
                        <div style="display: none;" class="input-hint">Input @@ to load tools selector; Ctrl+i To load preset question; Ctrl+/ To insert chat template.</div>
                        <div class="input-wrapper">
                            <textarea class="agent-chat-input" id="chatInput-${agent.id}" data-agent-id="${agent.id}" placeholder="Type a message..." title="Type @ to show suggestions. Use ArrowUp/ArrowDown to browse input history." spellcheck="false"></textarea>
                        </div>
                        <div class="input-toolbar">
                            <div class="toolbar-buttons">
                                <button class="toolbar-icon-btn config-tools-btn" title="Configure tools" data-agent-id="${agent.id}">
                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                        <path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/>
                                    </svg>
                                </button>
                                <button class="toolbar-icon-btn" title="Configure knowledge base" data-action="kb-config" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                  <path d="M12 2C7.58 2 4 3.79 4 6v12c0 2.21 3.58 4 8 4s8-1.79 8-4V6c0-2.21-3.58-4-8-4zm0 2c3.87 0 6 .99 6 2s-2.13 2-6 2-6-.99-6-2 2.13-2 6-2zm0 14c-3.87 0-6-.99-6-2v-2c1.46 1.01 4.05 1.5 6 1.5s4.54-.49 6-1.5v2c0 1.01-2.13 2-6 2zm0-6c-3.87 0-6-.99-6-2V8c1.46 1.01 4.05 1.5 6 1.5S16.54 9.01 18 8v2c0 1.01-2.13 2-6 2z"/>
                                </svg>
                                </button>
                                <button class="toolbar-icon-btn" title="Attachment" data-action="attachment" data-agent-id="${agent.id}"><svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor"><path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/></svg></button>
                                
                                <button class="toolbar-icon-btn" title="Add Plugin" data-action="add-plugin" data-agent-id="${agent.id}">

                                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <path d="M19.439 7.85c.157-.24.245-.525.245-.814V3a1 1 0 0 0-1-1h-3.95c-.289 0-.574.088-.814.245a2.5 2.5 0 1 1-3.84 0A1.5 1.5 0 0 0 9.266 2H5.316a1 1 0 0 0-1 1v3.95c0 .289-.088.574-.245.814a2.5 2.5 0 1 1 0 3.84c.157.24.245.525.245.814V20a1 1 0 0 0 1 1h3.95c.289 0 .574-.088.814-.245a2.5 2.5 0 1 1 3.84 0c.24.157.525.245.814.245h3.95a1 1 0 0 0 1-1v-3.95c0-.289.088-.574.245-.814a2.5 2.5 0 1 1 0-3.84Z"/>
                                    </svg>
                                </button>

                                <button class="toolbar-icon-btn" title="3D Avatar" data-agent-id="${agent.id}">       
                                        
                                        <svg height="22" viewBox="0 -960 960 960" width="22" fill="currentColor">
                                            <path d="M664-121q-8-2-15-7l-120-70q-14-8-21.5-21.5T500-249v-141q0-16 7.5-29.5T529-441l120-70q7-5 15-7t16-2q8 0 15.5 2.5T710-511l120 70q14 8 22 21.5t8 29.5v141q0 16-8 29.5T830-198l-120 70q-7 4-14.5 6.5T680-119q-8 0-16-2ZM287-527q-47-47-47-113t47-113q47-47 113-47t113 47q47 47 47 113t-47 113q-47 47-113 47t-113-47ZM80-160v-112q0-33 17-62t47-44q51-26 115-44t141-18h14q6 0 12 2-8 18-13.5 37.5T404-360h-4q-71 0-127.5 18T180-306q-9 5-14.5 14t-5.5 20v32h252q6 21 16 41.5t22 38.5H80Zm376.5-423.5Q480-607 480-640t-23.5-56.5Q433-720 400-720t-56.5 23.5Q320-673 320-640t23.5 56.5Q367-560 400-560t56.5-23.5ZM400-640Zm12 400Zm174-166 94 55 94-55-94-54-94 54Zm124 208 90-52v-110l-90 53v109Zm-150-52 90 53v-109l-90-53v109Z"/>
                                        </svg>                                      
                                                                               
                                </button>

                            </div>
                            <button class="send-btn" id="sendMessageBtn-${agent.id}" data-agent-id="${agent.id}" title="Send message">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                    <path d="M4 12l1.41 1.41L11 7.83V20h2V7.83l5.59 5.58L20 12l-8-8z"/>
                                </svg>
                            </button>
                            <button class="cancel-btn" id="cancelMessageBtn-${agent.id}" data-agent-id="${agent.id}" title="Stop generating">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                    <rect x="6" y="6" width="12" height="12" rx="2"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                </div>

                <!-- Right panel resizer -->
                <div class="agent-panel-resizer" id="agentPanelResizer-${agent.id}" data-agent-id="${agent.id}">
                    <div class="panel-resizer-handle">
                        <div class="panel-resizer-line"></div>
                    </div>
                    <button class="panel-collapse-btn" id="agentPanelCollapseBtn-${agent.id}" data-agent-id="${agent.id}" title="Collapse settings panel">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2.5">
                            <polyline points="9,6 15,12 9,18"/>
                        </svg>
                    </button>
                </div>

                <!-- Right settings panel -->
                <div class="agent-settings-panel" id="agentSettingsPanel-${agent.id}" data-agent-id="${agent.id}">
                    <!-- Tab content area -->
                    <div class="settings-tab-content" id="settingsTabContent-${agent.id}">
                        <!-- Param tab content -->
                        <div class="tab-pane active" data-tab="param" ${isRemote ? 'style="opacity:0.6;"' : ''}>
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z"/>
                                    </svg>
                                    <span>Model parameters</span>
                                </div>
                                <div class="param-group">
                                    <label class="param-label">
                                        <span>Temperature</span>
                                        <input type="number" class="param-input" value="0.7" min="0" max="2" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Max Tokens</span>
                                        <input type="number" class="param-input" value="2048" min="1" max="8192" step="1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Top P</span>
                                        <input type="number" class="param-input" value="0.9" min="0" max="1" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Frequency Penalty</span>
                                        <input type="number" class="param-input" value="0" min="-2" max="2" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                    <label class="param-label">
                                        <span>Presence Penalty</span>
                                        <input type="number" class="param-input" value="0" min="-2" max="2" step="0.1" data-agent-id="${agent.id}">
                                    </label>
                                </div>
                            </div>
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="#1a73e8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                        <line x1="4" y1="21" x2="4" y2="14"></line>
                                        <line x1="4" y1="10" x2="4" y2="3"></line>
                                        <line x1="12" y1="21" x2="12" y2="12"></line>
                                        <line x1="12" y1="8" x2="12" y2="3"></line>
                                        <line x1="20" y1="21" x2="20" y2="16"></line>
                                        <line x1="20" y1="12" x2="20" y2="3"></line>
                                        <line x1="1" y1="14" x2="7" y2="14"></line>
                                        <line x1="9" y1="8" x2="15" y2="8"></line>
                                        <line x1="17" y1="16" x2="23" y2="16"></line>
                                    </svg>                                    
                                    <span>Advanced settings</span>
                                </div>
                                <div class="param-group">
                                    <label class="param-toggle">
                                        <span>Stream mode</span>
                                        <input type="checkbox" checked data-agent-id="${agent.id}">
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <label class="param-toggle">
                                        <span>Show token usage</span>
                                        <input type="checkbox" data-agent-id="${agent.id}">
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <label class="param-toggle">
                                        <span>Thinking effort</span>
                                        <input type="checkbox" data-agent-id="${agent.id}">
                                        <span class="toggle-slider"></span>
                                    </label>
                                    <label class="param-label thinking-effort-wrapper" style="display:none;">
                                        <span>Effort level</span>
                                        <select class="param-input thinking-effort-select" data-agent-id="${agent.id}">
                                            <option value="minimal">minimal</option>
                                            <option value="low">low</option>
                                            <option value="medium" selected>medium</option>
                                            <option value="high">high</option>
                                            <option value="max">max</option>
                                        </select>
                                        <div class="thinking-effort-doc-link" style="display:none;">
                                            <a class="thinking-effort-doc-anchor" href="#" data-external-url="" target="_blank" rel="noopener noreferrer">View documentation</a>
                                        </div>
                                    </label>
                                </div>
                            </div>
                        </div>

                        <!-- Prompt tab content -->
                        <div class="tab-pane" data-tab="prompt" ${isRemote ? 'style="opacity:0.6;"' : ''}>
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm-5 14H7v-2h7v2zm3-4H7v-2h10v2zm0-4H7V7h10v2z"/>
                                    </svg>
                                    <span>System Prompt</span>
                                </div>
                                <div class="prompt-editor">
                                    <textarea class="prompt-textarea" id="systemPrompt-${agent.id}" data-agent-id="${agent.id}" placeholder="Enter system prompt...">You are a senior developer proficient in multiple programming languages and frameworks.</textarea>
                                    <button class="prompt-save-btn" data-agent-id="${agent.id}">Save</button>
                                </div>
                            </div>
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                                    </svg>
                                    <span>Preset prompts</span>
                                </div>
                                <div class="preset-list">
                                    <div class="preset-item" data-preset="developer" data-agent-id="${agent.id}">
                                        <span class="preset-name">Senior Developer</span>
                                        <button class="preset-use-btn" data-agent-id="${agent.id}">Use</button>
                                    </div>
                                    <div class="preset-item" data-preset="writer" data-agent-id="${agent.id}">
                                        <span class="preset-name">Creative Writing</span>
                                        <button class="preset-use-btn" data-agent-id="${agent.id}">Use</button>
                                    </div>
                                    <div class="preset-item" data-preset="analyst" data-agent-id="${agent.id}">
                                        <span class="preset-name">Data Analysis</span>
                                        <button class="preset-use-btn" data-agent-id="${agent.id}">Use</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- File tab content -->
                        <div class="tab-pane" data-tab="file" ${isRemote ? 'style="opacity:0.6;"' : ''}>
                            <div class="settings-section">
                                <div class="settings-section-title">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                                        <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/>
                                    </svg>
                                    <span>Chat files</span>
                                    <button class="file-upload-btn" title="Upload file" data-agent-id="${agent.id}">
                                        <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                                        </svg>
                                    </button>
                                </div>
                                <div class="file-list" id="chatFileList-${agent.id}" data-agent-id="${agent.id}">
                                    <div class="empty-state">
                                        <svg viewBox="0 0 24 24" width="48" height="48" fill="#ccc">
                                            <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm2 16H8v-2h8v2zm0-4H8v-2h8v2zm-3-5V3.5L18.5 9H13z"/>
                                        </svg>
                                        <p>No files</p>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- Plugin tabs will be added here dynamically -->
                    </div>

                    <!-- Bottom tab buttons -->
                    <div class="settings-tabs" id="settingsTabs-${agent.id}">
                        <button class="settings-tab active" data-tab="param" data-agent-id="${agent.id}" ${isRemote ? 'disabled' : ''}>
                            <span>Param</span>
                        </button>
                        <button class="settings-tab" data-tab="prompt" data-agent-id="${agent.id}" ${isRemote ? 'disabled' : ''}>
                            <span>Prompt</span>
                        </button>
                        <button class="settings-tab" data-tab="file" data-agent-id="${agent.id}" ${isRemote ? 'disabled' : ''}>
                            <span>File</span>
                        </button>
                    </div>
                </div>

            </div>
        `;
    }
};

export default AgentPage;
