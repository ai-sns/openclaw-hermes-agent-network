const { app, BrowserWindow, BrowserView, ipcMain, Menu, Tray, dialog, shell, clipboard, globalShortcut, session, nativeImage } = require('electron');

const path = require('path');

const { spawn } = require('child_process');

const fs = require('fs');

const fsp = require('fs/promises');

const http = require('http');

const https = require('https');



// Windows 10 + frameless window: disable GPU hardware acceleration (optional, enable as needed)

// app.disableHardwareAcceleration();



let mainWindow = null;

let mapWindow = null;

let browserView = null;



// Azure OpenAI config has been moved to the backend API Server (api_server.py)

// Config is loaded from the database or environment variables

// const AZURE_OPENAI_CONFIG = {

//     baseUrl: 'https://api.chatanywhere.tech/v1',

//     apiKey: 'sk-SVCuk9EAqrgUEvvh31PKxVIr1fZhwt5boDB2Hexw8vs2Bl26',

//     model: 'gpt-4o-mini'

// };

let tray = null;

let pythonProcess = null;

let isQuitting = false;

function _createMenuItemIcon({ fallbackPngPath, size = 16 }) {
    try {
        const img = nativeImage.createFromPath(path.join(__dirname, fallbackPngPath));
        if (img && !img.isEmpty()) {
            return img.resize({ width: size, height: size });
        }
    } catch (e) {
    }
    return undefined;
}

function isAudioOnlyMediaRequest(details) {
    const types = (details && Array.isArray(details.mediaTypes)) ? details.mediaTypes : [];
    const hasAudio = types.includes('audio');
    const hasVideo = types.includes('video');
    return hasAudio && !hasVideo;
}

function setupMediaPermissions() {
    const s = session && session.defaultSession;
    if (!s || typeof s.setPermissionRequestHandler !== 'function') return;

    s.setPermissionRequestHandler((webContents, permission, callback, details) => {
        // Allow microphone for ALL websites, but deny camera/video by default.
        if (permission === 'media' && isAudioOnlyMediaRequest(details)) {
            callback(true);
            return;
        }
        callback(false);
    });

    if (typeof s.setPermissionCheckHandler === 'function') {
        s.setPermissionCheckHandler((webContents, permission, requestingOrigin, details) => {
            if (permission !== 'media') return false;
            return isAudioOnlyMediaRequest(details);
        });
    }
}


function _readConfigJsonSyncSafe() {
    try {
        const configPath = path.join(process.cwd(), 'config.json');
        if (!fs.existsSync(configPath)) return {};
        const raw = fs.readFileSync(configPath, 'utf-8');
        const parsed = JSON.parse(raw);
        return (parsed && typeof parsed === 'object') ? parsed : {};
    } catch (e) {
        return {};
    }
}


function _cleanupOldBackendLogsOnExit() {
    try {
        const cfg = _readConfigJsonSyncSafe();
        const raw = (cfg && cfg.log_retention_days !== undefined && cfg.log_retention_days !== null)
            ? String(cfg.log_retention_days).trim()
            : '';
        if (!raw) {
            return;
        }

        const days = parseInt(raw, 10);
        if (!Number.isFinite(days) || days < 0) {
            return;
        }

        const logsRoot = path.join(process.cwd(), 'backend', 'logs');
        if (!fs.existsSync(logsRoot)) return;

        const entries = fs.readdirSync(logsRoot, { withFileTypes: true });
        const now = new Date();
        const msPerDay = 24 * 60 * 60 * 1000;
        const cutoffMs = now.getTime() - (days * msPerDay);

        for (const ent of entries) {
            if (!ent.isDirectory()) continue;
            const name = ent.name;
            if (!/^\d{4}-\d{2}-\d{2}$/.test(name)) continue;

            const folderDate = new Date(`${name}T00:00:00`);
            const t = folderDate.getTime();
            if (!Number.isFinite(t)) continue;
            if (t >= cutoffMs) continue;

            const fullPath = path.join(logsRoot, name);
            try {
                fs.rmSync(fullPath, { recursive: true, force: true });
            } catch (e) {
            }
        }
    } catch (e) {
    }
}

ipcMain.handle('write-clipboard-text', async (event, text) => {

    try {

        const v = (text === undefined || text === null) ? '' : String(text);

        clipboard.writeText(v);

        return { success: true };

    } catch (e) {

        return { success: false, error: e && e.message ? e.message : String(e) };

    }

});



ipcMain.handle('read-sns-human-input-history', async (event, payload) => {

    try {

        const modeRaw = payload && payload.mode ? String(payload.mode).trim() : '';
        const mode = (modeRaw === 'ai') ? 'ai' : ((modeRaw === 'friends' || modeRaw === 'target') ? 'target' : '');
        if (!mode) {
            return { success: false, error: 'Invalid mode' };
        }

        const filePath = path.join(app.getPath('userData'), `sns_human_input_history_${mode}.txt`);

        try {
            const raw = await fsp.readFile(filePath, 'utf-8');
            return { success: true, data: raw };
        } catch (e) {
            if (e && (e.code === 'ENOENT' || e.code === 'ENOTDIR')) {
                return { success: true, data: '' };
            }
            throw e;
        }

    } catch (e) {

        return { success: false, error: e && e.message ? e.message : String(e) };

    }

});



ipcMain.handle('write-sns-human-input-history', async (event, payload) => {

    try {

        const modeRaw = payload && payload.mode ? String(payload.mode).trim() : '';
        const mode = (modeRaw === 'ai') ? 'ai' : ((modeRaw === 'friends' || modeRaw === 'target') ? 'target' : '');
        if (!mode) {
            return { success: false, error: 'Invalid mode' };
        }

        const inputLines = payload && Array.isArray(payload.lines) ? payload.lines : [];
        const normalized = inputLines
            .map(v => (v === undefined || v === null) ? '' : String(v).trim())
            .filter(v => !!v);

        const maxEntries = 30;
        const trimmed = normalized.length > maxEntries
            ? normalized.slice(normalized.length - maxEntries)
            : normalized;

        const filePath = path.join(app.getPath('userData'), `sns_human_input_history_${mode}.txt`);
        await fsp.writeFile(filePath, trimmed.join('\n'), 'utf-8');

        return { success: true };

    } catch (e) {

        return { success: false, error: e && e.message ? e.message : String(e) };

    }

});



ipcMain.handle('read-agent-chat-input-history', async (event, payload) => {

    try {

        const agentIdRaw = payload && payload.agentId !== undefined && payload.agentId !== null
            ? String(payload.agentId).trim()
            : '';
        const agentId = parseInt(agentIdRaw, 10);
        if (!Number.isFinite(agentId) || agentId <= 0) {
            return { success: false, error: 'Invalid agentId' };
        }

        const filePath = path.join(app.getPath('userData'), `agent_chat_input_history_${agentId}.txt`);

        try {
            const raw = await fsp.readFile(filePath, 'utf-8');
            return { success: true, data: raw };
        } catch (e) {
            if (e && (e.code === 'ENOENT' || e.code === 'ENOTDIR')) {
                return { success: true, data: '' };
            }
            throw e;
        }

    } catch (e) {

        return { success: false, error: e && e.message ? e.message : String(e) };

    }

});



ipcMain.handle('write-agent-chat-input-history', async (event, payload) => {

    try {

        const agentIdRaw = payload && payload.agentId !== undefined && payload.agentId !== null
            ? String(payload.agentId).trim()
            : '';
        const agentId = parseInt(agentIdRaw, 10);
        if (!Number.isFinite(agentId) || agentId <= 0) {
            return { success: false, error: 'Invalid agentId' };
        }

        const inputLines = payload && Array.isArray(payload.lines) ? payload.lines : [];
        const normalized = inputLines
            .map(v => (v === undefined || v === null) ? '' : String(v).trim())
            .filter(v => !!v);

        const maxEntries = 30;
        const trimmed = normalized.length > maxEntries
            ? normalized.slice(normalized.length - maxEntries)
            : normalized;

        const filePath = path.join(app.getPath('userData'), `agent_chat_input_history_${agentId}.txt`);
        await fsp.writeFile(filePath, trimmed.join('\n'), 'utf-8');

        return { success: true };

    } catch (e) {

        return { success: false, error: e && e.message ? e.message : String(e) };

    }

});

ipcMain.handle('open-path', async (event, filePath) => {

    try {

        if (!filePath) {

            return 'Empty path';

        }

        const result = await shell.openPath(filePath);

        return result;

    } catch (e) {

        return String(e);

    }

});



ipcMain.handle('download-and-open', async (event, payload) => {

    try {

        const url = payload && payload.url;

        const filename = (payload && payload.filename) ? String(payload.filename) : 'file';

        if (!url) {

            return 'Empty url';

        }



        console.log('[download-and-open] start', { url, filename });



        const tempRoot = app.getPath('temp');

        const dir = path.join(tempRoot, 'ai-sns-attachments');

        await fsp.mkdir(dir, { recursive: true });



        const safeName = path.basename(filename);

        const targetPath = path.join(dir, `${Date.now()}_${Math.random().toString(16).slice(2)}_${safeName}`);



        await new Promise((resolve, reject) => {

            const mod = String(url).startsWith('https') ? https : http;

            const req = mod.get(url, (res) => {

                console.log('[download-and-open] http status', res.statusCode);

                if (res.statusCode && res.statusCode >= 400) {

                    reject(new Error(`HTTP ${res.statusCode}`));

                    return;

                }

                const stream = fs.createWriteStream(targetPath);

                res.pipe(stream);

                stream.on('finish', () => stream.close(resolve));

                stream.on('error', reject);

            });

            req.on('error', reject);

        });



        console.log('[download-and-open] saved', { targetPath });



        const result = await shell.openPath(targetPath);

        console.log('[download-and-open] openPath result', result);

        return result;

    } catch (e) {

        console.error('[download-and-open] failed', e);

        return String(e);

    }

});



function toggleDevToolsForFocused() {

    const win = BrowserWindow.getFocusedWindow();

    if (!win) return;



    if (browserView && win === mainWindow && browserView.webContents && browserView.webContents.isFocused()) {

        browserView.webContents.toggleDevTools();

        return;

    }



    win.webContents.toggleDevTools();

}



function registerDevToolsHotkeysForWebContents(webContents) {

    if (!webContents) return;

    webContents.on('before-input-event', (event, input) => {

        if (input.type === 'keyDown' && input.key === 'F12') {

            event.preventDefault();

            webContents.toggleDevTools();

        }

    });

}



// API server configuration

const DEFAULT_API_BASE_URL = '';
let API_BASE_URL = DEFAULT_API_BASE_URL;

function normalizeHttpUrl(raw) {

    const v = String(raw || '').trim();
    if (!v) return '';

    const withScheme = /^https?:\/\//i.test(v) ? v : `http://${v}`;
    return withScheme.endsWith('/') ? withScheme.slice(0, -1) : withScheme;

}

function loadConfigJsonSync() {

    try {

        const configPath = path.join(process.cwd(), 'config.json');
        if (!fs.existsSync(configPath)) {
            return {};
        }

        const raw = fs.readFileSync(configPath, 'utf-8');
        const parsed = JSON.parse(raw);
        return (parsed && typeof parsed === 'object') ? parsed : {};

    } catch (e) {

        return {};

    }

}

function refreshApiBaseUrlFromConfigSync() {

    const cfg = loadConfigJsonSync();
    const agentServer = normalizeHttpUrl(cfg.agent_server);
    API_BASE_URL = agentServer || DEFAULT_API_BASE_URL;

    return { cfg, apiBaseUrl: API_BASE_URL };

}

refreshApiBaseUrlFromConfigSync();



// Development mode detection

const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';



function createWindow() {

    mainWindow = new BrowserWindow({

        width: 1400,

        height: 900,

        minWidth: 1000,

        minHeight: 700,

        icon: path.join(__dirname, '../images/aisnsiconv2.png'),

        webPreferences: {

            nodeIntegration: false,

            contextIsolation: true,

            preload: path.join(__dirname, 'preload.js'),

            webSecurity: false,  // Disable cross-origin security policy to allow loading local server maps

            webviewTag: true,  // Enable the webview tag

            // Ensure input elements are usable

            enableBlinkFeatures: 'KeyboardFocusableScrollers'

        },

        // Frameless window with a custom title bar

        frame: false,

        // macOS-specific settings

        trafficLightPosition: { x: 16, y: 16 },

        // Enable window transparency effects

        transparent: false,

        backgroundColor: '#f5f5f5',

        // Enable window shadow

        hasShadow: true,

        show: false,

        // Windows focus fix

        skipTaskbar: false,

        focusable: true

    });



    // Intercept response headers and remove security headers that block iframe embedding

    mainWindow.webContents.session.webRequest.onHeadersReceived((details, callback) => {

        const responseHeaders = { ...details.responseHeaders };



        // Remove the X-Frame-Options header

        delete responseHeaders['x-frame-options'];

        delete responseHeaders['X-Frame-Options'];



        // Update the Content-Security-Policy header to remove the frame-ancestors restriction

        if (responseHeaders['content-security-policy']) {

            responseHeaders['content-security-policy'] = responseHeaders['content-security-policy'].map(

                value => value.replace(/frame-ancestors[^;]*(;|$)/gi, '')

            );

        }

        if (responseHeaders['Content-Security-Policy']) {

            responseHeaders['Content-Security-Policy'] = responseHeaders['Content-Security-Policy'].map(

                value => value.replace(/frame-ancestors[^;]*(;|$)/gi, '')

            );

        }



        callback({ responseHeaders });

    });



    // Remove application menu

    Menu.setApplicationMenu(null);



    registerDevToolsHotkeysForWebContents(mainWindow.webContents);



    // Load the main page

    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));



    // Show window after it is ready

    mainWindow.once('ready-to-show', () => {

        mainWindow.show();

        mainWindow.focus();

        mainWindow.webContents.focus();



        if (isDev) {

            console.log('Development mode: opening DevTools');

            mainWindow.webContents.openDevTools({

                mode: 'right' // Open DevTools on the right side

            });

        }

    });



    // Window close handler (minimize to tray)

    mainWindow.on('close', (event) => {

        if (!isQuitting) {

            event.preventDefault();

            mainWindow.hide();

            if (tray) {

                tray.displayBalloon({

                    title: 'AI-SNS',

                    content: 'The app has been minimized to the tray. Click the tray icon to restore the window.'

                });

            }

        }

    });



    mainWindow.on('closed', () => {

        mainWindow = null;

    });

}



async function createMapWindow() {

    mapWindow = new BrowserWindow({

        width: 1200,

        height: 800,

        minWidth: 800,

        minHeight: 600,

        icon: path.join(__dirname, '../images/aisnsiconv2.png'),

        webPreferences: {

            nodeIntegration: false,

            contextIsolation: true,

            preload: path.join(__dirname, 'preload.js'),

            webSecurity: true

        },

        frame: true,

        backgroundColor: '#f5f5f5',

        show: false

    });



    // Fetch map configuration and load the corresponding map page

    try {

        const { cfg, apiBaseUrl } = refreshApiBaseUrlFromConfigSync();
        const aiSnsServer = normalizeHttpUrl(cfg.ai_sns_server);

        const buildMapUrlByType = (mapType) => {
            const t = String(mapType || '').trim();
            const qs = new URLSearchParams();
            qs.set('agent_server', apiBaseUrl);
            if (aiSnsServer) {
                qs.set('ai_sns_server', aiSnsServer);
            }
            if (t === '0') {
                return `${apiBaseUrl}/scripts/googlemap3d.html?${qs.toString()}`;
            }
            return `${apiBaseUrl}/scripts/map.html?${qs.toString()}`;
        };

        let cachedMapType = '';
        try {
            cachedMapType = String(cfg.map_type || '').trim();
        } catch (e) {
        }

        // Start loading immediately (do not block on map-config)
        let mapUrl = buildMapUrlByType(cachedMapType);
        console.log('Initial map URL (non-blocking):', mapUrl);
        mapWindow.loadURL(mapUrl);

        // Fetch config asynchronously and switch if needed
        Promise.resolve().then(async () => {
            try {
                const controller = (typeof AbortController !== 'undefined') ? new AbortController() : null;
                const timeoutMs = 1200;
                let timeoutId = null;
                if (controller) {
                    timeoutId = setTimeout(() => {
                        try {
                            controller.abort();
                        } catch (e) {
                        }
                    }, timeoutMs);
                }

                const response = await fetch(
                    `${apiBaseUrl}/api/sns/map-config`,
                    controller ? { signal: controller.signal } : undefined
                );
                if (timeoutId) {
                    clearTimeout(timeoutId);
                }
                const result = await response.json();

                console.log('Map config API response:', JSON.stringify(result, null, 2));

                if (result && result.success && result.data) {
                    const mapType = String(result.data.map_type).trim();
                    const desiredUrl = buildMapUrlByType(mapType);
                    if (desiredUrl && desiredUrl !== mapUrl) {
                        console.log('Switching map URL after config fetch:', desiredUrl);
                        mapUrl = desiredUrl;
                        try {
                            if (mapWindow && !mapWindow.isDestroyed()) {
                                mapWindow.loadURL(mapUrl);
                            }
                        } catch (e) {
                        }
                    }
                }
            } catch (error) {
                console.warn('Failed to fetch map config (non-blocking):', error);
            }
        });

    } catch (error) {

        console.error('Failed to fetch map config:', error);

        // Use the default map on error

        const { cfg, apiBaseUrl } = refreshApiBaseUrlFromConfigSync();
        const aiSnsServer = normalizeHttpUrl(cfg.ai_sns_server);
        const qs = new URLSearchParams();
        qs.set('agent_server', apiBaseUrl);
        if (aiSnsServer) {
            qs.set('ai_sns_server', aiSnsServer);
        }
        mapWindow.loadURL(`${apiBaseUrl}/scripts/map.html?${qs.toString()}`);

    }



    // Show window after it is ready

    mapWindow.once('ready-to-show', () => {

        mapWindow.show();

        mapWindow.focus();



        if (isDev) {

            mapWindow.webContents.openDevTools();

        }

    });



    mapWindow.on('closed', () => {

        mapWindow = null;

    });

}

function createTray() {

    const iconPath = path.join(__dirname, '../images/aisnsiconv2.png');

    tray = new Tray(iconPath);

    const trayMenuIcons = {
        show: _createMenuItemIcon({
            fallbackPngPath: '../images/application.png'
        }),
        hide: _createMenuItemIcon({
            fallbackPngPath: '../images/hide.png'
        }),
        exit: _createMenuItemIcon({
            fallbackPngPath: '../images/exit.png'
        })
    };



    const contextMenu = Menu.buildFromTemplate([

        {

            label: 'Show',

            icon: trayMenuIcons.show,

            click: () => {

                if (mainWindow) {

                    mainWindow.show();

                    mainWindow.focus();

                }

            }

        },

        {

            label: 'Hide',

            icon: trayMenuIcons.hide,

            click: () => {

                if (mainWindow) {

                    mainWindow.hide();

                }

            }

        },

        { type: 'separator' },

        {

            label: 'Exit',

            icon: trayMenuIcons.exit,

            click: () => {

                isQuitting = true;

                app.quit();

            }

        }

    ]);



    tray.setToolTip('AI-SNS - AI Agent Social Network');

    tray.setContextMenu(contextMenu);



    tray.on('click', () => {

        if (mainWindow) {

            if (mainWindow.isVisible()) {

                mainWindow.hide();

            } else {

                mainWindow.show();

                mainWindow.focus();

            }

        }

    });

}



// IPC handlers

ipcMain.handle('get-api-url', () => {

    refreshApiBaseUrlFromConfigSync();
    return API_BASE_URL;

});



ipcMain.handle('get-app-path', () => {

    return app.getAppPath();

});



ipcMain.handle('read-config-json', async () => {

    try {

        const configPath = path.join(process.cwd(), 'config.json');

        try {

            const raw = await fsp.readFile(configPath, 'utf-8');

            const parsed = JSON.parse(raw);

            return { success: true, data: (parsed && typeof parsed === 'object') ? parsed : {} };

        } catch (e) {

            if (e && (e.code === 'ENOENT' || e.code === 'ENOTDIR')) {

                return { success: true, data: {} };

            }

            throw e;

        }

    } catch (e) {

        return { success: false, error: e && e.message ? e.message : String(e) };

    }

});



ipcMain.handle('write-config-json', async (event, patch) => {

    try {

        const configPath = path.join(process.cwd(), 'config.json');

        const allowedKeys = new Set(['agent_server', 'ai_sns_server', 'log_retention_days']);

        const input = (patch && typeof patch === 'object') ? patch : {};

        const filtered = {};

        for (const [k, v] of Object.entries(input)) {

            if (!allowedKeys.has(k)) continue;

            filtered[k] = (v === undefined || v === null) ? '' : String(v);

        }

        let existing = {};

        try {

            const raw = await fsp.readFile(configPath, 'utf-8');

            const parsed = JSON.parse(raw);

            existing = (parsed && typeof parsed === 'object') ? parsed : {};

        } catch (e) {

            if (!(e && (e.code === 'ENOENT' || e.code === 'ENOTDIR'))) {

                throw e;

            }

        }

        const next = { ...existing, ...filtered };

        await fsp.writeFile(configPath, JSON.stringify(next, null, 2), 'utf-8');

        return { success: true };

    } catch (e) {

        return { success: false, error: e && e.message ? e.message : String(e) };

    }

});



ipcMain.handle('show-open-dialog', async (event, options) => {

    const result = await dialog.showOpenDialog(mainWindow, options);

    return result;

});



ipcMain.handle('show-save-dialog', async (event, options) => {

    const result = await dialog.showSaveDialog(mainWindow, options);

    return result;

});



ipcMain.handle('show-message-box', async (event, options) => {

    const result = await dialog.showMessageBox(mainWindow, options);

    return result;

});



ipcMain.on('set-title', (event, title) => {

    if (mainWindow) {

        mainWindow.setTitle(title);

    }

});



// Map window control IPC

ipcMain.on('open-map-window', () => {

    createMapWindow().catch(err => console.error('Error creating map window:', err));

});



ipcMain.on('close-map-window', () => {

    if (mapWindow) {

        mapWindow.close();

    }

});



ipcMain.on('maximize-map-window', () => {

    if (mapWindow) {

        if (mapWindow.isMaximized()) {

            mapWindow.unmaximize();

        } else {

            mapWindow.maximize();

        }

    }

});



ipcMain.on('minimize-map-window', () => {

    if (mapWindow) {

        mapWindow.minimize();

    }

});



// Map operation IPC

ipcMain.on('map-command', (event, data) => {

    if (mapWindow) {

        mapWindow.webContents.send('map-command', data);

    }

});



// Map configuration IPC

ipcMain.handle('load-map-setting', async () => {

    // TODO: Load map settings from a config file or database

    return {

        mapType: 'baidu',

        center: { lng: 116.3974, lat: 39.9093 },

        zoom: 13,

        homePosition: null,

        route: null

    };

});



ipcMain.handle('save-map-setting', async (event, setting) => {

    // TODO: Save map settings to a config file or database

    console.log('Saving map setting:', setting);

    return true;

});



// Map chat IPC

ipcMain.on('map-chat-message', (event, data) => {

    if (mapWindow) {

        mapWindow.webContents.send('map-chat-message', data);

    }

});



// Open URL IPC

ipcMain.on('open-url', (event, url) => {

    shell.openExternal(url);

});



// Window control IPC

ipcMain.on('window-minimize', () => {

    if (mainWindow) {

        mainWindow.minimize();

    }

});



ipcMain.on('window-maximize', () => {

    if (mainWindow) {

        if (mainWindow.isMaximized()) {

            mainWindow.unmaximize();

        } else {

            mainWindow.maximize();

        }

    }

});



ipcMain.on('window-close', () => {

    if (mainWindow) {

        mainWindow.close();

    }

});



ipcMain.handle('window-is-maximized', () => {

    return mainWindow ? mainWindow.isMaximized() : false;

});



ipcMain.on('minimize-to-tray', () => {

    if (mainWindow) {

        mainWindow.hide();

    }

});



ipcMain.on('quit-app', () => {

    isQuitting = true;

    app.quit();

});



// Fix input focus issues for Windows 10 frameless windows

ipcMain.on('fix-input-focus', () => {

    if (mainWindow) {

        // Simulate minimize and restore to force Windows focus events

        mainWindow.minimize();

        setTimeout(() => {

            mainWindow.restore();

            mainWindow.focus();

            mainWindow.webContents.focus();

        }, 50);

    }

});



// Azure OpenAI streaming chat (via the backend API Server)

ipcMain.on('chat-stream-start', async (event, { messages, requestId }) => {

    try {

        const http = require('http');



        const requestBody = JSON.stringify({

            messages: messages,

            temperature: 1.0,

            max_tokens: 4096

        });



        console.log(`Sending chat request to backend: ${API_BASE_URL}/api/chat/stream`);



        const options = {

            hostname: API_HOST,

            port: API_PORT,

            path: '/api/chat/stream',

            method: 'POST',

            headers: {

                'Content-Type': 'application/json',

                'Accept': 'text/event-stream',

                'Content-Length': Buffer.byteLength(requestBody)

            }

        };



        const req = http.request(options, (res) => {

            let buffer = '';



            console.log(`Response status: ${res.statusCode}`);

            console.log(`Response headers:`, res.headers);



            // Check HTTP status code

            if (res.statusCode !== 200) {

                let errorBody = '';

                res.on('data', (chunk) => {

                    errorBody += chunk.toString();

                });

                res.on('end', () => {

                    console.error(`API Error Response: ${errorBody}`);

                    event.sender.send('chat-stream-error', {

                        requestId,

                        error: `HTTP ${res.statusCode}: ${errorBody}`

                    });

                });

                return;

            }



            // Handle SSE stream

            res.on('data', (chunk) => {

                const chunkStr = chunk.toString();

                buffer += chunkStr;



                // Process SSE data

                const lines = buffer.split('\n');

                buffer = lines.pop() || ''; // Keep the unfinished line



                for (const line of lines) {

                    const trimmedLine = line.trim();



                    // SSE format: event: message\ndata: {...}

                    if (trimmedLine.startsWith('event:')) {

                        // Skip the event line

                        continue;

                    }



                    if (trimmedLine.startsWith('data:')) {

                        const data = trimmedLine.slice(5).trim();



                        try {

                            const parsed = JSON.parse(data);



                            // Handle message content

                            if (parsed.content) {

                                console.log(`Stream content: ${parsed.content}`);

                                event.sender.send('chat-stream-data', { requestId, content: parsed.content });

                            }



                            // Handle completion state

                            if (parsed.status === 'completed') {

                                console.log('Stream completed');

                                event.sender.send('chat-stream-end', { requestId });

                                return;

                            }



                            // Handle errors

                            if (parsed.error) {

                                console.error(`Stream error: ${parsed.error}`);

                                event.sender.send('chat-stream-error', { requestId, error: parsed.error });

                                return;

                            }

                        } catch (e) {

                            console.log(`Parse error for line: ${trimmedLine}, error: ${e.message}`);

                        }

                    }

                }

            });



            res.on('end', () => {

                console.log('Stream connection closed');

                // Process the remaining buffer

                if (buffer.trim()) {

                    const lines = buffer.split('\n');

                    for (const line of lines) {

                        const trimmedLine = line.trim();

                        if (trimmedLine.startsWith('data:')) {

                            const data = trimmedLine.slice(5).trim();

                            try {

                                const parsed = JSON.parse(data);

                                if (parsed.content) {

                                    event.sender.send('chat-stream-data', { requestId, content: parsed.content });

                                }

                            } catch (e) {}

                        }

                    }

                }

                event.sender.send('chat-stream-end', { requestId });

            });



            res.on('error', (error) => {

                console.error(`Response error: ${error.message}`);

                event.sender.send('chat-stream-error', { requestId, error: error.message });

            });

        });



        req.on('error', (error) => {

            console.error(`Request error: ${error.message}`);

            event.sender.send('chat-stream-error', { requestId, error: error.message });

        });



        req.write(requestBody);

        req.end();



    } catch (error) {

        console.error(`Chat stream start error: ${error.message}`);

        event.sender.send('chat-stream-error', { requestId, error: error.message });

    }

});



// Windows focus fix: when the window gets focus, ensure webContents gets focus as well

app.on('browser-window-focus', () => {

    const win = BrowserWindow.getFocusedWindow();

    if (win) {

        win.webContents.focus();

    }

});



// BrowserView management

ipcMain.handle('load-url-in-browserview', async (event, url) => {

    if (!mainWindow) return;



    try {

        // If a BrowserView already exists, remove it first

        if (browserView) {

            mainWindow.removeBrowserView(browserView);

            browserView.webContents.destroy();

            browserView = null;

        }



        // Create a new BrowserView

        browserView = new BrowserView({

            webPreferences: {

                nodeIntegration: false,

                contextIsolation: true,

                webSecurity: true

            }

        });



        registerDevToolsHotkeysForWebContents(browserView.webContents);



        let loadFailedNotified = false;

        const cleanupBrowserView = () => {

            if (browserView && mainWindow) {

                try {

                    mainWindow.removeBrowserView(browserView);

                } catch (e) {

                }



                try {

                    browserView.webContents.destroy();

                } catch (e) {

                }



                browserView = null;

            }

        };



        const notifyLoadFailed = (payload) => {

            if (loadFailedNotified) return;

            loadFailedNotified = true;



            if (mainWindow && !mainWindow.isDestroyed()) {

                mainWindow.webContents.send('browserview-load-failed', payload);

            }

        };



        const handleLoadFailed = (payload) => {

            notifyLoadFailed(payload);

            cleanupBrowserView();

        };



        browserView.webContents.on('did-fail-provisional-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {

            if (!isMainFrame) return;

            handleLoadFailed({ url: validatedURL, errorCode, errorDescription });

        });



        browserView.webContents.on('did-fail-load', (event, errorCode, errorDescription, validatedURL, isMainFrame) => {

            if (!isMainFrame) return;

            handleLoadFailed({ url: validatedURL, errorCode, errorDescription });

        });



        browserView.webContents.on('render-process-gone', (event, details) => {

            handleLoadFailed({ url, errorCode: details && details.exitCode, errorDescription: details && details.reason });

        });



        browserView.webContents.on('context-menu', (event, params) => {

            if (!mainWindow || !browserView) return;



            const wc = browserView.webContents;

            const bounds = browserView.getBounds();

            const hasLink = !!params.linkURL;



            const template = [

                {

                    label: 'Back',

                    enabled: wc.canGoBack(),

                    click: () => wc.goBack()

                },

                {

                    label: 'Forward',

                    enabled: wc.canGoForward(),

                    click: () => wc.goForward()

                },

                {

                    label: 'Refresh',

                    click: () => wc.reload()

                },

                { type: 'separator' },

                {

                    role: 'cut',

                    enabled: params.editFlags && params.editFlags.canCut

                },

                {

                    role: 'copy',

                    enabled: params.editFlags && params.editFlags.canCopy

                },

                {

                    role: 'paste',

                    enabled: params.editFlags && params.editFlags.canPaste

                },

                {

                    role: 'selectAll',

                    enabled: params.editFlags && params.editFlags.canSelectAll

                },

                ...(hasLink

                    ? [

                          { type: 'separator' },

                          {

                              label: 'Open Link in Default Browser',

                              click: () => shell.openExternal(params.linkURL)

                          },

                          {

                              label: 'Copy Link Address',

                              click: () => clipboard.writeText(params.linkURL)

                          }

                      ]

                    : [])

            ];



            const menu = Menu.buildFromTemplate(template);

            menu.popup({

                window: mainWindow,

                x: Math.round(bounds.x + params.x),

                y: Math.round(bounds.y + params.y)

            });

        });



        mainWindow.addBrowserView(browserView);



        // Get main window dimensions and calculate the BrowserView position

        const bounds = mainWindow.getContentBounds();

        const sidebarWidth = 360; // Left nav (68px) + secondary sidebar (280px) + divider (8px) + button space (4px)

        const titlebarHeight = 38; // Title bar height



        browserView.setBounds({

            x: sidebarWidth,

            y: titlebarHeight,

            width: bounds.width - sidebarWidth,

            height: bounds.height - titlebarHeight

        });



        browserView.setAutoResize({

            width: true,

            height: true

        });



        // Load URL

        await browserView.webContents.loadURL(url);



        return { success: true };

    } catch (error) {

        console.error('Failed to load URL in BrowserView:', error);

        if (browserView && mainWindow) {

            try {

                mainWindow.webContents.send('browserview-load-failed', { url, errorCode: error && error.code, errorDescription: error && error.message });

            } catch (e) {

            }



            try {

                mainWindow.removeBrowserView(browserView);

            } catch (e) {

            }



            try {

                browserView.webContents.destroy();

            } catch (e) {

            }



            browserView = null;

        }

        return { success: false, error: error.message };

    }

});



ipcMain.on('close-browserview', () => {

    if (browserView && mainWindow) {

        mainWindow.removeBrowserView(browserView);

        browserView.webContents.destroy();

        browserView = null;

    }

});



ipcMain.on('hide-browserview', () => {

    if (browserView && mainWindow) {

        mainWindow.removeBrowserView(browserView);

        console.log('[BrowserView] Hidden (not destroyed)');

    }

});



ipcMain.on('show-browserview', () => {

    console.log('[Main] show-browserview called, browserView exists:', !!browserView, 'mainWindow exists:', !!mainWindow);

    if (browserView && mainWindow) {

        mainWindow.addBrowserView(browserView);



        // Restore BrowserView position

        const bounds = mainWindow.getContentBounds();

        const sidebarWidth = 360;

        const titlebarHeight = 38;



        browserView.setBounds({

            x: sidebarWidth,

            y: titlebarHeight,

            width: bounds.width - sidebarWidth,

            height: bounds.height - titlebarHeight

        });



        console.log('[BrowserView] Shown (restored)');

    } else {

        console.log('[BrowserView] Cannot show - browserView or mainWindow is null');

    }

});



ipcMain.on('update-browserview-bounds', (event, collapsed) => {

    if (browserView && mainWindow) {

        const bounds = mainWindow.getContentBounds();

        const sidebarWidth = collapsed ? 92 : 360; // Collapsed: 68+20+4, expanded: 68+280+8+4

        const titlebarHeight = 38;



        browserView.setBounds({

            x: sidebarWidth,

            y: titlebarHeight,

            width: bounds.width - sidebarWidth,

            height: bounds.height - titlebarHeight

        });

    }

});



ipcMain.handle('get-browserview-bounds', () => {

    if (browserView) {

        return browserView.getBounds();

    }

    return null;

});



// Adjust BrowserView when the window size changes

if (mainWindow) {

    mainWindow.on('resize', () => {

        if (browserView) {

            const bounds = mainWindow.getContentBounds();

            const sidebarWidth = 360; // Left nav (68px) + secondary sidebar (280px) + divider (8px) + button space (4px)

            const titlebarHeight = 38; // Title bar height



            browserView.setBounds({

                x: sidebarWidth,

                y: titlebarHeight,

                width: bounds.width - sidebarWidth,

                height: bounds.height - titlebarHeight

            });

        }

    });

}



// App lifecycle

app.whenReady().then(() => {

    setupMediaPermissions();

    createWindow();

    createTray();



    const f12Registered = globalShortcut.register('F12', () => {

        toggleDevToolsForFocused();

    });

    if (!f12Registered) {

        console.warn('[DevTools] Failed to register global shortcut: F12');

    }

    globalShortcut.register('CommandOrControl+Shift+I', () => {

        toggleDevToolsForFocused();

    });



    app.on('activate', () => {

        if (BrowserWindow.getAllWindows().length === 0) {

            createWindow();

        } else if (mainWindow) {

            mainWindow.show();

        }

    });

});



app.on('window-all-closed', () => {

    if (process.platform !== 'darwin') {

        app.quit();

    }

});



app.on('before-quit', () => {

    isQuitting = true;

    try {
        _cleanupOldBackendLogsOnExit();
    } catch (e) {
    }

    globalShortcut.unregisterAll();

    // Clean up the Python process

    if (pythonProcess) {

        pythonProcess.kill();

    }

});



// Error handling

process.on('uncaughtException', (error) => {

    console.error('Uncaught Exception:', error);

    dialog.showErrorBox('Error', `An uncaught exception occurred: ${error.message}`);

});

