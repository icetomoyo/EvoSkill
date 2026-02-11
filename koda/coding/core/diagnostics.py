"""
Diagnostics
等效于 Pi-Mono 的 packages/coding-agent/src/core/diagnostics.ts

诊断工具，用于问题排查和系统健康检查。
"""

import os
import sys
import platform
import asyncio
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json


@dataclass
class DiagnosticResult:
    """诊断结果"""
    name: str
    status: str  # "ok", "warning", "error"
    message: str
    details: Dict[str, Any] = field(default_factory=dict)
    suggestion: Optional[str] = None


class Diagnostics:
    """
    诊断工具
    
    检查系统健康状态和配置问题。
    
    Example:
        >>> diag = Diagnostics()
        >>> results = await diag.run_all_checks()
        >>> for r in results:
        ...     print(f"{r.name}: {r.status}")
    """
    
    def __init__(self):
        self.results: List[DiagnosticResult] = []
    
    async def run_all_checks(self) -> List[DiagnosticResult]:
        """运行所有检查"""
        self.results = []
        
        self.results.append(await self.check_python_version())
        self.results.append(await self.check_environment())
        self.results.append(await self.check_api_keys())
        self.results.append(await self.check_oauth_credentials())
        self.results.append(await self.check_config_files())
        self.results.append(await self.check_disk_space())
        self.results.append(await self.check_network())
        self.results.append(await self.check_dependencies())
        
        return self.results
    
    async def check_python_version(self) -> DiagnosticResult:
        """检查Python版本"""
        version = sys.version_info
        version_str = f"{version.major}.{version.minor}.{version.micro}"
        
        if version.major < 3 or (version.major == 3 and version.minor < 10):
            return DiagnosticResult(
                name="Python Version",
                status="error",
                message=f"Python {version_str} is too old",
                details={"version": version_str},
                suggestion="Upgrade to Python 3.10 or higher",
            )
        
        return DiagnosticResult(
            name="Python Version",
            status="ok",
            message=f"Python {version_str} is supported",
            details={"version": version_str},
        )
    
    async def check_environment(self) -> DiagnosticResult:
        """检查环境变量"""
        required_vars = []
        optional_vars = [
            "OPENAI_API_KEY",
            "ANTHROPIC_API_KEY",
            "KIMI_API_KEY",
            "GOOGLE_API_KEY",
        ]
        
        found = []
        missing = []
        
        for var in optional_vars:
            if os.getenv(var):
                found.append(var)
            else:
                missing.append(var)
        
        if not found:
            return DiagnosticResult(
                name="Environment Variables",
                status="warning",
                message="No API keys configured",
                details={"found": found, "missing": missing},
                suggestion="Set at least one API key in environment",
            )
        
        return DiagnosticResult(
            name="Environment Variables",
            status="ok",
            message=f"Found {len(found)} API keys",
            details={"found": found, "missing": missing},
        )
    
    async def check_api_keys(self) -> DiagnosticResult:
        """检查API keys格式"""
        # Check key formats
        checks = []
        
        openai_key = os.getenv("OPENAI_API_KEY", "")
        if openai_key and not openai_key.startswith("sk-"):
            checks.append("OPENAI_API_KEY format invalid")
        
        anthropic_key = os.getenv("ANTHROPIC_API_KEY", "")
        if anthropic_key and not anthropic_key.startswith("sk-ant-"):
            checks.append("ANTHROPIC_API_KEY format invalid")
        
        if checks:
            return DiagnosticResult(
                name="API Key Format",
                status="warning",
                message=f"Found {len(checks)} format issues",
                details={"issues": checks},
                suggestion="Verify your API keys are correct",
            )
        
        return DiagnosticResult(
            name="API Key Format",
            status="ok",
            message="API key formats look valid",
        )
    
    async def check_oauth_credentials(self) -> DiagnosticResult:
        """检查OAuth凭证"""
        auth_file = os.path.expanduser("~/.koda/auth.json")
        
        if not os.path.exists(auth_file):
            return DiagnosticResult(
                name="OAuth Credentials",
                status="ok",
                message="No OAuth credentials configured",
                details={"auth_file": auth_file},
            )
        
        try:
            with open(auth_file) as f:
                auth = json.load(f)
            
            providers = list(auth.keys())
            return DiagnosticResult(
                name="OAuth Credentials",
                status="ok",
                message=f"Found {len(providers)} OAuth providers",
                details={"providers": providers, "auth_file": auth_file},
            )
        except json.JSONDecodeError:
            return DiagnosticResult(
                name="OAuth Credentials",
                status="error",
                message="Auth file is corrupted",
                details={"auth_file": auth_file},
                suggestion="Delete the auth file and re-authenticate",
            )
    
    async def check_config_files(self) -> DiagnosticResult:
        """检查配置文件"""
        config_dirs = [
            os.path.expanduser("~/.koda"),
            os.path.expanduser("~/.config/koda"),
        ]
        
        found_configs = []
        for config_dir in config_dirs:
            if os.path.exists(config_dir):
                found_configs.append(config_dir)
        
        return DiagnosticResult(
            name="Config Files",
            status="ok",
            message=f"Found {len(found_configs)} config directories",
            details={"config_dirs": found_configs},
        )
    
    async def check_disk_space(self) -> DiagnosticResult:
        """检查磁盘空间"""
        try:
            import shutil
            stat = shutil.disk_usage(".")
            
            free_gb = stat.free / (1024**3)
            total_gb = stat.total / (1024**3)
            used_percent = (stat.used / stat.total) * 100
            
            if free_gb < 1:
                status = "error"
                suggestion = "Free up disk space immediately"
            elif free_gb < 5:
                status = "warning"
                suggestion = "Consider freeing up disk space"
            else:
                status = "ok"
                suggestion = None
            
            return DiagnosticResult(
                name="Disk Space",
                status=status,
                message=f"{free_gb:.1f} GB free ({used_percent:.1f}% used)",
                details={
                    "free_gb": free_gb,
                    "total_gb": total_gb,
                    "used_percent": used_percent,
                },
                suggestion=suggestion,
            )
        except Exception as e:
            return DiagnosticResult(
                name="Disk Space",
                status="warning",
                message=f"Could not check disk space: {e}",
            )
    
    async def check_network(self) -> DiagnosticResult:
        """检查网络连接"""
        # Try to connect to a few common endpoints
        endpoints = [
            ("api.openai.com", 443),
            ("api.anthropic.com", 443),
            ("google.com", 443),
        ]
        
        reachable = []
        unreachable = []
        
        for host, port in endpoints:
            try:
                reader, writer = await asyncio.wait_for(
                    asyncio.open_connection(host, port),
                    timeout=5,
                )
                writer.close()
                await writer.wait_closed()
                reachable.append(host)
            except Exception:
                unreachable.append(host)
        
        if not reachable:
            return DiagnosticResult(
                name="Network",
                status="error",
                message="No network connectivity",
                details={"reachable": reachable, "unreachable": unreachable},
                suggestion="Check your internet connection",
            )
        
        if unreachable:
            return DiagnosticResult(
                name="Network",
                status="warning",
                message=f"Some endpoints unreachable: {', '.join(unreachable)}",
                details={"reachable": reachable, "unreachable": unreachable},
            )
        
        return DiagnosticResult(
            name="Network",
            status="ok",
            message="Network connectivity OK",
            details={"reachable": reachable},
        )
    
    async def check_dependencies(self) -> DiagnosticResult:
        """检查依赖项"""
        required_packages = [
            "aiohttp",
        ]
        optional_packages = [
            "questionary",
            "tiktoken",
        ]
        
        missing_required = []
        missing_optional = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_required.append(package)
        
        for package in optional_packages:
            try:
                __import__(package)
            except ImportError:
                missing_optional.append(package)
        
        if missing_required:
            return DiagnosticResult(
                name="Dependencies",
                status="error",
                message=f"Missing required packages: {', '.join(missing_required)}",
                details={
                    "missing_required": missing_required,
                    "missing_optional": missing_optional,
                },
                suggestion="Install missing packages with pip",
            )
        
        if missing_optional:
            return DiagnosticResult(
                name="Dependencies",
                status="warning",
                message=f"Missing optional packages: {', '.join(missing_optional)}",
                details={
                    "missing_required": missing_required,
                    "missing_optional": missing_optional,
                },
                suggestion="Install optional packages for better experience",
            )
        
        return DiagnosticResult(
            name="Dependencies",
            status="ok",
            message="All dependencies satisfied",
        )
    
    def print_report(self, results: Optional[List[DiagnosticResult]] = None) -> None:
        """打印诊断报告"""
        if results is None:
            results = self.results
        
        print("\n" + "=" * 60)
        print("DIAGNOSTICS REPORT")
        print("=" * 60)
        print(f"Timestamp: {datetime.now().isoformat()}")
        print(f"Platform: {platform.platform()}")
        print("-" * 60)
        
        for result in results:
            status_icon = {
                "ok": "✓",
                "warning": "⚠",
                "error": "✗",
            }.get(result.status, "?")
            
            print(f"\n{status_icon} {result.name}")
            print(f"  Status: {result.status.upper()}")
            print(f"  Message: {result.message}")
            
            if result.suggestion:
                print(f"  Suggestion: {result.suggestion}")
        
        # Summary
        ok_count = sum(1 for r in results if r.status == "ok")
        warning_count = sum(1 for r in results if r.status == "warning")
        error_count = sum(1 for r in results if r.status == "error")
        
        print("\n" + "=" * 60)
        print(f"Summary: {ok_count} OK, {warning_count} Warnings, {error_count} Errors")
        print("=" * 60 + "\n")
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            "timestamp": datetime.now().isoformat(),
            "platform": platform.platform(),
            "python_version": sys.version,
            "results": [
                {
                    "name": r.name,
                    "status": r.status,
                    "message": r.message,
                    "details": r.details,
                    "suggestion": r.suggestion,
                }
                for r in self.results
            ],
        }


async def run_diagnostics() -> None:
    """运行诊断并打印报告"""
    diag = Diagnostics()
    await diag.run_all_checks()
    diag.print_report()


__all__ = [
    "DiagnosticResult",
    "Diagnostics",
    "run_diagnostics",
]
