# -*- coding: utf-8 -*-
"""
Tool Executor - Executes tools with real code execution
Executes plugins, MCPs, functions, and skills with actual code execution
"""
import os
import sys
import asyncio
import logging
import json
import shutil
import subprocess
import platform
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
import traceback
from contextlib import AsyncExitStack
from runtime.shared import debug_info

logger = logging.getLogger(__name__)

try:
    import httpx
except Exception:
    httpx = None


def _httpx_client_no_env(**kwargs):
    if httpx is None:
        raise ImportError("httpx is required for SSE MCP transport")
    return httpx.AsyncClient(trust_env=False, **kwargs)

# MCP client imports
try:
    from mcp import ClientSession, StdioServerParameters
    from mcp.client.stdio import stdio_client
    from mcp.client.sse import sse_client
    from mcp.client.streamable_http import streamablehttp_client
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
EXECUTION_TIMEOUT = 300


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
            # The MCP 'instruction' field is repurposed as Test Arguments (JSON):
            # it is not used by agent tool conversion, so we reuse it to pass
            # arguments to the first tool during connection tests.
            test_arguments = mcp_data.get('instruction', '')

            mcp_type_norm = str(mcp_type or 'stdio').lower().strip()
            is_http_transport = mcp_type_norm in ('sse', 'streamable-http')

            if not file_path:
                self.log_execution("mcp", mcp_id, "warning", "MCP file_path missing")
                return {
                    "status": "error",
                    "mcp_id": mcp_id,
                    "mcp_name": mcp_name,
                    "mcp_type": mcp_type,
                    "message": "MCP file_path is required",
                    "timestamp": datetime.now().isoformat(),
                }

            if not is_http_transport:
                is_file = os.path.exists(file_path)
                is_command = False
                if not is_file:
                    # stdio may use a command (e.g. npx) instead of a script path
                    is_command = shutil.which(str(file_path)) is not None

                if (not is_file) and (not is_command):
                    # If neither file nor command exists, return configuration status
                    self.log_execution("mcp", mcp_id, "warning", f"MCP stdio target not found: {file_path}")

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
                            "note": "MCP server file/command not found, but configuration is valid"
                        }
                    }

            # Real MCP server test
            self.log_execution("mcp", mcp_id, "testing", f"Testing MCP server: {file_path}")

            result = await self._test_mcp_server(file_path, mcp_type_norm, parameter, test_arguments)

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

    async def _test_mcp_server(self, file_path: str, mcp_type: str, parameter: str, test_arguments: str = '') -> dict:
        """Test MCP server by connecting and calling a tool.

        test_arguments: optional JSON object (from the MCP 'instruction' field,
        repurposed as Test Arguments) used as the arguments for the tested tool.
        When provided, it overrides the built-in default arguments and the tool
        called is always the first tool reported by the server.
        """

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
            mcp_type_norm = str(mcp_type or 'stdio').lower().strip()

            # Parse user-provided Test Arguments (JSON) for the tested tool.
            # Two accepted forms:
            #   1. {"tool_name": "fetch", "arguments": {"url": "..."}}
            #      -> test the named tool with the given arguments.
            #   2. {"url": "..."}
            #      -> treat the whole object as arguments for the first tool.
            custom_test_tool: Optional[str] = None
            custom_test_args: Optional[Dict[str, Any]] = None
            if test_arguments and str(test_arguments).strip():
                try:
                    parsed = json.loads(test_arguments) if isinstance(test_arguments, str) else test_arguments
                    if isinstance(parsed, dict):
                        tool_name_val = parsed.get('tool_name')
                        if isinstance(tool_name_val, str) and tool_name_val.strip():
                            custom_test_tool = tool_name_val.strip()
                            args_val = parsed.get('arguments')
                            custom_test_args = args_val if isinstance(args_val, dict) else {}
                        else:
                            custom_test_args = parsed
                except Exception:
                    # Ignore invalid Test Arguments JSON and fall back to defaults
                    custom_test_tool = None
                    custom_test_args = None

            stdio_args: list[str] = []
            stdio_env: Optional[Dict[str, str]] = None
            stdio_command_resolved: Optional[str] = None
            if mcp_type_norm == 'stdio' and parameter:
                try:
                    p = json.loads(parameter) if isinstance(parameter, str) else parameter
                    if isinstance(p, list):
                        stdio_args = [str(x) for x in p]
                    elif isinstance(p, dict):
                        if isinstance(p.get('args'), list):
                            stdio_args = [str(x) for x in p.get('args')]
                        if isinstance(p.get('env'), dict):
                            stdio_env = {str(k): str(v) for k, v in p.get('env').items()}
                except Exception:
                    # Ignore parameter parse errors for backward compatibility
                    pass

            total_timeout = 30
            if mcp_type_norm in ('sse', 'streamable-http'):
                total_timeout = 60
            if mcp_type_norm == 'stdio':
                # If file_path is a command (e.g., npx) rather than a script path, startup may be slow.
                if (not str(file_path).endswith('.py')) and (not os.path.exists(str(file_path))):
                    resolved = shutil.which(str(file_path))
                    if resolved:
                        stdio_command_resolved = resolved
                        total_timeout = 180

            launch_command = None
            launch_args: list[str] = []
            stderr_log_path = None
            stderr_log_file = None
            if mcp_type_norm == 'stdio':
                import tempfile
                stderr_log_file = tempfile.NamedTemporaryFile(
                    mode='w', suffix='.log', prefix='mcp_stderr_', delete=False, encoding='utf-8'
                )
                stderr_log_path = stderr_log_file.name
            async with asyncio.timeout(total_timeout):
                async with AsyncExitStack() as stack:
                    if mcp_type_norm == 'stdio':
                        # Prepare environment with UTF-8 encoding (for Windows compatibility)
                        env = os.environ.copy()
                        env['PYTHONIOENCODING'] = 'utf-8'
                        if stdio_env:
                            env.update(stdio_env)

                        # Determine command to start server
                        if file_path.endswith('.py'):
                            cmd = [get_python_executable(), file_path] + (stdio_args or [])
                        else:
                            cmd = [stdio_command_resolved or file_path] + (stdio_args or [])

                        # Windows: .cmd/.bat wrappers (e.g. npx.CMD, uvx) cannot be
                        # reliably launched directly via CreateProcess for stdio piping,
                        # which results in "Connection closed" during initialize().
                        # Launch them through cmd.exe /c instead.
                        if os.name == 'nt' and str(cmd[0]).lower().endswith(('.cmd', '.bat')):
                            cmd = ['cmd', '/c'] + cmd

                        launch_command = cmd[0]
                        launch_args = cmd[1:] if len(cmd) > 1 else []

                        server_params = StdioServerParameters(
                            command=launch_command,
                            args=launch_args,
                            env=env
                        )

                        # Pass errlog only if this mcp SDK version supports it,
                        # so we can capture the child process stderr for diagnostics.
                        try:
                            import inspect
                            _supports_errlog = 'errlog' in inspect.signature(stdio_client).parameters
                        except (ValueError, TypeError):
                            _supports_errlog = False

                        if _supports_errlog and stderr_log_file is not None:
                            stdio_transport = await stack.enter_async_context(
                                stdio_client(server_params, errlog=stderr_log_file)
                            )
                        else:
                            stdio_transport = await stack.enter_async_context(stdio_client(server_params))
                        read_stream, write_stream = stdio_transport
                        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))

                    elif mcp_type_norm == 'sse':
                        # file_path is treated as URL
                        sse_transport = await stack.enter_async_context(
                            sse_client(
                                str(file_path),
                                timeout=30.0,
                                sse_read_timeout=300.0,
                                httpx_client_factory=_httpx_client_no_env,
                            )
                        )
                        read_stream, write_stream = sse_transport
                        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))

                    elif mcp_type_norm == 'streamable-http':
                        candidates = []
                        raw_url = str(file_path)
                        candidates.append(raw_url)
                        if raw_url.endswith('/'):
                            candidates.append(raw_url.rstrip('/'))
                        else:
                            candidates.append(raw_url + '/')
                        # keep order but unique
                        seen = set()
                        candidates = [u for u in candidates if not (u in seen or seen.add(u))]

                        last_err: Optional[Exception] = None
                        http_transport = None
                        for url in candidates:
                            try:
                                http_transport = await stack.enter_async_context(
                                    streamablehttp_client(
                                        url,
                                        headers={},
                                        timeout=60,
                                        sse_read_timeout=300,
                                        httpx_client_factory=_httpx_client_no_env,
                                    )
                                )
                                break
                            except Exception as e:
                                last_err = e
                                continue

                        if http_transport is None:
                            raise last_err or RuntimeError('Failed to connect streamable-http')

                        # streamablehttp_client may return (read, write) or (read, write, get_session_id)
                        read_stream = http_transport[0]
                        write_stream = http_transport[1]
                        session = await stack.enter_async_context(ClientSession(read_stream, write_stream))

                    else:
                        raise ValueError(f"Unsupported MCP type: {mcp_type_norm}")

                    await session.initialize()

                    tools_result = await session.list_tools()
                    tools_list = [
                        {
                            "name": t.name,
                            "description": t.description,
                            "inputSchema": getattr(t, "inputSchema", None),
                        }
                        for t in (tools_result.tools or [])
                    ]

                    tool_call_result = None
                    if tools_list:
                        test_tool = None
                        test_args: Dict[str, Any] = {}

                        # If the user provided Test Arguments (JSON), skip the
                        # built-in default heuristics. When a tool_name is given,
                        # test that tool; otherwise test the first tool.
                        if custom_test_args is not None and tools_result.tools:
                            if custom_test_tool:
                                test_tool = custom_test_tool
                            else:
                                test_tool = tools_result.tools[0].name
                            test_args = custom_test_args

                        for t in (tools_result.tools if test_tool is None else []):
                            if t.name == 'get_weather':
                                test_tool = 'get_weather'
                                test_args = {"city": "Beijing", "unit": "celsius"}
                                break
                            if t.name == 'get_current_time':
                                test_tool = 'get_current_time'
                                test_args = {"timezone": "UTC"}
                                break
                            if t.name == 'calculate':
                                test_tool = 'calculate'
                                test_args = {"expression": "10 + 20"}
                                break
                            if t.name == 'echo':
                                test_tool = 'echo'
                                test_args = {"message": "Hello"}
                                break

                        if not test_tool and tools_result.tools:
                            test_tool = tools_result.tools[0].name
                            test_args = {}

                        if test_tool:
                            try:
                                call_result = await session.call_tool(test_tool, test_args)
                                result_text = ""
                                for content in call_result.content:
                                    if hasattr(content, 'text'):
                                        result_text += content.text

                                # If the result references MCP resource URIs (e.g. screenshots),
                                # read them in the same session before it closes.
                                resources = []
                                if result_text:
                                    import re
                                    uris = set(re.findall(r'[a-zA-Z][a-zA-Z0-9+.-]*://[^\s<>"\')\]]+', result_text))
                                    for uri in uris:
                                        if uri.startswith(('http://', 'https://', 'data:', 'mailto:')):
                                            continue
                                        try:
                                            resource = await session.read_resource(uri)
                                            if resource and hasattr(resource, 'contents'):
                                                for content in resource.contents:
                                                    if hasattr(content, 'blob'):
                                                        resources.append({
                                                            "uri": uri,
                                                            "mimeType": getattr(content, 'mimeType', None) or 'application/octet-stream',
                                                            "blob": content.blob,
                                                        })
                                        except Exception:
                                            pass

                                tool_call_result = {
                                    "tool_name": test_tool,
                                    "arguments": test_args,
                                    "success": True,
                                    "result": result_text,
                                    "resources": resources,
                                }
                            except Exception as e:
                                tool_call_result = {
                                    "tool_name": test_tool,
                                    "arguments": test_args,
                                    "success": False,
                                    "error": str(e),
                                    "resources": [],
                                }

                    return {
                        "status": "success",
                        "file_path": file_path,
                        "mcp_type": mcp_type_norm,
                        "command": launch_command,
                        "args": launch_args,
                        "message": "MCP server connected and tools tested successfully",
                        "tools_count": len(tools_list),
                        "tools": tools_list,
                        "tool_call_result": tool_call_result,
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

            def _flatten_exc(exc, depth=0):
                """Recursively unwrap ExceptionGroup to reach leaf exceptions."""
                leaves = []
                subs = getattr(exc, "exceptions", None)
                if subs:
                    for sub in subs:
                        leaves.extend(_flatten_exc(sub, depth + 1))
                else:
                    leaves.append(f"{type(exc).__name__}: {exc}")
                return leaves

            leaf_errors = _flatten_exc(e)
            if leaf_errors:
                error_msg = f"{str(e)}; root-causes: {' | '.join(leaf_errors)}"

            # Capture the child process's stderr (if any) to surface the real
            # reason a command-based stdio MCP exited during startup.
            server_stderr = ""
            try:
                if stderr_log_file is not None:
                    stderr_log_file.flush()
                if stderr_log_path and os.path.exists(stderr_log_path):
                    with open(stderr_log_path, 'r', encoding='utf-8', errors='replace') as fh:
                        server_stderr = fh.read().strip()
            except Exception:
                pass
            if server_stderr:
                error_msg = f"{error_msg}; server-stderr: {server_stderr[:1500]}"

            error_trace = traceback.format_exc()
            return {
                "status": "error",
                "file_path": file_path,
                "mcp_type": mcp_type,
                "command": locals().get("launch_command"),
                "args": locals().get("launch_args"),
                "message": f"MCP server test failed: {error_msg}",
                "error": error_msg,
                "server_stderr": server_stderr[:1500],
                "traceback": error_trace[:4000],  # Limit traceback
                "tools": [],
                "tool_call_result": None
            }
        finally:
            try:
                if 'stderr_log_file' in locals() and stderr_log_file is not None:
                    stderr_log_file.close()
                if 'stderr_log_path' in locals() and stderr_log_path and os.path.exists(stderr_log_path):
                    os.unlink(stderr_log_path)
            except Exception:
                pass

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
        from db.repositories import KeyValueRepository
        from db.database import get_db_session
        from db.models.tools import McpMng

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
            parameter = mcp_data.parameter or '{}'

            if not file_path:
                return {
                    "success": False,
                    "error": "MCP server file_path is required"
                }

            # Allow stdio MCPs to be launched via a PATH command (e.g. uvx, npx)
            # in addition to a local script path, mirroring _test_mcp_server.
            stdio_command_resolved = None
            if not os.path.exists(file_path):
                resolved = shutil.which(str(file_path))
                if resolved:
                    stdio_command_resolved = resolved
                else:
                    return {
                        "success": False,
                        "error": f"MCP server file/command not found: {file_path}"
                    }

        finally:
            db.close()

        # Setup stderr capture for diagnostics on Windows command-based MCPs
        stderr_log_path = None
        stderr_log_file = None
        if mcp_type == 'stdio':
            import tempfile
            stderr_log_file = tempfile.NamedTemporaryFile(
                mode='w', suffix='.log', prefix='mcp_stderr_', delete=False, encoding='utf-8'
            )
            stderr_log_path = stderr_log_file.name

        try:
            # Prepare environment with UTF-8 encoding (for Windows compatibility)
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'

            # Parse launch parameters (args/env) from the MCP 'parameter' field,
            # mirroring _test_mcp_server so command-based MCPs receive their args.
            stdio_args: list[str] = []
            if parameter:
                try:
                    p = json.loads(parameter) if isinstance(parameter, str) else parameter
                    if isinstance(p, list):
                        stdio_args = [str(x) for x in p]
                    elif isinstance(p, dict):
                        if isinstance(p.get('args'), list):
                            stdio_args = [str(x) for x in p.get('args')]
                        if isinstance(p.get('env'), dict):
                            env.update({str(k): str(v) for k, v in p.get('env').items()})
                except Exception:
                    # Ignore parameter parse errors for backward compatibility
                    pass

            # Determine command to start server
            if file_path.endswith('.py'):
                cmd = [get_python_executable(), file_path] + stdio_args
            else:
                cmd = [stdio_command_resolved or file_path] + stdio_args

            # Windows: .cmd/.bat wrappers (e.g. npx.CMD, uvx) cannot be
            # reliably launched directly via CreateProcess for stdio piping,
            # which results in "Connection closed" during initialize().
            # Launch them through cmd.exe /c instead.
            if os.name == 'nt' and str(cmd[0]).lower().endswith(('.cmd', '.bat')):
                cmd = ['cmd', '/c'] + cmd

            # Set up MCP client parameters
            server_params = StdioServerParameters(
                command=cmd[0],
                args=cmd[1:] if len(cmd) > 1 else [],
                env=env
            )

            # Command-based stdio MCPs (e.g. npx) can take a long time to start.
            total_timeout = 180 if mcp_type == 'stdio' else 60
            async with asyncio.timeout(total_timeout):
                async with AsyncExitStack() as stack:
                    # Start stdio transport
                    # Pass errlog only if this mcp SDK version supports it.
                    try:
                        import inspect
                        _supports_errlog = 'errlog' in inspect.signature(stdio_client).parameters
                    except (ValueError, TypeError):
                        _supports_errlog = False

                    if _supports_errlog and stderr_log_file is not None:
                        stdio_transport = await stack.enter_async_context(
                            stdio_client(server_params, errlog=stderr_log_file)
                        )
                    else:
                        stdio_transport = await stack.enter_async_context(stdio_client(server_params))
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
            error_msg = str(e)

            def _flatten_exc(exc, depth=0):
                leaves = []
                subs = getattr(exc, "exceptions", None)
                if subs:
                    for sub in subs:
                        leaves.extend(_flatten_exc(sub, depth + 1))
                else:
                    leaves.append(f"{type(exc).__name__}: {exc}")
                return leaves

            leaf_errors = _flatten_exc(e)
            if leaf_errors:
                error_msg = f"{str(e)}; root-causes: {' | '.join(leaf_errors)}"

            # Surface child stderr so we can see why the command-based MCP exited.
            server_stderr = ""
            try:
                if stderr_log_file is not None:
                    stderr_log_file.flush()
                if stderr_log_path and os.path.exists(stderr_log_path):
                    with open(stderr_log_path, 'r', encoding='utf-8', errors='replace') as fh:
                        server_stderr = fh.read().strip()
            except Exception:
                pass
            if server_stderr:
                error_msg = f"{error_msg}; server-stderr: {server_stderr[:1500]}"

            full_error = f"MCP tool execution failed: {error_msg}"
            error_trace = traceback.format_exc()
            self.log_execution("mcp_tool", mcp_id, "error", full_error, error_trace[:500])

            return {
                "success": False,
                "error": full_error,
                "server_stderr": server_stderr[:1500],
            }
        finally:
            try:
                if 'stderr_log_file' in locals() and stderr_log_file is not None:
                    stderr_log_file.close()
                if 'stderr_log_path' in locals() and stderr_log_path and os.path.exists(stderr_log_path):
                    os.unlink(stderr_log_path)
            except Exception:
                pass

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
