/**
 * SNS Avatar Configuration Dialog
 */

export class SNSAvatarDialog {
    constructor() {
        this.dialog = null;
        this.selectedAvatar3D = null;
        this.uploadedAvatar = null;
    }

    async show() {
        // Create dialog HTML
        const dialogHTML = `
            <div class="modal-overlay" id="snsAvatarDialog">
                <div class="modal-dialog" style="max-width: 800px;">
                    <div class="modal-header">
                        <h3>用户配置</h3>
                        <button class="modal-close" onclick="document.getElementById('snsAvatarDialog').remove()">&times;</button>
                    </div>
                    <div class="modal-tabs">
                        <button class="modal-tab active" data-tab="avatar">头像配置</button>
                        <button class="modal-tab" data-tab="userinfo">用户信息</button>
                    </div>
                    <div class="modal-body">
                        <!-- Avatar Config Tab -->
                        <div class="tab-content active" id="avatarTab">
                            <div class="avatar-config-container">
                                <!-- Upload Avatar Section -->
                                <div class="avatar-section">
                                    <h4>上传头像</h4>
                                    <div class="avatar-upload-area">
                                        <input type="file" id="avatarFileInput" accept="image/*" style="display: none;">
                                        <div class="avatar-preview" id="avatarPreview">
                                            <img id="avatarPreviewImg" src="" alt="头像预览" style="display: none; max-width: 150px; max-height: 150px;">
                                            <div id="avatarPlaceholder" class="avatar-placeholder">
                                                <span>点击上传头像</span>
                                            </div>
                                        </div>
                                        <button class="btn btn-primary" id="uploadAvatarBtn">选择图片</button>
                                    </div>
                                </div>

                                <!-- 3D Avatar Selection Section -->
                                <div class="avatar-section">
                                    <h4>选择3D头像</h4>
                                    <div class="avatar3d-grid" id="avatar3dGrid">
                                        <div class="loading">加载中...</div>
                                    </div>
                                </div>
                            </div>
                        </div>

                        <!-- User Info Tab -->
                        <div class="tab-content" id="userinfoTab" style="display: none;">
                            <div class="user-info-form">
                                <div class="form-group">
                                    <label for="userNickname">昵称</label>
                                    <input type="text" id="userNickname" class="form-control" placeholder="请输入昵称">
                                </div>
                                <div class="form-group">
                                    <label for="userSign">签名</label>
                                    <input type="text" id="userSign" class="form-control" placeholder="请输入签名">
                                </div>
                                <div class="form-group">
                                    <label for="userSnsUrl">SNS URL</label>
                                    <input type="text" id="userSnsUrl" class="form-control" placeholder="请输入SNS URL">
                                </div>
                                <div class="form-group">
                                    <label for="userAgentId">Agent</label>
                                    <select id="userAgentId" class="form-control">
                                        <option value="">请选择Agent</option>
                                    </select>
                                </div>
                            </div>
                        </div>
                    </div>
                    <div class="modal-footer">
                        <button class="btn btn-secondary" onclick="document.getElementById('snsAvatarDialog').remove()">取消</button>
                        <button class="btn btn-primary" id="saveAvatarBtn">保存</button>
                    </div>
                </div>
            </div>
        `;

        // Add to DOM
        document.body.insertAdjacentHTML('beforeend', dialogHTML);
        this.dialog = document.getElementById('snsAvatarDialog');

        // Load 3D avatars
        await this.load3DAvatars();

        // Load user info
        await this.loadUserInfo();

        // Load agent list
        await this.loadAgentList();

        // Setup event listeners
        this.setupEventListeners();
    }

    async load3DAvatars() {
        try {
            const response = await fetch('http://localhost:8788/api/sns/avatars3d');
            const avatars = await response.json();

            const grid = document.getElementById('avatar3dGrid');
            grid.innerHTML = '';

            avatars.forEach(avatar => {
                const item = document.createElement('div');
                item.className = 'avatar3d-item';
                item.dataset.name = avatar.name;
                item.dataset.modelUrl = avatar.model_url;
                item.innerHTML = `
                    <img src="http://localhost:8788${avatar.preview_url}" alt="${avatar.name}">
                    <div class="avatar3d-name">${avatar.name}</div>
                `;
                item.addEventListener('click', () => this.select3DAvatar(item, avatar));
                grid.appendChild(item);
            });
        } catch (error) {
            console.error('Error loading 3D avatars:', error);
            document.getElementById('avatar3dGrid').innerHTML = '<div class="error">加载失败</div>';
        }
    }

    select3DAvatar(element, avatar) {
        // Remove previous selection
        document.querySelectorAll('.avatar3d-item').forEach(item => {
            item.classList.remove('selected');
        });

        // Select current
        element.classList.add('selected');
        this.selectedAvatar3D = avatar;
    }

    setupEventListeners() {
        // Tab switching
        document.querySelectorAll('.modal-tab').forEach(tab => {
            tab.addEventListener('click', (e) => {
                const targetTab = e.target.dataset.tab;

                // Update tab buttons
                document.querySelectorAll('.modal-tab').forEach(t => t.classList.remove('active'));
                e.target.classList.add('active');

                // Update tab content
                document.querySelectorAll('.tab-content').forEach(content => {
                    content.style.display = 'none';
                    content.classList.remove('active');
                });

                const targetContent = document.getElementById(targetTab + 'Tab');
                if (targetContent) {
                    targetContent.style.display = 'block';
                    targetContent.classList.add('active');
                }
            });
        });

        // Upload button
        document.getElementById('uploadAvatarBtn').addEventListener('click', () => {
            document.getElementById('avatarFileInput').click();
        });

        // File input change
        document.getElementById('avatarFileInput').addEventListener('change', (e) => {
            const file = e.target.files[0];
            if (file) {
                this.previewAvatar(file);
            }
        });

        // Save button
        document.getElementById('saveAvatarBtn').addEventListener('click', () => {
            this.saveConfiguration();
        });
    }

    previewAvatar(file) {
        const reader = new FileReader();
        reader.onload = (e) => {
            const img = document.getElementById('avatarPreviewImg');
            const placeholder = document.getElementById('avatarPlaceholder');
            img.src = e.target.result;
            img.style.display = 'block';
            placeholder.style.display = 'none';
            this.uploadedAvatar = file;
        };
        reader.readAsDataURL(file);
    }

    async saveConfiguration() {
        try {
            const activeTab = document.querySelector('.modal-tab.active').dataset.tab;

            if (activeTab === 'avatar') {
                // Save avatar configuration
                const updates = {};

                // Upload avatar if selected
                if (this.uploadedAvatar) {
                    const formData = new FormData();
                    formData.append('file', this.uploadedAvatar);

                    const uploadResponse = await fetch('http://localhost:8788/api/sns/config/upload-avatar', {
                        method: 'POST',
                        body: formData
                    });

                    const uploadResult = await uploadResponse.json();
                    if (uploadResult.success) {
                        updates.avatar = uploadResult.avatar_data;
                    }
                }

                // Set 3D avatar if selected
                if (this.selectedAvatar3D) {
                    updates.avatar3d = this.selectedAvatar3D.name;
                }

                // Update configuration
                if (Object.keys(updates).length > 0) {
                    const response = await fetch('http://localhost:8788/api/sns/config', {
                        method: 'PUT',
                        headers: {
                            'Content-Type': 'application/json'
                        },
                        body: JSON.stringify(updates)
                    });

                    const result = await response.json();
                    if (result.success) {
                        alert('配置保存成功！');
                        this.dialog.remove();
                    } else {
                        alert('保存失败：' + result.message);
                    }
                } else {
                    alert('请选择头像或3D头像');
                }
            } else if (activeTab === 'userinfo') {
                // Save user info
                const nickname = document.getElementById('userNickname').value;
                const sign = document.getElementById('userSign').value;
                const snsUrl = document.getElementById('userSnsUrl').value;
                const agentId = document.getElementById('userAgentId').value;

                const response = await fetch('http://localhost:8788/api/sns/user-info', {
                    method: 'PUT',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        nickname,
                        sign,
                        sns_url: snsUrl,
                        agent_id: agentId || null
                    })
                });

                const result = await response.json();
                if (result.success) {
                    alert('用户信息保存成功！');
                    this.dialog.remove();
                } else {
                    alert('保存失败：' + result.message);
                }
            }
        } catch (error) {
            console.error('Error saving configuration:', error);
            alert('保存失败：' + error.message);
        }
    }

    async loadUserInfo() {
        try {
            const response = await fetch('http://localhost:8788/api/sns/user-info');
            const result = await response.json();

            if (result.success && result.data) {
                document.getElementById('userNickname').value = result.data.nickname || '';
                document.getElementById('userSign').value = result.data.sign || '';
                document.getElementById('userSnsUrl').value = result.data.sns_url || '';
                document.getElementById('userAgentId').value = result.data.agent_id || '';
            }
        } catch (error) {
            console.error('Error loading user info:', error);
        }
    }

    async loadAgentList() {
        try {
            const response = await fetch('http://localhost:8788/api/agent/list');
            const result = await response.json();

            if (result.success && result.data) {
                const select = document.getElementById('userAgentId');
                result.data.forEach(agent => {
                    const option = document.createElement('option');
                    option.value = agent.id;
                    option.textContent = agent.name;
                    select.appendChild(option);
                });
            }
        } catch (error) {
            console.error('Error loading agent list:', error);
        }
    }
}
