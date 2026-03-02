export class SNSPluginDialog {
    constructor(options = {}) {
        this.onLoad = typeof options.onLoad === 'function' ? options.onLoad : null;
        this.onDelete = typeof options.onDelete === 'function' ? options.onDelete : null;
        this._toolsManager = null;
        this._plugins = [];
    }

    async _getApiBaseUrl() {
        try {
            if (window.electronAPI && typeof window.electronAPI.getApiUrl === 'function') {
                const raw = await window.electronAPI.getApiUrl();
                return raw ? String(raw).replace(/\/+$/, '') : '';
            }
        } catch (e) {
        }

        try {
            const raw = (window.appConfig && window.appConfig.agent_server) || '';
            if (raw) return String(raw).replace(/\/+$/, '');
        } catch (e) {
        }

        try {
            if (typeof window.resolveAgentServerUrl === 'function') {
                const u = new URL(window.resolveAgentServerUrl('/'));
                return u.origin;
            }
        } catch (e) {
        }

        return '';
    }

    async _fetchRendererPlugins() {
        const apiBaseUrl = await this._getApiBaseUrl();
        if (!apiBaseUrl) return [];

        try {
            const resp = await fetch(`${apiBaseUrl}/api/tools/plugins?used_in_sns=true`);
            if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
            const data = await resp.json();
            const list = Array.isArray(data) ? data : [];
            return list.filter(p => {
                const pluginType = (p && p.plugin_type) ? String(p.plugin_type) : '';
                return pluginType.toLowerCase() === 'renderer';
            });
        } catch (e) {
            return [];
        }
    }

    async _deletePlugin(pluginId) {
        const apiBaseUrl = await this._getApiBaseUrl();
        if (!apiBaseUrl) {
            if (window.Notification && typeof window.Notification.error === 'function') {
                window.Notification.error('API base URL not available');
            }
            return false;
        }

        const id = pluginId ? String(pluginId).trim() : '';
        if (!id) return false;

        try {
            const resp = await fetch(`${apiBaseUrl}/api/tools/plugins/${encodeURIComponent(id)}`, {
                method: 'DELETE'
            });
            if (!resp.ok) {
                const text = await resp.text();
                throw new Error(text || `HTTP ${resp.status}`);
            }
            if (window.Notification && typeof window.Notification.success === 'function') {
                window.Notification.success('Plugin deleted');
            }
            return true;
        } catch (e) {
            if (window.Notification && typeof window.Notification.error === 'function') {
                window.Notification.error(`Delete failed: ${e && e.message ? e.message : String(e)}`);
            }
            return false;
        }
    }

    async open() {
        if (typeof Modal === 'undefined') {
            if (window.Notification && typeof window.Notification.error === 'function') {
                window.Notification.error('Modal component not loaded');
            }
            return;
        }

        const content = `
            <div style="display:flex; flex-direction:column; gap:12px;">
                <div class="form-group">
                    <label>Select plugin</label>
                    <select class="form-input" id="snsPluginSelect">
                        <option value="">Loading...</option>
                    </select>
                </div>
                <div class="form-group">
                    <label>Description</label>
                    <p style="font-size: 12px; color: var(--text-secondary, #666);" id="snsPluginDescription">Select a plugin to view details</p>
                </div>
                <div style="display:flex; gap:8px; align-items:center; flex-wrap:wrap;">
                    <button type="button" class="btn btn-secondary" id="snsPluginRefreshBtn">Refresh</button>
                    <button type="button" class="btn btn-secondary" id="snsPluginImportBtn">Import zip</button>
                    <button type="button" class="btn btn-secondary" id="snsPluginDeleteBtn" disabled>Delete</button>
                    <input type="file" id="snsPluginImportFile" accept=".zip" style="display:none" />
                </div>
            </div>
        `;

        Modal.show({
            title: 'SNS Plugins',
            content,
            confirmText: 'Load',
            showCancel: true,
            width: '560px',
            onOpen: async () => {
                await this._loadPluginsIntoUi();
                this._bindUiEvents();
            },
            onConfirm: async () => {
                const select = document.getElementById('snsPluginSelect');
                const id = select ? String(select.value || '').trim() : '';
                if (!id) {
                    if (window.Notification && typeof window.Notification.error === 'function') {
                        window.Notification.error('Please select a plugin');
                    }
                    return false;
                }

                const plugin = this._plugins.find(p => String(p.plugin_id) === id);
                if (!plugin) {
                    if (window.Notification && typeof window.Notification.error === 'function') {
                        window.Notification.error('Plugin not found');
                    }
                    return false;
                }

                if (this.onLoad) {
                    await this.onLoad(plugin);
                }
            }
        });
    }

    _bindUiEvents() {
        const select = document.getElementById('snsPluginSelect');
        const desc = document.getElementById('snsPluginDescription');
        const refreshBtn = document.getElementById('snsPluginRefreshBtn');
        const importBtn = document.getElementById('snsPluginImportBtn');
        const deleteBtn = document.getElementById('snsPluginDeleteBtn');
        const importFile = document.getElementById('snsPluginImportFile');

        if (select && desc) {
            select.addEventListener('change', () => {
                const id = String(select.value || '').trim();
                const plugin = this._plugins.find(p => String(p.plugin_id) === id);
                if (!plugin) {
                    desc.textContent = 'Select a plugin to view details';
                    if (deleteBtn) deleteBtn.disabled = true;
                    return;
                }
                const name = plugin.name ? String(plugin.name) : 'Unnamed plugin';
                const version = plugin.version ? String(plugin.version) : '';
                const detail = plugin.description ? String(plugin.description) : '';
                desc.textContent = `${name}${version ? ` v${version}` : ''}${detail ? ` - ${detail}` : ''}`;

                if (deleteBtn) deleteBtn.disabled = false;
            });
        }

        if (refreshBtn) {
            refreshBtn.addEventListener('click', async () => {
                await this._loadPluginsIntoUi();
            });
        }

        if (importBtn && importFile) {
            importBtn.addEventListener('click', () => {
                try {
                    importFile.value = '';
                } catch (e) {
                }
                importFile.click();
            });

            importFile.addEventListener('change', async () => {
                const file = importFile.files && importFile.files[0] ? importFile.files[0] : null;
                if (!file) return;
                await this._importZip(file);
                await this._loadPluginsIntoUi();
            });
        }

        if (deleteBtn) {
            deleteBtn.addEventListener('click', async () => {
                const id = select ? String(select.value || '').trim() : '';
                if (!id) return;

                const ok = window.confirm('Delete selected plugin?');
                if (!ok) return;

                const deleted = await this._deletePlugin(id);
                if (deleted) {
                    try {
                        if (this.onDelete) {
                            await this.onDelete(id);
                        }
                    } catch (e) {
                    }
                    await this._loadPluginsIntoUi();
                }
            });
        }
    }

    async _loadPluginsIntoUi() {
        const select = document.getElementById('snsPluginSelect');
        const desc = document.getElementById('snsPluginDescription');
        if (!select) return;

        select.innerHTML = '<option value="">Loading...</option>';
        if (desc) desc.textContent = 'Select a plugin to view details';

        const plugins = await this._fetchRendererPlugins();
        this._plugins = plugins;

        if (!plugins.length) {
            select.innerHTML = '<option value="">No renderer plugins found</option>';
            return;
        }

        select.innerHTML = '<option value="">Please select a plugin...</option>';
        for (const p of plugins) {
            const opt = document.createElement('option');
            opt.value = String(p.plugin_id);
            const name = p.name ? String(p.name) : String(p.plugin_id);
            opt.textContent = name;
            select.appendChild(opt);
        }
    }

    async _importZip(file) {
        const apiBaseUrl = await this._getApiBaseUrl();
        if (!apiBaseUrl) {
            if (window.Notification && typeof window.Notification.error === 'function') {
                window.Notification.error('API base URL not available');
            }
            return;
        }

        try {
            const form = new FormData();
            form.append('file', file, file.name || 'plugin.zip');

            const resp = await fetch(`${apiBaseUrl}/api/tools/plugins/import?used_in_sns=true`, {
                method: 'POST',
                body: form
            });

            if (!resp.ok) {
                const text = await resp.text();
                throw new Error(text || `HTTP ${resp.status}`);
            }

            if (window.Notification && typeof window.Notification.success === 'function') {
                window.Notification.success('Plugin imported');
            }
        } catch (e) {
            if (window.Notification && typeof window.Notification.error === 'function') {
                window.Notification.error(`Import failed: ${e && e.message ? e.message : String(e)}`);
            }
        }
    }
}
