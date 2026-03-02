/**
 * Agent Sidebar - sidebar rendering (multi-agent dynamic loading version - refactored architecture)
 * Each Agent has its own expand/collapse section, shown directly under the corresponding agent list item
 */

const AgentSidebar = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },
    /**
     * Render sidebar - returns base structure, filled dynamically by init()
     */
    render() {
        return `
            <div class="sidebar-section agent-list-section">
                <div class="agent-list" id="agentList"></div>
            </div>
        `;
    },

    /**
     * Init - load agents from API and create UI
     */
    async init() {
        console.log('[AgentSidebar] Starting initialization...');

        // 1. Load agent list from API
        const agents = await this.loadAgentsFromAPI();
        console.log('[AgentSidebar] Loaded agents:', agents);

        if (agents.length === 0) {
            console.warn('[AgentSidebar] No available agents');
            this.renderEmptyState();
            return;
        }

        // 2. Render agent list (each agent includes item + section)
        this.renderAgentList(agents);

        // 3. Bind events
        this.bindEvents();

        // 4. Restore previously selected agent, or expand the first agent by default
        if (agents.length > 0) {
            // Check for saved currentAgentId
            const savedAgentId = window.agentState?.currentAgentId;
            const agentToSelect = savedAgentId && agents.find(a => a.id === savedAgentId)
                ? savedAgentId
                : agents[0].id;

            console.log('[AgentSidebar] Selected agent:', agentToSelect, savedAgentId ? '(restored previous selection)' : '(default first)');

            // Ensure agentState has currentAgentId set
            if (window.agentState) {
                window.agentState.setCurrentAgent(agentToSelect);
            }

            this.switchAgent(agentToSelect);
        }

        console.log('[AgentSidebar] Initialization complete');
    },

    /**
     * Load agent list from API
     */
    async loadAgentsFromAPI() {
        try {
            const response = await fetch(this.resolve('/api/agent'));
            const result = await response.json();

            if (result.success && result.data) {
                return result.data.filter(agent => agent.is_active !== false);
            }
            return [];
        } catch (error) {
            console.error('[AgentSidebar] Failed to load agent list:', error);
            return [];
        }
    },

    async fetchAllAgentsForManage() {
        try {
            const response = await fetch(this.resolve('/api/agent'));
            const result = await response.json();

            if (result.success && result.data) {
                return result.data;
            }
            return [];
        } catch (error) {
            console.error('[AgentSidebar] Failed to load agent list:', error);
            return [];
        }
    },

    /**
     * Render agent list (new architecture: each agent item is followed by its section)
     */
    renderAgentList(agents) {
        const agentList = document.getElementById('agentList');
        if (!agentList) return;

        // For each agent create: item + section
        const agentItemsHTML = agents.map(agent => `
            <!-- Agent list item -->
            <div class="agent-item" data-agent-id="${agent.id}">
<svg width="16" height="16" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
  <!-- Head -->
  <rect x="3" y="6" width="18" height="14" rx="2" stroke="currentColor" stroke-width="2"/>
  <!-- Antenna -->
  <line x1="12" y1="6" x2="12" y2="3" stroke="currentColor" stroke-width="2"/>
  <circle cx="12" cy="2" r="1.5" fill="currentColor"/>
  <!-- Eyes -->
  <circle cx="8.5" cy="11.5" r="1.5" fill="currentColor"/>
  <circle cx="15.5" cy="11.5" r="1.5" fill="currentColor"/>
  <!-- Mouth -->
  <path d="M9 15 Q12 18 15 15" stroke="currentColor" stroke-width="2" stroke-linecap="round"/>
</svg>

                <span>${agent.name || 'Unnamed Agent'}</span>
            </div>

            <!-- Agent-specific expandable section (initially hidden) -->
            <div class="agent-section-container" data-agent-id="${agent.id}" style="display: none;">
                ${this.createAgentSectionHTML(agent)}
            </div>
        `).join('');

        // Add management buttons
        const managementButtons = `
            <div class="agent-item agent-management" data-page="model-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                </svg>
                <span>LLM Setting</span>
            </div>
            <div class="agent-item agent-management" data-page="role-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/>
                </svg>
                <span>Role Setting</span>
            </div>
            <div class="agent-item agent-management" data-page="agent-management">
                <svg viewBox="0 0 24 24" width="16" height="16" fill="#1a73e8">
                    <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/>
                </svg>
                <span>Agent Management</span>
            </div>
        `;

        agentList.innerHTML = agentItemsHTML + managementButtons;
        console.log('[AgentSidebar] Agent list rendered (new architecture: item + section)');
    },

    /**
     * Create a single Agent section HTML
     */
    createAgentSectionHTML(agent) {
        return `
            <div class="agent-user-section" data-agent-id="${agent.id}">
                <!-- Large icon buttons -->
                <div class="agent-action-buttons">
                    <button class="agent-action-btn" data-action="new-chat" data-agent-id="${agent.id}">
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
                    <button class="agent-action-btn" data-action="settings" data-agent-id="${agent.id}">
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
                <div class="conversation-section">
                    <!-- Chat List / Tag List switch -->
                    <div class="sns-sidebar-tabs">
                        <button class="sidebar-tab active" data-tab="chatList" data-agent-id="${agent.id}">Chat List</button>
                        <button class="sidebar-tab" data-tab="tagList" data-agent-id="${agent.id}">Tag List</button>
                    </div>
                    <div class="tab-content active" data-content="chatList" data-agent-id="${agent.id}">
                        <div class="sns-search-box">
                            <div class="sns-search-wrapper">
                                <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                                </svg>
                                <input type="text" class="sns-search-input" id="agentChatSearchInput-${agent.id}" placeholder="Keyword+Enter,Blank+Enter to reset" data-agent-id="${agent.id}" />
                                <button class="sns-search-clear" id="agentChatSearchClear-${agent.id}">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                        <!-- Chat list -->
                        <div class="chat-list-container" id="chatListContainer-${agent.id}">
                            <div class="chat-tree" id="chatList-${agent.id}">
                                   <div class="tree-children">
                                    <!-- Chat list will be loaded dynamically here -->
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="tab-content" data-content="tagList" data-agent-id="${agent.id}">
                        <div class="sns-search-box">
                            <div class="sns-search-wrapper">
                                <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                                </svg>
                                <input type="text" class="sns-search-input" id="agentTagSearchInput-${agent.id}" placeholder="Keyword+Enter,Blank+Enter to reset" data-agent-id="${agent.id}" />
                                <button class="sns-search-clear" id="agentTagSearchClear-${agent.id}">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                        <div class="chat-list-container" id="tagListContainer-${agent.id}">
                            <div class="chat-tree">
                                <div class="tree-children">
                                    <div class="empty-state">No tags</div>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Render empty state
     */
    renderEmptyState() {
        const agentList = document.getElementById('agentList');
        if (agentList) {
            agentList.innerHTML = `
                <div class="empty-state" style="padding: 20px; text-align: center; color: #999;">
                    <p>No available agents</p>
                    <p style="font-size: 12px; margin-top: 10px;">Please create an agent in Agent Management first</p>
                </div>
            `;
        }
    },

    /**
     * Bind events
     */
    bindEvents() {
        console.log('[AgentSidebar] Binding events...');

        // 1. Agent list item click - switch agent (expand/collapse)
        document.querySelectorAll('#agentList .agent-item[data-agent-id]').forEach(item => {
            item.addEventListener('click', () => {
                const agentId = parseInt(item.dataset.agentId);
                console.log('[AgentSidebar] Clicked agent:', agentId);
                this.switchAgent(agentId);
            });
        });

        // 2. Action buttons inside each agent section
        document.querySelectorAll('.agent-action-btn[data-action="new-chat"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const agentId = parseInt(btn.dataset.agentId);
                console.log('[AgentSidebar] Clicked New Chat:', agentId);
                this.handleNewChat(agentId);
            });
        });

        document.querySelectorAll('.agent-action-btn[data-action="settings"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const agentId = parseInt(btn.dataset.agentId);
                console.log('[AgentSidebar] Clicked Settings:', agentId);
                this.handleSettings(agentId);
            });
        });

        // 3. Tab switching (chatList/tagList)
        document.querySelectorAll('.sidebar-tab[data-agent-id]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.stopPropagation();
                const agentId = tab.dataset.agentId;
                const tabType = tab.dataset.tab;

                const sameSectionTabs = document.querySelectorAll(`.sidebar-tab[data-agent-id="${agentId}"]`);
                sameSectionTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                const contents = document.querySelectorAll(`.tab-content[data-agent-id="${agentId}"]`);
                contents.forEach(c => c.classList.remove('active'));
                const activeContent = document.querySelector(`.tab-content[data-agent-id="${agentId}"][data-content="${tabType}"]`);
                if (activeContent) {
                    activeContent.classList.add('active');
                }

                console.log('[AgentSidebar] Switched tab:', tabType, 'for agent:', agentId);

                if (window.multiAgentHandlers) {
                    const aId = parseInt(agentId);
                    if (tabType === 'tagList' && typeof window.multiAgentHandlers.loadTagListForAgent === 'function') {
                        window.multiAgentHandlers.loadTagListForAgent(aId);
                    }
                    if (tabType === 'chatList' && typeof window.multiAgentHandlers.loadChatListForAgent === 'function') {
                        window.multiAgentHandlers.loadChatListForAgent(aId);
                    }
                }
            });
        });

        document.querySelectorAll('.sns-search-input[id^="agentChatSearchInput-"], .sns-search-input[id^="agentTagSearchInput-"]').forEach(input => {
            input.addEventListener('keypress', (e) => {
                if (e.key !== 'Enter') return;
                const agentId = parseInt(input.dataset.agentId);
                const query = input.value.trim();
                if (!window.multiAgentHandlers) return;

                if (input.id.startsWith('agentChatSearchInput-') && typeof window.multiAgentHandlers.loadChatListForAgent === 'function') {
                    window.multiAgentHandlers.loadChatListForAgent(agentId, query);
                }
                if (input.id.startsWith('agentTagSearchInput-') && typeof window.multiAgentHandlers.loadTagListForAgent === 'function') {
                    window.multiAgentHandlers.loadTagListForAgent(agentId, query);
                }
            });
        });

        document.querySelectorAll('.sns-search-input[id^="agentChatSearchInput-"], .sns-search-input[id^="agentTagSearchInput-"]').forEach(input => {
            const clearId = input.id.includes('agentChatSearchInput-')
                ? input.id.replace('agentChatSearchInput-', 'agentChatSearchClear-')
                : input.id.replace('agentTagSearchInput-', 'agentTagSearchClear-');
            const clearBtn = document.getElementById(clearId);
            if (clearBtn) {
                input.addEventListener('input', () => {
                    clearBtn.classList.toggle('visible', input.value.length > 0);
                });
                clearBtn.addEventListener('click', (e) => {
                    e.stopPropagation();
                    input.value = '';
                    clearBtn.classList.remove('visible');
                    input.dispatchEvent(new Event('input'));
                });
            }
        });

        // 5. Management buttons (model management, role management, agent management)
        document.querySelectorAll('.agent-management[data-page]').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                console.log('[AgentSidebar] Clicked management button:', page);
                this.navigateToManagementPage(page);
            });
        });

        console.log('[AgentSidebar] Event binding complete');
    },

    /**
     * Switch agent (new architecture: expand/collapse the corresponding section-container)
     */
    switchAgent(agentId) {
        console.log('[AgentSidebar] Switching to agent:', agentId);

        // 0. Update agentState
        if (window.agentState) {
            window.agentState.setCurrentAgent(agentId);
            console.log('[AgentSidebar] Updated agentState.currentAgentId to:', agentId);
        }

        // 1. Collapse all agent-section-containers
        document.querySelectorAll('.agent-section-container').forEach(container => {
            container.style.display = 'none';
        });

        // 2. Expand selected agent's section-container
        const targetContainer = document.querySelector(`.agent-section-container[data-agent-id="${agentId}"]`);
        if (targetContainer) {
            targetContainer.style.display = 'block';
            console.log('[AgentSidebar] Expanded agent section container:', agentId);
        }

        // 3. Hide all agent pages
        document.querySelectorAll('.agent-page-layout').forEach(page => {
            page.style.display = 'none';
        });

        // 4. Show selected agent page
        const targetPage = document.getElementById(`page-agent-${agentId}`);
        if (targetPage) {
            targetPage.style.display = 'flex'; // Use flex instead of block to preserve layout
            console.log('[AgentSidebar] Agent page shown:', agentId);
        }

        // 5. Update agent list active state
        document.querySelectorAll('#agentList .agent-item[data-agent-id]').forEach(item => {
            item.classList.remove('active');
        });
        const activeItem = document.querySelector(`#agentList .agent-item[data-agent-id="${agentId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }

        // 6. Load chat list directly (avoid relying on the event system)
        // Add a small delay to ensure DOM has finished rendering
        setTimeout(() => {
            if (window.multiAgentHandlers && typeof window.multiAgentHandlers.loadChatListForAgent === 'function') {
                console.log('[AgentSidebar] Loading chat list for agent:', agentId);
                window.multiAgentHandlers.loadChatListForAgent(agentId);
            } else {
                console.error('[AgentSidebar] multiAgentHandlers.loadChatListForAgent is not available');
            }
        }, 100);  // 100ms delay to ensure DOM is ready

        // 7. Dispatch global event (for other modules)
        window.dispatchEvent(new CustomEvent('agent-switched', {
            detail: { agentId }
        }));

        console.log('[AgentSidebar] Agent switch complete');
    },

    /**
     * Handle New Chat
     */
    handleNewChat(agentId) {
        console.log('[AgentSidebar] Handling New Chat for agent:', agentId);

        // Dispatch global event
        window.dispatchEvent(new CustomEvent('agent-new-chat', {
            detail: { agentId }
        }));
    },

    /**
     * Handle Settings
     */
    async handleSettings(agentId) {
        console.log('[AgentSidebar] Handling Settings for agent:', agentId);

        try {
            // Load agent details
            const response = await fetch(this.resolve(`/api/agent/${agentId}`));
            const result = await response.json();

            if (result.success && result.data) {
                // Open settings dialog
                if (typeof AgentSettingsDialog !== 'undefined') {
                    AgentSettingsDialog.show(result.data);
                } else {
                    console.error('[AgentSidebar] AgentSettingsDialog is not defined');
                }
            } else {
                console.error('[AgentSidebar] Failed to load agent details:', result);
            }
        } catch (error) {
            console.error('[AgentSidebar] Failed to load agent details:', error);
        }
    },

    /**
     * Navigate to management page
     */
    async navigateToManagementPage(page) {
        try {
            console.log('[AgentSidebar] Navigating to management page:', page);

            if (page === 'agent-management') {
                await this.showAgentManageDialog();
                return;
            }

            // Import management pages dynamically
            const module = await import('./index.js');
            const { ModelManagementPage, RoleManagementPage } = module.default;

            console.log('[AgentSidebar] Management modules imported');

            if (page === 'model-management' && ModelManagementPage) {
                await ModelManagementPage.init();
                console.log('[AgentSidebar] LLM Setting page  has been initialized.');
            } else if (page === 'role-management' && RoleManagementPage) {
                await RoleManagementPage.init();
                console.log('[AgentSidebar] The role setting page has been initialized.');
            } else {
                console.error('[AgentSidebar] Page not found:', page);
            }
        } catch (error) {
            console.error('[AgentSidebar] Failed to navigate to the management page:', error);
        }
    },

    async showAgentManageDialog() {
        const agents = await this.fetchAllAgentsForManage();

        if (window.electronAPI && window.electronAPI.hideBrowserView) {
            window.electronAPI.hideBrowserView();
        }

        const dialogHTML = `
            <div class="web-manage-dialog-overlay" id="agentManageDialog">
                <div class="web-manage-dialog">
                    <div class="web-manage-dialog-header">
                        <h3>Manage Agents</h3>
                        <div style="display:flex; gap:8px; align-items:center;">
                            <button class="web-action-btn" id="agentAddBtn" style="height:32px; padding:0 12px;">
                                <span>Add</span>
                            </button>
                            <button class="web-manage-dialog-close" data-action="close-agent-manage">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M18 6L6 18M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="web-manage-dialog-content">
                        <div class="web-manage-list" id="agentManageList">
                            ${this.renderAgentManageItems(agents)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        const oldDialog = document.getElementById('agentManageDialog');
        if (oldDialog) oldDialog.remove();

        document.body.insertAdjacentHTML('beforeend', dialogHTML);

        this.initAgentDragAndDrop();
        this.bindAgentManageDialogEvents();
    },

    renderAgentManageItems(agents) {
        const visibleAgents = (agents || []).filter(a => a && a.is_active !== false);

        if (!visibleAgents || visibleAgents.length === 0) {
            return '<div class="web-empty-message">No agents available</div>';
        }

        return visibleAgents.map((agent, index) => {
            const name = (agent.name || 'Unnamed Agent');
            const description = (agent.description || '');
            const activeText = agent.is_active === false ? 'Inactive' : 'Active';

            return `
                <div class="web-manage-item" draggable="true" data-id="${agent.id}" data-position="${agent.position ?? index}">
                    <div class="web-manage-item-drag">
                        <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2">
                            <path d="M9 5h2M9 12h2M9 19h2M15 5h2M15 12h2M15 19h2"/>
                        </svg>
                    </div>
                    <div class="web-manage-item-icon">
                        <div class="web-icon-fallback">${String(name).charAt(0).toUpperCase()}</div>
                    </div>
                    <div class="web-manage-item-info">
                        <div class="web-manage-item-name">${name}</div>
                        <div class="web-manage-item-url">${description ? description : activeText}</div>
                    </div>
                    <div class="web-manage-item-actions">
                        <div style="font-size:12px; color:#666; padding:0 6px;">${activeText}</div>
                        <button type="button" class="web-manage-item-btn web-manage-item-btn-delete" data-action="delete-agent" data-id="${agent.id}" title="Delete">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                                <path d="M3 6h18"/>
                                <path d="M8 6V4h8v2"/>
                                <path d="M19 6l-1 14H6L5 6"/>
                                <path d="M10 11v6"/>
                                <path d="M14 11v6"/>
                            </svg>
                        </button>
                    </div>
                </div>
            `;
        }).join('');
    },

    bindAgentManageDialogEvents() {
        const dialog = document.getElementById('agentManageDialog');
        if (!dialog) return;

        dialog.addEventListener('click', async (e) => {
            const button = e.target.closest('button');
            if (!button) return;

            const action = button.dataset.action;
            if (action === 'close-agent-manage') {
                await this.closeAgentManageDialog();
                return;
            }

            if (button.id === 'agentAddBtn') {
                await this.showAddAgentDialog();
                return;
            }

            if (action === 'delete-agent') {
                e.preventDefault();
                e.stopPropagation();

                const agentId = parseInt(button.dataset.id);
                if (!agentId) return;

                const agents = await this.fetchAllAgentsForManage();
                const agent = (agents || []).find(a => parseInt(a.id) === agentId);
                const agentName = agent && agent.name ? `"${agent.name}"` : 'this agent';

                const confirmed = await (async () => {
                    try {
                        if (window.Toast && typeof window.Toast.confirm === 'function') {
                            return await window.Toast.confirm(`Delete ${agentName}?`, {
                                title: 'Delete Agent',
                                confirmText: 'Delete',
                                cancelText: 'Cancel',
                                type: 'warning'
                            });
                        }

                        if (window.Modal && typeof window.Modal.show === 'function') {
                            return await new Promise((resolve) => {
                                window.Modal.show({
                                    title: 'Delete Agent',
                                    content: `<p>Delete ${agentName}?</p>`,
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
                    } catch (err) {
                        console.error('Failed to show delete agent confirmation dialog:', err);
                    }
                    return false;
                })();

                if (!confirmed) return;

                try {
                    const resp = await fetch(this.resolve(`/api/agent/${agentId}`), {
                        method: 'DELETE'
                    });

                    if (!resp.ok) {
                        const text = await resp.text();
                        throw new Error(text || `Delete failed: ${resp.status}`);
                    }

                    const payload = await resp.json().catch(() => ({}));
                    if (payload && payload.success === false) {
                        throw new Error(payload.detail || payload.error || 'Delete failed');
                    }

                    if (window.Toast && typeof window.Toast.success === 'function') {
                        window.Toast.success('Agent deleted successfully');
                    }

                    const nextAgents = (await this.fetchAllAgentsForManage()).filter(a => a && a.is_active !== false);
                    const list = document.getElementById('agentManageList');
                    if (list) {
                        list.innerHTML = this.renderAgentManageItems(nextAgents);
                    }
                } catch (err) {
                    console.error('[AgentSidebar] Failed to delete agent:', err);
                    if (window.Toast && typeof window.Toast.error === 'function') {
                        window.Toast.error('Delete failed: ' + (err.message || String(err)));
                    }
                }
            }
        });

        dialog.addEventListener('click', async (e) => {
            if (e.target === dialog) {
                await this.closeAgentManageDialog();
            }
        });
    },

    async closeAgentManageDialog() {
        const dialog = document.getElementById('agentManageDialog');
        if (dialog) dialog.remove();

        if (window.electronAPI && window.electronAPI.showBrowserView) {
            window.electronAPI.showBrowserView();
        }

        await this.reload();
    },

    initAgentDragAndDrop() {
        const list = document.getElementById('agentManageList');
        if (!list) return;

        let draggedElement = null;

        list.addEventListener('dragstart', (e) => {
            if (e.target.classList.contains('web-manage-item')) {
                draggedElement = e.target;
                e.target.classList.add('dragging');
            }
        });

        list.addEventListener('dragend', (e) => {
            if (e.target.classList.contains('web-manage-item')) {
                e.target.classList.remove('dragging');
                draggedElement = null;
            }
        });

        list.addEventListener('dragover', (e) => {
            e.preventDefault();
            const afterElement = this.getDragAfterElement(list, e.clientY);
            const dragging = document.querySelector('.dragging');
            if (!dragging) return;

            if (afterElement == null) {
                list.appendChild(dragging);
            } else {
                list.insertBefore(dragging, afterElement);
            }
        });

        list.addEventListener('drop', async (e) => {
            e.preventDefault();
            await this.updateAgentPositions();
        });
    },

    getDragAfterElement(container, y) {
        const draggableElements = [...container.querySelectorAll('.web-manage-item:not(.dragging)')];

        return draggableElements.reduce((closest, child) => {
            const box = child.getBoundingClientRect();
            const offset = y - box.top - box.height / 2;

            if (offset < 0 && offset > closest.offset) {
                return { offset: offset, element: child };
            }
            return closest;
        }, { offset: Number.NEGATIVE_INFINITY }).element;
    },

    async updateAgentPositions() {
        const list = document.getElementById('agentManageList');
        if (!list) return;

        const items = [...list.querySelectorAll('.web-manage-item')];
        const updates = items.map((item, index) => ({
            id: parseInt(item.dataset.id),
            position: index
        }));

        try {
            const response = await fetch(this.resolve('/api/agent/reorder'), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to update agent positions');
            }
        } catch (error) {
            console.error('[AgentSidebar] Failed to update agent positions:', error);
            alert('Failed to update agent positions. Please try again.');
        }
    },

    async showAddAgentDialog() {
        // Use AgentSettingsDialog for comprehensive agent creation
        if (typeof AgentSettingsDialog !== 'undefined') {
            console.log('[AgentSidebar] Using AgentSettingsDialog for agent creation');
            await AgentSettingsDialog.show(null); // null indicates creating a new agent
        } else {
            console.error('[AgentSidebar] AgentSettingsDialog not available, falling back to simple dialog');
            // Fallback to simple dialog if AgentSettingsDialog is not available
            await this.showSimpleAddAgentDialog();
        }
    },

    async showSimpleAddAgentDialog() {
        const dialogHTML = `
            <div class="web-manage-dialog-overlay" id="agentAddDialog">
                <div class="web-edit-dialog">
                    <div class="web-edit-dialog-header">
                        <h3>Add Agent</h3>
                        <button class="web-edit-dialog-close" data-action="close-agent-add">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                <path d="M18 6L6 18M6 6l12 12"/>
                            </svg>
                        </button>
                    </div>
                    <div class="web-edit-dialog-content">
                        <div class="web-edit-form">
                            <div class="web-edit-form-group">
                                <label>Name *</label>
                                <input type="text" id="agentAddName" placeholder="e.g., Research Agent" required>
                            </div>
                            <div class="web-edit-form-group">
                                <label>Description</label>
                                <textarea id="agentAddDescription" rows="3"></textarea>
                            </div>
                            <div class="web-edit-form-group">
                                <label>Active</label>
                                <input type="checkbox" id="agentAddActive" checked>
                            </div>
                        </div>
                    </div>
                    <div class="web-edit-dialog-footer">
                        <button class="web-edit-dialog-btn web-edit-dialog-btn-cancel" data-action="cancel-agent-add">Cancel</button>
                        <button class="web-edit-dialog-btn web-edit-dialog-btn-save" data-action="save-agent-add">Add</button>
                    </div>
                </div>
            </div>
        `;

        const oldDialog = document.getElementById('agentAddDialog');
        if (oldDialog) oldDialog.remove();
        document.body.insertAdjacentHTML('beforeend', dialogHTML);

        const dialog = document.getElementById('agentAddDialog');
        if (!dialog) return;

        dialog.addEventListener('click', async (e) => {
            const button = e.target.closest('button');
            if (!button) return;
            const action = button.dataset.action;

            if (action === 'close-agent-add' || action === 'cancel-agent-add') {
                this.closeAddAgentDialog();
                return;
            }

            if (action === 'save-agent-add') {
                await this.saveAddAgent();
            }
        });
    },

    closeAddAgentDialog() {
        const dialog = document.getElementById('agentAddDialog');
        if (dialog) dialog.remove();
    },

    async saveAddAgent() {
        const nameEl = document.getElementById('agentAddName');
        const descEl = document.getElementById('agentAddDescription');
        const activeEl = document.getElementById('agentAddActive');

        const name = nameEl ? nameEl.value.trim() : '';
        const description = descEl ? descEl.value.trim() : '';
        const is_active = activeEl ? !!activeEl.checked : true;

        if (!name) {
            alert('Name is required');
            if (nameEl) nameEl.focus();
            return;
        }

        try {
            const response = await fetch(this.resolve('/api/agent'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ name, description, is_active })
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to create agent');
            }

            this.closeAddAgentDialog();

            const agents = (await this.fetchAllAgentsForManage()).filter(a => a && a.is_active !== false);
            const list = document.getElementById('agentManageList');
            if (list) {
                list.innerHTML = this.renderAgentManageItems(agents);
            }
        } catch (error) {
            console.error('[AgentSidebar] Failed to create agent:', error);
            alert('Failed to create agent. Please try again.');
        }
    },

    /**
     * Reload agent list (keep new architecture)
     * Used to refresh the sidebar after agent updates
     */
    async reload() {
        console.log('[AgentSidebar] Reloading...');

        // 1. Reload agent list from API
        const agents = await this.loadAgentsFromAPI();
        console.log('[AgentSidebar] Reloaded agents:', agents);

        if (agents.length === 0) {
            console.warn('[AgentSidebar] No available agents');
            this.renderEmptyState();
            return;
        }

        // 2. Save currently selected agent ID (prefer the one stored in agentState)
        const currentAgentId = window.agentState?.currentAgentId ||
            (() => {
                const currentExpandedContainer = document.querySelector('.agent-section-container[style*="display: block"]');
                return currentExpandedContainer ? parseInt(currentExpandedContainer.dataset.agentId) : null;
            })();

        // 3. Re-render agent list
        this.renderAgentList(agents);

        // 4. Re-bind events
        this.bindEvents();

        // 5. Restore previously expanded agent; if missing, expand the first
        if (currentAgentId && agents.find(a => a.id === currentAgentId)) {
            console.log('[AgentSidebar] Restoring previously selected agent:', currentAgentId);
            this.switchAgent(currentAgentId);
        } else if (agents.length > 0) {
            console.log('[AgentSidebar] Selecting the first agent');
            this.switchAgent(agents[0].id);
        }

        console.log('[AgentSidebar] Reload complete');
    }
};

// Export to global (for other modules)
if (typeof window !== 'undefined') {
    window.AgentSidebar = AgentSidebar;
}

export default AgentSidebar;
