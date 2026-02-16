const { contextBridge, ipcRenderer } = require('electron');



// 暴露安全的API到渲染进程

contextBridge.exposeInMainWorld('electronAPI', {

    // 获取API服务器URL

    getApiUrl: () => ipcRenderer.invoke('get-api-url'),



    // 获取应用路径

    getAppPath: () => ipcRenderer.invoke('get-app-path'),



    // 读取/写入工作目录下的 config.json

    readConfigJson: () => ipcRenderer.invoke('read-config-json'),

    writeConfigJson: (patch) => ipcRenderer.invoke('write-config-json', patch),



    // 文件对话框

    showOpenDialog: (options) => ipcRenderer.invoke('show-open-dialog', options),

    showSaveDialog: (options) => ipcRenderer.invoke('show-save-dialog', options),



    // 消息对话框

    showMessageBox: (options) => ipcRenderer.invoke('show-message-box', options),



    // 设置窗口标题

    setTitle: (title) => ipcRenderer.send('set-title', title),



    // 窗口控制

    windowMinimize: () => ipcRenderer.send('window-minimize'),

    windowMaximize: () => ipcRenderer.send('window-maximize'),

    windowClose: () => ipcRenderer.send('window-close'),

    windowIsMaximized: () => ipcRenderer.invoke('window-is-maximized'),



    // 最小化到托盘

    minimizeToTray: () => ipcRenderer.send('minimize-to-tray'),



    // 退出应用

    quitApp: () => ipcRenderer.send('quit-app'),



    // 修复输入框焦点问题

    fixInputFocus: () => ipcRenderer.send('fix-input-focus'),



    // 监听菜单操作

    onMenuAction: (callback) => {

        ipcRenderer.on('menu-action', (event, action) => callback(action));

    },



    // 监听导航事件

    onNavigate: (callback) => {

        ipcRenderer.on('navigate', (event, page) => callback(page));

    },



    // 移除监听器

    removeAllListeners: (channel) => {

        ipcRenderer.removeAllListeners(channel);

    },



    // BrowserView 控制

    loadUrlInBrowserView: (url) => ipcRenderer.invoke('load-url-in-browserview', url),

    closeBrowserView: () => ipcRenderer.send('close-browserview'),

    hideBrowserView: () => ipcRenderer.send('hide-browserview'),

    showBrowserView: () => ipcRenderer.send('show-browserview'),

    onBrowserViewLoadFailed: (callback) => {

        ipcRenderer.on('browserview-load-failed', (event, payload) => callback(payload));

    },

    getBrowserViewBounds: () => ipcRenderer.invoke('get-browserview-bounds'),

    updateBrowserViewBounds: (collapsed) => ipcRenderer.send('update-browserview-bounds', collapsed),



    // AI 聊天流式输出

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



    // 地图窗口功能

    openMapWindow: () => ipcRenderer.send('open-map-window'),

    closeMapWindow: () => ipcRenderer.send('close-map-window'),

    maximizeMapWindow: () => ipcRenderer.send('maximize-map-window'),

    minimizeMapWindow: () => ipcRenderer.send('minimize-map-window'),



    // 地图操作

    sendMapCommand: (command, param1, param2) => {

        ipcRenderer.send('map-command', { command, param1, param2 });

    },

    onMapCommand: (callback) => {

        ipcRenderer.on('map-command', (event, data) => callback(data));

    },



    // 地图配置

    loadMapSetting: () => ipcRenderer.invoke('load-map-setting'),

    saveMapSetting: (setting) => ipcRenderer.invoke('save-map-setting', setting),



    // 地图聊天

    sendMapChatMessage: (from, to, msg) => {

        ipcRenderer.send('map-chat-message', { from, to, msg });

    },

    onMapChatMessage: (callback) => {

        ipcRenderer.on('map-chat-message', (event, data) => callback(data));

    },



    // 打开链接

    openUrl: (url) => ipcRenderer.send('open-url', url),



    writeClipboardText: (text) => ipcRenderer.invoke('write-clipboard-text', text),



    openPath: (filePath) => ipcRenderer.invoke('open-path', filePath),



    downloadAndOpen: (url, filename) => ipcRenderer.invoke('download-and-open', { url, filename })

});



// 暴露平台信息

contextBridge.exposeInMainWorld('platform', {

    isWindows: process.platform === 'win32',

    isMac: process.platform === 'darwin',

    isLinux: process.platform === 'linux',

    platform: process.platform

});

