/**
 * Agent Tools Configuration Dialog
 * Configure tools for an Agent (Plugin, MCP, Function, Skill)
 */

const AgentToolsDialog = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },
    // Store all currently selected tools (across tabs)
    currentSelections: new Set(),

    // DocSkills selections (skill_key)
    docSkillSelections: new Set(),

    /**
     * Open dialog
     */
    async open(agentId) {
        console.log('[AgentToolsDialog] Opening for agent:', agentId);

        // Reset selection state
        this.currentSelections.clear();
        this.docSkillSelections.clear();

        // Remove existing dialog
        const existingDialog = document.getElementById('agentToolsDialog');
        if (existingDialog) {
            existingDialog.remove();
        }

        // Create and insert dialog
        const dialog = this.createDialog(agentId);
        document.body.insertAdjacentHTML('beforeend', dialog);

        // Bind events (bind before data load so the dialog can still be closed on error)
        this.bindEventHandlers(agentId);

        // Load data
        await this.loadData(agentId);
    },

    /**
     * Create dialog HTML
     */
    createDialog(agentId) {
        return `
            <div class="modal-overlay" id="agentToolsDialog">
                <div class="agent-tools-dialog">
                    <div class="dialog-header">
                        <h2>Configure Agent Tools</h2>
                        <button class="dialog-close-btn" id="closeAgentToolsDialog">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                        </button>
                    </div>

                    <div class="dialog-body">
                        <!-- Tool category tabs -->
                        <div class="tools-tabs">
                            <button class="tab-btn active" data-tab="plugin">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M20.5 11H19V7c0-1.1-.9-2-2-2h-4V3.5C13 2.12 11.88 1 10.5 1S8 2.12 8 3.5V5H4c-1.1 0-1.99.9-1.99 2v3.8H3.5c1.49 0 2.7 1.21 2.7 2.7s-1.21 2.7-2.7 2.7H2V20c0 1.1.9 2 2 2h3.8v-1.5c0-1.49 1.21-2.7 2.7-2.7 1.49 0 2.7 1.21 2.7 2.7V22H17c1.1 0 2-.9 2-2v-4h1.5c1.38 0 2.5-1.12 2.5-2.5S21.88 11 20.5 11z"/>
                                </svg>
                                Plugin
                            </button>
                            <button class="tab-btn" data-tab="mcp">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
                                </svg>
                                MCP
                            </button>
                            <button class="tab-btn" data-tab="function">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M9.4 16.6L4.8 12l4.6-4.6L8 6l-6 6 6 6 1.4-1.4zm5.2 0l4.6-4.6-4.6-4.6L16 6l6 6-6 6-1.4-1.4z"/>
                                </svg>
                                Function
                            </button>
                            <button class="tab-btn" data-tab="skill">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M19 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V5c0-1.1-.9-2-2-2zm0 16H5V5h14v14z"/>
                                </svg>
                                Computer Use
                            </button>

                            <button class="tab-btn" data-tab="doc-skill">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M19 2H8c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V4c0-1.1-.9-2-2-2zm-1 18H9V4h9v16z"/>
                                    <path d="M7 6H5c-1.1 0-2 .9-2 2v12c0 1.1.9 2 2 2h2V6z"/>
                                </svg>
                                Doc Skill
                            </button>
                        </div>

                        <!-- Tool list container -->
                        <div class="tools-list-container">
                            <!-- Search box -->
                            <div class="tools-search">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                                </svg>
                                <input type="text" id="toolsSearchInput" placeholder="Search tools...">
                            </div>

                            <!-- Tool list -->
                            <div class="tools-list" id="toolsList">
                                <div class="loading">Loading...</div>
                            </div>
                        </div>

                        <!-- Selected tools summary -->
                        <div class="selected-tools-summary">
                            <span class="summary-text">Selected <strong id="selectedCount">0</strong> tools</span>
                        </div>
                    </div>

                    <div class="dialog-footer">
                        <button class="btn-secondary" id="cancelAgentTools">Cancel</button>
                        <button class="btn-primary" id="saveAgentTools">Save</button>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Load data
     */
    async loadData(agentId) {
        try {
            // Load current config and available tools in parallel
            const [agentToolsResponse, allTools, agentDocSkillsResponse] = await Promise.all([
                agentApi.getAgentTools(agentId),
                this.loadAllTools(),
                fetch(this.resolve(`/api/skills/agent/${agentId}/skills`)).then(r => r.json())
            ]);

            // Extract actual tools array
            const agentTools = agentToolsResponse?.data?.tools || [];

            console.log('[AgentToolsDialog] Loaded agent tools:', agentTools);

            // Initialize currentSelections with configured tools
            this.currentSelections.clear();
            agentTools.forEach(tool => {
                // Extract the correct ID field based on tool_type
                const toolId = tool.plugin_id || tool.mcp_id || tool.function_id || tool.skill_id;
                const key = `${tool.tool_type}:${toolId}`;
                this.currentSelections.add(key);
                console.log('[AgentToolsDialog] Added to selections:', key);
            });

            // Initialize doc skills selections
            this.docSkillSelections.clear();
            const enabledSkillKeys = agentDocSkillsResponse?.data;
            if (Array.isArray(enabledSkillKeys)) {
                enabledSkillKeys.forEach(k => {
                    if (k) this.docSkillSelections.add(String(k));
                });
            }

            console.log('[AgentToolsDialog] Initialized selections:', Array.from(this.currentSelections));

            // Persist data to dialog
            const dialog = document.getElementById('agentToolsDialog');
            if (!dialog) {
                console.error('[AgentToolsDialog] Dialog element not found');
                return;
            }

            dialog.dataset.agentId = agentId;
            dialog.dataset.agentTools = JSON.stringify(agentTools);
            dialog.dataset.allTools = JSON.stringify(allTools);

            dialog.dataset.agentDocSkills = JSON.stringify(Array.from(this.docSkillSelections));

            // Show currently selected plugins
            this.renderTools('plugin', allTools.plugins || []);
        } catch (error) {
            console.error('[AgentToolsDialog] Failed to load data:', error);
            this.showError('Failed to load data');
        }
    },

    /**
     * Load all available tools
     */
    async loadAllTools() {
        try {
            const [plugins, mcps, functions, skills, docSkillsPayload] = await Promise.all([
                fetch(this.resolve('/api/tools/plugins')).then(r => r.json()),
                fetch(this.resolve('/api/tools/mcp')).then(r => r.json()),
                fetch(this.resolve('/api/tools/functions')).then(r => r.json()),
                fetch(this.resolve('/api/tools/skills')).then(r => r.json()),
                fetch(this.resolve('/api/skills/list')).then(r => r.json())
            ]);

            const docSkills = docSkillsPayload?.data || [];

            return {
                plugins: plugins || [],
                mcps: mcps || [],
                functions: functions || [],
                skills: skills || [],
                docSkills: docSkills
            };
        } catch (error) {
            console.error('[AgentToolsDialog] Failed to load all tools:', error);
            return {
                plugins: [],
                mcps: [],
                functions: [],
                skills: [],
                docSkills: []
            };
        }
    },

    /**
     * Render tools list
     */
    renderTools(toolType, tools) {
        const listContainer = document.getElementById('toolsList');

        if (!tools || tools.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">No tools available</div>';
            return;
        }

        console.log(`[AgentToolsDialog] Rendering ${toolType} tools:`, tools);
        console.log('[AgentToolsDialog] Current selections:', Array.from(this.currentSelections));

        // Create tool items
        const toolsHTML = tools.map(tool => {
            const toolId = toolType === 'doc-skill'
                ? (tool.skill_key || tool.skillKey || tool.name)
                : (tool.plugin_id || tool.mcp_id || tool.function_id || tool.skill_id);
            const selectionKey = `${toolType}:${toolId}`;
            const isSelected = toolType === 'doc-skill'
                ? this.docSkillSelections.has(String(toolId))
                : this.currentSelections.has(selectionKey);

            console.log(`[AgentToolsDialog] Tool ${tool.name}: id=${toolId}, key=${selectionKey}, selected=${isSelected}`);

            const icon = this.getToolIcon(toolType);
            const name = tool.name || tool.skill_key || 'Unnamed Tool';
            const description = tool.description || tool.instruction || (tool.eligible === false ? `Missing: ${(tool.missing || []).join(', ')}` : 'No description');

            return `
                <div class="tool-item ${isSelected ? 'selected' : ''}" data-tool-id="${toolId}" data-tool-type="${toolType}">
                    <div class="tool-checkbox">
                        <input type="checkbox" ${isSelected ? 'checked' : ''}
                               data-tool-id="${toolId}" data-tool-type="${toolType}">
                    </div>
                    <div class="tool-icon">${icon}</div>
                    <div class="tool-info">
                        <div class="tool-name">${name}</div>
                        <div class="tool-description">${description}</div>
                    </div>
                </div>
            `;
        }).join('');

        listContainer.innerHTML = toolsHTML;

        // Update counts
        this.updateSelectedCount();
    },

    /**
     * Get tool icon
     */
    getToolIcon(toolType) {
        const icons = {
            plugin: '🔌',
            mcp: '🔗',
            function: '⚡',
            skill: '🖥️',
            'doc-skill': '📄'
        };
        return icons[toolType] || '🔧';
    },

    /**
     * Bind event handlers
     */
    bindEventHandlers(agentId) {
        const dialog = document.getElementById('agentToolsDialog');
        if (!dialog) {
            console.error('[AgentToolsDialog] Dialog element not found for binding events');
            return;
        }

        // Close dialog
        const closeBtn = dialog.querySelector('#closeAgentToolsDialog');
        const cancelBtn = dialog.querySelector('#cancelAgentTools');
        const saveBtn = dialog.querySelector('#saveAgentTools');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.close());
        }

        // Click overlay to close (modal-overlay is the dialog container)
        dialog.addEventListener('click', (e) => {
            if (e.target.id === 'agentToolsDialog') {
                this.close();
            }
        });

        // Tab switch
        dialog.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // Search
        const searchInput = dialog.querySelector('#toolsSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTools(e.target.value);
            });
        }

        // Tool selection
        dialog.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.dataset.toolId) {
                this.toggleToolSelection(e.target);
            }
        });

        // Save config
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveConfiguration(agentId);
            });
        }
    },

    /**
     * Switch tab
     */
    switchTab(tab) {
        const dialog = document.getElementById('agentToolsDialog');
        const allTools = JSON.parse(dialog.dataset.allTools || '{}');

        // Update active state
        dialog.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        // Render tools for current tab
        const toolsMap = {
            plugin: allTools.plugins || [],
            mcp: allTools.mcps || [],
            function: allTools.functions || [],
            skill: allTools.skills || [],
            'doc-skill': allTools.docSkills || []
        };

        this.renderTools(tab, toolsMap[tab]);

        // Clear search
        const searchInput = document.getElementById('toolsSearchInput');
        if (searchInput) {
            searchInput.value = '';
        }
    },

    /**
     * Filter tools
     */
    filterTools(searchText) {
        const listContainer = document.getElementById('toolsList');
        const toolItems = listContainer.querySelectorAll('.tool-item');

        const lowerSearch = searchText.toLowerCase();

        toolItems.forEach(item => {
            const name = item.querySelector('.tool-name').textContent.toLowerCase();
            const description = item.querySelector('.tool-description').textContent.toLowerCase();

            if (name.includes(lowerSearch) || description.includes(lowerSearch)) {
                item.style.display = '';
            } else {
                item.style.display = 'none';
            }
        });
    },

    /**
     * Toggle tool selection state
     */
    toggleToolSelection(checkbox) {
        const toolItem = checkbox.closest('.tool-item');
        const toolId = checkbox.dataset.toolId;
        const toolType = checkbox.dataset.toolType;
        const selectionKey = `${toolType}:${toolId}`;

        if (toolType === 'doc-skill') {
            if (checkbox.checked) {
                this.docSkillSelections.add(String(toolId));
            } else {
                this.docSkillSelections.delete(String(toolId));
            }
        } else {
            // Update currentSelections
            if (checkbox.checked) {
                this.currentSelections.add(selectionKey);
            } else {
                this.currentSelections.delete(selectionKey);
            }
        }

        console.log('[AgentToolsDialog] Selection changed:', selectionKey, checkbox.checked);
        console.log('[AgentToolsDialog] Current selections:', Array.from(this.currentSelections));

        toolItem.classList.toggle('selected', checkbox.checked);
        this.updateSelectedCount();
    },

    /**
     * Update selected count
     */
    updateSelectedCount() {
        const countEl = document.getElementById('selectedCount');
        if (countEl) {
            countEl.textContent = (this.currentSelections.size + this.docSkillSelections.size);
        }
    },

    /**
     * Save configuration
     */
    async saveConfiguration(agentId) {
        try {
            // Build tool config list from currentSelections
            const tools = Array.from(this.currentSelections).map((key, index) => {
                const [tool_type, tool_id] = key.split(':');
                return {
                    tool_type,
                    tool_id,
                    enabled: true,
                    priority: index + 1
                };
            });

            console.log('[AgentToolsDialog] Saving tools:', tools);

            // Save via API
            const result = await agentApi.updateAgentTools(agentId, tools);

            // Save Doc Skills
            await fetch(this.resolve(`/api/skills/agent/${agentId}/skills`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ skill_keys: Array.from(this.docSkillSelections) })
            });

            console.log('[AgentToolsDialog] Save result:', result);

            // Show success message
            this.showSuccess('Tool configuration saved');

            // Close dialog
            setTimeout(() => this.close(), 1000);

        } catch (error) {
            console.error('[AgentToolsDialog] Failed to save configuration:', error);
            this.showError('Save failed: ' + error.message);
        }
    },

    /**
     * Close dialog
     */
    close() {
        const dialog = document.getElementById('agentToolsDialog');
        if (dialog) {
            dialog.remove();
        }
    },

    /**
     * Show success message
     */
    showSuccess(message) {
        // Simple implementation, can be improved later
        try {
            if (typeof window !== 'undefined' && window.Toast && typeof window.Toast.success === 'function') {
                window.Toast.success(message);
                return;
            }
            if (typeof Notification !== 'undefined' && Notification.success) {
                Notification.success(message);
                return;
            }
        } catch (e) {
        }
        alert('✓ ' + message);
    },

    /**
     * Show error message
     */
    showError(message) {
        // Simple implementation, can be improved later
        try {
            if (typeof window !== 'undefined' && window.Toast && typeof window.Toast.error === 'function') {
                window.Toast.error(message);
                return;
            }
            if (typeof Notification !== 'undefined' && Notification.error) {
                Notification.error(message);
                return;
            }
        } catch (e) {
        }
        alert('✗ ' + message);
    }
};

// Export
window.AgentToolsDialog = AgentToolsDialog;
