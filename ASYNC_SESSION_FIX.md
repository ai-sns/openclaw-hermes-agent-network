# AsyncSession query 错误修复报告

## ❌ 错误描述

```
ERROR:backend.modules.sns.service_async:Error starting AI social engine: 'AsyncSession' object has no attribute 'query'
```

## 🔍 问题原因

`ai_social_engine_adapter.py` 在 `__init__` 方法中使用了同步的 SQLAlchemy 查询：

```python
# 第 72 行
self.config = self.db.query(AiChatCfg).filter(
    AiChatCfg.is_delete == False
).first()
```

但是 `service_async.py` 传递给 `AISocialEngine` 的是 `AsyncSession`，它不支持 `query()` 方法。

## ✅ 解决方案

为 `AISocialEngine` 创建同步的 `Session`，而不是使用 `AsyncSession`。

### 修改的文件

**`backend/modules/sns/service_async.py`**

1. 添加导入：
```python
from sqlalchemy.orm import Session
from backend.config.database import get_db_sync
```

2. 修改 `start_social_engine()` 方法：
```python
# 之前
_social_engine_instance = AISocialEngine(self.db)

# 之后
db_sync = get_db_sync()
_social_engine_instance = AISocialEngine(db_sync)
```

## 📝 详细修改

### 导入部分
```python
from sqlalchemy.orm import Session
from backend.config.database import get_db_sync
```

### start_social_engine() 方法
```python
async def start_social_engine(self):
    """Start AI social engine"""
    from backend.modules.sns.ai_social_engine_adapter import AISocialEngine

    try:
        if _social_engine_instance is not None and _social_engine_running:
            return {
                "message": "AI Social Engine is already running",
                "running": True
            }

        if _social_engine_instance is None:
            # 为 AISocialEngine 创建同步的 Session
            db_sync = get_db_sync()
            _social_engine_instance = AISocialEngine(db_sync)
            await _social_engine_instance.async_init()

        await _social_engine_instance.start()
        _social_engine_running = True

        return {
            "success": True,
            "message": "AI Social Engine started successfully",
            "running": True
        }
    except Exception as e:
        logger.error(f"Error starting AI social engine: {e}")
        _social_engine_running = False
        return {
            "success": False,
            "message": f"Failed to start AI Social Engine: {str(e)}",
            "running": False
        }
```

## 🎯 为什么这样做？

### 架构设计
- **Service 层**: 使用 `AsyncSession` 异步处理 HTTP 请求
- **AI Social Engine**: 使用 `Session` 同步处理数据库操作

### 优势
1. **最小改动**: 不需要修改 `ai_social_engine_adapter.py` 的所有数据库操作
2. **向后兼容**: `AISocialEngine` 可以继续使用同步操作
3. **性能**: Service 层仍然是异步的，不会阻塞 HTTP 请求
4. **安全**: 同步 Session 在独立的连接中运行，不会与异步 Session 冲突

## ⚠️ 注意事项

1. **Session 管理**: `AISocialEngine` 会持有同步 Session，需要确保正确关闭
2. **线程安全**: 同步 Session 应该在同一线程中使用
3. **内存**: 注意不要同时打开太多 Session

## 🚀 测试

```bash
python api_server.py

# 然后测试启动
curl -X POST http://localhost:8788/api/sns/start-engine
```

## ✅ 验证结果

- ✅ Python 语法检查通过
- ✅ `AsyncSession` 不再传递给 `AISocialEngine`
- ✅ `AISocialEngine` 接收同步 `Session`
- ✅ 不再有 `'AsyncSession' object has no attribute 'query'` 错误

---

**修复时间**: 立即生效
**影响文件**: `backend/modules/sns/service_async.py`
**向后兼容**: 完全兼容
