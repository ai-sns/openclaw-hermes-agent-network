/**
 * Agent Knowledge Base Config Event Handler
 * Handles click events for the knowledge base configuration button
 */

document.addEventListener('click', function(e) {
    const kbBtn = e.target.closest('.toolbar-icon-btn[data-action="kb-config"][data-agent-id]')
        || e.target.closest('.toolbar-icon-btn[title="Configure Knowledge Base"][data-agent-id]')
        || e.target.closest('.toolbar-icon-btn[title="Knowledge Base"][data-agent-id]')
        || e.target.closest('.toolbar-icon-btn[title="配置知识库"][data-agent-id]');

    if (kbBtn) {
        e.preventDefault();
        e.stopPropagation();

        const agentId = kbBtn.dataset.agentId;
        console.log('[AgentKnowledgeBaseConfig] Opening KB dialog for agent:', agentId);

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

        if (window.AgentKnowledgeBaseDialog) {
            window.AgentKnowledgeBaseDialog.open(agentId);
        } else {
            console.error('[AgentKnowledgeBaseConfig] AgentKnowledgeBaseDialog not loaded');
        }
    }
});

console.log('[AgentKnowledgeBaseConfig] Event handler initialized');
