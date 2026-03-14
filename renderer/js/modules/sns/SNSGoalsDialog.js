/**
 * SNS Goals Dialog
 */

export class SNSGoalsDialog {
    constructor() {
        this.dialog = null;
        this.title = '__plan_goals__';
        this.content = '';
    }

    _isDialogAlive() {
        return !!(this.dialog && typeof document !== 'undefined' && document.body && document.body.contains(this.dialog));
    }

    _q(selector) {
        return this.dialog ? this.dialog.querySelector(selector) : null;
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

    clearInlineMessage() {
        const alertBox = this._q('#snsGoalsAlert');
        if (!alertBox) return;
        alertBox.style.display = 'none';
        alertBox.textContent = '';
        alertBox.classList.remove('inline-alert-error', 'inline-alert-success');
    }

    showInlineMessage(message, type = 'error') {
        const alertBox = this._q('#snsGoalsAlert');
        if (!alertBox) return;
        alertBox.textContent = message;
        alertBox.classList.remove('inline-alert-error', 'inline-alert-success');
        alertBox.classList.add(type === 'success' ? 'inline-alert-success' : 'inline-alert-error');
        alertBox.style.display = 'block';
    }

    async loadContent() {
        try {
            const url = this.resolve(`/api/sns/prompts/by-title/${encodeURIComponent(this.title)}`);
            const resp = await fetch(url);
            const data = await resp.json();

            if (!data || data.success === false) {
                const msg = (data && data.message) ? String(data.message) : 'Failed to load goals.';
                throw new Error(msg);
            }

            const payload = (data && data.data) ? data.data : {};
            this.content = (payload && payload.content !== undefined && payload.content !== null)
                ? String(payload.content)
                : '';
        } catch (e) {
            console.error('[SNSGoalsDialog] loadContent failed:', e);
            this.content = '';
            throw e;
        }
    }

    async saveContent(nextContent) {
        const contentToSave = (nextContent !== undefined && nextContent !== null) ? String(nextContent) : '';

        try {
            const url = this.resolve(`/api/sns/prompts/by-title/${encodeURIComponent(this.title)}`);
            const resp = await fetch(url, {
                method: 'PUT',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    content: contentToSave
                })
            });

            const data = await resp.json();
            if (!data || data.success === false) {
                const msg = (data && data.message) ? String(data.message) : 'Save failed.';
                throw new Error(msg);
            }

            this.content = contentToSave;
            return true;
        } catch (e) {
            console.error('[SNSGoalsDialog] saveContent failed:', e);
            throw e;
        }
    }

    async show() {
        const existing = document.getElementById('snsGoalsDialog');
        if (existing) {
            try {
                existing.remove();
            } catch (e) {
            }
        }

        const existingStyles = document.getElementById('snsGoalsDialogStyles');
        if (existingStyles) {
            try {
                existingStyles.remove();
            } catch (e) {
            }
        }

        try {
            await this.loadContent();
        } catch (e) {
            // Continue showing the dialog with empty content.
        }

        const dialogHTML = `
            <div class="modal-overlay" id="snsGoalsDialog">
                <div class="modal-dialog" style="max-width: 800px; width: 90vw; max-height: 90vh; display: flex; flex-direction: column;">
                    <div class="modal-header">
                        <h3>Goals</h3>
                        <button class="modal-close" onclick="(() => { const d=document.getElementById('snsGoalsDialog'); if(d) d.remove(); const s=document.getElementById('snsGoalsDialogStyles'); if(s) s.remove(); })()">&times;</button>
                    </div>
                    <div class="modal-body" style="flex: 1; overflow: hidden; display: flex; flex-direction: column; min-height: 0;">
                        <div class="sns-goals-container" style="display: flex; flex-direction: column; gap: 10px; flex: 1; min-height: 0;">
                            <div class="sns-goals-hint" id="snsGoalsHint">
                                Note: Your content may be modified by AI during execution.
                            </div>
                            <textarea id="snsGoalsContent" class="form-control" rows="16" spellcheck="false" autocapitalize="off" autocomplete="off" autocorrect="off" style="flex: 1; min-height: 240px; resize: vertical;"></textarea>
                            <div class="dialog-inline-alert" id="snsGoalsAlert" style="display: none;"></div>
                        </div>
                    </div>
                    <div class="modal-footer" style="display: flex; justify-content: flex-end; gap: 8px;">
                        <button class="btn btn-secondary" id="snsGoalsCloseBtn">Close</button>
                        <button class="btn btn-primary" id="snsGoalsSaveBtn">Save</button>
                    </div>
                </div>
            </div>
        `;

        const styles = `
            <style id="snsGoalsDialogStyles">
                #snsGoalsDialog .sns-goals-hint {
                    font-size: 12px;
                    color: var(--color-primary, #2196F3);
                    background: var(--bg-secondary, #fafafa);
                    border: 1px solid var(--border-color, #e0e0e0);
                    border-radius: 6px;
                    padding: 10px 12px;
                }

                #snsGoalsDialog textarea#snsGoalsContent {
                    font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
                    font-size: 13px;
                    line-height: 1.55;
                }

                #snsGoalsDialog .dialog-inline-alert {
                    padding: 10px 12px;
                    border-radius: 6px;
                    font-size: 12px;
                }

                #snsGoalsDialog .inline-alert-error {
                    background: rgba(244, 67, 54, 0.12);
                    color: #b71c1c;
                    border: 1px solid rgba(244, 67, 54, 0.35);
                }

                #snsGoalsDialog .inline-alert-success {
                    background: rgba(76, 175, 80, 0.12);
                    color: #1b5e20;
                    border: 1px solid rgba(76, 175, 80, 0.35);
                }
            </style>
        `;

        document.head.insertAdjacentHTML('beforeend', styles);
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsGoalsDialog');

        if (!this._isDialogAlive()) return;

        const textarea = this._q('#snsGoalsContent');
        if (textarea) {
            textarea.value = this.content || '';
        }

        this.clearInlineMessage();

        const closeBtn = this._q('#snsGoalsCloseBtn');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                try {
                    const d = document.getElementById('snsGoalsDialog');
                    if (d) d.remove();
                } catch (e) {
                }
                try {
                    const s = document.getElementById('snsGoalsDialogStyles');
                    if (s) s.remove();
                } catch (e) {
                }
            });
        }

        const saveBtn = this._q('#snsGoalsSaveBtn');
        if (saveBtn) {
            saveBtn.addEventListener('click', async () => {
                this.clearInlineMessage();
                const next = textarea ? textarea.value : '';
                saveBtn.disabled = true;
                try {
                    await this.saveContent(next);
                    try {
                        const d = document.getElementById('snsGoalsDialog');
                        if (d) d.remove();
                    } catch (e) {
                    }
                    try {
                        const s = document.getElementById('snsGoalsDialogStyles');
                        if (s) s.remove();
                    } catch (e) {
                    }
                } catch (e) {
                    const msg = (e && e.message) ? String(e.message) : 'Save failed.';
                    this.showInlineMessage(msg, 'error');
                } finally {
                    saveBtn.disabled = false;
                }
            });
        }
    }
}
