/**
 * Tools Sidebar - 侧边栏渲染
 */

const ToolsSidebar = {
    render() {
        return `
            <aside class="tools-sidebar-ref">
                <h2 class="tools-sidebar-ref__title">Tool Management</h2>
                <button class="tools-category-item active" data-category="tools-plugin" type="button">
                    <span class="material-icons-round tools-sidebar-ref__icon">extension</span>
                    <span class="tools-sidebar-ref__label">Tools Plugin</span>
                    <span class="category-arrow ml-auto material-icons-round">chevron_right</span>
                </button>
                <button class="tools-category-item" data-category="mcp" type="button">
                    <span class="material-icons-round tools-sidebar-ref__icon">api</span>
                    <span class="tools-sidebar-ref__label">MCP</span>
                    <span class="category-arrow ml-auto material-icons-round">chevron_right</span>
                </button>
                <button class="tools-category-item" data-category="function" type="button">
                    <span class="material-icons-round tools-sidebar-ref__icon">functions</span>
                    <span class="tools-sidebar-ref__label">Function</span>
                    <span class="category-arrow ml-auto material-icons-round">chevron_right</span>
                </button>
                <button class="tools-category-item" data-category="computer-use" type="button">
                    <span class="material-icons-round tools-sidebar-ref__icon">desktop_windows</span>
                    <span class="tools-sidebar-ref__label">Computer Use</span>
                    <span class="category-arrow ml-auto material-icons-round">chevron_right</span>
                </button>
                <button class="tools-category-item" data-category="doc-skill" type="button">
                    <span class="material-icons-round tools-sidebar-ref__icon">school</span>
                    <span class="tools-sidebar-ref__label">Doc Skills</span>
                    <span class="category-arrow ml-auto material-icons-round">chevron_right</span>
                </button>
            </aside>
        `;
    }
};

export default ToolsSidebar;
