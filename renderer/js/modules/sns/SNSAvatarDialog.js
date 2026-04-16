/**
 * SNS Avatar Configuration Dialog
 */

export class SNSAvatarDialog {
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
        const alertBox = this._q('#snsAvatarAlert');
        if (!alertBox) {
            return;
        }
        alertBox.style.display = 'none';
        alertBox.textContent = '';
        alertBox.classList.remove('inline-alert-error', 'inline-alert-success');
    }

    showInlineMessage(message, type = 'error', options = {}) {
        const alertBox = this._q('#snsAvatarAlert');
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
        const existing = document.getElementById('snsAvatarDialog');
        if (existing) {
            try {
                existing.remove();
            } catch (e) {
            }
        }

        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsAvatarDialog">
                <div class="modal-dialog" style="max-width: 600px;">
                    <div class="modal-header">
                        <h3>User Configuration</h3>
                        <button class="modal-close" onclick="document.getElementById('snsAvatarDialog').remove()">&times;</button>
                    </div>
                    <div class="modal-tabs">
                        <button class="modal-tab active" data-tab="avatar">Avatar Settings</button>
                        <button class="modal-tab" data-tab="userinfo">Profile Info</button>
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
                                                <svg viewBox="0 0 24 24" width="24" height="24" fill="currentColor" style="opacity: 0.6">
                                                    <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                                                </svg>
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
                                    <h4>Choose 3D Avatar</h4>
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
                                            <label for="userAgentId">Agent<span class="required-asterisk">*</span></label>
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

                        <div class="dialog-inline-alert" id="snsAvatarAlert" style="display: none;"></div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="document.getElementById('snsAvatarDialog').remove()">Cancel</button>
                        <button class="btn btn-primary" id="saveAvatarBtn">Save</button>
                    </div>
                </div>
            </div>
        `;

        // Add to DOM
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsAvatarDialog');

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
            const customPreviewUrl = this.resolve('/scripts/images/custom3d.png');
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

            const url = 'http://www.ai-sns.org';
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

        // Save button
        const saveBtn = this._q('#saveAvatarBtn');
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

            // 2) Profile info (nickname / signature / sns_url / agent)
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
                console.warn('[SNSAvatarDialog] Failed to resolve agent a2a endpoint:', e);
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
}
