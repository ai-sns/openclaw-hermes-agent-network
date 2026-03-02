/**
 * KM Page - Key-Value Editor (kmtype=2) - optimized version
 */

const KMKeyValuePage = {
    render(kbId) {
        return `
            <div class="km-page-layout km-kv-page-layout">
                <!-- Right: KV editor -->
                <div class="km-kv-editor-panel">
                    <div class="km-kv-editor-header">
                        <h3 id="kvEditorTitle">
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="var(--color-primary)" style="vertical-align: middle; margin-right: 8px;">
                                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                            </svg>
                            New Key-Value
                        </h3>
                        <div style="display: flex; gap: 8px;">
                            <span id="kvEditStatus" style="font-size: 12px; color: var(--text-muted); display: none;">
                                <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                                    <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
                                </svg>
                                Saved
                            </span>
                        </div>
                    </div>
                    <div class="km-kv-form">
                        <div class="form-group">
                            <label>
                                <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                                    <path d="M12.65 10C11.83 7.67 9.61 6 7 6c-3.31 0-6 2.69-6 6s2.69 6 6 6c2.61 0 4.83-1.67 5.65-4H17v4h4v-4h2v-4H12.65zM7 14c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2z"/>
                                </svg>
                                Key
                            </label>
                            <input type="text" id="kvKeyInput" class="form-input" placeholder="Enter a unique identifier key, e.g., api_key, config_name">
                        </div>
                        <div class="form-group" style="flex: 1; display: flex; flex-direction: column;">
                            <label>
                                <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                                    <path d="M14 2H6c-1.1 0-2 .9-2 2v16c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V8l-6-6zm4 18H6V4h7v5h5v11z"/>
                                </svg>
                                Value
                            </label>
                            <textarea id="kvValueInput" class="form-textarea" placeholder="Enter the value content. Text, JSON, and other formats are supported...&#10;&#10;Example:&#10;{&#10;  &quot;name&quot;: &quot;example&quot;,&#10;  &quot;version&quot;: &quot;1.0.0&quot;&#10;}"></textarea>
                        </div>
                        <div class="form-actions">
                            <button class="btn-primary" id="kvSaveBtn-${kbId}">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M17 3H5c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h14c1.1 0 2-.9 2-2V7l-4-4zm-5 16c-1.66 0-3-1.34-3-3s1.34-3 3-3 3 1.34 3 3-1.34 3-3 3zm3-10H5V5h10v4z"/>
                                </svg>
                                Save
                            </button>
                            <button class="btn-secondary" id="kvClearBtn">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                </svg>
                                Clear
                            </button>
                            <button class="btn-danger" id="kvDeleteBtn" style="display: none; margin-left: auto;">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M6 19c0 1.1.9 2 2 2h8c1.1 0 2-.9 2-2V7H6v12zM19 4h-3.5l-1-1h-5l-1 1H5v2h14V4z"/>
                                </svg>
                                Delete
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    init() {
        this.bindFormEvents();
        console.log('[KMKeyValuePage] Initialized');
    },

    bindFormEvents() {
        // Save button
        document.querySelectorAll('[id^="kvSaveBtn-"]').forEach(btn => {
            const kbId = btn.id.replace('kvSaveBtn-', '');
            btn.addEventListener('click', () => {
                if (window.kmHandlers) {
                    window.kmHandlers.saveCurrentKV(parseInt(kbId));
                }
            });
        });

        // Clear button
        const clearBtn = document.getElementById('kvClearBtn');
        if (clearBtn) {
            clearBtn.addEventListener('click', () => {
                if (window.kmHandlers) {
                    window.kmHandlers.clearKVForm();
                    // Update title
                    const titleEl = document.getElementById('kvEditorTitle');
                    if (titleEl) {
                        titleEl.innerHTML = `
                            <svg viewBox="0 0 24 24" width="20" height="20" fill="var(--color-primary)" style="vertical-align: middle; margin-right: 8px;">
                                <path d="M3 17.25V21h3.75L17.81 9.94l-3.75-3.75L3 17.25zM20.71 7.04c.39-.39.39-1.02 0-1.41l-2.34-2.34c-.39-.39-1.02-.39-1.41 0l-1.83 1.83 3.75 3.75 1.83-1.83z"/>
                            </svg>
                            New Key-Value
                        `;
                    }
                    // Hide delete button
                    const deleteBtn = document.getElementById('kvDeleteBtn');
                    if (deleteBtn) deleteBtn.style.display = 'none';
                }
            });
        }

        // Delete button
        const deleteBtn = document.getElementById('kvDeleteBtn');
        if (deleteBtn) {
            deleteBtn.addEventListener('click', () => {
                if (window.kmHandlers && window.kmHandlers.currentKvId) {
                    window.kmHandlers.deleteCurrentKV();
                }
            });
        }

        // Ctrl+S to save
        const kvValueInput = document.getElementById('kvValueInput');
        if (kvValueInput) {
            kvValueInput.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 's') {
                    e.preventDefault();
                    const saveBtn = document.querySelector('[id^="kvSaveBtn-"]');
                    if (saveBtn && window.kmHandlers) {
                        const kbId = saveBtn.id.replace('kvSaveBtn-', '');
                        window.kmHandlers.saveCurrentKV(parseInt(kbId));
                    }
                }
            });
        }

        // Ctrl+S also supported in Key input
        const kvKeyInput = document.getElementById('kvKeyInput');
        if (kvKeyInput) {
            kvKeyInput.addEventListener('keydown', (e) => {
                if (e.ctrlKey && e.key === 's') {
                    e.preventDefault();
                    const saveBtn = document.querySelector('[id^="kvSaveBtn-"]');
                    if (saveBtn && window.kmHandlers) {
                        const kbId = saveBtn.id.replace('kvSaveBtn-', '');
                        window.kmHandlers.saveCurrentKV(parseInt(kbId));
                    }
                }
            });
        }
    },

    destroy() {
        // Clean up event listeners if needed
    }
};

export default KMKeyValuePage;
