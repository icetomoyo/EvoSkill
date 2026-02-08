"""
Koda CLI - 命令行工具

Usage:
    koda init              # 初始化项目
    koda generate <task>   # 生成代码
    koda validate          # 验证代码
    koda run               # 执行代码
    koda config            # 配置管理
"""
import asyncio
import sys
import argparse
from pathlib import Path
from typing import List, Optional


def print_banner():
    """打印 Logo"""
    print("""
 _  __     _       _                
| |/ /    | |     | |               
| ' / ___ | | __ _| |__   ___  __ _ 
|  < / _ \\| |/ _` | '_ \\ / _ \\/ _` |
| . \\ (_) | | (_| | |_) |  __/ (_| |
|_|\\_\\___/|_|\\__,_|_.__/ \\___|\\__,_|
                                      
Koda - Autonomous Coding Agent Framework v0.1.0
    """)


async def cmd_init(args):
    """初始化项目"""
    workspace = Path(args.workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    
    # 创建配置文件
    from koda.config import KodaConfig
    config = KodaConfig()
    config.workspace = str(workspace)
    config.save(workspace / ".koda.yaml")
    
    # 创建工作目录
    (workspace / "src").mkdir(exist_ok=True)
    (workspace / "tests").mkdir(exist_ok=True)
    (workspace / "docs").mkdir(exist_ok=True)
    
    print(f"✓ Initialized Koda workspace: {workspace}")
    print(f"  - Created .koda.yaml")
    print(f"  - Created src/, tests/, docs/")


async def cmd_generate(args):
    """生成代码"""
    print(f"Generating code for: {args.task}")
    
    # 这里简化处理，实际应该创建 KodaAgent 并执行
    from koda.config import KodaConfig
    config = KodaConfig.load()
    
    print(f"Using model: {config.llm.model}")
    print("Code generation would start here...")
    print("(Implementation requires LLM configuration)")


async def cmd_validate(args):
    """验证代码"""
    target = Path(args.file) if args.file else Path(".")
    
    print(f"Validating: {target}")
    
    if not target.exists():
        print(f"✗ Path not found: {target}")
        return 1
    
    # 简单验证
    import ast
    
    if target.is_file():
        files = [target]
    else:
        files = list(target.rglob("*.py"))
    
    errors = 0
    for file in files:
        try:
            with open(file, 'r', encoding='utf-8') as f:
                content = f.read()
            ast.parse(content)
            print(f"✓ {file}")
        except SyntaxError as e:
            print(f"✗ {file}: {e}")
            errors += 1
    
    print(f"\nChecked {len(files)} files, {errors} errors")
    return 0 if errors == 0 else 1


async def cmd_config(args):
    """配置管理"""
    from koda.config import KodaConfig
    
    if args.show:
        config = KodaConfig.load()
        print("Current configuration:")
        print(f"  LLM Provider: {config.llm.provider}")
        print(f"  LLM Model: {config.llm.model}")
        print(f"  Workspace: {config.workspace}")
        print(f"  Max Iterations: {config.agent.max_iterations}")
        print(f"  Verbose: {config.agent.verbose}")
    elif args.init:
        config = KodaConfig()
        config.save(".koda.yaml")
        print("✓ Created .koda.yaml")
    else:
        print("Use --show to display config or --init to create default")


async def main(args: Optional[List[str]] = None):
    """主入口"""
    parser = argparse.ArgumentParser(
        prog="koda",
        description="Koda - Autonomous Coding Agent Framework",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # init
    init_parser = subparsers.add_parser("init", help="Initialize workspace")
    init_parser.add_argument("--workspace", default=".", help="Workspace path")
    
    # generate
    gen_parser = subparsers.add_parser("generate", help="Generate code")
    gen_parser.add_argument("task", help="Task description")
    gen_parser.add_argument("--output", "-o", help="Output directory")
    
    # validate
    val_parser = subparsers.add_parser("validate", help="Validate code")
    val_parser.add_argument("--file", "-f", help="File to validate")
    
    # config
    cfg_parser = subparsers.add_parser("config", help="Manage configuration")
    cfg_parser.add_argument("--show", action="store_true", help="Show config")
    cfg_parser.add_argument("--init", action="store_true", help="Create default config")
    
    # parse
    parsed = parser.parse_args(args)
    
    if not parsed.command:
        print_banner()
        parser.print_help()
        return 0
    
    # dispatch
    commands = {
        "init": cmd_init,
        "generate": cmd_generate,
        "validate": cmd_validate,
        "config": cmd_config,
    }
    
    if parsed.command in commands:
        return await commands[parsed.command](parsed) or 0
    else:
        print(f"Unknown command: {parsed.command}")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\nInterrupted")
        sys.exit(130)
