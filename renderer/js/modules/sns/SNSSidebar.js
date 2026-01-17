/**
 * SNS Module - Sidebar
 * SNS侧边栏渲染
 */

// Get global API client
const getApiClient = () => {
    if (typeof api !== 'undefined') {
        return api;
    }
    if (window.api) {
        return window.api;
    }
    console.error('API client not found');
    return null;
};

export default {
    userStats: {
        level: 3,
        credit: 100,
        money: 10996.61,
        life: 125,
        iq: 70,
        energy: 150,
        move: 187.5,
        exp: 30
    },

    contacts: [],
    trades: [],
    selectedContact: null,
    currentTab: 'chat',

    /**
     * 渲染SNS页面侧边栏
     */
    render() {
        return `
            <div class="sidebar-section">
                <div class="sidebar-header-row">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="#1a73e8"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-1 17.93c-3.95-.49-7-3.85-7-7.93 0-.62.08-1.21.21-1.79L9 15v1c0 1.1.9 2 2 2v1.93z"/></svg>
                    <span class="sidebar-section-title">Explore the Earth-Y宝</span>
                </div>
                <!-- 用户属性面板 -->
                <div class="user-stats-panel">
                    <div class="user-stats-charts">
                        <div class="user-stat-bars">
                            <div class="stat-bar-item">
                                <span class="stat-label">Level</span>
                                <div class="stat-bar-wrapper">
                                    <div class="stat-bar-container">
                                        <div class="stat-bar" style="width: ${(this.userStats.level / 10) * 100}%"></div>
                                        <span class="stat-value">${this.userStats.level}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="stat-bar-item">
                                <span class="stat-label">Credit</span>
                                <div class="stat-bar-wrapper">
                                    <div class="stat-bar-container">
                                        <div class="stat-bar" style="width: ${(this.userStats.credit / 200) * 100}%"></div>
                                        <span class="stat-value">${this.userStats.credit}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="stat-bar-item">
                                <span class="stat-label">Money</span>
                                <div class="stat-bar-wrapper">
                                    <div class="stat-bar-container">
                                        <div class="stat-bar" style="width: ${Math.min((this.userStats.money / 20000) * 100, 100)}%"></div>
                                        <span class="stat-value">${this.userStats.money.toFixed(2)}</span>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="user-stat-radar">
                            <canvas id="statsRadarChart" width="110" height="110"></canvas>
                        </div>
                    </div>
                </div>
            </div>
            <div class="sidebar-section">
                <!-- Chat / Trade tabs -->
                <div class="sns-sidebar-tabs">
                    <button class="sidebar-tab active" data-tab="chat">Chat</button>
                    <button class="sidebar-tab" data-tab="trade">Trade</button>
                </div>
                <!-- Contact List -->
                <div class="contact-section tab-content active" data-content="chat">
                    <div class="contact-tree" id="contactTree">
                        <div class="tree-item">
                            <span class="tree-toggle">▸</span>
                            <span class="tree-label">Buddies</span>
                        </div>
                        <div class="tree-children" id="contactList"></div>
                    </div>
                </div>
                <!-- Trade List -->
                <div class="trade-section tab-content" data-content="trade">
                    <div class="trade-list" id="tradeList"></div>
                </div>
                <!-- Chat Window -->
                <div class="chat-window" id="chatWindow">
                    <div class="chat-header">
                        <span class="chat-contact-name" id="chatContactName"></span>
                        <button class="chat-close-btn" id="closeChatBtn">×</button>
                    </div>
                    <div class="chat-messages" id="chatMessages"></div>
                    <div class="chat-input-area">
                        <input type="text" class="chat-input" id="chatInput" placeholder="Type a message..." />
                        <button class="chat-send-btn" id="sendMessageBtn">Send</button>
                        <button class="chat-file-btn" id="sendFileBtn">📎</button>
                    </div>
                </div>
            </div>
        `;
    },

    /**
     * 初始化图表和事件监听
     */
    async init() {
        await this.loadUserStats();
        await this.loadContacts();
        await this.loadTrades();
        this.renderRadarChart();
        this.attachEventListeners();
        this.setupTabSwitching();
        this.setupWebSocketListener();
    },

    /**
     * 设置WebSocket消息监听
     */
    setupWebSocketListener() {
        // Listen for WebSocket messages via window event
        window.addEventListener('websocket-message', (event) => {
            const message = event.detail;
            if (message.type === 'new_message') {
                this.handleNewMessage(message.data);
            }
        });
    },

    /**
     * 处理新收到的消息
     */
    handleNewMessage(messageData) {
        const { from_account, content, flag, create_time } = messageData;

        // Check if currently chatting with this contact
        if (this.selectedContact && this.selectedContact.account === from_account) {
            // Display message in chat window immediately
            const chatMessages = document.getElementById('chatMessages');
            if (chatMessages) {
                const messageDiv = document.createElement('div');
                messageDiv.className = `chat-message ${flag === 0 ? 'sent' : 'received'}`;
                messageDiv.innerHTML = `
                    <div class="message-content">${content}</div>
                    <div class="message-time">${new Date(create_time).toLocaleTimeString()}</div>
                `;
                chatMessages.appendChild(messageDiv);
                chatMessages.scrollTop = chatMessages.scrollHeight;
            }
        } else {
            // Add red dot to contact in contact list
            this.markContactUnread(from_account);
        }
    },

    /**
     * 标记联系人有未读消息
     */
    markContactUnread(account) {
        const contactItem = document.querySelector(`.contact-item[data-account="${account}"]`);
        if (contactItem) {
            // Check if badge already exists
            let badge = contactItem.querySelector('.contact-badge');
            if (!badge) {
                badge = document.createElement('span');
                badge.className = 'contact-badge';
                badge.textContent = '●';
                contactItem.appendChild(badge);
            }
        }

        // Update contact in local data
        const contact = this.contacts.find(c => c.account === account);
        if (contact) {
            contact.new_message_flag = true;
        }
    },

    /**
     * 加载用户统计数据
     */
    async loadUserStats() {
        try {
            const apiClient = getApiClient();
            if (!apiClient) return;

            const response = await apiClient.get('/api/sns/user-stats');
            if (response) {
                this.userStats = response;
                // Re-render stats after loading
                const statsPanel = document.querySelector('.user-stats-panel');
                if (statsPanel) {
                    this.renderStats();
                }
            }
        } catch (error) {
            console.error('Failed to load user stats:', error);
        }
    },

    /**
     * 加载联系人列表
     */
    async loadContacts() {
        try {
            const apiClient = getApiClient();
            if (!apiClient) return;

            const response = await apiClient.get('/api/sns/contacts');
            if (response && Array.isArray(response)) {
                this.contacts = response;
                this.renderContacts();
            }
        } catch (error) {
            console.error('Failed to load contacts:', error);
        }
    },

    /**
     * 渲染联系人列表
     */
    renderContacts() {
        const contactList = document.getElementById('contactList');
        if (!contactList) return;

        contactList.innerHTML = this.contacts.map(contact => `
            <div class="contact-item" data-account="${contact.account}">
                <div class="contact-avatar">${contact.nick_name.charAt(0)}</div>
                <span class="contact-name">${contact.nick_name}</span>
                ${contact.new_message_flag ? '<span class="contact-badge">●</span>' : ''}
            </div>
        `).join('');
    },

    /**
     * 加载交易列表
     */
    async loadTrades() {
        try {
            const apiClient = getApiClient();
            if (!apiClient) return;

            const response = await apiClient.get('/api/map/trades');
            if (response && Array.isArray(response)) {
                this.trades = response;
                this.renderTrades();
            }
        } catch (error) {
            console.error('Failed to load trades:', error);
        }
    },

    /**
     * 渲染交易列表
     */
    renderTrades() {
        const tradeList = document.getElementById('tradeList');
        if (!tradeList) return;

        if (this.trades.length === 0) {
            tradeList.innerHTML = '<div class="empty-message">No trades available</div>';
            return;
        }

        tradeList.innerHTML = this.trades.map(trade => `
            <div class="trade-item" data-trade-id="${trade.trade_id}">
                <div class="trade-header">
                    <span class="trade-title">${trade.title}</span>
                    <span class="trade-pay">$${trade.pay}</span>
                </div>
                <div class="trade-detail">${trade.detail || ''}</div>
                <div class="trade-footer">
                    <span class="trade-with">${trade.trade_with_name}</span>
                    <span class="trade-status">${trade.status === 0 ? 'Pending' : 'Completed'}</span>
                </div>
            </div>
        `).join('');
    },

    /**
     * 设置标签切换
     */
    setupTabSwitching() {
        const tabs = document.querySelectorAll('.sidebar-tab');
        const contents = document.querySelectorAll('.tab-content');

        tabs.forEach(tab => {
            tab.addEventListener('click', () => {
                const tabName = tab.dataset.tab;

                // Update active tab
                tabs.forEach(t => t.classList.remove('active'));
                tab.classList.add('active');

                // Update active content
                contents.forEach(c => c.classList.remove('active'));
                const activeContent = document.querySelector(`.tab-content[data-content="${tabName}"]`);
                if (activeContent) {
                    activeContent.classList.add('active');
                }

                this.currentTab = tabName;
            });
        });
    },

    /**
     * 渲染雷达图
     */
    renderRadarChart() {
        const canvas = document.getElementById('statsRadarChart');
        if (!canvas) return;

        const ctx = canvas.getContext('2d');
        const data = {
            labels: ['Life', 'IQ', 'Energy', 'Move', 'Exp'],
            datasets: [{
                data: [
                    this.userStats.life,
                    this.userStats.iq,
                    this.userStats.energy,
                    this.userStats.move,
                    this.userStats.exp
                ],
                backgroundColor: 'rgba(26, 115, 232, 0.2)',
                borderColor: 'rgba(26, 115, 232, 1)',
                borderWidth: 2
            }]
        };

        // Simple radar chart implementation
        this.drawRadarChart(ctx, data, 110, 110);
    },

    /**
     * 绘制雷达图
     */
    drawRadarChart(ctx, data, width, height) {
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2 - 15;
        const labels = data.labels;
        const values = data.datasets[0].data;
        const maxValue = 200;

        ctx.clearRect(0, 0, width, height);

        // Draw grid
        ctx.strokeStyle = '#e0e0e0';
        ctx.lineWidth = 0.5;
        for (let i = 1; i <= 5; i++) {
            ctx.beginPath();
            const r = (radius / 5) * i;
            for (let j = 0; j < labels.length; j++) {
                const angle = (Math.PI * 2 / labels.length) * j - Math.PI / 2;
                const x = centerX + r * Math.cos(angle);
                const y = centerY + r * Math.sin(angle);
                if (j === 0) ctx.moveTo(x, y);
                else ctx.lineTo(x, y);
            }
            ctx.closePath();
            ctx.stroke();
        }

        // Draw axes
        ctx.strokeStyle = '#ccc';
        ctx.lineWidth = 0.5;
        for (let i = 0; i < labels.length; i++) {
            const angle = (Math.PI * 2 / labels.length) * i - Math.PI / 2;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();

            // Draw labels
            ctx.fillStyle = '#666';
            ctx.font = '8px Arial';
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const labelOffset = 12;
            ctx.fillText(labels[i], x + Math.cos(angle) * labelOffset, y + Math.sin(angle) * labelOffset);
        }

        // Draw data
        ctx.fillStyle = data.datasets[0].backgroundColor;
        ctx.strokeStyle = data.datasets[0].borderColor;
        ctx.lineWidth = 1.5;
        ctx.beginPath();
        for (let i = 0; i < values.length; i++) {
            const angle = (Math.PI * 2 / values.length) * i - Math.PI / 2;
            const value = Math.min(values[i] / maxValue, 1);
            const x = centerX + radius * value * Math.cos(angle);
            const y = centerY + radius * value * Math.sin(angle);
            if (i === 0) ctx.moveTo(x, y);
            else ctx.lineTo(x, y);
        }
        ctx.closePath();
        ctx.fill();
        ctx.stroke();
    },

    /**
     * 附加事件监听器
     */
    attachEventListeners() {
        // Contact click
        document.querySelectorAll('.contact-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const account = e.currentTarget.dataset.account;
                this.openChat(account);
            });
        });

        // Close chat
        const closeChatBtn = document.getElementById('closeChatBtn');
        if (closeChatBtn) {
            closeChatBtn.addEventListener('click', () => this.closeChat());
        }

        // Send message
        const sendMessageBtn = document.getElementById('sendMessageBtn');
        if (sendMessageBtn) {
            sendMessageBtn.addEventListener('click', () => this.sendMessage());
        }

        // Send file
        const sendFileBtn = document.getElementById('sendFileBtn');
        if (sendFileBtn) {
            sendFileBtn.addEventListener('click', () => this.sendFile());
        }

        // Enter key to send
        const chatInput = document.getElementById('chatInput');
        if (chatInput) {
            chatInput.addEventListener('keypress', (e) => {
                if (e.key === 'Enter') this.sendMessage();
            });
        }
    },

    /**
     * 打开聊天窗口
     */
    async openChat(account) {
        const contact = this.contacts.find(c => c.account === account);
        if (!contact) return;

        this.selectedContact = contact;
        const chatWindow = document.getElementById('chatWindow');
        const chatContactName = document.getElementById('chatContactName');

        if (chatWindow && chatContactName) {
            chatContactName.textContent = contact.nick_name;
            chatWindow.classList.add('active');
            await this.loadChatHistory(account);

            // Clear unread badge
            this.clearContactUnread(account);

            // Scroll to chat window
            chatWindow.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
    },

    /**
     * 清除联系人未读标记
     */
    clearContactUnread(account) {
        const contactItem = document.querySelector(`.contact-item[data-account="${account}"]`);
        if (contactItem) {
            const badge = contactItem.querySelector('.contact-badge');
            if (badge) {
                badge.remove();
            }
        }

        // Update contact in local data
        const contact = this.contacts.find(c => c.account === account);
        if (contact) {
            contact.new_message_flag = false;
        }
    },

    /**
     * 关闭聊天窗口
     */
    closeChat() {
        const chatWindow = document.getElementById('chatWindow');
        if (chatWindow) {
            chatWindow.classList.remove('active');
            this.selectedContact = null;
        }
    },

    /**
     * 渲染用户统计数据
     */
    renderStats() {
        const statBars = document.querySelectorAll('.stat-bar-item');
        if (statBars.length > 0) {
            statBars[0].querySelector('.stat-bar').style.width = `${(this.userStats.level / 10) * 100}%`;
            statBars[0].querySelector('.stat-value').textContent = this.userStats.level;

            statBars[1].querySelector('.stat-bar').style.width = `${(this.userStats.credit / 200) * 100}%`;
            statBars[1].querySelector('.stat-value').textContent = this.userStats.credit;

            statBars[2].querySelector('.stat-bar').style.width = `${Math.min((this.userStats.money / 20000) * 100, 100)}%`;
            statBars[2].querySelector('.stat-value').textContent = this.userStats.money.toFixed(2);
        }
        this.renderRadarChart();
    },

    /**
     * 加载聊天历史
     */
    async loadChatHistory(account) {
        try {
            const apiClient = getApiClient();
            if (!apiClient) return;

            const response = await apiClient.get(`/api/sns/chat-history/${account}`);
            if (response && Array.isArray(response)) {
                this.renderChatMessages(response);
            }
        } catch (error) {
            console.error('Failed to load chat history:', error);
        }
    },

    /**
     * 渲染聊天消息
     */
    renderChatMessages(messages) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;

        chatMessages.innerHTML = messages.map(msg => `
            <div class="chat-message ${msg.flag === 0 ? 'sent' : 'received'}">
                <div class="message-content">${msg.content}</div>
                <div class="message-time">${new Date(msg.create_time).toLocaleTimeString()}</div>
            </div>
        `).join('');

        chatMessages.scrollTop = chatMessages.scrollHeight;
    },

    /**
     * 发送消息
     */
    async sendMessage() {
        const chatInput = document.getElementById('chatInput');
        if (!chatInput || !this.selectedContact) return;

        const message = chatInput.value.trim();
        if (!message) return;

        try {
            const apiClient = getApiClient();
            if (!apiClient) return;

            await apiClient.post('/api/sns/send-message', {
                to_account: this.selectedContact.account,
                content: message
            });

            chatInput.value = '';
            await this.loadChatHistory(this.selectedContact.account);
        } catch (error) {
            console.error('Failed to send message:', error);
        }
    },

    /**
     * 发送文件
     */
    async sendFile() {
        if (!this.selectedContact) return;

        const input = document.createElement('input');
        input.type = 'file';
        input.onchange = async (e) => {
            const file = e.target.files[0];
            if (!file) return;

            const formData = new FormData();
            formData.append('file', file);
            formData.append('to_account', this.selectedContact.account);

            try {
                const apiClient = getApiClient();
                if (!apiClient) return;

                // Use fetch directly for FormData
                const response = await fetch(`${apiClient.baseUrl}/api/sns/send-file`, {
                    method: 'POST',
                    body: formData
                });

                if (response.ok) {
                    await this.loadChatHistory(this.selectedContact.account);
                }
            } catch (error) {
                console.error('Failed to send file:', error);
            }
        };
        input.click();
    }
};
