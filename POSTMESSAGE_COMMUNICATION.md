# PostMessage Communication Between SNS and Map

## Overview
This document explains the postMessage communication flow between the SNS module (Electron renderer process) and the map iframe (http://localhost:8788).

## Architecture

```
┌─────────────────────────────────────┐
│   Electron Main Process             │
└─────────────────────────────────────┘
              │
              ▼
┌─────────────────────────────────────┐
│   Electron Renderer Process         │
│   (file:// or custom protocol)      │
│                                     │
│   ┌─────────────────────────────┐  │
│   │  snsHandlers.js             │  │
│   │  (Parent Window)            │  │
│   └─────────────────────────────┘  │
│              │                      │
│              │ postMessage          │
│              ▼                      │
│   ┌─────────────────────────────┐  │
│   │  <iframe>                   │  │
│   │  src: http://localhost:8788 │  │
│   │                             │  │
│   │  ┌───────────────────────┐ │  │
│   │  │ interact_python.js    │ │  │
│   │  │ (Iframe Content)      │ │  │
│   │  └───────────────────────┘ │  │
│   └─────────────────────────────┘  │
└─────────────────────────────────────┘
```

## Communication Flow

### 1. Parent Window → Iframe (snsHandlers.js → interact_python.js)

**Location:** `renderer/js/modules/sns/snsHandlers.js:530`

When the map iframe loads, the parent window sends an initialization message:

```javascript
const initialData = {
    type: 'init',
    data: {
        message: 'Hello from AI-SNS Electron App!',
        timestamp: Date.now()
    }
};

iframe.contentWindow.postMessage(initialData, 'http://localhost:8788');
```

### 2. Iframe Receives Message (interact_python.js)

**Location:** `scripts/js/interact_python.js:114-159`

The iframe listens for messages from the Electron parent window:

```javascript
window.addEventListener('message', function(event) {
    // Verify origin - Electron window may use file:// or custom protocol
    const allowedOrigins = [
        'file://',
        'http://localhost:8788',
        'http://127.0.0.1:8788'
    ];

    const isAllowedOrigin = allowedOrigins.some(origin =>
        event.origin === origin || event.origin.startsWith('file://')
    );

    if (!isAllowedOrigin && event.origin !== 'null') {
        console.warn('Received message from unexpected origin:', event.origin);
        return;
    }

    console.log('Received postMessage from parent window (Electron):', event.data);
    console.log('Message origin:', event.origin);

    // Handle init message
    if (event.data.type === 'init') {
        console.log('Initialization message received:', event.data.data);

        // Send "received" confirmation back
        const response = {
            type: 'received',
            data: {
                message: 'Message received successfully',
                originalType: event.data.type,
                timestamp: Date.now()
            }
        };

        // Use '*' as targetOrigin for Electron compatibility
        event.source.postMessage(response, '*');
        console.log('Sent "received" confirmation back to parent window (Electron)');
    }
});
```

**Important Notes:**
- The origin check allows `file://`, `null`, and localhost origins to support Electron
- Uses `'*'` as targetOrigin when sending back to handle file:// protocol restrictions
- Logs the actual origin for debugging purposes

### 3. Parent Window Receives Confirmation (snsHandlers.js)

**Location:** `renderer/js/modules/sns/snsHandlers.js:544-566`

The parent window listens for responses from the iframe:

```javascript
const handleMessage = (event) => {
    if (event.origin === 'http://localhost:8788') {
        const data = event.data;
        console.log('收到地图页面消息:', data);

        switch (data.type) {
            case 'received':
                console.log('地图页面已确认收到消息:', data.data);
                break;
            case 'locationUpdate':
                this.handleLocationUpdate(data.data);
                break;
            // ... other message types
        }
    }
};

window.addEventListener('message', handleMessage);
```

## Message Types

### From Parent to Iframe
- `init` - Initialization message sent when iframe loads

### From Iframe to Parent
- `received` - Confirmation that a message was received
- `locationUpdate` - Location data update
- `mapClick` - Map click event
- `markerAdd` - Marker addition event

## Security

### Origin Verification

**Electron Renderer (snsHandlers.js):**
- Only accepts messages from `http://localhost:8788` (the iframe's origin)
- This is secure because the iframe content is controlled

**Iframe (interact_python.js):**
- Accepts messages from:
  - `file://` protocol (Electron local files)
  - `http://localhost:8788` (local server)
  - `http://127.0.0.1:8788` (local server alternative)
  - `null` origin (some Electron configurations)
- Uses `'*'` as targetOrigin when responding due to file:// protocol limitations
- This is acceptable in Electron context as the parent window is trusted

### Electron-Specific Considerations

1. **File Protocol:** Electron apps often use `file://` protocol, which has special postMessage behavior
2. **Null Origin:** Some Electron configurations may report `null` as the origin
3. **Target Origin:** When sending to file:// origins, must use `'*'` as targetOrigin
4. **Security Context:** Since both parent and iframe are part of the same Electron app, the security model is different from web browsers

## Testing

To test the communication in Electron:

1. Start the backend server: `python api_server.py`
2. Launch the Electron app
3. Navigate to the SNS tab
4. Open DevTools (View → Toggle Developer Tools or Ctrl+Shift+I)
5. Check the Console for these messages:

**From Electron Renderer (snsHandlers.js):**
- "地图页面加载完成"
- "已发送初始化消息"
- "收到地图页面消息: {type: 'received', ...}"
- "地图页面已确认收到消息"

**From Iframe (interact_python.js):**
- "Received postMessage from parent window (Electron): {type: 'init', ...}"
- "Message origin: file://" (or "null" or other Electron origin)
- "Initialization message received"
- "Sent 'received' confirmation back to parent window (Electron)"

### Debugging Tips

1. **Check the origin:** Look for "Message origin:" in the console to see what origin Electron is using
2. **Network tab:** Verify the iframe is loading from `http://localhost:8788`
3. **Console errors:** Look for CORS or postMessage errors
4. **Timing issues:** The iframe must be fully loaded before postMessage works

## Adding New Message Types

To add a new message type:

1. **In snsHandlers.js:** Send the message using `sendMessageToMap(type, data)`
2. **In interact_python.js:** Add a new case in the message event listener
3. **In snsHandlers.js:** Add a new case in `handleMessage()` to handle responses
