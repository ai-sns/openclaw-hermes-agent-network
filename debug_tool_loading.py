# -*- coding: utf-8 -*-
"""Debug tool loading"""
import sys
sys.path.insert(0, '.')

from backend.database.repositories.agent_tools_repository import AgentToolsRepository
from backend.database.repositories.system_repository import (
    PluginMngRepository,
    FunctionMngRepository,
    McpMngRepository,
    SkillMngRepository
)
from backend.config.database import get_db_session

print("=" * 80)
print(" DEBUG: Tool Loading")
print("=" * 80)

# Step 1: Get agent_tools associations
db = get_db_session()
agent_tools_repo = AgentToolsRepository(db)
associations = agent_tools_repo.get_agent_tools(1)
print(f"\nStep 1: Found {len(associations)} tool associations")
for assoc in associations:
    print(f"  - {assoc['tool_type']:8s} {assoc['tool_id']:30s} (priority: {assoc['priority']})")

# Step 2: Try to load each tool
print(f"\nStep 2: Loading tool details...")
for assoc in associations:
    tool_type = assoc["tool_type"]
    tool_id = assoc["tool_id"]

    print(f"\n  Loading {tool_type}/{tool_id}...")

    if tool_type == "plugin":
        repo = PluginMngRepository()
        tool_obj = repo.get_one(plugin_id=tool_id)
        if tool_obj:
            print(f"    ✓ Found: {tool_obj.name}")
        else:
            print(f"    ✗ Not found")

    elif tool_type == "mcp":
        repo = McpMngRepository()
        tool_obj = repo.get_one(mcp_id=tool_id)
        if tool_obj:
            print(f"    ✓ Found: {tool_obj.name}")
            # Try to convert to dict
            try:
                tool_detail = {c.name: getattr(tool_obj, c.name) for c in tool_obj.__table__.columns}
                print(f"    ✓ Converted to dict: {len(tool_detail)} fields")
            except Exception as e:
                print(f"    ✗ Failed to convert: {e}")
        else:
            print(f"    ✗ Not found")

    elif tool_type == "function":
        repo = FunctionMngRepository()
        tool_obj = repo.get_one(function_id=tool_id)
        if tool_obj:
            print(f"    ✓ Found: {tool_obj.name}")
        else:
            print(f"    ✗ Not found")

    elif tool_type == "skill":
        repo = SkillMngRepository()
        tool_obj = repo.get_one(skill_id=tool_id)
        if tool_obj:
            print(f"    ✓ Found: {tool_obj.name}")
        else:
            print(f"    ✗ Not found")

db.close()

# Step 3: Try AgentService.get_agent_tools()
print(f"\nStep 3: Testing AgentService.get_agent_tools()...")
from backend.modules.agent.service import AgentService

tools = AgentService.get_agent_tools(1)
print(f"  Returned {len(tools)} tools")
for tool in tools:
    tool_type = tool.get('tool_type')
    if tool_type == 'mcp':
        print(f"    MCP: {tool.get('mcp_id')}")
    elif tool_type == 'plugin':
        print(f"    Plugin: {tool.get('plugin_id')}")
    elif tool_type == 'function':
        print(f"    Function: {tool.get('function_id')}")
    elif tool_type == 'skill':
        print(f"    Skill: {tool.get('skill_id')}")

print("\n" + "=" * 80)
