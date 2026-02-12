# -*- coding: utf-8 -*-
"""
Tool Executor - 真实执行工具代码
Executes plugins, MCPs, functions, and skills with actual code execution
"""
import os
import sys
import json
import logging
import subprocess
import asyncio
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
import traceback
from contextlib import AsyncExitStack

logger = logging.getLogger(__name__)

# MCP client imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    MCP_AVAILABLE = True
except ImportError:
    MCP_AVAILABLE = False
    logger.warning("MCP library not available. Install with: pip install mcp")


def get_python_executable():
    """Get the correct Python executable (prefer venv if available)"""
    # Check if we're in a virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        # Already in venv, use current executable
        return sys.executable

    # Try to find venv in project root
    project_root = Path(__file__).parent.parent.parent.parent
    venv_paths = [
        project_root / 'venv' / 'Scripts' / 'python.exe',  # Windows
        project_root / 'venv' / 'bin' / 'python',  # Linux/Mac
        project_root / '.venv' / 'Scripts' / 'python.exe',  # Windows alt
        project_root / '.venv' / 'bin' / 'python',  # Linux/Mac alt
    ]

    for venv_python in venv_paths:
        if venv_python.exists():
            logger.info(f"Using venv Python: {venv_python}")
            return str(venv_python)

    # Fallback to current executable
    logger.warning(f"No venv found, using system Python: {sys.executable}")
    return sys.executable


# Execution timeout in seconds
EXECUTION_TIMEOUT = 60


class ToolExecutor:
    """Tool executor for real code execution"""

    def __init__(self):
        self.execution_log = []

    def log_execution(self, tool_type: str, tool_id: str, status: str, message: str, details: Any = None):
        """Log execution details"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "tool_type": tool_type,
            "tool_id": tool_id,
            "status": status,
            "message": message,
            "details": details
        }
        self.execution_log.append(log_entry)
        logger.info(f"[{tool_type}] {tool_id}: {status} - {message}")

    async def execute_plugin(self, plugin_id: str, plugin_data: dict, params: dict) -> dict:
        """
        Execute a plugin with real code execution

        Execution priority:
        1. If runtime_main exists, execute the code
        2. If filename exists, execute the file
        3. Return error if neither exists
        """
        self.log_execution("plugin", plugin_id, "started", "Plugin execution started")

        try:
            plugin_name = plugin_data.get('name', 'Unnamed Plugin')
            runtime_main = plugin_data.get('runtime_main')
            filename = plugin_data.get('filename')
            plugin_directory = plugin_data.get('plugin_directory')

            # Prepare parameters
            params_json = json.dumps(params)

            # Case 1: Execute runtime_main code
            if runtime_main and runtime_main.strip():
                self.log_execution("plugin", plugin_id, "executing", "Executing runtime_main code")
                result = await self._execute_python_code(runtime_main, params, plugin_id)

                self.log_execution("plugin", plugin_id, "completed", "Plugin executed successfully", result)

                return {
                    "status": "success",
                    "plugin_id": plugin_id,
                    "plugin_name": plugin_name,
                    "message": f"Plugin '{plugin_name}' executed successfully",
                    "timestamp": datetime.now().isoformat(),
                    "execution_method": "runtime_main",
                    "output": result
                }

            # Case 2: Execute file
            elif filename:
                file_path = self._resolve_file_path(filename, plugin_directory)

                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Plugin file not found: {file_path}")

                self.log_execution("plugin", plugin_id, "executing", f"Executing file: {file_path}")

                # Determine file type
                if file_path.endswith('.py'):
                    result = await self._execute_python_file(file_path, params)
                elif file_path.endswith('.js'):
                    result = await self._execute_javascript_file(file_path, params)
                else:
                    result = await self._execute_shell_script(file_path, params)

                self.log_execution("plugin", plugin_id, "completed", "Plugin executed successfully", result)

                return {
                    "status": "success",
                    "plugin_id": plugin_id,
                    "plugin_name": plugin_name,
                    "message": f"Plugin '{plugin_name}' executed successfully",
                    "timestamp": datetime.now().isoformat(),
                    "execution_method": "file",
                    "file_path": file_path,
                    "output": result
                }

            # Case 3: No executable code
            else:
                self.log_execution("plugin", plugin_id, "error", "No executable code found")
                return {
                    "status": "error",
                    "plugin_id": plugin_id,
                    "plugin_name": plugin_name,
                    "message": "Plugin has no executable code (no runtime_main or filename)",
                    "timestamp": datetime.now().isoformat()
                }

        except asyncio.TimeoutError:
            self.log_execution("plugin", plugin_id, "timeout", f"Execution timeout after {EXECUTION_TIMEOUT}s")
            return {
                "status": "timeout",
                "plugin_id": plugin_id,
                "message": f"Plugin execution timeout after {EXECUTION_TIMEOUT} seconds",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            self.log_execution("plugin", plugin_id, "error", error_msg, error_trace)

            return {
                "status": "error",
                "plugin_id": plugin_id,
                "message": f"Plugin execution failed: {error_msg}",
                "error": error_msg,
                "traceback": error_trace,
                "timestamp": datetime.now().isoformat()
            }

    async def execute_mcp(self, mcp_id: str, mcp_data: dict, params: dict) -> dict:
        """
        Execute MCP server connection test or tool call

        For real MCP execution, we would:
        1. Start the MCP server process
        2. Connect to it via stdio or SSE
        3. List available tools or execute a specific tool

        Current implementation: Test server startup
        """
        self.log_execution("mcp", mcp_id, "started", "MCP execution started")

        try:
            mcp_name = mcp_data.get('name', 'Unnamed MCP')
            file_path = mcp_data.get('file_path')
            mcp_type = mcp_data.get('mcp_type', 'stdio')
            parameter = mcp_data.get('parameter', '{}')

            if not file_path or not os.path.exists(file_path):
                # If file doesn't exist, return connection test status
                self.log_execution("mcp", mcp_id, "warning", f"MCP file not found: {file_path}")

                return {
                    "status": "partial_success",
                    "mcp_id": mcp_id,
                    "mcp_name": mcp_name,
                    "mcp_type": mcp_type,
                    "message": f"MCP '{mcp_name}' configuration valid (file not found for actual execution)",
                    "timestamp": datetime.now().isoformat(),
                    "connection": {
                        "status": "configured",
                        "file_path": file_path,
                        "mcp_type": mcp_type,
                        "note": "MCP server file not found, but configuration is valid"
                    }
                }

            # Real MCP server test
            self.log_execution("mcp", mcp_id, "testing", f"Testing MCP server: {file_path}")

            result = await self._test_mcp_server(file_path, mcp_type, parameter)

            self.log_execution("mcp", mcp_id, "completed", "MCP test completed", result)

            return {
                "status": "success",
                "mcp_id": mcp_id,
                "mcp_name": mcp_name,
                "mcp_type": mcp_type,
                "message": f"MCP '{mcp_name}' connection test successful",
                "timestamp": datetime.now().isoformat(),
                "connection": result
            }

        except asyncio.TimeoutError:
            self.log_execution("mcp", mcp_id, "timeout", f"Execution timeout after {EXECUTION_TIMEOUT}s")
            return {
                "status": "timeout",
                "mcp_id": mcp_id,
                "message": f"MCP execution timeout after {EXECUTION_TIMEOUT} seconds",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            self.log_execution("mcp", mcp_id, "error", error_msg, error_trace)

            return {
                "status": "error",
                "mcp_id": mcp_id,
                "message": f"MCP execution failed: {error_msg}",
                "error": error_msg,
                "traceback": error_trace,
                "timestamp": datetime.now().isoformat()
            }

    async def execute_function(self, function_id: str, function_data: dict, params: dict) -> dict:
        """Execute a function with real code execution"""
        self.log_execution("function", function_id, "started", "Function execution started")

        try:
            function_name = function_data.get('name', 'Unnamed Function')
            file_path = function_data.get('file_path')
            function_type = function_data.get('function_type', 'python')
            parameter_schema = function_data.get('parameter', '{}')

            if not file_path:
                raise ValueError("Function file_path not specified")

            if not os.path.exists(file_path):
                raise FileNotFoundError(f"Function file not found: {file_path}")

            self.log_execution("function", function_id, "executing", f"Executing function file: {file_path}")

            # Execute based on function type
            if function_type == 'python' or file_path.endswith('.py'):
                result = await self._execute_python_file(file_path, params)
            elif function_type == 'javascript' or file_path.endswith('.js'):
                result = await self._execute_javascript_file(file_path, params)
            else:
                result = await self._execute_shell_script(file_path, params)

            self.log_execution("function", function_id, "completed", "Function executed successfully", result)

            return {
                "status": "success",
                "function_id": function_id,
                "function_name": function_name,
                "function_type": function_type,
                "message": f"Function '{function_name}' executed successfully",
                "timestamp": datetime.now().isoformat(),
                "file_path": file_path,
                "result": result
            }

        except asyncio.TimeoutError:
            self.log_execution("function", function_id, "timeout", f"Execution timeout after {EXECUTION_TIMEOUT}s")
            return {
                "status": "timeout",
                "function_id": function_id,
                "message": f"Function execution timeout after {EXECUTION_TIMEOUT} seconds",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            self.log_execution("function", function_id, "error", error_msg, error_trace)

            return {
                "status": "error",
                "function_id": function_id,
                "message": f"Function execution failed: {error_msg}",
                "error": error_msg,
                "traceback": error_trace,
                "timestamp": datetime.now().isoformat()
            }

    async def execute_skill(self, skill_id: str, skill_data: dict, params: dict) -> dict:
        """Execute a computer use skill with real system operations"""
        self.log_execution("skill", skill_id, "started", "Skill execution started")

        try:
            skill_name = skill_data.get('name', 'Unnamed Skill')
            skill_type = skill_data.get('skill_type', 'custom')
            file_path = skill_data.get('file_path')
            parameter = skill_data.get('parameter', '{}')

            # Parse default parameters
            try:
                default_params = json.loads(parameter) if parameter else {}
            except:
                default_params = {}

            # Merge with provided params
            merged_params = {**default_params, **params}

            self.log_execution("skill", skill_id, "executing", f"Executing skill type: {skill_type}")

            # Execute based on skill type
            if skill_type == 'screenshot':
                result = await self._execute_screenshot(merged_params)
            elif skill_type == 'mouse_click':
                result = await self._execute_mouse_click(merged_params)
            elif skill_type == 'keyboard_input':
                result = await self._execute_keyboard_input(merged_params)
            elif skill_type == 'custom' and file_path:
                if not os.path.exists(file_path):
                    raise FileNotFoundError(f"Skill file not found: {file_path}")
                result = await self._execute_python_file(file_path, merged_params)
            else:
                raise ValueError(f"Unknown skill type: {skill_type} or custom file not found")

            self.log_execution("skill", skill_id, "completed", "Skill executed successfully", result)

            return {
                "status": "success",
                "skill_id": skill_id,
                "skill_name": skill_name,
                "skill_type": skill_type,
                "message": f"Skill '{skill_name}' executed successfully",
                "timestamp": datetime.now().isoformat(),
                "action": result
            }

        except asyncio.TimeoutError:
            self.log_execution("skill", skill_id, "timeout", f"Execution timeout after {EXECUTION_TIMEOUT}s")
            return {
                "status": "timeout",
                "skill_id": skill_id,
                "message": f"Skill execution timeout after {EXECUTION_TIMEOUT} seconds",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            error_msg = str(e)
            error_trace = traceback.format_exc()
            self.log_execution("skill", skill_id, "error", error_msg, error_trace)

            return {
                "status": "error",
                "skill_id": skill_id,
                "message": f"Skill execution failed: {error_msg}",
                "error": error_msg,
                "traceback": error_trace,
                "timestamp": datetime.now().isoformat()
            }

    # ==================== Helper Methods ====================

    def _resolve_file_path(self, filename: str, plugin_directory: Optional[str] = None) -> str:
        """Resolve plugin file path"""
        if os.path.isabs(filename):
            return filename

        # Try plugin directory
        if plugin_directory:
            path = os.path.join(plugin_directory, filename)
            if os.path.exists(path):
                return path

        # Try relative to project root
        project_root = Path(__file__).parent.parent.parent.parent
        path = os.path.join(project_root, filename)
        if os.path.exists(path):
            return path

        # Return as-is if not found
        return filename

    async def _execute_python_code(self, code: str, params: dict, identifier: str) -> dict:
        """Execute Python code string"""
        try:
            # Create temporary file with UTF-8 encoding
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False, encoding='utf-8') as f:
                # Write code that accepts params from stdin
                wrapper_code = f'''# -*- coding: utf-8 -*-
import sys
import json
import io

# Force UTF-8 encoding for stdout/stderr (Windows compatibility)
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Read parameters from stdin
try:
    stdin_content = sys.stdin.read()
    params = json.loads(stdin_content) if stdin_content else {{}}
except:
    params = {{}}

# Also provide params as sys.argv for backward compatibility
# Some plugins expect: json.loads(sys.argv[1])
if params and len(sys.argv) == 1:
    sys.argv.append(json.dumps(params))

# User code
{code}

# If code defines a main function, call it
if 'main' in dir():
    result = main(params) if callable(main) else main
    print(json.dumps({{"result": result}}))
'''
                f.write(wrapper_code)
                temp_file = f.name

            try:
                # Prepare environment with UTF-8 encoding (for Windows compatibility)
                env = os.environ.copy()
                env['PYTHONIOENCODING'] = 'utf-8'

                # Execute with timeout
                process = await asyncio.create_subprocess_exec(
                    get_python_executable(), temp_file,
                    stdin=subprocess.PIPE,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env
                )

                # Send params as stdin
                params_json = json.dumps(params).encode()

                stdout, stderr = await asyncio.wait_for(
                    process.communicate(input=params_json),
                    timeout=EXECUTION_TIMEOUT
                )

                stdout_str = stdout.decode('utf-8', errors='replace')
                stderr_str = stderr.decode('utf-8', errors='replace')

                return {
                    "stdout": stdout_str,
                    "stderr": stderr_str,
                    "return_code": process.returncode,
                    "success": process.returncode == 0
                }
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_file)
                except:
                    pass

        except Exception as e:
            raise Exception(f"Python code execution failed: {str(e)}")

    async def _execute_python_file(self, file_path: str, params: dict) -> dict:
        """Execute Python file"""
        try:
            # Prepare environment with UTF-8 encoding (for Windows compatibility)
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            process = await asyncio.create_subprocess_exec(
                get_python_executable(), file_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )

            params_json = json.dumps(params).encode()

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=params_json),
                timeout=EXECUTION_TIMEOUT
            )

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": process.returncode,
                "success": process.returncode == 0
            }

        except Exception as e:
            raise Exception(f"Python file execution failed: {str(e)}")

    async def _execute_javascript_file(self, file_path: str, params: dict) -> dict:
        """Execute JavaScript file using Node.js"""
        try:
            # Check if node is available (cross-platform)
            if not shutil.which('node'):
                raise Exception("Node.js not found. Please install Node.js to execute JavaScript files.")

            # Prepare environment with UTF-8 encoding (for Windows compatibility)
            env = os.environ.copy()
            env['NODE_OPTIONS'] = '--max-old-space-size=4096'

            process = await asyncio.create_subprocess_exec(
                'node', file_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env
            )

            params_json = json.dumps(params).encode()

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=params_json),
                timeout=EXECUTION_TIMEOUT
            )

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": process.returncode,
                "success": process.returncode == 0
            }

        except Exception as e:
            raise Exception(f"JavaScript file execution failed: {str(e)}")

    async def _execute_shell_script(self, file_path: str, params: dict) -> dict:
        """Execute shell script"""
        try:
            # Make file executable
            os.chmod(file_path, 0o755)

            process = await asyncio.create_subprocess_exec(
                file_path,
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE
            )

            params_json = json.dumps(params).encode()

            stdout, stderr = await asyncio.wait_for(
                process.communicate(input=params_json),
                timeout=EXECUTION_TIMEOUT
            )

            stdout_str = stdout.decode('utf-8', errors='replace')
            stderr_str = stderr.decode('utf-8', errors='replace')

            return {
                "stdout": stdout_str,
                "stderr": stderr_str,
                "return_code": process.returncode,
                "success": process.returncode == 0
            }

        except Exception as e:
            raise Exception(f"Shell script execution failed: {str(e)}")

    async def _test_mcp_server(self, file_path: str, mcp_type: str, parameter: str) -> dict:
        """Test MCP server by connecting and calling a tool"""

        # Check if MCP library is available
        if not MCP_AVAILABLE:
            return {
                "status": "library_missing",
                "file_path": file_path,
                "mcp_type": mcp_type,
                "message": "MCP library not installed. Run: pip install mcp",
                "tools": [],
                "tool_call_result": None
            }

        try:
            # Prepare environment with UTF-8 encoding (for Windows compatibility)
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            # Determine command to start server
            if file_path.endswith('.py'):
                cmd = [get_python_executable(), file_path]
            else:
                cmd = [file_path]

            # Set up MCP client parameters
            server_params = StdioServerParameters(
                command=cmd[0],
                args=cmd[1:] if len(cmd) > 1 else [],
                env=env
            )

            # Connect to MCP server and test with timeout
            async with asyncio.timeout(30):  # 30 second timeout
                async with AsyncExitStack() as stack:
                    # Start stdio transport
                    stdio_transport = await stack.enter_async_context(
                        stdio_client(server_params)
                    )
                    stdio, write = stdio_transport

                    # Create client session
                    session = await stack.enter_async_context(
                        ClientSession(stdio, write)
                    )

                    # Initialize connection
                    await session.initialize()

                    # List available tools
                    tools_result = await session.list_tools()
                    tools_list = []
                    for tool in tools_result.tools:
                        tools_list.append({
                            "name": tool.name,
                            "description": tool.description
                        })

                    # Try to call the first tool (or a specific tool)
                    tool_call_result = None
                    if tools_list:
                        # Try to find get_weather or use first tool
                        test_tool = None
                        test_args = {}

                        # Look for get_weather tool
                        for tool in tools_result.tools:
                            if tool.name == "get_weather":
                                test_tool = "get_weather"
                                test_args = {"city": "Beijing", "unit": "celsius"}
                                break
                            elif tool.name == "get_current_time":
                                test_tool = "get_current_time"
                                test_args = {"timezone": "UTC"}
                                break
                            elif tool.name == "calculate":
                                test_tool = "calculate"
                                test_args = {"expression": "10 + 20"}
                                break

                        # If no specific tool found, use first one with empty args
                        if not test_tool and tools_result.tools:
                            test_tool = tools_result.tools[0].name
                            test_args = {}

                        # Call the tool
                        if test_tool:
                            try:
                                call_result = await session.call_tool(test_tool, test_args)

                                # Extract text content
                                result_text = ""
                                for content in call_result.content:
                                    if hasattr(content, 'text'):
                                        result_text += content.text

                                tool_call_result = {
                                    "tool_name": test_tool,
                                    "arguments": test_args,
                                    "success": True,
                                    "result": result_text[:500]  # Limit to 500 chars
                                }
                            except Exception as e:
                                tool_call_result = {
                                    "tool_name": test_tool,
                                    "arguments": test_args,
                                    "success": False,
                                    "error": str(e)
                                }

                    # Return success with tool list and call result
                    return {
                        "status": "success",
                        "file_path": file_path,
                        "mcp_type": mcp_type,
                        "message": "MCP server connected and tools tested successfully",
                        "tools_count": len(tools_list),
                        "tools": tools_list,
                        "tool_call_result": tool_call_result
                    }

        except asyncio.TimeoutError:
            return {
                "status": "timeout",
                "file_path": file_path,
                "mcp_type": mcp_type,
                "message": "MCP server connection timeout",
                "tools": [],
                "tool_call_result": None
            }
        except Exception as e:
            # Handle all exceptions including ExceptionGroup
            error_msg = str(e)
            error_trace = traceback.format_exc()
            return {
                "status": "error",
                "file_path": file_path,
                "mcp_type": mcp_type,
                "message": f"MCP server test failed: {error_msg}",
                "error": error_msg,
                "traceback": error_trace[:1000],  # Limit traceback
                "tools": [],
                "tool_call_result": None
            }

    async def execute_mcp_tool(self, mcp_id: str, tool_name: str, arguments: dict) -> dict:
        """
        Execute specific MCP tool (for agent tool calling)

        This is different from _test_mcp_server which tests the server.
        This method connects to the MCP server and executes a specific tool with given arguments.

        Args:
            mcp_id: MCP server ID (e.g., "MC2026011511561554068")
            tool_name: Tool name (e.g., "get_weather")
            arguments: Tool arguments (e.g., {"city": "Shanghai", "unit": "celsius"})

        Returns:
            {
                "success": bool,
                "result": str,  # Tool output
                "error": str    # Error message if failed
            }
        """
        self.log_execution("mcp_tool", mcp_id, "started", f"Executing tool: {tool_name}")

        # Check if MCP library is available
        if not MCP_AVAILABLE:
            return {
                "success": False,
                "error": "MCP library not installed. Run: pip install mcp"
            }

        # Get MCP config from database
        from backend.database.repositories.system_repository import KeyValueRepository
        from backend.config.database import get_db_session
        from backend.database.models.system import McpMng

        db = get_db_session()
        try:
            # Query MCP directly from database
            mcp_data = db.query(McpMng).filter_by(mcp_id=mcp_id).first()

            if not mcp_data:
                return {
                    "success": False,
                    "error": f"MCP {mcp_id} not found in database"
                }

            file_path = mcp_data.file_path
            mcp_type = mcp_data.mcp_type or 'stdio'

            if not file_path or not os.path.exists(file_path):
                return {
                    "success": False,
                    "error": f"MCP server file not found: {file_path}"
                }

        finally:
            db.close()

        try:
            # Prepare environment with UTF-8 encoding (for Windows compatibility)
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            # Determine command to start server
            if file_path.endswith('.py'):
                cmd = [get_python_executable(), file_path]
            else:
                cmd = [file_path]

            # Set up MCP client parameters
            server_params = StdioServerParameters(
                command=cmd[0],
                args=cmd[1:] if len(cmd) > 1 else [],
                env=env
            )

            # Connect to MCP server and execute tool
            async with AsyncExitStack() as stack:
                # Start stdio transport
                stdio_transport = await stack.enter_async_context(
                    stdio_client(server_params)
                )
                stdio, write = stdio_transport

                # Create client session
                session = await stack.enter_async_context(
                    ClientSession(stdio, write)
                )

                # Initialize connection
                await session.initialize()

                # Call the specific tool
                call_result = await session.call_tool(tool_name, arguments)

                # Extract text content from result
                result_text = ""
                for content in call_result.content:
                    if hasattr(content, 'text'):
                        result_text += content.text

                self.log_execution("mcp_tool", mcp_id, "completed", f"Tool {tool_name} executed successfully")

                return {
                    "success": True,
                    "result": result_text
                }

        except asyncio.TimeoutError:
            error_msg = f"MCP tool execution timeout for {tool_name}"
            self.log_execution("mcp_tool", mcp_id, "timeout", error_msg)
            return {
                "success": False,
                "error": error_msg
            }

        except Exception as e:
            error_msg = f"MCP tool execution failed: {str(e)}"
            error_trace = traceback.format_exc()
            self.log_execution("mcp_tool", mcp_id, "error", error_msg, error_trace[:500])

            return {
                "success": False,
                "error": error_msg
            }

    async def _execute_screenshot(self, params: dict) -> dict:
        """Execute screenshot capture"""
        try:
            # Try to import screenshot libraries
            try:
                import pyautogui

                region = params.get('region', 'full')
                format = params.get('format', 'png')

                # Take screenshot
                screenshot = pyautogui.screenshot()

                # Save to temp file
                temp_dir = tempfile.gettempdir()
                filename = f"screenshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}"
                filepath = os.path.join(temp_dir, filename)

                screenshot.save(filepath)

                return {
                    "performed": "screenshot_capture",
                    "region": region,
                    "format": format,
                    "filepath": filepath,
                    "size": f"{screenshot.width}x{screenshot.height}",
                    "message": f"Screenshot saved to {filepath}"
                }

            except ImportError:
                return {
                    "performed": "screenshot_capture",
                    "status": "library_missing",
                    "message": "pyautogui not installed. Run: pip install pyautogui pillow",
                    "note": "Screenshot functionality requires pyautogui"
                }

        except Exception as e:
            raise Exception(f"Screenshot execution failed: {str(e)}")

    async def _execute_mouse_click(self, params: dict) -> dict:
        """Execute mouse click"""
        try:
            try:
                import pyautogui

                x = params.get('x', 0)
                y = params.get('y', 0)
                button = params.get('button', 'left')
                clicks = params.get('clicks', 1)

                pyautogui.click(x, y, clicks=clicks, button=button)

                return {
                    "performed": "mouse_click",
                    "coordinates": f"({x}, {y})",
                    "button": button,
                    "clicks": clicks,
                    "message": f"Clicked {button} button {clicks} time(s) at ({x}, {y})"
                }

            except ImportError:
                return {
                    "performed": "mouse_click",
                    "status": "library_missing",
                    "message": "pyautogui not installed. Run: pip install pyautogui",
                    "note": "Mouse control functionality requires pyautogui"
                }

        except Exception as e:
            raise Exception(f"Mouse click execution failed: {str(e)}")

    async def _execute_keyboard_input(self, params: dict) -> dict:
        """Execute keyboard input"""
        try:
            try:
                import pyautogui

                text = params.get('text', '')
                interval_ms = params.get('interval_ms', 50)
                interval = interval_ms / 1000.0

                if text:
                    pyautogui.write(text, interval=interval)

                return {
                    "performed": "keyboard_input",
                    "text_length": len(text),
                    "interval_ms": interval_ms,
                    "message": f"Typed {len(text)} characters"
                }

            except ImportError:
                return {
                    "performed": "keyboard_input",
                    "status": "library_missing",
                    "message": "pyautogui not installed. Run: pip install pyautogui",
                    "note": "Keyboard control functionality requires pyautogui"
                }

        except Exception as e:
            raise Exception(f"Keyboard input execution failed: {str(e)}")

    def get_execution_logs(self) -> list:
        """Get all execution logs"""
        return self.execution_log

    def clear_execution_logs(self):
        """Clear execution logs"""
        self.execution_log = []


# Global executor instance
_executor = None


def get_tool_executor() -> ToolExecutor:
    """Get global tool executor instance"""
    global _executor
    if _executor is None:
        _executor = ToolExecutor()
    return _executor
