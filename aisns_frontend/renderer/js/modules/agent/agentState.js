/**
 * Agent State - multi-agent state management
 * Manages chat history, streaming state, etc. for multiple agents
 */

const agentState = {
    // Current active agent ID
    currentAgentId: null,

    // List of all agents
    agents: [],

    // Per-agent state { agent_id: { chatHistory, conversationId, modelConfig, roleConfig, ... } }
    agentStates: {},

    // Global fields kept for backward compatibility. Do not use these for multi-agent logic.
    currentRequestId: null,
    currentStreamingContent: '',

    // Model list
    models: [],

    // Role list
    roles: [],

    /**
     * Set current active agent
     */
    setCurrentAgent(agentId) {
        this.currentAgentId = agentId;
        // Initialize state if this agent does not have one yet
        if (!this.agentStates[agentId]) {
            this.agentStates[agentId] = {
                chatHistory: [],
                conversationId: null,
                currentModelConfig: null,
                currentRoleConfig: null,
                streamingContent: '',
                requestId: null,
                cancelledRequestId: null,
                attachments: []
            };
        }
    },

    ensureAgentState(agentId) {
        if (!this.agentStates[agentId]) {
            this.agentStates[agentId] = {
                chatHistory: [],
                conversationId: null,
                currentModelConfig: null,
                currentRoleConfig: null,
                streamingContent: '',
                requestId: null,
                cancelledRequestId: null,
                attachments: []
            };
        }
        return this.agentStates[agentId];
    },

    getAgentState(agentId) {
        return this.agentStates[agentId] || null;
    },

    /**
     * Get current agent
     */
    getCurrentAgent() {
        if (!this.currentAgentId) return null;
        return this.agents.find(a => a.id === this.currentAgentId);
    },

    /**
     * Get current agent state
     */
    getCurrentAgentState() {
        if (!this.currentAgentId || !this.agentStates[this.currentAgentId]) {
            return null;
        }
        return this.agentStates[this.currentAgentId];
    },

    /**
     * Set agents list
     */
    setAgents(agents) {
        this.agents = agents;
        // If there is no current agent yet, set the first one
        if (!this.currentAgentId && agents.length > 0) {
            this.setCurrentAgent(agents[0].id);
        }
    },

    /**
     * Get agents list
     */
    getAgents() {
        return this.agents;
    },

    /**
     * Add a message to the current agent chat history
     */
    addMessage(role, content) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.chatHistory.push({ role, content });
        }
    },

    addMessageForAgent(agentId, role, content) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.chatHistory.push({ role, content });
        }
    },

    /**
     * Get current agent chat history
     */
    getChatHistory() {
        const state = this.getCurrentAgentState();
        return state ? [...state.chatHistory] : [];
    },

    /**
     * Clear current agent chat history
     */
    clearChatHistory() {
        const state = this.getCurrentAgentState();
        if (state) {
            state.chatHistory = [];
        }
    },

    /**
     * Set current agent conversation ID
     */
    setConversationId(id) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.conversationId = id;
        }
    },

    /**
     * Get current agent conversation ID
     */
    getConversationId() {
        const state = this.getCurrentAgentState();
        return state ? state.conversationId : null;
    },

    /**
     * Generate a new conversation ID
     */
    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * Set current agent model config
     */
    setModel(configId) {
        const state = this.getCurrentAgentState();
        if (state) {
            if (!state.currentModelConfig) {
                state.currentModelConfig = {};
            }
            state.currentModelConfig.config_id = configId;
        }
    },

    /**
     * Get current agent model config
     */
    get currentModelConfig() {
        const state = this.getCurrentAgentState();
        return state ? state.currentModelConfig : null;
    },

    set currentModelConfig(config) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.currentModelConfig = config;
        }
    },

    /**
     * Set current agent role config
     */
    setRole(roleId) {
        const state = this.getCurrentAgentState();
        if (state) {
            if (!state.currentRoleConfig) {
                state.currentRoleConfig = {};
            }
            state.currentRoleConfig.role_id = roleId;
        }
    },

    /**
     * Get current agent role config
     */
    get currentRoleConfig() {
        const state = this.getCurrentAgentState();
        return state ? state.currentRoleConfig : null;
    },

    set currentRoleConfig(config) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.currentRoleConfig = config;
        }
    },

    /**
     * Get current agent system prompt
     */
    getSystemPrompt() {
        const roleConfig = this.currentRoleConfig;
        if (roleConfig && roleConfig.system_prompt) {
            return roleConfig.system_prompt;
        }
        // Fallback to default prompt
        return 'You are a helpful AI assistant.';
    },

    /**
     * Set request ID (for streaming responses)
     */
    setRequestId(id) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.requestId = id;
        }
        this.currentRequestId = id;
    },

    setRequestIdForAgent(agentId, id) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.requestId = id;
        }
        if (String(agentId) === String(this.currentAgentId || '')) {
            this.currentRequestId = id;
        }
    },

    /**
     * Set cancelled flag for an agent
     */
    setCancelledForAgent(agentId, cancelled) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.cancelled = cancelled;
        }
    },

    /**
     * Check if an agent's request is cancelled
     */
    isCancelledForAgent(agentId) {
        const state = this.ensureAgentState(agentId);
        return state ? !!state.cancelled : false;
    },

    setCancelledRequestIdForAgent(agentId, requestId) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.cancelledRequestId = requestId ? String(requestId) : null;
        }
    },

    getCancelledRequestIdForAgent(agentId) {
        const state = this.ensureAgentState(agentId);
        return state ? (state.cancelledRequestId || null) : null;
    },

    clearCancelledRequestIdForAgent(agentId) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.cancelledRequestId = null;
        }
    },

    isCancelledRequestForAgent(agentId, requestId) {
        if (!requestId) return false;
        const state = this.ensureAgentState(agentId);
        return state ? (String(state.cancelledRequestId || '') === String(requestId)) : false;
    },

    /**
     * Get request ID
     */
    getRequestId() {
        const state = this.getCurrentAgentState();
        if (state && state.requestId) return state.requestId;
        return this.currentRequestId;
    },

    getRequestIdForAgent(agentId) {
        const state = this.ensureAgentState(agentId);
        return state ? (state.requestId || null) : null;
    },

    /**
     * Clear request ID
     */
    clearRequestId() {
        const state = this.getCurrentAgentState();
        if (state) {
            state.requestId = null;
        }
        this.currentRequestId = null;
    },

    clearRequestIdForAgent(agentId) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.requestId = null;
        }
        if (String(agentId) === String(this.currentAgentId || '')) {
            this.currentRequestId = null;
        }
    },

    /**
     * Append streaming content
     */
    appendStreamingContent(content) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.streamingContent += content;
        }
        this.currentStreamingContent = state ? state.streamingContent : (this.currentStreamingContent + content);
    },

    appendStreamingContentForAgent(agentId, content) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.streamingContent += content;
        }
        if (String(agentId) === String(this.currentAgentId || '')) {
            this.currentStreamingContent = state ? state.streamingContent : this.currentStreamingContent;
        }
    },

    /**
     * Get streaming content
     */
    getStreamingContent() {
        const state = this.getCurrentAgentState();
        if (state) return state.streamingContent || '';
        return this.currentStreamingContent;
    },

    getStreamingContentForAgent(agentId) {
        const state = this.ensureAgentState(agentId);
        return state ? (state.streamingContent || '') : '';
    },

    /**
     * Clear streaming content
     */
    clearStreamingContent() {
        const state = this.getCurrentAgentState();
        if (state) {
            state.streamingContent = '';
        }
        this.currentStreamingContent = state ? state.streamingContent : '';
    },

    clearStreamingContentForAgent(agentId) {
        const state = this.ensureAgentState(agentId);
        if (state) {
            state.streamingContent = '';
        }
        if (String(agentId) === String(this.currentAgentId || '')) {
            this.currentStreamingContent = state ? state.streamingContent : '';
        }
    },

    /**
     * Set model list
     */
    setModels(models) {
        this.models = models;
    },

    /**
     * Get model list
     */
    getModels() {
        return this.models;
    },

    /**
     * Set role list
     */
    setRoles(roles) {
        this.roles = roles;
    },

    /**
     * Get role list
     */
    getRoles() {
        return this.roles;
    },

    /**
     * Reset all state
     */
    reset() {
        this.currentAgentId = null;
        this.agents = [];
        this.agentStates = {};
        this.currentRequestId = null;
        this.currentStreamingContent = '';
    }
};

// Export to global (for other modules)
if (typeof window !== 'undefined') {
    window.agentState = agentState;
}

export default agentState;
