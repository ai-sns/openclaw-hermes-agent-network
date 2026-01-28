/**
 * Web Handlers - 事件处理
 */

const webHandlers = {
    webPage: null,
    webSidebar: null,

    init(webPage, webSidebar) {
        this.webPage = webPage;
        this.webSidebar = webSidebar;
        this.bindEvents();
    },

    bindEvents() {
        // Section header click - toggle expand/collapse
        document.addEventListener('click', (e) => {
            const header = e.target.closest('.web-section-header');
            if (header) {
                this.toggleSection(header);
            }
        });

        // Icon click - load URL in BrowserView
        document.addEventListener('click', (e) => {
            const iconItem = e.target.closest('.web-icon-item');
            if (iconItem && !e.ctrlKey && !e.metaKey && e.button === 0) {
                const url = iconItem.dataset.url;
                if (url) {
                    this.webPage.loadUrl(url);
                }
            }
        });

        // Icon right-click - show context menu
        document.addEventListener('contextmenu', (e) => {
            const iconItem = e.target.closest('.web-icon-item');
            if (iconItem) {
                e.preventDefault();
                this.showContextMenu(e, iconItem);
            }
        });

        // Add/Manage buttons
        document.addEventListener('click', (e) => {
            if (e.target.closest('#addLLMBtn')) {
                this.showAddModal('LLM');
            } else if (e.target.closest('#manageLLMBtn')) {
                this.showManageModal('LLM');
            } else if (e.target.closest('#addToolBtn')) {
                this.showAddModal('Tool');
            } else if (e.target.closest('#manageToolBtn')) {
                this.showManageModal('Tool');
            }
        });

        // Search functionality
        document.addEventListener('input', (e) => {
            if (e.target.id === 'llmSearchInput') {
                this.filterIcons('llm', e.target.value);
            } else if (e.target.id === 'toolSearchInput') {
                this.filterIcons('tool', e.target.value);
            }
        });
    },

    toggleSection(header) {
        const section = header.closest('.web-section');
        const sectionType = header.dataset.section;

        if (sectionType === 'llm') {
            this.webSidebar.llmExpanded = !this.webSidebar.llmExpanded;
            this.webSidebar.toolExpanded = !this.webSidebar.llmExpanded;
        } else if (sectionType === 'tool') {
            this.webSidebar.toolExpanded = !this.webSidebar.toolExpanded;
            this.webSidebar.llmExpanded = !this.webSidebar.toolExpanded;
        }

        // Re-render sidebar - only update the web module's sidebar container
        const sidebar = document.getElementById('sidebar-web');
        if (sidebar) {
            sidebar.innerHTML = this.webSidebar.render();
        }
    },

    showContextMenu(e, iconItem) {
        const url = iconItem.dataset.url;
        const name = iconItem.dataset.name;

        // Remove existing context menu
        const existingMenu = document.querySelector('.web-context-menu');
        if (existingMenu) {
            existingMenu.remove();
        }

        // Create context menu
        const menu = document.createElement('div');
        menu.className = 'web-context-menu';
        menu.style.left = e.pageX + 'px';
        menu.style.top = e.pageY + 'px';
        menu.innerHTML = `
            <div class="web-context-menu-item" data-action="open-browser">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <path d="M18 13v6a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2V8a2 2 0 0 1 2-2h6"/>
                    <polyline points="15 3 21 3 21 9"/>
                    <line x1="10" y1="14" x2="21" y2="3"/>
                </svg>
                <span>Open in Default Browser</span>
            </div>
            <div class="web-context-menu-item" data-action="copy-url">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"/>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"/>
                </svg>
                <span>Copy URL</span>
            </div>
        `;

        document.body.appendChild(menu);

        // Handle menu item clicks
        menu.addEventListener('click', (e) => {
            const item = e.target.closest('.web-context-menu-item');
            if (item) {
                const action = item.dataset.action;
                if (action === 'open-browser') {
                    this.webPage.openInBrowser(url);
                } else if (action === 'copy-url') {
                    navigator.clipboard.writeText(url).then(() => {
                        console.log('URL copied to clipboard');
                    });
                }
                menu.remove();
            }
        });

        // Close menu on outside click
        setTimeout(() => {
            document.addEventListener('click', function closeMenu() {
                menu.remove();
                document.removeEventListener('click', closeMenu);
            });
        }, 0);
    },

    filterIcons(type, searchTerm) {
        const section = document.querySelector(`.web-section[data-section="${type}"]`);
        if (!section) return;

        const icons = section.querySelectorAll('.web-icon-item');
        const term = searchTerm.toLowerCase();

        icons.forEach(icon => {
            const name = icon.dataset.name.toLowerCase();
            icon.style.display = name.includes(term) ? '' : 'none';
        });
    },

    showAddModal(type) {
        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        Modal.show({
            title: `Add ${type} Service`,
            content: `
                <div class="form-group">
                    <label>Service Name</label>
                    <input type="text" class="form-input" id="serviceName" placeholder="e.g., ChatGPT">
                </div>
                <div class="form-group">
                    <label>Service URL</label>
                    <input type="url" class="form-input" id="serviceUrl" placeholder="https://...">
                </div>
                <div class="form-group">
                    <label>Description (Optional)</label>
                    <textarea class="form-input" id="serviceDesc" rows="3"></textarea>
                </div>
            `,
            confirmText: 'Add',
            onConfirm: async () => {
                const name = document.getElementById('serviceName')?.value;
                const url = document.getElementById('serviceUrl')?.value;
                const description = document.getElementById('serviceDesc')?.value;

                if (!name || !url) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please fill in required fields');
                    }
                    return false;
                }

                try {
                    if (window.api) {
                        await window.api.post('/api/system/web-mng', {
                            name,
                            url,
                            type,
                            description,
                            filename: 'openai.png'
                        });

                        await this.webSidebar.loadData();
                        const sidebar = document.getElementById('sidebar-web');
                        if (sidebar) {
                            sidebar.innerHTML = this.webSidebar.render();
                        }

                        if (typeof Notification !== 'undefined') {
                            Notification.success(`${type} service added successfully`);
                        }
                    }
                } catch (error) {
                    console.error('Failed to add service:', error);
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Failed to add service');
                    }
                }
            }
        });
    },

    showManageModal(type) {
        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        const data = type === 'LLM' ? this.webSidebar.llmData : this.webSidebar.toolData;
        const items = data.map(item => `
            <div class="manage-item">
                <span class="manage-item-name">${item.name}</span>
                <div class="manage-item-actions">
                    <button class="btn-sm" data-action="edit" data-id="${item.id}">Edit</button>
                    <button class="btn-sm btn-danger" data-action="delete" data-id="${item.id}">Delete</button>
                </div>
            </div>
        `).join('');

        Modal.show({
            title: `Manage ${type} Services`,
            content: `
                <div class="manage-list">
                    ${items || '<div class="manage-empty">No services available</div>'}
                </div>
            `,
            showCancel: false,
            confirmText: 'Close'
        });
    },

    destroy() {
        // Cleanup if needed
    }
};

export default webHandlers;
