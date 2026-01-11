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
            if (window.api && window.api.getAgents) {
                return await window.api.getAgents();
            }
            // 模拟数据
            return {
                success: true,
                data: [
                    { id: 1, name: 'Balabala', model: 'GPT-4' },
                    { id: 2, name: 'Justin', model: 'Claude 3' },
                    { id: 3, name: 'Peter', model: 'DeepSeek' },
                    { id: 4, name: 'Musk (Planner)', model: 'GPT-4' },
                    { id: 5, name: 'Mike (Critic)', model: 'GPT-3.5' }
                ]
            };
        } catch (error) {
            console.error('获取Agent列表失败:', error);
            return { success: false, data: [] };
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
    async getConversations(limit = 50) {
        try {
            const response = await fetch(`http://localhost:8788/api/chat/conversations?limit=${limit}`);
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
    }
};

export default agentApi;
