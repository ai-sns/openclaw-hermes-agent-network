/**
 * Agent Handlers - shared utility functions
 * Provides renderMarkdown, highlightCodeBlocks, createMessageElement, copyCode,
 * loadModelOptions, loadRoleOptions, and related helpers used by
 * multiAgentHandlers.js and management pages via window.agentHandlers.
 */

import agentState from './agentState.js';

const agentHandlers = {
    resolve(urlOrPath) {
        try {
            if (typeof window !== 'undefined' && typeof window.resolveAgentServerUrl === 'function') {
                return window.resolveAgentServerUrl(urlOrPath);
            }
        } catch (e) {
        }
        return urlOrPath;
    },

    /**
     * Legacy init stub - kept for index.js fallback compatibility.
     * Multi-agent system uses multiAgentHandlers.init() instead.
     */
    init() {
        console.warn('[agentHandlers] Legacy init() called; multi-agent system should use multiAgentHandlers.init()');
    },

    /**
     * Load model options
     */
    async loadModelOptions() {
        const modelSelector = document.getElementById('modelSelector');
        if (!modelSelector) return;

        try {
            const response = await fetch(this.resolve('/api/agent/llm-configs'));
            const result = await response.json();

            if (result.success && result.data) {
                const models = result.data.filter(m => m.is_active !== false);

                if (models.length > 0) {
                    // Keep the first option if there is no default model
                    let defaultModel = models.find(m => m.is_default) || models[0];

                    modelSelector.innerHTML = models.map(model => `
                        <option value="${model.config_id}" ${model.is_default ? 'selected' : ''}>
                            ${model.name}${model.provider ? ` (${model.provider})` : ''}
                        </option>
                    `).join('');

                    // Set the currently selected model
                    if (defaultModel) {
                        agentState.setModel(defaultModel.config_id);
                        // Load the full configuration for the default model
                        await this.loadAndApplyModelConfig(defaultModel.config_id);
                    }
                } else {
                    modelSelector.innerHTML = '<option value="">No available models</option>';
                }
            }
        } catch (error) {
            console.error('Failed to load model list:', error);
            // Keep default options
        }
    },

    /**
     * Load role options
     */
    async loadRoleOptions() {
        const roleSelector = document.getElementById('roleSelector');
        if (!roleSelector) return;

        try {
            const response = await fetch(this.resolve('/api/agent/role-configs'));
            const result = await response.json();

            if (result.success && result.data) {
                const roles = result.data.filter(r => r.is_active !== false);

                if (roles.length > 0) {
                    // Keep the first option if there is no default role
                    let defaultRole = roles.find(r => r.is_default) || roles[0];

                    roleSelector.innerHTML = roles.map(role => `
                        <option value="${role.role_id}" ${role.is_default ? 'selected' : ''}>
                            ${role.name}${role.category ? ` - ${role.category}` : ''}
                        </option>
                    `).join('');

                    // Set the currently selected role
                    if (defaultRole) {
                        agentState.setRole(defaultRole.role_id);
                        // Load the full configuration for the default role
                        await this.loadAndApplyRoleConfig(defaultRole.role_id);
                    }
                } else {
                    roleSelector.innerHTML = '<option value="">No available roles</option>';
                }
            }
        } catch (error) {
            console.error('Failed to load role list:', error);
            // Keep default options
        }
    },

    /**
     * Create message element
     */
    createMessageElement(role, content, time) {
        const isUser = role === 'user';
        const currentAgent = !isUser ? agentState.getCurrentAgent() : null;
        const assistantName = !isUser ? (currentAgent?.name || 'AI Assistant') : null;
        const avatarSvg = isUser ?
            '<svg viewBox="0 0 24 24" width="20" height="20" fill="currentColor"><path d="M12 12c2.21 0 4-1.79 4-4s-1.79-4-4-4-4 1.79-4 4 1.79 4 4 4zm0 2c-2.67 0-8 1.34-8 4v2h16v-2c0-2.66-5.33-4-8-4z"/></svg>' :
            '<svg viewBox="0 0 48 48" width="26" height="26" xmlns="http://www.w3.org/2000/svg"  fill="currentColor"><g transform="translate(4.8, 4.8) scale(0.8)"><path d="M24 7v3 M21 7h6 M16 12h16a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H16a3 3 0 0 1-3-3V15a3 3 0 0 1 3-3z M19 19h2 M27 19h2 M11 34c0-3 3-5 6-5h14c3 0 6 2 6 5v4H11v-4z" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"/><circle cx="20" cy="19" r="1.5" fill="currentColor"/><circle cx="28" cy="19" r="1.5" fill="currentColor"/></g></svg>';

        // Copy icon SVG
        const copyIconSvg = `
            <button class="message-copy-btn" title="Copy message" aria-label="Copy message">
                <svg viewBox="0 0 24 24" width="14" height="14" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="9" y="9" width="13" height="13" rx="2" ry="2"></rect>
                    <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
                </svg>
            </button>
        `;

        return `
            <div class="message-item ${isUser ? 'user-message' : 'assistant-message'}">
                <div class="message-header">
                    <div class="message-avatar ${isUser ? 'user-avatar' : 'assistant-avatar'}">
                        ${avatarSvg}
                    </div>
                    <span class="message-sender">${isUser ? 'You' : this.escapeHtml(assistantName)}</span>
                    <span class="message-time">${time}</span>
                </div>
                <div class="message-body">${this.renderMarkdown(content)}</div>
                <div class="message-footer">
                    ${copyIconSvg}
                </div>
            </div>
        `;
    },

    /**
     * Format time
     */
    formatTime(timestamp) {
        if (!timestamp) return '';
        try {
            const date = new Date(timestamp);
            return date.toLocaleString('zh-CN', {
                month: '2-digit',
                day: '2-digit',
                hour: '2-digit',
                minute: '2-digit'
            });
        } catch (error) {
            return '';
        }
    },

    /**
     * Markdown rendering
     */
    renderMarkdown(text, isStreaming = false) {
        if (!text) return '';

        // Preserve code blocks to avoid being processed by other rules
        const codeBlocks = [];

        // Full code block handling
        text = text.replace(/```(\w*)\n?([\s\S]*?)```/g, (match, lang, code) => {
            const language = lang || 'plaintext';
            const rawCode = code.trim();
            const escapedCode = this.escapeHtml(rawCode);
            const escapedRawCode = this.escapeHtml(rawCode).replace(/"/g, '&quot;');
            const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
            codeBlocks.push(`<div class="code-block"><div class="code-header"><span class="code-lang">${language}</span><button class="copy-code-btn" onclick="agentHandlers.copyCode(this)"><svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor"><path d="M16 1H4c-1.1 0-2 .9-2 2v14h2V3h12V1zm3 4H8c-1.1 0-2 .9-2 2v14c0 1.1.9 2 2 2h11c1.1 0 2-.9 2-2V7c0-1.1-.9-2-2-2zm0 16H8V7h11v14z"/></svg><span>Copy</span></button></div><pre><code class="language-${language}" data-raw-code="${escapedRawCode}">${escapedCode}</code></pre></div>`);
            return placeholder;
        });

        // Handle incomplete code blocks (during streaming)
        if (isStreaming) {
            text = text.replace(/```(\w*)\n?([\s\S]*)$/g, (match, lang, code) => {
                if (match.includes('__CODEBLOCK_')) return match;
                const language = lang || 'plaintext';
                const escapedCode = this.escapeHtml(code);
                const escapedRawCode = this.escapeHtml(code).replace(/"/g, '&quot;');
                const placeholder = `__CODEBLOCK_${codeBlocks.length}__`;
                codeBlocks.push(`<div class="code-block streaming-code"><div class="code-header"><span class="code-lang">${language}</span></div><pre><code class="language-${language}" data-raw-code="${escapedRawCode}">${escapedCode}</code></pre></div>`);
                return placeholder;
            });
        }

        // Inline code
        text = text.replace(/`([^`]+)`/g, '<code class="inline-code">$1</code>');

        // Bold
        text = text.replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>');

        // Italic
        text = text.replace(/\*([^*]+)\*/g, '<em>$1</em>');

        // Headings
        text = text.replace(/^### (.+)$/gm, '<h3>$1</h3>');
        text = text.replace(/^## (.+)$/gm, '<h2>$1</h2>');
        text = text.replace(/^# (.+)$/gm, '<h1>$1</h1>');

        // Unordered lists
        text = text.replace(/^- (.+)$/gm, '<li>$1</li>');
        text = text.replace(/(<li>.*<\/li>\n?)+/g, '<ul>$&</ul>');

        // Links
        text = text.replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" target="_blank" rel="noopener">$1</a>');

        // Blockquotes
        text = text.replace(/^> (.+)$/gm, '<blockquote>$1</blockquote>');

        // Newline handling
        text = text.replace(/\n\n/g, '</p><p>');
        text = text.replace(/\n/g, '<br>');

        // Wrap in paragraph
        if (!text.startsWith('<') && !text.startsWith('__CODEBLOCK_')) {
            text = '<p>' + text + '</p>';
        }

        // Restore code blocks
        codeBlocks.forEach((block, index) => {
            text = text.replace(`__CODEBLOCK_${index}__`, block);
        });

        return text;
    },

    /**
     * Code highlighting
     */
    highlightCodeBlocks(container) {
        container.querySelectorAll('pre code').forEach(block => {
            if (block.dataset.highlighted) return;
            block.dataset.highlighted = 'true';

            let code = block.textContent;
            block.dataset.rawCode = code;

            let highlighted = this.escapeHtml(code);

            // Keyword highlighting
            const keywords = [
                'function', 'const', 'let', 'var', 'if', 'else', 'for', 'while', 'return',
                'class', 'import', 'export', 'from', 'async', 'await', 'try', 'catch',
                'def', 'print', 'self', 'None', 'True', 'False', 'in', 'not', 'and', 'or'
            ];

            const keywordPattern = new RegExp(`\\b(${keywords.join('|')})\\b`, 'g');
            highlighted = highlighted.replace(keywordPattern, '<span class="hljs-keyword">$1</span>');

            // Number highlighting
            highlighted = highlighted.replace(/\\b(\\d+\\.?\\d*)\\b/g, '<span class="hljs-number">$1</span>');

            // String highlighting
            highlighted = highlighted.replace(/(&quot;[^&]*&quot;|&#39;[^&]*&#39;)/g, '<span class="hljs-string">$1</span>');

            // Comment highlighting
            highlighted = highlighted.replace(/(\/\/.*$|#.*$)/gm, '<span class="hljs-comment">$1</span>');

            block.innerHTML = highlighted;
        });
    },

    /**
     * Copy code
     */
    copyCode(btn) {
        const codeBlock = btn.closest('.code-block');
        const codeElement = codeBlock.querySelector('code');
        const code = codeElement.dataset.rawCode || codeElement.textContent;

        const showCopiedState = () => {
            const originalText = btn.querySelector('span').textContent;
            btn.querySelector('span').textContent = 'Copied!';
            btn.classList.add('copied');
            setTimeout(() => {
                btn.querySelector('span').textContent = originalText;
                btn.classList.remove('copied');
            }, 2000);
        };

        const showFailedState = () => {
            const originalText = btn.querySelector('span').textContent;
            btn.querySelector('span').textContent = 'Copy failed';
            setTimeout(() => {
                btn.querySelector('span').textContent = originalText;
            }, 2000);
        };

        const fallbackCopy = () => {
            const textarea = document.createElement('textarea');
            textarea.value = code;
            textarea.setAttribute('readonly', '');
            textarea.style.position = 'fixed';
            textarea.style.top = '-1000px';
            textarea.style.left = '-1000px';
            document.body.appendChild(textarea);
            textarea.select();
            textarea.setSelectionRange(0, textarea.value.length);

            let ok = false;
            try {
                ok = document.execCommand('copy');
            } catch (e) {
                ok = false;
            }

            document.body.removeChild(textarea);
            return ok;
        };

        (async () => {
            try {
                if (window.electronAPI && typeof window.electronAPI.writeClipboardText === 'function') {
                    const res = await window.electronAPI.writeClipboardText(code);
                    if (res && res.success) {
                        showCopiedState();
                        return;
                    }
                }

                if (navigator.clipboard && typeof navigator.clipboard.writeText === 'function') {
                    await navigator.clipboard.writeText(code);
                    showCopiedState();
                    return;
                }

                const ok = fallbackCopy();
                if (ok) {
                    showCopiedState();
                    return;
                }

                throw new Error('All copy methods failed');
            } catch (err) {
                console.warn('[AgentHandlers] Failed to copy code to clipboard:', err);
                showFailedState();
            }
        })();
    },

    /**
     * HTML escaping
     */
    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    },

    /**
     * Load and apply model config
     */
    async loadAndApplyModelConfig(configId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/llm-configs/${configId}`));
            const result = await response.json();

            if (result.success && result.data) {
                const modelConfig = result.data;
                // Save to state
                agentState.currentModelConfig = modelConfig;
                // Update right-side panel Param tab
                this.populateParamTab(modelConfig);
                console.log('[AgentHandlers] Model config loaded:', modelConfig.name);
            }
        } catch (error) {
            console.error('Failed to load model config:', error);
        }
    },

    /**
     * Load and apply role config
     */
    async loadAndApplyRoleConfig(roleId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/role-configs/${roleId}`));
            const result = await response.json();

            if (result.success && result.data) {
                const roleConfig = result.data;
                // Save to state
                agentState.currentRoleConfig = roleConfig;
                // Update right-side panel Prompt tab
                this.populatePromptTab(roleConfig);
                console.log('[AgentHandlers] Role config loaded:', roleConfig.name);
            }
        } catch (error) {
            console.error('Failed to load role config:', error);
        }
    },

    /**
     * Populate Param tab - display parameters for the selected model
     */
    populateParamTab(modelConfig) {
        if (!modelConfig) return;

        // Find inputs in the param tab
        const paramTab = document.querySelector('[data-tab="param"]');
        if (!paramTab) return;

        const inputs = paramTab.querySelectorAll('.param-input');
        inputs.forEach(input => {
            const label = input.closest('.param-label');
            if (!label) return;

            const labelText = label.querySelector('span')?.textContent.trim();

            if (labelText === 'Temperature' && modelConfig.temperature !== undefined) {
                input.value = modelConfig.temperature;
            } else if (labelText === 'Max Tokens' && modelConfig.max_tokens !== undefined) {
                input.value = modelConfig.max_tokens;
            } else if (labelText === 'Top P' && modelConfig.top_p !== undefined) {
                input.value = modelConfig.top_p;
            } else if (labelText === 'Frequency Penalty' && modelConfig.frequency_penalty !== undefined) {
                input.value = modelConfig.frequency_penalty;
            } else if (labelText === 'Presence Penalty' && modelConfig.presence_penalty !== undefined) {
                input.value = modelConfig.presence_penalty;
            }
        });

        const checkboxes = Array.from(paramTab.querySelectorAll('input[type="checkbox"]'));
        for (const cb of checkboxes) {
            const label = cb.closest('label.param-toggle');
            const labelText = label ? (label.querySelector('span')?.textContent || '').trim() : '';
            if (labelText === 'Stream mode' && modelConfig.stream !== undefined) {
                cb.checked = !!modelConfig.stream;
            }
        }

        for (const cb of checkboxes) {
            const label = cb.closest('label.param-toggle');
            const labelText = label ? (label.querySelector('span')?.textContent || '').trim() : '';
            if (labelText === 'Thinking effort') {
                cb.checked = !!modelConfig.thinking_effort_enabled;
            }
        }

        const effortSelect = paramTab.querySelector('select.thinking-effort-select');
        if (effortSelect) {
            const v = String(modelConfig.thinking_effort_level || '').trim().toLowerCase();
            if (v) effortSelect.value = v;
        }

        try {
            const wrapper = paramTab.querySelector('.thinking-effort-wrapper');
            const enabled = !!modelConfig.thinking_effort_enabled;
            if (wrapper) wrapper.style.display = enabled ? '' : 'none';
            const linkBox = paramTab.querySelector('.thinking-effort-doc-link');
            const link = paramTab.querySelector('.thinking-effort-doc-anchor');
            let url = '';
            try {
                const provider = String(modelConfig.provider || '').trim().toLowerCase();
                if (provider === 'gemini') url = 'https://ai.google.dev/gemini-api/docs/openai?authuser=1&hl=zh-cn#thinking';
                else if (provider === 'claude') url = 'https://platform.claude.com/docs/en/build-with-claude/adaptive-thinking';
                else url = 'https://developers.openai.com/api/docs/models/all';
            } catch (e) {
                url = 'https://developers.openai.com/api/docs/models/all';
            }
            if (link) {
                link.dataset.externalUrl = enabled ? url : '';
                link.href = enabled ? url : '#';
            }
            if (linkBox) linkBox.style.display = enabled ? '' : 'none';
        } catch (e) {
        }
    },

    /**
     * Populate Prompt tab - display the selected role prompt
     */
    populatePromptTab(roleConfig) {
        if (!roleConfig) return;

        const promptTextarea = document.getElementById('systemPrompt');
        if (promptTextarea && roleConfig.system_prompt) {
            promptTextarea.value = roleConfig.system_prompt;
        }
    },

    /**
     * Destroy
     */
    destroy() {
        // Clean up event listeners
        agentState.reset();
    }
};

// Export as a global object to allow calling from HTML
if (typeof window !== 'undefined') {
    window.agentHandlers = agentHandlers;
}

export default agentHandlers;
