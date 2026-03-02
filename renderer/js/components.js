/**
 * AI-SNS UI Components
 * Reusable UI components
 */

// ==================== Override native alert/confirm/prompt ====================
// Prevent native dialogs from breaking focus state in Electron frameless window

(function() {
    const originalAlert = window.alert;
    const originalConfirm = window.confirm;
    const originalPrompt = window.prompt;

    // Override alert - use console.warn and Notification instead
    window.alert = function(message) {
        console.warn('[Alert]', message);
        try {
            if (typeof window !== 'undefined' && window.Toast && typeof window.Toast.warning === 'function') {
                window.Toast.warning(String(message));
            } else if (typeof Notification !== 'undefined' && Notification.warning) {
                Notification.warning(String(message));
            }
        } catch (e) {
        }
        // Restore focus
        setTimeout(() => {
            window.focus();
            document.body.focus();
        }, 10);
    };

    // Override confirm - always return true to avoid blocking
    window.confirm = function(message) {
        console.warn('[Confirm]', message);
        return true;
    };

    // Override prompt - return empty string to avoid blocking
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
        this.onOpen = options.onOpen || null;
        this.onClose = options.onClose || null;
        this.confirmText = options.confirmText || 'Confirm';
        this.cancelText = options.cancelText || 'Cancel';
        this.showCancel = options.showCancel !== false;
        this.closeOnClickOutside = options.closeOnClickOutside !== false;
        this.width = options.width || '500px';
        this.element = null;
    }

    render() {
        const html = `
            <div class="modal-overlay">
                <div class="modal" style="max-width: ${this.width};">
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

        // Call onOpen callback after rendering completes
        if (this.onOpen) {
            this.onOpen(this);
        }

        return this;
    }

    bindEvents() {
        this.element.addEventListener('click', async (e) => {
            const action = e.target.dataset.action;

            if (action === 'close') {
                this.close();
                return;
            }

            if (action === 'cancel') {
                if (this.onCancel) {
                    try {
                        const result = await this.onCancel(this);
                        if (result !== false) {
                            this.close();
                        }
                    } catch (error) {
                        console.error('[Modal] Error in onCancel:', error);
                    }
                } else {
                    this.close();
                }
                return;
            }

            if (action === 'confirm') {
                if (this.onConfirm) {
                    try {
                        const result = await this.onConfirm(this);
                        if (result !== false) {
                            this.close();
                        }
                    } catch (error) {
                        console.error('[Modal] Error in onConfirm:', error);
                    }
                } else {
                    this.close();
                }
            }
        });

        // Click overlay to close
        if (this.closeOnClickOutside) {
            this.element.addEventListener('click', async (e) => {
                if (e.target === this.element) {
                    if (this.onCancel) {
                        try {
                            const result = await this.onCancel(this);
                            if (result !== false) {
                                this.close();
                            }
                        } catch (error) {
                            console.error('[Modal] Error in onCancel:', error);
                        }
                    } else {
                        this.close();
                    }
                }
            });
        }

        // Close on ESC key
        document.addEventListener('keydown', this.handleKeydown = async (e) => {
            if (e.key === 'Escape') {
                if (this.onCancel) {
                    try {
                        const result = await this.onCancel(this);
                        if (result !== false) {
                            this.close();
                        }
                    } catch (error) {
                        console.error('[Modal] Error in onCancel:', error);
                    }
                } else {
                    this.close();
                }
            }
        });
    }

    close() {
        if (this.element) {
            this.element.remove();
            document.removeEventListener('keydown', this.handleKeydown);
            if (this.onClose) {
                this.onClose();
            }
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
            title: 'Confirm',
            content: `<p>${message}</p>`,
            onConfirm
        });
    }

    static alert(message, title = 'Notice') {
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
        try {
            if (typeof window !== 'undefined' && window.Toast && typeof window.Toast.show === 'function') {
                return window.Toast.show(String(message), type, duration);
            }
        } catch (e) {
        }

        if (!this.container) this.init();

        const notification = document.createElement('div');
        notification.className = `notification ${type}`;
        notification.innerHTML = `
            <span class="notification-message">${message}</span>
            <button class="notification-close">&times;</button>
        `;

        this.container.appendChild(notification);

        // Bind close button
        notification.querySelector('.notification-close').addEventListener('click', () => {
            this.remove(notification);
        });

        // Auto remove
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

    // Bind action button events
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
        return 'Just now';
    } else if (diff < 3600000) {
        return `${Math.floor(diff / 60000)} minutes ago`;
    } else if (diff < 86400000) {
        return `${Math.floor(diff / 3600000)} hours ago`;
    } else {
        return date.toLocaleDateString('zh-CN');
    }
}

function getStatusText(status) {
    const statusTexts = {
        'available': 'Online',
        'chat': 'Chatting',
        'away': 'Away',
        'xa': 'Extended away',
        'dnd': 'Do not disturb',
        'offline': 'Offline'
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
        title = 'No data',
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
