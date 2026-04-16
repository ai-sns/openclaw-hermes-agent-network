/**
 * Agent API - API call wrapper
 * Handles communication with the backend
 */

const agentApi = {
    // Store abort controllers for active requests
    _activeStreamControllers: new Map(),
    _activeNonStreamControllers: new Map(),
    
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
            formData.append('show_token_usage', options.show_token_usage ? 'true' : 'false');

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

            let finalUsage = null;
            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    if (callbacks.onEnd) {
                        callbacks.onEnd([], finalUsage);
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
                                    callbacks.onEnd(parsed.attachments || [], finalUsage);
                                }
                                return { success: true, attachments: parsed.attachments || [], usage: finalUsage };
                            }

                            if (parsed.usage) {
                                finalUsage = parsed.usage;
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
        let controllerKey = null;
        try {
            const abortController = new AbortController();
            const requestId = options && (options.requestId || options.request_id) ? String(options.requestId || options.request_id) : null;
            controllerKey = requestId
                ? `nonstream_${agentId}_${requestId}`
                : `nonstream_${agentId}_${Date.now()}`;
            this._activeNonStreamControllers.set(controllerKey, abortController);

            const response = await fetch(this.resolve(`/api/agent/${agentId}/chat`), {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    message: message,
                    conversation_id: conversationId,
                    use_memory: options.use_memory !== false,
                    use_knowledge_base: options.use_knowledge_base !== false,
                    show_token_usage: !!options.show_token_usage
                }),
                signal: abortController.signal
            });
            return await response.json();
        } catch (error) {
            console.error('Agent chat failed:', error);
            throw error;
        } finally {
            try {
                if (controllerKey) {
                    this._activeNonStreamControllers.delete(controllerKey);
                }
            } catch (e) {
            }
        }
    },

    /**
     * Agent streaming chat (by ID)
     */
    async agentChatStream(agentId, message, conversationId = null, callbacks = {}, options = {}) {
        try {
            // Create abort controller for this request
            const abortController = new AbortController();
            const requestId = `stream_${agentId}_${Date.now()}`;
            this._activeStreamControllers.set(requestId, abortController);
            
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
                    use_knowledge_base: options.use_knowledge_base !== false,
                    show_token_usage: !!options.show_token_usage
                }),
                signal: abortController.signal
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            let finalUsage = null;

            while (true) {
                const { done, value } = await reader.read();

                if (done) {
                    // Clean up abort controller
                    this._activeStreamControllers.delete(requestId);
                    
                    if (callbacks.onEnd) {
                        callbacks.onEnd([], finalUsage);
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
                                    callbacks.onEnd([], finalUsage);
                                }
                                return { success: true };
                            }

                            if (parsed.content) {
                                if (callbacks.onData) {
                                    callbacks.onData(parsed.content);
                                }
                            }

                            if (parsed.usage) {
                                finalUsage = parsed.usage;
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
     * Cancel active streaming request for an agent
     */
    cancelActiveStream(agentId) {
        // Find and abort any active stream for this agent
        let cancelled = false;
        this._activeStreamControllers.forEach((controller, requestId) => {
            if (requestId.includes(`stream_${agentId}_`)) {
                controller.abort();
                this._activeStreamControllers.delete(requestId);
                cancelled = true;
                console.log('[AgentApi] Cancelled active stream for agent:', agentId);
            }
        });
        return cancelled;
    },

    cancelActiveNonStream(agentId, requestId = null) {
        let cancelled = false;
        const prefix = requestId
            ? `nonstream_${agentId}_${String(requestId)}`
            : `nonstream_${agentId}_`;
        this._activeNonStreamControllers.forEach((controller, key) => {
            if (String(key).startsWith(prefix)) {
                try {
                    controller.abort();
                } catch (e) {
                }
                this._activeNonStreamControllers.delete(key);
                cancelled = true;
                console.log('[AgentApi] Cancelled active non-stream request for agent:', agentId);
            }
        });
        return cancelled;
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
