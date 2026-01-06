const { app, BrowserWindow, ipcMain, Menu, Tray, dialog, shell } = require('electron');
const path = require('path');
const { spawn } = require('child_process');

// Windows 10 + 无边框窗口：禁用 GPU 硬件加速（可选，根据需要启用）
// app.disableHardwareAcceleration();

let mainWindow = null;

// Azure OpenAI 配置（OpenAI 兼容格式）
const AZURE_OPENAI_CONFIG = {
    baseUrl: 'https://fstock.openai.azure.com/openai/v1',
    apiKey: '7Jd0HVW50YOKPpqK3Hywj6qiRdw4H1RBTlQWxF022vt5Eww7UwYlJQQJ99BIACHYHv6XJ3w3AAABACOGH9HI',
    model: 'gpt-5-prod'
};
let tray = null;
let pythonProcess = null;
let isQuitting = false;

// API服务器配置
const API_HOST = 'localhost';
const API_PORT = 8765;
const API_BASE_URL = `http://${API_HOST}:${API_PORT}`;

// 开发模式检测
const isDev = process.argv.includes('--dev') || process.env.NODE_ENV === 'development';

function createWindow() {
    mainWindow = new BrowserWindow({
        width: 1400,
        height: 900,
        minWidth: 1000,
        minHeight: 700,
        icon: path.join(__dirname, '../images/logowithe.png'),
        webPreferences: {
            nodeIntegration: false,
            contextIsolation: true,
            preload: path.join(__dirname, 'preload.js'),
            webSecurity: true,
            // 确保输入框可用
            enableBlinkFeatures: 'KeyboardFocusableScrollers'
        },
        // 无边框窗口，使用自定义标题栏
        frame: false,
        // macOS 专用设置
        trafficLightPosition: { x: 16, y: 16 },
        // 启用窗口透明效果
        transparent: false,
        backgroundColor: '#f5f5f5',
        // 启用窗口阴影
        hasShadow: true,
        show: false,
        // Windows 焦点修复
        skipTaskbar: false,
        focusable: true
    });

    // 移除应用菜单
    Menu.setApplicationMenu(null);

    // 加载主页面
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));

    // 窗口准备好后显示
    mainWindow.once('ready-to-show', () => {
        mainWindow.show();
        mainWindow.focus();
        mainWindow.webContents.focus();

        if (isDev) {
            mainWindow.webContents.openDevTools();
        }
    });

    // 窗口关闭事件处理（最小化到托盘）
    mainWindow.on('close', (event) => {
        if (!isQuitting) {
            event.preventDefault();
            mainWindow.hide();
            if (tray) {
                tray.displayBalloon({
                    title: 'AI-SNS',
                    content: '应用已最小化到托盘，点击托盘图标可恢复窗口'
                });
            }
        }
    });

    mainWindow.on('closed', () => {
        mainWindow = null;
    });
}

function createTray() {
    const iconPath = path.join(__dirname, '../images/logowithe.png');
    tray = new Tray(iconPath);

    const contextMenu = Menu.buildFromTemplate([
        {
            label: '显示',
            click: () => {
                if (mainWindow) {
                    mainWindow.show();
                    mainWindow.focus();
                }
            }
        },
        {
            label: '隐藏',
            click: () => {
                if (mainWindow) {
                    mainWindow.hide();
                }
            }
        },
        { type: 'separator' },
        {
            label: '退出',
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

// IPC通信处理
ipcMain.handle('get-api-url', () => {
    return API_BASE_URL;
});

ipcMain.handle('get-app-path', () => {
    return app.getAppPath();
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

// 窗口控制 IPC
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

// 修复 Windows 10 无边框窗口输入框焦点问题
ipcMain.on('fix-input-focus', () => {
    if (mainWindow) {
        // 模拟最小化再还原，强制触发 Windows 焦点事件
        mainWindow.minimize();
        setTimeout(() => {
            mainWindow.restore();
            mainWindow.focus();
            mainWindow.webContents.focus();
        }, 50);
    }
});

// Azure OpenAI 流式聊天（使用 OpenAI 兼容格式）
ipcMain.on('chat-stream-start', async (event, { messages, requestId }) => {
    try {
        const https = require('https');

        // 从 baseUrl 解析 hostname 和 path
        const url = new URL(AZURE_OPENAI_CONFIG.baseUrl);
        const hostname = url.hostname;
        const apiPath = `${url.pathname}/chat/completions`;

        console.log(`Connecting to Azure OpenAI: https://${hostname}${apiPath}`);

        const requestBody = JSON.stringify({
            model: AZURE_OPENAI_CONFIG.model,
            messages: messages,
            stream: true,
            temperature: 1.0,
            max_completion_tokens: 4096
        });

        const options = {
            hostname: hostname,
            port: 443,
            path: apiPath,
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${AZURE_OPENAI_CONFIG.apiKey}`,
                'Content-Length': Buffer.byteLength(requestBody)
            }
        };

        const req = https.request(options, (res) => {
            let buffer = '';
            let fullResponse = '';

            console.log(`Response status: ${res.statusCode}`);
            console.log(`Response headers:`, res.headers);

            // 检查 HTTP 状态码
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

            res.on('data', (chunk) => {
                const chunkStr = chunk.toString();
                buffer += chunkStr;
                fullResponse += chunkStr;

                // 处理 SSE 数据
                const lines = buffer.split('\n');
                buffer = lines.pop() || ''; // 保留未完成的行

                for (const line of lines) {
                    const trimmedLine = line.trim();
                    if (trimmedLine.startsWith('data: ')) {
                        const data = trimmedLine.slice(6);
                        if (data === '[DONE]') {
                            event.sender.send('chat-stream-end', { requestId });
                            return;
                        }
                        try {
                            const parsed = JSON.parse(data);
                            const content = parsed.choices?.[0]?.delta?.content;
                            if (content) {
                                console.log(`Stream content: ${content}`);
                                event.sender.send('chat-stream-data', { requestId, content });
                            }
                        } catch (e) {
                            console.log(`Parse error for line: ${trimmedLine}`);
                        }
                    }
                }
            });

            res.on('end', () => {
                console.log(`Full response received, length: ${fullResponse.length}`);
                // 处理剩余的 buffer
                if (buffer.trim()) {
                    const trimmedLine = buffer.trim();
                    if (trimmedLine.startsWith('data: ') && trimmedLine.slice(6) !== '[DONE]') {
                        try {
                            const parsed = JSON.parse(trimmedLine.slice(6));
                            const content = parsed.choices?.[0]?.delta?.content;
                            if (content) {
                                event.sender.send('chat-stream-data', { requestId, content });
                            }
                        } catch (e) {}
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
            event.sender.send('chat-stream-error', { requestId, error: error.message });
        });

        req.write(requestBody);
        req.end();

    } catch (error) {
        event.sender.send('chat-stream-error', { requestId, error: error.message });
    }
});

// Windows 焦点修复：窗口获得焦点时确保 webContents 也获得焦点
app.on('browser-window-focus', () => {
    const win = BrowserWindow.getFocusedWindow();
    if (win) {
        win.webContents.focus();
    }
});

// 应用生命周期
app.whenReady().then(() => {
    createWindow();
    createTray();

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
    // 清理Python进程
    if (pythonProcess) {
        pythonProcess.kill();
    }
});

// 错误处理
process.on('uncaughtException', (error) => {
    console.error('Uncaught Exception:', error);
    dialog.showErrorBox('错误', `发生未捕获的异常: ${error.message}`);
});
