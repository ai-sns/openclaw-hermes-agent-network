/**
 * Code Plugin - 代码执行插件
 * 从聊天中提取代码并在浏览器中运行
 */

const CodePlugin = {
    /**
     * 插件信息
     */
    info: {
        id: 'code',
        name: '代码执行插件',
        version: '1.0.0',
        description: '从聊天中提取代码块，提供编辑和运行功能'
    },

    /**
     * 插件状态
     */
    state: {
        codeBlocks: [],
        currentIndex: 0
    },

    /**
     * 当前渲染的容器（用于多实例支持）
     */
    _currentContainer: null,

    /**
     * 渲染插件UI
     */
    render(container) {
        // 保存当前容器引用
        this._currentContainer = container;
        container.innerHTML = `
            <div style="padding: 12px; display: flex; flex-direction: column; gap: 12px; height: 100%;">
                <!-- 代码信息栏 -->
                <div style="display: flex; justify-content: space-between; align-items: center; padding: 8px; background: var(--bg-secondary, #f5f5f5); border-radius: 4px;">
                    <div style="display: flex; align-items: center; gap: 8px;">
                        <span style="font-size: 10px; color: var(--text-secondary, #666);" id="code-plugin-info">未提取代码</span>
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
                        提取代码
                    </button>
                </div>

                <!-- 代码编辑器 -->
                <textarea
                    id="code-plugin-editor"
                    placeholder="点击'提取代码'按钮从聊天中获取代码，或直接在此编写代码..."
                    style="flex: 1; min-height: 200px; padding: 12px; font-family: 'Consolas', 'Monaco', monospace; font-size: 12px; line-height: 1.5; border: 1px solid var(--border-light, #ddd); border-radius: 4px; background: var(--bg-content, #fff); color: var(--text-primary, #333); resize: vertical;"
                ></textarea>

                <!-- 控制按钮组 -->
                <div style="display: flex; gap: 8px; flex-wrap: wrap;">
                    <button class="preset-use-btn" style="flex: 1; min-width: 80px;" onclick="CodePlugin.run()">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                            <path d="M8 5v14l11-7z"/>
                        </svg>
                        运行
                    </button>
                    <button class="preset-use-btn" style="flex: 1; min-width: 80px;" onclick="CodePlugin.clearEditor()">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle; margin-right: 4px;">
                            <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                        </svg>
                        清空
                    </button>
                    <button class="preset-use-btn" style="flex: 0.5; min-width: 60px;" onclick="CodePlugin.navigate('prev')" id="code-plugin-prev">
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle;">
                            <path d="M15.41 7.41L14 6l-6 6 6 6 1.41-1.41L10.83 12z"/>
                        </svg>
                        上一个
                    </button>
                    <button class="preset-use-btn" style="flex: 0.5; min-width: 60px;" onclick="CodePlugin.navigate('next')" id="code-plugin-next">
                        下一个
                        <svg viewBox="0 0 24 24" width="14" height="14" fill="currentColor" style="vertical-align: middle;">
                            <path d="M10 6L8.59 7.41 13.17 12l-4.58 4.59L10 18l6-6z"/>
                        </svg>
                    </button>
                </div>

                <!-- 输出区域 -->
                <div style="border-top: 1px solid var(--border-light, #ddd); padding-top: 12px;">
                    <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 8px;">
                        <span style="font-size: 11px; font-weight: bold; color: var(--text-primary, #333);">输出结果：</span>
                        <button class="preset-use-btn" style="padding: 2px 6px; font-size: 10px;" onclick="CodePlugin.clearOutput()">清空输出</button>
                    </div>
                    <div id="code-plugin-output" style="min-height: 80px; max-height: 200px; overflow-y: auto; padding: 8px; background: var(--bg-secondary, #f5f5f5); border: 1px solid var(--border-light, #ddd); border-radius: 4px; font-family: 'Consolas', 'Monaco', monospace; font-size: 11px; line-height: 1.4; color: var(--text-primary, #333); white-space: pre-wrap;"></div>
                </div>
            </div>
        `;

        console.log('[CodePlugin] 插件UI已渲染');
    },

    /**
     * 从聊天中提取所有代码块
     */
    extractCodes() {
        // 尝试找到聊天消息容器 - 支持单agent和多agent场景
        let chatMessages = null;

        // 方法1：查找单agent场景的容器
        chatMessages = document.getElementById('chatMessages');

        // 方法2：如果找不到，尝试查找多agent场景下当前显示的容器
        if (!chatMessages) {
            const agentChatMessages = document.querySelectorAll('.agent-chat-messages');
            // 找到可见的聊天消息容器
            for (const container of agentChatMessages) {
                const style = window.getComputedStyle(container);
                if (style.display !== 'none' && container.offsetParent !== null) {
                    chatMessages = container;
                    break;
                }
            }
        }

        if (!chatMessages) {
            this.showOutput('错误: 未找到聊天消息容器。请确保在聊天页面使用此插件。', 'error');
            return;
        }

        // 查找所有代码块
        const codeBlocks = chatMessages.querySelectorAll('.code-block code');
        const extractedCodes = [];

        codeBlocks.forEach((codeElement, index) => {
            const langSpan = codeElement.closest('.code-block')?.querySelector('.code-lang');
            const language = langSpan ? langSpan.textContent.trim().toLowerCase() : 'plaintext';
            const code = codeElement.dataset.rawCode || codeElement.textContent;

            // 跳过 mindmap 代码块
            if (language !== 'mindmap' && code.trim()) {
                extractedCodes.push({
                    language: language,
                    code: code,
                    index: index + 1
                });
            }
        });

        if (extractedCodes.length === 0) {
            this.showOutput('未在聊天中找到代码块（mindmap 除外）', 'info');
            if (typeof Notification !== 'undefined') {
                Notification.info('未找到可提取的代码');
            }
            return;
        }

        // 保存到状态
        this.state.codeBlocks = extractedCodes;
        this.state.currentIndex = 0;

        // 显示第一个代码
        this.displayCurrent();

        if (typeof Notification !== 'undefined') {
            Notification.success(`已提取 ${extractedCodes.length} 个代码块`);
        }

        console.log('[CodePlugin] 提取了', extractedCodes.length, '个代码块');
    },

    /**
     * 显示当前代码
     */
    displayCurrent() {
        const { codeBlocks, currentIndex } = this.state;

        console.log('[CodePlugin] displayCurrent 调用:', {
            codeBlocksCount: codeBlocks.length,
            currentIndex,
            hasContainer: !!this._currentContainer
        });

        if (codeBlocks.length === 0) {
            console.log('[CodePlugin] 没有代码块可显示');
            return;
        }

        if (!this._currentContainer) {
            console.error('[CodePlugin] 容器引用丢失');
            return;
        }

        const currentCode = codeBlocks[currentIndex];
        console.log('[CodePlugin] 当前代码:', {
            language: currentCode.language,
            codeLength: currentCode.code ? currentCode.code.length : 0,
            codePreview: currentCode.code ? currentCode.code.substring(0, 50) : 'null'
        });

        // 在容器作用域内查找元素
        const editor = this._currentContainer.querySelector('#code-plugin-editor');
        const info = this._currentContainer.querySelector('#code-plugin-info');
        const langSelect = this._currentContainer.querySelector('#code-plugin-language');

        console.log('[CodePlugin] 元素查找结果:', {
            editor: !!editor,
            info: !!info,
            langSelect: !!langSelect
        });

        if (editor) {
            editor.value = currentCode.code;
            console.log('[CodePlugin] 代码已设置到编辑器，长度:', editor.value.length);
        } else {
            console.error('[CodePlugin] 未找到编辑器元素 #code-plugin-editor');
        }

        if (info) {
            info.textContent = `代码 ${currentIndex + 1} / ${codeBlocks.length}`;
        } else {
            console.error('[CodePlugin] 未找到信息元素 #code-plugin-info');
        }

        if (langSelect) {
            // 尝试匹配语言
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
            console.log('[CodePlugin] 语言已设置为:', langSelect.value);
        } else {
            console.error('[CodePlugin] 未找到语言选择器 #code-plugin-language');
        }

        // 更新按钮状态
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
     * 导航代码
     */
    navigate(direction) {
        const { codeBlocks, currentIndex } = this.state;

        if (codeBlocks.length === 0) {
            this.showOutput('请先提取代码', 'info');
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
     * 运行代码
     */
    run() {
        if (!this._currentContainer) {
            console.error('[CodePlugin] 容器引用丢失');
            return;
        }

        const editor = this._currentContainer.querySelector('#code-plugin-editor');
        const langSelect = this._currentContainer.querySelector('#code-plugin-language');
        const output = this._currentContainer.querySelector('#code-plugin-output');

        if (!editor || !langSelect || !output) {
            console.error('[CodePlugin] 未找到必要的UI元素');
            return;
        }

        const code = editor.value.trim();
        const language = langSelect.value;

        if (!code) {
            this.showOutput('请输入代码', 'error');
            return;
        }

        // 清空之前的输出
        output.innerHTML = '';
        this.showOutput(`[运行 ${language.toUpperCase()} 代码...]\n`, 'info');

        try {
            if (language === 'javascript') {
                this.runJavaScript(code);
            } else if (language === 'python') {
                this.showOutput('\nPython 执行需要后端支持，当前仅支持 JavaScript 和 HTML', 'error');
            } else if (language === 'html') {
                this.runHTML(code);
            }
        } catch (error) {
            this.showOutput(`\n错误: ${error.message}\n${error.stack}`, 'error');
        }
    },

    /**
     * 运行 JavaScript 代码
     */
    runJavaScript(code) {
        // 捕获 console 输出
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
            // 使用 Function 构造函数执行代码
            const result = new Function(code)();

            // 恢复原始 console 方法
            console.log = originalLog;
            console.error = originalError;
            console.warn = originalWarn;

            // 显示输出
            if (logs.length > 0) {
                this.showOutput(logs.join('\n'), 'success');
            }

            // 显示返回值
            if (result !== undefined) {
                this.showOutput(`\n\n[返回值]: ${typeof result === 'object' ? JSON.stringify(result, null, 2) : result}`, 'success');
            }

            if (logs.length === 0 && result === undefined) {
                this.showOutput('\n[代码执行完成，无输出]', 'success');
            }

        } catch (error) {
            // 恢复原始 console 方法
            console.log = originalLog;
            console.error = originalError;
            console.warn = originalWarn;

            this.showOutput(`\n执行错误: ${error.message}`, 'error');
            throw error;
        }
    },

    /**
     * 运行 HTML 代码（在 iframe 中）
     */
    runHTML(code) {
        if (!this._currentContainer) return;

        const output = this._currentContainer.querySelector('#code-plugin-output');
        if (!output) return;

        // 创建 iframe 用于预览
        const iframe = document.createElement('iframe');
        iframe.style.cssText = 'width: 100%; height: 300px; border: 1px solid var(--border-light, #ddd); border-radius: 4px; background: white;';

        output.innerHTML = '[HTML 预览]\n';
        output.appendChild(iframe);

        // 写入 HTML 内容
        const iframeDoc = iframe.contentDocument || iframe.contentWindow.document;
        iframeDoc.open();
        iframeDoc.write(code);
        iframeDoc.close();
    },

    /**
     * 显示输出
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

        // 滚动到底部
        output.scrollTop = output.scrollHeight;
    },

    /**
     * 清空编辑器
     */
    clearEditor() {
        if (!this._currentContainer) return;

        const editor = this._currentContainer.querySelector('#code-plugin-editor');
        if (editor) {
            editor.value = '';
        }

        if (typeof Notification !== 'undefined') {
            Notification.success('编辑器已清空');
        }
    },

    /**
     * 清空输出
     */
    clearOutput() {
        if (!this._currentContainer) return;

        const output = this._currentContainer.querySelector('#code-plugin-output');
        if (output) {
            output.innerHTML = '';
        }
    }
};

// 导出插件
if (typeof window !== 'undefined') {
    window.CodePlugin = CodePlugin;
}

export default CodePlugin;
