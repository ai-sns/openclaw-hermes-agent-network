/**
 * Agent Tools Config Event Handler
 * 处理工具配置按钮的点击事件
 */

// 使用事件委托处理动态创建的工具配置按钮
document.addEventListener('click', function(e) {
    // 检查是否点击了工具配置按钮或其子元素
    const configBtn = e.target.closest('.config-tools-btn');

    if (configBtn) {
        e.preventDefault();
        e.stopPropagation();

        const agentId = configBtn.dataset.agentId;
        console.log('[AgentToolsConfig] Opening tools dialog for agent:', agentId);

        const page = document.getElementById(`page-agent-${agentId}`);
        const agentType = (page && page.dataset && page.dataset.agentType) ? String(page.dataset.agentType).toLowerCase() : '';
        if (agentType === 'remote') {
            const msg = 'This feature is not available for Remote agents.';
            if (typeof Notification !== 'undefined' && Notification.error) {
                Notification.error(msg);
            } else {
                alert(msg);
            }
            return;
        }

        // 打开工具配置对话框
        if (window.AgentToolsDialog) {
            window.AgentToolsDialog.open(agentId);
        } else {
            console.error('[AgentToolsConfig] AgentToolsDialog not loaded');
        }
    }
});

console.log('[AgentToolsConfig] Event handler initialized');
