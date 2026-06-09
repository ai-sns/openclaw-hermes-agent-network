/**
 * AI-SNS API Client
 * Handles communication with the Python backend API
 */

class APIClient {
    constructor() {
        this.baseUrl = '';
        this.wsConnection = null;
        this.wsCallbacks = new Map();
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 5;
    }

    async init() {
        // Get API URL from Electron
        if (window.electronAPI) {
            try {
                this.baseUrl = await window.electronAPI.getApiUrl();
            } catch (e) {
                console.log('Using default API URL');
            }
        }
        this.baseUrl = this.normalizeHttpBaseUrl(this.baseUrl);
        await this.loadAppConfig();
        console.log('API Client initialized with base URL:', this.baseUrl);
    }

    normalizeHttpBaseUrl(raw) {
        const v = String(raw || '').trim();
        if (!v) {
            return '';
        }
        const withScheme = /^https?:\/\//i.test(v) ? v : `http://${v}`;
        return withScheme.endsWith('/') ? withScheme.slice(0, -1) : withScheme;
    }

    toWebSocketUrl(clientId) {
        const base = this.normalizeHttpBaseUrl(this.baseUrl);
        if (!base) {
            return '';
        }
        const u = new URL(base);
        const wsProto = u.protocol === 'https:' ? 'wss:' : 'ws:';
        return `${wsProto}//${u.host}/ws/${clientId}`;
    }

    async loadAppConfig() {
        const cfg = {};
        try {
            if (window.electronAPI && typeof window.electronAPI.readConfigJson === 'function') {
                const local = await window.electronAPI.readConfigJson();
                if (local && local.success && local.data && typeof local.data === 'object') {
                    Object.assign(cfg, local.data);
                }
            }
        } catch (e) {
        }

        try {
            if (this.baseUrl) {
                const remote = await this.get('/api/system/config');
                if (remote && remote.success && remote.data && typeof remote.data === 'object') {
                    Object.assign(cfg, remote.data);
                }
            }
        } catch (e) {
        }

        if (!window.appConfig || typeof window.appConfig !== 'object') {
            window.appConfig = {};
        }

        if (this.baseUrl) {
            window.appConfig.agent_server = this.baseUrl;
        }
        if (cfg.ai_sns_server) {
            window.appConfig.ai_sns_server = cfg.ai_sns_server;
        }
        if (cfg.agent_server) {
            window.appConfig.agent_server = this.normalizeHttpBaseUrl(cfg.agent_server);
            this.baseUrl = window.appConfig.agent_server;
        }
        if (cfg.language) {
            window.appConfig.language = String(cfg.language).toLowerCase();
        }

        const getAgentServer = () => {
            const v = window.appConfig && window.appConfig.agent_server;
            return this.normalizeHttpBaseUrl(v || this.baseUrl);
        };

        const getAiSnsServer = () => {
            const v = window.appConfig && window.appConfig.ai_sns_server;
            return this.normalizeHttpBaseUrl(v || '');
        };

        if (typeof window.resolveAgentServerUrl !== 'function') {
            window.resolveAgentServerUrl = (inputUrl) => {
                const base = getAgentServer();
                const u = String(inputUrl || '').trim();
                if (!u) return u;
                if (!base) return u;

                if (u.startsWith('/')) {
                    return base + u;
                }

                try {
                    const parsed = new URL(u);
                    if ((parsed.hostname === 'localhost' || parsed.hostname === '127.0.0.1') && parsed.port === '8788') {
                        const baseParsed = new URL(base);
                        parsed.protocol = baseParsed.protocol;
                        parsed.host = baseParsed.host;
                        return parsed.toString();
                    }
                } catch (e) {
                }
                return u;
            };
        }

        if (typeof window.resolveAiSnsServerUrl !== 'function') {
            window.resolveAiSnsServerUrl = (inputUrlOrPath) => {
                const base = getAiSnsServer();
                const u = String(inputUrlOrPath || '').trim();
                if (!u) return u;
                if (!base) return u;
                if (/^https?:\/\//i.test(u)) {
                    return u;
                }
                if (u.startsWith('/')) {
                    return base + u;
                }
                return base + '/' + u;
            };
        }

        if (!window.__agentServerFetchWrapped && typeof window.fetch === 'function') {
            window.__agentServerFetchWrapped = true;
            const originalFetch = window.fetch.bind(window);
            window.fetch = (input, init) => {
                try {
                    if (typeof input === 'string' && typeof window.resolveAgentServerUrl === 'function') {
                        return originalFetch(window.resolveAgentServerUrl(input), init);
                    }
                    if (input && typeof input.url === 'string' && typeof window.resolveAgentServerUrl === 'function') {
                        const nextUrl = window.resolveAgentServerUrl(input.url);
                        if (nextUrl !== input.url) {
                            const nextReq = new Request(nextUrl, input);
                            return originalFetch(nextReq, init);
                        }
                    }
                } catch (e) {
                }
                return originalFetch(input, init);
            };
        }
    }

    // ==================== HTTP request methods ====================

    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const defaultOptions = {
            headers: {
                'Content-Type': 'application/json',
            },
        };

        const config = { ...defaultOptions, ...options };

        // Log request details
        console.log(`[API] ${config.method || 'GET'} ${endpoint}`);
        if (config.body && typeof config.body === 'object') {
            console.log('[API] Request body:', config.body);
            config.body = JSON.stringify(config.body);
        }

        try {
            const response = await fetch(url, config);

            if (!response.ok) {
                const errorText = await response.text();
                console.error(`[API] Error response (${response.status}):`, errorText);
                
                let errorDetail;
                try {
                    const errorJson = JSON.parse(errorText);
                    errorDetail = errorJson.detail || errorJson.message || errorText;
                } catch {
                    errorDetail = errorText;
                }
                
                throw new Error(`HTTP ${response.status}: ${errorDetail}`);
            }

            return await response.json();
        } catch (error) {
            console.error(`API Error [${endpoint}]:`, error.message || error);
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

    // ==================== WebSocket connection ====================

    connectWebSocket(clientId) {
        return new Promise((resolve, reject) => {
            const wsUrl = this.toWebSocketUrl(clientId);
            if (!wsUrl) {
                reject(new Error('WebSocket base URL not configured'));
                return;
            }

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

        // Invoke registered callbacks
        if (this.wsCallbacks.has(type)) {
            const callbacks = this.wsCallbacks.get(type);
            callbacks.forEach(callback => callback(message));
        }

        // Trigger generic event
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

    // ==================== Health Check ====================

    async healthCheck() {
        return this.get('/health');
    }
}

// Create global API client instance
const api = new APIClient();

// Expose to window for other modules
window.api = api;

// Note: API client initialization is driven by the startup bootstrap
// (renderer/js/core/bootstrap.js), which calls `api.init()` AFTER the
// backend health endpoint is reachable. Auto-initializing here on
// DOMContentLoaded would race with bootstrap and may attempt
// /api/system/config before the backend is ready.
