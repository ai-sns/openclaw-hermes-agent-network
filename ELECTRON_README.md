# AI-SNS Electron 版本

本项目已从 PyQt5 桌面应用改造为 Electron + Python 混合架构。

## 架构说明

```
┌─────────────────────────────────────────────────────────────┐
│                      Electron 应用                          │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                   渲染进程 (Renderer)                    ││
│  │  ┌─────────────────────────────────────────────────────┐││
│  │  │  HTML/CSS/JavaScript 界面                           │││
│  │  │  - index.html (主页面)                              │││
│  │  │  - css/ (样式文件)                                  │││
│  │  │  - js/ (业务逻辑)                                   │││
│  │  └─────────────────────────────────────────────────────┘││
│  └─────────────────────────────────────────────────────────┘│
│                           ↕ IPC                             │
│  ┌─────────────────────────────────────────────────────────┐│
│  │                    主进程 (Main)                        ││
│  │  - electron/main.js (窗口管理、菜单、托盘)               ││
│  │  - electron/preload.js (安全桥接)                       ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
                           ↕ HTTP/WebSocket
┌─────────────────────────────────────────────────────────────┐
│                    Python API 服务器                         │
│  ┌─────────────────────────────────────────────────────────┐│
│  │  FastAPI 后端 (api_server.py)                           ││
│  │  - REST API 端点                                        ││
│  │  - WebSocket 实时通信                                   ││
│  │  - 数据库操作                                           ││
│  │  - AI Agent 管理                                        ││
│  │  - 知识库管理                                           ││
│  └─────────────────────────────────────────────────────────┘│
│  ┌─────────────────────────────────────────────────────────┐│
│  │  原有 Python 模块                                       ││
│  │  - Agent.py                                             ││
│  │  - db/DBFactory.py                                      ││
│  │  - 其他业务逻辑                                         ││
│  └─────────────────────────────────────────────────────────┘│
└─────────────────────────────────────────────────────────────┘
```

## 目录结构

```
ai-sns-el/
├── electron/                    # Electron 主进程
│   ├── main.js                 # 主进程入口
│   └── preload.js              # 预加载脚本
├── renderer/                    # 渲染进程 (前端界面)
│   ├── index.html              # 主页面
│   ├── css/
│   │   ├── main.css           # 主样式
│   │   ├── components.css     # 组件样式
│   │   └── themes.css         # 主题定义
│   └── js/
│       ├── api.js             # API 客户端
│       ├── components.js      # UI 组件
│       ├── pages.js           # 页面控制器
│       └── app.js             # 应用入口
├── api_server.py               # Python API 服务器
├── package.json                # Node.js 配置
├── start.sh                    # Linux/macOS 启动脚本
├── start.bat                   # Windows 启动脚本
├── db/                         # 数据库模块
├── agent/                      # Agent 模块
├── km/                         # 知识库模块
└── ... (其他原有文件)
```

## 快速开始

### 前置要求

- Node.js 18+
- Python 3.8+
- npm 或 yarn

### 安装依赖

```bash
# 安装 Node.js 依赖
npm install

# 安装 Python 依赖 (如果还没有)
pip install fastapi uvicorn
```

### 运行应用

#### 方式一：一键启动 (推荐)

```bash
# Linux/macOS
./start.sh

# Windows
start.bat
```

#### 方式二：分别启动

```bash
# 终端1: 启动 Python API 服务器
python api_server.py

# 终端2: 启动 Electron 应用
npm run start:electron
```

#### 方式三：开发模式

```bash
# 开发模式 (自动重载)
npm run dev
```

### 打包发布

```bash
# 打包为当前平台
npm run build

# 打包为 Windows
npm run build:win

# 打包为 macOS
npm run build:mac

# 打包为 Linux
npm run build:linux
```

## API 端点

API 服务器默认运行在 `http://localhost:8765`

### Agent 管理
- `GET /api/agents` - 获取所有 Agent
- `POST /api/agents` - 创建 Agent
- `PUT /api/agents/{id}` - 更新 Agent
- `DELETE /api/agents/{id}` - 删除 Agent

### 聊天
- `POST /api/chat` - 发送聊天消息
- `GET /api/chat/history/{agent_id}` - 获取聊天历史

### 知识库
- `GET /api/knowledge-base` - 获取知识库列表
- `POST /api/knowledge-base` - 创建知识库
- `POST /api/knowledge-base/{id}/upload` - 上传文件

### 系统
- `GET /api/system/config` - 获取系统配置
- `PUT /api/system/config` - 更新系统配置
- `GET /health` - 健康检查

### WebSocket
- `ws://localhost:8765/ws/{client_id}` - 实时通信

## 主题支持

支持以下主题:
- Dark (深色) - 默认
- Light (浅色)
- Catppuccin Mocha
- Nord
- Dracula
- Tokyo Night
- One Dark
- GitHub Dark
- Material Dark
- Gruvbox Dark
- Solarized Dark

## 与原 PyQt5 版本的区别

| 特性 | PyQt5 版本 | Electron 版本 |
|------|-----------|---------------|
| 界面技术 | PyQt5 (Python) | HTML/CSS/JS |
| 后端 | 同进程 | 独立 API 服务器 |
| 通信方式 | 直接调用 | HTTP/WebSocket |
| 打包大小 | 较小 | 较大 (包含 Chromium) |
| 跨平台 | 需编译 | 统一代码 |
| 热更新 | 不支持 | 支持 |
| 开发调试 | PyCharm | Chrome DevTools |

## 注意事项

1. 首次运行需要安装 npm 依赖，可能需要一些时间
2. API 服务器需要先于 Electron 启动
3. 开发时可以单独修改前端代码，刷新即可看到效果
4. 生产环境建议使用打包后的版本

## 故障排除

### Electron 无法启动
- 检查 Node.js 版本是否 >= 18
- 尝试删除 node_modules 重新安装

### API 连接失败
- 确保 Python API 服务器已启动
- 检查端口 8765 是否被占用

### 样式显示异常
- 清除浏览器缓存
- 检查 CSS 文件路径

## 开发指南

### 添加新页面

1. 在 `renderer/index.html` 添加页面 HTML
2. 在 `renderer/js/pages.js` 添加页面控制器
3. 在导航菜单添加入口

### 添加新 API

1. 在 `api_server.py` 添加端点
2. 在 `renderer/js/api.js` 添加客户端方法
3. 在页面控制器中调用

### 自定义主题

编辑 `renderer/css/themes.css`，按照现有主题格式添加新主题。
