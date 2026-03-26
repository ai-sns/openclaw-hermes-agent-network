# Human Takeover 指令处理机制详解

## 一、总体语义（语义3：单条在途）

| 规则 | 描述 |
|------|------|
| **单条在途** | 同一时刻只允许一条 human 指令处于执行中。若上一条未完成，新指令直接被拒绝，提示 `Previous command is still running. Please wait.` |
| **指令优先，先收尾对话** | 收到 human 指令时，若引擎正在进行 communicate / buy / sell 对话，先向对方发送 `TERMINATE`，然后完整结束对话（stop_talk + 清理状态 + 取消延迟任务），再执行 human 指令。 |
| **退出 takeover 的接续** | 退出 human takeover 时：空闲则自动恢复 `process_activity`；不空闲（有 action / 对话 / LLM 在途）则让当前流程自然继续，不打断。 |

---

## 二、核心状态标记

| 标记 | 位置 | 含义 |
|------|------|------|
| `_human_command_inflight` | `ai_social_engine.py` (初始化于 `handle_human_instruction` L1307) | human 指令是否在途（从接受到动作/对话/工具完成） |
| `agent_replying_flag` | `agent_interaction_mixin.py` L104, L252 | LLM 请求是否在途 |
| `command_status` | `agent_interaction_mixin.py` L111, L268 | LLM 回复路由键（非空 = 有 LLM 请求在等待） |
| `active_conversation` | `communication_mixin.py` L504 | 当前对话状态 dict（None = 无对话） |
| `human_take_over` | `ai_social_engine.py` L100 | 是否处于 human takeover 模式 |

---

## 三、关键流程

### 3.1 Human 指令入口（takeover 模式）

```
用户发送指令
  │
  ▼
service_async.send_human_message()          ← L1006
  │
  ├─ is_busy_for_human_command()?           ← L1021 (service层提前检查)
  │   └─ True → 返回 busy 提示，不做任何 ensure/抢占
  │
  ▼
engine.human_message_received()             ← ai_social_engine.py L1059
  │
  ├─ is_busy_for_human_command()?           ← L1062 (engine层二次检查)
  │   └─ True → show_information("Previous command...") → return
  │
  ▼
engine.handle_human_instruction()           ← L1284
  │
  ├─ _human_command_inflight = True         ← L1307
  ├─ _terminate_active_conversation_for_priority_action()  ← L1312
  │   ├─ sendMessage("TERMINATE", ...)      ← L1166
  │   └─ end_active_conversation(resume_activity=False)    ← L1171
  │
  ▼
taskmng.process_task(action="process_human_instruction")   ← L1318
  │
  ▼
ask_agent_instruction_to_process_human_instruction()
  │ agent_replying_flag = True              ← agent_interaction_mixin.py L104
  │ command_status 被捕获                    ← L111
  ▼
LLM 返回
  │ agent_replying_flag = False             ← L252
  │ 检查 command_status 匹配               ← L269
  ▼
parse_agent_instruction_for_process_human_instruction()    ← map_task_manager.py L481
  │
  ▼
parse_agent_instruction_for_process_activity()             ← ai_social_engine.py L1242
  │ （执行动作：移动/对话/工具/服务等）
  │
  ▼
动作完成 → _maybe_finish_human_command_if_idle()          ← L1138
  │
  ├─ _is_idle_except_human_command_inflight()?
  │   └─ False → 不清理（对话/工具仍在进行）
  │   └─ True  → _human_command_inflight = False → _maybe_resume_process_activity_if_idle()
  ▼
```

### 3.2 Human 指令入口（非 takeover，submit_agent_instruction）

```
前端发送指令（如 talk_to_it 按钮）
  │
  ▼
service_async.submit_agent_instruction()    ← L1079
  │
  ├─ is_busy_for_human_command()?           ← (busy gate inline L1113)
  │   └─ True → 返回 busy 提示
  │
  ├─ _human_command_inflight = True         ← L1040 (service层)
  ├─ _ensure_engine_running_for_priority_action()
  ├─ _terminate_active_conversation_for_priority_action()  ← L1158
  │
  ▼
handle_parse_agent_instruction_for_process_activity()
  （后续同 3.1 的动作执行流程）
```

### 3.3 退出 Human Takeover

```
set_human_control_state(human_take_over=False)
  │
  ├─ is_idle_for_auto_activity()?           ← service_async.py L979
  │   ├─ True  → asyncio.create_task(process_activity)  ← L993
  │   └─ False → 跳过，让进行中流程自然结束  ← L980
  ▼
```

### 3.4 对话开始后释放 inflight 标记

```
human 指令触发对话（communicate/buy/sell）
  │
  ▼
start_active_conversation() → _touch_conversation_activity()
  │
  └─ _human_command_inflight = False        ← communication_mixin.py L75
     （对话已"接管"，允许下一条 human 指令打断对话）
```

---

## 四、忙/空闲判定

### `is_busy_for_human_command()` — ai_social_engine.py L1079

```python
def is_busy_for_human_command(self) -> bool:
    return bool(getattr(self, "_human_command_inflight", False))
```

只看 `_human_command_inflight`。**不**把 `active_conversation` 算作 busy（因为对话可以被 TERMINATE 打断）。

### `is_idle_for_auto_activity()` — ai_social_engine.py L1088

```python
def is_idle_for_auto_activity(self) -> bool:
    return (
        self._is_idle_except_human_command_inflight()
        and not self._human_command_inflight
    )
```

### `_is_idle_except_human_command_inflight()` — ai_social_engine.py L1096

```python
def _is_idle_except_human_command_inflight(self) -> bool:
    # 以下任一为 True 则非空闲:
    #   agent_replying_flag    (LLM 在等)
    #   command_status != ""   (有待路由的 LLM 请求)
    #   active_conversation    (有正在进行的对话)
    return True  # 全部为 False 时
```

---

## 五、防止 LLM 回复错路由

`ask_agent_and_get_instruction()` 在发送 LLM 请求时捕获当时的 `command_status` (L111)，
回复到达 `on_agent_return_instruction()` 时与当前 `command_status` 比较 (L269)：
- 匹配 → 正常处理
- 不匹配 → 丢弃回复（日志记录 "Dropping agent reply due to command_status mismatch"）

---

## 六、`_maybe_finish_human_command_if_idle()` 的调用点

当 human 指令触发的动作/对话/工具完成时，需要清理 `_human_command_inflight` 并可能恢复 `process_activity`。
以下位置都已接入此方法：

| 文件 | 调用点 | 场景 |
|------|--------|------|
| `ai_social_engine.py` L1002 | `parse_agent_instruction_for_process_activity()` 完成后 | 同步动作完成 |
| `communication_mixin.py` L530 | `end_active_conversation(resume_activity=True)` | 对话正常结束 |
| `communication_mixin.py` L582 | 对话启动失败 fallback | 账号无效等异常 |
| `tools_mixin.py` L195,231,258,283 | 工具/服务调用完成或失败 | web service 各分支 |
| `tools_mixin.py` L443 | `handle_service_called_result()` | 服务调用成功 |
| `trade_mixin.py` L664 | 卖方联系人耗尽 | 反骚扰规则触发 |
| `map_task_manager.py` L465 | plan summary 完成后 | 计划摘要恢复 |
| `map_task_manager.py` L750 | tool check 完成后 | 工具检查恢复 |

---

## 七、改动文件汇总

| 文件 | 改动概要 |
|------|----------|
| `backend/apps/sns/ai_social_engine.py` | 新增 `_human_command_inflight` 标记；`is_busy_for_human_command()`、`is_idle_for_auto_activity()`、`_is_idle_except_human_command_inflight()`、`_maybe_resume_process_activity_if_idle()`、`_maybe_finish_human_command_if_idle()`、`_terminate_active_conversation_for_priority_action()`、`_mark_human_command_complete()` 方法；`human_message_received()` 加 busy gate；`handle_human_instruction()` 设 inflight + terminate conversation；`_ensure_engine_ready_for_priority_action()` 移除对话终止（避免 busy 时误终止）；`parse_agent_instruction_for_process_activity()` 完成后检查 inflight |
| `backend/apps/sns/service_async.py` | `send_human_message()` 加 busy gate（ensure 之前）；`set_human_control_state()` 退出 takeover 时检查 `is_idle_for_auto_activity()`；`submit_agent_instruction()` 加 busy gate + inflight 标记 + terminate conversation |
| `backend/apps/sns/mixin/agent_interaction_mixin.py` | `ask_agent_and_get_instruction()` 入口设 `agent_replying_flag=True`；捕获 `command_status`；`on_agent_return_instruction()` 清 `agent_replying_flag` + 丢弃不匹配回复 |
| `backend/apps/sns/mixin/communication_mixin.py` | `end_active_conversation()` 取消 timeout/first_message 任务；resume_activity 分支检查 inflight；`_touch_conversation_activity()` 对话活动时清理 inflight |
| `backend/apps/sns/mixin/tools_mixin.py` | 所有 `process_activity` 调度点加 inflight guard |
| `backend/apps/sns/mixin/trade_mixin.py` | 卖方联系人耗尽时加 inflight guard |
| `backend/apps/sns/map_task_manager.py` | plan summary / tool check 完成后加 inflight guard |

---

## 八、回归验证要点

1. **快速连续发 2 条 human 指令**：第 2 条应立即被拒绝并提示 busy
2. **engine 正在对话中收到 human 指令**：对话先 TERMINATE + end，再执行指令
3. **退出 takeover（引擎忙）**：不触发 `process_activity`
4. **退出 takeover（引擎空闲）**：自动触发 `process_activity`
5. **human 指令触发对话后再发新指令**：允许（inflight 已清），新指令会先 TERMINATE 旧对话
6. **LLM 回复到达时 command_status 已变**：回复被丢弃，不会错路由
