/**
 * SNS Module - Index
 * SNS模块入口
 */

import SNSPage from './SNSPage.js';
import SNSSidebar from './SNSSidebar.js';
import snsHandlers from './snsHandlers.js';

export default {
    name: 'sns',
    version: '1.0.0',

    /**
     * 渲染主内容区
     */
    renderPage() {
        return SNSPage.render();
    },

    /**
     * 渲染侧边栏
     */
    renderSidebar() {
        return SNSSidebar.render();
    },

    /**
     * 初始化模块
     */
    async init() {
        snsHandlers.init();
        // Initialize sidebar charts and contacts
        await SNSSidebar.init();
    },

    /**
     * 销毁模块
     */
    destroy() {
        snsHandlers.destroy();
    }
};
