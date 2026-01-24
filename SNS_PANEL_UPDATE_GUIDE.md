# SNS 面板实时更新功能

## 概述

已优化 `backend/modules/sns/ai_social_engine_adapter.py`，使其能够通过 WebSocket 将内容实时推送到前端 Electron 的 SNS 栏目右侧面板的不同页签中。

## 功能说明

### 1. Think 页签更新

**后端函数**: `write_thinking_process_to_pane(title, content)`

- 将 AI 的思考过程写入 Think 页签的 "Thinking Log" 部分
- 内容会以格式化的方式显示，包含步骤编号和标题
- 自动滚动到最新内容

**示例**:
```python
adapter.write_thinking_process_to_pane(
    "分析用户需求",
    "用户希望在地图上查看附近的餐厅..."
)
```

### 2. Process 页签更新

**后端函数**: `write_task_process_to_pane(content)`

- 将任务处理过程写入 Process 页签
- 自动分离 "On Going" 和 "Process History" 内容
- 内容格式应包含特定标记：
  - `⏳ On Going` - 标记正在进行的任务
  - `📜 Process history` - 标记历史记录

**示例**:
```python
adapter.write_task_process_to_pane(content)
```

## 技术实现

### 后端

1. **WebSocket 管理器**: 使用 `backend/shared/websocket_manager.py` 中的单例管理器
2. **消息格式**:
```json
{
    "type": "sns_update",
    "tab": "think" | "process",
    "content": "实际内容..."
}
```

3. **异步发送**: 使用 `asyncio.create_task()` 异步发送消息，不阻塞主流程

### 前端

1. **WebSocket 连接**: 自动连接到 `ws://localhost:8000/ws`
2. **自动重连**: 连接断开后 5 秒自动重连
3. **页面销毁**: 离开 SNS 页面时自动关闭连接

## 使用方法

### 启动服务

1. 启动后端服务器:
```bash
python api_server.py
```

2. 启动 Electron 前端:
```bash
npm start
```

### 测试功能

在后端代码中调用相应函数即可自动推送到前端：

```python
from backend.modules.sns.ai_social_engine_adapter import AISocialEngineAdapter

# 创建适配器实例
adapter = AISocialEngineAdapter(db_session)

# 发送思考过程到 Think 页签
adapter.write_thinking_process_to_pane(
    "步骤1：分析环境",
    "当前位置：北京市朝阳区\n周边设施：餐厅、商场、公园"
)

# 发送任务进度到 Process 页签
process_content = """
⏳ On Going
正在执行任务：查找附近餐厅
进度：50%

📜 Process history
[2024-01-22 10:30] 开始任务
[2024-01-22 10:31] 获取位置信息
[2024-01-22 10:32] 查询数据库
"""
adapter.write_task_process_to_pane(process_content)
```

## 前端显示效果

### Think 页签
- 每条思考记录显示为独立的卡片
- 蓝色左边框，浅蓝色背景
- 等宽字体，便于阅读代码和结构化内容
- 自动滚动到最新内容

### Process 页签
- "On Going" 部分显示当前正在执行的任务
- "Process History" 部分显示历史记录
- 等宽字体，保持格式对齐

## 注意事项

1. **异步调用**: `_send_to_frontend` 是异步方法，使用 `asyncio.create_task()` 调用
2. **错误处理**: WebSocket 发送失败会记录日志但不会中断主流程
3. **连接管理**: 前端会自动管理连接状态和重连
4. **内容格式**: Process 页签的内容需要包含特定标记才能正确分离显示

## 文件修改清单

### 后端
- `backend/modules/sns/ai_social_engine_adapter.py`
  - 添加 WebSocket 管理器导入
  - 添加 `_send_to_frontend()` 方法
  - 修改 `write_thinking_process_to_pane()` 方法
  - 修改 `write_task_process_to_pane()` 方法

- `api_server.py`
  - 添加通用 WebSocket 端点 `/ws`

### 前端
- `renderer/js/modules/sns/snsHandlers.js`
  - 添加 `initWebSocketListener()` 方法
  - 添加 `handleSNSUpdate()` 方法
  - 添加 `updateThinkTab()` 方法
  - 添加 `updateProcessTab()` 方法
  - 修改 `init()` 方法添加 WebSocket 初始化
  - 修改 `destroy()` 方法添加 WebSocket 清理

## 扩展建议

1. **添加更多页签**: 可以扩展到 Resource 页签显示资源使用情况
2. **消息过滤**: 可以根据消息类型或优先级进行过滤
3. **历史记录**: 可以在前端保存历史记录，支持查看和搜索
4. **通知提醒**: 重要消息可以触发桌面通知
