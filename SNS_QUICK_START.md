# SNS Module - Quick Start Guide

## 启动系统

### 1. 启动后端服务器
```bash
cd /mnt/c/dev/agi-ev/ai-sns-el
python api_server.py
```

服务器将自动:
- 加载SNS模块
- 连接XMPP服务器
- 启动API端点

### 2. 启动Electron前端
```bash
npm start
```

## 配置XMPP账户

### 数据库配置
在 `db/db.sqlite` 的 `aichat_cfg` 表中配置第一条记录:

```sql
UPDATE aichat_cfg SET
    account = 'your_jid@xmpp.server.com',
    password = 'your_password',
    serveraddress = 'xmpp.server.com',  -- 可选
    port = 5222                          -- 可选
WHERE id = 1;
```

### 用户统计数据
同样在 `aichat_cfg` 表中设置:

```sql
UPDATE aichat_cfg SET
    level = 3,
    credit = 100,
    money = 10996.61,
    life_point = 125,
    iq_point = 70,
    energy_point = 150,
    move_point = 187.5,
    exp_point = 30
WHERE id = 1;
```

## 使用功能

### 查看用户统计
1. 打开应用
2. 点击左侧导航栏的 "SNS" 按钮
3. 侧边栏顶部显示:
   - 横向柱状图: Level, Credit, Money
   - 雷达图: Life, IQ, Energy, Move, Exp

### 查看联系人
1. 在SNS页面侧边栏
2. "Contact List" 下方显示所有好友
3. 好友来自 `ai_friend` 表

### 聊天功能
1. 点击联系人列表中的任意好友
2. 底部弹出聊天窗口
3. 可以:
   - 查看聊天历史
   - 发送文本消息
   - 发送文件 (点击📎按钮)
   - 关闭聊天窗口 (点击×按钮)

## API端点

### 获取用户统计
```
GET http://localhost:8788/api/sns/user-stats
```

### 获取联系人列表
```
GET http://localhost:8788/api/sns/contacts
```

### 获取聊天历史
```
GET http://localhost:8788/api/sns/chat-history/{account}?limit=50
```

### 发送消息
```
POST http://localhost:8788/api/sns/send-message
Content-Type: application/json

{
    "to_account": "friend@xmpp.server.com",
    "content": "Hello!"
}
```

### 发送文件
```
POST http://localhost:8788/api/sns/send-file
Content-Type: multipart/form-data

file: [binary file data]
to_account: friend@xmpp.server.com
```

## 故障排除

### XMPP连接失败
检查:
1. `aichat_cfg` 表中的 account 和 password 是否正确
2. XMPP服务器是否可访问
3. 查看后端日志: `⚠ Failed to start XMPP client: ...`

### 联系人列表为空
检查:
1. `ai_friend` 表中是否有数据
2. `owner_sns_account` 是否匹配当前用户的 account
3. `is_delete` 字段是否为 False

### 聊天历史不显示
检查:
1. `ai_chat_messages` 表中是否有数据
2. `owner_account` 和 `friend_account` 是否正确
3. `is_delete` 字段是否为 False

### 图表不显示
检查:
1. 浏览器控制台是否有JavaScript错误
2. `sns.css` 是否正确加载
3. Canvas元素是否正确渲染

## 日志查看

### 后端日志
```bash
# 查看XMPP连接状态
grep "XMPP" api_server.log

# 查看SNS模块加载
grep "SNS Module" api_server.log
```

### 前端日志
打开浏览器开发者工具 (F12):
- Console标签: 查看JavaScript日志
- Network标签: 查看API请求

## 数据库查询

### 查看当前用户配置
```sql
SELECT account, nickname, level, credit, money,
       life_point, iq_point, energy_point, move_point, exp_point
FROM aichat_cfg
WHERE is_delete = 0
LIMIT 1;
```

### 查看联系人
```sql
SELECT account, nick_name, groups, subscription, new_message_flag
FROM ai_friend
WHERE is_delete = 0
ORDER BY nick_name;
```

### 查看聊天记录
```sql
SELECT flag, content, owner_account, friend_account, create_time
FROM ai_chat_messages
WHERE is_delete = 0
ORDER BY create_time DESC
LIMIT 50;
```

## 开发调试

### 修改前端代码
1. 编辑 `renderer/js/modules/sns/` 下的文件
2. 刷新Electron窗口 (Ctrl+R 或 Cmd+R)

### 修改后端代码
1. 编辑 `backend/modules/sns/` 下的文件
2. 重启 `api_server.py`

### 修改样式
1. 编辑 `renderer/css/sns.css`
2. 刷新Electron窗口

## 性能优化建议

1. **联系人列表**: 如果联系人很多，考虑添加分页或虚拟滚动
2. **聊天历史**: 默认只加载最近50条消息，可根据需要调整
3. **XMPP心跳**: 默认30秒，可根据网络情况调整
4. **图表渲染**: 使用Canvas而非SVG以提高性能

## 安全注意事项

1. **密码存储**: 当前密码明文存储在数据库中，生产环境应使用加密
2. **XMPP连接**: 建议使用SSL/TLS连接
3. **API认证**: 当前API无认证，生产环境应添加认证机制
4. **XSS防护**: 消息内容应进行HTML转义

## 联系支持

如有问题，请查看:
- 完整文档: `SNS_OPTIMIZATION_SUMMARY.md`
- 代码注释: 各模块文件中的详细注释
- 日志文件: 后端和前端的错误日志
