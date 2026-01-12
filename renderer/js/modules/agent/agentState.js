/**
 * Agent State - 多Agent状态管理
 * 管理多个Agent的聊天历史、流式状态等
 */

const agentState = {
    // 当前活动的agent ID
    currentAgentId: null,

    // 所有agents的列表
    agents: [],

    // 每个agent的独立状态 { agent_id: { chatHistory, conversationId, modelConfig, roleConfig, ... } }
    agentStates: {},

    // 当前请求ID（用于流式响应）
    currentRequestId: null,

    // 当前流式内容
    currentStreamingContent: '',

    // 模型列表
    models: [],

    // 角色列表
    roles: [],

    /**
     * 设置当前活动的agent
     */
    setCurrentAgent(agentId) {
        this.currentAgentId = agentId;
        // 如果该agent没有状态，初始化它
        if (!this.agentStates[agentId]) {
            this.agentStates[agentId] = {
                chatHistory: [],
                conversationId: null,
                currentModelConfig: null,
                currentRoleConfig: null,
                streamingContent: '',
                requestId: null
            };
        }
    },

    /**
     * 获取当前agent
     */
    getCurrentAgent() {
        if (!this.currentAgentId) return null;
        return this.agents.find(a => a.id === this.currentAgentId);
    },

    /**
     * 获取当前agent的状态
     */
    getCurrentAgentState() {
        if (!this.currentAgentId || !this.agentStates[this.currentAgentId]) {
            return null;
        }
        return this.agentStates[this.currentAgentId];
    },

    /**
     * 设置agents列表
     */
    setAgents(agents) {
        this.agents = agents;
        // 如果还没有当前agent，设置第一个为当前agent
        if (!this.currentAgentId && agents.length > 0) {
            this.setCurrentAgent(agents[0].id);
        }
    },

    /**
     * 获取agents列表
     */
    getAgents() {
        return this.agents;
    },

    /**
     * 添加消息到当前agent的聊天历史
     */
    addMessage(role, content) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.chatHistory.push({ role, content });
        }
    },

    /**
     * 获取当前agent的聊天历史
     */
    getChatHistory() {
        const state = this.getCurrentAgentState();
        return state ? [...state.chatHistory] : [];
    },

    /**
     * 清空当前agent的聊天历史
     */
    clearChatHistory() {
        const state = this.getCurrentAgentState();
        if (state) {
            state.chatHistory = [];
        }
    },

    /**
     * 设置当前agent的conversation ID
     */
    setConversationId(id) {
        const state = this.getCurrentAgentState();
        if (state) {
            state.conversationId = id;
        }
    },

    /**
     * 获取当前agent的conversation ID
     */
    getConversationId() {
        const state = this.getCurrentAgentState();
        return state ? state.conversationId : null;
    },

    /**
     * 生成新的conversation ID
     */
    generateConversationId() {
        return 'conv_' + Date.now() + '_' + Math.random().toString(36).substr(2, 9);
    },

    /**
     * 设置当前agent的模型配置
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
     * 获取当前agent的模型配置
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
     * 设置当前agent的角色配置
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
     * 获取当前agent的角色配置
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
     * 获取当前agent的system prompt
     */
    getSystemPrompt() {
        const roleConfig = this.currentRoleConfig;
        if (roleConfig && roleConfig.system_prompt) {
            return roleConfig.system_prompt;
        }
        // 回退到默认提示词
        return '你是一个有帮助的AI助手。';
    },

    /**
     * 设置请求ID（用于流式响应）
     */
    setRequestId(id) {
        this.currentRequestId = id;
        const state = this.getCurrentAgentState();
        if (state) {
            state.requestId = id;
        }
    },

    /**
     * 获取请求ID
     */
    getRequestId() {
        return this.currentRequestId;
    },

    /**
     * 清除请求ID
     */
    clearRequestId() {
        this.currentRequestId = null;
        const state = this.getCurrentAgentState();
        if (state) {
            state.requestId = null;
        }
    },

    /**
     * 添加流式内容
     */
    appendStreamingContent(content) {
        this.currentStreamingContent += content;
        const state = this.getCurrentAgentState();
        if (state) {
            state.streamingContent += content;
        }
    },

    /**
     * 获取流式内容
     */
    getStreamingContent() {
        return this.currentStreamingContent;
    },

    /**
     * 清空流式内容
     */
    clearStreamingContent() {
        this.currentStreamingContent = '';
        const state = this.getCurrentAgentState();
        if (state) {
            state.streamingContent = '';
        }
    },

    /**
     * 设置模型列表
     */
    setModels(models) {
        this.models = models;
    },

    /**
     * 获取模型列表
     */
    getModels() {
        return this.models;
    },

    /**
     * 设置角色列表
     */
    setRoles(roles) {
        this.roles = roles;
    },

    /**
     * 获取角色列表
     */
    getRoles() {
        return this.roles;
    },

    /**
     * 重置所有状态
     */
    reset() {
        this.currentAgentId = null;
        this.agents = [];
        this.agentStates = {};
        this.currentRequestId = null;
        this.currentStreamingContent = '';
    }
};

export default agentState;
