# -*- coding: utf-8 -*-
"""
Create test data for Tools module with executable code
"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.config.database import SessionLocal
from backend.database.models.system import PluginMng, McpMng, FunctionMng, SkillMng
import json
from datetime import datetime
import uuid

def create_test_scripts():
    """Create test script files"""
    test_scripts_dir = "/tmp/ai_sns_test_tools"
    os.makedirs(test_scripts_dir, exist_ok=True)

    # 1. Simple Python plugin script
    plugin_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json

# Read parameters from stdin
try:
    params = json.loads(sys.stdin.read()) if sys.stdin.read() else {}
except:
    params = {}

# Execute plugin logic
result = {
    "status": "success",
    "message": "Hello from Test Plugin!",
    "params_received": params,
    "timestamp": str(__import__('datetime').datetime.now())
}

# Output result as JSON
print(json.dumps(result, ensure_ascii=False))
"""

    plugin_path = f"{test_scripts_dir}/test_plugin.py"
    with open(plugin_path, 'w', encoding='utf-8') as f:
        f.write(plugin_script)
    os.chmod(plugin_path, 0o755)

    # 2. Function script
    function_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json

def calculate_sum(numbers):
    \"\"\"Calculate sum of numbers\"\"\"
    return sum(numbers)

if __name__ == "__main__":
    try:
        params = json.loads(sys.stdin.read()) if sys.stdin.read() else {}
    except:
        params = {}

    numbers = params.get('numbers', [1, 2, 3, 4, 5])
    total = calculate_sum(numbers)

    result = {
        "function": "calculate_sum",
        "input": numbers,
        "output": total
    }

    print(json.dumps(result))
"""

    function_path = f"{test_scripts_dir}/test_function.py"
    with open(function_path, 'w', encoding='utf-8') as f:
        f.write(function_script)
    os.chmod(function_path, 0o755)

    # 3. MCP server script (simple test)
    mcp_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json

# Simple MCP test that returns success
result = {
    "protocol_version": "1.0",
    "server_info": {
        "name": "Test MCP Server",
        "version": "1.0.0"
    },
    "capabilities": ["tools", "resources"]
}

print(json.dumps(result))
"""

    mcp_path = f"{test_scripts_dir}/test_mcp_server.py"
    with open(mcp_path, 'w', encoding='utf-8') as f:
        f.write(mcp_script)
    os.chmod(mcp_path, 0o755)

    # 4. Skill script
    skill_script = """#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys
import json

try:
    params = json.loads(sys.stdin.read()) if sys.stdin.read() else {}
except:
    params = {}

result = {
    "skill": "custom_test_skill",
    "action": params.get('action', 'test'),
    "result": "Skill executed successfully",
    "params": params
}

print(json.dumps(result))
"""

    skill_path = f"{test_scripts_dir}/test_skill.py"
    with open(skill_path, 'w', encoding='utf-8') as f:
        f.write(skill_script)
    os.chmod(skill_path, 0o755)

    print(f"✓ Created test scripts in {test_scripts_dir}")
    return {
        "plugin": plugin_path,
        "function": function_path,
        "mcp": mcp_path,
        "skill": skill_path
    }


def create_test_data():
    """Create test data for all 4 tool types"""
    db = SessionLocal()

    try:
        # Create test script files
        script_paths = create_test_scripts()

        print("\nStarting to create test data...")

        # 1. Create Plugin with file_path
        plugin1 = PluginMng(
            plugin_id=str(uuid.uuid4())[:8].upper(),
            name="Test Plugin - File Execution",
            description="A test plugin that executes from file path",
            instruction="Use this plugin to test file-based execution. It accepts any parameters and returns a JSON response.",
            plugin_type="tool",
            filename=script_paths["plugin"],
            detail=json.dumps({"test_mode": True}),
            confirm_needed=False,
            is_delete=False
        )
        db.add(plugin1)

        # 2. Create Plugin with runtime_main code
        runtime_code = """import sys
import json

result = {
    "status": "success",
    "message": "Hello from inline code!",
    "execution_type": "runtime_main"
}

print(json.dumps(result))
"""

        plugin2 = PluginMng(
            plugin_id=str(uuid.uuid4())[:8].upper(),
            name="Test Plugin - Inline Code",
            description="A test plugin that executes inline Python code",
            instruction="Use this plugin to test inline code execution. No file needed.",
            plugin_type="custom",
            runtime_main=runtime_code,
            detail=json.dumps({}),
            confirm_needed=False,
            is_delete=False
        )
        db.add(plugin2)

        # 3. Create MCP
        mcp1 = McpMng(
            mcp_id=str(uuid.uuid4())[:8].upper(),
            name="Test MCP Server",
            description="A test MCP server for testing connection",
            instruction="Use this MCP server for testing. It provides basic server info.",
            mcp_type="stdio",
            file_path=script_paths["mcp"],
            parameter=json.dumps({"timeout": 10}),
            requirement="",
            confirm_needed=False,
            is_delete=False
        )
        db.add(mcp1)

        # 4. Create Function
        function1 = FunctionMng(
            function_id=str(uuid.uuid4())[:8].upper(),
            name="Calculate Sum Function",
            description="Calculates the sum of a list of numbers",
            instruction="Use this function to calculate sum. Pass an array of numbers in 'numbers' parameter.",
            function_type="python",
            file_path=script_paths["function"],
            parameter=json.dumps({
                "numbers": {
                    "type": "array",
                    "description": "Array of numbers to sum",
                    "default": [1, 2, 3, 4, 5]
                }
            }),
            confirm_needed=False,
            is_delete=False
        )
        db.add(function1)

        # 5. Create Skills (Computer Use)

        # Screenshot skill
        skill1 = SkillMng(
            skill_id=str(uuid.uuid4())[:8].upper(),
            name="Screenshot Capture",
            description="Captures a screenshot of the entire screen",
            instruction="Use this skill to take a screenshot. No parameters needed.",
            skill_type="screenshot",
            parameter=json.dumps({}),
            confirm_needed=True,
            is_delete=False
        )
        db.add(skill1)

        # Mouse click skill
        skill2 = SkillMng(
            skill_id=str(uuid.uuid4())[:8].upper(),
            name="Mouse Click",
            description="Simulates a mouse click at specified coordinates",
            instruction="Use this skill to click at specific screen coordinates. Provide x and y parameters.",
            skill_type="mouse_click",
            parameter=json.dumps({
                "x": {"type": "int", "description": "X coordinate", "default": 100},
                "y": {"type": "int", "description": "Y coordinate", "default": 100}
            }),
            confirm_needed=True,
            is_delete=False
        )
        db.add(skill2)

        # Keyboard input skill
        skill3 = SkillMng(
            skill_id=str(uuid.uuid4())[:8].upper(),
            name="Keyboard Input",
            description="Types text using keyboard simulation",
            instruction="Use this skill to type text. Provide 'text' parameter with the string to type.",
            skill_type="keyboard_input",
            parameter=json.dumps({
                "text": {"type": "string", "description": "Text to type", "default": "Hello World"}
            }),
            confirm_needed=True,
            is_delete=False
        )
        db.add(skill3)

        # Custom skill with script
        skill4 = SkillMng(
            skill_id=str(uuid.uuid4())[:8].upper(),
            name="Custom Test Skill",
            description="A custom skill that executes a Python script",
            instruction="Use this custom skill for testing script execution.",
            skill_type="custom",
            file_path=script_paths["skill"],
            parameter=json.dumps({"action": "test"}),
            confirm_needed=False,
            is_delete=False
        )
        db.add(skill4)

        # Commit all changes
        db.commit()

        print("\n✓ Test data created successfully:")
        print(f"  - 2 Plugins (file + inline code)")
        print(f"  - 1 MCP")
        print(f"  - 1 Function")
        print(f"  - 4 Skills")
        print(f"\nAll test tools are executable!")

    except Exception as e:
        print(f"\n✗ Failed to create test data: {e}")
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    create_test_data()
