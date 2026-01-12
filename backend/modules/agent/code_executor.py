# -*- coding: utf-8 -*-
"""
Code Executor - 代码执行器
负责安全地执行AI生成的代码
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
    代码执行器

    特性:
    1. 支持Python代码执行
    2. 沙箱隔离（使用临时目录）
    3. 超时控制
    4. 输出捕获
    """

    def __init__(
        self,
        work_dir: Optional[str] = None,
        timeout: int = 30,
        max_output_size: int = 10000
    ):
        """
        初始化代码执行器

        Args:
            work_dir: 工作目录，如果为None则使用临时目录
            timeout: 执行超时时间（秒）
            max_output_size: 最大输出大小（字符）
        """
        self.work_dir = work_dir or tempfile.mkdtemp(prefix="agent_code_")
        self.timeout = timeout
        self.max_output_size = max_output_size

        # 确保工作目录存在
        Path(self.work_dir).mkdir(parents=True, exist_ok=True)

        logger.info(f"代码执行器已初始化: work_dir={self.work_dir}, timeout={self.timeout}s")

    def execute_python(self, code: str, **kwargs) -> Dict[str, Any]:
        """
        执行Python代码

        Args:
            code: Python代码
            **kwargs: 额外参数

        Returns:
            执行结果字典 {
                'success': bool,
                'output': str,
                'error': str,
                'exit_code': int
            }
        """
        try:
            # 创建临时文件
            code_file = Path(self.work_dir) / f"code_{os.getpid()}.py"
            with open(code_file, 'w', encoding='utf-8') as f:
                f.write(code)

            # 执行代码
            result = subprocess.run(
                ['python', str(code_file)],
                cwd=self.work_dir,
                capture_output=True,
                text=True,
                timeout=self.timeout
            )

            # 限制输出大小
            stdout = result.stdout[:self.max_output_size] if result.stdout else ""
            stderr = result.stderr[:self.max_output_size] if result.stderr else ""

            # 删除临时文件
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
            logger.error(f"代码执行超时: {self.timeout}s")
            return {
                'success': False,
                'output': '',
                'error': f'Execution timeout ({self.timeout}s)',
                'exit_code': -1
            }

        except Exception as e:
            logger.error(f"代码执行失败: {e}", exc_info=True)
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1
            }

    def execute_shell(self, command: str, **kwargs) -> Dict[str, Any]:
        """
        执行Shell命令

        Args:
            command: Shell命令
            **kwargs: 额外参数

        Returns:
            执行结果字典
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
            logger.error(f"Shell命令执行失败: {e}")
            return {
                'success': False,
                'output': '',
                'error': str(e),
                'exit_code': -1
            }

    def cleanup(self):
        """清理工作目录"""
        try:
            import shutil
            if os.path.exists(self.work_dir) and self.work_dir.startswith(tempfile.gettempdir()):
                shutil.rmtree(self.work_dir)
                logger.info(f"工作目录已清理: {self.work_dir}")
        except Exception as e:
            logger.error(f"清理工作目录失败: {e}")
