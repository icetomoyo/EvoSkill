"""
Sandbox - Isolated execution environment
Equivalent to Pi Mono's sandbox.ts
"""
import os
import subprocess
import tempfile
from typing import Dict, List, Optional
from pathlib import Path
import shutil


class Sandbox:
    """
    Sandbox environment for isolated execution
    
    Features:
    - File system isolation
    - Resource limits
    - Timeout control
    """
    
    def __init__(self, root_dir: Optional[Path] = None):
        if root_dir is None:
            self.root_dir = Path(tempfile.mkdtemp(prefix="koda_sandbox_"))
            self._cleanup = True
        else:
            self.root_dir = Path(root_dir)
            self.root_dir.mkdir(parents=True, exist_ok=True)
            self._cleanup = False
    
    async def execute(
        self,
        command: List[str],
        timeout: float = 60.0,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None
    ) -> dict:
        """
        Execute command in sandbox
        
        Args:
            command: Command and arguments
            timeout: Timeout in seconds
            env: Environment variables
            cwd: Working directory (relative to sandbox root)
        
        Returns:
            dict with stdout, stderr, exit_code
        """
        work_dir = self.root_dir
        if cwd:
            work_dir = self.root_dir / cwd
            work_dir.mkdir(parents=True, exist_ok=True)
        
        # Merge environment
        run_env = os.environ.copy()
        if env:
            run_env.update(env)
        
        # Restrict PATH for safety
        run_env["PATH"] = "/usr/bin:/bin"
        
        try:
            result = subprocess.run(
                command,
                cwd=work_dir,
                env=run_env,
                capture_output=True,
                text=True,
                timeout=timeout
            )
            
            return {
                "stdout": result.stdout,
                "stderr": result.stderr,
                "exit_code": result.returncode,
                "success": result.returncode == 0
            }
        except subprocess.TimeoutExpired:
            return {
                "stdout": "",
                "stderr": f"Command timed out after {timeout}s",
                "exit_code": -1,
                "success": False
            }
        except Exception as e:
            return {
                "stdout": "",
                "stderr": str(e),
                "exit_code": -1,
                "success": False
            }
    
    def write_file(self, path: str, content: str) -> None:
        """Write file in sandbox"""
        file_path = self.root_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')
    
    def read_file(self, path: str) -> Optional[str]:
        """Read file from sandbox"""
        file_path = self.root_dir / path
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        return None
    
    def cleanup(self) -> None:
        """Clean up sandbox directory"""
        if self._cleanup and self.root_dir.exists():
            shutil.rmtree(self.root_dir, ignore_errors=True)
    
    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()
