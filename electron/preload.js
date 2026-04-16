const { contextBridge, ipcRenderer } = require('electron');



// Expose safe APIs to the renderer process

contextBridge.exposeInMainWorld('electronAPI', {

    // Get API server URL

    getApiUrl: () => ipcRenderer.invoke('get-api-url'),



    // Get application path

    getAppPath: () => ipcRenderer.invoke('get-app-path'),



    // Read/write config.json under the working directory

    readConfigJson: () => ipcRenderer.invoke('read-config-json'),

    writeConfigJson: (patch) => ipcRenderer.invoke('write-config-json', patch),



    // File dialogs

    showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),

    showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),



    // Message dialog

    showMessageBox: (options) => ipcRenderer.invoke('show-message-box', options),



    // Set window title

    setTitle: (title) => ipcRenderer.send('set-title', title),



    // Window controls

    windowMinimize: () => ipcRenderer.send('window-minimize'),

    windowMaximize: () => ipcRenderer.send('window-maximize'),

    windowClose: () => ipcRenderer.send('window-close'),

    windowIsMaximized: () => ipcRenderer.invoke('window-is-maximized'),



    // Minimize to tray

    minimizeToTray: () => ipcRenderer.send('minimize-to-tray'),



    // Quit the app

    quitApp: () => ipcRenderer.send('quit-app'),



    // Fix input focus issue

    fixInputFocus: () => ipcRenderer.send('fix-input-focus'),



    // Listen for menu actions

    onMenuAction: (callback) => {

        ipcRenderer.on('menu-action', (event, action) => callback(action));

    },



    // Listen for navigation events

    onNavigate: (callback) => {

        ipcRenderer.on('navigate', (event, page) => callback(page));

    },



    // Remove listeners

    removeAllListeners: (channel) => {

        ipcRenderer.removeAllListeners(channel);

    },



    // BrowserView controls

    loadUrlInBrowserView: (url) => ipcRenderer.invoke('load-url-in-browserview', url),

    closeBrowserView: () => ipcRenderer.send('close-browserview'),

    hideBrowserView: () => ipcRenderer.send('hide-browserview'),

    showBrowserView: () => ipcRenderer.send('show-browserview'),

    onBrowserViewLoadFailed: (callback) => {

        ipcRenderer.on('browserview-load-failed', (event, payload) => callback(payload));

    },

    getBrowserViewBounds: () => ipcRenderer.invoke('get-browserview-bounds'),

    updateBrowserViewBounds: (collapsed) => ipcRenderer.send('update-browserview-bounds', collapsed),



    // AI chat streaming output

    chatStreamStart: (messages, requestId) => {

        ipcRenderer.send('chat-stream-start', { messages, requestId });

    },

    onChatStreamData: (callback) => {

        ipcRenderer.on('chat-stream-data', (event, data) => callback(data));

    },

    onChatStreamEnd: (callback) => {

        ipcRenderer.on('chat-stream-end', (event, data) => callback(data));

    },

    onChatStreamError: (callback) => {

        ipcRenderer.on('chat-stream-error', (event, data) => callback(data));

    },

    removeChatStreamListeners: () => {

        ipcRenderer.removeAllListeners('chat-stream-data');

        ipcRenderer.removeAllListeners('chat-stream-end');

        ipcRenderer.removeAllListeners('chat-stream-error');

    },



    // Map window features

    openMapWindow: () => ipcRenderer.send('open-map-window'),

    closeMapWindow: () => ipcRenderer.send('close-map-window'),

    maximizeMapWindow: () => ipcRenderer.send('maximize-map-window'),

    minimizeMapWindow: () => ipcRenderer.send('minimize-map-window'),



    // Map operations

    sendMapCommand: (command, param1, param2) => {

        ipcRenderer.send('map-command', { command, param1, param2 });

    },

    onMapCommand: (callback) => {

        ipcRenderer.on('map-command', (event, data) => callback(data));

    },



    // Map chat

    sendMapChatMessage: (from, to, msg) => {

        ipcRenderer.send('map-chat-message', { from, to, msg });

    },

    onMapChatMessage: (callback) => {

        ipcRenderer.on('map-chat-message', (event, data) => callback(data));

    },



    // Open URL

    openUrl: (url) => ipcRenderer.send('open-url', url),



    writeClipboardText: (text) => ipcRenderer.invoke('write-clipboard-text', text),



    openPath: (filePath) => ipcRenderer.invoke('open-path', filePath),



    downloadAndOpen: (url, filename) => ipcRenderer.invoke('download-and-open', { url, filename }),

    readSnsHumanInputHistory: (mode) => ipcRenderer.invoke('read-sns-human-input-history', { mode }),

    writeSnsHumanInputHistory: (mode, lines) => ipcRenderer.invoke('write-sns-human-input-history', { mode, lines }),

    readAgentChatInputHistory: (agentId) => ipcRenderer.invoke('read-agent-chat-input-history', { agentId }),

    writeAgentChatInputHistory: (agentId, lines) => ipcRenderer.invoke('write-agent-chat-input-history', { agentId, lines })

});



// Expose platform info

contextBridge.exposeInMainWorld('platform', {

    isWindows: process.platform === 'win32',

    isMac: process.platform === 'darwin',

    isLinux: process.platform === 'linux',

    platform: process.platform

});

