/**
 * Code Plugin - code execution plugin
 * Extract code from chat and run it in the browser
 */

const CodePlugin = {
    /**
     * Plugin metadata
     */
    info: {
        id: 'code',
        name: 'Code Execution Plugin',
        version: '1.0.0',
        description: 'Extract code blocks from chat, with editing and execution'
    },

    /**
     * Plugin state
     */
    state: {
        codeBlocks: [],
        currentIndex: 0
    },

    /**
     * Currently rendered container (for multi-instance support)
     */
    _currentContainer: null,

    /**
     * Render plugin UI
     */
    render(container) {
        // Save current container reference
        this._currentContainer = container;
        container.innerHTML = `
            <div style="padding: 12px; display: flex; flex-direction: column; gap: 12px; height: 100%;">
                <!-- Code info bar -->
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: var(--bg-secondary, #f5f5f5); border-radius: 4px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 10px; color: var(--text-secondary, #666);" id="code-plugin-info">No code extracted</span>
                        <select id="code-plugin-language" style="font-size: 10px; padding: 2px 4px; border: 1px solid var(--border-light, #ddd); border-radius: 3px; background: var(--bg-content, #fff); color: var(--text-primary, #333);">
                            <option value="javascript">JavaScript</option>
                            <option value="python">Python</option>
                            <option value="html">HTML</option>
                        </select>
                    </div>
                    <button class="preset-use-btn" style="padding: 4px 8px; font-size: 10px;" onclick="CodePlugin.extractCodes()">
                        <svg viewBox="0 0 24 24" width="12" height="12" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                            <path d="M19 13h-6v6h-2v-6H5v-2h6V5h2v6h6v2z"/>
                        </svg>
                        Extract code
                    </button>
                </div>

                <!-- Code editor -->
                <textarea
                    id="code-plugin-editor"
                    placeholder="Click 'Extract code' to get code from chat, or write code here..."
                    style="flex: 1; min-height: 200px; padding: 12px; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.5; border: 1px solid var(--border-light, #ddd); border-radius: 4px; background: var(--bg-content, #fff); color: var(--text-primary, #333); resize: vertical;"
                ></textarea>

                <!-- Control buttons -->
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <button class="preset-use-btn" style="flex: 1; min-width: 80px;" onclick="CodePlugin.run()">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                        Run
                    </button>
                    <button class="preset-use-btn" style="flex: 1; min-width: 80px;" onclick="CodePlugin.clearEditor()">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                        Clear
                    </button>
                    <button class="preset-use-btn" style="flex: 0.5; min-width: 60px;" onclick="CodePlugin.navigate('prev')" id="code-plugin-prev">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle;">
                            <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                        </svg>
                        Previous
                    </button>
                    <button class="preset-use-btn" style="flex: 0.5; min-width: 60px;" onclick="CodePlugin.navigate('next')" id="code-plugin-next">
                        Next
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle;">
                            <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                        </svg>
                    </button>
                </div>

                <!-- Output area -->
                <div style="border-top: 1px solid var(--border-light, #ddd); padding-top: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: bold; color: var(--text-primary, #333);">Output:</span>
                        <button class="preset-use-btn" style="padding: 2px 6px; font-size: 10px;" onclick="CodePlugin.clearOutput()">Clear output</button>
                    </div>
                    <div id="code-plugin-output" style="min-height: 80px; max-height: 200px; overflow-y: auto; padding: 8px; background: var(--bg-secondary, #f5f5f5); border: 1px solid var(--border-light, #ddd); border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; line-height: 1.4; color: var(--text-primary, #333); white-space: pre-wrap;"></div>
                </div>
            </div>
        `;

        console.log('[CodePlugin] Plugin UI rendered');
    },

    /**
     * Extract all code blocks from chat
     */
    extractCodes() {
        // Try to find the chat messages container - supports single-agent and multi-agent scenarios
        let chatMessages = null;

        // Method 1: find the single-agent container
        chatMessages = document.getElementById('chatMessages');

        // Method 2: if not found, try the currently visible container in multi-agent mode
        if (!chatMessages) {
            const agentChatMessages = document.querySelectorAll('.agent-chat-messages');
            // Find a visible chat messages container
            for (const container of agentChatMessages) {
                const style = window.getComputedStyle(container);
                if (style.display !== 'none' && container.offsetParent !== null) {
                    chatMessages = container;
                    break;
                }
            }
        }

        if (!chatMessages) {
            this.showOutput('Error: chat message container not found. Please use this plugin on the chat page.', 'error');
            return;
        }

        // Find all code blocks
        const codeBlocks = chatMessages.querySelectorAll('.code-block code');
        const extractedCodes = [];

        codeBlocks.forEach((codeElement, index) => {
            const langSpan = codeElement.closest('.code-block')?.querySelector('.code-lang');
            const language = langSpan ? langSpan.textContent.trim().toLowerCase() : 'plaintext';
            const code = codeElement.dataset.rawCode || codeElement.textContent;

            // Skip mindmap code blocks
            if (language !== 'mindmap' && code.trim()) {
                extractedCodes.push({
                    language: language,
                    code: code,
                    index: index + 1
                });
            }
        });

        if (extractedCodes.length === 0) {
            this.showOutput('No code blocks found in chat (excluding mindmap)', 'info');
            if (typeof Notification !== 'undefined') {
                Notification.info('No code found to extract');
            }
            return;
        }

        // Save to state
        this.state.codeBlocks = extractedCodes;
        this.state.currentIndex = 0;

        // Display first code
        this.displayCurrent();

        if (typeof Notification !== 'undefined') {
            Notification.success(`Extracted ${extractedCodes.length} code blocks`);
        }

        console.log('[CodePlugin] Extracted', extractedCodes.length, 'code blocks');
    },

    /**
     * Display current code
     */
    displayCurrent() {
        const { codeBlocks, currentIndex } = this.state;

        console.log('[CodePlugin] displayCurrent called:', {
            codeBlocksCount: codeBlocks.length,
            currentIndex,
            hasContainer: !!this._currentContainer
        });

        if (codeBlocks.length === 0) {
            console.log('[CodePlugin] No code blocks to display');
            return;
        }

        if (!this._currentContainer) {
            console.error('[CodePlugin] Container reference lost');
            return;
        }

        const currentCode = codeBlocks[currentIndex];
        console.log('[CodePlugin] Current code:', {
            language: currentCode.language,
            codeLength: currentCode.code ? currentCode.code.length : 0,
            codePreview: currentCode.code ? currentCode.code.substring(0, 50) : 'null'
        });

        // Query elements within the container scope
        const editor = this._currentContainer.querySelector('#code-plugin-editor');
        const info = this._currentContainer.querySelector('#code-plugin-info');
        const langSelect = this._currentContainer.querySelector('#code-plugin-language');

        console.log('[CodePlugin] Element query results:', {
            editor: !!editor,
            info: !!info,
            langSelect: !!langSelect
        });

        if (editor) {
            editor.value = currentCode.code;
            console.log('[CodePlugin] Code set to editor, length:', editor.value.length);
        } else {
            console.error('[CodePlugin] Editor element not found: #code-plugin-editor');
        }

        if (info) {
            info.textContent = `Code ${currentIndex + 1} / ${codeBlocks.length}`;
        } else {
            console.error('[CodePlugin] Info element not found: #code-plugin-info');
        }

        if (langSelect) {
            // Try to match language
            const validLanguages = ['javascript', 'python', 'html'];
            if (validLanguages.includes(currentCode.language)) {
                langSelect.value = currentCode.language;
            } else if (currentCode.language === 'js') {
                langSelect.value = 'javascript';
            } else if (currentCode.language === 'py') {
                langSelect.value = 'python';
            } else {
                langSelect.value = 'javascript';
            }
            console.log('[CodePlugin] Language set to:', langSelect.value);
        } else {
            console.error('[CodePlugin] Language selector not found: #code-plugin-language');
        }

        // Update button state
        const prevBtn = this._currentContainer.querySelector('#code-plugin-prev');
        const nextBtn = this._currentContainer.querySelector('#code-plugin-next');

        if (prevBtn) {
            prevBtn.disabled = currentIndex === 0;
            prevBtn.style.opacity = currentIndex === 0 ? '0.5' : '1';
        }

        if (nextBtn) {
            nextBtn.disabled = currentIndex === codeBlocks.length - 1;
            nextBtn.style.opacity = currentIndex === codeBlocks.length - 1 ? '0.5' : '1';
        }
    },

    /**
     * Navigate code
     */
    navigate(direction) {
        const { codeBlocks, currentIndex } = this.state;

        if (codeBlocks.length === 0) {
            this.showOutput('Please extract code first', 'info');
            return;
        }

        if (direction === 'prev' && currentIndex > 0) {
            this.state.currentIndex--;
            this.displayCurrent();
        } else if (direction === 'next' && currentIndex < codeBlocks.length - 1) {
            this.state.currentIndex++;
            this.displayCurrent();
        }
    },

    /**
     * Run code
     */
    run() {
        if (!this._currentContainer) {
            console.error('[CodePlugin] Container reference lost');
            return;
        }

        const editor = this._currentContainer.querySelector('#code-plugin-editor');
        const langSelect = this._currentContainer.querySelector('#code-plugin-language');
        const output = this._currentContainer.querySelector('#code-plugin-output');

        if (!editor || !langSelect || !output) {
            console.error('[CodePlugin] Required UI elements not found');
            return;
        }

        const code = editor.value.trim();
        const language = langSelect.value;

        if (!code) {
            this.showOutput('Please enter code', 'error');
            return;
        }

        // Clear previous output
        output.innerHTML = '';
        this.showOutput(`[Running ${language.toUpperCase()} code...]\n`, 'info');

        try {
            if (language === 'javascript') {
                this.runJavaScript(code);
            } else if (language === 'python') {
                this.showOutput('\nPython execution requires backend support. Currently only JavaScript and HTML are supported.', 'error');
            } else if (language === 'html') {
                this.runHTML(code);
            }
        } catch (error) {
            this.showOutput(`\nError: ${error.message}\n${error.stack}`, 'error');
        }
    },

    /**
     * Run JavaScript code
     */
    runJavaScript(code) {
        // Capture console output
        const originalLog = console.log;
        const originalError = console.error;
        const originalWarn = console.warn;

        const logs = [];

        console.log = (...args) => {
            logs.push(args.map(arg => {
                if (typeof arg === 'object') {
                    try {
                        return JSON.stringify(arg, null, 2);
                    } catch (e) {
                        return String(arg);
                    }
                }
                return String(arg);
            }).join(' '));
            originalLog.apply(console, args);
        };

        console.error = (...args) => {
            logs.push('ERROR: ' + args.join(' '));
            originalError.apply(console, args);
        };

        console.warn = (...args) => {
            logs.push('WARN: ' + args.join(' '));
            originalWarn.apply(console, args);
        };

        try {
            // Execute code using Function constructor
            const result = new Function(code)();

            // Restore original console methods
            console.log = originalLog;
            console.error = originalError;
            console.warn = originalWarn;

            // Show output
            if (logs.length > 0) {
                this.showOutput(logs.join('\n'), 'success');
            }

            // Show return value
            if (result !== undefined) {
                this.showOutput(`\n\n[Return value]: ${typeof result === 'object' ? JSON.stringify(result, null, 2) : result}`, 'success');
            }

            if (logs.length === 0 && result === undefined) {
                this.showOutput('\n[Execution completed with no output]', 'success');
            }

        } catch (error) {
            // Restore original console methods
            console.log = originalLog;
            console.error = originalError;
            console.warn = originalWarn;

            this.showOutput(`\nExecution error: ${error.message}`, 'error');
            throw error;
        }
    },

    /**
     * Run HTML code (in an iframe)
     */
    runHTML(code) {
        if (!this._currentContainer) return;

        const output = this._currentContainer.querySelector('#code-plugin-output');
        if (!output) return;

        // Create iframe for preview
        const iframe = document.createElement('iframe');
        iframe.style.cssText = 'width: 100%; height: 300px; border: 1px solid var(--border-light, #ddd); border-radius: 4px; background: white;';

        output.innerHTML = '[HTML Preview]\n';
        output.appendChild(iframe);

        // Write HTML content
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write(code);
        iframeDoc.close();
    },

    /**
     * Show output
     */
    showOutput(message, type = 'info') {
        if (!this._currentContainer) return;

        const output = this._currentContainer.querySelector('#code-plugin-output');
        if (!output) return;

        const messageEl = document.createElement('span');

        if (type === 'error') {
            messageEl.style.color = '#d32f2f';
        } else if (type === 'success') {
            messageEl.style.color = '#388e3c';
        } else {
            messageEl.style.color = 'var(--text-secondary, #666)';
        }

        messageEl.textContent = message;
        output.appendChild(messageEl);

        // Scroll to bottom
        output.scrollTop = output.scrollHeight;
    },

    /**
     * Clear editor
     */
    clearEditor() {
        if (!this._currentContainer) return;

        const editor = this._currentContainer.querySelector('#code-plugin-editor');
        if (editor) {
            editor.value = '';
        }

        if (typeof Notification !== 'undefined') {
            Notification.success('Editor cleared');
        }
    },

    /**
     * Clear output
     */
    clearOutput() {
        if (!this._currentContainer) return;

        const output = this._currentContainer.querySelector('#code-plugin-output');
        if (output) {
            output.innerHTML = '';
        }
    }
};

// Export plugin
if (typeof window !== 'undefined') {
    window.CodePlugin = CodePlugin;
}

export default CodePlugin;
