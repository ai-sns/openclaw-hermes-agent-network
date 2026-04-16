const InitializationWizard = {
    modal: null,
    step: 0,
    avatar3dItems: [],
    captcha: {
        id: '',
        objectUrl: ''
    },
    state: {
        id: null,
        status: 0,
        name: '',
        avatar: '',
        password: '',
        confirm_password: '',
        profile: '',
        llm: 'OpenAI',
        llm_server: 'https://api.openai.com/v1/chat/completions',
        api_key: '',
        avatar3d: '',
        account: '',
        account_password: '',
        sns_url: '',
        map: 'Google',
        map_api_key: '',
        map_id: ''
    },

    setInlineTestResult(type, message) {
        if (!this.modal || !this.modal.element) {
            return;
        }
        const root = this.modal.element.querySelector('#initWizard');
        if (!root) {
            return;
        }
        const el = root.querySelector('#initInlineTestResult');
        if (!el) {
            return;
        }
        const text = (message || '').toString();
        if (!text) {
            el.style.display = 'none';
            el.textContent = '';
            return;
        }
        el.style.display = 'block';
        el.textContent = text;

        const ok = type === 'success';
        el.style.borderColor = ok ? 'rgba(46, 204, 113, 0.65)' : 'rgba(231, 76, 60, 0.65)';
        el.style.background = ok ? 'rgba(46, 204, 113, 0.08)' : 'rgba(231, 76, 60, 0.08)';
        el.style.color = ok ? 'rgba(46, 204, 113, 0.95)' : 'rgba(231, 76, 60, 0.95)';
    },

    setTestingState(kind, isTesting) {
        if (!this.modal || !this.modal.element) {
            return;
        }
        const root = this.modal.element.querySelector('#initWizard');
        if (!root) {
            return;
        }

        const map = {
            llm: { btn: '#initTestLlmBtn', indicator: '#initLlmTestingIndicator' },
            xmpp: { btn: '#initTestXmppBtn', indicator: '#initXmppTestingIndicator' }
        };
        const cfg = map[kind];
        if (!cfg) {
            return;
        }

        const btn = root.querySelector(cfg.btn);
        const indicator = root.querySelector(cfg.indicator);

        if (btn) {
            try { btn.disabled = !!isTesting; } catch (_) {}
        }

        if (indicator) {
            indicator.style.display = isTesting ? 'flex' : 'none';
        }
    },

    clearAllTestingState() {
        this.setTestingState('llm', false);
        this.setTestingState('xmpp', false);
    },

    async show(options = {}) {
        if (typeof Modal === 'undefined') {
            console.error('Modal component not loaded');
            return;
        }

        await this.loadInitialData();

        const auto = !!(options && options.auto);

        if (auto && Number(this.state.status) === 1) {
            return;
        }

        if (Number(this.state.status) === 1) {
            Modal.show({
                title: 'Initialization Setup',
                content: this.renderReadonlySummary(),
                showCancel: false,
                confirmText: 'Close',
                width: '820px'
            });
            return;
        }

        this.step = 0;

        Modal.show({
            title: 'Initialization Setup',
            content: this.renderStep(),
            showCancel: true,
            cancelText: 'Cancel',
            confirmText: 'Next',
            width: '820px',
            closeOnClickOutside: false,
            onOpen: (modal) => {
                this.modal = modal;
                this.bindStepEvents();
            },
            onCancel: async () => {
                if (this.step > 0) {
                    this.collectFormValues();
                    await this.saveDraftSilently();
                    this.step -= 1;
                    this.updateModal();
                    return false;
                }

                this.cleanupCaptchaObjectUrl();
                if (window.electronAPI && typeof window.electronAPI.quitApp === 'function') {
                    window.electronAPI.quitApp();
                } else if (window.electronAPI && typeof window.electronAPI.windowClose === 'function') {
                    window.electronAPI.windowClose();
                } else {
                    window.close();
                }
                return true;
            },
            onConfirm: async () => {
                this.collectFormValues();

                const validateResult = this.validateCurrentStep();
                if (validateResult !== true) {
                    return false;
                }

                if (this.step < 4) {
                    await this.saveDraftSilently();
                    this.step += 1;
                    this.updateModal();
                    return false;
                }

                const captchaCode = (this.state.captcha_code || '').trim();
                if (!this.captcha.id || !captchaCode) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error('Please enter the captcha code');
                    }
                    return false;
                }

                try {
                    const payload = {
                        ...this.state,
                        captcha_id: this.captcha.id,
                        captcha_code: captchaCode
                    };

                    const res = await window.api.post('/api/system/init-wizard/submit', payload);
                    if (res && res.success) {
                        if (typeof Notification !== 'undefined') {
                            Notification.success('Configuration saved');
                        }
                        this.cleanupCaptchaObjectUrl();
                        return true;
                    }

                    if (typeof Notification !== 'undefined') {
                        Notification.error(res?.message || res?.detail || 'Submit failed');
                    }
                    return false;
                } catch (e) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error(e.message || 'Submit failed');
                    }
                    return false;
                }
            },
            onClose: () => {
                this.cleanupCaptchaObjectUrl();
            }
        });
    },

    async loadInitialData() {
        try {
            const draftRes = await window.api.get('/api/system/init-wizard/draft');
            if (draftRes && draftRes.success && draftRes.data) {
                this.state = { ...this.state, ...draftRes.data };
            }
        } catch (e) {
            console.warn('Failed to load init draft:', e);
        }

        try {
            const avatarRes = await window.api.get('/api/system/init-wizard/avatar3d');
            if (avatarRes && avatarRes.success && Array.isArray(avatarRes.data)) {
                this.avatar3dItems = avatarRes.data;
            }
        } catch (e) {
            console.warn('Failed to load avatar3d list:', e);
        }
    },

    apiBaseUrl() {
        const raw = (window.api && window.api.baseUrl)
            || (window.appConfig && window.appConfig.agent_server)
            || '';
        if (raw) return String(raw).replace(/\/+$/, '');
        if (typeof window.resolveAgentServerUrl === 'function') {
            try {
                const u = new URL(window.resolveAgentServerUrl('/'));
                return u.origin;
            } catch (e) {
                return '';
            }
        }
        return '';
    },

    renderReadonlySummary() {
        const avatarUrl = this.state.avatar ? `${this.apiBaseUrl()}/images/avatars/${this.state.avatar}` : '';
        return `
            <div class="initialization-wizard">
                <div style="display:flex;gap:16px;align-items:flex-start;">
                    <div style="width:88px;">
                        ${avatarUrl ? `<img src="${avatarUrl}" style="width:70px;height:70px;border-radius:50%;object-fit:cover;display:block;margin:0 auto;"/>` : ''}
                    </div>
                    <div style="flex:1;">
                        <h4 style="margin:0 0 8px 0;">Initialization complete</h4>
                        <div style="opacity:0.9;">
                            <div><strong>Nickname:</strong> ${this.escapeHtml(this.state.name || '')}</div>
                            <div><strong>Account:</strong> ${this.escapeHtml(this.state.account || '')}</div>
                            <div><strong>Map:</strong> ${this.escapeHtml(this.state.map || '')}</div>
                            <div><strong>3D Avatar:</strong> ${this.escapeHtml(this.state.avatar3d || '')}</div>
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    renderStep() {
        const steps = [
            { key: 'basic', title: 'Basic' },
            { key: 'llm', title: 'LLM' },
            { key: 'xmpp', title: 'XMPP' },
            { key: 'map', title: 'Map' },
            { key: 'submit', title: 'Verify & Submit' }
        ];

        return `
            <div class="initialization-wizard" id="initWizard">
                <div class="settings-tabs" style="margin-bottom:12px;">
                    ${steps.map((s, idx) => `
                        <button class="settings-tab-btn ${idx === this.step ? 'active' : ''}" data-step="${idx}" type="button" disabled>${s.title}</button>
                    `).join('')}
                </div>

                <div class="init-wizard-body">
                    ${this.step === 0 ? this.renderBasicStep() : ''}
                    ${this.step === 1 ? this.renderLlmStep() : ''}
                    ${this.step === 2 ? this.renderXmppStep() : ''}
                    ${this.step === 3 ? this.renderMapStep() : ''}
                    ${this.step === 4 ? this.renderCaptchaStep() : ''}
                </div>
            </div>
        `;
    },

    renderBasicStep() {
        const avatarUrl = this.state.avatar ? `${this.apiBaseUrl()}/images/avatars/${this.state.avatar}` : `${this.apiBaseUrl()}/images/avatar.png`;

        return `
            <div class="init-step init-step-basic">
                <div style="display:flex;gap:16px;align-items:flex-start;">
                    <div style="width:96px;text-align:center;">
                        <img id="initAvatarPreview" src="${avatarUrl}" style="width:70px;height:70px;border-radius:50%;object-fit:cover;border:1px solid rgba(255,255,255,0.2);display:block;margin:0 auto;" />
                        <div style="margin-top:8px;display:flex;flex-direction:column;gap:6px;align-items:center;">
                            <input id="initAvatarFile" type="file" accept="image/*" style="display:none;" />
                            <button class="btn btn-secondary" id="initAvatarSelectBtn" type="button" style="width:92px;display:block;margin:0 auto;">Upload</button>
                            <div id="initAvatarFileName" style="font-size:11px;opacity:0.75;max-width:96px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;"></div>
                        </div>
                    </div>

                    <div style="flex:1;">
                        <div class="form-group">
                            <label>Nickname *</label>
                            <input class="form-input" id="initName" type="text" value="${this.escapeHtml(this.state.name || '')}" />
                        </div>

                        <div class="form-row" style="display:flex;gap:12px;">
                            <div class="form-group" style="flex:1;">
                                <label>Password *</label>
                                <input class="form-input" id="initPassword" type="password" value="${this.escapeHtml(this.state.password || '')}" />
                            </div>
                            <div class="form-group" style="flex:1;">
                                <label>Confirm password *</label>
                                <input class="form-input" id="initConfirmPassword" type="password" value="${this.escapeHtml(this.state.confirm_password || '')}" />
                            </div>
                        </div>

                        <div class="form-group">
                            <label>Bio *</label>
                            <textarea class="form-input" id="initProfile" placeholder="Introduce yourself" rows="3">${this.escapeHtml(this.state.profile || '')}</textarea>
                        </div>

                        <div class="form-group">
                            <label>Your social links</label>
                            <input class="form-input" id="initSnsUrl" type="text" placeholder="e.g. https://x.com/ai_sns_org" value="${this.escapeHtml(this.state.sns_url || '')}" />
                        </div>
                    </div>
                </div>
            </div>
        `;
    },

    renderLlmStep() {
        const llmOptions = [
            'OpenAI',
            'DeepSeek',
            'Claude',
            'Gemini',
            'OpenAI Compatible Provider',
            'DeepSeek Compatible Provider'
        ];

        return `
            <div class="init-step init-step-llm">
                <div class="form-group">
                    <label>LLM *</label>
                    <select class="form-input" id="initLlm">
                        ${llmOptions.map(o => `<option value="${this.escapeHtml(o)}" ${o === this.state.llm ? 'selected' : ''}>${this.escapeHtml(o)}</option>`).join('')}
                    </select>
                </div>

                <div class="form-group">
                    <label>LLM Server *</label>
                    <input class="form-input" id="initLlmServer" type="text" value="${this.escapeHtml(this.state.llm_server || '')}" />
                </div>

                <div class="form-group">
                    <label>API Key *</label>
                    <input class="form-input" id="initApiKey" type="text" value="${this.escapeHtml(this.state.api_key || '')}" />
                </div>

                <div class="form-group">
                    <div id="initInlineTestResult" style="display:none; border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px 16px; background:rgba(255,255,255,0.03); font-family:var(--font-mono, monospace); font-size:12px; line-height:1.5;"></div>
                </div>

                <div class="form-group" style="display:flex;justify-content:flex-end;align-items:center;gap:12px;margin-top:16px;">
                    <div id="initLlmTestingIndicator" style="display:none; align-items:center; gap:8px; color:var(--color-primary, #1a73e8); font-size:13px; font-weight:500; transition: all 0.2s;">
                        <div class="spinner" style="width:16px; height:16px; border-width:2px; margin:0;"></div>
                        <span>Testing...</span>
                    </div>
                    <button class="btn btn-secondary" id="initTestLlmBtn" type="button" style="min-width:80px; transition: all 0.2s;">Test</button>
                </div>
            </div>
        `;
    },

    renderXmppStep() {
        return `
            <div class="init-step init-step-xmpp">
                <div class="form-row" style="display:flex;gap:12px;">
                    <div class="form-group" style="flex:1;">
                        <label>XMPP Account *</label>
                        <input class="form-input" id="initAccount" type="text" value="${this.escapeHtml(this.state.account || '')}" />
                    </div>
                    <div class="form-group" style="flex:1;">
                        <label>XMPP Password *</label>
                        <input class="form-input" id="initAccountPassword" type="password" value="${this.escapeHtml(this.state.account_password || '')}" />
                    </div>
                </div>

                <div class="form-group" style="display:flex;justify-content:flex-start;">
                    <div style="display:flex;align-items:center;gap:8px;white-space:nowrap;">
                        <label style="white-space:nowrap;margin:0;">If you don't have an account:</label>
                        <a href="#" id="initSnsRegisterLink" style="font-size:12px;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;">Get one</a>
                    </div>
                </div>

                <div class="form-group">
                    <div id="initInlineTestResult" style="display:none; border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px 16px; background:rgba(255,255,255,0.03); font-family:var(--font-mono, monospace); font-size:12px; line-height:1.5;"></div>
                </div>

                <div class="form-group" style="display:flex;justify-content:flex-end;align-items:center;gap:12px;margin-top:16px;">
                    <div id="initXmppTestingIndicator" style="display:none; align-items:center; gap:8px; color:var(--color-primary, #1a73e8); font-size:13px; font-weight:500; transition: all 0.2s;">
                        <div class="spinner" style="width:16px; height:16px; border-width:2px; margin:0;"></div>
                        <span>Testing...</span>
                    </div>
                    <button class="btn btn-secondary" id="initTestXmppBtn" type="button" style="min-width:80px; transition: all 0.2s;">Test</button>
                </div>
            </div>
        `;
    },

    renderMapStep() {
        const avatarGrid = this.avatar3dItems.map(item => {
            const selected = item.glb_url === this.state.avatar3d;
            return `
                <div class="avatar3d-item" data-glb-url="${this.escapeHtml(item.glb_url)}" style="cursor:pointer;border:1px solid ${selected ? '#1a73e8' : 'rgba(255,255,255,0.2)'};border-radius:10px;padding:6px;flex:0 0 auto;width:86px;">
                    <img src="${this.escapeHtml(item.png_url)}" style="width:72px;height:72px;object-fit:cover;border-radius:8px;display:block;margin:0 auto;" />
                    <div style="font-size:11px;opacity:0.85;margin-top:6px;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;">${this.escapeHtml(item.key)}</div>
                </div>
            `;
        }).join('');

        const mapIdReadOnly = this.state.map === 'Baidu';
        const mapIdValue = mapIdReadOnly ? 'do_not_need_map_id' : (this.state.map_id || '');

        return `
            <div class="init-step init-step-map">
                <div class="form-group">
                    <label>Please choose your 3D avatar *</label>
                    <div style="display:flex;align-items:center;gap:8px;">
                        <button class="btn btn-secondary" id="avatar3dPrevBtn" type="button" style="padding:6px 10px;">◀</button>
                        <div id="avatar3dGrid" style="display:flex;gap:10px;overflow-x:auto;overflow-y:hidden;scrollbar-width:thin;padding:6px 2px;flex:1;min-width:0;">
                            ${avatarGrid}
                        </div>
                        <button class="btn btn-secondary" id="avatar3dNextBtn" type="button" style="padding:6px 10px;">▶</button>
                    </div>
                    <input type="hidden" id="initAvatar3d" value="${this.escapeHtml(this.state.avatar3d || '')}" />
                </div>

                <div class="form-row" style="display:flex;gap:12px;align-items:center;">
                    <div class="form-group" style="flex:1;min-width:0;">
                        <label>Map Type *</label>
                        <select class="form-input" id="initMapType">
                            <option value="Google" ${this.state.map === 'Google' ? 'selected' : ''}>Google</option>
                            <option value="Baidu" ${this.state.map === 'Baidu' ? 'selected' : ''}>Baidu</option>
                        </select>
                    </div>
                    <div class="form-group" style="flex:1;min-width:0;">
                        <div style="display:flex;align-items:center;gap:6px;white-space:nowrap;">
                            <span style="font-size:14px;opacity:0.9;">If you don't have an Api Key:</span>
                            <a href="#" id="initMapRegisterLink" style="font-size:14px;white-space:nowrap;display:inline-flex;align-items:center;gap:6px;">Get one</a>
                        </div>
                    </div>
                </div>

                <div class="form-row" style="display:flex;gap:12px;">
                    <div class="form-group" style="flex:1;">
                        <label>Map API Key *</label>
                        <input class="form-input" id="initMapApiKey" type="text" value="${this.escapeHtml(this.state.map_api_key || '')}" />
                    </div>
                    <div class="form-group" style="flex:1;min-width:0;">
                        <label>Map ID *</label>
                        <input class="form-input" id="initMapId" type="text" value="${this.escapeHtml(mapIdValue)}" ${mapIdReadOnly ? 'readonly' : ''} />
                    </div>
                </div>

                <div class="form-group">
                    <div id="initInlineTestResult" style="display:none; border:1px solid rgba(255,255,255,0.1); border-radius:10px; padding:12px 16px; background:rgba(255,255,255,0.03); font-family:var(--font-mono, monospace); font-size:12px; line-height:1.5;"></div>
                </div>

                <div class="form-group" style="display:flex;justify-content:flex-end;margin-top:16px;">
                    <button class="btn btn-secondary" id="initTestMapBtn" type="button" style="min-width:80px; transition: all 0.2s;">Test</button>
                </div>
            </div>
        `;
    },

    renderCaptchaStep() {
        return `
            <div class="init-step init-step-captcha">
                <div class="form-group">
                    <label>Please enter the captcha code *</label>
                    <div style="display:flex;gap:12px;align-items:center;">
                        <input class="form-input" id="initCaptchaCode" type="text" value="${this.escapeHtml(this.state.captcha_code || '')}" style="flex:1;" />
                        <img id="initCaptchaImg" style="width:140px;height:56px;border:1px solid rgba(255,255,255,0.2);border-radius:6px;object-fit:contain;" />
                        <button class="btn btn-secondary" id="initCaptchaRefresh" type="button">Refresh</button>
                    </div>
                </div>


            </div>
        `;
    },

    updateModal() {
        if (!this.modal || !this.modal.element) {
            return;
        }

        this.clearAllTestingState();

        const body = this.modal.element.querySelector('.modal-body');
        if (body) {
            body.innerHTML = this.renderStep();
        }

        const title = this.modal.element.querySelector('.modal-title');
        if (title) {
            title.textContent = 'Initialization Setup';
        }

        const cancelBtn = this.modal.element.querySelector('[data-action="cancel"]');
        const confirmBtn = this.modal.element.querySelector('[data-action="confirm"]');

        if (cancelBtn) {
            cancelBtn.textContent = this.step === 0 ? 'Cancel' : 'Previous';
        }

        if (confirmBtn) {
            confirmBtn.textContent = this.step < 4 ? 'Next' : 'Submit';
        }

        this.bindStepEvents();
    },

    bindStepEvents() {
        if (!this.modal || !this.modal.element) {
            return;
        }

        this.clearAllTestingState();

        const closeBtn = this.modal.element.querySelector('[data-action="close"]');
        if (closeBtn && !closeBtn.dataset.initWizardBound) {
            closeBtn.dataset.initWizardBound = '1';
            closeBtn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopImmediatePropagation();
                this.cleanupCaptchaObjectUrl();

                if (window.electronAPI && typeof window.electronAPI.quitApp === 'function') {
                    window.electronAPI.quitApp();
                    return;
                }
                if (window.electronAPI && typeof window.electronAPI.windowClose === 'function') {
                    window.electronAPI.windowClose();
                    return;
                }
                window.close();
            }, true);
        }

        const root = this.modal.element.querySelector('#initWizard');
        if (!root) {
            return;
        }

        root.querySelectorAll('.settings-tab-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
            });
        });

        const testLlmBtn = root.querySelector('#initTestLlmBtn');
        if (testLlmBtn) {
            testLlmBtn.addEventListener('click', async () => {
                this.collectFormValues();
                this.setInlineTestResult(null, '');
                try {
                    this.setTestingState('llm', true);

                    const providerMap = {
                        'OpenAI': 'openai',
                        'DeepSeek': 'custom',
                        'Claude': 'claude',
                        'Gemini': 'gemini',
                        'OpenAI Compatible Provider': 'custom',
                        'DeepSeek Compatible Provider': 'custom'
                    };

                    const modelCandidatesMap = {
                        openai: ['gpt-4o-mini', 'gpt-4o', 'gpt-3.5-turbo'],
                        custom: ['deepseek-chat', 'deepseek-reasoner', 'gpt-4o-mini'],
                        gemini: ['gemini-2.0-flash', 'gemini-1.5-flash', 'gemini-1.5-pro'],
                        claude: ['claude-3-5-sonnet-20240620', 'claude-3-5-haiku-20241022', 'claude-3-haiku-20240307']
                    };

                    const provider = providerMap[this.state.llm] || 'custom';
                    const candidates = modelCandidatesMap[provider] || modelCandidatesMap.custom;

                    const endpoint = String(this.state.llm_server || '').trim();
                    const apiKey = String(this.state.api_key || '').trim();

                    let lastErr = null;
                    let okResult = null;
                    for (const modelName of candidates) {
                        try {
                            const res = await window.api.post('/api/agent/llm-configs/test', {
                                api_endpoint: endpoint,
                                api_key: apiKey,
                                model_name: modelName,
                                provider
                            });

                            if (res && res.success && res.data && String(res.data.status || '').toLowerCase() === 'success') {
                                okResult = res.data;
                                break;
                            }

                            lastErr = res?.error || res?.data?.message || res?.message || res?.detail || 'Test failed';
                        } catch (innerErr) {
                            lastErr = innerErr?.message || 'Test failed';
                        }
                    }

                    if (okResult) {
                        const messageLines = [
                            `Status: ${okResult.status || 'success'}`,
                            okResult.model ? `Model: ${okResult.model}` : '',
                            okResult.base_url ? `Base URL: ${okResult.base_url}` : '',
                            okResult.latency_ms != null ? `Latency: ${okResult.latency_ms} ms` : '',
                            okResult.reply ? `Reply: ${okResult.reply}` : ''
                        ].filter(Boolean);
                        this.setInlineTestResult('success', messageLines.join('\n'));
                    } else {
                        this.setInlineTestResult('error', String(lastErr || 'Test failed'));
                    }
                } catch (e) {
                    this.setInlineTestResult('error', e.message || 'Test failed');
                } finally {
                    this.setTestingState('llm', false);
                }
            });
        }

        const openUrlInDefaultBrowser = (url) => {
            const u = String(url || '').trim();
            if (!u) {
                return;
            }
            if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                window.electronAPI.openUrl(u);
            } else {
                window.open(u, '_blank');
            }
        };

        const testXmppBtn = root.querySelector('#initTestXmppBtn');
        if (testXmppBtn) {
            testXmppBtn.addEventListener('click', async () => {
                this.collectFormValues();
                this.setInlineTestResult(null, '');
                try {
                    this.setTestingState('xmpp', true);
                    const res = await window.api.post('/api/system/init-wizard/test-xmpp', {
                        account: this.state.account,
                        account_password: this.state.account_password
                    });
                    if (res && res.success) {
                        this.setInlineTestResult('success', res.message || 'Test passed');
                    } else {
                        this.setInlineTestResult('error', res?.message || res?.detail || 'Test failed');
                    }
                } catch (e) {
                    this.setInlineTestResult('error', e.message || 'Test failed');
                } finally {
                    this.setTestingState('xmpp', false);
                }
            });
        }

        const snsRegisterLink = root.querySelector('#initSnsRegisterLink');
        if (snsRegisterLink) {
            snsRegisterLink.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                openUrlInDefaultBrowser('https://www.baidu.com');
            });
        }

        const testMapBtn = root.querySelector('#initTestMapBtn');
        if (testMapBtn) {
            testMapBtn.addEventListener('click', async () => {
                this.collectFormValues();
                this.setInlineTestResult(null, '');
                const mapType = String(this.state.map || '').trim();
                const url = mapType === 'Google'
                    ? 'http://localhost:8788/scripts/google3dmap_test.html'
                    : 'http://localhost:8788/scripts/map_test.html';
                openUrlInDefaultBrowser(url);
            });
        }

        const mapRegisterLink = root.querySelector('#initMapRegisterLink');
        if (mapRegisterLink) {
            mapRegisterLink.addEventListener('click', (e) => {
                e.preventDefault();
                e.stopPropagation();
                openUrlInDefaultBrowser('https://map.baidu.com');
            });
        }

        const fileInput = root.querySelector('#initAvatarFile');
        const fileSelectBtn = root.querySelector('#initAvatarSelectBtn');
        const fileNameEl = root.querySelector('#initAvatarFileName');
        if (fileSelectBtn && fileInput) {
            fileSelectBtn.addEventListener('click', () => {
                fileInput.click();
            });
        }
        if (fileInput) {
            fileInput.addEventListener('change', async () => {
                const file = fileInput.files && fileInput.files[0];
                if (!file) {
                    return;
                }

                if (fileNameEl) {
                    fileNameEl.textContent = file.name || '';
                }

                try {
                    const form = new FormData();
                    form.append('avatar_file', file);

                    const resp = await fetch(`${this.apiBaseUrl()}/api/system/init-wizard/avatar`, {
                        method: 'POST',
                        body: form
                    });
                    if (!resp.ok) {
                        const text = await resp.text();
                        throw new Error(text || resp.statusText);
                    }

                    const json = await resp.json();
                    if (!json.success) {
                        throw new Error(json.message || json.detail || 'Upload failed');
                    }

                    this.state.avatar = json.data.avatar;
                    await this.saveDraftSilently();

                    const preview = root.querySelector('#initAvatarPreview');
                    if (preview) {
                        preview.src = `${this.apiBaseUrl()}/images/avatars/${this.state.avatar}`;
                    }

                    if (typeof Notification !== 'undefined') {
                        Notification.success('Avatar updated');
                    }
                } catch (e) {
                    if (typeof Notification !== 'undefined') {
                        Notification.error(e.message || 'Avatar upload failed');
                    }
                } finally {
                    fileInput.value = '';
                }
            });
        }

        const llmSelect = root.querySelector('#initLlm');
        if (llmSelect) {
            llmSelect.addEventListener('change', () => {
                const llm = llmSelect.value;
                const urlMap = {
                    'OpenAI': 'https://api.openai.com/v1/chat/completions',
                    'DeepSeek': 'https://api.deepseek.com/v1/chat/completions',
                    'Claude': 'https://api.anthropic.com/v1/messages',
                    'Gemini': 'https://generativelanguage.googleapis.com/v1beta/openai/chat/completions'
                };
                const serverInput = root.querySelector('#initLlmServer');
                if (serverInput && urlMap[llm]) {
                    serverInput.value = urlMap[llm];
                }
            });
        }

        const mapType = root.querySelector('#initMapType');
        if (mapType) {
            mapType.addEventListener('change', () => {
                const mapId = root.querySelector('#initMapId');
                if (!mapId) {
                    return;
                }

                if (mapType.value === 'Baidu') {
                    mapId.value = 'do_not_need_map_id';
                    mapId.setAttribute('readonly', 'readonly');
                } else {
                    mapId.removeAttribute('readonly');
                    if (mapId.value === 'do_not_need_map_id') {
                        mapId.value = '';
                    }
                }
            });
        }

        const avatarGrid = root.querySelector('#avatar3dGrid');
        const prevBtn = root.querySelector('#avatar3dPrevBtn');
        const nextBtn = root.querySelector('#avatar3dNextBtn');
        if (avatarGrid) {
            if (typeof this._avatar3dScrollLeft === 'number') {
                avatarGrid.scrollLeft = this._avatar3dScrollLeft;
                this._avatar3dScrollLeft = null;
            }
            const scrollByAmount = (dir) => {
                const amount = Math.max(120, Math.floor((avatarGrid.clientWidth || 0) * 0.7));
                avatarGrid.scrollBy({ left: dir * amount, behavior: 'smooth' });
            };

            if (prevBtn) {
                prevBtn.addEventListener('click', () => scrollByAmount(-1));
            }
            if (nextBtn) {
                nextBtn.addEventListener('click', () => scrollByAmount(1));
            }

            avatarGrid.addEventListener('wheel', (e) => {
                if (Math.abs(e.deltaY) > Math.abs(e.deltaX)) {
                    avatarGrid.scrollLeft += e.deltaY;
                    e.preventDefault();
                }
            }, { passive: false });

            avatarGrid.querySelectorAll('.avatar3d-item').forEach(item => {
                item.addEventListener('click', async () => {
                    this._avatar3dScrollLeft = avatarGrid.scrollLeft;
                    const glbUrl = item.dataset.glbUrl;
                    this.state.avatar3d = glbUrl;
                    const hidden = root.querySelector('#initAvatar3d');
                    if (hidden) {
                        hidden.value = glbUrl;
                    }
                    await this.saveDraftSilently();
                    this.updateModal();
                });
            });
        }

        const captchaImg = root.querySelector('#initCaptchaImg');
        const captchaRefresh = root.querySelector('#initCaptchaRefresh');
        if (captchaImg && captchaRefresh) {
            captchaRefresh.addEventListener('click', async () => {
                await this.loadCaptcha();
            });

            this.loadCaptcha().catch(() => {});
        }
    },

    collectFormValues() {
        if (!this.modal || !this.modal.element) {
            return;
        }

        const root = this.modal.element.querySelector('#initWizard');
        if (!root) {
            return;
        }

        const get = (sel) => {
            const el = root.querySelector(sel);
            return el ? el.value : '';
        };

        if (this.step === 0) {
            this.state.name = get('#initName');
            this.state.password = get('#initPassword');
            this.state.confirm_password = get('#initConfirmPassword');
            this.state.profile = get('#initProfile');
            this.state.sns_url = get('#initSnsUrl');
        } else if (this.step === 1) {
            this.state.llm = get('#initLlm');
            this.state.llm_server = get('#initLlmServer');
            this.state.api_key = get('#initApiKey');
        } else if (this.step === 2) {
            this.state.account = get('#initAccount');
            this.state.account_password = get('#initAccountPassword');
        } else if (this.step === 3) {
            this.state.avatar3d = get('#initAvatar3d');
            this.state.map = get('#initMapType');
            this.state.map_api_key = get('#initMapApiKey');
            this.state.map_id = get('#initMapId');
        } else if (this.step === 4) {
            this.state.captcha_code = get('#initCaptchaCode');
        }
    },

    validateCurrentStep() {
        if (this.step === 0) {
            if (!this.state.name || !this.state.avatar || !this.state.password || !this.state.confirm_password || !this.state.profile) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('All fields are required except the SNS homepage.');
                }
                return false;
            }

            if (this.state.password !== this.state.confirm_password) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Password and confirm password do not match.');
                }
                return false;
            }

            if (!this.isPasswordValid(this.state.password)) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Password must include uppercase, lowercase, digits, and special characters, and be at least 8 characters long.');
                }
                return false;
            }
        }

        if (this.step === 1) {
            if (!this.state.llm || !this.state.llm_server || !this.state.api_key) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Please complete the LLM configuration.');
                }
                return false;
            }
        }

        if (this.step === 2) {
            if (!this.state.account || !this.state.account_password) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Please complete the XMPP configuration.');
                }
                return false;
            }
        }

        if (this.step === 3) {
            if (!this.state.avatar3d || !this.state.map || !this.state.map_api_key || !this.state.map_id) {
                if (typeof Notification !== 'undefined') {
                    Notification.error('Map configuration is required.');
                }
                return false;
            }

            if (this.state.map === 'Baidu' && this.state.map_id !== 'do_not_need_map_id') {
                this.state.map_id = 'do_not_need_map_id';
            }
        }

        return true;
    },

    isPasswordValid(password) {
        if (!password || password.length < 8) return false;
        const hasUpper = /[A-Z]/.test(password);
        const hasLower = /[a-z]/.test(password);
        const hasDigit = /[0-9]/.test(password);
        const hasSpecial = /[!@#$%^&*(),.?":{}|<>]/.test(password);
        return hasUpper && hasLower && hasDigit && hasSpecial;
    },

    async saveDraftSilently() {
        try {
            const payload = { ...this.state };
            delete payload.captcha_code;
            await window.api.put('/api/system/init-wizard/draft', payload);
        } catch (e) {
            console.warn('Save draft failed:', e);
        }
    },

    async loadCaptcha() {
        this.cleanupCaptchaObjectUrl();

        const resp = await fetch(`${this.apiBaseUrl()}/api/system/init-wizard/captcha`, {
            method: 'GET'
        });
        if (!resp.ok) {
            throw new Error(await resp.text());
        }

        this.captcha.id = resp.headers.get('X-Captcha-ID') || '';
        const blob = await resp.blob();
        this.captcha.objectUrl = URL.createObjectURL(blob);

        if (!this.modal || !this.modal.element) {
            return;
        }

        const img = this.modal.element.querySelector('#initCaptchaImg');
        if (img) {
            img.src = this.captcha.objectUrl;
        }
    },

    cleanupCaptchaObjectUrl() {
        if (this.captcha.objectUrl) {
            try {
                URL.revokeObjectURL(this.captcha.objectUrl);
            } catch (_) {
            }
            this.captcha.objectUrl = '';
        }
    },

    escapeHtml(str) {
        return String(str || '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#039;');
    }
};

export default InitializationWizard;
