# -*- coding: utf-8 -*-
"""
Code Executor - Code executor
Responsible for safely executing AI-generated code
"""
import logging
import subprocess
import tempfile
import os
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class CodeExecutor:
    """
    Code executor

    Features:
    1. Supports Python code execution
    2. Sandbox isolation (uses a temp directory)
    3. Timeout control
    4. Output capture
    """

    def __init__(
        self,
        work_dir: Optional[str] = None,
        timeout: int = 30,
        max_output_size: int = 10000
    ):
        """
        Initialize code executor.

        Args:
            work_dir: Working directory; if None, uses a temp directory
            timeout: Execution timeout (seconds)
            max_output_size: Max output size (characters)
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="agent_code_")
        self.timeout = timeout
        self.max_output_size = max_output_size

        # Ensure work directory exists
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"Code executor initialized: work_dir={self.work_dir}, timeout={self.timeout}s")

    def execute_python(self, code: str, **kwargs) -> Dict[str, Any]:
        """
        Execute Python code.

        Args:
            code: Python code
            **kwargs: Extra params

        Returns:
            Result dict {
                'success': bool,
                'output': str,
                'error': str,
                'exit_code': int
            }
        """
        try:
            # Create temp file
            code_file = Path(self.work_dir) / f"code_{os.getpid()}.py"
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)

            # Execute code
            result = subprocess.run(
                ['python', str(code_file)],
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # Limit output size
            stdout = result.stdout[:self.max_output_size] if result.stdout else ""
            stderr = result.stderr[:self.max_output_size] if result.stderr else ""

            # Delete temp file
            try:
                code_file.unlink()
            except:
                pass

            return {
                'success': result.returncode == 0,
                'output': stdout,
                'error': stderr,
                'exit_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            logger.error(f"Code execution timed out: {self.timeout}s")
            return {
                'success': False,
                'output': '',
                'error': f'Execution timeout ({self.timeout}s)',
                'exit_code': -1
            }

        except Exception as e:
            logger.error(f"Code execution failed: {e}", exc_info=True)
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1
            }

    def execute_shell(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a shell command.

        Args:
            command: Shell command
            **kwargs: Extra params

        Returns:
            Result dict
        """
        try:
            result = subprocess.run(
                command,
                shell=True,
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            stdout = result.stdout[:self.max_output_size] if result.stdout else ""
            stderr = result.stderr[:self.max_output_size] if result.stderr else ""

            return {
                'success': result.returncode == 0,
                'output': stdout,
                'error': stderr,
                'exit_code': result.returncode
            }

        except subprocess.TimeoutExpired:
            return {
                'success': False,
                'output': '',
                'error': f'Execution timeout ({self.timeout}s)',
                'exit_code': -1
            }

        except Exception as e:
            logger.error(f"Shell command execution failed: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1
            }

    def cleanup(self):
        """Clean up the working directory."""
        try:
            import shutil
            if os.path.exists(self.work_dir) and self.work_dir.startswith(tempfile.gettempdir()):
                shutil.rmtree(self.work_dir)
                logger.info(f"Work directory cleaned: {self.work_dir}")
        except Exception as e:
            logger.error(f"Failed to clean work directory: {e}")
