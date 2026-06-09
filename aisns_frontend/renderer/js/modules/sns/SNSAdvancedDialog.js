/**
 * SNS Advanced Configuration Dialog
 */

export class SNSAdvancedDialog {
    constructor() {
        this.dialog = null;
        this.selectedAvatar3D = null;
        this.selectedAvatar3DMode = null;
        this.uploadedAvatar = null;
        this.uploadedAvatarMeta = null;
        this.existingConfig = null;
        this.existingAvatar3DName = null;
        this.existingAvatar3DCustomUrl = null;
        this.existingAgentId = null;
        this.existingUserInfo = null;
    }

    _resolveAvatarSrc(avatarValue) {
        const value = String(avatarValue || '').trim();
        if (!value) return '';

        if (value.startsWith('data:')) {
            return value;
        }

        if (this._isWebUrl(value) || value.startsWith('/')) {
            return this.resolve(value);
        }

        return this.resolve(`/images/avatars/${value}`);
    }

    clearInlineMessage() {
        const alertBox = this._q('#snsAdvancedAlert');
        if (!alertBox) {
            return;
        }
        alertBox.style.display = 'none';
        alertBox.textContent = '';
        alertBox.classList.remove('inline-alert-error', 'inline-alert-success');
    }

    showInlineMessage(message, type = 'error', options = {}) {
        const alertBox = this._q('#snsAdvancedAlert');
        if (!alertBox) {
            return;
        }

        const targetTab = options && options.tab ? String(options.tab) : '';
        const focusEl = options && options.focusEl ? options.focusEl : null;
        if (targetTab) {
            this.setActiveTab(targetTab);
        }

        if (targetTab) {
            requestAnimationFrame(() => {
                try {
                    this.setActiveTab(targetTab);
                } catch (e) {
                }
            });
        }

        alertBox.textContent = message;
        alertBox.classList.remove('inline-alert-error', 'inline-alert-success');
        alertBox.classList.add(type === 'success' ? 'inline-alert-success' : 'inline-alert-error');
        alertBox.style.display = 'block';

        requestAnimationFrame(() => {
            try {
                if (focusEl && typeof focusEl.focus === 'function') {
                    try {
                        focusEl.focus({ preventScroll: true });
                    } catch (e) {
                        focusEl.focus();
                    }
                }

                const modalBody = this._q('.modal-body');
                if (modalBody && modalBody.scrollHeight > modalBody.clientHeight) {
                    modalBody.scrollTop = modalBody.scrollHeight;
                }
                if (typeof alertBox.scrollIntoView === 'function') {
                    alertBox.scrollIntoView({ block: 'end' });
                }
            } catch (e) {
            }
        });
    }

    setActiveTab(tabKey) {
        const key = String(tabKey || '').trim();
        if (!key) {
            return;
        }

        const modalTabs = this._qa('.modal-tab');
        modalTabs.forEach(t => {
            const isActive = t && t.dataset && t.dataset.tab === key;
            if (isActive) t.classList.add('active');
            else t.classList.remove('active');
        });

        const tabContents = this._qa('.tab-content');
        tabContents.forEach(content => {
            content.style.display = 'none';
            content.classList.remove('active');
        });

        const targetContent = this._q(`#${key}Tab`);
        if (targetContent) {
            targetContent.style.display = 'block';
            targetContent.classList.add('active');
        }
    }

    _isDialogAlive() {
        return !!(this.dialog && typeof document !== 'undefined' && document.body && document.body.contains(this.dialog));
    }

    _q(selector) {
        return this.dialog ? this.dialog.querySelector(selector) : null;
    }

    _qa(selector) {
        return this.dialog ? Array.from(this.dialog.querySelectorAll(selector)) : [];
    }

    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    }

    _isWebUrl(url) {
        const u = String(url || '').trim();
        return u.startsWith('http://') || u.startsWith('https://') || u.startsWith('//');
    }

    _setCustomAvatar3dInputVisible(visible) {
        const container = this._q('#avatar3dCustomContainer');
        if (!container) return;
        container.style.display = visible ? 'block' : 'none';
    }

    _getCustomAvatar3dUrlValue() {
        const input = this._q('#avatar3dCustomUrl');
        return input ? String(input.value || '').trim() : '';
    }

    _getEffectiveAvatar3dValue() {
        if (this.selectedAvatar3DMode === 'custom') {
            return this._getCustomAvatar3dUrlValue();
        }

        if (this.selectedAvatar3D) {
            const name = String(this.selectedAvatar3D.name || '');
            return name.toLowerCase().endsWith('.glb') ? name : `${name}.glb`;
        }

        return (this.existingConfig && this.existingConfig.avatar3d)
            ? String(this.existingConfig.avatar3d)
            : '';
    }

    _validateCustomAvatar3dUrl(urlValue) {
        const url = String(urlValue || '').trim();
        if (!url) {
            return 'Please enter a URL for your custom 3D avatar.';
        }
        if (!this._isWebUrl(url)) {
            return 'The custom 3D avatar URL must start with http://, https://, or //.';
        }

        const cleaned = url.split('#')[0].split('?')[0];
        if (!cleaned.toLowerCase().endsWith('.glb')) {
            return 'The custom 3D avatar URL must point to a .glb file.';
        }
        return null;
    }

    async show() {
        const existing = document.getElementById('snsAdvancedDialog');
        if (existing) {
            try {
                existing.remove();
            } catch (e) {
            }
        }

        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsAdvancedDialog">
                <div class="modal-dialog" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>Advanced Configuration</h3>
                        <button class="modal-close" onclick="document.getElementById('snsAdvancedDialog').remove()">&times;</button>
                    </div>
                    <div class="modal-tabs">
                        <button class="modal-tab active" data-tab="avatar">Avatar Settings</button>
                        <button class="modal-tab" data-tab="userinfo">Identity</button>
                        <button class="modal-tab" data-tab="xmpp">XMPP</button>
                        <button class="modal-tab" data-tab="security">Security</button>
                    </div>
                    <div class="modal-body">
                        <!-- Avatar Config Tab -->
                        <div class="tab-content active" id="avatarTab">
                            <div class="avatar-config-container">
                                <!-- Upload Avatar Section -->
                                <div class="avatar-section">
                                    <h4>Upload Avatar</h4>
                                    <div class="avatar-upload-area">
                                        <input type="file" id="avatarFileInput" accept="image/*" style="display: none;">
                                        <div class="avatar-preview" id="avatarPreview" role="button" tabindex="0" aria-label="Upload avatar preview">
                                            <img id="avatarPreviewImg" class="avatar-preview-img" src="" alt="Avatar preview">
                                            <div id="avatarPlaceholder" class="avatar-placeholder">

                                                <span class="avatar-placeholder-title">Upload</span>
                                            </div>
                                        </div>
                                        <div class="avatar-upload-controls">
                                            <div class="avatar-nationid" id="avatarNationIdText">Nation ID: -</div>
                                            <button class="btn btn-primary" id="uploadAvatarBtn">Choose Image</button>
                                        </div>
                                    </div>
                                </div>

                                <!-- 3D Avatar Selection Section -->
                                <div class="avatar-section">
                                    <div class="avatar-section-header" style="display: flex; align-items: baseline; gap: 2ch;">
                                        <h4 style="margin: 0;">Choose 3D Avatar</h4>
                                        <a href="#" id="avatar3dLicensesLink" class="avatar3d-licenses-link" style="font-size: 12px;">Licenses</a>
                                    </div>
                                    <div class="avatar3d-grid" id="avatar3dGrid">
                                        <div class="loading">Loading...</div>
                                    </div>
                                    <div class="avatar3d-custom-container" id="avatar3dCustomContainer" style="display: none;">
                                        <input type="text" id="avatar3dCustomUrl" class="form-control" placeholder="Enter a .glb URL (https://...)" autocomplete="off">
                                        <div class="avatar3d-custom-hint">The URL must allow cross-origin requests (CORS). Consider hosting it via a CDN such as Cloudflare or jsDelivr.</div>
                                    </div>
                                    <div class="avatar3d-face-customize-hint">You can customize your own 3D avatar using your face photo. <a href="#" id="avatar3dFaceDetailLink">detail</a></div>
                                </div>
                            </div>
                        </div>

                        <!-- User Info Tab -->
                        <div class="tab-content" id="userinfoTab" style="display: none;">
                            <div class="avatar-config-container">
                                <div class="avatar-section">
                                    <h4>Basic Information</h4>
                                    <div class="user-info-form">
                                        <div class="form-group">
                                            <label for="userNickname">Nickname<span class="required-asterisk">*</span></label>
                                            <input type="text" id="userNickname" class="form-control" placeholder="Enter a nickname">
                                        </div>
                                        <div class="form-group">
                                            <label for="userSign">Bio<span class="required-asterisk">*</span></label>
                                            <input type="text" id="userSign" class="form-control" placeholder="Introduce yourself">
                                        </div>
                                        <div class="form-group">
                                            <label for="userSnsUrl">SNS URL</label>
                                            <input type="text" id="userSnsUrl" class="form-control" placeholder="X.com URL or other social links(to learn more about you)">
                                        </div>
                                        <div class="form-group">
                                            <label for="userAgentId">Select an agent to run on the map<span class="required-asterisk">*</span></label>
                                            <select id="userAgentId" class="form-control">
                                                <option value="">Select an agent</option>
                                            </select>
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="tab-content" id="xmppTab" style="display: none;">
                            <div class="avatar-config-container">
                                <div class="avatar-section">
                                    <h4>XMPP</h4>
                                    <div class="user-info-form">
                                        <div class="form-group">
                                            <label for="xmppAccount">Account<span class="required-asterisk">*</span></label>
                                            <input type="text" id="xmppAccount" class="form-control" placeholder="Enter the XMPP account">
                                        </div>
                                        <div class="form-group">
                                            <label for="xmppPassword">Password</label>
                                            <input type="password" id="xmppPassword" class="form-control" placeholder="Enter the XMPP password">
                                        </div>
                                    </div>
                                </div>
                                <div class="avatar-section" style="margin-top: 16px;">
                                    <h4>Ad-hoc Commands</h4>
                                    <div id="a2aCommandList" style="margin-bottom: 8px;"></div>
                                    <div style="display: flex; gap: 8px; align-items: center;">
                                        <button type="button" class="btn btn-sm btn-outline-primary" id="a2aAddCommandBtn" style="font-size: 12px;">+ Add Command</button>
                                        <button type="button" class="btn btn-sm btn-outline-secondary" id="a2aReloadAgentCardBtn" style="font-size: 12px;" title="Re-fetch the agent card from the a2aserver and republish via PEP">Reload Agent Card</button>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="tab-content" id="securityTab" style="display: none;">
                            <div class="avatar-config-container">
                                <div class="avatar-section">
                                    <h4>Security</h4>
                                    <div class="user-info-form">
                                        <div class="avatar-nationid" id="securityNationIdText">Nation ID: -</div>
                                        <div class="form-group" style="margin-top: 10px;">
                                            <label for="newNationPassword">New Nation Password</label>
                                            <input type="password" id="newNationPassword" class="form-control" placeholder="Enter the new nation password">
                                        </div>
                                        <div class="form-group">
                                            <label for="retypeNationPassword">Retype New Nation Password</label>
                                            <input type="password" id="retypeNationPassword" class="form-control" placeholder="Retype the new nation password">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <div class="dialog-inline-alert" id="snsAdvancedAlert" style="display: none;"></div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="document.getElementById('snsAdvancedDialog').remove()">Cancel</button>
                        <button class="btn btn-primary" id="saveAdvancedBtn">Save</button>
                    </div>
                </div>
            </div>
        `;

        // Add to DOM
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsAdvancedDialog');

        if (!this._isDialogAlive()) return;

        this.clearInlineMessage();

        await this.loadExistingConfig();

        if (!this._isDialogAlive()) return;

        // Load 3D avatars
        await this.load3DAvatars();

        if (!this._isDialogAlive()) return;

        // Load user info
        await this.loadUserInfo();

        if (!this._isDialogAlive()) return;

        // Load agent list
        await this.loadAgentList();

        if (!this._isDialogAlive()) return;

        // Setup event listeners
        this.setupEventListeners();
    }

    setAvatarPreview(avatarSrc) {
        const img = this._q('#avatarPreviewImg');
        const preview = this._q('#avatarPreview');
        if (!img || !preview || !avatarSrc) return;

        img.src = avatarSrc;
        img.alt = 'Avatar preview';
        preview.classList.add('has-image');
    }

    async loadExistingConfig() {
        try {
            const response = await fetch(this.resolve('/api/sns/config'));
            const result = await response.json();

            const config = result && typeof result === 'object' && 'data' in result ? result.data : result;
            if (!config || typeof config !== 'object') return;

            this.existingConfig = config;

            const xmppAccountEl = this._q('#xmppAccount');
            if (xmppAccountEl) xmppAccountEl.value = config.account || '';

            // Load A2A config from memo (inline agent_card is no longer
            // supported on the UI — the agent card is sourced exclusively
            // from AgentCfg.memo.agent_card_url via HTTP fetch).
            const a2aConfig = config.a2a_config || {};
            this._a2aConfig = a2aConfig;

            // Load merged ad-hoc command list (builtin + plugin) from backend
            await this._loadMergedA2ACommands();

            if (config.avatar) {
                const avatarSrc = this._resolveAvatarSrc(config.avatar);
                this.setAvatarPreview(avatarSrc);
            }
            if (config.avatar3d) {
                const rawName = String(config.avatar3d || '');
                if (this._isWebUrl(rawName)) {
                    this.existingAvatar3DCustomUrl = rawName;
                    this.existingAvatar3DName = null;
                    this.selectedAvatar3DMode = 'custom';
                } else {
                    this.existingAvatar3DCustomUrl = null;
                    const baseName = rawName.split('/').pop().split('\\').pop();
                    this.existingAvatar3DName = baseName.toLowerCase().endsWith('.glb') ? baseName.slice(0, -4) : baseName;
                    this.selectedAvatar3DMode = 'preset';
                }
            }
        } catch (error) {
            console.error('Error loading existing config:', error);
        }
    }

    async load3DAvatars() {
        try {
            const response = await fetch(this.resolve('/api/sns/avatars3d'));
            const avatars = await response.json();

            const grid = this._q('#avatar3dGrid');
            if (!grid) return;
            grid.innerHTML = '';

            avatars.forEach(avatar => {
                const item = document.createElement('div');
                item.className = 'avatar3d-item';
                item.dataset.name = avatar.name;
                item.dataset.modelUrl = avatar.model_url;
                const previewUrl = this.resolve(avatar.preview_url);
                item.innerHTML = `
                    <img src="${previewUrl}" alt="${avatar.name}">
                    <div class="avatar3d-name">${avatar.name}</div>
                `;
                item.addEventListener('click', () => this.select3DAvatar(item, avatar));
                grid.appendChild(item);
            });

            const customItem = document.createElement('div');
            customItem.className = 'avatar3d-item avatar3d-item-custom';
            customItem.dataset.custom = '1';
            const customPreviewUrl = this.resolve('/static/assets/custom3d.png');
            customItem.innerHTML = `
                <img src="${customPreviewUrl}" alt="Custom">
                <div class="avatar3d-name">Custom</div>
            `;
            customItem.addEventListener('click', () => this.selectCustom3DAvatar(customItem));
            grid.appendChild(customItem);

            if (this.existingAvatar3DName) {
                const existingAvatar = avatars.find(a => a.name === this.existingAvatar3DName);
                const existingItem = grid.querySelector(`.avatar3d-item[data-name="${CSS.escape(this.existingAvatar3DName)}"]`);
                if (existingAvatar && existingItem) {
                    this.select3DAvatar(existingItem, existingAvatar);
                }
            } else if (this.existingAvatar3DCustomUrl) {
                const input = this._q('#avatar3dCustomUrl');
                if (input) {
                    input.value = this.existingAvatar3DCustomUrl;
                }
                this.selectCustom3DAvatar(customItem, { skipFocus: true });
            }
        } catch (error) {
            console.error('Error loading 3D avatars:', error);
            const grid = this._q('#avatar3dGrid');
            if (grid) grid.innerHTML = '<div class="error">Load failed</div>';
        }
    }

    select3DAvatar(element, avatar) {
        // Remove previous selection
        if (this.dialog) {
            this.dialog.querySelectorAll('.avatar3d-item').forEach(item => {
                item.classList.remove('selected');
            });
        }

        // Select current
        element.classList.add('selected');
        this.selectedAvatar3D = avatar;
        this.selectedAvatar3DMode = 'preset';
        this._setCustomAvatar3dInputVisible(false);
    }

    selectCustom3DAvatar(element, options = {}) {
        // Remove previous selection
        if (this.dialog) {
            this.dialog.querySelectorAll('.avatar3d-item').forEach(item => {
                item.classList.remove('selected');
            });
        }

        element.classList.add('selected');
        this.selectedAvatar3D = null;
        this.selectedAvatar3DMode = 'custom';
        this._setCustomAvatar3dInputVisible(true);

        const input = this._q('#avatar3dCustomUrl');
        if (input && !(options && options.skipFocus)) {
            try {
                input.focus();
            } catch (e) {
            }
        }
    }

    setupEventListeners() {
        // Tab switching
        const modalTabs = this._qa('.modal-tab');
        modalTabs.forEach(tab => {
            tab.addEventListener('click', (e) => {
                const targetTab = e.target.dataset.tab;

                this.setActiveTab(targetTab);
            });
        });

        const clear = () => this.clearInlineMessage();
        const nicknameEl = this._q('#userNickname');
        if (nicknameEl) nicknameEl.addEventListener('input', clear);
        const signEl = this._q('#userSign');
        if (signEl) signEl.addEventListener('input', clear);
        const agentIdEl = this._q('#userAgentId');
        if (agentIdEl) agentIdEl.addEventListener('change', clear);
        const xmppAccountEl = this._q('#xmppAccount');
        if (xmppAccountEl) xmppAccountEl.addEventListener('input', clear);

        const customAvatar3dUrlEl = this._q('#avatar3dCustomUrl');
        if (customAvatar3dUrlEl) customAvatar3dUrlEl.addEventListener('input', clear);

        const avatar3dDetailLink = this._q('#avatar3dFaceDetailLink');
        const openAvatar3dCustomizeDetail = (event) => {
            try {
                if (event && typeof event.preventDefault === 'function') {
                    event.preventDefault();
                }
            } catch (e) {
            }

            const url = 'http://guide.ai-sns.org/avatar.html';
            try {
                if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                    window.electronAPI.openUrl(url);
                    return;
                }
            } catch (e) {
            }

            try {
                window.open(url, '_blank', 'noopener');
            } catch (e) {
            }
        };
        if (avatar3dDetailLink) {
            avatar3dDetailLink.addEventListener('click', openAvatar3dCustomizeDetail);
            avatar3dDetailLink.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    openAvatar3dCustomizeDetail(e);
                }
            });
        }

        const avatar3dLicensesLink = this._q('#avatar3dLicensesLink');
        const openAvatar3dLicenses = (event) => {
            try {
                if (event && typeof event.preventDefault === 'function') {
                    event.preventDefault();
                }
            } catch (e) {
            }

            const url = 'https://ai-sns.gitbook.io/docs/documentation/more/3d-assets-licenses';
            try {
                if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                    window.electronAPI.openUrl(url);
                    return;
                }
            } catch (e) {
            }

            try {
                window.open(url, '_blank', 'noopener');
            } catch (e) {
            }
        };
        if (avatar3dLicensesLink) {
            avatar3dLicensesLink.addEventListener('click', openAvatar3dLicenses);
            avatar3dLicensesLink.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    openAvatar3dLicenses(e);
                }
            });
        }

        // Upload button
        const uploadBtn = this._q('#uploadAvatarBtn');
        const fileInput = this._q('#avatarFileInput');
        const triggerFilePicker = () => {
            if (fileInput) {
                fileInput.click();
            }
        };

        if (uploadBtn && fileInput) {
            uploadBtn.addEventListener('click', triggerFilePicker);
        }

        const preview = this._q('#avatarPreview');
        if (preview && fileInput) {
            preview.addEventListener('click', triggerFilePicker);
            preview.addEventListener('keydown', (e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    triggerFilePicker();
                }
            });
        }

        // File input change
        if (fileInput) {
            fileInput.addEventListener('change', (e) => {
                const file = e.target.files[0];
                if (file) {
                    this.previewAvatar(file);
                }
            });
        }

        // A2A Add Command button — opens the online guide in the system default browser
        const addCmdBtn = this._q('#a2aAddCommandBtn');
        const openAdhocCommandGuide = (event) => {
            try {
                if (event && typeof event.preventDefault === 'function') {
                    event.preventDefault();
                }
            } catch (e) {
            }

            const url = 'https://guide.ai-sns.org/docs.html#adhoccommand';
            try {
                if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                    window.electronAPI.openUrl(url);
                    return;
                }
            } catch (e) {
            }

            try {
                window.open(url, '_blank', 'noopener');
            } catch (e) {
            }
        };
        if (addCmdBtn) {
            addCmdBtn.addEventListener('click', openAdhocCommandGuide);
        }

        // A2A Reload Agent Card button
        const reloadBtn = this._q('#a2aReloadAgentCardBtn');
        if (reloadBtn) {
            reloadBtn.addEventListener('click', async () => {
                if (reloadBtn.disabled) return;
                const originalText = reloadBtn.textContent;
                reloadBtn.disabled = true;
                reloadBtn.textContent = 'Reloading...';
                try {
                    const resp = await fetch(this.resolve('/api/sns/xmpp-a2a/reload'), {
                        method: 'POST',
                        headers: { 'Content-Type': 'application/json' },
                        body: '{}',
                    });
                    const result = await resp.json();
                    if (result && result.success) {
                        const cardName = result.data && result.data.agent_card_name ? result.data.agent_card_name : '(unknown)';
                        const cmdCount = result.data && Array.isArray(result.data.registered_commands)
                            ? result.data.registered_commands.length : 0;
                        if (window.Toast) {
                            window.Toast.show(`Agent card reloaded: ${cardName} (${cmdCount} commands registered)`, 'success');
                        }
                    } else {
                        const msg = result && result.message ? result.message : 'Unknown error';
                        if (window.Toast) {
                            window.Toast.show('Reload failed: ' + msg, 'error');
                        }
                    }
                } catch (e) {
                    if (window.Toast) {
                        window.Toast.show('Reload failed: ' + (e && e.message ? e.message : String(e)), 'error');
                    }
                } finally {
                    reloadBtn.disabled = false;
                    reloadBtn.textContent = originalText;
                }
            });
        }

        // Save button
        const saveBtn = this._q('#saveAdvancedBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', () => {
                this.saveConfiguration();
            });
        }
    }

    previewAvatar(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = this._q('#avatarPreviewImg');
            const preview = this._q('#avatarPreview');
            if (!img || !preview) return;
            img.src = e.target.result;
            img.alt = file.name || 'Avatar preview';
            preview.classList.add('has-image');
            this.uploadedAvatar = file;
        };
        reader.readAsDataURL(file);
    }

    async saveConfiguration() {
        try {
            const errors = [];
            let didChange = false;
            let didChangeSubmit = false;
            let nicknameChanged = false;
            let nicknameValue = '';

            let avatarMapToSubmit = this.uploadedAvatarMeta && this.uploadedAvatarMeta.avatar_map
                ? String(this.uploadedAvatarMeta.avatar_map)
                : '';

            const newNationPasswordEl = this._q('#newNationPassword');
            const retypeNationPasswordEl = this._q('#retypeNationPassword');
            const newNationPassword = newNationPasswordEl ? String(newNationPasswordEl.value || '').trim() : '';
            const retypeNationPassword = retypeNationPasswordEl ? String(retypeNationPasswordEl.value || '').trim() : '';
            if (newNationPassword) {
                didChange = true;
            }

            const xmppAccountEl = this._q('#xmppAccount');
            const xmppPasswordEl = this._q('#xmppPassword');
            const xmppAccount = xmppAccountEl ? String(xmppAccountEl.value || '').trim() : '';
            const xmppPassword = xmppPasswordEl ? String(xmppPasswordEl.value || '').trim() : '';

            const nicknameEl = this._q('#userNickname');
            const signEl = this._q('#userSign');
            const agentIdEl = this._q('#userAgentId');
            const nicknameRaw = nicknameEl ? String(nicknameEl.value || '') : '';
            const signRaw = signEl ? String(signEl.value || '') : '';
            const agentIdRaw = agentIdEl ? String(agentIdEl.value || '') : '';

            if (!nicknameRaw.trim()) {
                this.showInlineMessage('Nickname is required.', 'error', { tab: 'userinfo', focusEl: nicknameEl });
                return;
            }
            if (!signRaw.trim()) {
                this.showInlineMessage('Profile is required.', 'error', { tab: 'userinfo', focusEl: signEl });
                return;
            }
            if (!agentIdRaw.trim()) {
                this.showInlineMessage('Agent is required.', 'error', { tab: 'userinfo', focusEl: agentIdEl });
                return;
            }

            // Ensure the selected agent's LLM model has a valid API key before it runs on the map.
            const agentKeyCheck = await this._validateSelectedAgentApiKey(agentIdRaw.trim());
            if (!agentKeyCheck.ok) {
                this.showInlineMessage(agentKeyCheck.message, 'error', { tab: 'userinfo', focusEl: agentIdEl });
                return;
            }

            if (!xmppAccount) {
                this.showInlineMessage('Account is required.', 'error', { tab: 'xmpp', focusEl: xmppAccountEl });
                return;
            }

            if (this.selectedAvatar3DMode === 'custom') {
                const customUrl = this._getCustomAvatar3dUrlValue();
                const urlError = this._validateCustomAvatar3dUrl(customUrl);
                if (urlError) {
                    const input = this._q('#avatar3dCustomUrl');
                    this.showInlineMessage(urlError, 'error', { tab: 'avatar', focusEl: input });
                    return;
                }
            }
            const xmppUpdates = {};
            const prevXmppAccount = this.existingConfig && this.existingConfig.account ? String(this.existingConfig.account || '') : '';
            if (xmppAccount && xmppAccount !== prevXmppAccount) xmppUpdates.account = xmppAccount;
            if (xmppPassword) xmppUpdates.password = xmppPassword;

            // Collect A2A config (agent card + commands)
            const a2aConfig = this._collectA2AConfig();
            const prevA2aConfig = (this.existingConfig && this.existingConfig.a2a_config) || {};
            if (JSON.stringify(a2aConfig) !== JSON.stringify(prevA2aConfig)) {
                xmppUpdates.a2a_config = a2aConfig;
            }

            if (Object.keys(xmppUpdates).length > 0) {
                didChange = true;
            }

            // 1) Avatar settings (upload avatar / select 3D avatar)
            const configUpdates = {};

            const effectiveAvatar3dValue = this._getEffectiveAvatar3dValue();
            const prevAvatar3dValue = (this.existingConfig && this.existingConfig.avatar3d) ? String(this.existingConfig.avatar3d) : '';
            if (effectiveAvatar3dValue && effectiveAvatar3dValue !== prevAvatar3dValue) {
                configUpdates.avatar3d = effectiveAvatar3dValue;
            }

            if (this.uploadedAvatar) {
                const formData = new FormData();
                formData.append('file', this.uploadedAvatar);

                const uploadResponse = await fetch(this.resolve('/api/sns/avatar-dialog/upload-avatar'), {
                    method: 'POST',
                    body: formData
                });

                const uploadResult = await uploadResponse.json();
                const uploadData = uploadResult && uploadResult.data ? uploadResult.data : null;
                if (uploadResult && uploadResult.success && uploadData) {
                    didChange = true;
                    didChangeSubmit = true;
                    try {
                        this.uploadedAvatarMeta = uploadData;
                        const avatarSrc = uploadData.avatar_url
                            ? this._resolveAvatarSrc(uploadData.avatar_url)
                            : this._resolveAvatarSrc(uploadData.avatar);

                        if (avatarSrc) {
                            this.setAvatarPreview(avatarSrc);
                        }
                        if (uploadData.avatar_map) {
                            avatarMapToSubmit = String(uploadData.avatar_map);
                        }
                    } catch (e) {
                    }
                } else {
                    errors.push('Avatar upload failed' + (uploadResult && uploadResult.message ? (': ' + uploadResult.message) : '.'));
                }
            }

            if (Object.keys(configUpdates).length > 0) {
                didChange = true;
                didChangeSubmit = true;
                // avatar3d will be submitted in one request below
            }

            // 2) Identity (nickname / signature / sns_url / agent)
            const snsUrlEl = this._q('#userSnsUrl');
            const nickname = nicknameRaw;
            const sign = signRaw;
            const snsUrl = snsUrlEl ? snsUrlEl.value : '';
            const agentId = agentIdRaw;

            const previous = this.existingUserInfo || {};
            const userInfoUpdates = {};

            if ((previous.nickname || '') !== nickname) userInfoUpdates.nickname = nickname;
            if ((previous.sign || '') !== sign) userInfoUpdates.sign = sign;
            if ((previous.sns_url || '') !== snsUrl) userInfoUpdates.sns_url = snsUrl;

            const prevAgent = previous.agent_id == null ? '' : String(previous.agent_id);
            const nextAgent = agentId || '';
            if (prevAgent !== nextAgent) userInfoUpdates.agent_id = nextAgent ? nextAgent : null;

            if (Object.keys(userInfoUpdates).length > 0) {
                didChange = true;
                didChangeSubmit = true;
                // user info will be submitted in one request below
            }

            if (!didChange) {
                alert('No changes to save.');
                return;
            }

            if (errors.length > 0) {
                alert('Save failed: ' + errors.join('\n'));
                return;
            }

            if (newNationPassword) {
                if (!retypeNationPassword) {
                    errors.push('Please retype the new nation password.');
                } else if (newNationPassword !== retypeNationPassword) {
                    errors.push('The two nation password entries do not match.');
                }
            }

            if (errors.length > 0) {
                alert('Save failed: ' + errors.join('\n'));
                return;
            }

            if (newNationPassword) {
                const passResp = await fetch(this.resolve('/api/sns/change-nationpassword'), {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        new_password: newNationPassword
                    })
                });
                const passResult = await passResp.json();
                if (!passResult || !passResult.success) {
                    errors.push('Nation password update failed' + (passResult && passResult.message ? (': ' + passResult.message) : '.'));
                } else {
                    if (newNationPasswordEl) newNationPasswordEl.value = '';
                    if (retypeNationPasswordEl) retypeNationPasswordEl.value = '';
                }
            }

            if (Object.keys(xmppUpdates).length > 0) {
                const xmppResp = await fetch(this.resolve('/api/sns/config'), {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify(xmppUpdates)
                });
                const xmppResult = await xmppResp.json();
                if (!xmppResult || !xmppResult.success) {
                    errors.push('XMPP update failed' + (xmppResult && xmppResult.message ? (': ' + xmppResult.message) : '.'));
                } else {
                    // Ensure remote sync happens even when only XMPP fields change.
                    didChangeSubmit = true;
                    if (xmppUpdates.account) {
                        this.existingConfig = {
                            ...(this.existingConfig || {}),
                            account: xmppUpdates.account
                        };
                    }
                    if (xmppPasswordEl) xmppPasswordEl.value = '';
                }
            }

            if (errors.length > 0) {
                alert('Save failed: ' + errors.join('\n'));
                return;
            }

            if (!didChangeSubmit) {
                alert('Saved successfully.');
                this.dialog.remove();
                return;
            }

            const avatar3dValue = this._getEffectiveAvatar3dValue();

            const submitPayload = {
                avatar3d: avatar3dValue,
                nickname,
                profile: sign,
                sns_url: snsUrl,
                agent_id: agentId
            };

            try {
                const agentIdNum = agentId ? parseInt(String(agentId), 10) : null;
                if (agentIdNum && Number.isFinite(agentIdNum)) {
                    const agentResp = await fetch(this.resolve(`/api/agent/${agentIdNum}`));
                    const agentResult = await agentResp.json();
                    const agentData = agentResult && agentResult.success ? agentResult.data : null;
                    const a2aUrl = agentData && agentData.url ? String(agentData.url).trim() : '';
                    if (a2aUrl) {
                        submitPayload.a2a_endpoint = a2aUrl;
                    }
                }
            } catch (e) {
                console.warn('[SNSAdvancedDialog] Failed to resolve agent a2a endpoint:', e);
            }

            try {
                const accountToSubmit = xmppAccount || (this.existingConfig && this.existingConfig.account ? String(this.existingConfig.account) : '');
                if (accountToSubmit) {
                    submitPayload.account = accountToSubmit;
                }
            } catch (e) {
            }

            if (avatarMapToSubmit) {
                submitPayload.avatar_map = avatarMapToSubmit;
            }

            const submitResp = await fetch(this.resolve('/api/sns/avatar-dialog/submit'), {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(submitPayload)
            });
            const submitResult = await submitResp.json();
            if (!submitResult || !submitResult.success) {
                errors.push('Submit failed' + (submitResult && submitResult.message ? (': ' + submitResult.message) : '.'));
            } else {
                if ((this.existingUserInfo && (this.existingUserInfo.nickname || '')) !== nickname) {
                    nicknameChanged = true;
                    nicknameValue = nickname;
                }
                this.existingAgentId = agentId;
                this.existingUserInfo = {
                    nickname,
                    sign,
                    sns_url: snsUrl,
                    agent_id: agentId ? agentId : null
                };
                this.existingConfig = {
                    ...(this.existingConfig || {}),
                    avatar3d: avatar3dValue
                };
                if (this._isWebUrl(avatar3dValue)) {
                    this.existingAvatar3DCustomUrl = avatar3dValue;
                    this.existingAvatar3DName = null;
                    this.selectedAvatar3DMode = 'custom';
                } else {
                    const normalized = String(avatar3dValue || '');
                    const baseName = normalized.split('/').pop().split('\\').pop();
                    this.existingAvatar3DName = baseName.toLowerCase().endsWith('.glb') ? baseName.slice(0, -4) : baseName;
                    this.existingAvatar3DCustomUrl = null;
                    this.selectedAvatar3DMode = 'preset';
                }
            }

            if (errors.length > 0) {
                alert('Save failed: ' + errors.join('\n'));
                return;
            }

            if (nicknameChanged) {
                try {
                    window.dispatchEvent(new CustomEvent('sns-user-info-updated', {
                        detail: {
                            nickname: nicknameValue
                        }
                    }));
                } catch (e) {
                }
            }

            alert('Saved successfully.');
            this.dialog.remove();
        } catch (error) {
            console.error('Error saving configuration:', error);
            alert('Save failed: ' + error.message);
        }
    }

    async loadUserInfo() {
        try {
            const response = await fetch(this.resolve('/api/sns/user-info'));
            const result = await response.json();

            if (result.success && result.data) {
                const nationIdTextEl = this._q('#avatarNationIdText');
                let nationid = result.data.nationid || '';
                if (!nationid) {
                    try {
                        if (typeof window !== 'undefined') {
                            nationid = window.nationid || window.nation_id_me || '';
                        }
                    } catch (e) {
                    }
                }
                if (nationIdTextEl) nationIdTextEl.textContent = `Nation ID: ${nationid || '-'}`;

                const securityNationIdTextEl = this._q('#securityNationIdText');
                if (securityNationIdTextEl) securityNationIdTextEl.textContent = `Nation ID: ${nationid || '-'}`;

                const nicknameEl = this._q('#userNickname');
                const signEl = this._q('#userSign');
                const snsUrlEl = this._q('#userSnsUrl');
                if (nicknameEl) nicknameEl.value = result.data.nickname || '';
                if (signEl) signEl.value = result.data.sign || '';
                if (snsUrlEl) snsUrlEl.value = result.data.sns_url || '';
                this.existingAgentId = result.data.agent_id || '';
                this.existingUserInfo = {
                    nickname: result.data.nickname || '',
                    sign: result.data.sign || '',
                    sns_url: result.data.sns_url || '',
                    agent_id: result.data.agent_id || null
                };
                const agentEl = this._q('#userAgentId');
                if (agentEl) agentEl.value = this.existingAgentId;
            }
        } catch (error) {
            console.error('Error loading user info:', error);
        }
    }

    _isInvalidApiKey(key) {
        const raw = String(key == null ? '' : key).trim();
        if (!raw) return true;
        const lower = raw.toLowerCase();
        const placeholders = new Set([
            'your_api_key', 'your-api-key', 'yourapikey', 'your_api_key_here',
            'your_key', 'your-key', 'api_key', 'apikey', 'placeholder',
            'changeme', 'change_me', 'none', 'null', 'undefined', 'todo',
            '***redacted***', 'sk-xxx', 'sk-xxxx', 'sk-xxxxxxxx'
        ]);
        if (placeholders.has(lower)) return true;
        if (/^x+$/i.test(raw)) return true;            // e.g. xxxxxx
        if (/^sk-x+$/i.test(raw)) return true;         // e.g. sk-xxxxxx
        if (/^<.*>$/.test(raw)) return true;           // e.g. <your-key>
        return false;
    }

    async _validateSelectedAgentApiKey(agentId) {
        try {
            const resp = await fetch(this.resolve(`/api/agent/${encodeURIComponent(agentId)}`));
            const result = await resp.json();
            const agent = result && result.success ? result.data : null;
            if (!agent) {
                return { ok: false, message: 'Failed to load the selected agent configuration.' };
            }

            const agentType = String(agent.agent_type || 'local').toLowerCase();
            // Remote agents run through an external A2A endpoint and do not require a local LLM API key.
            if (agentType === 'remote') {
                return { ok: true };
            }

            const configId = String(agent.model_config_id || agent.model || '').trim();
            if (!configId) {
                return { ok: false, message: 'The selected agent has no LLM model configured. Please configure an LLM model for this agent first.' };
            }

            const cfgResp = await fetch(this.resolve(`/api/agent/llm-configs/${encodeURIComponent(configId)}`));
            const cfgResult = await cfgResp.json();
            const cfg = cfgResult && cfgResult.success ? cfgResult.data : null;
            if (!cfg) {
                return { ok: false, message: 'The LLM model of the selected agent could not be found. Please reconfigure the agent LLM model.' };
            }

            if (this._isInvalidApiKey(cfg.api_key)) {
                const modelName = cfg.name ? ` (${cfg.name})` : '';
                return { ok: false, message: `The LLM model${modelName} of the selected agent has no valid API key configured. Please set a valid API key before running it on the map.` };
            }

            return { ok: true };
        } catch (e) {
            console.error('[SNSAdvancedDialog] Failed to validate agent LLM API key:', e);
            return { ok: false, message: 'Failed to validate the selected agent LLM API key. Please try again.' };
        }
    }

    async loadAgentList() {
        try {
            const response = await fetch(this.resolve('/api/agent/list'));
            const result = await response.json();

            if (result.success && result.data) {
                const select = this._q('#userAgentId');
                if (!select) return;
                result.data.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.id;
                    option.textContent = agent.name;
                    select.appendChild(option);
                });

                if (this.existingAgentId) {
                    select.value = this.existingAgentId;
                }
            }
        } catch (error) {
            console.error('Error loading agent list:', error);
        }
    }

    // ── A2A Command List Management ─────────────────────────────────────

    async _loadMergedA2ACommands() {
        // Fetch the merged command list (builtin + plugin) from the backend.
        try {
            const resp = await fetch(this.resolve('/api/sns/a2a/commands'));
            const data = await resp.json();
            if (data && data.success && Array.isArray(data.commands)) {
                this._a2aCommands = data.commands
                    .map(c => ({
                        node: c.node || '',
                        name: c.name || '',
                        description: c.description || '',
                        source: c.source || 'builtin',
                        enabled: c.enabled !== false,
                    }));
            } else {
                this._a2aCommands = [];
            }
        } catch (e) {
            console.warn('[SNSAdvancedDialog] Failed to load merged A2A commands:', e);
            this._a2aCommands = [];
        }
        this._renderA2ACommandList();
    }

    _renderA2ACommandList() {
        const container = this._q('#a2aCommandList');
        if (!container) return;
        container.innerHTML = '';

        if (!this._a2aCommands || this._a2aCommands.length === 0) {
            container.innerHTML = '<div style="font-size: 12px; color: #888;">No commands configured. Built-in commands will be registered by default.</div>';
            return;
        }

        // Inject styles for modern action buttons if not already present
        if (!document.getElementById('a2a-cmd-styles')) {
            const style = document.createElement('style');
            style.id = 'a2a-cmd-styles';
            style.innerHTML = `
                .a2a-cmd-action-btn {
                    background: transparent;
                    border: none;
                    padding: 4px;
                    border-radius: 4px;
                    cursor: pointer;
                    color: var(--text-secondary, #888);
                    transition: all 0.2s ease;
                    display: flex;
                    align-items: center;
                    justify-content: center;
                }
                .a2a-cmd-action-btn:hover {
                    color: var(--text-primary, #333);
                    background: var(--bg-hover, rgba(0,0,0,0.05));
                }
                .a2a-cmd-action-btn.del-btn:hover {
                    color: #ef4444;
                    background: rgba(239, 68, 68, 0.1);
                }
                .a2a-cmd-row:hover {
                    background: var(--bg-hover, rgba(0,0,0,0.02));
                }
            `;
            document.head.appendChild(style);
        }

        this._a2aCommands.forEach((cmd, idx) => {
            const row = document.createElement('div');
            row.className = 'a2a-cmd-row';
            row.style.cssText = 'display: flex; align-items: center; gap: 8px; margin-bottom: 2px; padding: 4px 6px; border-radius: 6px; font-size: 13px; transition: background 0.2s;';

            const source = cmd.source || 'builtin';
            const enabled = cmd.enabled !== false;

            const isDark = document.body.classList.contains('theme-dark');
            const badgeBg = source === 'plugin'
                ? (isDark ? 'rgba(16,185,129,0.2)' : '#d1fae5')
                : (isDark ? 'rgba(99,102,241,0.2)' : '#e0e7ff');
            const badgeColor = source === 'plugin'
                ? (isDark ? '#6ee7b7' : '#065f46')
                : (isDark ? '#a5b4fc' : '#3730a3');

            row.innerHTML = `
                <input type="checkbox" data-cmd-idx="${idx}" class="a2a-cmd-enabled" ${enabled ? 'checked' : ''} style="margin: 0; cursor: pointer;" title="${enabled ? 'Enabled' : 'Disabled'}">
                <span style="flex: 1; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-primary, inherit); font-weight: 500;" title="${cmd.node || ''}">${cmd.name || cmd.node || '(unnamed)'}</span>
                <span style="font-size: 10px; padding: 2px 6px; border-radius: 4px; font-weight: 600; text-transform: uppercase; letter-spacing: 0.5px; background: ${badgeBg}; color: ${badgeColor};">${source}</span>
            `;
            container.appendChild(row);
        });

        // Bind events
        container.querySelectorAll('.a2a-cmd-enabled').forEach(cb => {
            cb.addEventListener('change', (e) => {
                const i = parseInt(e.target.dataset.cmdIdx, 10);
                if (this._a2aCommands[i]) this._a2aCommands[i].enabled = e.target.checked;
            });
        });
    }

    _collectA2AConfig() {
        const adhocCommands = [];
        for (const c of (this._a2aCommands || [])) {
            const source = c.source || 'builtin';
            if (c.enabled === false) {
                // Persist disabled state for builtin/plugin to override default-on behaviour
                adhocCommands.push({
                    node: c.node,
                    name: c.name,
                    source: source,
                    enabled: false,
                });
            }
            // Otherwise (builtin/plugin enabled): rely on backend default-on, do not persist
        }

        return {
            adhoc_commands: adhocCommands,
        };
    }
}
