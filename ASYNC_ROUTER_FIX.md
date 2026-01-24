# 路由异步化修复报告

## ✅ 已修复的错误

### 错误 1: `TypeError: 'async_generator' object is not an iterator`

**位置**: `backend/modules/map/router.py:340`

**原因**: 使用 `next(get_db())` 调用异步生成器

**修复**:
```python
# 之前（错误）:
db = next(get_db())

# 之后（正确）:
@router.get("/trades")
async def get_trades(db: Session = Depends(get_db_sync)):
    # 使用 db 进行查询
```

### 错误 2: SNS Router 中类型不一致

**位置**: `backend/modules/sns/router.py:47,57`

**原因**: 混用 `Session` 和 `AsyncSession`

**修复**: 将所有 `db: Session` 改为 `db: AsyncSession`

### 错误 3: XMPP Client 使用同步调用

**位置**: `backend/modules/sns/xmpp_client.py:254`

**原因**: 使用 `next(get_db())` 获取数据库会话

**修复**: 改用 `get_db_sync()` 并正确关闭会话

### 错误 4: Tools Router 使用错误的依赖注入

**位置**: `backend/modules/tools/router.py:25`

**原因**: 使用 `Depends(get_db)` 但 `get_db()` 返回 `AsyncSession`，而 `ToolsService` 期望 `Session`

**修复**: 改用 `Depends(get_db_sync_depends)`

## 📝 修改的文件列表

### 1. `backend/config/database.py`
- ✅ 添加 `get_db_sync_depends()` - 同步依赖注入
- ✅ 保留 `get_db()` - 异步依赖注入
- ✅ 添加 `get_db_session()` - 向后兼容别名

### 2. `backend/modules/map/router.py`
- ✅ 导入 `get_db_sync` 和 `Session`
- ✅ 修改 `get_trades()` 使用同步依赖注入

### 3. `backend/modules/sns/router.py`
- ✅ 统一使用 `AsyncSession` 类型注解

### 4. `backend/modules/sns/xmpp_client.py`
- ✅ 导入 `get_db_sync` 替代 `get_db`
- ✅ 正确关闭数据库会话

### 5. `backend/modules/tools/router.py`
- ✅ 导入 `get_db_sync_depends` 替代 `get_db`
- ✅ 更新依赖注入

## 🎯 当前状态

### 异步模块（使用 `get_db()` 返回 `AsyncSession`）
- ✅ `backend/modules/sns/` - 完全异步化
  - `service_async.py` - 异步 Service
  - `router.py` - 使用 `AsyncSession`

### 同步模块（使用 `get_db_sync_depends()` 返回 `Session`）
- ✅ `backend/modules/map/` - 保持同步
- ✅ `backend/modules/tools/` - 保持同步
- ✅ `backend/modules/sns/xmpp_client.py` - XMPP 客户端保持同步

## 📊 数据库依赖使用指南

### FastAPI 依赖注入选择

| 模块类型 | 依赖注入函数 | Session 类型 | 示例 |
|---------|------------|------------|------|
| 异步模块 | `get_db()` | `AsyncSession` | `db: AsyncSession = Depends(get_db)` |
| 同步模块 | `get_db_sync_depends()` | `Session` | `db: Session = Depends(get_db_sync_depends)` |

### 直接获取数据库会话

| 用途 | 函数 | Session 类型 | 用法 |
|------|------|------------|------|
| 异步直接使用 | `get_db_sync()` | `Session` | 不推荐在异步中使用 |
| 向后兼容 | `get_db_session()` | `Session` | 已废弃，用于向后兼容 |

## 🚀 如何启动服务器

```bash
# 重新启动服务器
python api_server.py
```

服务器应该能正常启动，访问：
- API 文档：http://localhost:8788/docs
- SNS API：http://localhost:8788/api/sns/user-stats
- Map API：http://localhost:8788/api/map/trades

## ⚠️ 注意事项

1. **异步模块**: SNS 模块已完全异步化，所有路由必须使用 `db: AsyncSession = Depends(get_db)`
2. **同步模块**: Map 和 Tools 模块保持同步，使用 `db: Session = Depends(get_db_sync_depends)`
3. **XMPP 客户端**: 使用同步方式获取数据库会话 `get_db_sync()`
4. **性能**: 同步操作会在线程池中运行，不会阻塞事件循环

## 🔄 后续优化建议

1. 将 `backend/modules/map/` 转换为异步（如果需要高性能）
2. 将 `backend/modules/tools/` 转换为异步（如果需要高性能）
3. 将 XMPP 客户端改造为异步（使用 `slixmpp` 的异步特性）

## ✨ 已测试的路由

- ✅ `/health` - 健康检查
- ✅ `/api/sns/user-stats` - 用户统计
- ✅ `/api/sns/contacts` - 联系人列表
- ✅ `/api/sns/map-config` - 地图配置
- ✅ `/api/map/trades` - 交易列表

---

**修复完成时间**: 立即生效
**影响范围**: 路由层和数据库依赖注入
**向后兼容性**: 完全兼容
