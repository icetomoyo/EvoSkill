#!/usr/bin/env python3
"""
Koda AI CLI
等效于 Pi-Mono 的 packages/ai/src/cli.ts

AI包的独立CLI工具，用于OAuth登录和模型管理。

Usage:
    koda-ai login [provider]    # 登录到OAuth provider
    koda-ai list                # 列出可用providers
    koda-ai models [provider]   # 列出可用模型
    koda-ai config              # 配置管理
"""

import argparse
import asyncio
import json
import os
import sys
from pathlib import Path
from typing import Optional, Dict, Any

from .models import get_providers, get_models, ModelInfo, find_models
from .providers.oauth.types import OAuthCredentials, OAuthProviderId


# Default auth file location
DEFAULT_AUTH_FILE = Path.home() / ".koda" / "auth.json"


def load_auth(auth_file: Optional[Path] = None) -> Dict[str, Any]:
    """加载认证信息"""
    file_path = auth_file or DEFAULT_AUTH_FILE
    if not file_path.exists():
        return {}
    try:
        with open(file_path, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return {}


def save_auth(auth: Dict[str, Any], auth_file: Optional[Path] = None) -> None:
    """保存认证信息"""
    file_path = auth_file or DEFAULT_AUTH_FILE
    file_path.parent.mkdir(parents=True, exist_ok=True)
    with open(file_path, "w") as f:
        json.dump(auth, f, indent=2)


def get_oauth_providers() -> list:
    """获取所有OAuth providers"""
    return [
        {"id": "anthropic", "name": "Anthropic", "description": "Claude API"},
        {"id": "github-copilot", "name": "GitHub Copilot", "description": "GitHub Copilot API"},
        {"id": "google-antigravity", "name": "Google Antigravity", "description": "Google Antigravity"},
        {"id": "google-gemini-cli", "name": "Google Gemini CLI", "description": "Google Gemini CLI"},
        {"id": "openai-codex", "name": "OpenAI Codex", "description": "OpenAI Codex CLI"},
    ]


async def login_command(provider_id: Optional[str] = None) -> int:
    """
    登录命令
    
    Args:
        provider_id: Provider ID，如果不指定则交互式选择
    
    Returns:
        退出码
    """
    providers = get_oauth_providers()
    
    # Select provider
    if provider_id is None:
        print("Select a provider:\n")
        for i, p in enumerate(providers, 1):
            print(f"  {i}. {p['name']} - {p['description']}")
        print()
        
        try:
            choice = input(f"Enter number (1-{len(providers)}): ").strip()
            idx = int(choice) - 1
            if idx < 0 or idx >= len(providers):
                print("Invalid selection", file=sys.stderr)
                return 1
            provider_id = providers[idx]["id"]
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled", file=sys.stderr)
            return 1
    
    # Validate provider
    provider_info = None
    for p in providers:
        if p["id"] == provider_id:
            provider_info = p
            break
    
    if not provider_info:
        print(f"Unknown provider: {provider_id}", file=sys.stderr)
        print("Use 'koda-ai list' to see available providers", file=sys.stderr)
        return 1
    
    print(f"Logging in to {provider_info['name']}...")
    
    try:
        # Import and use appropriate OAuth provider
        if provider_id == "anthropic":
            from .providers.oauth.anthropic import AnthropicOAuth
            oauth = AnthropicOAuth()
        elif provider_id == "github-copilot":
            from .providers.oauth.github_copilot_oauth import GitHubCopilotOAuth
            oauth = GitHubCopilotOAuth()
        elif provider_id == "google-antigravity":
            from .providers.oauth.google_antigravity_oauth import GoogleAntigravityOAuth
            oauth = GoogleAntigravityOAuth()
        elif provider_id == "google-gemini-cli":
            from .providers.oauth.google_gemini_cli_oauth import GoogleGeminiCLIOAuth
            oauth = GoogleGeminiCLIOAuth()
        elif provider_id == "openai-codex":
            from .providers.oauth.openai_codex_oauth import OpenAICodexOAuth
            oauth = OpenAICodexOAuth()
        else:
            print(f"Provider {provider_id} not implemented", file=sys.stderr)
            return 1
        
        # Define callbacks
        def on_auth(info):
            print(f"\n{info.format_message()}\n")
        
        async def on_prompt(prompt):
            return input(f"{prompt.message}: ").strip()
        
        def on_progress(msg):
            print(f"  {msg}")
        
        # Perform login
        credentials = await oauth.login(
            on_auth=on_auth,
            on_prompt=on_prompt,
            on_progress=on_progress,
        )
        
        # Save credentials
        auth = load_auth()
        auth[provider_id] = {
            "type": "oauth",
            **credentials.to_dict(),
        }
        save_auth(auth)
        
        print(f"\n✓ Credentials saved to {DEFAULT_AUTH_FILE}")
        return 0
        
    except KeyboardInterrupt:
        print("\n\nCancelled", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n✗ Error: {e}", file=sys.stderr)
        return 1


async def list_command() -> int:
    """列出命令"""
    providers = get_oauth_providers()
    auth = load_auth()
    
    print("Available OAuth providers:\n")
    for p in providers:
        status = "✓ authenticated" if p["id"] in auth else "○ not authenticated"
        print(f"  {p['id']:<25} {p['name']:<20} {status}")
    print()
    return 0


async def models_command(provider: Optional[str] = None) -> int:
    """
    模型列表命令
    
    Args:
        provider: 可选，按provider筛选
    """
    print("Available models:\n")
    
    providers = [provider] if provider else get_providers()
    
    for prov in providers:
        models = get_models(prov)
        if not models:
            continue
        
        print(f"\n{prov.upper()}:")
        print("-" * 80)
        
        for model in sorted(models, key=lambda m: m.cost.input):
            cost_str = f"${model.cost.input:.2f}/${model.cost.output:.2f}"
            caps = []
            if model.capabilities.vision:
                caps.append("vision")
            if model.capabilities.tools:
                caps.append("tools")
            if model.capabilities.reasoning:
                caps.append("reasoning")
            
            cap_str = f"[{', '.join(caps)}]" if caps else ""
            
            print(f"  {model.id:<40} {cost_str:<15} {cap_str}")
    
    print()
    return 0


async def config_command() -> int:
    """配置管理命令"""
    auth_file = DEFAULT_AUTH_FILE
    
    print("Configuration:\n")
    print(f"  Auth file: {auth_file}")
    print(f"  Exists: {auth_file.exists()}")
    
    if auth_file.exists():
        auth = load_auth()
        print(f"  Providers configured: {len(auth)}")
        for provider_id in auth.keys():
            print(f"    - {provider_id}")
    
    print()
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        prog="koda-ai",
        description="Koda AI CLI - OAuth and model management",
    )
    
    subparsers = parser.add_subparsers(dest="command", help="Commands")
    
    # login command
    login_parser = subparsers.add_parser("login", help="Login to an OAuth provider")
    login_parser.add_argument(
        "provider",
        nargs="?",
        help="Provider ID (anthropic, github-copilot, etc.)",
    )
    
    # list command
    subparsers.add_parser("list", help="List available providers")
    
    # models command
    models_parser = subparsers.add_parser("models", help="List available models")
    models_parser.add_argument(
        "provider",
        nargs="?",
        help="Filter by provider",
    )
    
    # config command
    subparsers.add_parser("config", help="Show configuration")
    
    # help is default
    parser.set_defaults(command="help")
    
    args = parser.parse_args()
    
    command = args.command
    
    if command == "help" or command is None:
        parser.print_help()
        return 0
    
    if command == "login":
        return asyncio.run(login_command(args.provider))
    
    elif command == "list":
        return asyncio.run(list_command())
    
    elif command == "models":
        return asyncio.run(models_command(args.provider))
    
    elif command == "config":
        return asyncio.run(config_command())
    
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
