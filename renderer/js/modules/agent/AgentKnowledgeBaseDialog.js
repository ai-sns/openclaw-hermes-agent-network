const AgentKnowledgeBaseDialog = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },
    currentSelections: new Set(),

    async open(agentId) {
        this.currentSelections.clear();

        const existingDialog = document.getElementById('agentKnowledgeBaseDialog');
        if (existingDialog) {
            existingDialog.remove();
        }

        const dialog = this.createDialog(agentId);
        document.body.insertAdjacentHTML('beforeend', dialog);

        this.bindEventHandlers(agentId);
        await this.loadData(agentId);
    },

    createDialog(agentId) {
        return `
            <div class="modal-overlay" id="agentKnowledgeBaseDialog">
                <div class="agent-kb-dialog">
                    <div class="dialog-header">
                        <h2>Configure Knowledge Base</h2>
                        <button class="dialog-close-btn" id="closeAgentKbDialog">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                                <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                            </svg>
                        </button>
                    </div>

                    <div class="dialog-body">
                        <div class="kb-search">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                            </svg>
                            <input type="text" id="kbSearchInput" placeholder="Search knowledge bases...">
                        </div>

                        <div class="kb-list" id="kbList">
                            <div class="loading">Loading...</div>
                        </div>

                        <div class="selected-kb-summary">
                            <span class="summary-text">Selected <strong id="selectedKbCount">0</strong> knowledge bases</span>
                        </div>
                    </div>

                    <div class="dialog-footer">
                        <button class="btn-secondary" id="cancelAgentKb">Cancel</button>
                        <button class="btn-primary" id="saveAgentKb">Save</button>
                    </div>
                </div>
            </div>
        `;
    },

    async loadData(agentId) {
        try {
            const [agentKbResp, allKbsResp] = await Promise.all([
                fetch(this.resolve(`/api/agent/${agentId}/knowledge-bases`)).then(r => r.json()),
                fetch(this.resolve('/api/km')).then(r => r.json())
            ]);

            const selectedKmIds = (agentKbResp && agentKbResp.success && agentKbResp.data && Array.isArray(agentKbResp.data.km_ids))
                ? agentKbResp.data.km_ids
                : [];

            selectedKmIds.forEach(kmId => this.currentSelections.add(String(kmId)));

            const allKbs = (allKbsResp && allKbsResp.success && Array.isArray(allKbsResp.data)) ? allKbsResp.data : [];
            const visibleKbs = allKbs.filter(kb => kb.is_show !== false && (kb.is_delete === null || kb.is_delete === false));

            const dialog = document.getElementById('agentKnowledgeBaseDialog');
            if (dialog) {
                dialog.dataset.agentId = String(agentId);
                dialog.dataset.allKbs = JSON.stringify(visibleKbs);
            }

            this.renderKbList(visibleKbs);
        } catch (error) {
            console.error('[AgentKnowledgeBaseDialog] Failed to load data:', error);
            this.showError('Failed to load data');
        }
    },

    renderKbList(kbs) {
        const listContainer = document.getElementById('kbList');
        if (!listContainer) return;

        if (!kbs || kbs.length === 0) {
            listContainer.innerHTML = '<div class="empty-state">No knowledge bases available</div>';
            this.updateSelectedCount();
            return;
        }

        const html = kbs.map(kb => {
            const kmId = String(kb.km_id || '');
            const isSelected = this.currentSelections.has(kmId);
            const name = kb.name || 'Unnamed KB';
            const memo = kb.memo || '';
            const typeLabel = String(kb.kmtype) === '0'
                ? 'File'
                : String(kb.kmtype) === '2'
                    ? 'Key-Value'
                    : 'Note';

            return `
                <div class="kb-item ${isSelected ? 'selected' : ''}" data-km-id="${this.escapeHtml(kmId)}">
                    <div class="kb-checkbox">
                        <input type="checkbox" ${isSelected ? 'checked' : ''} data-km-id="${this.escapeHtml(kmId)}">
                    </div>
                    <div class="kb-info">
                        <div class="kb-name">${this.escapeHtml(name)}</div>
                        <div class="kb-description">${this.escapeHtml(memo)}${memo ? ' · ' : ''}${this.escapeHtml(typeLabel)} · ${this.escapeHtml(kmId)}</div>
                    </div>
                </div>
            `;
        }).join('');

        listContainer.innerHTML = html;
        this.updateSelectedCount();
    },

    bindEventHandlers(agentId) {
        const dialog = document.getElementById('agentKnowledgeBaseDialog');
        if (!dialog) return;

        const closeBtn = dialog.querySelector('#closeAgentKbDialog');
        const cancelBtn = dialog.querySelector('#cancelAgentKb');
        const saveBtn = dialog.querySelector('#saveAgentKb');

        if (closeBtn) closeBtn.addEventListener('click', () => this.close());
        if (cancelBtn) cancelBtn.addEventListener('click', () => this.close());

        dialog.addEventListener('click', (e) => {
            if (e.target && e.target.id === 'agentKnowledgeBaseDialog') {
                this.close();
            }
        });

        const searchInput = dialog.querySelector('#kbSearchInput');
        if (searchInput) {
            searchInput.addEventListener('input', (e) => {
                this.filterList(e.target.value);
            });
        }

        dialog.addEventListener('change', (e) => {
            if (e.target && e.target.type === 'checkbox' && e.target.dataset.kmId) {
                this.toggleSelection(e.target);
            }
        });

        if (saveBtn) {
            saveBtn.addEventListener('click', () => this.saveConfiguration(agentId));
        }
    },

    filterList(searchText) {
        const dialog = document.getElementById('agentKnowledgeBaseDialog');
        if (!dialog) return;

        const allKbs = JSON.parse(dialog.dataset.allKbs || '[]');
        const lower = String(searchText || '').toLowerCase();

        const filtered = allKbs.filter(kb => {
            const name = String(kb.name || '').toLowerCase();
            const memo = String(kb.memo || '').toLowerCase();
            const kmId = String(kb.km_id || '').toLowerCase();
            return name.includes(lower) || memo.includes(lower) || kmId.includes(lower);
        });

        this.renderKbList(filtered);
    },

    toggleSelection(checkbox) {
        const kmId = String(checkbox.dataset.kmId);
        const item = checkbox.closest('.kb-item');

        if (checkbox.checked) {
            this.currentSelections.add(kmId);
        } else {
            this.currentSelections.delete(kmId);
        }

        if (item) {
            item.classList.toggle('selected', checkbox.checked);
        }

        this.updateSelectedCount();
    },

    updateSelectedCount() {
        const countEl = document.getElementById('selectedKbCount');
        if (countEl) {
            countEl.textContent = String(this.currentSelections.size);
        }
    },

    async saveConfiguration(agentId) {
        try {
            const kmIds = Array.from(this.currentSelections);

            const resp = await fetch(this.resolve(`/api/agent/${agentId}/knowledge-bases`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ km_ids: kmIds })
            });

            const result = await resp.json();
            if (!result || !result.success) {
                throw new Error(result && result.detail ? result.detail : 'Save failed');
            }

            this.showSuccess('Knowledge base configuration saved');
            setTimeout(() => this.close(), 800);
        } catch (error) {
            console.error('[AgentKnowledgeBaseDialog] Save failed:', error);
            this.showError('Save failed: ' + (error && error.message ? error.message : String(error)));
        }
    },

    close() {
        const dialog = document.getElementById('agentKnowledgeBaseDialog');
        if (dialog) {
            dialog.remove();
        }
    },

    escapeHtml(text) {
        if (text === null || text === undefined) return '';
        const div = document.createElement('div');
        div.textContent = String(text);
        return div.innerHTML;
    },

    showSuccess(message) {
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

    showError(message) {
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

window.AgentKnowledgeBaseDialog = AgentKnowledgeBaseDialog;
