# SNS栏目 AI社交引擎集成说明

## 概述
本次优化实现了Electron前端SNS栏目的 `snsStartBtn` 按钮与后端 `ai_social_engine.py` 中的 `start()` 函数的集成。

## 实现的功能

### 1. 后端API端点
在 `backend/modules/sns/router.py` 中添加了两个新的API端点：

- **POST `/api/sns/start-engine`** - 启动AI社交引擎
- **POST `/api/sns/stop-engine`** - 停止AI社交引擎

### 2. 后端服务层
在 `backend/modules/sns/service.py` 中添加了三个新方法：

- `start_social_engine()` - 启动AI社交引擎
- `stop_social_engine()` - 停止AI社交引擎
- `get_engine_status()` - 获取引擎状态

### 3. AI社交引擎适配器
创建了新文件 `backend/modules/sns/ai_social_engine_adapter.py`，提供了一个后端兼容的AI社交引擎适配器：

- **AISocialEngine类** - 封装了原有 `ai_social_engine.py` 中的核心功能
- **start()方法** - 启动引擎，初始化能力列表和任务处理循环
- **stop()方法** - 停止引擎，清理资源
- **get_status()方法** - 获取引擎当前状态

**核心功能：**
- 管理引擎启动/停止状态
- 初始化6大核心能力：
  - 查找人员进行沟通
  - 查找地点进行移动
  - 查找工具使用服务
  - 查找任务执行
  - 查找交易进行
  - 查找探访进行
- 后台任务处理循环
- 异步任务管理

### 4. 前端API调用
在 `renderer/js/modules/sns/snsApi.js` 中添加了两个新方法：

- `startEngine()` - 调用后端启动引擎API
- `stopEngine()` - 调用后端停止引擎API

### 5. 前端按钮事件处理
在 `renderer/js/modules/sns/snsHandlers.js` 中优化了 `snsStartBtn` 按钮的点击事件：

- **点击Start** - 调用后端API启动引擎，按钮变为Pause状态
- **点击Pause** - 调用后端API停止引擎，按钮恢复为Start状态
- **加载状态** - 在API调用期间显示 "Starting..." 或 "Stopping..."
- **Toast提示** - 成功或失败时显示相应的提示消息

## 使用方法

### 启动后端服务
```bash
# 确保后端服务正在运行
python api_server.py
# 或
python backend/main.py
```

### 启动前端应用
```bash
# 启动Electron应用
npm start
```

### 使用SNS功能
1. 在Electron应用中切换到SNS栏目
2. 找到底部操作栏的 "Start" 按钮
3. 点击 "Start" 按钮启动AI社交引擎
4. 引擎启动后，按钮变为 "Pause"，可以点击停止引擎

## 技术架构

```
前端 (Electron/Renderer)
  └── renderer/js/modules/sns/
      ├── SNSPage.js         (UI组件 - 包含snsStartBtn)
      ├── snsApi.js          (API调用层 - startEngine/stopEngine)
      └── snsHandlers.js     (事件处理 - 按钮点击逻辑)
                ↓ HTTP POST
后端 (FastAPI)
  └── backend/modules/sns/
      ├── router.py          (路由层 - /start-engine, /stop-engine)
      ├── service.py         (服务层 - 业务逻辑)
      └── ai_social_engine_adapter.py  (引擎适配器)
                ↓
      └── ai_social_engine.py (原有的AI社交引擎)
```

## 注意事项

1. **异步处理**: 所有的启动/停止操作都是异步的，避免阻塞UI
2. **状态管理**: 引擎状态通过全局变量在服务层管理，确保单例运行
3. **错误处理**: 完善的错误处理和用户提示
4. **Qt依赖**: 原有的 `ai_social_engine.py` 依赖Qt框架，适配器提供了无Qt版本

## 后续优化建议

1. **状态持久化**: 将引擎状态保存到数据库，应用重启后恢复
2. **实时反馈**: 通过WebSocket向前端推送引擎运行状态
3. **任务监控**: 添加任务执行进度和日志查看功能
4. **配置管理**: 提供UI界面配置引擎参数
5. **错误恢复**: 添加自动重启和错误恢复机制

## 相关文件清单

**后端文件：**
- `backend/modules/sns/router.py` - 新增API路由
- `backend/modules/sns/service.py` - 新增服务方法
- `backend/modules/sns/ai_social_engine_adapter.py` - 新建适配器文件
- `backend/modules/sns/ai_social_engine.py` - 原有引擎（参考）

**前端文件：**
- `renderer/js/modules/sns/SNSPage.js` - UI定义（包含按钮）
- `renderer/js/modules/sns/snsApi.js` - 新增API方法
- `renderer/js/modules/sns/snsHandlers.js` - 修改事件处理

## 测试方法

### 1. 后端API测试
```bash
# 启动引擎
curl -X POST http://localhost:8788/api/sns/start-engine

# 停止引擎
curl -X POST http://localhost:8788/api/sns/stop-engine
```

### 2. 前端集成测试
1. 启动Electron应用
2. 打开开发者工具（F12）
3. 切换到SNS栏目
4. 点击Start按钮
5. 查看Console输出和Network请求
6. 验证Toast提示消息

## 版本信息
- 更新日期: 2026-01-18
- 版本: 1.0.0
- 状态: 已完成并可用
