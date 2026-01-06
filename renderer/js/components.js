/**
 * AI-SNS UI Components
 * 可复用的UI组件
 */

// ==================== 覆盖原生 alert/confirm/prompt ====================
// 防止原生弹框破坏 Electron 无边框窗口的焦点状态

(function() {
    const originalAlert = window.alert;
    const originalConfirm = window.confirm;
    const originalPrompt = window.prompt;

    // 覆盖 alert - 使用 console.warn 和 Notification 代替
    window.alert = function(message) {
        console.warn('[Alert]', message);
        // 如果 Notification 组件可用，使用它显示消息
        if (typeof Notification !== 'undefined' && Notification.warning) {
            Notification.warning(String(message));
        }
        // 恢复焦点
        setTimeout(() => {
            window.focus();
            document.body.focus();
        }, 10);
    };

    // 覆盖 confirm - 始终返回 true，避免阻塞
    window.confirm = function(message) {
        console.warn('[Confirm]', message);
        return true;
    };

    // 覆盖 prompt - 返回空字符串，避免阻塞
    window.prompt = function(message, defaultValue) {
        console.warn('[Prompt]', message);
        return defaultValue || '';
    };
})();

// ==================== Modal Component ====================

class Modal {
    constructor(options = {}) {
        this.title = options.title || '';
        this.content = options.content || '';
        this.onConfirm = options.onConfirm || null;
        this.onCancel = options.onCancel || null;
        this.confirmText = options.confirmText || '确认';
        this.cancelText = options.cancelText || '取消';
        this.showCancel = options.showCancel !== false;
        this.element = null;
    }

    render() {
        const html = `
            <div class="modal-overlay">
                <div class="modal">
                    <div class="modal-header">
                        <h3 class="modal-title">${this.title}</h3>
                        <button class="modal-close" data-action="close">&times;</button>
                    </div>
                    <div class="modal-body">
                        ${this.content}
                    </div>
                    <div class="modal-footer">
                        ${this.showCancel ? `<button class="btn btn-secondary" data-action="cancel">${this.cancelText}</button>` : ''}
                        <button class="btn btn-primary" data-action="confirm">${this.confirmText}</button>
                    </div>
                </div>
            </div>
        `;

        const container = document.getElementById('modalContainer');
        container.innerHTML = html;
        this.element = container.querySelector('.modal-overlay');

        this.bindEvents();
        return this;
    }

    bindEvents() {
        this.element.addEventListener('click', (e) => {
            const action = e.target.dataset.action;

            if (action === 'close' || action === 'cancel') {
                this.close();
                if (this.onCancel) this.onCancel();
            } else if (action === 'confirm') {
                if (this.onConfirm) {
                    const result = this.onConfirm(this);
                    if (result !== false) {
                        this.close();
                    }
                } else {
                    this.close();
                }
            }
        });

        // 点击遮罩层关闭
        this.element.addEventListener('click', (e) => {
            if (e.target === this.element) {
                this.close();
                if (this.onCancel) this.onCancel();
            }
        });

        // ESC键关闭
        document.addEventListener('keydown', this.handleKeydown = (e) => {
            if (e.key === 'Escape') {
                this.close();
                if (this.onCancel) this.onCancel();
            }
        });
    }

    close() {
        if (this.element) {
            this.element.remove();
            document.removeEventListener('keydown', this.handleKeydown);
        }
    }

    getFormData() {
        const form = this.element.querySelector('form');
        if (!form) return {};

        const formData = new FormData(form);
        const data = {};
        for (let [key, value] of formData.entries()) {
            data[key] = value;
        }
        return data;
    }

    static show(options) {
        return new Modal(options).render();
    }

    static confirm(message, onConfirm) {
        return Modal.show({
            title: '确认',
            content: `<p>${message}</p>`,
            onConfirm
        });
    }

    static alert(message, title = '提示') {
        return Modal.show({
            title,
            content: `<p>${message}</p>`,
            showCancel: false
        });
    }
}

// ==================== Notification Component ====================

class Notification {
    static container = null;
    static timeout = 5000;

    static init() {
        this.container = document.getElementById('notificationContainer');
    }

    static show(message, type = 'info', duration = this.timeout) {
        if (!this.container) this.init();

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;

        this.container.appendChild(notification);

        // 绑定关闭按钮
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.remove(notification);
        });

        // 自动移除
        if (duration > 0) {
            setTimeout(() => {
                this.remove(notification);
            }, duration);
        }

        return notification;
    }

    static remove(notification) {
        notification.style.animation = 'slideOut 0.3s ease forwards';
        setTimeout(() => {
            notification.remove();
        }, 300);
    }

    static success(message, duration) {
        return this.show(message, 'success', duration);
    }

    static error(message, duration) {
        return this.show(message, 'error', duration);
    }

    static warning(message, duration) {
        return this.show(message, 'warning', duration);
    }

    static info(message, duration) {
        return this.show(message, 'info', duration);
    }
}

// ==================== Card Component ====================

function createCard(options = {}) {
    const {
        title = '',
        description = '',
        icon = '',
        actions = [],
        className = '',
        onClick = null
    } = options;

    const actionsHtml = actions.map(action => `
        <button class="btn ${action.className || 'btn-secondary'}" data-action="${action.action}">
            ${action.label}
        </button>
    `).join('');

    const card = document.createElement('div');
    card.className = `card ${className}`;
    card.innerHTML = `
        <div class="card-header">
            <div class="card-title">
                ${icon ? `<span class="card-icon">${icon}</span>` : ''}
                ${title}
            </div>
        </div>
        ${description ? `<div class="card-description">${description}</div>` : ''}
        ${actionsHtml ? `<div class="card-footer">${actionsHtml}</div>` : ''}
    `;

    if (onClick) {
        card.style.cursor = 'pointer';
        card.addEventListener('click', (e) => {
            if (!e.target.closest('button')) {
                onClick(card);
            }
        });
    }

    // 绑定操作按钮事件
    actions.forEach(action => {
        const btn = card.querySelector(`[data-action="${action.action}"]`);
        if (btn && action.onClick) {
            btn.addEventListener('click', (e) => {
                e.stopPropagation();
                action.onClick(card);
            });
        }
    });

    return card;
}

// ==================== Chat Message Component ====================

function createChatMessage(message) {
    const {
        role = 'user',
        content = '',
        timestamp = null
    } = message;

    const messageEl = document.createElement('div');
    messageEl.className = `message ${role}`;
    messageEl.innerHTML = `
        <div class="message-content">${escapeHtml(content)}</div>
        ${timestamp ? `<div class="message-time">${formatTime(timestamp)}</div>` : ''}
    `;

    return messageEl;
}

// ==================== Chat Item Component ====================

function createChatItem(chat, onClick) {
    const {
        id,
        name = '',
        avatar = '',
        lastMessage = '',
        unread = 0
    } = chat;

    const chatItem = document.createElement('div');
    chatItem.className = 'chat-item';
    chatItem.dataset.chatId = id;
    chatItem.innerHTML = `
        <div class="chat-item-avatar">${avatar || name.charAt(0).toUpperCase()}</div>
        <div class="chat-item-info">
            <div class="chat-item-name">${name}</div>
            <div class="chat-item-preview">${lastMessage}</div>
        </div>
        ${unread > 0 ? `<span class="badge badge-primary">${unread}</span>` : ''}
    `;

    if (onClick) {
        chatItem.addEventListener('click', () => onClick(chat));
    }

    return chatItem;
}

// ==================== Buddy Item Component ====================

function createBuddyItem(buddy, onClick) {
    const {
        id,
        name = '',
        status = 'offline',
        avatar = ''
    } = buddy;

    const buddyItem = document.createElement('div');
    buddyItem.className = 'buddy-item';
    buddyItem.dataset.buddyId = id;
    buddyItem.innerHTML = `
        <div class="buddy-avatar">${avatar || name.charAt(0).toUpperCase()}</div>
        <div class="buddy-info">
            <div class="buddy-name">${name}</div>
            <div class="buddy-status">
                <span class="status-indicator status-${status}"></span>
                ${getStatusText(status)}
            </div>
        </div>
    `;

    if (onClick) {
        buddyItem.addEventListener('click', () => onClick(buddy));
    }

    return buddyItem;
}

// ==================== Form Builder ====================

class FormBuilder {
    constructor() {
        this.fields = [];
    }

    addTextField(name, label, options = {}) {
        this.fields.push({
            type: 'text',
            name,
            label,
            ...options
        });
        return this;
    }

    addTextArea(name, label, options = {}) {
        this.fields.push({
            type: 'textarea',
            name,
            label,
            ...options
        });
        return this;
    }

    addSelect(name, label, selectOptions, options = {}) {
        this.fields.push({
            type: 'select',
            name,
            label,
            options: selectOptions,
            ...options
        });
        return this;
    }

    addNumber(name, label, options = {}) {
        this.fields.push({
            type: 'number',
            name,
            label,
            ...options
        });
        return this;
    }

    addCheckbox(name, label, options = {}) {
        this.fields.push({
            type: 'checkbox',
            name,
            label,
            ...options
        });
        return this;
    }

    render() {
        const form = document.createElement('form');
        form.className = 'form';

        this.fields.forEach(field => {
            const group = document.createElement('div');
            group.className = 'form-group';

            const label = document.createElement('label');
            label.className = 'form-label';
            label.textContent = field.label;
            label.htmlFor = field.name;

            let input;
            switch (field.type) {
                case 'textarea':
                    input = document.createElement('textarea');
                    input.className = 'form-textarea';
                    input.rows = field.rows || 4;
                    break;

                case 'select':
                    input = document.createElement('select');
                    input.className = 'form-select';
                    (field.options || []).forEach(opt => {
                        const option = document.createElement('option');
                        option.value = opt.value;
                        option.textContent = opt.label;
                        input.appendChild(option);
                    });
                    break;

                case 'checkbox':
                    const checkboxWrapper = document.createElement('label');
                    checkboxWrapper.className = 'form-checkbox';
                    input = document.createElement('input');
                    input.type = 'checkbox';
                    checkboxWrapper.appendChild(input);
                    checkboxWrapper.appendChild(document.createTextNode(field.label));
                    group.appendChild(checkboxWrapper);
                    break;

                default:
                    input = document.createElement('input');
                    input.className = 'form-input';
                    input.type = field.type;
            }

            if (input) {
                input.name = field.name;
                input.id = field.name;
                if (field.placeholder) input.placeholder = field.placeholder;
                if (field.value !== undefined) input.value = field.value;
                if (field.required) input.required = true;
                if (field.min !== undefined) input.min = field.min;
                if (field.max !== undefined) input.max = field.max;
                if (field.step !== undefined) input.step = field.step;

                if (field.type !== 'checkbox') {
                    group.appendChild(label);
                    group.appendChild(input);
                }
            }

            if (field.helper) {
                const helper = document.createElement('span');
                helper.className = 'form-helper';
                helper.textContent = field.helper;
                group.appendChild(helper);
            }

            form.appendChild(group);
        });

        return form;
    }
}

// ==================== Utility Functions ====================

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

function formatTime(timestamp) {
    const date = new Date(timestamp);
    const now = new Date();
    const diff = now - date;

    if (diff < 60000) {
        return '刚刚';
    } else if (diff < 3600000) {
        return `${Math.floor(diff / 60000)}分钟前`;
    } else if (diff < 86400000) {
        return `${Math.floor(diff / 3600000)}小时前`;
    } else {
        return date.toLocaleDateString('zh-CN');
    }
}

function getStatusText(status) {
    const statusTexts = {
        'available': '在线',
        'chat': '聊天中',
        'away': '离开',
        'xa': '长时间离开',
        'dnd': '请勿打扰',
        'offline': '离线'
    };
    return statusTexts[status] || status;
}

function generateId() {
    return Date.now().toString(36) + Math.random().toString(36).substr(2);
}

// ==================== Loading States ====================

function showLoading(container) {
    const loading = document.createElement('div');
    loading.className = 'loading-overlay';
    loading.innerHTML = '<div class="spinner"></div>';
    container.style.position = 'relative';
    container.appendChild(loading);
    return loading;
}

function hideLoading(loading) {
    if (loading && loading.parentNode) {
        loading.remove();
    }
}

function showEmptyState(container, options = {}) {
    const {
        icon = '📭',
        title = '暂无数据',
        description = '',
        actionText = '',
        onAction = null
    } = options;

    container.innerHTML = `
        <div class="empty-state">
            <div class="empty-state-icon">${icon}</div>
            <div class="empty-state-title">${title}</div>
            ${description ? `<div class="empty-state-description">${description}</div>` : ''}
            ${actionText ? `<button class="btn btn-primary empty-state-action">${actionText}</button>` : ''}
        </div>
    `;

    if (onAction) {
        const actionBtn = container.querySelector('.empty-state-action');
        if (actionBtn) {
            actionBtn.addEventListener('click', onAction);
        }
    }
}
