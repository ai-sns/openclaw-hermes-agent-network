/**
 * Web Module - Index
 * Web服务模块入口
 */

import WebPage from './WebPage.js';
import WebSidebar from './WebSidebar.js';
import webHandlers from './webHandlers.js';

export default {
    name: 'web',
    version: '1.0.0',

    /**
     * 渲染主内容区
     */
    renderPage() {
        return WebPage.render();
    },

    /**
     * 渲染侧边栏
     */
    renderSidebar() {
        return WebSidebar.render();
    },

    /**
     * 初始化模块
     */
    async init() {
        console.log('[Web Module] Initializing...');
        await WebSidebar.init();

        // Re-render sidebar after data is loaded
        const sidebarContainer = document.getElementById('sidebar-web');
        console.log('[Web Module] Sidebar container:', sidebarContainer);
        if (sidebarContainer) {
            console.log('[Web Module] Re-rendering sidebar with data...');
            sidebarContainer.innerHTML = WebSidebar.render();
        } else {
            console.warn('[Web Module] Sidebar container not found!');
        }

        webHandlers.init(WebPage, WebSidebar);

        // Listen for page changes to close BrowserView when leaving web page
        if (window.eventBus) {
            window.eventBus.on('page:changed', (data) => {
                if (data.from === 'web' && data.to !== 'web') {
                    console.log('[Web Module] Leaving web page, closing BrowserView');
                    WebPage.closeBrowserView();
                }
            });
        }

        console.log('[Web Module] Initialization complete');
    },

    /**
     * 销毁模块
     */
    destroy() {
        console.log('[Web Module] Destroying...');
        WebPage.closeBrowserView();
        webHandlers.destroy();
        
        // Clean up sidebar state
        const sidebarContainer = document.getElementById('secondarySidebar');
        if (sidebarContainer) {
            sidebarContainer.innerHTML = '';
        }
    }
};
