/**
 * KM Handlers - Multi-KB event handling for all KB types
 */

import Toast from '../../utils/toast.js';
import KMNotePage from './KMNotePage.js';
import KMFilePage from './KMFilePage.js';
import KMKeyValuePage from './KMKeyValuePage.js';

const kmHandlers = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },
    currentKbId: null,
    currentKmId: null,  // String km_id like "note_store"
    currentKbType: null,
    currentNoteId: null,
    currentFileId: null,
    currentKvId: null,
    mainPageCache: {},
    notes: {},
    files: {},
    keyValues: {},

    init() {
        this.bindGlobalEvents();
    },

    bindGlobalEvents() {
        // Listen for KB switch events
        window.addEventListener('km-switched', async (e) => {
            const { kbId, kmId, kbType } = e.detail;
            this.currentKbId = kbId;
            this.currentKmId = kmId;  // Store string km_id
            this.currentKbType = kbType;
            console.log('[kmHandlers] KB switched to:', kbId, 'kmId:', kmId, 'type:', kbType);

            // Initialize the appropriate page based on KB type
            await this.initializePage(kbId, kmId, kbType);
        });

        // Listen for new note events
        window.addEventListener('km-new-note', (e) => {
            const { kbId } = e.detail;
            this.createNewNote(kbId);
        });

        // Listen for add file events
        window.addEventListener('km-add-file', (e) => {
            const { kbId } = e.detail;
            this.showAddFileDialog(kbId);
        });

        // Listen for add key-value events
        window.addEventListener('km-add-kv', (e) => {
            const { kbId } = e.detail;
            this.showAddKVDialog(kbId);
        });
    },

    /**
     * Initialize the appropriate page based on KB type
     */
    async initializePage(kbId, kmId, kbType) {
        console.log(`[kmHandlers] Initializing page for KB ${kbId} (kmId: ${kmId}, type: ${kbType})`);

        // Get main content container
        const mainContent = document.getElementById('km-main-content');
        if (!mainContent) {
            console.error('[kmHandlers] Main content container not found');
            return;
        }

        const cacheKey = String(kbId);
        const cached = this.mainPageCache[cacheKey];
        const cachedType = cached ? cached.kbType : null;
        const canReuse = cached && cached.el && cachedType === kbType;

        if (canReuse) {
            if (mainContent.firstChild !== cached.el) {
                mainContent.innerHTML = '';
                mainContent.appendChild(cached.el);
            }
            console.log('[kmHandlers] Reused cached page for KB:', kbId);
        } else {
            if (cached && cached.el && cached.el.parentNode) {
                cached.el.parentNode.removeChild(cached.el);
            }

            const pageWrapper = document.createElement('div');
            pageWrapper.className = 'km-main-page-cache';
            pageWrapper.dataset.kbId = String(kbId);
            pageWrapper.dataset.kbType = String(kbType);

            // Render appropriate page HTML based on KB type
            let pageHTML = '';
            if (kbType === 1) {
                // Note type
                pageHTML = KMNotePage.render();
            } else if (kbType === 0) {
                // File type - pass kbId parameter
                pageHTML = KMFilePage.render(kbId);
            } else if (kbType === 2) {
                // Key-value type - pass kbId parameter
                pageHTML = KMKeyValuePage.render(kbId);
            } else {
                pageHTML = '<div class="km-empty-state"><p style="text-align: center; color: var(--text-muted); padding: 40px;">Unknown KB type</p></div>';
            }

            pageWrapper.innerHTML = pageHTML;
            this.mainPageCache[cacheKey] = { el: pageWrapper, kbType };

            mainContent.innerHTML = '';
            mainContent.appendChild(pageWrapper);
            console.log('[kmHandlers] Rendered and cached page HTML for type:', kbType);

            // Initialize the editor/page based on KB type
            setTimeout(() => {
                try {
                    if (kbType === 1) {
                        if (KMNotePage && typeof KMNotePage.init === 'function') {
                            KMNotePage.init();
                            console.log('[kmHandlers] KMNotePage initialized');
                        }
                    } else if (kbType === 0) {
                        if (KMFilePage && typeof KMFilePage.init === 'function') {
                            KMFilePage.init();
                            console.log('[kmHandlers] KMFilePage initialized');
                        }
                    } else if (kbType === 2) {
                        if (KMKeyValuePage && typeof KMKeyValuePage.init === 'function') {
                            KMKeyValuePage.init();
                            console.log('[kmHandlers] KMKeyValuePage initialized');
                        }
                    }
                } catch (error) {
                    console.error('[kmHandlers] Error initializing page:', error);
                }
            }, 100);
        }

        // Load data based on KB type (use kmId for filtering)
        try {
            if (kbType === 1) {
                // Load notes - use kmId for filtering
                await this.loadNotesForKb(kbId, kmId);
            } else if (kbType === 0) {
                // Load files
                await this.loadFilesForKb(kbId);
            } else if (kbType === 2) {
                // Load key-values
                await this.loadKeyValuesForKb(kbId);
            }
        } catch (error) {
            console.error('[kmHandlers] Error loading KB data:', error);
        }
    },

    async vectorizeCurrentNote() {
        try {
            const noteId = this.currentNoteId;
            const kmId = this.currentKmId;
            if (!noteId || !kmId) {
                Toast.warning('Please select a saved note first');
                return;
            }

            const loading = Toast.loading('Vectorizing...');
            const response = await fetch(this.resolve(`/api/km/notes/${encodeURIComponent(String(noteId))}/vectorize`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ km_id: kmId })
            });
            loading.close();

            if (!response.ok) {
                let message = 'Vectorization failed';
                try {
                    const data = await response.json();
                    if (data && data.detail) message = data.detail;
                } catch (e) {
                    // ignore
                }
                throw new Error(message);
            }

            const result = await response.json();
            const chunks = (result && result.data && typeof result.data.chunks !== 'undefined') ? result.data.chunks : 0;
            Toast.success(`Vectorization completed (chunks: ${chunks})`);
        } catch (e) {
            console.error('[kmHandlers] vectorizeCurrentNote failed:', e);
            Toast.error('Vectorization failed: ' + (e && e.message ? e.message : String(e)));
        }
    },

    showNoteVectorSearchDialog() {
        const kmId = this.currentKmId;
        if (!kmId) {
            Toast.warning('Please select a knowledge base first');
            return;
        }

        if (!window.Modal || typeof window.Modal.show !== 'function') {
            Toast.error('Modal component is not ready');
            return;
        }

        window.Modal.show({
            title: 'Vector search',
            width: '720px',
            content: `
                <div class="form-group">
                    <label class="form-label">Query</label>
                    <input type="text" id="noteVectorQueryInput" class="form-input" placeholder="Type a natural-language question..." autofocus>
                </div>
                <div class="form-group" style="margin-top: 10px;">
                    <div id="noteVectorSearchResults" style="max-height: 50vh; overflow-y: auto;"></div>
                </div>
            `,
            confirmText: 'Search',
            onConfirm: async (modal) => {
                const input = modal.element.querySelector('#noteVectorQueryInput');
                const resultsEl = modal.element.querySelector('#noteVectorSearchResults');
                const query = input ? input.value.trim() : '';
                if (!query) {
                    Toast.warning('Please enter a query');
                    return false;
                }
                if (resultsEl) {
                    resultsEl.innerHTML = '<div class="loading">Searching...</div>';
                }

                try {
                    const response = await fetch(this.resolve('/api/km/notes/vector-search'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ km_id: kmId, query, top_k: 5 })
                    });
                    if (!response.ok) {
                        let message = 'Search failed';
                        try {
                            const data = await response.json();
                            if (data && data.detail) message = data.detail;
                        } catch (e) {
                            // ignore
                        }
                        throw new Error(message);
                    }

                    const result = await response.json();
                    const results = result.data || [];
                    if (!resultsEl) return false;

                    if (!results.length) {
                        resultsEl.innerHTML = '<div class="empty-state">No results found</div>';
                        return false;
                    }

                    const html = results.map((r, idx) => {
                        const score = (r && typeof r.score === 'number') ? r.score.toFixed(3) : '0.000';
                        const title = r && r.metadata && r.metadata.title ? r.metadata.title : '';
                        const content = r && (r.content || r.text) ? (r.content || r.text) : '';
                        return `
                            <div class="search-result-item" style="margin-bottom: 10px;">
                                <div class="result-header">
                                    <span class="result-number">${idx + 1}</span>
                                    <span class="result-score">Score: ${score}</span>
                                </div>
                                ${title ? `<div class="result-metadata">Title: ${this.escapeHtml(title)}</div>` : ''}
                                <div class="result-content">${this.escapeHtml(content)}</div>
                            </div>
                        `;
                    }).join('');

                    resultsEl.innerHTML = html;
                } catch (e) {
                    console.error('[kmHandlers] note vector search failed:', e);
                    if (resultsEl) {
                        resultsEl.innerHTML = `<div class="error-state">Search failed: ${this.escapeHtml(e && e.message ? e.message : String(e))}</div>`;
                    }
                }

                return false;
            }
        });
    },

    async downloadAndOpenKmFile(kbId, fileId, filename) {
        try {
            if (!window.electronAPI || typeof window.electronAPI.downloadAndOpen !== 'function') {
                return;
            }

            const path = `/api/km/${encodeURIComponent(String(kbId))}/files/${encodeURIComponent(String(fileId))}/download`;
            const url = this.resolve(path);
            const result = await window.electronAPI.downloadAndOpen(url, filename || 'file');
            if (result) {
                Toast.error(`Failed to open file: ${result}`);
            }
        } catch (e) {
            console.error('[kmHandlers] downloadAndOpenKmFile failed:', e);
            Toast.error('Failed to open file: ' + (e && e.message ? e.message : String(e)));
        }
    },

    /**
     * Load notes for a specific KB (kmtype=1)
     */
    async loadNotesForKb(kbId, kmId) {
        const noteTree = document.getElementById(`noteTree-${kbId}`);
        if (!noteTree) {
            console.warn(`[kmHandlers] noteTree-${kbId} not found`);
            return;
        }

        // Silent load; do not show loading indicator
        try {
            // Use the search endpoint with kmId parameter (no query means get all notes for this KB)
            const url = this.resolve(`/api/km/notes/search?km_id=${encodeURIComponent(kmId)}`);
            console.log('[kmHandlers] Loading notes from:', url);

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const notes = await response.json();  // API returns array directly
            console.log(`[kmHandlers] Loaded ${notes.length} notes for kmId:`, kmId);

            this.notes[kbId] = Array.isArray(notes) ? notes : [];
            this.renderNoteList(kbId);
            this.bindNoteListEvents(kbId);
            this.renderNoteTagList(kbId);
        } catch (error) {
            console.error('[kmHandlers] Error loading notes:', error);
            noteTree.innerHTML = '<div style="padding: 20px; color: var(--text-muted);">Failed to load notes</div>';
        }
    },

    renderNoteList(kbId) {
        const noteTree = document.getElementById(`noteTree-${kbId}`);
        if (!noteTree) return;

        const noteContainer = document.getElementById(`noteContainer-${kbId}`);

        const notes = this.notes[kbId] || [];

        if (notes.length === 0) {
            if (noteContainer) {
                noteContainer.classList.add('km-list-empty');
            }
            noteTree.innerHTML = `
                <div class="km-empty-state">
                    <p>No notes</p>
                    <p>Click "New Note" to create</p>
                </div>
            `;
            return;
        }

        if (noteContainer) {
            noteContainer.classList.remove('km-list-empty');
        }

        const sortedNotes = [...notes].sort((a, b) => {
            if (a.is_pinned !== b.is_pinned) {
                return a.is_pinned ? -1 : 1;
            }
            return new Date(b.updated_at || b.create_time) - new Date(a.updated_at || a.create_time);
        });

        const html = sortedNotes.map(note => {
            const isPinned = note.is_pinned ? '<span style="color: #ff9800; margin-left: 5px;">📌</span>' : '';
            return `
                <div class="km-tree-item ${this.currentNoteId === note.id ? 'active' : ''}"
                     data-note-id="${note.id}" data-kb-id="${kbId}">
                    <span class="tree-icon">📄</span>
                    <span class="tree-text">${this.escapeHtml(note.title)}${isPinned}</span>
                </div>
            `;
        }).join('');

        noteTree.innerHTML = html;
    },

    bindNoteListEvents(kbId) {
        const noteTree = document.getElementById(`noteTree-${kbId}`);
        if (!noteTree) return;

        noteTree.addEventListener('click', (e) => {
            const item = e.target.closest('.km-tree-item[data-note-id]');
            if (item) {
                const noteId = parseInt(item.dataset.noteId);
                this.openNote(kbId, noteId);
            }
        });

        noteTree.addEventListener('contextmenu', (e) => {
            const item = e.target.closest('.km-tree-item[data-note-id]');
            if (item) {
                e.preventDefault();
                const noteId = parseInt(item.dataset.noteId);
                this.showNoteContextMenu(e, kbId, noteId);
            }
        });

        // Bind search input
        const searchInput = document.getElementById(`kmNoteSearchInput-${kbId}`);
        if (searchInput) {
            searchInput.addEventListener('keypress', async (e) => {
                if (e.key === 'Enter') {
                    const query = searchInput.value.trim();
                    await this.searchNotesInKb(kbId, query);
                }
            });
        }

        const tagSearchInput = document.getElementById(`kmNoteTagSearchInput-${kbId}`);
        if (tagSearchInput) {
            tagSearchInput.addEventListener('keypress', async (e) => {
                if (e.key !== 'Enter') return;
                const query = tagSearchInput.value.trim();
                this.renderNoteTagList(kbId, query);
            });
        }
    },

    renderNoteTagList(kbId, query = '') {
        const container = document.getElementById(`kmNoteTagList-${kbId}`);
        if (!container) return;

        const notes = this.notes[kbId] || [];
        const taggedNotes = (notes || []).filter(n => Array.isArray(n.tags) && n.tags.length > 0);
        if (taggedNotes.length === 0) {
            container.classList.add('km-list-empty');
            container.innerHTML = '<div class="empty-state">No tags</div>';
            return;
        }

        container.classList.remove('km-list-empty');

        const groups = {};
        for (const note of taggedNotes) {
            for (const rawTag of (note.tags || [])) {
                const tag = String(rawTag || '').trim();
                if (!tag) continue;
                if (!groups[tag]) groups[tag] = [];
                groups[tag].push(note);
            }
        }

        const q = String(query || '').trim().toLowerCase();
        if (q) {
            for (const tag of Object.keys(groups)) {
                const items = (groups[tag] || []).filter(note => {
                    const t = String(tag).toLowerCase();
                    const title = String(note && note.title ? note.title : '').toLowerCase();
                    return t.includes(q) || title.includes(q);
                });
                if (items.length === 0) {
                    delete groups[tag];
                } else {
                    groups[tag] = items;
                }
            }
        }

        const tags = Object.keys(groups).sort((a, b) => a.localeCompare(b));
        if (tags.length === 0) {
            container.classList.add('km-list-empty');
            container.innerHTML = '<div class="empty-state">No tags</div>';
            return;
        }

        container.classList.remove('km-list-empty');

        container.innerHTML = tags.map(tag => {
            const items = groups[tag] || [];
            const itemHtml = items.map(note => `
                <div class="km-tree-item km-tag-note-item" data-note-id="${note.id}" data-kb-id="${kbId}" style="padding-left: 16px;">
                    <span class="tree-icon">📄</span>
                    <span class="tree-text">${this.escapeHtml(note.title || 'Untitled Note')}${note.is_pinned ? ' <span style=\"color:#ff9800;\">📌</span>' : ''}</span>
                </div>
            `).join('');

            return `
                <div class="tag-group" style="padding: 6px 8px;">
                    <div class="tag-group-header" style="font-weight: 600; color: var(--text-primary, #333); padding: 4px 0;">${this.escapeHtml(tag)}</div>
                    <div class="tag-group-items">${itemHtml}</div>
                </div>
            `;
        }).join('');

        container.querySelectorAll('.km-tag-note-item').forEach(item => {
            item.addEventListener('click', () => {
                container.querySelectorAll('.km-tag-note-item').forEach(i => i.classList.remove('active'));
                item.classList.add('active');
                const noteId = parseInt(item.dataset.noteId);
                this.openNote(kbId, noteId);
            });

            item.addEventListener('contextmenu', (e) => {
                e.preventDefault();
                const noteId = parseInt(item.dataset.noteId);
                this.showNoteContextMenu(e, kbId, noteId);
            });
        });
    },

    /**
     * Search notes in a KB
     */
    async searchNotesInKb(kbId, query) {
        const noteTree = document.getElementById(`noteTree-${kbId}`);
        if (!noteTree) return;

        // Get string km_id from data attribute
        const kmId = noteTree.dataset.kmId;
        if (!kmId) {
            console.error('No kmId found for noteTree');
            return;
        }

        const loading = Toast.loading(query ? 'Searching notes...' : 'Loading all notes...');

        try {
            let url = this.resolve(`/api/km/notes/search?km_id=${encodeURIComponent(kmId)}`);
            if (query) {
                url += `&query=${encodeURIComponent(query)}`;
            }

            const response = await fetch(url);
            if (!response.ok) {
                throw new Error('Failed to search notes');
            }

            const notes = await response.json();
            this.notes[kbId] = Array.isArray(notes) ? notes : [];
            this.renderNoteList(kbId);
            this.bindNoteListEvents(kbId);
            this.renderNoteTagList(kbId, query);
            loading.close();

            if (query) {
                Toast.success(`Found ${this.notes[kbId].length} notes`);
            }
        } catch (error) {
            console.error('Error searching notes:', error);
            loading.close();
            Toast.error('Failed to search notes');
            noteTree.innerHTML = '<div style="padding: 20px; color: #999;">Failed to search notes</div>';
        }
    },

    async openNote(kbId, noteId) {
        const notes = this.notes[kbId] || [];
        const note = notes.find(n => n.id === noteId);
        if (!note) return;

        const noteContent = document.getElementById('noteContent');
        if (noteContent) {
            let content = note.content || '<p></p>';

            // Normalize content: if it's plain text without HTML tags, wrap it in <p>
            if (content && !content.trim().startsWith('<')) {
                content = `<p>${content}</p>`;
            }

            noteContent.innerHTML = content;
            noteContent.focus();
        }

        this.currentNoteId = noteId;
        this.currentKbId = kbId;

        document.querySelectorAll(`#noteTree-${kbId} .km-tree-item`).forEach(i => i.classList.remove('active'));
        const activeItem = document.querySelector(`#noteTree-${kbId} .km-tree-item[data-note-id="${noteId}"]`);
        if (activeItem) {
            activeItem.classList.add('active');
        }
    },

    createNewNote(kbId) {
        const noteContent = document.getElementById('noteContent');
        if (noteContent) {
            noteContent.innerHTML = '<p></p>';
            noteContent.focus();
        }

        this.currentNoteId = null;
        this.currentKbId = kbId;

        document.querySelectorAll(`#noteTree-${kbId} .km-tree-item`).forEach(item => {
            item.classList.remove('active');
        });
    },

    async saveNote() {
        if (!this.currentKbId || !this.currentKmId) {
            console.error('No KB selected');
            Toast.error('Please select a knowledge base first');
            return;
        }

        const noteContent = document.getElementById('noteContent');
        if (!noteContent) return;

        const content = noteContent.innerHTML.trim();
        if (!content || content === '<p></p>' || content === '<p><br></p>') {
            Toast.warning('Note content cannot be empty');
            return;
        }

        let title = null;
        if (!this.currentNoteId) {
            const tempDiv = document.createElement('div');
            tempDiv.innerHTML = content;
            const plainText = tempDiv.textContent || tempDiv.innerText || '';
            title = plainText.substring(0, 20).trim();
            if (plainText.length > 20) title += '...';
            if (!title) title = 'Untitled Note';
        }

        // const loading = Toast.loading('Saving note...');

        try {
            let savedNote;
            if (this.currentNoteId) {
                // Update existing note
                const response = await fetch(this.resolve(`/api/km/notes/${this.currentNoteId}`), {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ content })
                });
                if (!response.ok) throw new Error('Save failed');
                savedNote = await response.json();
            } else {
                // Create new note - use string km_id
                const response = await fetch(this.resolve('/api/km/notes'), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({
                        title,
                        content,
                        km_id: this.currentKmId,  // Use string km_id
                        tags: []
                    })
                });
                if (!response.ok) throw new Error('Save failed');
                savedNote = await response.json();
                this.currentNoteId = savedNote.id;
            }

            // Reload notes list with both kbId and kmId
            await this.loadNotesForKb(this.currentKbId, this.currentKmId);
            // loading.close();
            Toast.success('Note saved successfully');
        } catch (error) {
            console.error('Save note failed:', error);
            // loading.close();
            Toast.error('Save failed: ' + error.message);
        }
    },

    showNoteContextMenu(event, kbId, noteId) {
        const notes = this.notes[kbId] || [];
        const note = notes.find(n => n.id === noteId);
        if (!note) return;

        const existingMenu = document.querySelector('.note-context-menu');
        if (existingMenu) existingMenu.remove();

        const menu = document.createElement('div');
        menu.className = 'status-context-menu note-context-menu';
        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;
        menu.style.display = 'block';
        menu.style.zIndex = '10001';

        menu.innerHTML = `
            <button type="button" class="context-menu-item" data-action="rename"><span>Rename</span></button>
            <button type="button" class="context-menu-item" data-action="pin"><span>${note.is_pinned ? 'Unpin' : 'Pin'}</span></button>
            <button type="button" class="context-menu-item" data-action="tag"><span>Tag</span></button>
            <button type="button" class="context-menu-item" data-action="delete" style="color: var(--color-danger, #f44336);"><span>Delete</span></button>
        `;

        document.body.appendChild(menu);

        menu.addEventListener('click', async (e) => {
            const item = e.target.closest('.context-menu-item');
            if (!item) return;

            if (item.dataset.action === 'rename') {
                const input = await Toast.prompt('Enter a new title:', {
                    title: 'Rename Note',
                    defaultValue: note.title || '',
                    confirmText: 'Save',
                    cancelText: 'Cancel',
                    type: 'info'
                });
                if (input === null) {
                    menu.remove();
                    return;
                }
                const newTitle = String(input).trim();
                if (!newTitle) {
                    Toast.warning('Title cannot be empty');
                    menu.remove();
                    return;
                }

                try {
                    const response = await fetch(this.resolve(`/api/km/notes/${noteId}`), {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ title: newTitle })
                    });
                    if (!response.ok) throw new Error('Rename failed');
                    await this.loadNotesForKb(kbId, this.currentKmId);
                    this.renderNoteTagList(kbId);
                    Toast.success('Note renamed successfully');
                } catch (error) {
                    console.error('Rename failed:', error);
                    Toast.error('Rename failed: ' + error.message);
                }
                menu.remove();
                return;
            }

            if (item.dataset.action === 'pin') {
                try {
                    const response = await fetch(this.resolve(`/api/km/notes/${noteId}/toggle-pin`), {
                        method: 'POST'
                    });
                    if (!response.ok) throw new Error('Pin toggle failed');
                    await this.loadNotesForKb(kbId, this.currentKmId);
                    this.renderNoteTagList(kbId);
                    Toast.success(note.is_pinned ? 'Note unpinned' : 'Note pinned');
                } catch (error) {
                    console.error('Pin toggle failed:', error);
                    Toast.error('Pin toggle failed: ' + error.message);
                }
                menu.remove();
                return;
            }

            if (item.dataset.action === 'tag') {
                const currentTags = Array.isArray(note.tags) ? note.tags : [];
                const current = currentTags.length > 0 ? currentTags.join(',') : '';
                const input = await Toast.prompt('Enter tags (comma-separated, leave blank to clear):', {
                    title: 'Set Tags',
                    defaultValue: current,
                    confirmText: 'Save',
                    cancelText: 'Cancel',
                    type: 'info'
                });
                if (input === null) {
                    menu.remove();
                    return;
                }

                const raw = String(input).trim();
                const tags = raw
                    ? Array.from(new Set(raw.split(',').map(t => String(t || '').trim()).filter(Boolean)))
                    : [];

                try {
                    const response = await fetch(this.resolve(`/api/km/notes/${noteId}`), {
                        method: 'PUT',
                        headers: { 'Content-Type': 'application/json' },
                        body: JSON.stringify({ tags })
                    });
                    if (!response.ok) throw new Error('Tag update failed');
                    await this.loadNotesForKb(kbId, this.currentKmId);
                    this.renderNoteTagList(kbId);
                    Toast.success(tags.length > 0 ? 'Tags updated successfully' : 'Tags cleared successfully');
                } catch (error) {
                    console.error('Tag update failed:', error);
                    Toast.error('Tag update failed: ' + error.message);
                }
                menu.remove();
                return;
            }

            if (item.dataset.action === 'delete') {
                const confirmed = await Toast.confirm(`Delete note "${note.title}"?`, {
                    title: 'Delete Note',
                    confirmText: 'Delete',
                    cancelText: 'Cancel',
                    type: 'warning'
                });

                if (confirmed) {
                    try {
                        const response = await fetch(this.resolve(`/api/km/notes/${noteId}`), {
                            method: 'DELETE'
                        });
                        if (!response.ok) throw new Error('Delete failed');

                        this.notes[kbId] = this.notes[kbId].filter(n => n.id !== noteId);
                        if (this.currentNoteId === noteId) {
                            const noteContent = document.getElementById('noteContent');
                            if (noteContent) noteContent.innerHTML = '<p></p>';
                            this.currentNoteId = null;
                        }
                        this.renderNoteList(kbId);
                        this.bindNoteListEvents(kbId);
                        this.renderNoteTagList(kbId);
                        Toast.success('Note deleted successfully');
                    } catch (error) {
                        console.error('Delete failed:', error);
                        Toast.error('Delete failed: ' + error.message);
                    }
                }
            }
            menu.remove();
        });

        setTimeout(() => {
            document.addEventListener('click', function closeMenu() {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            });
        }, 0);
    },

    /**
     * Load files for a specific KB (kmtype=0)
     */
    async loadFilesForKb(kbId) {
        const fileTree = document.getElementById(`fileTree-${kbId}`);
        if (!fileTree) return;

        // Silent load; do not show loading indicator
        try {
            const response = await fetch(this.resolve(`/api/km/${kbId}/files`));
            if (!response.ok) throw new Error('Failed to load files');

            const result = await response.json();
            this.files[kbId] = result.data || [];
            this.renderFileList(kbId);
            this.bindFileListEvents(kbId);
        } catch (error) {
            console.error('Error loading files:', error);
            fileTree.innerHTML = '<div style="padding: 20px; color: var(--text-muted);">Failed to load files</div>';
        }
    },

    renderFileList(kbId) {
        const fileTree = document.getElementById(`fileTree-${kbId}`);
        if (!fileTree) return;

        const fileContainer = document.getElementById(`fileContainer-${kbId}`);

        const files = this.files[kbId] || [];

        if (files.length === 0) {
            if (fileContainer) {
                fileContainer.classList.add('km-list-empty');
            }
            fileTree.innerHTML = `
                <div class="km-empty-state" style="padding: 40px 20px;">
                    <svg viewBox="0 0 24 24" width="48" height="48" fill="#ddd">
                        <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
                    </svg>
                    <p>No files</p>
                    <p style="font-size: 12px; color: #aaa; margin-top: 8px;">Click "Add file" to upload documents</p>
                </div>
            `;
            return;
        }

        if (fileContainer) {
            fileContainer.classList.remove('km-list-empty');
        }

        const html = files.map(file => {
            const ext = (file.filename || '').split('.').pop().toLowerCase();
            const iconColor = this.getFileIconColor(ext);
            return `
                <div class="km-file-item" data-file-id="${file.id}" data-kb-id="${kbId}">
                    <div class="km-file-icon" style="background: ${iconColor}15;">
                        <svg viewBox="0 0 24 24" width="24" height="24" fill="${iconColor}">
                            ${this.getFileIconPath(ext)}
                        </svg>
                    </div>
                    <div class="km-file-info">
                        <div class="km-file-name">${this.escapeHtml(file.filename)}</div>
                        <div class="km-file-meta">${file.file_size ? this.formatFileSize(file.file_size) : ''} ${file.create_time ? '• ' + this.formatDate(file.create_time) : ''}</div>
                    </div>
                </div>
            `;
        }).join('');

        fileTree.innerHTML = html;
    },

    getFileIconColor(ext) {
        const colors = {
            'pdf': '#f44336',
            'doc': '#2196f3', 'docx': '#2196f3',
            'xls': '#4caf50', 'xlsx': '#4caf50',
            'ppt': '#ff9800', 'pptx': '#ff9800',
            'txt': '#9e9e9e',
            'md': '#607d8b'
        };
        return colors[ext] || '#1a73e8';
    },

    getFileIconPath(ext) {
        if (['pdf'].includes(ext)) {
            return '<path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm-1 9h-2v2H9v-2H7V9h2V7h2v2h2v2zm-1 5H6v-2h6v2zm2-11V3.5L18.5 9H15z"/>';
        }
        return '<path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>';
    },

    formatFileSize(bytes) {
        if (!bytes) return '';
        const sizes = ['B', 'KB', 'MB', 'GB'];
        const i = Math.floor(Math.log(bytes) / Math.log(1024));
        return (bytes / Math.pow(1024, i)).toFixed(1) + ' ' + sizes[i];
    },

    formatDate(dateStr) {
        if (!dateStr) return '';
        const date = new Date(dateStr);
        return date.toLocaleDateString('en-US');
    },

    bindFileListEvents(kbId) {
        const fileTree = document.getElementById(`fileTree-${kbId}`);
        if (!fileTree) return;
        if (fileTree.dataset.kmFileListBound === '1') return;
        fileTree.dataset.kmFileListBound = '1';

        // Click file item
        fileTree.addEventListener('click', (e) => {
            const item = e.target.closest('.km-file-item[data-file-id]');
            if (item) {
                const now = Date.now();
                const lastOpenAt = Number(item.dataset.lastOpenAt || 0);
                if (now - lastOpenAt < 1000) return;
                item.dataset.lastOpenAt = String(now);
                const fileId = parseInt(item.dataset.fileId);
                const files = this.files[kbId] || [];
                const file = files.find(f => f.id === fileId);
                const filename = file ? file.filename : 'file';
                this.downloadAndOpenKmFile(kbId, fileId, filename);
            }
        });

        fileTree.addEventListener('contextmenu', (e) => {
            const item = e.target.closest('.km-file-item[data-file-id]');
            if (item) {
                e.preventDefault();
                const fileId = parseInt(item.dataset.fileId);
                this.showFileContextMenu(e, kbId, fileId);
            }
        });
    },

    async confirmDeleteFile(kbId, fileId) {
        const files = this.files[kbId] || [];
        const file = files.find(f => f.id === fileId);
        if (!file) return;

        const confirmed = await Toast.confirm(`Want to delete "${file.filename}"?`, {
            title: 'Delete File',
            confirmText: 'Confirm',
            cancelText: 'Cancel',
            type: 'warning'
        });

        if (confirmed) {
            try {
                const response = await fetch(this.resolve(`/api/km/${kbId}/files/${fileId}`), {
                    method: 'DELETE'
                });
                if (!response.ok) throw new Error('Failed to delete file');

                this.files[kbId] = this.files[kbId].filter(f => f.id !== fileId);
                this.renderFileList(kbId);
                this.bindFileListEvents(kbId);
                Toast.success('File deleted successfully');
            } catch (error) {
                console.error('Delete failed:', error);
                Toast.error('Failed to delete file: ' + error.message);
            }
        }
    },

    showFileContextMenu(event, kbId, fileId) {
        const files = this.files[kbId] || [];
        const file = files.find(f => f.id === fileId);
        if (!file) return;

        const existingMenu = document.querySelector('.file-context-menu');
        if (existingMenu) existingMenu.remove();

        const menu = document.createElement('div');
        menu.className = 'status-context-menu file-context-menu';
        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;
        menu.style.display = 'block';
        menu.style.zIndex = '10001';

        menu.innerHTML = `
            <button type="button" class="context-menu-item" data-action="delete" style="color: var(--color-danger, #f44336);">
                <span>Delete</span>
            </button>
        `;

        document.body.appendChild(menu);

        menu.addEventListener('click', async (e) => {
            const item = e.target.closest('.context-menu-item');
            if (!item) return;

            if (item.dataset.action === 'delete') {
                await this.confirmDeleteFile(kbId, fileId);
            }
            menu.remove();
        });

        setTimeout(() => {
            document.addEventListener('click', function closeMenu() {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            });
        }, 0);
    },

    showAddFileDialog(kbId) {
        const input = document.createElement('input');
        input.type = 'file';
        input.accept = '.doc,.docx,.pdf,.ppt,.pptx,.txt,.md,.markdown,.xls,.xlsx';
        input.multiple = true;

        input.addEventListener('change', async (e) => {
            const files = e.target.files;
            if (files.length === 0) return;

            for (const file of files) {
                await this.uploadFile(kbId, file);
            }

            await this.loadFilesForKb(kbId);
        });

        input.click();
    },

    async uploadFile(kbId, file) {
        const loading = Toast.loading(`Uploading ${file.name}...`);
        const formData = new FormData();
        formData.append('file', file);
        formData.append('km_id', kbId);

        try {
            const response = await fetch(this.resolve(`/api/km/${kbId}/files`), {
                method: 'POST',
                body: formData
            });

            if (!response.ok) {
                let message = 'Upload failed';
                try {
                    const data = await response.json();
                    if (data && data.detail) message = data.detail;
                } catch (e) {
                    // ignore
                }
                throw new Error(message);
            }

            loading.close();
            Toast.success(`${file.name} uploaded successfully`);
            console.log('File uploaded:', file.name);
        } catch (error) {
            loading.close();
            console.error('Upload failed:', error);
            Toast.error(`Upload failed for ${file.name}: ${error.message}`);
        }
    },

    async loadKeyValuesForKb(kbId) {
        const kvTree = document.getElementById(`kvTree-${kbId}`);
        if (!kvTree) return;

        // Silent load; do not show loading indicator
        try {
            const response = await fetch(this.resolve(`/api/km/${kbId}/keyvalues`));
            if (!response.ok) throw new Error('Failed to load key-values');

            const result = await response.json();
            this.keyValues[kbId] = result.data || [];
            this.renderKeyValueList(kbId);
            this.bindKeyValueListEvents(kbId);
        } catch (error) {
            console.error('Error loading key-values:', error);
            kvTree.innerHTML = '<div style="padding: 20px; color: var(--text-muted);">Failed to load key-values</div>';
        }
    },

    renderKeyValueList(kbId) {
        const kvTree = document.getElementById(`kvTree-${kbId}`);
        if (!kvTree) return;

        const kvContainer = document.getElementById(`kvContainer-${kbId}`);

        const kvs = this.keyValues[kbId] || [];

        if (kvs.length === 0) {
            if (kvContainer) {
                kvContainer.classList.add('km-list-empty');
            }
            kvTree.innerHTML = `
                <div class="km-empty-state" style="padding: 40px 20px;">
                    <svg viewBox="0 0 24 24" width="48" height="48" fill="#ddd">
                        <path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
                    </svg>
                    <p>No key-value items</p>
                    <p style="font-size: 12px; color: #aaa; margin-top: 8px;">Click "New" to add</p>
                </div>
            `;
            return;
        }

        if (kvContainer) {
            kvContainer.classList.remove('km-list-empty');
        }

        const html = kvs.map(kv => {
            const preview = (kv.value || '').substring(0, 50);
            return `
                <div class="km-kv-item ${this.currentKvId === kv.id ? 'active' : ''}"
                     data-kv-id="${kv.id}" data-kb-id="${kbId}">
                    <div class="km-kv-icon">
                        <svg viewBox="0 0 24 24" fill="currentColor">
                            <path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
                        </svg>
                    </div>
                    <div class="km-kv-info">
                        <div class="km-kv-key">${this.escapeHtml(kv.key)}</div>
                        <div class="km-kv-preview">${this.escapeHtml(preview)}${preview.length < (kv.value || '').length ? '...' : ''}</div>
                    </div>
                </div>
            `;
        }).join('');

        kvTree.innerHTML = html;
    },

    bindKeyValueListEvents(kbId) {
        const kvTree = document.getElementById(`kvTree-${kbId}`);
        if (!kvTree) return;

        kvTree.addEventListener('click', (e) => {
            const item = e.target.closest('.km-kv-item[data-kv-id]');
            if (item) {
                const kvId = parseInt(item.dataset.kvId);
                this.openKeyValue(kbId, kvId);
            }
        });

        kvTree.addEventListener('contextmenu', (e) => {
            const item = e.target.closest('.km-kv-item[data-kv-id]');
            if (item) {
                e.preventDefault();
                const kvId = parseInt(item.dataset.kvId);
                this.showKVContextMenu(e, kbId, kvId);
            }
        });
    },

    openKeyValue(kbId, kvId) {
        const kvs = this.keyValues[kbId] || [];
        const kv = kvs.find(k => k.id === kvId);
        if (!kv) return;

        const kvKeyInput = document.getElementById('kvKeyInput');
        const kvValueInput = document.getElementById('kvValueInput');
        const deleteBtn = document.getElementById('kvDeleteBtn');
        const titleEl = document.getElementById('kvEditorTitle');

        if (kvKeyInput) kvKeyInput.value = kv.key;
        if (kvValueInput) kvValueInput.value = kv.value;
        if (deleteBtn) deleteBtn.style.display = 'inline-flex';
        if (titleEl) {
            titleEl.innerHTML = `
                <div class="dialog-title">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="var(--color-primary)" style="vertical-align: middle; margin-right: 8px;">
                        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                    </svg>
                    Edit key-value item
                </div>
            `;
        }

        this.currentKvId = kvId;
        this.currentKbId = kbId;

        document.querySelectorAll(`#kvTree-${kbId} .km-kv-item`).forEach(i => i.classList.remove('active'));
        const activeItem = document.querySelector(`#kvTree-${kbId} .km-kv-item[data-kv-id="${kvId}"]`);
        if (activeItem) activeItem.classList.add('active');
    },

    showAddKVDialog(kbId) {
        this.currentKbId = kbId;
        this.currentKvId = null;

        this.clearKVForm();

        const keyInput = document.getElementById('kvKeyInput');
        if (keyInput) keyInput.focus();
    },

    async deleteCurrentKV() {
        const kbId = this.currentKbId;
        const kvId = this.currentKvId;

        if (!kbId || !kvId) return;

        const kvs = this.keyValues[kbId] || [];
        const kv = kvs.find(k => k.id === kvId);
        if (!kv) return;

        const confirmed = await Toast.confirm(`Delete key-value "${kv.key}"?`, {
            title: 'Delete Key-Value',
            confirmText: 'Delete',
            cancelText: 'Cancel',
            type: 'warning'
        });

        if (!confirmed) return;

        try {
            const response = await fetch(this.resolve(`/api/km/${kbId}/keyvalues/${kvId}`), {
                method: 'DELETE'
            });
            if (!response.ok) throw new Error('Delete failed');

            this.keyValues[kbId] = (this.keyValues[kbId] || []).filter(k => k.id !== kvId);
            this.currentKvId = null;

            this.clearKVForm();
            this.renderKeyValueList(kbId);
            this.bindKeyValueListEvents(kbId);
            Toast.success('Key-value deleted successfully');
        } catch (error) {
            console.error('Delete failed:', error);
            Toast.error('Delete failed: ' + error.message);
        }
    },

    async saveKeyValue(kbId, kvId, key, value) {
        const loading = Toast.loading('Saving key-value...');

        try {
            let savedKv;
            if (kvId) {
                const response = await fetch(this.resolve(`/api/km/${kbId}/keyvalues/${kvId}`), {
                    method: 'PUT',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key, value })
                });
                if (!response.ok) throw new Error('Save failed');
                const result = await response.json();
                savedKv = result.data;
            } else {
                const response = await fetch(this.resolve(`/api/km/${kbId}/keyvalues`), {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ key, value, km_id: kbId })
                });
                if (!response.ok) throw new Error('Save failed');
                const result = await response.json();
                savedKv = result.data;
            }

            await this.loadKeyValuesForKb(kbId);
            loading.close();
            Toast.success('Key-value saved successfully');
        } catch (error) {
            console.error('Save key-value failed:', error);
            loading.close();
            Toast.error('Save failed: ' + error.message);
        }
    },

    showKVContextMenu(event, kbId, kvId) {
        const kvs = this.keyValues[kbId] || [];
        const kv = kvs.find(k => k.id === kvId);
        if (!kv) return;

        const existingMenu = document.querySelector('.kv-context-menu');
        if (existingMenu) existingMenu.remove();

        const menu = document.createElement('div');
        menu.className = 'status-context-menu kv-context-menu';
        menu.style.left = `${event.clientX}px`;
        menu.style.top = `${event.clientY}px`;
        menu.style.display = 'block';
        menu.style.zIndex = '10001';

        menu.innerHTML = `
            <button type="button" class="context-menu-item" data-action="delete" style="color: var(--color-danger, #f44336);">
                <span>Delete</span>
            </button>
        `;

        document.body.appendChild(menu);

        menu.addEventListener('click', async (e) => {
            const item = e.target.closest('.context-menu-item');
            if (!item) return;

            if (item.dataset.action === 'delete') {
                const confirmed = await Toast.confirm(`Delete key-value "${kv.key}"?`, {
                    title: 'Delete Key-Value',
                    confirmText: 'Delete',
                    cancelText: 'Cancel',
                    type: 'warning'
                });

                if (confirmed) {
                    try {
                        const response = await fetch(this.resolve(`/api/km/${kbId}/keyvalues/${kvId}`), {
                            method: 'DELETE'
                        });
                        if (!response.ok) throw new Error('Delete failed');

                        this.keyValues[kbId] = this.keyValues[kbId].filter(k => k.id !== kvId);
                        if (this.currentKvId === kvId) {
                            const kvKeyInput = document.getElementById('kvKeyInput');
                            const kvValueInput = document.getElementById('kvValueInput');
                            if (kvKeyInput) kvKeyInput.value = '';
                            if (kvValueInput) kvValueInput.value = '';
                            this.currentKvId = null;
                        }
                        this.renderKeyValueList(kbId);
                        this.bindKeyValueListEvents(kbId);
                        Toast.success('Key-value deleted successfully');
                    } catch (error) {
                        console.error('Delete failed:', error);
                        Toast.error('Delete failed: ' + error.message);
                    }
                }
            }
            menu.remove();
        });

        setTimeout(() => {
            document.addEventListener('click', function closeMenu() {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            });
        }, 0);
    },

    escapeHtml(text) {
        const map = {
            '&': '&amp;',
            '<': '&lt;',
            '>': '&gt;',
            '"': '&quot;',
            "'": '&#039;'
        };
        return String(text).replace(/[&<>"']/g, m => map[m]);
    },

    async performVectorSearch(kbId) {
        const searchInput = document.getElementById(`vectorSearchInput-${kbId}`);
        const searchResults = document.getElementById(`searchResults-${kbId}`);

        if (!searchInput || !searchResults) return;

        const query = searchInput.value.trim();
        if (!query) {
            Toast.warning('Please enter a search query');
            return;
        }

        const loading = Toast.loading('Searching...');
        searchResults.innerHTML = '<div class="loading">Searching...</div>';

        try {
            const response = await fetch(this.resolve(`/api/km/${kbId}/search`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ query, top_k: 5 })
            });

            if (!response.ok) throw new Error('Search failed');

            const result = await response.json();
            const results = result.data || [];

            if (results.length === 0) {
                loading.update('No results found');
                setTimeout(() => loading.close(), 2000);
                searchResults.innerHTML = '<div class="empty-state">No results found</div>';
                return;
            }

            const html = results.map((r, idx) => `
                <div class="search-result-item">
                    <div class="result-header">
                        <span class="result-number">${idx + 1}</span>
                        <span class="result-score">Score: ${(r.score || 0).toFixed(3)}</span>
                    </div>
                    <div class="result-content">${this.escapeHtml(r.content || r.text || '')}</div>
                    ${r.metadata ? `<div class="result-metadata">Source: ${this.escapeHtml(r.metadata.filename || r.metadata.source || 'Unknown')}</div>` : ''}
                </div>
            `).join('');

            searchResults.innerHTML = html;
            loading.update(`Found ${results.length} results`);
            setTimeout(() => loading.close(), 2000);
        } catch (error) {
            console.error('Search failed:', error);
            loading.close();
            Toast.error('Search failed: ' + error.message);
            searchResults.innerHTML = `<div class="error-state">Search failed: ${error.message}</div>`;
        }
    },

    saveCurrentKV(kbId) {
        const kvKeyInput = document.getElementById('kvKeyInput');
        const kvValueInput = document.getElementById('kvValueInput');

        if (!kvKeyInput || !kvValueInput) return;

        const key = kvKeyInput.value.trim();
        const value = kvValueInput.value.trim();

        if (!key) {
            Toast.warning('Key cannot be empty');
            return;
        }

        this.saveKeyValue(kbId, this.currentKvId, key, value);
    },

    clearKVForm() {
        const kvKeyInput = document.getElementById('kvKeyInput');
        const kvValueInput = document.getElementById('kvValueInput');
        const deleteBtn = document.getElementById('kvDeleteBtn');
        const titleEl = document.getElementById('kvEditorTitle');

        if (kvKeyInput) kvKeyInput.value = '';
        if (kvValueInput) kvValueInput.value = '';
        if (deleteBtn) deleteBtn.style.display = 'none';
        if (titleEl) {
            titleEl.innerHTML = `
                <div class="dialog-title">
                    <svg viewBox="0 0 24 24" width="20" height="20" fill="var(--color-primary)" style="vertical-align: middle; margin-right: 8px;">
                        <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                    </svg>
                    New key-value item
                </div>
            `;
        }

        this.currentKvId = null;

        if (this.currentKbId) {
            document.querySelectorAll(`#kvTree-${this.currentKbId} .km-kv-item`).forEach(i => i.classList.remove('active'));
        }
    }
};

// Export to global
if (typeof window !== 'undefined') {
    window.kmHandlers = kmHandlers;
}

export default kmHandlers;
