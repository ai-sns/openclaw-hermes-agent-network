# Agent 模型和角色管理功能 - 用户指南

## 功能概述

本系统提供了完整的 AI 模型和角色配置管理功能，支持：

- **模型管理**：配置和管理 OpenAI、Claude、Gemini 和类 OpenAI 接口的 LLM 模型
- **角色管理**：创建和管理不同的 AI 角色（人设），支持预设模板
- **动态选择器**：聊天界面上的模型和角色选择器会从配置中动态加载
- **导入导出**：支持配置的批量导入和导出，方便备份和分享

## 快速开始

### 1. 访问管理界面

在 Agent 栏目的侧边栏中，点击以下按钮进入对应的管理界面：

- **模型管理** - 配置 LLM 模型连接
- **角色管理** - 配置 AI 角色人设

### 2. 添加第一个模型

1. 点击侧边栏的"模型管理"
2. 点击右上角的"+ 添加模型"按钮
3. 填写基础配置：
   - **显示名称**：如 "我的 GPT-4"
   - **接口类型**：选择 OpenAI / Claude / Gemini / 类 OpenAI
   - **API 端点**：如 `https://api.openai.com/v1/chat/completions`
   - **API Key**：你的 API 密钥
   - **模型名称**：如 `gpt-4o`
4. （可选）切换到"高级参数"标签页配置温度、Token 等
5. （可选）勾选"设为默认模型"
6. 点击"保存"

### 3. 添加第一个角色

1. 点击侧边栏的"角色管理"
2. 可以选择：
   - 点击"从模板创建"选择预设角色模板（推荐）
   - 点击"+ 添加角色"从零创建
3. 填写角色信息：
   - **角色名称**：如 "Python 专家"
   - **系统提示词**：定义角色的行为和特点
   - **分类**：选择开发者/写作者/分析师/助手/其他
4. 点击"保存"

## 详细功能说明

### 模型管理

#### 支持的接口类型

1. **OpenAI**
   - API 端点：`https://api.openai.com/v1/chat/completions`
   - 支持：GPT-3.5、GPT-4、GPT-4o 等所有 OpenAI 模型

2. **Claude (Anthropic)**
   - API 端点：`https://api.anthropic.com/v1/messages`
   - 支持：Claude 3 Sonnet、Opus 等

3. **Gemini (Google)**
   - API 端点：Google AI Studio 提供的端点
   - 支持：Gemini Pro 等

4. **类 OpenAI (自定义)**
   - 任何兼容 OpenAI API 格式的端点
   - 如：本地部署的 LLaMA、通义千问等

#### 基础配置项

| 配置项 | 说明 | 必填 |
|--------|------|------|
| 显示名称 | 在选择器中显示的名称 | 是 |
| 接口类型 | 选择 API 提供商类型 | 是 |
| API 端点 | 完整的 API URL | 是 |
| API Key | 认证密钥 | 是 |
| 模型名称 | 具体的模型标识符 | 是 |
| 描述 | 配置说明 | 否 |
| 设为默认 | 是否作为默认模型 | 否 |
| 启用此配置 | 是否在选择器中显示 | 否 |

#### 高级参数

| 参数 | 范围 | 默认值 | 说明 |
|------|------|--------|------|
| Temperature | 0-2 | 0.7 | 控制输出随机性，越高越随机 |
| Max Tokens | 1+ | 2048 | 最大生成令牌数 |
| Top P | 0-1 | 1.0 | 核采样参数 |
| Frequency Penalty | -2 到 2 | 0 | 频率惩罚 |
| Presence Penalty | -2 到 2 | 0 | 存在惩罚 |
| 流式输出 | - | 开启 | 是否启用流式响应 |

#### 测试连接

在保存前，可以点击"测试连接"按钮验证配置是否正确。系统会尝试连接 API 并返回测试结果。

#### 导入导出

**导出配置：**
1. 点击"导出"按钮
2. 系统会下载一个 JSON 文件（API Key 会被脱敏处理）
3. 文件名格式：`llm-configs-{timestamp}.json`

**导入配置：**
1. 点击"导入"按钮
2. 选择之前导出的 JSON 文件
3. 系统会显示将要导入的配置数量
4. 确认后批量创建配置

### 角色管理

#### 预设角色模板

系统提供以下预设角色模板：

1. **资深程序员**
   - 分类：开发者
   - 特点：精通多种编程语言，善于编写高质量代码

2. **创意写作**
   - 分类：写作者
   - 特点：擅长各种文体创作，富有创意

3. **数据分析师**
   - 分类：分析师
   - 特点：擅长数据分析、统计和可视化

4. **通用助手**（默认）
   - 分类：助手
   - 特点：友好、全能的 AI 助手

#### 自定义角色

创建自定义角色时需要提供：

| 配置项 | 说明 | 必填 |
|--------|------|------|
| 角色名称 | 内部标识名称 | 是 |
| 显示名称 | 在选择器中显示的名称 | 否 |
| 系统提示词 | 定义角色行为的核心提示词 | 是 |
| 欢迎消息 | 选择角色时的欢迎语 | 否 |
| 分类 | 开发者/写作者/分析师/助手/其他 | 否 |
| 描述 | 角色说明 | 否 |
| 标签 | 逗号分隔的标签，如"Python,AI" | 否 |

**系统提示词编写技巧：**
- 明确定义角色的专业领域
- 说明回答风格（专业/友好/简洁等）
- 给出具体的行为指引
- 可以包含示例

示例：
```
你是一位专精于 Python 和机器学习的高级工程师。
请用专业但易懂的方式回答问题，并在适当时提供代码示例。
注重代码质量和最佳实践，解释你的设计决策。
```

#### 使用次数统计

系统会自动统计每个角色的使用次数，帮助你了解哪些角色最常用。

### 在聊天中使用

配置完成后，在 Agent 聊天界面：

1. **选择模型**：从顶部的模型选择器中选择已配置的模型
2. **选择角色**：从角色选择器中选择角色
3. **开始聊天**：发送消息时会使用选定的模型和角色配置

选择器会自动从配置中加载，只显示已启用的配置。

## API 文档

### 模型配置 API

**基础 URL:** `http://localhost:8788/api`

#### 获取所有模型

```http
GET /llm-configs?active_only=true
```

**响应：**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "config_id": "llm_abc123def456",
      "name": "我的 GPT-4",
      "provider": "openai",
      "model_name": "gpt-4o",
      "api_endpoint": "https://api.openai.com/v1/chat/completions",
      "temperature": 0.7,
      "max_tokens": 2048,
      "is_active": true,
      "is_default": false
    }
  ]
}
```

#### 创建模型

```http
POST /llm-configs
Content-Type: application/json

{
  "name": "我的 GPT-4",
  "provider": "openai",
  "api_endpoint": "https://api.openai.com/v1/chat/completions",
  "api_key": "sk-...",
  "model_name": "gpt-4o",
  "temperature": 0.7,
  "max_tokens": 2048
}
```

#### 更新模型

```http
PUT /llm-configs/{config_id}
Content-Type: application/json

{
  "temperature": 0.9,
  "is_active": false
}
```

#### 删除模型

```http
DELETE /llm-configs/{config_id}
```

#### 测试连接

```http
POST /llm-configs/test
Content-Type: application/json

{
  "provider": "openai",
  "api_endpoint": "https://api.openai.com/v1/chat/completions",
  "api_key": "sk-...",
  "model_name": "gpt-4o"
}
```

#### 导出配置

```http
GET /llm-configs/export/all
```

#### 导入配置

```http
POST /llm-configs/import
Content-Type: application/json

[
  {
    "name": "配置1",
    "provider": "openai",
    ...
  }
]
```

### 角色配置 API

#### 获取所有角色

```http
GET /role-configs?active_only=true&category=developer
```

#### 获取预设模板

```http
GET /role-configs/presets
```

#### 创建角色

```http
POST /role-configs
Content-Type: application/json

{
  "name": "Python 专家",
  "system_prompt": "你是一位 Python 专家...",
  "category": "developer",
  "is_active": true
}
```

#### 其他操作

类似模型配置 API，支持 GET、PUT、DELETE、导入导出等操作。

## 常见问题

### Q: 如何切换默认模型？

A: 在模型管理界面，编辑想要设为默认的模型，勾选"设为默认模型"并保存。系统会自动取消其他模型的默认状态。

### Q: 预设角色可以删除吗？

A: 不可以。预设角色不能删除，但可以禁用（取消勾选"启用此角色"）。

### Q: 导入配置会覆盖现有配置吗？

A: 不会。导入会创建新的配置，不会影响现有配置。

### Q: API Key 是如何存储的？

A: API Key 存储在数据库中。导出时会被自动脱敏（显示为 `***REDACTED***`）。

### Q: 可以为不同用户配置不同的模型吗？

A: 当前版本中，模型和角色配置是全局的。多用户支持将在未来版本中添加。

### Q: 测试连接失败怎么办？

A: 请检查：
1. API 端点 URL 是否正确
2. API Key 是否有效
3. 网络连接是否正常
4. 模型名称是否正确

## 技术说明

### 数据库表结构

#### llm_config 表
- 存储 LLM 模型配置
- 支持多种 Provider
- 包含基础和高级参数

#### role_config 表
- 存储角色配置
- 区分预设和自定义角色
- 统计使用次数

### 文件结构

```
backend/
├── database/
│   ├── migrations/add_model_role_config.py  # 数据库迁移
│   └── models/system.py                      # 数据模型
├── modules/
│   └── agent/
│       ├── llm_schemas.py                    # 模型配置 Schema
│       ├── llm_service.py                    # 业务逻辑
│       ├── llm_router.py                     # API 路由
│       ├── role_schemas.py                   # 角色配置 Schema
│       ├── role_service.py                   # 业务逻辑
│       └── role_router.py                    # API 路由

renderer/
└── js/
    └── modules/
        └── agent/
            ├── ModelManagementPage.js        # 模型管理界面
            ├── RoleManagementPage.js         # 角色管理界面
            ├── AgentSidebar.js               # 侧边栏（新增按钮）
            ├── agentState.js                 # 状态管理
            └── agentHandlers.js              # 事件处理
```

## 更新日志

### v1.0.0 (2026-01-11)

**新增功能：**
- ✨ LLM 模型配置管理
- ✨ 角色配置管理
- ✨ 预设角色模板
- ✨ 配置导入导出
- ✨ 连接测试功能
- ✨ 动态选择器加载

**支持的 Provider:**
- OpenAI
- Claude (Anthropic)
- Gemini (Google)
- 类 OpenAI 自定义接口

---

**文档更新日期：** 2026-01-11
**版本：** 1.0.0
