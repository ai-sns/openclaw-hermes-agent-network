/**
 * KM Sidebar - Dynamic knowledge base loading (similar to AgentSidebar)
 */

const KMSidebar = {
    /**
     * Render sidebar - returns basic structure, dynamically filled by init()
     */
    render() {
        return `
            <div class="sidebar-section km-list-section">
                <div class="km-list" id="kmList"></div>
            </div>
        `;
    },

    /**
     * Initialize - load knowledge bases from API and create UI
     */
    async init() {
        console.log('[KMSidebar] Starting initialization...');

        // 1. Load knowledge base list from API
        const kbs = await this.loadKnowledgeBasesFromAPI();
        console.log('[KMSidebar] Loaded knowledge bases:', kbs);

        if (kbs.length === 0) {
            console.warn('[KMSidebar] No available knowledge bases');
            // Still render the empty hint + KM Management button so the user can create a KB
            this.renderEmptyState();
            this.bindEvents();
            return;
        }

        // 2. Render knowledge base list (each kb includes item + section)
        this.renderKMList(kbs);

        // 3. Bind events
        this.bindEvents();

        // 4. Restore previous selection or expand first kb
        if (kbs.length > 0) {
            const savedKbId = window.kmState?.currentKbId;
            const kbToSelect = savedKbId && kbs.find(k => k.id === savedKbId)
                ? savedKbId
                : kbs[0].id;

            console.log('[KMSidebar] Selecting KB:', kbToSelect, savedKbId ? '(restored)' : '(default first)');

            if (window.kmState) {
                window.kmState.setCurrentKb(kbToSelect);
            }

            this.switchKb(kbToSelect);
        }

        console.log('[KMSidebar] Initialization complete');
    },

    /**
     * Load knowledge base list from API
     */
    async loadKnowledgeBasesFromAPI() {
        try {
            const base = (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function')
                ? window.resolveAgentServerUrl('/api/km')
                : '/api/km';
            // Cache-bust to make sure the sidebar always sees the latest data
            // immediately after a KB update (e.g. rename).
            const url = `${base}${base.includes('?') ? '&' : '?'}_t=${Date.now()}`;
            const response = await fetch(url, { cache: 'no-store' });
            const result = await response.json();

            if (result.success && result.data) {
                return result.data.filter(kb => kb.is_show !== false && (kb.is_delete === null || kb.is_delete === false));
            }
            return [];
        } catch (error) {
            console.error('[KMSidebar] Failed to load knowledge bases:', error);
            return [];
        }
    },

    /**
     * Render knowledge base list (new architecture: each kb item followed by its section)
     */
    renderKMList(kbs) {
        const kmList = document.getElementById('kmList');
        if (!kmList) return;

        // Create item + section for each kb
        const kmItemsHTML = kbs.map(kb => `
            <!-- KB list item -->
            <div class="km-item" data-kb-id="${kb.id}" data-km-id="${kb.km_id}" data-kb-type="${kb.kmtype}">
                <svg viewBox="0 0 24 24" width="18" height="18" fill="#1a73e8">
                    <path d="${this.getKbIcon(kb.kmtype)}"/>
                </svg>
                <span class="web-section-title">${kb.name || 'Unnamed KB'}</span>
            </div>

            <!-- KB-specific expandable section (initially hidden) -->
            <div class="km-section-container" data-kb-id="${kb.id}" data-km-id="${kb.km_id}" style="display: none;">
                ${this.createKbSectionHTML(kb)}
            </div>
        `).join('');

        // Add management button
        const managementButtons = `
            <div class="km-item km-management" data-page="km-management">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/>
                </svg>
                <span class="web-section-title">KM Management</span>
            </div>
        `;

        kmList.innerHTML = kmItemsHTML + managementButtons;
        console.log('[KMSidebar] KB list rendered (new architecture: item+section mode)');
    },

    /**
     * Get icon path based on kb type
     */
    getKbIcon(kmtype) {
        const icons = {
            '0': 'M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z', // File
            '1': 'M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z', // Note
            '2': 'M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z' // Key-value
        };
        return icons[String(kmtype)] || icons['1'];
    },

    /**
     * Create section HTML for a single KB
     */
    createKbSectionHTML(kb) {
        const kmtype = String(kb.kmtype);

        if (kmtype === '1') {
            // Note type
            return this.createNoteSectionHTML(kb);
        } else if (kmtype === '0') {
            // File type
            return this.createFileSectionHTML(kb);
        } else if (kmtype === '2') {
            // Key-value type
            return this.createKeyValueSectionHTML(kb);
        }

        return '<div>Unknown KB type</div>';
    },

    /**
     * Create note type section HTML (kmtype=1)
     */
    createNoteSectionHTML(kb) {
        return `
            <div class="km-user-section" data-kb-id="${kb.id}" data-km-id="${kb.km_id}">
                <!-- Action buttons -->
                <div class="agent-action-buttons">
                    <button class="agent-action-btn" data-action="new-note" data-kb-id="${kb.id}" data-km-id="${kb.km_id}">
                        <div class="action-btn-icon">
                             <svg viewBox="0 0 48 48" width="40" height="40">
                                <rect x="8" y="8" width="32" height="32" rx="2" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="24" y1="16" x2="24" y2="32" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="16" y1="24" x2="32" y2="24" stroke="#1a73e8" stroke-width="2"/>
                            </svg>
                        </div>
                        <span class="action-btn-text">New Note</span>
                    </button>
                    <button class="agent-action-btn" data-action="settings" data-kb-id="${kb.id}" data-km-id="${kb.km_id}">
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
                <div class="km-content-section">
                    <div class="sns-sidebar-tabs">
                        <button class="sidebar-tab active" data-tab="all" data-kb-id="${kb.id}" data-km-id="${kb.km_id}">All</button>
                        <button class="sidebar-tab" data-tab="tag" data-kb-id="${kb.id}" data-km-id="${kb.km_id}">Tag</button>
                    </div>
                    <div class="tab-content active" data-content="all" data-kb-id="${kb.id}" data-km-id="${kb.km_id}">
                        <div class="sns-search-box">
                            <div class="sns-search-wrapper">
                                <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                                </svg>
                                <input type="text" class="sns-search-input" id="kmNoteSearchInput-${kb.id}" placeholder="Keyword+Enter,Blank+Enter to reset" data-kb-id="${kb.id}" data-km-id="${kb.km_id}" />
                                <button class="sns-search-clear" id="kmNoteSearchClear-${kb.id}">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                        <!-- Note list -->
                        <div class="km-note-container" id="noteContainer-${kb.id}">
                            <div class="km-note-tree" id="noteTree-${kb.id}" data-km-id="${kb.km_id}">
                                <!-- Notes will be dynamically loaded here -->
                            </div>
                        </div>
                    </div>
                    <div class="tab-content" data-content="tag" data-kb-id="${kb.id}" data-km-id="${kb.km_id}">
                        <div class="sns-search-box">
                            <div class="sns-search-wrapper">
                                <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                                </svg>
                                <input type="text" class="sns-search-input" id="kmNoteTagSearchInput-${kb.id}" placeholder="Keyword+Enter,Blank+Enter to reset" data-kb-id="${kb.id}" data-km-id="${kb.km_id}" />
                                <button class="sns-search-clear" id="kmNoteTagSearchClear-${kb.id}">
                                    <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                        <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                    </svg>
                                </button>
                            </div>
                        </div>
                        <div class="chat-list-container" id="kmNoteTagList-${kb.id}">
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
     * Create file type section HTML (kmtype=0)
     */
    createFileSectionHTML(kb) {
        return `
            <div class="km-user-section" data-kb-id="${kb.id}">
                <!-- Action buttons -->
                <div class="agent-action-buttons">
                    <button class="agent-action-btn" data-action="add-file" data-kb-id="${kb.id}">
                        <div class="action-btn-icon">
                             <svg viewBox="0 0 48 48" width="40" height="40">
                                <rect x="8" y="8" width="32" height="32" rx="2" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="24" y1="16" x2="24" y2="32" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="16" y1="24" x2="32" y2="24" stroke="#1a73e8" stroke-width="2"/>
                            </svg>
                        </div>
                        <span class="action-btn-text">Add File</span>
                    </button>
                    <button class="agent-action-btn" data-action="settings" data-kb-id="${kb.id}">
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
                <div class="km-content-section">
                    <div class="sns-search-box">
                        <div class="sns-search-wrapper">
                            <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                            </svg>
                            <input type="text" class="sns-search-input" id="kmFileSearchInput-${kb.id}" placeholder="Keyword+Enter,Blank+Enter to reset" data-kb-id="${kb.id}" />
                            <button class="sns-search-clear" id="kmFileSearchClear-${kb.id}">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <!-- File list -->
                    <div class="km-file-container" id="fileContainer-${kb.id}">
                        <div class="km-file-tree" id="fileTree-${kb.id}">
                            <!-- Files will be dynamically loaded here -->
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * Create key-value type section HTML (kmtype=2)
     */
    createKeyValueSectionHTML(kb) {
        return `
            <div class="km-user-section" data-kb-id="${kb.id}">
                <!-- Action buttons -->
                <div class="agent-action-buttons">
                    <button class="agent-action-btn" data-action="add-kv" data-kb-id="${kb.id}">
                        <div class="action-btn-icon">
                            <svg viewBox="0 0 48 48" width="40" height="40">
                                <rect x="8" y="8" width="32" height="32" rx="2" fill="none" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="24" y1="16" x2="24" y2="32" stroke="#1a73e8" stroke-width="2"/>
                                <line x1="16" y1="24" x2="32" y2="24" stroke="#1a73e8" stroke-width="2"/>
                            </svg>
                        </div>
                        <span class="action-btn-text">Add</span>
                    </button>
                    <button class="agent-action-btn" data-action="settings" data-kb-id="${kb.id}">
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
                <div class="km-content-section">
                    <div class="sns-search-box">
                        <div class="sns-search-wrapper">
                            <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                            </svg>
                            <input type="text" class="sns-search-input" id="kmKvSearchInput-${kb.id}" placeholder="Keyword+Enter,Blank+Enter to reset" data-kb-id="${kb.id}" />
                            <button class="sns-search-clear" id="kmKvSearchClear-${kb.id}">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <!-- Key-value list -->
                    <div class="km-kv-container" id="kvContainer-${kb.id}">
                        <div class="km-kv-tree" id="kvTree-${kb.id}">
                            <!-- Key-value pairs will be dynamically loaded here -->
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
        const kmList = document.getElementById('kmList');
        if (!kmList) return;
        // Keep the KM Management entry visible so the user can still create a KB.
        const managementButton = `
            <div class="km-item km-management" data-page="km-management">
                <svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor">
                    <path d="M19.14 12.94c.04-.31.06-.63.06-.94 0-.31-.02-.63-.06-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.04.31-.06.63-.06.94s.02.63.06.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58z"/>
                </svg>
                <span class="web-section-title">KM Management</span>
            </div>
        `;
        kmList.innerHTML = `
            <div class="empty-state" style="padding: 20px; text-align: center; color: #999;">
                <p>No available knowledge bases</p>
                <p style="font-size: 12px; margin-top: 10px;">Please create a knowledge base in KM Management</p>
            </div>
            ${managementButton}
        `;
    },

    /**
     * Bind events
     */
    bindEvents() {
        console.log('[KMSidebar] Starting event binding...');

        // 1. KB list item click - switch KB (expand/collapse)
        document.querySelectorAll('#kmList .km-item[data-kb-id]').forEach(item => {
            item.addEventListener('click', () => {
                const kbId = parseInt(item.dataset.kbId);
                console.log('[KMSidebar] Clicked KB:', kbId);
                this.switchKb(kbId);
            });
        });

        // 2. New Note button
        document.querySelectorAll('[data-action="new-note"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const kbId = parseInt(btn.dataset.kbId);
                console.log('[KMSidebar] Clicked New Note:', kbId);
                this.handleNewNote(kbId);
            });
        });

        // 3. Add File button
        document.querySelectorAll('[data-action="add-file"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const kbId = parseInt(btn.dataset.kbId);
                console.log('[KMSidebar] Clicked Add File:', kbId);
                this.handleAddFile(kbId);
            });
        });

        // 4. Add Key-Value button
        document.querySelectorAll('[data-action="add-kv"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const kbId = parseInt(btn.dataset.kbId);
                console.log('[KMSidebar] Clicked Add KV:', kbId);
                this.handleAddKV(kbId);
            });
        });

        // 5. Settings button
        document.querySelectorAll('[data-action="settings"]').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                const kbId = parseInt(btn.dataset.kbId);
                console.log('[KMSidebar] Clicked Settings:', kbId);
                this.handleSettings(kbId);
            });
        });

        // 6. Tab switching
        document.querySelectorAll('.sidebar-tab[data-kb-id]').forEach(tab => {
            tab.addEventListener('click', (e) => {
                e.stopPropagation();
                const kbId = tab.dataset.kbId;
                const tabType = tab.dataset.tab;

                const sameSectionTabs = document.querySelectorAll(`.sidebar-tab[data-kb-id="${kbId}"]`);
                sameSectionTabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                const contents = document.querySelectorAll(`.tab-content[data-kb-id="${kbId}"]`);
                contents.forEach(c => c.classList.remove('active'));
                const activeContent = document.querySelector(`.tab-content[data-kb-id="${kbId}"][data-content="${tabType}"]`);
                if (activeContent) {
                    activeContent.classList.add('active');
                }

                console.log('[KMSidebar] Switched tab:', tabType, 'for KB:', kbId);

                if (tabType === 'tag' && window.kmHandlers && typeof window.kmHandlers.renderNoteTagList === 'function') {
                    window.kmHandlers.renderNoteTagList(parseInt(kbId));
                }
            });
        });

        // Search clear button handling (SNS style)
        document.querySelectorAll('.sns-search-input[id^="kmNoteSearchInput-"], .sns-search-input[id^="kmNoteTagSearchInput-"], .sns-search-input[id^="kmFileSearchInput-"], .sns-search-input[id^="kmKvSearchInput-"]').forEach(input => {
            const clearId = input.id
                .replace('kmNoteSearchInput-', 'kmNoteSearchClear-')
                .replace('kmNoteTagSearchInput-', 'kmNoteTagSearchClear-')
                .replace('kmFileSearchInput-', 'kmFileSearchClear-')
                .replace('kmKvSearchInput-', 'kmKvSearchClear-');

            const clearBtn = document.getElementById(clearId);
            if (!clearBtn) return;

            input.addEventListener('input', () => {
                clearBtn.classList.toggle('visible', input.value.length > 0);
            });

            clearBtn.addEventListener('click', (e) => {
                e.stopPropagation();
                input.value = '';
                clearBtn.classList.remove('visible');
                input.dispatchEvent(new Event('input'));
            });
        });

        // 7. Management button
        document.querySelectorAll('.km-management[data-page]').forEach(btn => {
            btn.addEventListener('click', () => {
                const page = btn.dataset.page;
                console.log('[KMSidebar] Clicked management button:', page);
                this.navigateToManagementPage(page);
            });
        });

        console.log('[KMSidebar] Event binding complete');
    },

    /**
     * Switch KB (new architecture: expand/collapse corresponding section-container)
     */
    switchKb(kbId) {
        console.log('[KMSidebar] Switching to KB:', kbId);

        // 0. Update kmState
        if (window.kmState) {
            window.kmState.setCurrentKb(kbId);
            console.log('[KMSidebar] Updated kmState.currentKbId to:', kbId);
        }

        // 1. Collapse all km-section-container
        document.querySelectorAll('.km-section-container').forEach(container => {
            container.style.display = 'none';
        });

        // 2. Expand selected kb's section-container
        const targetContainer = document.querySelector(`.km-section-container[data-kb-id="${kbId}"]`);
        if (targetContainer) {
            targetContainer.style.display = 'block';
            console.log('[KMSidebar] Expanded KB section container:', kbId);
        }

        // 3. Update km list active state
        document.querySelectorAll('#kmList .km-item[data-kb-id]').forEach(item => {
            item.classList.remove('active');
        });
        const activeItem = document.querySelector(`#kmList .km-item[data-kb-id="${kbId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }

        // 4. Get KB type and km_id, then trigger global event
        const kbItem = document.querySelector(`#kmList .km-item[data-kb-id="${kbId}"]`);
        const kbType = kbItem ? parseInt(kbItem.dataset.kbType) : null;
        const kmId = kbItem ? kbItem.dataset.kmId : null;

        // 5. Trigger global event with kbType and kmId - this will cause kmHandlers to render the appropriate page
        window.dispatchEvent(new CustomEvent('km-switched', {
            detail: { kbId, kmId, kbType }
        }));

        console.log('[KMSidebar] KB switch complete');
    },

    /**
     * Handle New Note
     */
    handleNewNote(kbId) {
        console.log('[KMSidebar] Handle New Note for KB:', kbId);
        window.dispatchEvent(new CustomEvent('km-new-note', {
            detail: { kbId }
        }));
    },

    /**
     * Handle Add File
     */
    handleAddFile(kbId) {
        console.log('[KMSidebar] Handle Add File for KB:', kbId);
        window.dispatchEvent(new CustomEvent('km-add-file', {
            detail: { kbId }
        }));
    },

    /**
     * Handle Add Key-Value
     */
    handleAddKV(kbId) {
        console.log('[KMSidebar] Handle Add KV for KB:', kbId);
        window.dispatchEvent(new CustomEvent('km-add-kv', {
            detail: { kbId }
        }));
    },

    /**
     * Handle Settings
     */
    async handleSettings(kbId) {
        console.log('[KMSidebar] Handle Settings for KB:', kbId);

        if (!window.KMManagementDialog) {
            console.error('[KMSidebar] KMManagementDialog not available');
            return;
        }

        // Find the KB data
        const kbs = await this.loadKnowledgeBasesFromAPI();
        const kb = kbs.find(k => k.id === kbId);

        if (!kb) {
            console.error('[KMSidebar] KB not found:', kbId);
            return;
        }

        // Show edit dialog
        const kbData = await window.KMManagementDialog.showEditDialog(kb);

        if (kbData) {
            // Update KB
            const updated = await window.KMManagementDialog.updateKB(kbData);
            if (updated) {
                // Reload sidebar
                await this.reload();
            }
        }
    },

    /**
     * Navigate to management page
     */
    async navigateToManagementPage(page) {
        console.log('[KMSidebar] Navigate to management page:', page);

        if (!window.KMManagementDialog) {
            console.error('[KMSidebar] KMManagementDialog not available');
            return;
        }

        if (page === 'km-management') {
            await this.showKMManageDialog();
            return;
        }

        if (page === 'create') {
            // Show create dialog
            const kbData = await window.KMManagementDialog.showCreateDialog();

            if (kbData) {
                // Create KB
                const created = await window.KMManagementDialog.createKB(kbData);
                if (created) {
                    // Reload sidebar
                    await this.reload();
                    // Switch to the newly created KB
                    this.switchKb(created.id);
                }
            }
        } else if (page === 'list') {
            // Show KB list management
            await this.showKBListManagement();
        }
    },

    async showKMManageDialog() {
        const kbsAll = await this.fetchAllKnowledgeBasesForManage();

        if (window.electronAPI && window.electronAPI.hideBrowserView) {
            window.electronAPI.hideBrowserView();
        }

        const dialogHTML = `
            <div class="web-manage-dialog-overlay" id="kmManageDialog">
                <div class="web-manage-dialog">
                    <div class="web-manage-dialog-header">
                        <h3>Manage Knowledge Bases</h3>
                        <div style="display:flex; gap:8px; align-items:center;">
                            <button class="web-action-btn" id="kmAddBtn" style="height:32px; padding:0 12px;">
                                <span>Add</span>
                            </button>
                            <button class="web-manage-dialog-close" data-action="close-km-manage">
                                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="2">
                                    <path d="M18 6L6 18M6 6l12 12"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="web-manage-dialog-content">
                        <div class="web-manage-list" id="kmManageList">
                            ${this.renderKMManageItems(kbsAll)}
                        </div>
                    </div>
                </div>
            </div>
        `;

        const oldDialog = document.getElementById('kmManageDialog');
        if (oldDialog) oldDialog.remove();

        document.body.insertAdjacentHTML('beforeend', dialogHTML);

        this.initKMDragAndDrop();
        this.bindKMManageDialogEvents();
    },

    async fetchAllKnowledgeBasesForManage() {
        try {
            const url = (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function')
                ? window.resolveAgentServerUrl('/api/km')
                : '/api/km';
            const response = await fetch(url);
            const result = await response.json();
            if (result && result.success && result.data) {
                return result.data.filter(kb => kb.is_delete === null || kb.is_delete === false);
            }
            return [];
        } catch (error) {
            console.error('[KMSidebar] Failed to load knowledge bases for manage:', error);
            return [];
        }
    },

    renderKMManageItems(kbs) {
        if (!kbs || kbs.length === 0) {
            return '<div class="web-empty-message">No knowledge bases available</div>';
        }

        return kbs.map((kb, index) => {
            const name = (kb.name || 'Unnamed KB');
            const memo = (kb.memo || '');
            const showText = kb.is_show === false ? 'Hidden' : 'Shown';
            const kmTypeNum = Number(kb.kmtype);
            const typeText = kmTypeNum === 1 ? 'Note' : kmTypeNum === 0 ? 'File' : kmTypeNum === 2 ? 'Key-Value' : String(kb.kmtype);

            return `
                <div class="web-manage-item" draggable="true" data-id="${kb.id}" data-position="${kb.position ?? index}">
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
                        <div class="web-manage-item-url">${memo ? memo : `${typeText} | ${showText}`}</div>
                    </div>
                    <div class="web-manage-item-actions">
                        <button type="button" class="web-manage-item-btn web-manage-item-btn-delete" data-action="delete-kb" data-id="${kb.id}" title="Delete">
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

    bindKMManageDialogEvents() {
        const dialog = document.getElementById('kmManageDialog');
        if (!dialog) return;

        dialog.addEventListener('click', async (e) => {
            const button = e.target.closest('button');
            if (!button) return;

            const action = button.dataset.action;
            if (action === 'close-km-manage') {
                await this.closeKMManageDialog();
                return;
            }

            if (button.id === 'kmAddBtn') {
                const kbData = await window.KMManagementDialog.showCreateDialog();
                if (kbData) {
                    const created = await window.KMManagementDialog.createKB(kbData);
                    if (created) {
                        // Refresh management interface
                        const kbsAll = await this.fetchAllKnowledgeBasesForManage();
                        const list = document.getElementById('kmManageList');
                        if (list) {
                            list.innerHTML = this.renderKMManageItems(kbsAll);
                        }

                        // Refresh sidebar to show new KB immediately
                        await this.reload();
                        // Switch to the newly created KB
                        this.switchKb(created.id);
                    }
                }
                return;
            }

            if (action === 'delete-kb') {
                e.preventDefault();
                e.stopPropagation();

                const kbId = parseInt(button.dataset.id);
                if (!kbId) return;

                const kbsAll = await this.fetchAllKnowledgeBasesForManage();
                const kb = (kbsAll || []).find(k => parseInt(k.id) === kbId);
                const kbName = kb && kb.name ? `"${kb.name}"` : 'this knowledge base';

                const confirmed = await (async () => {
                    try {
                        if (window.Toast && typeof window.Toast.confirm === 'function') {
                            return await window.Toast.confirm(`Delete ${kbName}?`, {
                                title: 'Delete Knowledge Base',
                                confirmText: 'Delete',
                                cancelText: 'Cancel',
                                type: 'warning'
                            });
                        }

                        if (window.Modal && typeof window.Modal.show === 'function') {
                            return await new Promise((resolve) => {
                                window.Modal.show({
                                    title: 'Delete Knowledge Base',
                                    content: `<p>Delete ${kbName}?</p>`,
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
                        console.error('Failed to show delete KB confirmation dialog:', err);
                    }
                    return false;
                })();

                if (!confirmed) return;

                try {
                    const deleteUrl = (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function')
                        ? window.resolveAgentServerUrl(`/api/km/${kbId}`)
                        : `/api/km/${kbId}`;
                    const resp = await fetch(deleteUrl, {
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
                        window.Toast.success('Knowledge base deleted successfully');
                    }

                    const nextKbs = await this.fetchAllKnowledgeBasesForManage();
                    const list = document.getElementById('kmManageList');
                    if (list) {
                        list.innerHTML = this.renderKMManageItems(nextKbs);
                    }

                    await this.reload();
                } catch (err) {
                    console.error('[KMSidebar] Failed to delete knowledge base:', err);
                    if (window.Toast && typeof window.Toast.error === 'function') {
                        window.Toast.error('Delete failed: ' + (err.message || String(err)));
                    }
                }
            }
        });

        // Clicking the overlay no longer closes the dialog to prevent accidental dismissal
    },

    async closeKMManageDialog() {
        const dialog = document.getElementById('kmManageDialog');
        if (dialog) dialog.remove();

        // Only restore BrowserView if user is currently on the Web page; otherwise
        // showing it would cover the active KM/Agent/etc. page with a stale webview.
        const onWebPage = !!(window.router && typeof window.router.getCurrentPage === 'function' && window.router.getCurrentPage() === 'web');
        if (onWebPage && window.electronAPI && window.electronAPI.showBrowserView) {
            window.electronAPI.showBrowserView();
        }

        await this.reload();
    },

    initKMDragAndDrop() {
        const list = document.getElementById('kmManageList');
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
            await this.updateKMPositions();
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

    async updateKMPositions() {
        const list = document.getElementById('kmManageList');
        if (!list) return;

        const items = [...list.querySelectorAll('.web-manage-item')];
        const updates = items.map((item, index) => ({
            id: parseInt(item.dataset.id),
            position: index
        }));

        try {
            const url = (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function')
                ? window.resolveAgentServerUrl('/api/km/reorder')
                : '/api/km/reorder';
            const response = await fetch(url, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(updates)
            });

            if (!response.ok) {
                const errorText = await response.text();
                throw new Error(errorText || 'Failed to update KB positions');
            }
        } catch (error) {
            console.error('[KMSidebar] Failed to update KB positions:', error);
            alert('Failed to update KB positions. Please try again.');
        }
    },

    /**
     * Show KB list management
     */
    async showKBListManagement() {
        console.log('[KMSidebar] Show KB list management');

        const kbs = await this.loadKnowledgeBasesFromAPI();

        if (kbs.length === 0) {
            window.Toast.info('No knowledge bases found. Create one first!');
            return;
        }

        // Create management panel
        const backdrop = document.createElement('div');
        backdrop.style.cssText = `
            position: fixed;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            background: rgba(0, 0, 0, 0.5);
            z-index: 100002;
            display: flex;
            align-items: center;
            justify-content: center;
        `;

        const panel = document.createElement('div');
        panel.style.cssText = `
            background: white;
            border-radius: 12px;
            padding: 24px;
            min-width: 600px;
            max-width: 800px;
            max-height: 80vh;
            overflow-y: auto;
            box-shadow: 0 8px 32px rgba(0, 0, 0, 0.25);
        `;

        const kbListHTML = kbs.map(kb => `
            <div class="kb-item" style="
                padding: 16px;
                border: 1px solid #ddd;
                border-radius: 8px;
                margin-bottom: 12px;
                display: flex;
                justify-content: space-between;
                align-items: center;
            ">
                <div style="flex: 1;">
                    <div style="font-weight: 600; margin-bottom: 4px;">${this.escapeHtml(kb.name)}</div>
                    <div style="font-size: 12px; color: #666;">
                        Type: ${kb.kmtype === 1 ? 'Note' : kb.kmtype === 0 ? 'File' : 'Key-Value'}
                        | ID: ${kb.km_id}
                    </div>
                    ${kb.memo ? `<div style="font-size: 12px; color: #999; margin-top: 4px;">${this.escapeHtml(kb.memo)}</div>` : ''}
                </div>
                <div style="display: flex; gap: 8px;">
                    <button class="kb-edit-btn" data-kb-id="${kb.id}" style="
                        padding: 6px 12px;
                        background: #1a73e8;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    ">Edit</button>
                    <button class="kb-delete-btn" data-kb-id="${kb.id}" style="
                        padding: 6px 12px;
                        background: #f44336;
                        color: white;
                        border: none;
                        border-radius: 4px;
                        cursor: pointer;
                    ">Delete</button>
                </div>
            </div>
        `).join('');

        panel.innerHTML = `
            <div style="margin-bottom: 24px;">
                <h2 style="margin: 0 0 8px 0; font-size: 20px;">Knowledge Bases Management</h2>
                <p style="margin: 0; color: #666; font-size: 14px;">Manage all your knowledge bases</p>
            </div>
            <div class="kb-list">
                ${kbListHTML}
            </div>
            <div style="margin-top: 24px; text-align: right;">
                <button id="closeListBtn" style="
                    padding: 10px 20px;
                    border: 1px solid #ddd;
                    background: white;
                    border-radius: 6px;
                    cursor: pointer;
                ">Close</button>
            </div>
        `;

        backdrop.appendChild(panel);
        document.body.appendChild(backdrop);

        // Bind events
        panel.querySelectorAll('.kb-edit-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const kbId = parseInt(btn.dataset.kbId);
                const kb = kbs.find(k => k.id === kbId);
                if (kb) {
                    const kbData = await window.KMManagementDialog.showEditDialog(kb);
                    if (kbData) {
                        const updated = await window.KMManagementDialog.updateKB(kbData);
                        if (updated) {
                            backdrop.remove();
                            await this.reload();
                        }
                    }
                }
            });
        });

        panel.querySelectorAll('.kb-delete-btn').forEach(btn => {
            btn.addEventListener('click', async () => {
                const kbId = parseInt(btn.dataset.kbId);
                const kb = kbs.find(k => k.id === kbId);
                if (kb) {
                    const confirmed = await window.KMManagementDialog.confirmDelete(kb);
                    if (confirmed) {
                        const deleted = await window.KMManagementDialog.deleteKB(kbId);
                        if (deleted) {
                            backdrop.remove();
                            await this.reload();
                        }
                    }
                }
            });
        });

        panel.querySelector('#closeListBtn').addEventListener('click', () => {
            backdrop.remove();
        });

        // Clicking the backdrop no longer closes the panel to prevent accidental dismissal
    },

    /**
     * Escape HTML
     */
    escapeHtml(text) {
        if (!text) return '';
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Reload KB list
     */
    async reload() {
        console.log('[KMSidebar] Starting reload...');

        const kbs = await this.loadKnowledgeBasesFromAPI();
        console.log('[KMSidebar] Reloaded KBs:', kbs);

        if (kbs.length === 0) {
            console.warn('[KMSidebar] No available knowledge bases');
            this.renderEmptyState();
            // Bind events so KM Management button works in empty state
            this.bindEvents();
            return;
        }

        const currentKbId = window.kmState?.currentKbId ||
            (() => {
                const currentExpandedContainer = document.querySelector('.km-section-container[style*="display: block"]');
                return currentExpandedContainer ? parseInt(currentExpandedContainer.dataset.kbId) : null;
            })();

        this.renderKMList(kbs);
        this.bindEvents();

        if (currentKbId && kbs.find(k => k.id === currentKbId)) {
            console.log('[KMSidebar] Restoring previous KB:', currentKbId);
            this.switchKb(currentKbId);
        } else if (kbs.length > 0) {
            console.log('[KMSidebar] Selecting first KB');
            this.switchKb(kbs[0].id);
        }

        console.log('[KMSidebar] Reload complete');
    }
};

// Export to global (for use by other modules)
if (typeof window !== 'undefined') {
    window.KMSidebar = KMSidebar;

    // Initialize kmState if not exists
    if (!window.kmState) {
        window.kmState = {
            currentKbId: null,
            setCurrentKb: function(kbId) {
                this.currentKbId = kbId;
            }
        };
    }
}

export default KMSidebar;
