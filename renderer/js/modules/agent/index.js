/**
 * Agent Module - Index
 * AI聊天代理模块入口
 */

import AgentPage from './AgentPage.js';
import AgentSidebar from './AgentSidebar.js';
import agentHandlers from './agentHandlers.js';
import ModelManagementPage from './ModelManagementPage.js';
import RoleManagementPage from './RoleManagementPage.js';

export default {
    name: 'agent',
    version: '1.0.0',

    /**
     * 渲染主内容区
     */
    renderPage() {
        return AgentPage.render();
    },

    /**
     * 渲染侧边栏
     */
    renderSidebar() {
        return AgentSidebar.render();
    },

    /**
     * 初始化模块
     */
    init() {
        agentHandlers.init();
    },

    /**
     * 销毁模块
     */
    destroy() {
        agentHandlers.destroy();
    },

    /**
     * 导出管理页面
     */
    ModelManagementPage,
    RoleManagementPage
};
