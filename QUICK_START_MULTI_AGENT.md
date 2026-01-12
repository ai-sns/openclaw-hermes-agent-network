# 多Agent系统快速启动指南

## 前置条件

1. **后端服务运行**
   ```bash
   # 确保后端服务在 http://localhost:8788 运行
   python api_server.py
   ```

2. **数据库中有Agent数据**
   ```bash
   # 如果没有测试数据，创建一些：
   curl -X POST http://localhost:8788/api/agent \
     -H "Content-Type: application/json" \
     -d '{
       "name": "通用助手",
       "description": "可以回答各种问题的AI助手",
       "is_active": true
     }'

   curl -X POST http://localhost:8788/api/agent \
     -H "Content-Type: application/json" \
     -d '{
       "name": "程序员助手",
       "description": "精通多种编程语言的资深程序员",
       "is_active": true
     }'
   ```

## 启动步骤

### 1. 启动Electron应用

```bash
cd /mnt/c/dev/agi-ev/ai-sns-el
npm start
```

或者如果是Web版本：
```bash
# 直接在浏览器打开 index.html
# 或使用本地服务器
python -m http.server 8080
# 访问 http://localhost:8080
```

### 2. 验证功能

打开浏览器开发者工具（F12），检查Console输出：

```
[AgentModule] 初始化多Agent系统...
[MultiAgentHandlers] 开始初始化多Agent系统...
[MultiAgentHandlers] 已加载agents: 2
[AgentSidebar] 开始初始化...
[AgentSidebar] 加载到的agents: [...]
[AgentSidebar] 已创建所有Agent sections
[AgentSidebar] Agent列表已渲染
[AgentSidebar] 事件绑定完成
[AgentSidebar] 初始化完成
[AgentPage] 开始初始化，agents数量: 2
[AgentPage] 所有Agent pages已创建
[MultiAgentHandlers] 多Agent系统初始化完成
[AgentModule] 多Agent系统初始化完成
```

### 3. 测试功能清单

#### ✅ 基础功能
- [ ] 页面加载后看到所有agents显示在侧边栏底部的Agent列表中
- [ ] 第一个agent的section和page默认展开显示
- [ ] 其他agents的section和page处于隐藏状态

#### ✅ Agent切换
- [ ] 点击Agent列表中的第二个agent
- [ ] 第一个agent的section折叠（隐藏）
- [ ] 第二个agent的section展开（显示）
- [ ] 主内容区也相应切换到第二个agent的page
- [ ] Console输出显示：`[AgentSidebar] 切换到Agent: 2`

#### ✅ 独立的New Chat
- [ ] 在第一个agent中点击"New Chat"按钮
- [ ] 聊天区域清空，显示欢迎消息
- [ ] 切换到第二个agent
- [ ] 第二个agent仍保留之前的聊天内容（如果有）
- [ ] 在第二个agent中点击"New Chat"
- [ ] 两个agents的聊天历史相互独立

#### ✅ 独立的Settings
- [ ] 在第一个agent中点击"Setting"按钮
- [ ] 弹出的对话框显示第一个agent的名称和配置
- [ ] 关闭对话框，切换到第二个agent
- [ ] 点击第二个agent的"Setting"按钮
- [ ] 弹出的对话框显示第二个agent的名称和配置
- [ ] 配置是agent-specific的，互不影响

#### ✅ 发送消息
- [ ] 在第一个agent的输入框输入消息并发送
- [ ] 消息正确显示在第一个agent的聊天区域
- [ ] 切换到第二个agent
- [ ] 第二个agent的聊天区域为空（或显示之前的内容）
- [ ] 在第二个agent中发送消息
- [ ] 两个agents的对话完全独立

#### ✅ 流式响应
- [ ] 发送消息后看到"思考中..."动画
- [ ] AI回复逐字显示（流式输出）
- [ ] 回复完成后显示完整的Markdown格式内容
- [ ] 代码块正确高亮显示

#### ✅ 聊天列表
- [ ] 每个agent的侧边栏显示"Chat List"
- [ ] 发送消息后，聊天列表自动更新
- [ ] 点击聊天列表项可以加载历史对话
- [ ] 不同agent的聊天列表独立

#### ✅ 模型和角色选择
- [ ] 顶部工具栏显示模型选择器和角色选择器
- [ ] 切换模型后，右侧设置面板的Param页签更新
- [ ] 切换角色后，右侧设置面板的Prompt页签更新
- [ ] 不同agent可以选择不同的模型和角色

#### ✅ 右侧设置面板
- [ ] 点击底部的"Param"、"Prompt"、"File"页签可以切换
- [ ] 修改参数后自动保存
- [ ] 点击Prompt页签的"保存"按钮可以保存提示词
- [ ] 点击折叠按钮可以隐藏/显示设置面板

## 调试技巧

### 查看当前状态

打开Console，输入：

```javascript
// 查看当前agent ID
agentState.currentAgentId

// 查看所有agents
agentState.getAgents()

// 查看当前agent的状态
agentState.getCurrentAgentState()

// 查看当前agent的聊天历史
agentState.getChatHistory()
```

### 常见问题

#### 1. Agent列表为空

**症状**: 侧边栏没有显示agents，只显示"暂无可用的Agent"

**原因**:
- 后端API不可用
- 数据库中没有agents
- agents的is_active字段为false

**解决**:
```bash
# 检查后端是否运行
curl http://localhost:8788/api/agent

# 如果返回空，创建测试数据
curl -X POST http://localhost:8788/api/agent \
  -H "Content-Type: application/json" \
  -d '{"name": "Test Agent", "is_active": true}'
```

#### 2. 切换agent无反应

**症状**: 点击agent列表项没有任何变化

**原因**:
- JavaScript错误（查看Console）
- 事件绑定失败

**解决**:
1. 打开Console查看错误信息
2. 刷新页面重新初始化
3. 检查 `[AgentSidebar] 事件绑定完成` 日志是否输出

#### 3. 发送消息失败

**症状**: 点击发送按钮没反应，或显示错误

**原因**:
- 后端聊天API不可用
- 模型配置错误
- 网络问题

**解决**:
```bash
# 检查聊天API
curl -X POST http://localhost:8788/api/chat/stream \
  -H "Content-Type: application/json" \
  -d '{"messages": [{"role": "user", "content": "hello"}]}'
```

#### 4. 流式响应不显示

**症状**: 消息发送后一直显示"思考中..."

**原因**:
- SSE连接失败
- 回调函数未正确绑定

**解决**:
1. 检查Network面板的stream请求
2. 查看Console是否有错误
3. 确认后端支持SSE

## 高级配置

### 修改初始Agent

编辑 `multiAgentHandlers.js`:

```javascript
// 在 init() 方法中
if (agents.length > 0) {
    // 修改这里来改变默认agent
    const defaultAgentId = agents[0].id;  // 改为其他agent的id
    agentState.setCurrentAgent(defaultAgentId);
}
```

### 添加自定义事件处理

```javascript
// 监听agent切换事件
window.addEventListener('agent-switched', (e) => {
    const { agentId } = e.detail;
    console.log('切换到Agent:', agentId);
    // 添加你的自定义逻辑
});

// 监听new chat事件
window.addEventListener('agent-new-chat', (e) => {
    const { agentId } = e.detail;
    console.log('Agent', agentId, '创建新对话');
    // 添加你的自定义逻辑
});
```

### 自定义样式

如果需要调整agent section的样式，编辑CSS:

```css
/* 隐藏agent-section时的过渡效果 */
.agent-user-section {
    transition: all 0.3s ease;
}

.agent-user-section[style*="display: none"] {
    height: 0;
    overflow: hidden;
}

/* agent列表项hover效果 */
.agent-item:hover {
    background-color: #f5f5f5;
}

/* 当前激活的agent */
.agent-item.active {
    background-color: #e8f0fe;
    font-weight: 500;
}
```

## 性能监控

### 检查内存使用

```javascript
// 打开Chrome DevTools -> Memory -> Take Heap Snapshot
// 创建多个agents后，切换多次，再次Take Snapshot
// 对比两次snapshot，检查是否有内存泄漏
```

### 检查事件监听器

```javascript
// 打开Chrome DevTools -> Elements
// 选择一个agent的元素
// 右侧Properties面板查看Event Listeners
// 确保没有重复绑定的事件
```

## 下一步

1. **创建更多测试Agents**: 在Agent Management中创建不同用途的agents
2. **配置模型和角色**: 为每个agent选择合适的模型和角色
3. **测试并发场景**: 同时在多个agents中发送消息
4. **自定义界面**: 根据需求调整样式和布局

## 获取帮助

如果遇到问题：

1. **查看文档**: 阅读 `IMPLEMENTATION_COMPLETE_REPORT.md` 了解详细架构
2. **查看Console**: 所有关键操作都有日志输出
3. **查看Network**: 检查API调用是否成功
4. **查看源码**: 代码有详细的注释说明

---

**最后更新**: 2026-01-12
**版本**: 2.0.0
