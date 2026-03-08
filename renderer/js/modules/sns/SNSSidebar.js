/**
 * SNS Module - Sidebar
 * SNS sidebar rendering
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

    _exploreNickname: '',

    escapeHtml(value) {
        return String(value ?? '')
            .replace(/&/g, '&amp;')
            .replace(/</g, '&lt;')
            .replace(/>/g, '&gt;')
            .replace(/"/g, '&quot;')
            .replace(/'/g, '&#39;');
    },

    formatRadarValue(label, value) {
        const num = Number(value);
        if (!Number.isFinite(num)) return String(value ?? '');

        if (label === 'Money') {
            const pct = Math.round((num / 1000) * 100);
            return `${pct}`;
        }

        const decimals = label === 'Move' ? 1 : 0;
        const fixed = num.toFixed(decimals);
        return decimals === 0 ? fixed : fixed.replace(/\.0+$/, '');
    },

    /**
     * Format a value with dynamic K/M/B/T suffix and compute bar percentage.
     * Returns { display: string, percent: number }.
     */
    formatScaledValue(v) {
        const num = Number(v) || 0;
        // Use "ceiling" unit scaling:
        // - < 1K => show in K (v/1K)
        // - [1K, 1M) => show in M (v/1M)
        // - [1M, 1B) => show in B (v/1B)
        // - [1B, 1T) => show in T (v/1T)
        let tier;
        if (num < 1e3) tier = { divisor: 1e3, suffix: 'K' };
        else if (num < 1e6) tier = { divisor: 1e6, suffix: 'M' };
        else if (num < 1e9) tier = { divisor: 1e9, suffix: 'B' };
        else tier = { divisor: 1e12, suffix: 'T' };

        const ratio = num / tier.divisor;
        const percent = Math.min(ratio * 100, 100);

        const ratioText = ratio
            .toFixed(3)
            .replace(/\.0+$/, '')
            .replace(/(\.\d*?)0+$/, '$1');

        return { display: `${ratioText}${tier.suffix}`, percent };
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

    _truncateDisplayWidth(value, maxWidth) {
        const s = String(value ?? '');
        let width = 0;
        let out = '';
        for (const ch of s) {
            const w = /[\u4e00-\u9fff]/.test(ch) ? 2 : 1;
            if (width + w > maxWidth) break;
            out += ch;
            width += w;
        }
        return out;
    },

    _formatExploreNickname(rawNickname) {
        const name = String(rawNickname ?? '').trim();
        if (!name) return '';
        return this._truncateDisplayWidth(name, 12);
    },

    updateExploreTitle(nickname) {
        const formatted = this._formatExploreNickname(nickname);
        this._exploreNickname = formatted;
        const titleEl = document.getElementById('snsExploreTitle');
        if (!titleEl) return;
        titleEl.textContent = formatted ? `${formatted}` : 'Explore the Earth';
    },

    async loadExploreNickname() {
        try {
            const apiClient = getApiClient();
            if (!apiClient || typeof apiClient.get !== 'function') return;
            const resp = await apiClient.get('/api/sns/user-info');
            if (resp && resp.success && resp.data) {
                this.updateExploreTitle(resp.data.nickname);
            }
        } catch (e) {
            console.warn('[SNSSidebar] Failed to load explore nickname:', e);
        }
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
     * Render SNS page sidebar
     */
    render() {
        return `
            <div class="sidebar-section">
                <div class="sidebar-header-row">
<svg height="26" viewBox="0 -960 960 960" width="26" fill="#1a73e8"><path d="M572-405.5q43-21.5 68-63.5-35-27-75.5-43T480-528q-44 0-84.5 16T320-469q25 42 68 63.5t92 21.5q49 0 92-21.5ZM480-576q30 0 51-21t21-51q0-30-21-51t-51-21q-30 0-51 21t-21 51q0 30 21 51t51 21Zm0 385q119-107 179.5-197T720-549q0-105-68.5-174T480-792q-103 0-171.5 69T240-549q0 71 60.5 161T480-191Zm0 95Q323-227 245.5-339.5T168-549q0-134 89-224.5T480-864q133 0 222.5 90.5T792-549q0 97-77 209T480-96Zm0-456Z"/></svg>
                    <span class="sidebar-section-title" id="snsExploreTitle"></span>
                </div>
                <!-- User stats panel -->
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
                                        <div class="stat-bar" style="width: ${this.formatScaledValue(this.userStats.credit).percent}%"></div>
                                        <span class="stat-value">${this.formatScaledValue(this.userStats.credit).display}</span>
                                    </div>
                                </div>
                            </div>
                            <div class="stat-bar-item">
                                <span class="stat-label">Exp</span>
                                <div class="stat-bar-wrapper">
                                    <div class="stat-bar-container">
                                        <div class="stat-bar" style="width: ${this.formatScaledValue(this.userStats.exp).percent}%"></div>
                                        <span class="stat-value">${this.formatScaledValue(this.userStats.exp).display}</span>
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
     * Initialize charts and event listeners
     */
    async init() {
        await this.loadExploreNickname();
        await this.loadUserStats();
        await this.loadContacts();
        await this.loadTrades();
        this.renderRadarChart();
        this.setupThemeObserver();
        this.attachEventListeners();
        this.setupTabSwitching();
        this.setupWebSocketListener();

        if (!this._exploreTitleListenerBound) {
            window.addEventListener('sns-user-info-updated', (event) => {
                const detail = event && event.detail ? event.detail : {};
                this.updateExploreTitle(detail.nickname);
            });
            this._exploreTitleListenerBound = true;
        }
    },

    /**
     * Set up WebSocket message listener
     */
    setupWebSocketListener() {
        // Listen for WebSocket messages via window event
        window.addEventListener('websocket-message', (event) => {
            const message = event.detail;
            if (message.type === 'new_message') {
                this.handleNewMessage(message.data);
            } else if (message.type === 'contact_upserted') {
                this.handleContactUpserted(message.data);
            } else if (message.type === 'user_stats_update') {
                // Handle user stats updates
                this.handleUserStatsUpdate(message.data);
            }
        });
    },

    upsertContact(contactData) {
        if (!contactData || !contactData.account) return null;

        const existing = this.contacts.find(c => c.account === contactData.account);
        if (existing) {
            Object.assign(existing, contactData);
            return existing;
        }

        const fallbackNick = contactData.nick_name || contactData.account;
        const next = {
            id: contactData.id,
            account: contactData.account,
            nick_name: fallbackNick,
            groups: contactData.groups,
            subscription: contactData.subscription,
            new_message_flag: !!contactData.new_message_flag,
            last_message_time: contactData.last_message_time || null,
        };

        this.contacts.unshift(next);
        return next;
    },

    handleContactUpserted(contactData) {
        const upserted = this.upsertContact(contactData);
        if (!upserted) return;

        this.renderContacts();
    },

    /**
     * Handle user stats updates
     */
    handleUserStatsUpdate(data) {
        console.log('Received user stats update:', data);

        // Update local userStats
        if (data) {
            this.userStats = {
                level: data.level ?? this.userStats.level,
                credit: data.credit ?? this.userStats.credit,
                money: data.money ?? this.userStats.money,
                life: data.life ?? this.userStats.life,
                iq: data.iq ?? this.userStats.iq,
                energy: data.energy ?? this.userStats.energy,
                move: data.move ?? this.userStats.move,
                exp: data.exp ?? this.userStats.exp
            };

            // Re-render charts and stats
            this.renderStats();

            console.log('User stats updated successfully:', this.userStats);
        }
    },

    /**
     * Handle newly received message
     */
    handleNewMessage(messageData) {
        const { from_account, content, flag, create_time, contact } = messageData;

        if (contact) {
            this.upsertContact(contact);
        } else if (from_account) {
            this.upsertContact({
                account: from_account,
                nick_name: from_account,
                new_message_flag: flag !== 0,
                last_message_time: create_time || null,
            });
        }

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

        this.renderContacts();
    },

    /**
     * Mark a contact as unread
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
     * Load user stats
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
     * Load contacts
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
     * Render contacts
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
     * Load trades
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
     * Render trades
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
     * Set up tab switching
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
     * Render radar chart
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

        // Money radar value: (money/1000)*100, capped at 100 for line length
        const moneyRadar = Math.min(Math.round((this.userStats.money / 1000) * 100), 100);

        const data = {
            labels: ['Energy', 'Life', 'Money', 'Move', 'IQ'],
            datasets: [{
                data: [
                    this.userStats.energy,
                    this.userStats.life,
                    moneyRadar,
                    this.userStats.move,
                    this.userStats.iq
                ],
                // Raw values for label display (Money shows uncapped percentage)
                rawValues: [
                    this.userStats.energy,
                    this.userStats.life,
                    this.userStats.money,
                    this.userStats.move,
                    this.userStats.iq
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
     * Draw radar chart
     */
    drawRadarChart(ctx, data, width, height) {
        const centerX = width / 2;
        const centerY = height / 2;
        const radius = Math.min(width, height) / 2 - 25;
        const labels = data.labels;
        const values = data.datasets[0].data;
        const maxValue = 100;
        const rawValues = data.datasets[0].rawValues || values;

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

        // Draw grid - use bar-chart palette
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

        // Draw axes - use bar-chart palette
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

            // Draw labels with values - append numbers, use bar-chart palette
            ctx.textAlign = 'center';
            ctx.textBaseline = 'middle';
            const labelOffset = 16;
            const labelX = x + Math.cos(angle) * labelOffset;
            const labelY = y + Math.sin(angle) * labelOffset;

            ctx.font = '9px Inter, Arial';
            this.drawOutlinedText(ctx, `${labels[i]}`, labelX, labelY - 4, theme.textSecondary, theme.labelStroke);
            ctx.font = '8px Inter, Arial';
            this.drawOutlinedText(ctx, this.formatRadarValue(labels[i], rawValues[i]), labelX, labelY + 6, theme.textPrimary, theme.labelStroke);
        }

        // Draw data - use bar-chart palette
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

        // Draw data points - use bar-chart palette
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
     * Attach event listeners
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
     * Attach contact click event listeners
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
     * Open chat window
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
     * Clear contact unread indicator
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
     * Close chat window
     */
    closeChat() {
        const chatWindow = document.getElementById('chatWindow');
        if (chatWindow) {
            chatWindow.classList.remove('active');
            this.selectedContact = null;
        }
    },

    /**
     * Render user stats
     */
    renderStats() {
        const statBars = document.querySelectorAll('.stat-bar-item');
        if (statBars.length > 0) {
            // Level bar: max 10
            statBars[0].querySelector('.stat-bar').style.width = `${(this.userStats.level / 10) * 100}%`;
            statBars[0].querySelector('.stat-value').textContent = this.userStats.level;

            // Credit bar: dynamic K/M/B/T scaling
            const creditFmt = this.formatScaledValue(this.userStats.credit);
            statBars[1].querySelector('.stat-bar').style.width = `${creditFmt.percent}%`;
            statBars[1].querySelector('.stat-value').textContent = creditFmt.display;

            // Exp bar: dynamic K/M/B/T scaling
            const expFmt = this.formatScaledValue(this.userStats.exp);
            statBars[2].querySelector('.stat-bar').style.width = `${expFmt.percent}%`;
            statBars[2].querySelector('.stat-value').textContent = expFmt.display;
        }
        this.renderRadarChart();
    },

    /**
     * Load chat history
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
     * Render chat messages
     */
    renderChatMessages(messages) {
        const chatMessages = document.getElementById('chatMessages');
        if (!chatMessages) return;

        chatMessages.innerHTML = messages.map(msg => this.createChatMessageHTML(msg)).join('');

        chatMessages.scrollTop = chatMessages.scrollHeight;
    },

    /**
     * Send message
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
     * Send file
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
