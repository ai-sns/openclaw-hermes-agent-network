/**
 * Agent State - 状态管理
 * 管理聊天历史、流式状态等
 */

const agentState = {
    // 聊天历史记录
    chatHistory: [],

    // 当前请求ID
    currentRequestId: null,

    // 当前流式内容
    streamingContent: '',

    // 当前选择的模型
    selectedModel: 'gpt-4o',

    // 当前选择的角色
    selectedRole: 'senior-dev',

    // Agent列表
    agents: [],

    // 聊天列表
    chats: [],

    // 模型列表
    models: [],

    // 角色列表
    roles: [],

    /**
     * 重置状态
     */
    reset() {
        this.chatHistory = [];
        this.currentRequestId = null;
        this.streamingContent = '';
    },

    /**
     * 添加消息到历史
     */
    addMessage(role, content) {
        this.chatHistory.push({ role, content });
    },

    /**
     * 获取聊天历史
     */
    getChatHistory() {
        return [...this.chatHistory];
    },

    /**
     * 设置当前请求ID
     */
    setRequestId(id) {
        this.currentRequestId = id;
    },

    /**
     * 获取当前请求ID
     */
    getRequestId() {
        return this.currentRequestId;
    },

    /**
     * 清除当前请求ID
     */
    clearRequestId() {
        this.currentRequestId = null;
    },

    /**
     * 设置流式内容
     */
    setStreamingContent(content) {
        this.streamingContent = content;
    },

    /**
     * 追加流式内容
     */
    appendStreamingContent(content) {
        this.streamingContent += content;
    },

    /**
     * 获取流式内容
     */
    getStreamingContent() {
        return this.streamingContent;
    },

    /**
     * 清除流式内容
     */
    clearStreamingContent() {
        this.streamingContent = '';
    },

    /**
     * 设置选择的模型
     */
    setModel(model) {
        this.selectedModel = model;
    },

    /**
     * 获取选择的模型
     */
    getModel() {
        return this.selectedModel;
    },

    /**
     * 设置选择的角色
     */
    setRole(role) {
        this.selectedRole = role;
    },

    /**
     * 获取选择的角色
     */
    getRole() {
        return this.selectedRole;
    },

    /**
     * 获取系统提示词
     */
    getSystemPrompt() {
        const prompts = {
            'senior-dev': '你是一位资深的软件工程师，有超过15年的开发经验。你精通多种编程语言和框架，善于编写高质量、可维护的代码。请用专业但易懂的方式回答问题，必要时提供代码示例。',
            'assistant': '你是一个通用的AI助手，能够帮助用户解答各种问题。请用友好、清晰的方式回答。',
            'writer': '你是一位专业的创意写作者，擅长各种文体的写作，包括故事、文章、诗歌等。请发挥创意，提供高质量的写作内容。',
            'analyst': '你是一位专业的数据分析师，擅长数据分析、统计和可视化。请用专业的角度分析问题，必要时提供数据支持。'
        };
        return prompts[this.selectedRole] || prompts['assistant'];
    },

    /**
     * 设置Agent列表
     */
    setAgents(agents) {
        this.agents = agents;
    },

    /**
     * 获取Agent列表
     */
    getAgents() {
        return this.agents;
    },

    /**
     * 设置聊天列表
     */
    setChats(chats) {
        this.chats = chats;
    },

    /**
     * 获取聊天列表
     */
    getChats() {
        return this.chats;
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
    }
};

export default agentState;
