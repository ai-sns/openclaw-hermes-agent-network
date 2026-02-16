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

    _themeObserver: null,
    _themeListenerBound: false,

    contacts: [],
    trades: [],
    selectedContact: null,
    currentTab: 'chat',
    contactSearchQuery: '',
    tradeSearchQuery: '',
    _chatLinkListenerBound: false,

    escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    renderMessageContent(content) {
        const escaped = this.escapeHtml(content);
        const withLinks = escaped.replace(/(https?:\/\/[^\s<]+)/g, (url) => {
            return `<a href="${url}" class="chat-link" data-external-url="${url}" target="_blank" rel="noopener noreferrer">${url}</a>`;
        });

        return withLinks.replace(/\n/g, '<br>');
    },

    createChatMessageHTML(message) {
        return `
            <div class="chat-message ${message.flag === 0 ? 'sent' : 'received'}">
                <div class="message-content">${this.renderMessageContent(message.content)}</div>
                <div class="message-time">${new Date(message.create_time).toLocaleTimeString()}</div>
            </div>
        `;
    },

    bindChatLinkOpenHandler() {
        if (this._chatLinkListenerBound) return;

        document.addEventListener('click', (event) => {
            const link = event.target.closest('.chat-link[data-external-url]');
            if (!link) return;

            event.preventDefault();
            const url = link.dataset.externalUrl || link.getAttribute('href');
            if (!url) return;

            if (window.electronAPI && typeof window.electronAPI.openUrl === 'function') {
                window.electronAPI.openUrl(url);
            } else {
                window.open(url, '_blank', 'noopener,noreferrer');
            }
        });

        this._chatLinkListenerBound = true;
    },

    getRadarTheme() {
        const styles = getComputedStyle(document.body);
        const getVar = (name, fallback) => (styles.getPropertyValue(name).trim() || fallback);
        const isDark = document.body.classList.contains('theme-dark');

        return {
            isDark,
            primary: getVar('--color-primary', '#1a73e8'),
            primaryLight: getVar('--color-primary-light', '#1a73e8'),
            textPrimary: getVar('--text-primary', '#111827'),
            textSecondary: getVar('--text-secondary', '#4B5563'),
            textTertiary: getVar('--text-tertiary', '#6B7280'),
            borderColor: getVar('--border-color', '#E5E7EB'),
            labelStroke: isDark ? 'rgba(0, 0, 0, 0.55)' : 'rgba(255, 255, 255, 0.85)'
        };
    },

    hexToRgba(hex, alpha) {
        const value = (hex || '').trim();
        const match = /^#?([a-f\d]{2})([a-f\d]{2})([a-f\d]{2})$/i.exec(value);
        if (!match) return value;
        const r = parseInt(match[1], 16);
        const g = parseInt(match[2], 16);
        const b = parseInt(match[3], 16);
        return `rgba(${r}, ${g}, ${b}, ${alpha})`;
    },

    toRgba(color, alpha) {
        const value = (color || '').trim();
        if (!value) return value;
        if (value.startsWith('#')) return this.hexToRgba(value, alpha);
        const rgbaMatch = /^rgba\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*,\s*([\d.]+)\s*\)$/i.exec(value);
        if (rgbaMatch) return `rgba(${rgbaMatch[1]}, ${rgbaMatch[2]}, ${rgbaMatch[3]}, ${alpha})`;
        const rgbMatch = /^rgb\(\s*(\d+)\s*,\s*(\d+)\s*,\s*(\d+)\s*\)$/i.exec(value);
        if (rgbMatch) return `rgba(${rgbMatch[1]}, ${rgbMatch[2]}, ${rgbMatch[3]}, ${alpha})`;
        return value;
    },

    drawOutlinedText(ctx, text, x, y, fillStyle, strokeStyle) {
        ctx.strokeStyle = strokeStyle;
        ctx.lineWidth = 3;
        ctx.strokeText(text, x, y);
        ctx.fillStyle = fillStyle;
        ctx.fillText(text, x, y);
    },

    setupThemeObserver() {
        if (!this._themeListenerBound) {
            window.addEventListener('theme-changed', () => {
                this.renderRadarChart();
            });
            this._themeListenerBound = true;
        }

        if (this._themeObserver) return;
        if (!document.body) return;

        this._themeObserver = new MutationObserver(() => {
            this.renderRadarChart();
        });

        this._themeObserver.observe(document.body, {
            attributes: true,
            attributeFilter: ['class']
        });
    },

    /**
     * 渲染SNS页面侧边栏
     */
    render() {
        return `
            <div class="sidebar-section">
                <div class="sidebar-header-row">
                    <svg viewBox="0 0 24 24" width="18" height="18" fill="none" stroke="#1a73e8" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" xmlns="http://www.w3.org/2000/svg">
  <!-- 地图轮廓 -->
  <polygon points="1 6 1 22 8 18 16 22 23 18 23 2 16 6 8 2 1 6"></polygon>
  <!-- 内部折痕 -->
  <line x1="8" y1="2" x2="8" y2="18"></line>
  <line x1="16" y1="6" x2="16" y2="22"></line>
</svg>
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
                    <!-- Search Box -->
                    <div class="sns-search-box">
                        <div class="sns-search-wrapper">
                            <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                            </svg>
                            <input type="text" class="sns-search-input" id="contactSearchInput" placeholder="Search contacts..." />
                            <button class="sns-search-clear" id="contactSearchClear">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
                    <div class="contact-tree" id="contactTree">
                        <div class="tree-children" id="contactList"></div>
                    </div>
                </div>
                <!-- Trade List -->
                <div class="trade-section tab-content" data-content="trade">
                    <!-- Search Box -->
                    <div class="sns-search-box">
                        <div class="sns-search-wrapper">
                            <svg class="sns-search-icon" viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M15.5 14h-.79l-.28-.27C15.41 12.59 16 11.11 16 9.5 16 5.91 13.09 3 9.5 3S3 5.91 3 9.5 5.91 16 9.5 16c1.61 0 3.09-.59 4.23-1.57l.27.28v.79l5 4.99L20.49 19l-4.99-5zm-6 0C7.01 14 5 11.99 5 9.5S7.01 5 9.5 5 14 7.01 14 9.5 11.99 14 9.5 14z"/>
                            </svg>
                            <input type="text" class="sns-search-input" id="tradeSearchInput" placeholder="Search trades..." />
                            <button class="sns-search-clear" id="tradeSearchClear">
                                <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                    <path d="M19 6.41L17.59 5 12 10.59 6.41 5 5 6.41 10.59 12 5 17.59 6.41 19 12 13.41 17.59 19 19 17.59 13.41 12z"/>
                                </svg>
                            </button>
                        </div>
                    </div>
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
                        <button class="chat-file-btn" id="sendFileBtn" title="Attach file">
                            <svg viewBox="0 0 24 24" width="16" height="16" fill="currentColor">
                                <path d="M16.5 6v11.5c0 2.21-1.79 4-4 4s-4-1.79-4-4V5c0-1.38 1.12-2.5 2.5-2.5s2.5 1.12 2.5 2.5v10.5c0 .55-.45 1-1 1s-1-.45-1-1V6H10v9.5c0 1.38 1.12 2.5 2.5 2.5s2.5-1.12 2.5-2.5V5c0-2.21-1.79-4-4-4S7 2.79 7 5v12.5c0 3.04 2.46 5.5 5.5 5.5s5.5-2.46 5.5-5.5V6h-1.5z"/>
                            </svg>
                        </button>
                        <button class="chat-send-btn" id="sendMessageBtn" title="Send message">
                            <svg viewBox="0 0 24 24" width="18" height="18" fill="currentColor">
                                <path d="M2.01 21L23 12 2.01 3 2 10l15 2-15 2z"/>
                            </svg>
                        </button>
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
        this.setupThemeObserver();
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
            } else if (message.type === 'user_stats_update') {
                // 处理用户统计数据更新
                this.handleUserStatsUpdate(message.data);
            }
        });
    },

    /**
     * 处理用户统计数据更新
     */
    handleUserStatsUpdate(data) {
        console.log('Received user stats update:', data);

        // 更新本地userStats对象
        if (data) {
            this.userStats = {
                level: data.level || this.userStats.level,
                credit: data.credit || this.userStats.credit,
                money: data.money || this.userStats.money,
                life: data.life || this.userStats.life,
                iq: data.iq || this.userStats.iq,
                energy: data.energy || this.userStats.energy,
                move: data.move || this.userStats.move,
                exp: data.exp || this.userStats.exp
            };

            // 重新渲染图表和统计数据
            this.renderStats();

            console.log('User stats updated successfully:', this.userStats);
        }
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
                    <div class="message-content">${this.renderMessageContent(content)}</div>
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

        // Filter contacts based on search query
        const filteredContacts = this.contacts.filter(contact => {
            if (!this.contactSearchQuery) return true;
            const query = this.contactSearchQuery.toLowerCase();
            return contact.nick_name.toLowerCase().includes(query) ||
                   contact.account.toLowerCase().includes(query);
        });

        if (filteredContacts.length === 0) {
            contactList.innerHTML = '<div class="empty-message">No contacts found</div>';
            return;
        }

        contactList.innerHTML = filteredContacts.map(contact => `
            <div class="contact-item" data-account="${contact.account}">
                <div class="contact-avatar">${contact.nick_name.charAt(0)}</div>
                <span class="contact-name">${contact.nick_name}</span>
                ${contact.new_message_flag ? '<span class="contact-badge">●</span>' : ''}
            </div>
        `).join('');

        // Re-attach event listeners for filtered contacts
        this.attachContactListeners();
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

        // Filter trades based on search query
        const filteredTrades = this.trades.filter(trade => {
            if (!this.tradeSearchQuery) return true;
            const query = this.tradeSearchQuery.toLowerCase();
            return trade.title.toLowerCase().includes(query) ||
                   (trade.detail && trade.detail.toLowerCase().includes(query)) ||
                   trade.trade_with_name.toLowerCase().includes(query);
        });

        if (filteredTrades.length === 0) {
            tradeList.innerHTML = '<div class="empty-message">No trades found</div>';
            return;
        }

        tradeList.innerHTML = filteredTrades.map(trade => `
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
        const dpr = window.devicePixelRatio || 1;
        const width = 110;
        const height = 110;

        canvas.width = Math.floor(width * dpr);
        canvas.height = Math.floor(height * dpr);
        canvas.style.width = `${width}px`;
        canvas.style.height = `${height}px`;

        ctx.setTransform(1, 0, 0, 1, 0, 0);
        ctx.clearRect(0, 0, canvas.width, canvas.height);
        ctx.setTransform(dpr, 0, 0, dpr, 0, 0);

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
        this.drawRadarChart(ctx, data, width, height);
    },

    /**
     * 绘制雷达图
     */
    drawRadarChart(ctx, data, width, height) {
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2 - 25;
        const labels = data.labels;
        const values = data.datasets[0].data;
        const maxValue = 200;

        const theme = this.getRadarTheme();
        const gridStroke = this.toRgba(theme.textTertiary, theme.isDark ? 0.35 : 0.4);
        const axisStroke = this.toRgba(theme.textSecondary, theme.isDark ? 0.45 : 0.5);
        const dataFill = this.toRgba(theme.primary, theme.isDark ? 0.22 : 0.14);
        const dataStroke = this.toRgba(theme.primary, 0.95);
        const pointFill = theme.primaryLight;

        // Alternating ring fill to improve readability in both themes
        const ringA = this.toRgba(theme.primary, theme.isDark ? 0.08 : 0.05);
        const ringB = this.toRgba(theme.primary, theme.isDark ? 0.03 : 0.02);

        for (let i = 5; i >= 1; i--) {
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
            ctx.fillStyle = (i % 2 === 0) ? ringA : ringB;
            ctx.fill();
        }

        // Draw grid - 使用柱状图的配色
        ctx.strokeStyle = gridStroke;
        ctx.lineWidth = 1;
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

        // Draw axes - 使用柱状图的配色
        ctx.strokeStyle = axisStroke;
        ctx.lineWidth = 1;
        for (let i = 0; i < labels.length; i++) {
            const angle = (Math.PI * 2 / labels.length) * i - Math.PI / 2;
            const x = centerX + radius * Math.cos(angle);
            const y = centerY + radius * Math.sin(angle);
            ctx.beginPath();
            ctx.moveTo(centerX, centerY);
            ctx.lineTo(x, y);
            ctx.stroke();

            // Draw labels with values - 文字后面跟数字，使用柱状图的配色
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const labelOffset = 16;
            const labelX = x + Math.cos(angle) * labelOffset;
            const labelY = y + Math.sin(angle) * labelOffset;

            ctx.font = '9px Inter, Arial';
            this.drawOutlinedText(ctx, `${labels[i]}`, labelX, labelY - 4, theme.textSecondary, theme.labelStroke);
            ctx.font = '8px Inter, Arial';
            this.drawOutlinedText(ctx, `${values[i]}`, labelX, labelY + 6, theme.textPrimary, theme.labelStroke);
        }

        // Draw data - 使用柱状图的配色
        ctx.fillStyle = dataFill;
        ctx.strokeStyle = dataStroke;
        ctx.lineWidth = 2;
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

        // Draw data points - 使用柱状图的配色
        for (let i = 0; i < values.length; i++) {
            const angle = (Math.PI * 2 / values.length) * i - Math.PI / 2;
            const value = Math.min(values[i] / maxValue, 1);
            const x = centerX + radius * value * Math.cos(angle);
            const y = centerY + radius * value * Math.sin(angle);

            // Draw point
            ctx.fillStyle = pointFill;
            ctx.beginPath();
            ctx.arc(x, y, 3, 0, Math.PI * 2);
            ctx.fill();
        }
    },

    /**
     * 附加事件监听器
     */
    attachEventListeners() {
        this.bindChatLinkOpenHandler();

        // Contact click
        this.attachContactListeners();

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

        // Contact search
        const contactSearchInput = document.getElementById('contactSearchInput');
        const contactSearchClear = document.getElementById('contactSearchClear');
        if (contactSearchInput) {
            contactSearchInput.addEventListener('input', (e) => {
                this.contactSearchQuery = e.target.value;
                this.renderContacts();
                // Show/hide clear button
                if (contactSearchClear) {
                    contactSearchClear.classList.toggle('visible', e.target.value.length > 0);
                }
            });
        }
        if (contactSearchClear) {
            contactSearchClear.addEventListener('click', () => {
                if (contactSearchInput) {
                    contactSearchInput.value = '';
                    this.contactSearchQuery = '';
                    this.renderContacts();
                    contactSearchClear.classList.remove('visible');
                }
            });
        }

        // Trade search
        const tradeSearchInput = document.getElementById('tradeSearchInput');
        const tradeSearchClear = document.getElementById('tradeSearchClear');
        if (tradeSearchInput) {
            tradeSearchInput.addEventListener('input', (e) => {
                this.tradeSearchQuery = e.target.value;
                this.renderTrades();
                // Show/hide clear button
                if (tradeSearchClear) {
                    tradeSearchClear.classList.toggle('visible', e.target.value.length > 0);
                }
            });
        }
        if (tradeSearchClear) {
            tradeSearchClear.addEventListener('click', () => {
                if (tradeSearchInput) {
                    tradeSearchInput.value = '';
                    this.tradeSearchQuery = '';
                    this.renderTrades();
                    tradeSearchClear.classList.remove('visible');
                }
            });
        }
    },

    /**
     * 附加联系人点击事件监听器
     */
    attachContactListeners() {
        document.querySelectorAll('.contact-item').forEach(item => {
            item.addEventListener('click', (e) => {
                const account = e.currentTarget.dataset.account;
                this.openChat(account);
            });
        });
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

        chatMessages.innerHTML = messages.map(msg => this.createChatMessageHTML(msg)).join('');

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
