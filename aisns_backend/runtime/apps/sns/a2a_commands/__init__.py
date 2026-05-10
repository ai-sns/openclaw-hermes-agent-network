"""
A2A Commands Registry — Auto-discovery of ad-hoc command plugins.

Scans:
1. Built-in commands in this package (a2a_commands/*.py)
2. User-defined plugins in aisns_backend/scripts/a2a_commands/*.py
3. Config-type commands from aisns_cfg.memo.a2a_config (DB)

Provides discover_commands() which returns all AdhocCommand instances.
"""
import importlib
import importlib.util
import inspect
import logging
import os
import sys
from pathlib import Path
from typing import List, Optional, Dict, Any

from runtime.apps.sns.a2a_commands.base import AdhocCommand, TemplateCommand

logger = logging.getLogger(__name__)

# Directory containing built-in command modules
_BUILTIN_DIR = Path(__file__).resolve().parent

# Backend root (aisns_backend)
_BACKEND_ROOT = _BUILTIN_DIR.parent.parent.parent.parent

# User plugin directory
_USER_PLUGIN_DIR = _BACKEND_ROOT / "scripts" / "a2a_commands"


def discover_commands(user_dir: Optional[str] = None) -> List[AdhocCommand]:
    """
    Discover all available ad-hoc command plugin instances.

    Args:
        user_dir: Optional override for user plugin directory path.

    Returns:
        List of AdhocCommand instances (builtin + plugin).
        Does NOT include config-type commands (those are loaded separately from DB).
    """
    commands: List[AdhocCommand] = []
    seen_nodes: set = set()

    # 1. Scan built-in modules
    builtin_cmds = _scan_directory(_BUILTIN_DIR, source="builtin")
    for cmd in builtin_cmds:
        if cmd.node and cmd.node not in seen_nodes:
            seen_nodes.add(cmd.node)
            commands.append(cmd)

    # 2. Scan user plugin directory
    plugin_dir = Path(user_dir) if user_dir else _USER_PLUGIN_DIR
    if plugin_dir.exists() and plugin_dir.is_dir():
        plugin_cmds = _scan_directory(plugin_dir, source="plugin")
        for cmd in plugin_cmds:
            if cmd.node and cmd.node not in seen_nodes:
                seen_nodes.add(cmd.node)
                commands.append(cmd)
            elif cmd.node in seen_nodes:
                logger.warning(
                    "Plugin command node %s conflicts with existing command, skipping",
                    cmd.node,
                )

    logger.info(
        "Discovered %d ad-hoc commands (builtin=%d, plugin=%d)",
        len(commands),
        sum(1 for c in commands if c._source == "builtin"),
        sum(1 for c in commands if c._source == "plugin"),
    )
    return commands


def build_config_commands(adhoc_commands_config: List[Dict[str, Any]]) -> List[AdhocCommand]:
    """
    Build TemplateCommand instances from config-type command definitions.

    Args:
        adhoc_commands_config: List of command defs from aisns_cfg.memo.a2a_config.adhoc_commands
                              (only entries with source=="config")

    Returns:
        List of TemplateCommand instances.
    """
    commands: List[AdhocCommand] = []
    for cmd_def in adhoc_commands_config:
        if not isinstance(cmd_def, dict):
            continue
        source = cmd_def.get("source", "")
        if source != "config":
            continue

        node = cmd_def.get("node", "").strip()
        name = cmd_def.get("name", "").strip()
        if not node or not name:
            logger.warning("Skipping config command with missing node or name: %s", cmd_def)
            continue

        cmd = TemplateCommand(
            node=node,
            name=name,
            form_fields=cmd_def.get("form_fields", []),
            response_template=cmd_def.get("response_template"),
            description=cmd_def.get("description", ""),
        )
        commands.append(cmd)

    return commands


def _scan_directory(directory: Path, source: str = "builtin") -> List[AdhocCommand]:
    """
    Scan a directory for Python modules containing AdhocCommand subclasses.

    Skips:
    - __init__.py
    - base.py
    - Files starting with underscore

    Args:
        directory: Path to scan
        source: Source tag to assign ("builtin" or "plugin")

    Returns:
        List of instantiated AdhocCommand subclasses found.
    """
    commands: List[AdhocCommand] = []
    skip_names = {"__init__", "base"}

    for py_file in directory.glob("*.py"):
        module_name = py_file.stem
        if module_name in skip_names or module_name.startswith("_"):
            continue

        try:
            # For built-in modules, use package-relative import
            if source == "builtin":
                full_module_name = f"runtime.apps.sns.a2a_commands.{module_name}"
                if full_module_name in sys.modules:
                    # Reload to pick up edits (supports hot-reload via XMPP restart)
                    module = importlib.reload(sys.modules[full_module_name])
                else:
                    module = importlib.import_module(full_module_name)
            else:
                # For user plugins, do a spec-based import
                # Always re-execute to support hot-reload of plugin file edits
                spec = importlib.util.spec_from_file_location(
                    f"a2a_user_plugins.{module_name}", str(py_file)
                )
                if spec is None or spec.loader is None:
                    logger.warning("Cannot load plugin module: %s", py_file)
                    continue
                module = importlib.util.module_from_spec(spec)
                # Ensure backend root is in path for plugin imports
                if str(_BACKEND_ROOT) not in sys.path:
                    sys.path.insert(0, str(_BACKEND_ROOT))
                spec.loader.exec_module(module)

            # Find AdhocCommand subclasses in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    inspect.isclass(attr)
                    and issubclass(attr, AdhocCommand)
                    and attr is not AdhocCommand
                    and attr is not TemplateCommand
                    and getattr(attr, 'node', '')  # Must have a node defined
                    # Skip classes imported from elsewhere; only instantiate
                    # those defined in the current module
                    and getattr(attr, '__module__', '') == getattr(module, '__name__', '')
                ):
                    try:
                        instance = attr()
                    except Exception as inst_err:
                        logger.error(
                            "Failed to instantiate command class %s in %s: %s",
                            attr_name, py_file.name, inst_err,
                        )
                        continue
                    instance._source = source
                    commands.append(instance)
                    logger.debug(
                        "Loaded command: node=%s name=%s source=%s from=%s",
                        instance.node, instance.name, source, py_file.name,
                    )

        except Exception as e:
            logger.error(
                "Failed to load command module %s: %s", py_file.name, e
            )

    return commands
