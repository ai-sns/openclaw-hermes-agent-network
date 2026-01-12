/**
 * Agent Module - Index（多Agent版本）
 * AI聊天代理模块入口
 */

import AgentPage from './AgentPage.js';
import AgentSidebar from './AgentSidebar.js';
import agentHandlers from './agentHandlers.js';
import multiAgentHandlers from './multiAgentHandlers.js';
import ModelManagementPage from './ModelManagementPage.js';
import RoleManagementPage from './RoleManagementPage.js';

export default {
    name: 'agent',
    version: '2.0.0', // 升级到2.0.0表示多Agent版本

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
     * 初始化模块（多Agent版本）
     */
    async init() {
        console.log('[AgentModule] 初始化多Agent系统...');

        try {
            // 使用多Agent处理器初始化
            await multiAgentHandlers.init();
            console.log('[AgentModule] 多Agent系统初始化完成');
        } catch (error) {
            console.error('[AgentModule] 初始化失败:', error);
            // 降级到传统模式
            console.warn('[AgentModule] 降级到传统单Agent模式');
            agentHandlers.init();
        }
    },

    /**
     * 销毁模块
     */
    destroy() {
        if (agentHandlers && agentHandlers.destroy) {
            agentHandlers.destroy();
        }
    },

    /**
     * 导出管理页面
     */
    ModelManagementPage,
    RoleManagementPage,

    /**
     * 导出handlers供外部使用
     */
    agentHandlers,
    multiAgentHandlers
};
