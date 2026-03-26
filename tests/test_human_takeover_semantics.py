"""
Smoke tests for human takeover command handling semantics.

Tests the core state logic WITHOUT requiring a running server, database,
or LLM. Uses monkeypatching to isolate the state machine.

Run:  python -m pytest tests/test_human_takeover_semantics.py -v
  or: python tests/test_human_takeover_semantics.py
"""
import sys
import os
import types
import asyncio
import time

# ---- minimal path setup so imports resolve ----
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)


# ---------------------------------------------------------------------------
# Helpers: build a lightweight stub engine that has the key mixins' methods
# without needing DB / XMPP / agent / websocket etc.
# ---------------------------------------------------------------------------

class _FakeTaskmngJs:
    def __init__(self):
        self.last_info = None
    def show_information(self, msg):
        self.last_info = msg


class _FakeTaskmng:
    def __init__(self):
        self.last_call = None
    def process_task(self, **kw):
        self.last_call = kw
    def add_process_info_to_list(self, msg):
        pass
    def get_current_objective(self):
        return ""


class _StubEngine:
    """
    Minimal object that has only the state-machine methods we need to test,
    copied from the real AISocialEngine via import.  We avoid instantiating
    the real class because its __init__ requires DB + XMPP + agent_manager.
    """
    def __init__(self):
        self.started_flag = True
        self.map_task_status = "started"
        self.human_take_over = False
        self.human_talk_type = 0
        self.agent_replying_flag = False
        self.command_status = ""
        self.active_conversation = None
        self._human_command_inflight = False
        self._conversation_timeout_task = None
        self._conversation_first_message_task = None
        self.stopping_ai_process_flag = False
        self.current_talk_people = None
        self.current_talk_history = []
        self.talk_type = ""
        self._conversation_last_activity_ts = 0.0
        self.taskmng_js = _FakeTaskmngJs()
        self.taskmng = _FakeTaskmng()
        self._sent_messages = []  # track sendMessage calls

    def _now_ts(self):
        return float(time.time())

    def _ensure_conversation_timeout_task(self):
        return

    # ---- patch in real methods from ai_social_engine ----
    # We import the unbound functions and bind them to our stub.


def _bind_methods(engine):
    """
    Import and bind the real methods from the source modules onto our stub.
    This lets us test the actual logic without constructing the full class.
    """
    # We need to import the modules, not the class (to avoid __init__ side effects).
    from backend.apps.sns import ai_social_engine as _eng_mod
    from backend.apps.sns.mixin import communication_mixin as _comm_mod

    _EngCls = _eng_mod.AISocialEngine
    _CommCls = _comm_mod.CommunicationMixin

    # Methods from AISocialEngine
    for name in [
        "is_busy_for_human_command",
        "is_idle_for_auto_activity",
        "_is_idle_except_human_command_inflight",
        "_maybe_resume_process_activity_if_idle",
        "_maybe_finish_human_command_if_idle",
        "_terminate_active_conversation_for_priority_action",
        "_mark_human_command_complete",
        "human_message_received",
        "handle_human_instruction",
    ]:
        fn = getattr(_EngCls, name, None)
        if fn is not None:
            setattr(engine, name, types.MethodType(fn, engine))

    # Methods from CommunicationMixin
    for name in [
        "end_active_conversation",
        "_touch_conversation_activity",
        "_get_active_account",
    ]:
        fn = getattr(_CommCls, name, None)
        if fn is not None:
            setattr(engine, name, types.MethodType(fn, engine))

    # Stub methods that the real code calls but we don't need
    def _noop(*a, **kw):
        pass

    def _sendMessage(self_or_msg, *a, **kw):
        # Capture sent messages for assertions
        # handle both bound and unbound calls
        if isinstance(self_or_msg, str):
            engine._sent_messages.append(self_or_msg)
        elif len(a) > 0:
            engine._sent_messages.append(a[0] if len(a) > 0 else self_or_msg)

    engine.sendMessage = lambda msg, *a, **kw: engine._sent_messages.append(msg)
    engine.send_msg_to_map = _noop
    engine.show_status_on_map = _noop
    engine.show_alert_on_map = _noop
    engine.write_on_going_process_to_pane = _noop
    engine.write_thinking_process_to_pane = _noop
    engine.write_task_process_to_pane = _noop

    # memory_manager stub
    engine.memory_manager = types.SimpleNamespace(capture_async=_noop)


# ===========================================================================
# Tests
# ===========================================================================

def _make_engine():
    e = _StubEngine()
    _bind_methods(e)
    return e


def test_busy_gate_rejects_when_inflight():
    """When _human_command_inflight=True, is_busy_for_human_command() returns True."""
    e = _make_engine()
    e._human_command_inflight = False
    assert e.is_busy_for_human_command() is False

    e._human_command_inflight = True
    assert e.is_busy_for_human_command() is True


def test_idle_for_auto_activity():
    """is_idle_for_auto_activity requires all flags clear."""
    e = _make_engine()
    # All clear → idle
    assert e.is_idle_for_auto_activity() is True

    # inflight → not idle
    e._human_command_inflight = True
    assert e.is_idle_for_auto_activity() is False
    e._human_command_inflight = False

    # agent replying → not idle
    e.agent_replying_flag = True
    assert e.is_idle_for_auto_activity() is False
    e.agent_replying_flag = False

    # command_status set → not idle
    e.command_status = "something"
    assert e.is_idle_for_auto_activity() is False
    e.command_status = ""

    # active conversation → not idle
    e.active_conversation = {"account": "x"}
    assert e.is_idle_for_auto_activity() is False
    e.active_conversation = None

    # Back to idle
    assert e.is_idle_for_auto_activity() is True


def test_is_idle_except_inflight():
    """_is_idle_except_human_command_inflight ignores _human_command_inflight."""
    e = _make_engine()
    e._human_command_inflight = True  # should be ignored
    assert e._is_idle_except_human_command_inflight() is True

    e.active_conversation = {"account": "y"}
    assert e._is_idle_except_human_command_inflight() is False


def test_terminate_active_conversation_sends_terminate():
    """_terminate_active_conversation_for_priority_action sends TERMINATE then clears conversation."""
    e = _make_engine()
    e.active_conversation = {
        "account": "bob@example.com",
        "nick_name": "Bob",
        "talk_type": "communication",
    }

    e._terminate_active_conversation_for_priority_action()

    # Should have sent TERMINATE
    assert "TERMINATE" in e._sent_messages
    # Conversation should be cleared
    assert e.active_conversation is None


def test_terminate_noop_when_no_conversation():
    """_terminate_active_conversation_for_priority_action is a no-op when no active conversation."""
    e = _make_engine()
    e.active_conversation = None
    e._terminate_active_conversation_for_priority_action()
    assert len(e._sent_messages) == 0


def test_maybe_finish_clears_inflight_when_idle():
    """_maybe_finish_human_command_if_idle clears inflight and attempts resume."""
    e = _make_engine()
    e._human_command_inflight = True
    e.human_take_over = False  # so resume would be attempted

    e._maybe_finish_human_command_if_idle(ask_content="test")

    assert e._human_command_inflight is False


def test_maybe_finish_does_not_clear_when_busy():
    """_maybe_finish_human_command_if_idle does NOT clear inflight when engine is busy."""
    e = _make_engine()
    e._human_command_inflight = True
    e.agent_replying_flag = True  # engine is busy (LLM pending)

    e._maybe_finish_human_command_if_idle(ask_content="")

    # inflight should still be True because engine is not idle
    assert e._human_command_inflight is True


def test_maybe_resume_skips_in_takeover():
    """_maybe_resume_process_activity_if_idle does nothing during takeover."""
    e = _make_engine()
    e.human_take_over = True
    e.taskmng.last_call = None

    e._maybe_resume_process_activity_if_idle(ask_content="x")

    assert e.taskmng.last_call is None  # no process_task scheduled


def test_touch_conversation_clears_inflight():
    """When a conversation starts (touch), _human_command_inflight is cleared."""
    e = _make_engine()
    e._human_command_inflight = True
    e.active_conversation = {"account": "alice@example.com"}

    e._touch_conversation_activity("alice@example.com")

    assert e._human_command_inflight is False


def test_human_message_received_busy_prompt():
    """human_message_received shows busy prompt and returns when busy."""
    e = _make_engine()
    e.human_take_over = True
    e.human_talk_type = 0
    e._human_command_inflight = True

    # Should not call handle_human_instruction (we'd get an error if it did
    # because our stub doesn't have all the task machinery)
    e.human_message_received("do something")

    assert "Previous command" in (e.taskmng_js.last_info or "")


# ===========================================================================
# Runner
# ===========================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("Human Takeover Command Handling — Smoke Tests")
    print("=" * 60)

    tests = [
        test_busy_gate_rejects_when_inflight,
        test_idle_for_auto_activity,
        test_is_idle_except_inflight,
        test_terminate_active_conversation_sends_terminate,
        test_terminate_noop_when_no_conversation,
        test_maybe_finish_clears_inflight_when_idle,
        test_maybe_finish_does_not_clear_when_busy,
        test_maybe_resume_skips_in_takeover,
        test_touch_conversation_clears_inflight,
        test_human_message_received_busy_prompt,
    ]

    passed = 0
    failed = 0
    errors = []

    for t in tests:
        name = t.__name__
        try:
            t()
            print(f"  PASS  {name}")
            passed += 1
        except Exception as exc:
            print(f"  FAIL  {name}: {exc}")
            failed += 1
            errors.append((name, exc))

    print("-" * 60)
    print(f"Results: {passed} passed, {failed} failed, {passed + failed} total")

    if errors:
        print("\nFailures:")
        for name, exc in errors:
            print(f"  {name}: {exc}")
        sys.exit(1)
    else:
        print("\nAll tests passed!")
        sys.exit(0)
