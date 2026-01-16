/**
 * Agent Tools Configuration Dialog
 * 为Agent配置工具（Plugin, MCP, Function, Skill）
 */

const AgentToolsDialog = {
    // 存储当前所有选中的工具（跨标签页）
    currentSelections: new Set(),

    /**
     * 打开对话框
     */
    async open(agentId) {
        console.log('[AgentToolsDialog] Opening for agent:', agentId);

        // 重置选择状态
        this.currentSelections.clear();

        // 移除已存在的对话框
        const existingDialog = document.getElementById('agentToolsDialog');
        if (existingDialog) {
            existingDialog.remove();
        }

        // 创建并添加对话框
        const dialog = this.createDialog(agentId);
        document.body.insertAdjacentHTML('beforeend', dialog);

        // 绑定事件（在加载数据前绑定，避免错误时无法关闭对话框）
        this.bindEventHandlers(agentId);

        // 加载数据
        await this.loadData(agentId);
    },

    /**
     * 创建对话框HTML
     */
    createDialog(agentId) {
        return `
            <div class="modal-overlay" id="agentToolsDialog">
                <div class="agent-tools-dialog">
                    <div class="dialog-header">
                        <h2>配置Agent工具</h2>
                        <button class="dialog-close-btn" id="closeAgentToolsDialog">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                        </button>
                    </div>

                    <div class="dialog-body">
                        <!-- 工具分类标签页 -->
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
                        </div>

                        <!-- 工具列表容器 -->
                        <div class="tools-list-container">
                            <!-- 搜索框 -->
                            <div class="tools-search">
                                <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                                </svg>
                                <input type="text" id="toolsSearchInput" placeholder="搜索工具...">
                            </div>

                            <!-- 工具列表 -->
                            <div class="tools-list" id="toolsList">
                                <div class="loading">加载中...</div>
                            </div>
                        </div>

                        <!-- 已选工具统计 -->
                        <div class="selected-tools-summary">
                            <span class="summary-text">已选择 <strong id="selectedCount">0</strong> 个工具</span>
                        </div>
                    </div>

                    <div class="dialog-footer">
                        <button class="btn-secondary" id="cancelAgentTools">取消</button>
                        <button class="btn-primary" id="saveAgentTools">保存配置</button>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 加载数据
     */
    async loadData(agentId) {
        try {
            // 并行加载当前配置和可用工具
            const [agentToolsResponse, allTools] = await Promise.all([
                agentApi.getAgentTools(agentId),
                this.loadAllTools()
            ]);

            // 提取实际的工具数组
            const agentTools = agentToolsResponse?.data?.tools || [];

            console.log('[AgentToolsDialog] Loaded agent tools:', agentTools);

            // 初始化currentSelections为已配置的工具
            this.currentSelections.clear();
            agentTools.forEach(tool => {
                // 根据tool_type提取正确的ID字段
                const toolId = tool.plugin_id || tool.mcp_id || tool.function_id || tool.skill_id;
                const key = `${tool.tool_type}:${toolId}`;
                this.currentSelections.add(key);
                console.log('[AgentToolsDialog] Added to selections:', key);
            });

            console.log('[AgentToolsDialog] Initialized selections:', Array.from(this.currentSelections));

            // 保存数据到对话框
            const dialog = document.getElementById('agentToolsDialog');
            if (!dialog) {
                console.error('[AgentToolsDialog] Dialog element not found');
                return;
            }

            dialog.dataset.agentId = agentId;
            dialog.dataset.agentTools = JSON.stringify(agentTools);
            dialog.dataset.allTools = JSON.stringify(allTools);

            // 显示当前选中的插件
            this.renderTools('plugin', allTools.plugins || []);
        } catch (error) {
            console.error('[AgentToolsDialog] Failed to load data:', error);
            this.showError('加载数据失败');
        }
    },

    /**
     * 加载所有可用工具
     */
    async loadAllTools() {
        try {
            const [plugins, mcps, functions, skills] = await Promise.all([
                fetch('http://localhost:8788/api/tools/plugins').then(r => r.json()),
                fetch('http://localhost:8788/api/tools/mcp').then(r => r.json()),
                fetch('http://localhost:8788/api/tools/functions').then(r => r.json()),
                fetch('http://localhost:8788/api/tools/skills').then(r => r.json())
            ]);

            return {
                plugins: plugins || [],
                mcps: mcps || [],
                functions: functions || [],
                skills: skills || []
            };
        } catch (error) {
            console.error('[AgentToolsDialog] Failed to load all tools:', error);
            return {
                plugins: [],
                mcps: [],
                functions: [],
                skills: []
            };
        }
    },

    /**
     * 渲染工具列表
     */
    renderTools(toolType, tools) {
        const listContainer = document.getElementById('toolsList');

        if (!tools || tools.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">暂无可用工具</div>';
            return;
        }

        console.log(`[AgentToolsDialog] Rendering ${toolType} tools:`, tools);
        console.log('[AgentToolsDialog] Current selections:', Array.from(this.currentSelections));

        // 创建工具项
        const toolsHTML = tools.map(tool => {
            const toolId = tool.plugin_id || tool.mcp_id || tool.function_id || tool.skill_id;
            const selectionKey = `${toolType}:${toolId}`;
            const isSelected = this.currentSelections.has(selectionKey);

            console.log(`[AgentToolsDialog] Tool ${tool.name}: id=${toolId}, key=${selectionKey}, selected=${isSelected}`);

            const icon = this.getToolIcon(toolType);
            const name = tool.name || 'Unnamed Tool';
            const description = tool.description || tool.instruction || 'No description';

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

        // 更新统计
        this.updateSelectedCount();
    },

    /**
     * 获取工具图标
     */
    getToolIcon(toolType) {
        const icons = {
            plugin: '🔌',
            mcp: '🔗',
            function: '⚡',
            skill: '🖥️'
        };
        return icons[toolType] || '🔧';
    },

    /**
     * 绑定事件处理器
     */
    bindEventHandlers(agentId) {
        const dialog = document.getElementById('agentToolsDialog');
        if (!dialog) {
            console.error('[AgentToolsDialog] Dialog element not found for binding events');
            return;
        }

        // 关闭对话框
        const closeBtn = dialog.querySelector('#closeAgentToolsDialog');
        const cancelBtn = dialog.querySelector('#cancelAgentTools');
        const saveBtn = dialog.querySelector('#saveAgentTools');

        if (closeBtn) {
            closeBtn.addEventListener('click', () => this.close());
        }

        if (cancelBtn) {
            cancelBtn.addEventListener('click', () => this.close());
        }

        // 点击遮罩关闭（modal-overlay是dialog的父元素）
        dialog.addEventListener('click', (e) => {
            if (e.target.id === 'agentToolsDialog') {
                this.close();
            }
        });

        // 标签页切换
        dialog.querySelectorAll('.tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const tab = e.currentTarget.dataset.tab;
                this.switchTab(tab);
            });
        });

        // 搜索
        const searchInput = dialog.querySelector('#toolsSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterTools(e.target.value);
            });
        }

        // 工具选择
        dialog.addEventListener('change', (e) => {
            if (e.target.type === 'checkbox' && e.target.dataset.toolId) {
                this.toggleToolSelection(e.target);
            }
        });

        // 保存配置
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveConfiguration(agentId);
            });
        }
    },

    /**
     * 切换标签页
     */
    switchTab(tab) {
        const dialog = document.getElementById('agentToolsDialog');
        const allTools = JSON.parse(dialog.dataset.allTools || '{}');

        // 更新激活状态
        dialog.querySelectorAll('.tab-btn').forEach(btn => {
            btn.classList.toggle('active', btn.dataset.tab === tab);
        });

        // 渲染对应工具列表
        const toolsMap = {
            plugin: allTools.plugins || [],
            mcp: allTools.mcps || [],
            function: allTools.functions || [],
            skill: allTools.skills || []
        };

        this.renderTools(tab, toolsMap[tab]);

        // 清空搜索
        const searchInput = document.getElementById('toolsSearchInput');
        if (searchInput) {
            searchInput.value = '';
        }
    },

    /**
     * 过滤工具
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
     * 切换工具选择状态
     */
    toggleToolSelection(checkbox) {
        const toolItem = checkbox.closest('.tool-item');
        const toolId = checkbox.dataset.toolId;
        const toolType = checkbox.dataset.toolType;
        const selectionKey = `${toolType}:${toolId}`;

        // 更新currentSelections
        if (checkbox.checked) {
            this.currentSelections.add(selectionKey);
        } else {
            this.currentSelections.delete(selectionKey);
        }

        console.log('[AgentToolsDialog] Selection changed:', selectionKey, checkbox.checked);
        console.log('[AgentToolsDialog] Current selections:', Array.from(this.currentSelections));

        toolItem.classList.toggle('selected', checkbox.checked);
        this.updateSelectedCount();
    },

    /**
     * 更新选中数量
     */
    updateSelectedCount() {
        const countEl = document.getElementById('selectedCount');
        if (countEl) {
            countEl.textContent = this.currentSelections.size;
        }
    },

    /**
     * 保存配置
     */
    async saveConfiguration(agentId) {
        try {
            // 从currentSelections构建工具配置列表
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

            // 调用API保存
            const result = await agentApi.updateAgentTools(agentId, tools);

            console.log('[AgentToolsDialog] Save result:', result);

            // 显示成功消息
            this.showSuccess('工具配置已保存');

            // 关闭对话框
            setTimeout(() => this.close(), 1000);

        } catch (error) {
            console.error('[AgentToolsDialog] Failed to save configuration:', error);
            this.showError('保存失败：' + error.message);
        }
    },

    /**
     * 关闭对话框
     */
    close() {
        const dialog = document.getElementById('agentToolsDialog');
        if (dialog) {
            dialog.remove();
        }
    },

    /**
     * 显示成功消息
     */
    showSuccess(message) {
        // 简单实现，可以后续优化
        alert('✓ ' + message);
    },

    /**
     * 显示错误消息
     */
    showError(message) {
        // 简单实现，可以后续优化
        alert('✗ ' + message);
    }
};

// 导出
window.AgentToolsDialog = AgentToolsDialog;
