/**
 * AI-SNS API Client
 * 处理与Python后端API的通信
 */

class APIClient {
    constructor() {
        this.baseUrl = 'http://localhost:8788';
        this.wsConnection = null;
        this.wsCallbacks = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    async init() {
        // 从Electron获取API URL
        if (window.electronAPI) {
            try {
                this.baseUrl = await window.electronAPI.getApiUrl();
            } catch (e) {
                console.log('Using default API URL');
            }
        }
        console.log('API Client initialized with base URL:', this.baseUrl);
    }

    // ==================== HTTP 请求方法 ====================

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };

        if (config.body && typeof config.body === 'object') {
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.detail || `HTTP ${response.status}: ${response.statusText}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error);
            throw error;
        }
    }

    async get(endpoint) {
        return this.request(endpoint, { method: 'GET' });
    }

    async post(endpoint, data) {
        return this.request(endpoint, { method: 'POST', body: data });
    }

    async put(endpoint, data) {
        return this.request(endpoint, { method: 'PUT', body: data });
    }

    async delete(endpoint) {
        return this.request(endpoint, { method: 'DELETE' });
    }

    // ==================== WebSocket 连接 ====================

    connectWebSocket(clientId) {
        return new Promise((resolve, reject) => {
            const wsUrl = `ws://localhost:8788/ws/${clientId}`;

            this.wsConnection = new WebSocket(wsUrl);

            this.wsConnection.onopen = () => {
                console.log('WebSocket connected');
                this.reconnectAttempts = 0;
                resolve(this.wsConnection);
            };

            this.wsConnection.onclose = (event) => {
                console.log('WebSocket closed:', event.code, event.reason);
                this.handleReconnect(clientId);
            };

            this.wsConnection.onerror = (error) => {
                console.error('WebSocket error:', error);
                reject(error);
            };

            this.wsConnection.onmessage = (event) => {
                try {
                    const message = JSON.parse(event.data);
                    this.handleWebSocketMessage(message);
                } catch (e) {
                    console.error('Failed to parse WebSocket message:', e);
                }
            };
        });
    }

    handleWebSocketMessage(message) {
        const { type } = message;

        // 调用注册的回调
        if (this.wsCallbacks.has(type)) {
            const callbacks = this.wsCallbacks.get(type);
            callbacks.forEach(callback => callback(message));
        }

        // 触发通用事件
        if (this.wsCallbacks.has('*')) {
            const callbacks = this.wsCallbacks.get('*');
            callbacks.forEach(callback => callback(message));
        }

        // Dispatch custom window event for WebSocket messages
        window.dispatchEvent(new CustomEvent('websocket-message', {
            detail: message
        }));
    }

    handleReconnect(clientId) {
        if (this.reconnectAttempts < this.maxReconnectAttempts) {
            this.reconnectAttempts++;
            const delay = Math.min(1000 * Math.pow(2, this.reconnectAttempts), 30000);
            console.log(`Reconnecting in ${delay}ms (attempt ${this.reconnectAttempts})`);

            setTimeout(() => {
                this.connectWebSocket(clientId).catch(console.error);
            }, delay);
        }
    }

    onWebSocketMessage(type, callback) {
        if (!this.wsCallbacks.has(type)) {
            this.wsCallbacks.set(type, []);
        }
        this.wsCallbacks.get(type).push(callback);
    }

    sendWebSocketMessage(message) {
        if (this.wsConnection && this.wsConnection.readyState === WebSocket.OPEN) {
            this.wsConnection.send(JSON.stringify(message));
        } else {
            console.error('WebSocket is not connected');
        }
    }

    // ==================== Agent API ====================

    async getAgents() {
        return this.get('/api/agents');
    }

    async createAgent(agentData) {
        return this.post('/api/agents', agentData);
    }

    async updateAgent(agentId, agentData) {
        return this.put(`/api/agents/${agentId}`, agentData);
    }

    async deleteAgent(agentId) {
        return this.delete(`/api/agents/${agentId}`);
    }

    // ==================== AI Chat API ====================

    async getAiChatConfigs() {
        return this.get('/api/ai-chat/configs');
    }

    async createAiChatConfig(configData) {
        return this.post('/api/ai-chat/configs', configData);
    }

    async sendChatMessage(agentId, message, conversationId = null) {
        return this.post('/api/chat', {
            agent_id: agentId,
            message: message,
            conversation_id: conversationId
        });
    }

    async getChatHistory(agentId, conversationId = null) {
        let endpoint = `/api/chat/history/${agentId}`;
        if (conversationId) {
            endpoint += `?conversation_id=${conversationId}`;
        }
        return this.get(endpoint);
    }

    // ==================== Knowledge Base API ====================

    async getKnowledgeBases() {
        return this.get('/api/knowledge-base');
    }

    async createKnowledgeBase(kbData) {
        return this.post('/api/knowledge-base', kbData);
    }

    async uploadToKnowledgeBase(kbId, file) {
        const formData = new FormData();
        formData.append('file', file);

        const response = await fetch(`${this.baseUrl}/api/knowledge-base/${kbId}/upload`, {
            method: 'POST',
            body: formData
        });

        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }

        return response.json();
    }

    // ==================== System Config API ====================

    async getSystemConfig() {
        return this.get('/api/system/config');
    }

    async updateSystemConfig(configData) {
        return this.put('/api/system/config', configData);
    }

    // ==================== Plugins API ====================

    async getPlugins() {
        return this.get('/api/plugins');
    }

    // ==================== Health Check ====================

    async healthCheck() {
        return this.get('/health');
    }
}

// 创建全局API客户端实例
const api = new APIClient();

// 暴露到window对象供其他模块使用
window.api = api;

// 初始化API客户端
document.addEventListener('DOMContentLoaded', async () => {
    await api.init();
});
