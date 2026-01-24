# SNS AI Service Implementation

## 概述
为SNS模块实现了AI对话服务，允许前端通过control-send-btn与AI Agent进行交互。

## 实现的功能

### 1. 后端AI服务 (`backend/modules/sns/ai_service.py`)
- 创建了`SNSAIService`类，提供AI对话功能
- 支持通过Agent ID或名称调用Agent实例
- 实现了动态system prompt修改功能：
  - 根据mode参数（"ai"或"friends"）临时修改system prompt
  - AI模式：添加"我是你的AI助手"前缀
  - Friends模式：添加"我是你的朋友"前缀
  - 对话完成后自动恢复原始system prompt
- 使用`agent_manager`获取和管理Agent实例

### 2. API端点 (`backend/modules/sns/router.py`)
- 添加了`/api/sns/ai-chat`端点
- 接收参数：
  - `agent_identifier`: Agent ID或名称
  - `message`: 用户消息
  - `mode`: 对话模式（"ai"或"friends"）
- 返回格式：
  ```json
  {
    "success": true/false,
    "reply": "AI回复内容",
    "error": "错误信息（如果有）"
  }
  ```

### 3. 数据模型 (`backend/modules/sns/schemas.py`)
- 添加了`AIChatRequest`模型：定义请求参数
- 添加了`AIChatResponse`模型：定义响应格式

### 4. 前端API调用 (`renderer/js/modules/sns/snsApi.js`)
- 添加了`chatWithAI`方法
- 封装了与后端AI服务的HTTP通信

### 5. 前端事件处理 (`renderer/js/modules/sns/snsHandlers.js`)
- 为control-send-btn添加了点击事件处理
- 支持Enter键发送消息
- 自动获取当前选中的模式（AI/Friends）
- 实现了Toast消息显示功能，用于展示AI回复
- Toast特性：
  - 成功消息：绿色背景
  - 错误消息：红色背景
  - 3秒后自动消失
  - 支持长文本自动换行

## 使用方式

### 前端使用
1. 在SNS页面点击"Control"按钮进入控制模式
2. 在control-toggle-buttons中选择"AI"或"Friends"模式
3. 在control-input输入框中输入消息
4. 点击control-send-btn或按Enter键发送
5. AI回复会通过Toast消息显示在右上角

### 后端调用示例
```python
from backend.modules.sns.ai_service import SNSAIService

# 与Agent对话
reply = await SNSAIService.chat_with_agent(
    agent_identifier="1",  # 或使用Agent名称
    message="你好",
    mode="ai"  # 或 "friends"
)
```

## 技术特点

1. **动态System Prompt修改**
   - 临时修改，不影响数据库
   - 自动恢复原始配置
   - 支持不同对话模式

2. **Agent实例复用**
   - 使用`agent_manager`的缓存机制
   - 避免重复加载Agent配置

3. **错误处理**
   - 完整的异常捕获和日志记录
   - 友好的错误消息返回给前端

4. **用户体验**
   - Toast消息提供即时反馈
   - 支持键盘快捷键（Enter发送）
   - 自动清空输入框

## 注意事项

1. 当前实现使用Agent ID "1"作为默认Agent，可根据需要修改
2. 对话不使用memory和knowledge_base，每次都是独立对话
3. Toast消息最多显示3秒，长文本可能需要用户快速阅读
4. 需要确保至少有一个可用的Agent配置在数据库中

## 后续优化建议

1. 添加Agent选择功能，让用户可以选择不同的Agent
2. 支持对话历史记录
3. 添加流式响应支持，提升长回复的用户体验
4. 增加加载状态指示器
5. 支持更丰富的消息展示方式（如对话气泡）
