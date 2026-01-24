/**
 * SNS Social Role Configuration Dialog
 */

export class SNSSocialRoleDialog {
    constructor() {
        this.dialog = null;
        this.selectedRole = null;
    }

    async show() {
        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsSocialRoleDialog">
                <div class="modal-dialog" style="max-width: 700px;">
                    <div class="modal-header">
                        <h3>社交角色配置</h3>
                        <button class="modal-close" onclick="document.getElementById('snsSocialRoleDialog').remove()">&times;</button>
                    </div>
                    <div class="modal-body">
                        <div class="social-role-container">
                            <div class="role-list" id="socialRoleList">
                                <div class="loading">加载中...</div>
                            </div>
                            <div class="role-preview" id="rolePreview">
                                <h4>角色详情</h4>
                                <div class="role-preview-content">
                                    <p class="placeholder">请选择一个社交角色查看详情</p>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="document.getElementById('snsSocialRoleDialog').remove()">取消</button>
                        <button class="btn btn-primary" id="saveSocialRoleBtn">确定</button>
                    </div>
                </div>
            </div>
        `;

        // Add to DOM
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsSocialRoleDialog');

        // Load social roles
        await this.loadSocialRoles();

        // Setup event listeners
        this.setupEventListeners();
    }

    async loadSocialRoles() {
        try {
            const response = await fetch('http://localhost:8788/api/sns/social-roles');
            const roles = await response.json();

            const roleList = document.getElementById('socialRoleList');
            roleList.innerHTML = '';

            if (roles.length === 0) {
                roleList.innerHTML = '<div class="empty-state">暂无社交角色</div>';
                return;
            }

            roles.forEach(role => {
                const item = document.createElement('div');
                item.className = 'role-item';
                item.dataset.roleId = role.id;
                item.innerHTML = `
                    <div class="role-item-header">
                        <h5>${role.title}</h5>
                        ${role.tags ? `<span class="role-tags">${role.tags}</span>` : ''}
                    </div>
                    <div class="role-item-preview">${this.truncateText(role.content, 100)}</div>
                `;
                item.addEventListener('click', () => this.selectRole(item, role));
                roleList.appendChild(item);
            });
        } catch (error) {
            console.error('Error loading social roles:', error);
            document.getElementById('socialRoleList').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    selectRole(element, role) {
        // Remove previous selection
        document.querySelectorAll('.role-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Select current
        element.classList.add('selected');
        this.selectedRole = role;

        // Show preview
        this.showRolePreview(role);
    }

    showRolePreview(role) {
        const preview = document.querySelector('#rolePreview .role-preview-content');
        preview.innerHTML = `
            <div class="role-detail">
                <h5>${role.title}</h5>
                ${role.tags ? `<div class="role-tags-detail"><strong>标签:</strong> ${role.tags}</div>` : ''}
                ${role.question ? `<div class="role-question"><strong>问题:</strong> ${role.question}</div>` : ''}
                <div class="role-content">
                    <strong>内容:</strong>
                    <p>${role.content}</p>
                </div>
            </div>
        `;
    }

    truncateText(text, maxLength) {
        if (!text) return '';
        if (text.length <= maxLength) return text;
        return text.substring(0, maxLength) + '...';
    }

    setupEventListeners() {
        // Save button
        document.getElementById('saveSocialRoleBtn').addEventListener('click', () => {
            this.saveConfiguration();
        });
    }

    async saveConfiguration() {
        if (!this.selectedRole) {
            alert('请选择一个社交角色');
            return;
        }

        try {
            // Here you might want to save the selected role to a specific field
            // For now, we'll just show a success message
            alert(`已选择社交角色: ${this.selectedRole.title}`);
            this.dialog.remove();

            // You can emit an event or call a callback here
            window.dispatchEvent(new CustomEvent('social-role-selected', {
                detail: this.selectedRole
            }));
        } catch (error) {
            console.error('Error saving social role:', error);
            alert('保存失败：' + error.message);
        }
    }
}
