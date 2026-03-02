/**
 * Agent API - API call wrapper
 * Handles communication with the backend
 */

const agentApi = {
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
     * Get agent list
     */
    async getAgents() {
        try {
            const response = await fetch(this.resolve('/api/agent'));
            return await response.json();
        } catch (error) {
            console.error('Failed to get agent list:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * Get agent details
     */
    async getAgent(agentId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}`));
            return await response.json();
        } catch (error) {
            console.error('Failed to get agent details:', error);
            throw error;
        }
    },

    async agentChatStreamWithFiles(agentId, message, conversationId = null, files = [], callbacks = {}, options = {}) {
        try {
            const formData = new FormData();
            formData.append('message', message);
            if (conversationId) {
                formData.append('conversation_id', conversationId);
            }
            formData.append('use_memory', options.use_memory !== false ? 'true' : 'false');
            formData.append('use_knowledge_base', options.use_knowledge_base !== false ? 'true' : 'false');

            (files || []).forEach(f => {
                formData.append('files', f);
            });

            const response = await fetch(this.resolve(`/api/agent/${agentId}/chat/stream-with-files`), {
                method: 'POST',
                headers: {
                    'Accept': 'text/event-stream'
                },
                body: formData
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
                        callbacks.onEnd([]);
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
                                    callbacks.onEnd(parsed.attachments || []);
                                }
                                return { success: true, attachments: parsed.attachments || [] };
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
            console.error('Agent streaming chat (with attachments) failed:', error);
            if (callbacks.onError) {
                callbacks.onError(error.message);
            }
            throw error;
        }
    },

    /**
     * Get agent instance info
     */
    async getAgentInfo(agentId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}/info`));
            return await response.json();
        } catch (error) {
            console.error('Failed to get agent instance info:', error);
            throw error;
        }
    },

    /**
     * Agent non-streaming chat (by ID)
     */
    async agentChat(agentId, message, conversationId = null, options = {}) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}/chat`), {
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
            console.error('Agent chat failed:', error);
            throw error;
        }
    },

    /**
     * Agent streaming chat (by ID)
     */
    async agentChatStream(agentId, message, conversationId = null, callbacks = {}, options = {}) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${agentId}/chat/stream`), {
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
            console.error('Agent streaming chat failed:', error);
            if (callbacks.onError) {
                callbacks.onError(error.message);
            }
            throw error;
        }
    },

    /**
     * Agent chat (by name)
     */
    async agentChatByName(agentName, message, conversationId = null, options = {}) {
        try {
            const response = await fetch(this.resolve(`/api/agent/name/${encodeURIComponent(agentName)}/chat`), {
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
            console.error('Agent chat failed:', error);
            throw error;
        }
    },

    /**
     * Clear agent memory
     */
    async clearAgentMemory(agentId, conversationId = null) {
        try {
            const path = conversationId
                ? `/api/agent/${encodeURIComponent(agentId)}/memory?conversation_id=${encodeURIComponent(conversationId)}`
                : `/api/agent/${encodeURIComponent(agentId)}/memory`;

            const response = await fetch(this.resolve(path), {
                method: 'DELETE'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to clear memory:', error);
            throw error;
        }
    },

    /**
     * Get agent memory
     */
    async getAgentMemory(agentId, conversationId = null) {
        try {
            const path = conversationId
                ? `/api/agent/${encodeURIComponent(agentId)}/memory?conversation_id=${encodeURIComponent(conversationId)}`
                : `/api/agent/${encodeURIComponent(agentId)}/memory`;

            const response = await fetch(this.resolve(path));
            return await response.json();
        } catch (error) {
            console.error('Failed to get memory:', error);
            throw error;
        }
    },

    /**
     * Reload agent
     */
    async reloadAgent(agentId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${encodeURIComponent(agentId)}/reload`), {
                method: 'POST'
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to reload agent:', error);
            throw error;
        }
    },

    /**
     * Create agent
     */
    async createAgent(agentData) {
        try {
            if (window.api && window.api.createAgent) {
                return await window.api.createAgent(agentData);
            }
            // Mock create
            return {
                success: true,
                data: { id: Date.now(), ...agentData }
            };
        } catch (error) {
            console.error('Failed to create agent:', error);
            throw error;
        }
    },

    /**
     * Get chat history
     */
    async getChatHistory() {
        try {
            // Call the newer conversations list API
            return await this.getConversations();
        } catch (error) {
            console.error('Failed to get chat history:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * Get conversations list
     */
    async getConversations(limit = 50, agentId = null) {
        try {
            let path = `/api/chat/conversations?limit=${encodeURIComponent(limit)}`;
            if (agentId !== null) {
                path += `&agent_id=${encodeURIComponent(agentId)}`;
            }
            const response = await fetch(this.resolve(path));
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Failed to get conversation list:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * Get conversation messages
     */
    async getConversationMessages(conversationId) {
        try {
            const response = await fetch(this.resolve(`/api/chat/conversations/${encodeURIComponent(conversationId)}`));
            const result = await response.json();
            return result;
        } catch (error) {
            console.error('Failed to get conversation messages:', error);
            return { success: false, data: [] };
        }
    },

    /**
     * Send message (streaming) - via HTTP SSE
     */
    async sendMessageStream(messages, requestId, modelConfigId = null, modelConfig = null, conversationId = null, callbacks = {}) {
        try {
            // Build request payload
            const requestBody = {
                messages: messages,
                conversation_id: conversationId,  // Add conversation_id
                model_config_id: modelConfigId
            };

            // If a model config is provided, use its params
            if (modelConfig) {
                if (modelConfig.temperature !== undefined) {
                    requestBody.temperature = modelConfig.temperature;
                }
                if (modelConfig.max_tokens !== undefined) {
                    requestBody.max_tokens = modelConfig.max_tokens;
                }
            }

            // Use fetch to make the SSE request
            const response = await fetch(this.resolve('/api/chat/stream'), {
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

            // Read streaming data
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    // Notify stream end
                    if (callbacks.onEnd) {
                        callbacks.onEnd({ requestId });
                    }
                    break;
                }

                // Decode data
                buffer += decoder.decode(value, { stream: true });

                // Split by line
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // Keep the incomplete line

                for (const line of lines) {
                    if (line.startsWith('data: ')) {
                        const data = line.slice(6);

                        if (data === '[DONE]') {
                            // Stream ended
                            if (callbacks.onEnd) {
                                callbacks.onEnd({ requestId });
                            }
                            return { success: true };
                        }

                        try {
                            const parsed = JSON.parse(data);

                            // Handle error
                            if (parsed.error) {
                                if (callbacks.onError) {
                                    callbacks.onError({
                                        requestId,
                                        error: parsed.error
                                    });
                                }
                                return { success: false, error: parsed.error };
                            }

                            // Handle content
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
                            // The error event details will be in data on the next line
                            continue;
                        }
                    }
                }
            }

            return { success: true };
        } catch (error) {
            console.error('Failed to send message:', error);

            // Notify error
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
     * Send message (streaming) - legacy electronAPI compatibility
     */
    async sendMessageStreamLegacy(messages, requestId) {
        try {
            if (window.electronAPI && window.electronAPI.chatStreamStart) {
                window.electronAPI.chatStreamStart(messages, requestId);
                return { success: true };
            }
            // If electronAPI is not available, fail
            throw new Error('Streaming chat API is not available');
        } catch (error) {
            console.error('Failed to send message:', error);
            throw error;
        }
    },

    /**
     * Send message (non-streaming, for compatibility)
     */
    async sendMessage(messages) {
        try {
            if (window.api && window.api.chat) {
                return await window.api.chat({ messages });
            }
            // Mock response
            return {
                success: true,
                data: {
                    role: 'assistant',
                    content: 'This is a mock response.'
                }
            };
        } catch (error) {
            console.error('Failed to send message:', error);
            throw error;
        }
    },

    /**
     * Delete chat
     */
    async deleteChat(chatId) {
        try {
            if (window.api && window.api.deleteChat) {
                return await window.api.deleteChat(chatId);
            }
            return { success: true };
        } catch (error) {
            console.error('Failed to delete chat:', error);
            throw error;
        }
    },

    /**
     * Update chat title
     */
    async updateChatTitle(chatId, title) {
        try {
            if (window.api && window.api.updateChatTitle) {
                return await window.api.updateChatTitle(chatId, title);
            }
            return { success: true };
        } catch (error) {
            console.error('Failed to update chat title:', error);
            throw error;
        }
    },

    /**
     * Star/unstar chat
     */
    async toggleChatStar(chatId, starred) {
        try {
            if (window.api && window.api.toggleChatStar) {
                return await window.api.toggleChatStar(chatId, starred);
            }
            return { success: true };
        } catch (error) {
            console.error('Favorite operation failed:', error);
            throw error;
        }
    },

    /**
     * Create blockchain wallet
     */
    async createWallet(label = '') {
        try {
            const response = await fetch(this.resolve('/api/wallet/create'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ label })
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to create wallet:', error);
            throw error;
        }
    },

    /**
     * Import blockchain wallet
     */
    async importWallet(privateKey, label = '') {
        try {
            const response = await fetch(this.resolve('/api/wallet/import'), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ private_key: privateKey, label })
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to import wallet:', error);
            throw error;
        }
    },

    /**
     * Get wallet list
     */
    async listWallets() {
        try {
            const response = await fetch(this.resolve('/api/wallet/list'));
            return await response.json();
        } catch (error) {
            console.error('Failed to get wallet list:', error);
            throw error;
        }
    },

    /**
     * Get wallet info
     */
    async getWallet(address) {
        try {
            const response = await fetch(this.resolve(`/api/wallet/${encodeURIComponent(address)}`));
            return await response.json();
        } catch (error) {
            console.error('Failed to get wallet info:', error);
            throw error;
        }
    },

    /**
     * Update agent config
     */
    async updateAgent(agentId, agentData) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${encodeURIComponent(agentId)}`), {
                method: 'PUT',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify(agentData)
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to update agent:', error);
            throw error;
        }
    },

    // ==================== Agent Tools Management ====================

    /**
     * Get agent linked tools
     */
    async getAgentTools(agentId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${encodeURIComponent(agentId)}/tools`));
            return await response.json();
        } catch (error) {
            console.error('Failed to get agent tools:', error);
            return { success: false, data: { agent_id: agentId, tools: [] } };
        }
    },

    /**
     * Update agent linked tools
     */
    async updateAgentTools(agentId, tools) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${encodeURIComponent(agentId)}/tools`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ tools })
            });
            return await response.json();
        } catch (error) {
            console.error('Failed to update agent tools:', error);
            throw error;
        }
    },

    /**
     * Get all available tools
     */
    async getAvailableTools(agentId) {
        try {
            const response = await fetch(this.resolve(`/api/agent/${encodeURIComponent(agentId)}/available-tools`));
            return await response.json();
        } catch (error) {
            console.error('Failed to get available tools:', error);
            return { success: false, data: {} };
        }
    },

    // ==================== Legacy generic Chat API (kept for compatibility) ====================
};

// Export as ES6 module
export default agentApi;

// Also export to window for non-module scripts
window.agentApi = agentApi;
