#!/usr/bin/env python
"""
Offline tests for the XMPP A2A ad-hoc command subsystem.

These tests do NOT require a live XMPP server. They cover:

  1. Built-in command discovery
  2. User plugin discovery from aisns_backend/scripts/a2a_commands/
  3. Files starting with '_' are skipped
  4. Files without an AdhocCommand subclass produce nothing
  5. Duplicate node between plugin and builtin: builtin wins
  6. build_config_commands filters by source and required fields
  7. TemplateCommand.handle_submit variable substitution
  8. AdhocCommand metadata shape
  9. Hot-reload semantics: discover_commands picks up a freshly added
     plugin file even if previous discovery already ran in the process.
 10. Plugin file syntax errors do not crash discovery; other plugins still load.

Run:
  C:\\dev\\agi-ev\\ai-sns-el\\venv\\Scripts\\python.exe examples_and_tests\\test_a2a_commands_offline.py
"""
from __future__ import annotations

import asyncio
import logging
import os
import shutil
import sys
import tempfile
import textwrap
import traceback
from pathlib import Path
from types import SimpleNamespace
from typing import Any, Callable, Dict, List, Tuple

# ── Path bootstrap so we can import the backend package ─────────────────────
THIS_FILE = Path(__file__).resolve()
REPO_ROOT = THIS_FILE.parent.parent
BACKEND_ROOT = REPO_ROOT / "aisns_backend"
USER_PLUGIN_DIR = BACKEND_ROOT / "scripts" / "a2a_commands"

if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

# Quiet noisy library loggers when running tests
logging.basicConfig(level=logging.WARNING, format="%(levelname)s %(name)s: %(message)s")

# Imports under test
from runtime.apps.sns.a2a_commands import (  # noqa: E402
    discover_commands,
    build_config_commands,
    _USER_PLUGIN_DIR,
    _BACKEND_ROOT,
)
from runtime.apps.sns.a2a_commands.base import (  # noqa: E402
    AdhocCommand,
    TemplateCommand,
    CommandContext,
)


# ═══════════════════════════════════════════════════════════════════════════
#  Test infrastructure: tiny runner with PASS/FAIL output
# ═══════════════════════════════════════════════════════════════════════════
TESTS: List[Tuple[str, Callable[[], None]]] = []


def test(fn: Callable[[], None]) -> Callable[[], None]:
    TESTS.append((fn.__name__, fn))
    return fn


def assert_eq(actual: Any, expected: Any, msg: str = "") -> None:
    if actual != expected:
        raise AssertionError(
            f"assert_eq failed: {msg}\n  expected={expected!r}\n  actual={actual!r}"
        )


def assert_in(needle: Any, haystack: Any, msg: str = "") -> None:
    if needle not in haystack:
        raise AssertionError(
            f"assert_in failed: {msg}\n  needle={needle!r}\n  haystack={haystack!r}"
        )


def assert_true(cond: bool, msg: str = "") -> None:
    if not cond:
        raise AssertionError(f"assert_true failed: {msg}")


# ═══════════════════════════════════════════════════════════════════════════
#  Helpers: temporary plugin file management
# ═══════════════════════════════════════════════════════════════════════════
class _TempPluginFile:
    """Context manager that drops a .py file into the user plugin dir for a test."""

    def __init__(self, name: str, content: str):
        if not name.endswith(".py"):
            name += ".py"
        self.path = USER_PLUGIN_DIR / name
        self.content = content

    def __enter__(self) -> Path:
        USER_PLUGIN_DIR.mkdir(parents=True, exist_ok=True)
        self.path.write_text(self.content, encoding="utf-8")
        return self.path

    def __exit__(self, exc_type, exc, tb) -> None:
        try:
            if self.path.exists():
                self.path.unlink()
        except Exception:
            pass


# ═══════════════════════════════════════════════════════════════════════════
#  Mock XMPP form (mimics slixmpp xep_0004 form just enough)
# ═══════════════════════════════════════════════════════════════════════════
class MockField(dict):
    def get(self, key, default=None):
        return super().get(key, default)


class MockForm:
    """Tiny stand-in for slixmpp Form object."""

    def __init__(self, ftype: str = "form", title: str = ""):
        self.ftype = ftype
        self.title = title
        self._fields: Dict[str, MockField] = {}

    def addField(self, var: str, ftype: str = "text-single", label: str = "",
                 value: Any = "", **_kwargs) -> None:
        self._fields[var] = MockField(
            type=ftype, label=label,
            value="" if value is None else str(value),
        )

    def get_fields(self) -> Dict[str, MockField]:
        return self._fields


class MockXep0004:
    def make_form(self, ftype: str = "form", title: str = "") -> MockForm:
        return MockForm(ftype=ftype, title=title)


class MockXMPPClient:
    """Mimics ``client['xep_0004']`` access pattern."""

    def __init__(self) -> None:
        self._plugins = {"xep_0004": MockXep0004()}

    def __getitem__(self, key: str) -> Any:
        return self._plugins[key]


def make_ctx() -> CommandContext:
    return CommandContext(
        xmpp_client=MockXMPPClient(),
        a2a_manager=None,
        logger=logging.getLogger("test"),
    )


# ═══════════════════════════════════════════════════════════════════════════
#  Test cases
# ═══════════════════════════════════════════════════════════════════════════
@test
def test_user_plugin_dir_resolves_under_aisns_backend() -> None:
    """_USER_PLUGIN_DIR must point to aisns_backend/scripts/a2a_commands."""
    assert_eq(
        _USER_PLUGIN_DIR.resolve(),
        (BACKEND_ROOT / "scripts" / "a2a_commands").resolve(),
        "user plugin dir mismatch",
    )
    assert_true(_USER_PLUGIN_DIR.exists(), "user plugin dir must exist")
    assert_eq(
        _BACKEND_ROOT.resolve(), BACKEND_ROOT.resolve(),
        "_BACKEND_ROOT must match repo aisns_backend",
    )


@test
def test_builtin_commands_discovered() -> None:
    """At minimum, the two built-in commands must be discovered."""
    cmds = discover_commands()
    nodes = {c.node for c in cmds}
    assert_in("urn:xmpp:a2a:cmd:tasks", nodes, "tasks builtin missing")
    assert_in("urn:xmpp:a2a:cmd:exchange_business_card", nodes, "exchange builtin missing")
    for c in cmds:
        if c.node in {"urn:xmpp:a2a:cmd:tasks", "urn:xmpp:a2a:cmd:exchange_business_card"}:
            assert_eq(c._source, "builtin", f"{c.node} source must be builtin")


@test
def test_plugin_file_is_discovered_and_unloaded() -> None:
    """Adding a plugin file makes it appear in discover_commands; removing makes it disappear."""
    plugin_src = textwrap.dedent("""
        from runtime.apps.sns.a2a_commands.base import AdhocCommand

        class _AutoTestEcho(AdhocCommand):
            node = "urn:xmpp:a2a:cmd:_autotest_echo"
            name = "AutoTest Echo"
            description = "Returns the submitted form values verbatim."
            form_fields = [
                {"var": "msg", "type": "text-single", "label": "Message"},
            ]
    """).strip() + "\n"

    with _TempPluginFile("autotest_echo_cmd", plugin_src):
        cmds = discover_commands()
        nodes = [c.node for c in cmds]
        assert_in("urn:xmpp:a2a:cmd:_autotest_echo", nodes, "plugin not discovered")
        echo = next(c for c in cmds if c.node == "urn:xmpp:a2a:cmd:_autotest_echo")
        assert_eq(echo._source, "plugin", "plugin source tag wrong")
        assert_eq(echo.name, "AutoTest Echo", "plugin name wrong")
        meta = echo.get_metadata()
        assert_eq(meta["form_fields"][0]["var"], "msg", "plugin form_fields wrong")

    # After context exit: file removed → command should be gone
    cmds_after = discover_commands()
    nodes_after = [c.node for c in cmds_after]
    assert_true(
        "urn:xmpp:a2a:cmd:_autotest_echo" not in nodes_after,
        "plugin should be gone after removal",
    )


@test
def test_underscore_filename_is_skipped() -> None:
    """A plugin file whose name starts with '_' must not be loaded."""
    plugin_src = textwrap.dedent("""
        from runtime.apps.sns.a2a_commands.base import AdhocCommand

        class _SkippedCmd(AdhocCommand):
            node = "urn:xmpp:a2a:cmd:_should_be_skipped"
            name = "Skipped"
    """).strip() + "\n"

    # Filename starts with underscore (after stripping .py the stem starts with _)
    with _TempPluginFile("_hidden_plugin", plugin_src):
        cmds = discover_commands()
        nodes = [c.node for c in cmds]
        assert_true(
            "urn:xmpp:a2a:cmd:_should_be_skipped" not in nodes,
            "underscore-prefixed file must be skipped",
        )


@test
def test_plugin_with_no_command_class_is_noop() -> None:
    """A plain .py file without an AdhocCommand subclass loads quietly."""
    plugin_src = "VALUE = 42\n"
    with _TempPluginFile("autotest_no_cmd", plugin_src):
        # Discovery must not crash and must not add anything from this file
        cmds = discover_commands()
        # Sanity: builtins still present
        nodes = {c.node for c in cmds}
        assert_in("urn:xmpp:a2a:cmd:tasks", nodes,
                  "builtin still present despite junk file")


@test
def test_plugin_with_syntax_error_does_not_break_discovery() -> None:
    """A broken plugin must not prevent other plugins / builtins from loading."""
    broken_src = "this is not python(((\n"
    good_src = textwrap.dedent("""
        from runtime.apps.sns.a2a_commands.base import AdhocCommand

        class _AutoTestGood(AdhocCommand):
            node = "urn:xmpp:a2a:cmd:_autotest_good"
            name = "AutoTest Good"
    """).strip() + "\n"

    with _TempPluginFile("autotest_broken_cmd", broken_src), \
         _TempPluginFile("autotest_good_cmd", good_src):
        cmds = discover_commands()
        nodes = {c.node for c in cmds}
        assert_in("urn:xmpp:a2a:cmd:tasks", nodes, "builtin must still load")
        assert_in("urn:xmpp:a2a:cmd:_autotest_good", nodes,
                  "good plugin must still load despite sibling syntax error")


@test
def test_duplicate_node_between_plugin_and_builtin_keeps_builtin() -> None:
    """If a plugin reuses a builtin node, builtin wins (plugin is dropped)."""
    plugin_src = textwrap.dedent("""
        from runtime.apps.sns.a2a_commands.base import AdhocCommand

        class _DupBuiltin(AdhocCommand):
            node = "urn:xmpp:a2a:cmd:tasks"
            name = "Duplicate Tasks"
    """).strip() + "\n"

    with _TempPluginFile("autotest_dup_cmd", plugin_src):
        cmds = discover_commands()
        tasks = [c for c in cmds if c.node == "urn:xmpp:a2a:cmd:tasks"]
        assert_eq(len(tasks), 1, "must keep exactly one tasks command")
        assert_eq(tasks[0]._source, "builtin", "builtin must win over plugin")


@test
def test_build_config_commands_filters_source_and_missing_fields() -> None:
    """Only entries with source=='config' AND non-empty node+name produce a TemplateCommand."""
    raw = [
        # 1. Valid config command
        {
            "source": "config",
            "node": "urn:xmpp:a2a:cmd:_cfg_ok",
            "name": "Config OK",
            "description": "ok",
            "form_fields": [{"var": "x", "type": "text-single", "label": "X"}],
            "response_template": {"echo": "{{x}}"},
        },
        # 2. Wrong source
        {
            "source": "plugin",
            "node": "urn:xmpp:a2a:cmd:_cfg_skip_source",
            "name": "Should be skipped",
        },
        # 3. Missing node
        {
            "source": "config",
            "name": "no node",
        },
        # 4. Missing name
        {
            "source": "config",
            "node": "urn:xmpp:a2a:cmd:_cfg_no_name",
        },
        # 5. Garbage entry
        "not a dict",
    ]
    cmds = build_config_commands(raw)
    assert_eq(len(cmds), 1, "only one valid entry should yield a command")
    cmd = cmds[0]
    assert_true(isinstance(cmd, TemplateCommand), "must be TemplateCommand")
    assert_eq(cmd.node, "urn:xmpp:a2a:cmd:_cfg_ok", "node mismatch")
    assert_eq(cmd._source, "config", "source mismatch")


@test
def test_template_command_substitution() -> None:
    """TemplateCommand.handle_submit replaces {{var}} placeholders with submitted values."""
    cmd = TemplateCommand(
        node="urn:xmpp:a2a:cmd:_tpl_test",
        name="Tpl Test",
        form_fields=[{"var": "name", "type": "text-single", "label": "Name"}],
        response_template={"message": "Hello, {{name}}!", "static": "literal"},
        description="",
    )

    # Build a fake submitted form
    payload = MockForm(ftype="submit")
    payload.addField(var="name", ftype="text-single", value="Alice")

    session: dict = {}
    asyncio.run(cmd.handle_submit(payload, session, make_ctx()))

    out: MockForm = session["payload"]
    fields = out.get_fields()
    assert_eq(fields["message"]["value"], "Hello, Alice!", "substitution failed")
    assert_eq(fields["static"]["value"], "literal", "static template wrong")
    assert_eq(session["has_next"], False, "has_next must be False after submit")


@test
def test_template_command_empty_template_echoes_values() -> None:
    """An empty response_template echoes the submitted values."""
    cmd = TemplateCommand(
        node="urn:xmpp:a2a:cmd:_tpl_echo",
        name="Tpl Echo",
        form_fields=[{"var": "x", "type": "text-single", "label": "X"}],
        response_template={},
        description="",
    )
    payload = MockForm(ftype="submit")
    payload.addField(var="x", ftype="text-single", value="42")
    session: dict = {}
    asyncio.run(cmd.handle_submit(payload, session, make_ctx()))
    fields = session["payload"].get_fields()
    assert_eq(fields["x"]["value"], "42", "echo should pass value through")


@test
def test_default_handle_execute_builds_form_from_fields() -> None:
    """AdhocCommand.handle_execute should build a form from form_fields."""

    class _LocalCmd(AdhocCommand):
        node = "urn:xmpp:a2a:cmd:_local_cmd"
        name = "Local"
        form_fields = [
            {"var": "city", "type": "text-single", "label": "City"},
            {"var": "qty", "type": "text-single", "label": "Qty", "default": "1"},
        ]

    cmd = _LocalCmd()
    session: dict = {}
    asyncio.run(cmd.handle_execute(iq=None, session=session, ctx=make_ctx()))
    form: MockForm = session["payload"]
    fields = form.get_fields()
    assert_in("city", fields, "city field missing")
    assert_in("qty", fields, "qty field missing")
    assert_eq(fields["qty"]["value"], "1", "default value wrong")
    assert_eq(session["has_next"], True, "execute must set has_next True")
    assert_eq(session["allow_complete"], True, "execute must allow complete")


@test
def test_metadata_includes_source_and_form_fields() -> None:
    cmd = TemplateCommand(
        node="urn:xmpp:a2a:cmd:_meta_test",
        name="Meta",
        form_fields=[{"var": "x", "type": "text-single", "label": "X"}],
        response_template={"y": "{{x}}"},
        description="d",
    )
    meta = cmd.get_metadata()
    assert_eq(meta["node"], "urn:xmpp:a2a:cmd:_meta_test")
    assert_eq(meta["name"], "Meta")
    assert_eq(meta["description"], "d")
    assert_eq(meta["source"], "config")
    assert_eq(meta["form_fields"][0]["var"], "x")


# ═══════════════════════════════════════════════════════════════════════════
#  Additional tests for multi-resource fallback and tool_executor fix
# ═══════════════════════════════════════════════════════════════════════════
@test
def test_get_all_resources_returns_sorted_by_priority() -> None:
    """_get_all_resources must return full JIDs sorted by priority descending."""
    from runtime.apps.sns.xmpp_a2a import XMPPA2AManager

    # Build a minimal mock client with roster data
    class MockResources:
        def __init__(self, data):
            self._data = data
        def items(self):
            return self._data.items()

    class MockEntry:
        def __init__(self, resources):
            self.resources = resources

    class MockRoster:
        def __init__(self, entries):
            self._entries = entries
        def has_jid(self, jid):
            return jid in self._entries
        def __getitem__(self, jid):
            return self._entries[jid]

    class MockClient:
        def __init__(self):
            # Simulate two resources: one priority 5, one priority 0
            self.client_roster = MockRoster({
                "bob@example.com": MockEntry({
                    "Monal-iOS.abc": {"priority": 5},
                    "1234567890": {"priority": 0},
                })
            })

    mgr = XMPPA2AManager.__new__(XMPPA2AManager)
    mgr.client = MockClient()

    result = mgr._get_all_resources("bob@example.com")
    assert_eq(len(result), 2, "must return 2 resources")
    # Monal has higher priority → comes first
    assert_eq(result[0], "bob@example.com/Monal-iOS.abc", "highest priority first")
    assert_eq(result[1], "bob@example.com/1234567890", "lower priority second")

    # Test with already-full JID
    result2 = mgr._get_all_resources("bob@example.com/explicit")
    assert_eq(result2, ["bob@example.com/explicit"], "full JID returned as-is")

    # Test with unknown JID
    result3 = mgr._get_all_resources("unknown@example.com")
    assert_eq(result3, [], "unknown JID returns empty")


@test
def test_tool_executor_has_path_import() -> None:
    """tool_executor.py must have 'from pathlib import Path' so get_python_executable works."""
    from runtime.modules.tools.tool_executor import Path as ToolPath
    from pathlib import Path as RealPath
    assert_true(ToolPath is RealPath, "tool_executor.Path must be pathlib.Path")


@test
def test_call_adhoc_command_has_timeout_per_resource_param() -> None:
    """call_adhoc_command must accept timeout_per_resource for per-resource timeout control."""
    import inspect
    from runtime.apps.sns.xmpp_a2a import XMPPA2AManager

    sig = inspect.signature(XMPPA2AManager.call_adhoc_command)
    params = list(sig.parameters.keys())
    assert_true("timeout_per_resource" in params,
                "call_adhoc_command must have timeout_per_resource parameter")
    default = sig.parameters["timeout_per_resource"].default
    assert_true(isinstance(default, (int, float)) and default > 0,
                f"timeout_per_resource default must be a positive number, got {default}")
    assert_true(default <= 30,
                f"timeout_per_resource default should be <=30s for fast fallback, got {default}")


# ═══════════════════════════════════════════════════════════════════════════
#  Main runner
# ═══════════════════════════════════════════════════════════════════════════
def main() -> int:
    print(f"Backend root: {BACKEND_ROOT}")
    print(f"User plugin dir: {USER_PLUGIN_DIR} (exists={USER_PLUGIN_DIR.exists()})")
    print(f"Running {len(TESTS)} test(s)\n")

    passed = 0
    failed: List[Tuple[str, str]] = []
    for name, fn in TESTS:
        try:
            fn()
        except AssertionError as e:
            failed.append((name, str(e)))
            print(f"  FAIL  {name}")
            continue
        except Exception:
            failed.append((name, traceback.format_exc()))
            print(f"  ERROR {name}")
            continue
        passed += 1
        print(f"  PASS  {name}")

    print()
    print(f"Result: {passed}/{len(TESTS)} passed, {len(failed)} failed")
    if failed:
        print("\nFailures:")
        for name, msg in failed:
            print(f"\n--- {name} ---")
            print(msg)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
