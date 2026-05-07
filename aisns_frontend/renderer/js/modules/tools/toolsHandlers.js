/**
 * Tools Handlers - event handling and content rendering
 */

import ToolsEditDialog from './ToolsEditDialog.js';

const toolsHandlers = {
    currentCategory: 'mcp',
    apiBaseUrl: '',
    skillsApiBaseUrl: '',
    editDialog: null,

    // Pagination state
    currentOffset: 0,
    pageSize: 50, // Default value; will be read from config
    hasMore: true,
    currentData: [],

    init() {
        const normalizeHttpBaseUrl = (raw) => {
            const v = String(raw || '').trim();
            if (!v) return '';
            const withScheme = /^https?:\/\//i.test(v) ? v : `http://${v}`;
            return withScheme.endsWith('/') ? withScheme.slice(0, -1) : withScheme;
        };

        const base = normalizeHttpBaseUrl(
            (window.appConfig && window.appConfig.agent_server)
            || (window.api && window.api.baseUrl)
            || ''
        );

        this.apiBaseUrl = base ? `${base}/api/tools` : '/api/tools';
        this.skillsApiBaseUrl = base ? `${base}/api/skills` : '/api/skills';

        // Ensure global toolsEditDialog instance exists
        if (!window.toolsEditDialog) {
            window.toolsEditDialog = new ToolsEditDialog();
        }
        this.editDialog = window.toolsEditDialog;

        // Load config
        this.loadConfig();

        this.bindEvents();
        // Initial load for the first category
        this.loadCategoryContent(this.currentCategory);

        try {
            window.addEventListener('app-config-updated', () => {
                try {
                    const normalizeHttpBaseUrl = (raw) => {
                        const v = String(raw || '').trim();
                        if (!v) return '';
                        const withScheme = /^https?:\/\//i.test(v) ? v : `http://${v}`;
                        return withScheme.endsWith('/') ? withScheme.slice(0, -1) : withScheme;
                    };
                    const base = normalizeHttpBaseUrl(
                        (window.appConfig && window.appConfig.agent_server)
                        || (window.api && window.api.baseUrl)
                        || ''
                    );
                    this.apiBaseUrl = base ? `${base}/api/tools` : '/api/tools';
                    this.skillsApiBaseUrl = base ? `${base}/api/skills` : '/api/skills';
                } catch (e) {}
            });
        } catch (e) {}
    },

    showConfirmDialog({ title, message, confirmText = 'Confirm', cancelText = 'Cancel' }) {
        return new Promise((resolve) => {
            const dialogId = 'confirmDialog_' + Math.random().toString(16).slice(2);
            const html = `
                <div class="modal-overlay" id="${dialogId}">
                    <div class="modal-dialog" style="max-width: 520px;">
                        <div class="modal-header">
                            <h2>${title || 'Confirm action'}</h2>
                            <button class="modal-close skill-modal__close" data-confirm-close="1">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                            </button>
                        </div>
                        <div class="modal-body" style="color: var(--text-primary); font-size: 14px; line-height: 1.7;">
                            ${message || ''}
                        </div>
                        <div class="modal-footer">
                            <button type="button" class="btn btn-secondary" data-confirm-cancel="1">${cancelText}</button>
                            <button type="button" class="btn btn-primary" data-confirm-ok="1">${confirmText}</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', html);
            const el = document.getElementById(dialogId);
            if (!el) {
                resolve(false);
                return;
            }

            const cleanup = (val) => {
                try { el.remove(); } catch (e) {}
                resolve(val);
            };

            el.addEventListener('click', (e) => {
                const t = e.target;
                if (!t) return;
                if (t.id === dialogId) return cleanup(false);
                if (t.closest('[data-confirm-close]')) return cleanup(false);
                if (t.closest('[data-confirm-cancel]')) return cleanup(false);
                if (t.closest('[data-confirm-ok]')) return cleanup(true);
            });
        });
    },

    showChoiceDialog({ title, message, choices = [], cancelText = 'Cancel' }) {
        return new Promise((resolve) => {
            const dialogId = 'choiceDialog_' + Math.random().toString(16).slice(2);
            const safeChoices = Array.isArray(choices) ? choices.slice(0, 4) : [];
            const buttonsHtml = safeChoices
                .map((c, idx) => {
                    const label = String(c?.label ?? 'Option');
                    const value = String(c?.value ?? idx);
                    return `<button type="button" class="btn btn-secondary" data-choice-value="${value}">${label}</button>`;
                })
                .join('');

            const html = `
                <div class="modal-overlay" id="${dialogId}">
                    <div class="modal-dialog" style="max-width: 520px;">
                        <div class="modal-header">
                            <h2>${title || 'Select an option'}</h2>
                            <button class="modal-close skill-modal__close" data-choice-close="1">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                            </button>
                        </div>
                        <div class="modal-body" style="color: var(--text-primary); font-size: 14px; line-height: 1.7;">
                            ${message || ''}
                        </div>
                        <div class="modal-footer" style="display:flex; gap: 8px; justify-content:flex-end;">
                            <button type="button" class="btn btn-secondary" data-choice-cancel="1">${cancelText}</button>
                            ${buttonsHtml}
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', html);
            const el = document.getElementById(dialogId);
            if (!el) {
                resolve(null);
                return;
            }

            const cleanup = (val) => {
                try { el.remove(); } catch (e) {}
                resolve(val);
            };

            el.addEventListener('click', (e) => {
                const t = e.target;
                if (!t) return;
                if (t.id === dialogId) return cleanup(null);
                if (t.closest('[data-choice-close]')) return cleanup(null);
                if (t.closest('[data-choice-cancel]')) return cleanup(null);

                const btn = t.closest('[data-choice-value]');
                if (btn) return cleanup(btn.getAttribute('data-choice-value'));
            });
        });
    },

    showImportPluginDialog({ title = 'Import Plugin', message = '', confirmText = 'Confirm', cancelText = 'Cancel' } = {}) {
        return new Promise((resolve) => {
            const dialogId = 'importPluginDialog_' + Math.random().toString(16).slice(2);

            const html = `
                <div class="modal-overlay" id="${dialogId}">
                    <div class="modal-dialog" style="max-width: 520px;">
                        <div class="modal-header">
                            <h2>${title}</h2>
                            <button class="modal-close skill-modal__close" data-import-close="1">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                            </button>
                        </div>
                        <div class="modal-body" style="color: var(--text-primary); font-size: 14px; line-height: 1.7;">
                            <div>${message || ''}</div>
                            <div style="margin-top: 12px; display: grid; gap: 10px;">
                                <label style="display:flex; align-items:center; gap: 10px; cursor: pointer;">
                                    <input type="radio" name="importPluginTarget" value="agent" checked />
                                    <span>Use in Agent</span>
                                </label>
                                <label style="display:flex; align-items:center; gap: 10px; cursor: pointer;">
                                    <input type="radio" name="importPluginTarget" value="sns" />
                                    <span>Use in SNS</span>
                                </label>
                            </div>
                        </div>
                        <div class="modal-footer" style="display:flex; gap: 8px; justify-content:flex-end;">
                            <button type="button" class="btn btn-secondary" data-import-cancel="1">${cancelText}</button>
                            <button type="button" class="btn btn-primary" data-import-confirm="1">${confirmText}</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', html);
            const el = document.getElementById(dialogId);
            if (!el) {
                resolve(null);
                return;
            }

            const cleanup = (val) => {
                try { el.remove(); } catch (e) {}
                resolve(val);
            };

            el.addEventListener('click', (e) => {
                const t = e.target;
                if (!t) return;
                if (t.id === dialogId) return cleanup(null);
                if (t.closest('[data-import-close]')) return cleanup(null);
                if (t.closest('[data-import-cancel]')) return cleanup(null);
                if (t.closest('[data-import-confirm]')) {
                    const checked = el.querySelector('input[name="importPluginTarget"]:checked');
                    const val = checked ? String(checked.value || '') : '';
                    return cleanup(val || null);
                }
            });
        });
    },

    async selectZipFile({ accept = '.zip' } = {}) {
        return new Promise((resolve) => {
            const input = document.createElement('input');
            input.type = 'file';
            input.accept = accept;
            input.style.display = 'none';
            document.body.appendChild(input);

            input.addEventListener('change', () => {
                const file = input.files && input.files[0] ? input.files[0] : null;
                try { input.remove(); } catch (e) {}
                resolve(file);
            }, { once: true });

            input.click();
        });
    },

    async importRendererPluginZip({ usedInSns }) {
        const file = await this.selectZipFile({ accept: '.zip' });
        if (!file) return;

        const fd = new FormData();
        fd.append('file', file);

        const url = `${this.apiBaseUrl}/plugins/import?used_in_sns=${usedInSns ? 'true' : 'false'}`;
        const response = await fetch(url, {
            method: 'POST',
            body: fd
        });
        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || `Import failed: ${response.status}`);
        }
        return await response.json();
    },

    showMcpJsonImportDialog() {
        return new Promise((resolve) => {
            const dialogId = 'mcpJsonImportDialog';
            try {
                document.getElementById(dialogId)?.remove();
            } catch (e) {
            }

            const html = `
                <div class="modal-overlay" id="${dialogId}">
                    <div class="modal-dialog test-result-dialog" style="max-width: 900px; max-height: 90vh; overflow: auto;">
                        <div class="modal-header">
                            <h2>Import MCP JSON</h2>
                            <button class="modal-close skill-modal__close" data-mcpjson-close="1">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                                    <line x1="18" y1="6" x2="6" y2="18"/>
                                    <line x1="6" y1="6" x2="18" y2="18"/>
                                </svg>
                            </button>
                        </div>
                        <div class="modal-body">
                            <textarea id="mcpJsonImportEditor" spellcheck="false" style="width: 100%; min-height: 55vh; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 12px; line-height: 1.4; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px;" placeholder='{"mcpServers":{"mcpadvisor":{"command":"npx","args":["-y","@xiaohui-wang/mcpadvisor"]}}}'></textarea>
                            <div style="margin-top: 8px; color: var(--text-secondary); font-size: 12px; line-height: 1.6;">
                                Paste a JSON object that contains <code>mcpServers</code> or paste the <code>mcpServers</code> object directly.
                            </div>
                        </div>
                        <div class="modal-footer" style="display:flex; justify-content:flex-end; gap: 8px; padding: 12px 16px;">
                            <button type="button" class="btn btn-secondary" data-mcpjson-cancel="1">Cancel</button>
                            <button type="button" class="btn btn-primary" data-mcpjson-import="1">Import</button>
                        </div>
                    </div>
                </div>
            `;

            document.body.insertAdjacentHTML('beforeend', html);
            const el = document.getElementById(dialogId);
            const editor = document.getElementById('mcpJsonImportEditor');
            if (!el || !editor) {
                try { el?.remove(); } catch (e) {}
                resolve(null);
                return;
            }

            const cleanup = (val) => {
                try { el.remove(); } catch (e) {}
                resolve(val);
            };

            el.addEventListener('click', (e) => {
                const t = e.target;
                if (!t) return;
                if (t.id === dialogId) return cleanup(null);
                if (t.closest('[data-mcpjson-close]')) return cleanup(null);
                if (t.closest('[data-mcpjson-cancel]')) return cleanup(null);
                if (t.closest('[data-mcpjson-import]')) return cleanup(String(editor.value || ''));
            });
        });
    },

    async importDocSkillZip() {
        const file = await this.selectZipFile({ accept: '.zip' });
        if (!file) return;

        const fd = new FormData();
        fd.append('file', file);

        const response = await fetch(`${this.skillsApiBaseUrl}/import`, {
            method: 'POST',
            body: fd
        });
        if (!response.ok) {
            const text = await response.text();
            throw new Error(text || `Import failed: ${response.status}`);
        }
        return await response.json();
    },

    async loadConfig() {
        try {
            // Fetch system config from API
            const url = window.resolveAgentServerUrl ? window.resolveAgentServerUrl('/api/system/config') : '/api/system/config';
            const response = await fetch(url);
            if (response.ok) {
                const config = await response.json();
                if (config.tools && config.tools.page_size) {
                    this.pageSize = config.tools.page_size;
                }
            }
        } catch (error) {
            console.log('Failed to load config, using default page size:', this.pageSize);
        }
    },

    showDocSkillRunDialog(skillKey) {
        const html = `
            <div class="modal-overlay" id="docSkillRunDialog">
                <div class="modal-dialog test-result-dialog" style="max-width: 760px; max-height: 85vh; overflow: auto;">
                    <div class="modal-header">
                        <h2>Run Skill - ${skillKey}</h2>
                        <button class="modal-close skill-modal__close" onclick="document.getElementById('docSkillRunDialog').remove()">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                    <div class="modal-body">
                        <div style="margin-bottom: 10px; color: var(--text-secondary); font-size: 13px;">
                            Enter parameters (JSON) and they will be sent as the request body to /api/skills/${skillKey}/run.
                        </div>
                        <textarea id="docSkillRunParamsEditor" style="width: 100%; min-height: 240px; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 12px; line-height: 1.4; padding: 12px; border: 1px solid var(--border-color); border-radius: 10px;"></textarea>
                    </div>
                    <div class="modal-footer" style="display:flex; justify-content:flex-end; gap: 8px; padding: 12px 16px;">
                        <button type="button" class="btn btn-primary" id="docSkillRunBtn">Run</button>
                        <button type="button" class="btn btn-secondary" onclick="document.getElementById('docSkillRunDialog').remove()">Cancel</button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', html);

        const editor = document.getElementById('docSkillRunParamsEditor');
        if (editor) {
            editor.value = "{}";
        }

        const runBtn = document.getElementById('docSkillRunBtn');
        if (runBtn) {
            runBtn.addEventListener('click', async () => {
                const editor = document.getElementById('docSkillRunParamsEditor');
                const raw = editor ? editor.value : '';

                let params = {};
                try {
                    params = raw && raw.trim() ? JSON.parse(raw) : {};
                } catch (e) {
                    this.showMessage('Failed to parse params JSON: ' + e.message, 'error');
                    return;
                }
                if (params === null || typeof params !== 'object' || Array.isArray(params)) {
                    this.showMessage('Params must be a JSON object (e.g. {})', 'error');
                    return;
                }

                runBtn.disabled = true;
                const originalText = runBtn.textContent;
                runBtn.textContent = 'Running...';

                try {
                    const response = await fetch(`${this.skillsApiBaseUrl}/${encodeURIComponent(skillKey)}/run`, {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify(params)
                    });
                    if (!response.ok) {
                        const text = await response.text();
                        throw new Error(text || `HTTP error! status: ${response.status}`);
                    }
                    const result = await response.json();
                    document.getElementById('docSkillRunDialog')?.remove();
                    this.showTestResult(result.result || result);
                } catch (e) {
                    console.error('Run skill error:', e);
                    this.showMessage('Run failed: ' + e.message, 'error');
                } finally {
                    runBtn.disabled = false;
                    runBtn.textContent = originalText;
                }
            });
        }
    },

    bindEvents() {
        // Category item click
        document.querySelectorAll('.tools-category-item').forEach(item => {
            item.addEventListener('click', () => {
                const category = item.getAttribute('data-category');
                this.onCategoryClick(category);

                // Set active state
                document.querySelectorAll('.tools-category-item').forEach(i => {
                    i.classList.remove('active');
                });
                item.classList.add('active');
            });
        });

        // More button click
        const moreBtn = document.querySelector('.plugin-more-btn');
        if (moreBtn) {
            moreBtn.addEventListener('click', () => this.loadMoreTools());
        }

        // Add button click (button must exist in the page)
        const addBtn = document.querySelector('.tools-add-btn');
        if (addBtn) {
            addBtn.addEventListener('click', () => this.showAddDialog(this.currentCategory));
        }
    },

    onCategoryClick(category) {
        console.log('Category clicked:', category);
        this.currentCategory = category;

        // Reset pagination state
        this.currentOffset = 0;
        this.hasMore = true;
        this.currentData = [];

        this.loadCategoryContent(category);

        // Emit custom event
        if (typeof window.eventBus !== 'undefined') {
            window.eventBus.emit('tools:category:changed', { category });
        }
    },

    async loadCategoryContent(category, offset = 0, limit = null) {
        const pluginGrid = document.getElementById('pluginGrid');
        if (!pluginGrid) {
            console.error('Plugin grid element not found');
            return;
        }

        // Update title
        const titleElement = document.querySelector('.plugin-list-title');
        if (titleElement) {
            titleElement.textContent = `${this.getCategoryDisplayName(category)} List`;
        }

        // Show loading state (first load only)
        if (offset === 0) {
            pluginGrid.innerHTML = '<div class="loading-spinner">Loading...</div>';
        }

        try {
            let data = [];
            let endpoint = '';

            // Pick API endpoint by category
            switch(category) {
                case 'tools-plugin':
                    endpoint = '/plugins';
                    break;
                case 'mcp':
                    endpoint = '/mcp';
                    break;
                case 'function':
                    endpoint = '/functions';
                    break;
                case 'computer-use':
                    endpoint = '/skills';
                    break;
                case 'skill':
                    endpoint = '/list';
                    break;
                default:
                    pluginGrid.innerHTML = '<div class="empty-state">Unknown category</div>';
                    return;
            }

            // Load data from API (only fetch on first load)
            if (offset === 0 || this.currentData.length === 0) {
                const baseUrl = category === 'skill' ? this.skillsApiBaseUrl : this.apiBaseUrl;
                const response = await fetch(`${baseUrl}${endpoint}`);
                if (!response.ok) {
                    throw new Error(`HTTP error! status: ${response.status}`);
                }
                const payload = await response.json();
                let items = category === 'skill' ? (payload?.data || []) : payload;

                if (category === 'tools-plugin' && Array.isArray(items)) {
                    items = items.filter((p) => String(p?.plugin_type || '').toLowerCase() === 'renderer');
                }

                this.currentData = items;
            }

            console.log(`Loaded ${this.currentData.length} total items for ${category}`);

            // Use page size
            const pageSize = limit || this.pageSize;

            // Compute display range
            const endIndex = offset + pageSize;
            const displayData = this.currentData.slice(0, endIndex);

            // Determine whether there is more data
            this.hasMore = endIndex < this.currentData.length;
            this.currentOffset = offset;

            // Render content
            if (displayData && displayData.length > 0) {
                pluginGrid.innerHTML = this.renderToolCards(displayData, category);
                this.bindToolCardEvents();
            } else {
                pluginGrid.innerHTML = this.renderEmptyState(category);
            }

            // Update More button state
            this.updateMoreButton();

        } catch (error) {
            console.error('Error loading tools:', error);
            pluginGrid.innerHTML = `
                <div class="error-state">
                    <h3>Load failed</h3>
                    <p>${error.message}</p>
                    <button onclick="toolsHandlers.loadCategoryContent('${category}')" class="retry-btn">
                        Retry
                    </button>
                </div>
            `;
        }
    },

    loadMoreTools() {
        if (!this.hasMore) return;

        const newOffset = this.currentOffset + this.pageSize;
        this.loadCategoryContent(this.currentCategory, newOffset);
    },

    updateMoreButton() {
        const moreBtn = document.querySelector('.plugin-more-btn');
        if (moreBtn) {
            if (this.hasMore) {
                moreBtn.style.display = 'block';
                moreBtn.disabled = false;
            } else {
                moreBtn.style.display = 'none';
            }
        }
    },

    renderToolCards(tools, category) {
        return tools.map(tool => this.renderToolCard(tool, category)).join('');
    },

    renderToolCard(tool, category) {
        const id = tool.plugin_id || tool.mcp_id || tool.function_id || tool.skill_id || tool.skill_key || '';
        const name = tool.name || 'Unnamed Tool';
        const description = tool.description || 'No description available';
        const type = this.getCategoryDisplayName(category);

        const runner = (tool && typeof tool.runner === 'object' && tool.runner) ? tool.runner : {};
        const runnerKind = runner && typeof runner.kind === 'string' ? runner.kind : '';
        const runnerTarget = runner && typeof runner.target === 'string' ? runner.target : '';
        const runnerLabel = [runnerKind, runnerTarget].filter(Boolean).join(' ');

        const mcpType = String(tool?.mcp_type || '').toLowerCase();
        const mcpTypeLabel = mcpType === 'streamable-http'
            ? 'Streamable HTTP'
            : (mcpType === 'sse' ? 'SSE' : (mcpType || 'stdio'));

        const pluginTypeLabel = tool?.used_in_sns ? 'SNS' : 'Agent';

        const statusLabel = category === 'tools-plugin'
            ? pluginTypeLabel
            : (category === 'mcp'
                ? mcpTypeLabel
                : (category === 'skill'
                    ? (runnerKind || 'Unknown')
                    : (tool.confirm_needed ? 'Confirm Required' : 'Active')));

        const statusClass = category === 'skill'
            ? (tool.eligible ? 'author-official--active' : 'author-official--confirm')
            : (tool.confirm_needed ? 'author-official--confirm' : 'author-official--active');

        const categoryIconMap = {
            'tools-plugin': 'extension',
            'mcp': 'dns',
            'function': 'functions',
            'computer-use': 'desktop_windows',
            'skill': 'school'
        };
        const iconName = categoryIconMap[category] || 'construction';

        const instructionLabel = category === 'skill'
            ? (runnerLabel || name)
            : (tool.instruction || name);
        const filePath = tool.file_path || tool.location || '';

        const actionsHTML = category === 'skill'
            ? `
                <div class="plugin-actions tools-card-ref__actions">
                    <button class="plugin-test-btn tools-card-ref__btn tools-card-ref__btn--test" data-id="${id}" data-category="${category}" title="Run">
                        <span class="material-icons-round">play_arrow</span>
                        Run
                    </button>
                    <button class="plugin-edit-btn tools-card-ref__btn tools-card-ref__btn--edit" data-id="${id}" data-category="${category}" title="Edit SKILL.md">
                        <span class="material-icons-round">edit</span>
                        Edit
                    </button>
                    <button class="plugin-delete-btn tools-card-ref__btn tools-card-ref__btn--delete" data-id="${id}" data-category="${category}" title="Delete (workspace skills/ only)">
                        <span class="material-icons-round">delete</span>
                        Delete
                    </button>
                </div>
            `
            : `
                <div class="plugin-actions tools-card-ref__actions">
                    <button class="plugin-test-btn tools-card-ref__btn tools-card-ref__btn--test" data-id="${id}" data-category="${category}" title="Test run">
                        <span class="material-icons-round">play_arrow</span>
                        Test
                    </button>
                    <button class="plugin-edit-btn tools-card-ref__btn tools-card-ref__btn--edit" data-id="${id}" data-category="${category}" title="Edit">
                        <span class="material-icons-round">edit</span>
                        Edit
                    </button>
                    <button class="plugin-delete-btn tools-card-ref__btn tools-card-ref__btn--delete" data-id="${id}" data-category="${category}" title="Delete">
                        <span class="material-icons-round">delete</span>
                        Delete
                    </button>
                </div>
            `;

        return `
            <div class="plugin-card tool-card tools-card-ref" data-id="${id}" data-category="${category}">
                <div class="tools-card-ref__top">
                    <div class="tools-card-ref__top-left">
                        <div class="tools-card-ref__icon">
                            <span class="material-icons-round">${iconName}</span>
                        </div>
                        <div class="tools-card-ref__meta">
                            <div class="tools-card-ref__title-row">
                                <h3 class="plugin-name">${name}</h3>
                                <span class="plugin-badge-connector">${type}</span>
                            </div>
                            <div class="plugin-author">
                                <span class="author-label">Type</span>
                                <span class="author-official ${statusClass}">${statusLabel}</span>
                            </div>
                        </div>
                    </div>
                </div>
                <p class="plugin-desc">${description}</p>
                ${(instructionLabel || filePath) ? `
                    <div class="tools-card-ref__codeblock">
                        <div class="tools-card-ref__codehead">
                            <span class="material-icons-round">terminal</span>
                            <span class="tools-card-ref__mono">${instructionLabel}</span>
                        </div>
                        ${filePath ? `
                            <div class="plugin-file-path tools-card-ref__codebody">
                                <span class="material-icons-round">folder</span>
                                <span class="tools-card-ref__mono">${filePath}</span>
                            </div>
                        ` : ''}
                    </div>
                ` : ''}
                ${actionsHTML}
            </div>
        `;
    },

    renderEmptyState(category) {
        const typeName = this.getCategoryDisplayName(category);
        return `
            <div class="empty-state">
                <svg viewBox="0 0 24 24" width="64" height="64" fill="none" stroke="currentColor" stroke-width="1.5">
                    <rect x="3" y="3" width="18" height="18" rx="2"/>
                    <line x1="9" y1="9" x2="15" y2="15"/>
                    <line x1="15" y1="9" x2="9" y2="15"/>
                </svg>
                <h3>No ${typeName} yet</h3>
                <p>Click the button below to create the first ${typeName}</p>
                <button onclick="toolsHandlers.showAddDialog('${category}')" class="add-tool-btn">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="currentColor" stroke-width="2">
                        <line x1="12" y1="5" x2="12" y2="19"/>
                        <line x1="5" y1="12" x2="19" y2="12"/>
                    </svg>
                    Add ${typeName}
                </button>
            </div>
        `;
    },

    bindToolCardEvents() {
        // Test button
        document.querySelectorAll('.plugin-test-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.getAttribute('data-id');
                const category = btn.getAttribute('data-category');
                await this.testTool(id, category, btn);
            });
        });

        // Edit button
        document.querySelectorAll('.plugin-edit-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.getAttribute('data-id');
                const category = btn.getAttribute('data-category');
                await this.editTool(id, category);
            });
        });

        // Delete button
        document.querySelectorAll('.plugin-delete-btn').forEach(btn => {
            btn.addEventListener('click', async (e) => {
                e.stopPropagation();
                const id = btn.getAttribute('data-id');
                const category = btn.getAttribute('data-category');
                await this.deleteTool(id, category);
            });
        });
    },

    async testTool(id, category, btn) {
        if (category === 'skill') {
            this.showDocSkillRunDialog(id);
            return;
        }

        if (category === 'tools-plugin') {
            // Find the plugin data
            const tool = (this.currentData || []).find(t => String(t.plugin_id || t.id) === String(id));
            if (tool) {
                if (tool.used_in_sns) {
                    this.showMessage('Please go to the SNS page to test this plugin.', 'info');
                } else {
                    this.showMessage('Please go to the Agent chat page to test this plugin.', 'info');
                }
            } else {
                this.showMessage('Plugin not found.', 'error');
            }
            return;
        }

        // Show running state
        const originalText = btn.innerHTML;
        btn.innerHTML = '<span class="spinner-small"></span> Running...';
        btn.disabled = true;

        try {
            let endpoint = '';
            switch(category) {
                case 'mcp':
                    endpoint = `/mcp/${id}/execute`;
                    break;
                case 'function':
                    endpoint = `/functions/${id}/execute`;
                    break;
                case 'computer-use':
                    endpoint = `/skills/${id}/execute`;
                    break;
                case 'skill':
                    endpoint = `/${id}/run`;
                    break;
            }

            const baseUrl = category === 'skill' ? this.skillsApiBaseUrl : this.apiBaseUrl;
            const response = await fetch(`${baseUrl}${endpoint}`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({})
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const result = await response.json();

            // Show result
            this.showTestResult(result.result || result);

        } catch (error) {
            console.error('Test error:', error);
            this.showMessage('Test failed: ' + error.message, 'error');
        } finally {
            btn.innerHTML = originalText;
            btn.disabled = false;
        }
    },

    showTestResult(result) {
        // Create result dialog
        const resultHTML = `
            <div class="modal-overlay" id="testResultDialog">
                <div class="modal-dialog test-result-dialog">
                    <div class="modal-header">
                        <h2>Test result</h2>
                        <button class="modal-close" onclick="document.getElementById('testResultDialog').remove()">
                            <svg viewBox="0 0 24 24" width="24" height="24" fill="none" stroke="currentColor" stroke-width="2">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                    <div class="modal-body">
                        <pre class="test-result-pre">${JSON.stringify(result, null, 2)}</pre>
                    </div>
                    <div class="modal-footer">
                        <button type="button" class="btn btn-primary" onclick="document.getElementById('testResultDialog').remove()">
                            Close
                        </button>
                    </div>
                </div>
            </div>
        `;

        document.body.insertAdjacentHTML('beforeend', resultHTML);
    },

    async editTool(id, category) {
        try {
            if (category === 'skill') {
                const response = await fetch(`${this.skillsApiBaseUrl}/read?skill_key=${encodeURIComponent(id)}`);
                if (!response.ok) {
                    throw new Error('Failed to fetch SKILL.md');
                }
                const payload = await response.json();
                const markdown = payload?.data?.markdown || '';
                this.showDocSkillMarkdown(id, markdown);
                return;
            }

            // Fetch tool data
            let endpoint = '';
            switch(category) {
                case 'tools-plugin':
                    endpoint = `/plugins/${id}`;
                    break;
                case 'mcp':
                    endpoint = `/mcp/${id}`;
                    break;
                case 'function':
                    endpoint = `/functions/${id}`;
                    break;
                case 'computer-use':
                    endpoint = `/skills/${id}`;
                    break;
            }

            const response = await fetch(`${this.apiBaseUrl}${endpoint}`);
            if (!response.ok) {
                throw new Error('Failed to fetch tool data');
            }

            const tool = await response.json();

            // Show edit dialog
            this.editDialog.show(category, tool, () => {
                // Reload after successful save
                this.loadCategoryContent(category);
            });

        } catch (error) {
            console.error('Edit error:', error);
            this.showMessage('Failed to load tool data: ' + error.message, 'error');
        }
    },

    async deleteTool(id, category) {
        if (category === 'skill') {
            const ok = await this.showConfirmDialog({
                title: 'Delete Skill',
                message: 'Want to delete this Skill? (Only skills in the workspace "skills/" directory can be deleted.)',
                confirmText: 'Delete',
                cancelText: 'Cancel'
            });
            if (!ok) return;

            try {
                const response = await fetch(`${this.skillsApiBaseUrl}/delete?skill_key=${encodeURIComponent(id)}`, {
                    method: 'DELETE'
                });
                if (!response.ok) {
                    const text = await response.text();
                    throw new Error(text || `Delete failed: ${response.status}`);
                }
                this.showMessage('Deleted successfully', 'success');
                await this.loadCategoryContent(category);
            } catch (error) {
                console.error('Delete skill error:', error);
                this.showMessage('Delete failed: ' + error.message, 'error');
            }
            return;
        }

        const tool = (this.currentData || []).find((t) => {
            const tid = t.plugin_id || t.mcp_id || t.function_id || t.skill_id || '';
            return String(tid) === String(id);
        });
        const toolName = tool && tool.name ? `"${tool.name}"` : 'this tool';
        const ok = await this.showConfirmDialog({
            title: 'Delete Tool',
            message: `Delete ${toolName}?`,
            confirmText: 'Delete',
            cancelText: 'Cancel'
        });
        if (!ok) return;

        try {
            let endpoint = '';
            switch(category) {
                case 'tools-plugin':
                    endpoint = `/plugins/${id}`;
                    break;
                case 'mcp':
                    endpoint = `/mcp/${id}`;
                    break;
                case 'function':
                    endpoint = `/functions/${id}`;
                    break;
                case 'computer-use':
                    endpoint = `/skills/${id}`;
                    break;
            }

            const response = await fetch(`${this.apiBaseUrl}${endpoint}`, {
                method: 'DELETE'
            });

            if (!response.ok) {
                throw new Error(`Delete failed: ${response.status}`);
            }

            this.showMessage('Deleted successfully', 'success');
            await this.loadCategoryContent(category);
        } catch (error) {
            console.error('Delete error:', error);
            this.showMessage('Delete failed: ' + error.message, 'error');
        }
    },

    showAddDialog(category) {
        if (this._addDialogInFlight) return;
        this._addDialogInFlight = true;
        if (category === 'tools-plugin') {
            (async () => {
                try {
                    const choice = await this.showImportPluginDialog({
                        title: 'Import Plugin',
                        message: 'Choose where this renderer plugin will be used.'
                    });
                    if (!choice) return;

                    const usedInSns = choice === 'sns';
                    await this.importRendererPluginZip({ usedInSns });
                    this.showMessage('Imported successfully', 'success');
                    await this.loadCategoryContent(category);
                } catch (e) {
                    console.error('Import plugin zip error:', e);
                    this.showMessage('Import failed: ' + e.message, 'error');
                } finally {
                    this._addDialogInFlight = false;
                }
            })();
            return;
        }

        if (category === 'mcp') {
            (async () => {
                try {
                    const choice = await this.showChoiceDialog({
                        title: 'Add MCP',
                        message: 'Create an MCP entry manually or import from a common MCP JSON config.',
                        choices: [
                            { label: 'Create Manually', value: 'manual' },
                            { label: 'Import from MCP JSON', value: 'import-json' },
                        ],
                        cancelText: 'Cancel'
                    });
                    if (!choice) return;

                    if (choice === 'manual') {
                        this.editDialog.show(category, null, () => {
                            this.loadCategoryContent(category);
                        });
                        return;
                    }

                    const raw = await this.showMcpJsonImportDialog();
                    if (!raw) return;

                    let parsed;
                    try {
                        parsed = JSON.parse(raw);
                    } catch (e) {
                        throw new Error('Invalid JSON');
                    }

                    const servers = (parsed && typeof parsed === 'object' && parsed.mcpServers && typeof parsed.mcpServers === 'object')
                        ? parsed.mcpServers
                        : parsed;

                    if (!servers || typeof servers !== 'object') {
                        throw new Error('Missing mcpServers');
                    }

                    const entries = Object.entries(servers);
                    if (!entries.length) {
                        throw new Error('No MCP servers found');
                    }

                    const results = [];
                    for (const [key, cfg] of entries) {
                        try {
                            const c = (cfg && typeof cfg === 'object') ? cfg : {};

                            let mcpType = 'stdio';
                            let filePath = '';
                            let parameter = null;

                            if (typeof c.url === 'string' && c.url.trim()) {
                                filePath = c.url.trim();
                                const urlLower = filePath.toLowerCase();
                                mcpType = urlLower.includes('/sse') || urlLower.endsWith('/sse') ? 'sse' : 'streamable-http';
                            } else if (typeof c.command === 'string' && c.command.trim()) {
                                filePath = c.command.trim();
                                const args = Array.isArray(c.args) ? c.args : [];
                                const env = (c.env && typeof c.env === 'object') ? c.env : undefined;
                                parameter = JSON.stringify({ args, env }, null, 0);
                                mcpType = 'stdio';
                            } else {
                                throw new Error('Unsupported MCP server config (expected command+args or url)');
                            }

                            const payload = {
                                name: String(c.name || key || 'MCP'),
                                instruction: String(c.instruction || ''),
                                description: String(c.description || `Imported from MCP JSON: ${key}`),
                                mcp_type: mcpType,
                                file_path: filePath,
                                parameter: parameter,
                                requirement: String(c.requirement || ''),
                            };

                            const resp = await fetch(`${this.apiBaseUrl}/mcp`, {
                                method: 'POST',
                                headers: { 'Content-Type': 'application/json' },
                                body: JSON.stringify(payload)
                            });
                            if (!resp.ok) {
                                const text = await resp.text();
                                throw new Error(text || `HTTP ${resp.status}`);
                            }
                            const created = await resp.json();
                            results.push({ key, status: 'success', mcp_id: created?.mcp_id || null, name: created?.name || payload.name });
                        } catch (e) {
                            results.push({ key, status: 'error', error: String(e?.message || e) });
                        }
                    }

                    this.showTestResult({ imported: results });
                    await this.loadCategoryContent(category);
                } catch (e) {
                    console.error('Import MCP JSON error:', e);
                    this.showMessage('Import failed: ' + e.message, 'error');
                } finally {
                    this._addDialogInFlight = false;
                }
            })();
            return;
        }

        if (category === 'skill') {
            (async () => {
                try {
                    await this.importDocSkillZip();
                    this.showMessage('Imported successfully', 'success');
                    await this.loadCategoryContent(category);
                } catch (e) {
                    console.error('Import skill zip error:', e);
                    this.showMessage('Import failed: ' + e.message, 'error');
                } finally {
                    this._addDialogInFlight = false;
                }
            })();
            return;
        }

        try {
            this.editDialog.show(category, null, () => {
                this.loadCategoryContent(category);
            });
        } finally {
            this._addDialogInFlight = false;
        }
    },

    getCategoryDisplayName(category) {
        const names = {
            'tools-plugin': 'Plugin',
            'mcp': 'MCP',
            'function': 'Function',
            'computer-use': 'Computer Use',
            'skill': 'Skill'
        };
        return names[category] || category;
    },

    showDocSkillMarkdown(skillKey, markdown) {
        try {
            document.getElementById('docSkillMarkdownDialog')?.remove();
        } catch (e) {
        }

        const html = `
            <div class="modal-overlay" id="docSkillMarkdownDialog">
                <div class="modal-dialog test-result-dialog" style="max-width: 900px; max-height: 90vh; overflow: auto;">
                    <div class="modal-header">
                        <h2>SKILL.md - ${skillKey}</h2>
                        <button class="modal-close skill-modal__close" onclick="document.getElementById('docSkillMarkdownDialog').remove()">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round">
                                <line x1="18" y1="6" x2="6" y2="18"/>
                                <line x1="6" y1="6" x2="18" y2="18"/>
                            </svg>
                        </button>
                    </div>
                    <div class="modal-body">
                        <textarea id="docSkillMarkdownEditor" spellcheck="false" style="width: 100%; min-height: 60vh; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace; font-size: 12px; line-height: 1.4; padding: 12px; border: 1px solid #e5e7eb; border-radius: 8px;"></textarea>
                    </div>
                    <div class="modal-footer" style="display:flex; justify-content:flex-end; gap: 8px; padding: 12px 16px;">
                        <button type="button" class="btn btn-primary" id="docSkillSaveBtn">Save</button>
                        <button type="button" class="btn btn-secondary" onclick="document.getElementById('docSkillMarkdownDialog').remove()">Cancel</button>
                    </div>
                </div>
            </div>
        `;
        document.body.insertAdjacentHTML('beforeend', html);

        const editor = document.getElementById('docSkillMarkdownEditor');
        if (editor) {
            editor.value = markdown || '';
        }

        const saveBtn = document.getElementById('docSkillSaveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                const editor = document.getElementById('docSkillMarkdownEditor');
                const newMd = editor ? editor.value : '';
                saveBtn.disabled = true;
                const originalText = saveBtn.textContent;
                saveBtn.textContent = 'Saving...';
                try {
                    const resp = await fetch(`${this.skillsApiBaseUrl}/edit`, {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ skill_key: skillKey, markdown: newMd })
                    });
                    if (!resp.ok) {
                        const text = await resp.text();
                        throw new Error(text || `Save failed: ${resp.status}`);
                    }
                    this.showMessage('Saved successfully', 'success');
                    await this.loadCategoryContent('skill');
                    document.getElementById('docSkillMarkdownDialog')?.remove();
                } catch (e) {
                    console.error('Save skill error:', e);
                    this.showMessage('Save failed: ' + e.message, 'error');
                } finally {
                    saveBtn.disabled = false;
                    saveBtn.textContent = originalText;
                }
            });
        }
    },

    getToolIcon(category) {
        const icons = {
            'tools-plugin': '<svg viewBox="0 0 24 24" width="32" height="32" fill="#10a37f"><path d="M22.7 19l-9.1-9.1c.9-2.3.4-5-1.5-6.9-2-2-5-2.4-7.4-1.3L9 6 6 9 1.6 4.7C.4 7.1.9 10.1 2.9 12.1c1.9 1.9 4.6 2.4 6.9 1.5l9.1 9.1c.4.4 1 .4 1.4 0l2.3-2.3c.5-.4.5-1.1.1-1.4z"/></svg>',
            'mcp': '<svg viewBox="0 0 24 24" width="32" height="32" fill="#1a73e8"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="8" y1="21" x2="16" y2="21" stroke="currentColor" stroke-width="2"/></svg>',
            'function': '<svg viewBox="0 0 24 24" width="32" height="32" fill="#d97706"><path d="M15.6 5.29c-1.1-.1-2.07.71-2.17 1.81L13.18 10H16v2h-3l-.44 5.07c-.14 1.55-1.28 2.76-2.81 2.93-1.81.2-3.39-1.16-3.59-2.97L6 10H4V8h2.23l.21-2.93c.14-1.55 1.28-2.76 2.81-2.93 1.81-.2 3.39 1.16 3.59 2.97l.16 2.9H16V5.5c0-.83.67-1.5 1.5-1.5s1.5.67 1.5 1.5V8h2.5c.83 0 1.5.67 1.5 1.5S21.83 11 21 11h-2.5v7.5c0 .83-.67 1.5-1.5 1.5s-1.5-.67-1.5-1.5V11h-2.23l-.17 2.09z"/></svg>',
            'computer-use': '<svg viewBox="0 0 24 24" width="32" height="32" fill="#7c3aed"><rect x="2" y="3" width="20" height="14" rx="2"/><line x1="2" y1="20" x2="22" y2="20" stroke="currentColor" stroke-width="2"/></svg>'
        };
        return icons[category] || icons['tools-plugin'];
    },

    showMessage(message, type = 'info') {
        console.log(`[${type}] ${message}`);

        try {
            if (typeof window !== 'undefined' && window.Toast && typeof window.Toast.show === 'function') {
                window.Toast.show(String(message), String(type || 'info'), 3000);
                return;
            }
        } catch (e) {
        }

        const toast = document.createElement('div');
        toast.className = `toast toast-${type}`;
        toast.textContent = message;
        toast.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            padding: 16px 24px;
            background: ${type === 'success' ? '#10b981' : type === 'error' ? '#ef4444' : '#3b82f6'};
            color: white;
            border-radius: 8px;
            box-shadow: 0 4px 12px rgba(0,0,0,0.15);
            z-index: 2000000;
            animation: slideIn 0.3s ease-out;
        `;

        document.body.appendChild(toast);

        setTimeout(() => {
            toast.style.animation = 'slideOut 0.3s ease-out';
            setTimeout(() => toast.remove(), 300);
        }, 3000);
    },

    destroy() {
        this.currentCategory = 'tools-plugin';
    }
};

// Export
if (typeof module !== 'undefined' && module.exports) {
    module.exports = toolsHandlers;
}

if (typeof window !== 'undefined') {
    window.toolsHandlers = toolsHandlers;
}

export default toolsHandlers;
