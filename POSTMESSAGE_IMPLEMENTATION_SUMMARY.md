# PostMessage Implementation Summary

## 问题描述
需要在 Electron 渲染进程 (snsHandlers.js) 和 iframe 内的地图页面 (interact_python.js) 之间建立 postMessage 通信，使得：
1. snsHandlers.js 向 iframe 发送初始化消息
2. interact_python.js 接收消息并回复 "received" 确认

## 架构说明

```
Electron 渲染进程 (file:// 或自定义协议)
    └── snsHandlers.js
         │
         │ postMessage({type: 'init', ...})
         ▼
    <iframe src="http://localhost:8788">
         └── interact_python.js
              │
              │ postMessage({type: 'received', ...})
              ▼
         snsHandlers.js (接收确认)
```

## 实现的修改

### 1. scripts/js/interact_python.js (新增代码)

**位置:** 第 114-159 行

**功能:**
- 添加 `window.addEventListener('message')` 监听器
- 接收来自 Electron 父窗口的 postMessage
- 验证消息来源（支持 file://, localhost, null 等 Electron 特有的 origin）
- 处理 `init` 类型消息
- 发送 `received` 确认消息回父窗口

**关键代码:**
```javascript
window.addEventListener('message', function(event) {
    // 允许的来源
    const allowedOrigins = [
        'file://',
        'http://localhost:8788',
        'http://127.0.0.1:8788'
    ];

    // 验证来源
    const isAllowedOrigin = allowedOrigins.some(origin =>
        event.origin === origin || event.origin.startsWith('file://')
    );

    if (!isAllowedOrigin && event.origin !== 'null') {
        console.warn('Received message from unexpected origin:', event.origin);
        return;
    }

    // 处理 init 消息
    if (event.data.type === 'init') {
        // 发送确认
        const response = {
            type: 'received',
            data: {
                message: 'Message received successfully',
                originalType: event.data.type,
                timestamp: Date.now()
            }
        };

        // 使用 '*' 作为 targetOrigin（Electron file:// 协议要求）
        event.source.postMessage(response, '*');
    }
});
```

### 2. renderer/js/modules/sns/snsHandlers.js (修改)

**位置:** 第 550-552 行

**功能:**
- 在现有的消息处理器中添加 `received` 类型的处理
- 记录确认消息的接收

**修改内容:**
```javascript
switch (data.type) {
    case 'received':  // 新增
        console.log('地图页面已确认收到消息:', data.data);
        break;
    case 'locationUpdate':
        // ... 现有代码
```

### 3. 文档

创建了两个文档：
- `POSTMESSAGE_COMMUNICATION.md` - 完整的通信机制说明
- `POSTMESSAGE_IMPLEMENTATION_SUMMARY.md` - 本文档

## Electron 特殊处理

### Origin 验证
由于 Electron 使用 `file://` 协议或自定义协议，需要特殊处理：

1. **允许的 origins:**
   - `file://` - Electron 本地文件
   - `null` - 某些 Electron 配置
   - `http://localhost:8788` - iframe 的实际地址

2. **targetOrigin 设置:**
   - 发送到 Electron 父窗口时使用 `'*'`
   - 这是因为 `file://` 协议的限制
   - 在 Electron 环境中是安全的（父窗口是可信的）

### 安全性
- Electron 渲染进程只接受来自 `http://localhost:8788` 的消息（iframe）
- iframe 接受来自 Electron 的消息（file://, null, localhost）
- 由于是同一个应用内部通信，安全模型与浏览器不同

## 测试方法

1. 启动后端服务器: `python api_server.py`
2. 启动 Electron 应用
3. 打开 SNS 标签页
4. 打开开发者工具 (Ctrl+Shift+I)
5. 查看控制台输出

**预期的控制台消息:**

从 Electron 渲染进程:
```
地图页面加载完成
已发送初始化消息
收到地图页面消息: {type: 'received', ...}
地图页面已确认收到消息: {message: 'Message received successfully', ...}
```

从 iframe:
```
Received postMessage from parent window (Electron): {type: 'init', ...}
Message origin: file:// (或 null)
Initialization message received: {message: 'Hello from AI-SNS Electron App!', ...}
Sent "received" confirmation back to parent window (Electron)
```

## 消息类型

### 父窗口 → iframe
- `init` - 初始化消息（当前实现）
- 可扩展其他类型

### iframe → 父窗口
- `received` - 确认消息（新实现）
- `locationUpdate` - 位置更新（已存在）
- `mapClick` - 地图点击（已存在）
- `markerAdd` - 标记添加（已存在）

## 扩展方法

要添加新的消息类型：

1. **在 snsHandlers.js 中发送:**
   ```javascript
   this.sendMessageToMap('newType', { /* data */ });
   ```

2. **在 interact_python.js 中接收:**
   ```javascript
   if (event.data.type === 'newType') {
       // 处理新类型
   }
   ```

3. **在 snsHandlers.js 中接收响应:**
   ```javascript
   case 'newTypeResponse':
       // 处理响应
       break;
   ```

## 注意事项

1. **时序问题:** 确保 iframe 完全加载后再发送消息（已通过 `iframe.onload` 处理）
2. **Origin 日志:** 代码会记录实际的 origin，便于调试
3. **错误处理:** 包含 try-catch 块处理 postMessage 失败
4. **兼容性:** 支持不同的 Electron 配置和协议

## 完成状态

✅ interact_python.js 添加 postMessage 监听器
✅ 支持 Electron 特有的 origin 验证
✅ 实现 "received" 确认消息
✅ snsHandlers.js 处理 "received" 消息
✅ 完整的文档和测试说明
✅ 错误处理和日志记录

## 相关文件

- `scripts/js/interact_python.js` - iframe 端实现
- `renderer/js/modules/sns/snsHandlers.js` - Electron 端实现
- `POSTMESSAGE_COMMUNICATION.md` - 详细文档
- `POSTMESSAGE_IMPLEMENTATION_SUMMARY.md` - 本文档
