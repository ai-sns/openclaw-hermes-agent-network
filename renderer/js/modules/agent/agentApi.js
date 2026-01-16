/**
 * Agent API - API调用封装
 * 处理与后端的通信
 */

const agentApi = {
    /**
     * 获取Agent列表
     */
    async getAgents() {
        try {
            const response = await fetch('http://localhost:8788/api/agent');
            return await response.json();
        } catch (error) {
            console.error('获取Agent列表失败:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * 获取单个Agent详情
     */
    async getAgent(agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}`);
            return await response.json();
        } catch (error) {
            console.error('获取 Agent 详情失败:', error);
            throw error;
        }
    },

    /**
     * 获取Agent实例信息
     */
    async getAgentInfo(agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/info`);
            return await response.json();
        } catch (error) {
            console.error('获取Agent实例信息失败:', error);
            throw error;
        }
    },

    /**
     * Agent非流式问答（按ID）
     */
    async agentChat(agentId, message, conversationId = null, options = {}) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId,
                    use_memory: options.use_memory !== false,
                    use_knowledge_base: options.use_knowledge_base !== false
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Agent问答失败:', error);
            throw error;
        }
    },

    /**
     * Agent流式问答（按ID）
     */
    async agentChatStream(agentId, message, conversationId = null, callbacks = {}, options = {}) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/chat/stream`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId,
                    use_memory: options.use_memory !== false,
                    use_knowledge_base: options.use_knowledge_base !== false
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    if (callbacks.onEnd) {
                        callbacks.onEnd();
                    }
                    break;
                }

                buffer += decoder.decode(value, { stream: true });

                const lines = buffer.split('\n');
                buffer = lines.pop() || '';

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        try {
                            const parsed = JSON.parse(data);

                            if (parsed.error) {
                                if (callbacks.onError) {
                                    callbacks.onError(parsed.error);
                                }
                                return { success: false, error: parsed.error };
                            }

                            if (parsed.done) {
                                if (callbacks.onEnd) {
                                    callbacks.onEnd();
                                }
                                return { success: true };
                            }

                            if (parsed.content) {
                                if (callbacks.onData) {
                                    callbacks.onData(parsed.content);
                                }
                            }
                        } catch (e) {
                            console.warn('Failed to parse SSE data:', data);
                        }
                    }
                }
            }

            return { success: true };
        } catch (error) {
            console.error('Agent流式问答失败:', error);
            if (callbacks.onError) {
                callbacks.onError(error.message);
            }
            throw error;
        }
    },

    /**
     * Agent问答（按名称）
     */
    async agentChatByName(agentName, message, conversationId = null, options = {}) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/name/${encodeURIComponent(agentName)}/chat`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId,
                    use_memory: options.use_memory !== false,
                    use_knowledge_base: options.use_knowledge_base !== false
                })
            });
            return await response.json();
        } catch (error) {
            console.error('Agent问答失败:', error);
            throw error;
        }
    },

    /**
     * 清除Agent记忆
     */
    async clearAgentMemory(agentId, conversationId = null) {
        try {
            const url = conversationId
                ? `http://localhost:8788/api/agent/${agentId}/memory?conversation_id=${conversationId}`
                : `http://localhost:8788/api/agent/${agentId}/memory`;

            const response = await fetch(url, {
                method: 'DELETE'
            });
            return await response.json();
        } catch (error) {
            console.error('清除记忆失败:', error);
            throw error;
        }
    },

    /**
     * 获取Agent记忆
     */
    async getAgentMemory(agentId, conversationId = null) {
        try {
            const url = conversationId
                ? `http://localhost:8788/api/agent/${agentId}/memory?conversation_id=${conversationId}`
                : `http://localhost:8788/api/agent/${agentId}/memory`;

            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('获取记忆失败:', error);
            throw error;
        }
    },

    /**
     * 重新加载Agent
     */
    async reloadAgent(agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/reload`, {
                method: 'POST'
            });
            return await response.json();
        } catch (error) {
            console.error('重新加载Agent失败:', error);
            throw error;
        }
    },

    /**
     * 创建Agent
     */
    async createAgent(agentData) {
        try {
            if (window.api && window.api.createAgent) {
                return await window.api.createAgent(agentData);
            }
            // 模拟创建
            return {
                success: true,
                data: { id: Date.now(), ...agentData }
            };
        } catch (error) {
            console.error('创建Agent失败:', error);
            throw error;
        }
    },

    /**
     * 获取聊天历史
     */
    async getChatHistory() {
        try {
            // 调用新的对话列表API
            return await this.getConversations();
        } catch (error) {
            console.error('获取聊天历史失败:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * 获取对话列表
     */
    async getConversations(limit = 50, agentId = null) {
        try {
            let url = `http://localhost:8788/api/chat/conversations?limit=${limit}`;
            if (agentId !== null) {
                url += `&agent_id=${agentId}`;
            }
            const response = await fetch(url);
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('获取对话列表失败:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * 获取对话消息
     */
    async getConversationMessages(conversationId) {
        try {
            const response = await fetch(`http://localhost:8788/api/chat/conversations/${conversationId}`);
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('获取对话消息失败:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * 发送消息 (流式) - 使用 HTTP SSE
     */
    async sendMessageStream(messages, requestId, modelConfigId = null, modelConfig = null, conversationId = null, callbacks = {}) {
        try {
            // 构建请求体
            const requestBody = {
                messages: messages,
                conversation_id: conversationId,  // 添加conversation_id
                model_config_id: modelConfigId
            };

            // 如果提供了模型配置，使用其参数
            if (modelConfig) {
                if (modelConfig.temperature !== undefined) {
                    requestBody.temperature = modelConfig.temperature;
                }
                if (modelConfig.max_tokens !== undefined) {
                    requestBody.max_tokens = modelConfig.max_tokens;
                }
            }

            // 使用 fetch 进行 SSE 请求
            const response = await fetch('http://localhost:8788/api/chat/stream', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'Accept': 'text/event-stream'
                },
                body: JSON.stringify(requestBody)
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            // 读取流式数据
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    // 通知流结束
                    if (callbacks.onEnd) {
                        callbacks.onEnd({ requestId });
                    }
                    break;
                }

                // 解码数据
                buffer += decoder.decode(value, { stream: true });

                // 按行分割
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // 保留不完整的行

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            // 流结束
                            if (callbacks.onEnd) {
                                callbacks.onEnd({ requestId });
                            }
                            return { success: true };
                        }

                        try {
                            const parsed = JSON.parse(data);

                            // 处理错误
                            if (parsed.error) {
                                if (callbacks.onError) {
                                    callbacks.onError({
                                        requestId,
                                        error: parsed.error
                                    });
                                }
                                return { success: false, error: parsed.error };
                            }

                            // 处理内容
                            if (parsed.content) {
                                if (callbacks.onData) {
                                    callbacks.onData({
                                        requestId,
                                        content: parsed.content
                                    });
                                }
                            }
                        } catch (e) {
                            console.warn('Failed to parse SSE data:', data);
                        }
                    } else if (line.startsWith('event: ')) {
                        const event = line.slice(7);
                        if (event === 'error') {
                            // 错误事件将在下一行的 data 中
                            continue;
                        }
                    }
                }
            }

            return { success: true };
        } catch (error) {
            console.error('发送消息失败:', error);

            // 通知错误
            if (callbacks.onError) {
                callbacks.onError({
                    requestId,
                    error: error.message
                });
            }

            throw error;
        }
    },

    /**
     * 发送消息 (流式) - 兼容旧的 electronAPI 方式
     */
    async sendMessageStreamLegacy(messages, requestId) {
        try {
            if (window.electronAPI && window.electronAPI.chatStreamStart) {
                window.electronAPI.chatStreamStart(messages, requestId);
                return { success: true };
            }
            // 如果没有 electronAPI，返回失败
            throw new Error('流式聊天API不可用');
        } catch (error) {
            console.error('发送消息失败:', error);
            throw error;
        }
    },

    /**
     * 发送消息 (非流式，用于兼容)
     */
    async sendMessage(messages) {
        try {
            if (window.api && window.api.chat) {
                return await window.api.chat({ messages });
            }
            // 模拟响应
            return {
                success: true,
                data: {
                    role: 'assistant',
                    content: '这是一个模拟响应。'
                }
            };
        } catch (error) {
            console.error('发送消息失败:', error);
            throw error;
        }
    },

    /**
     * 删除聊天
     */
    async deleteChat(chatId) {
        try {
            if (window.api && window.api.deleteChat) {
                return await window.api.deleteChat(chatId);
            }
            return { success: true };
        } catch (error) {
            console.error('删除聊天失败:', error);
            throw error;
        }
    },

    /**
     * 更新聊天标题
     */
    async updateChatTitle(chatId, title) {
        try {
            if (window.api && window.api.updateChatTitle) {
                return await window.api.updateChatTitle(chatId, title);
            }
            return { success: true };
        } catch (error) {
            console.error('更新聊天标题失败:', error);
            throw error;
        }
    },

    /**
     * 收藏/取消收藏聊天
     */
    async toggleChatStar(chatId, starred) {
        try {
            if (window.api && window.api.toggleChatStar) {
                return await window.api.toggleChatStar(chatId, starred);
            }
            return { success: true };
        } catch (error) {
            console.error('收藏操作失败:', error);
            throw error;
        }
    },

    /**
     * 创建区块链钱包
     */
    async createWallet(label = '') {
        try {
            const response = await fetch('http://localhost:8788/api/wallet/create', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label })
            });
            return await response.json();
        } catch (error) {
            console.error('创建钱包失败:', error);
            throw error;
        }
    },

    /**
     * 导入区块链钱包
     */
    async importWallet(privateKey, label = '') {
        try {
            const response = await fetch('http://localhost:8788/api/wallet/import', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ private_key: privateKey, label })
            });
            return await response.json();
        } catch (error) {
            console.error('导入钱包失败:', error);
            throw error;
        }
    },

    /**
     * 获取钱包列表
     */
    async listWallets() {
        try {
            const response = await fetch('http://localhost:8788/api/wallet/list');
            return await response.json();
        } catch (error) {
            console.error('获取钱包列表失败:', error);
            throw error;
        }
    },

    /**
     * 获取钱包信息
     */
    async getWallet(address) {
        try {
            const response = await fetch(`http://localhost:8788/api/wallet/${address}`);
            return await response.json();
        } catch (error) {
            console.error('获取钱包信息失败:', error);
            throw error;
        }
    },

    /**
     * 更新 Agent 配置
     */
    async updateAgent(agentId, agentData) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}`, {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(agentData)
            });
            return await response.json();
        } catch (error) {
            console.error('更新 Agent 失败:', error);
            throw error;
        }
    },

    // ==================== Agent Tools Management ====================

    /**
     * 获取Agent的关联工具
     */
    async getAgentTools(agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/tools`);
            return await response.json();
        } catch (error) {
            console.error('获取Agent工具失败:', error);
            return { success: false, data: { tools: [] } };
        }
    },

    /**
     * 更新Agent的关联工具
     */
    async updateAgentTools(agentId, tools) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/tools`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(tools)
            });
            return await response.json();
        } catch (error) {
            console.error('更新Agent工具失败:', error);
            throw error;
        }
    },

    /**
     * 获取所有可用工具
     */
    async getAvailableTools(agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/available-tools`);
            return await response.json();
        } catch (error) {
            console.error('获取可用工具失败:', error);
            return { success: false, data: {} };
        }
    },

    /**
     * 获取Agent已配置的工具
     */
    async getAgentTools(agentId) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/tools`);
            return await response.json();
        } catch (error) {
            console.error('获取Agent工具配置失败:', error);
            return [];
        }
    },

    /**
     * 更新Agent的工具配置
     */
    async updateAgentTools(agentId, tools) {
        try {
            const response = await fetch(`http://localhost:8788/api/agent/${agentId}/tools`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({ tools })
            });
            return await response.json();
        } catch (error) {
            console.error('更新Agent工具配置失败:', error);
            throw error;
        }
    },

    // ==================== 以下是旧的通用Chat API（保留兼容性） ====================
};

// 导出为ES6模块
export default agentApi;

// 同时导出到window对象供非模块脚本使用
window.agentApi = agentApi;
