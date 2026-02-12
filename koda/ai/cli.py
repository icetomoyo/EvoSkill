#!/usr/bin/env python3
"""
Koda AI CLI
等效于 Pi-Mono 的 packages/ai/src/cli.ts

AI包的独立CLI工具，用于OAuth登录和模型管理。

Usage:
    koda-ai login [provider]    # 登录到OAuth provider
    koda-ai logout [provider]   # 登出OAuth provider
    koda-ai status [provider]   # 查看登录状态
    koda-ai list                # 列出可用providers
    koda-ai models [provider]   # 列出可用模型
    koda-ai config              # 配置管理
    koda-ai refresh [provider]  # 刷新token
"""

import argparse
import asyncio
import json
import os
import sys
import time
import stat
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List

from .models import get_providers, get_models, ModelInfo, find_models
from .providers.oauth.types import OAuthCredentials, OAuthProviderId


# Default auth file location
DEFAULT_AUTH_FILE = Path.home() / ".koda" / "auth.json"
DEFAULT_CONFIG_DIR = Path.home() / ".koda"


class OAuthStorage:
    """
    OAuth Token Storage

    Secure storage for OAuth tokens with file permissions.
    """

    def __init__(self, auth_file: Optional[Path] = None):
        self.auth_file = auth_file or DEFAULT_AUTH_FILE

    def load(self) -> Dict[str, Any]:
        """Load all stored credentials"""
        if not self.auth_file.exists():
            return {}
        try:
            with open(self.auth_file, "r") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            return {}

    def save(self, auth: Dict[str, Any]) -> None:
        """Save credentials with secure file permissions"""
        self.auth_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.auth_file, "w") as f:
            json.dump(auth, f, indent=2)
        # Set secure file permissions (read/write for owner only)
        self.auth_file.chmod(stat.S_IRUSR | stat.S_IWUSR)

    def load_provider(self, provider_id: str) -> Optional[OAuthCredentials]:
        """Load credentials for a specific provider"""
        auth = self.load()
        if provider_id not in auth:
            return None
        data = auth[provider_id]
        if data.get("type") != "oauth":
            return None
        return OAuthCredentials.from_dict(data)

    def save_provider(self, provider_id: str, credentials: OAuthCredentials) -> None:
        """Save credentials for a specific provider"""
        auth = self.load()
        auth[provider_id] = {
            "type": "oauth",
            "provider_id": provider_id,
            "authenticated_at": datetime.now().isoformat(),
            **credentials.to_dict(),
        }
        self.save(auth)

    def delete_provider(self, provider_id: str) -> bool:
        """Delete credentials for a specific provider"""
        auth = self.load()
        if provider_id in auth:
            del auth[provider_id]
            self.save(auth)
            return True
        return False

    def get_all_providers(self) -> Dict[str, Dict[str, Any]]:
        """Get all stored provider data"""
        return self.load()


def load_auth(auth_file: Optional[Path] = None) -> Dict[str, Any]:
    """加载认证信息"""
    storage = OAuthStorage(auth_file)
    return storage.load()


def save_auth(auth: Dict[str, Any], auth_file: Optional[Path] = None) -> None:
    """保存认证信息"""
    storage = OAuthStorage(auth_file)
    storage.save(auth)


@dataclass
class ProviderInfo:
    """OAuth Provider信息"""
    id: str
    name: str
    description: str
    requires_client_id: bool = False
    supports_refresh: bool = True
    default_client_id: Optional[str] = None
    auth_type: str = "oauth"  # oauth, device_flow, pkce


def get_oauth_providers() -> List[ProviderInfo]:
    """获取所有OAuth providers"""
    return [
        ProviderInfo(
            id="anthropic",
            name="Anthropic",
            description="Claude API via OAuth",
            requires_client_id=False,
            supports_refresh=False,
            auth_type="pkce",
        ),
        ProviderInfo(
            id="github-copilot",
            name="GitHub Copilot",
            description="GitHub Copilot API",
            requires_client_id=False,
            supports_refresh=False,
            default_client_id="Iv1.b507a08c87ecfe98",
            auth_type="device_flow",
        ),
        ProviderInfo(
            id="google-antigravity",
            name="Google Antigravity",
            description="Google Antigravity API",
            requires_client_id=True,
            supports_refresh=True,
            auth_type="pkce",
        ),
        ProviderInfo(
            id="google-gemini-cli",
            name="Google Gemini CLI",
            description="Google Gemini CLI API",
            requires_client_id=True,
            supports_refresh=True,
            auth_type="pkce",
        ),
        ProviderInfo(
            id="openai-codex",
            name="OpenAI Codex",
            description="OpenAI Codex CLI",
            requires_client_id=True,
            supports_refresh=True,
            auth_type="pkce",
        ),
    ]


async def login_command(provider_id: Optional[str] = None, client_id: Optional[str] = None) -> int:
    """
    登录命令

    Args:
        provider_id: Provider ID，如果不指定则交互式选择
        client_id: Optional client ID for providers that require it

    Returns:
        退出码
    """
    providers = get_oauth_providers()
    storage = OAuthStorage()

    # Select provider
    if provider_id is None:
        print("Select a provider:\n")
        for i, p in enumerate(providers, 1):
            # Show authentication status
            stored = storage.load_provider(p.id)
            status = "[authenticated]" if stored and not stored.is_expired() else ""
            print(f"  {i}. {p.name} - {p.description} {status}")
        print()

        try:
            choice = input(f"Enter number (1-{len(providers)}): ").strip()
            idx = int(choice) - 1
            if idx < 0 or idx >= len(providers):
                print("Invalid selection", file=sys.stderr)
                return 1
            provider_id = providers[idx].id
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled", file=sys.stderr)
            return 1

    # Validate provider
    provider_info = None
    for p in providers:
        if p.id == provider_id:
            provider_info = p
            break

    if not provider_info:
        print(f"Unknown provider: {provider_id}", file=sys.stderr)
        print("Use 'koda-ai list' to see available providers", file=sys.stderr)
        return 1

    print(f"\nLogging in to {provider_info.name}...")
    print(f"  Auth type: {provider_info.auth_type}")

    # Check if client ID is required
    if provider_info.requires_client_id and not client_id:
        # Try to load from environment or config
        env_var = f"{provider_id.upper().replace('-', '_')}_CLIENT_ID"
        client_id = os.environ.get(env_var)

        if not client_id:
            try:
                client_id = input(f"  Enter client ID for {provider_info.name}: ").strip()
                if not client_id:
                    print("Client ID is required for this provider", file=sys.stderr)
                    return 1
            except KeyboardInterrupt:
                print("\nCancelled", file=sys.stderr)
                return 1

    try:
        # Get the OAuth provider instance
        oauth = await _create_oauth_provider(provider_id, client_id or provider_info.default_client_id)

        if oauth is None:
            print(f"Provider {provider_id} not implemented", file=sys.stderr)
            return 1

        # Define callbacks
        def on_auth(info):
            print(f"\n{'='*60}")
            print(info.format_message())
            print('='*60)

        async def on_prompt(prompt):
            return input(f"  {prompt.message}: ").strip()

        def on_progress(msg):
            print(f"  [>] {msg}")

        # Perform login
        credentials = await oauth.login(
            on_auth=on_auth,
            on_prompt=on_prompt,
            on_progress=on_progress,
        )

        # Save credentials
        storage.save_provider(provider_id, credentials)

        print(f"\n[OK] Successfully logged in to {provider_info.name}")
        print(f"     Credentials saved to {storage.auth_file}")

        # Show token info
        if credentials.expires_at:
            expires_dt = datetime.fromtimestamp(credentials.expires_at)
            print(f"     Token expires: {expires_dt.strftime('%Y-%m-%d %H:%M:%S')}")
        else:
            print("     Token does not expire")

        return 0

    except KeyboardInterrupt:
        print("\n\nCancelled", file=sys.stderr)
        return 130
    except Exception as e:
        print(f"\n[ERROR] Login failed: {e}", file=sys.stderr)
        import traceback
        if os.environ.get("KODA_DEBUG"):
            traceback.print_exc()
        return 1


async def _create_oauth_provider(provider_id: str, client_id: Optional[str] = None):
    """
    Create OAuth provider instance.

    Args:
        provider_id: Provider identifier
        client_id: Optional client ID

    Returns:
        OAuth provider instance or None
    """
    if provider_id == "anthropic":
        from .providers.oauth.anthropic import AnthropicOAuth
        return AnthropicOAuth(client_id=client_id or "anthropic-cli")

    elif provider_id == "github-copilot":
        from .providers.oauth.github_copilot_oauth import GitHubCopilotOAuth
        return GitHubCopilotOAuth(client_id=client_id)

    elif provider_id == "google-antigravity":
        from .providers.oauth.google_antigravity_oauth import GoogleAntigravityOAuth
        if not client_id:
            raise ValueError("Client ID required for Google Antigravity")
        return GoogleAntigravityOAuth(client_id=client_id)

    elif provider_id == "google-gemini-cli":
        from .providers.oauth.google_gemini_cli_oauth import GoogleGeminiCLIOAuth
        if not client_id:
            raise ValueError("Client ID required for Google Gemini CLI")
        return GoogleGeminiCLIOAuth(client_id=client_id)

    elif provider_id == "openai-codex":
        from .providers.oauth.openai_codex_oauth import OpenAICodexOAuth
        if not client_id:
            raise ValueError("Client ID required for OpenAI Codex")
        return OpenAICodexOAuth(client_id=client_id)

    return None


async def logout_command(provider_id: Optional[str] = None) -> int:
    """
    登出命令

    Args:
        provider_id: Provider ID，如果不指定则交互式选择

    Returns:
        退出码
    """
    providers = get_oauth_providers()
    storage = OAuthStorage()

    # Get authenticated providers
    auth = storage.get_all_providers()
    authenticated = {pid: data for pid, data in auth.items() if data.get("type") == "oauth"}

    if not authenticated:
        print("No authenticated providers.")
        return 0

    # Select provider
    if provider_id is None:
        print("Select a provider to logout:\n")
        auth_providers = []
        for p in providers:
            if p.id in authenticated:
                auth_providers.append(p)
                print(f"  {len(auth_providers)}. {p.name}")

        if not auth_providers:
            print("No authenticated providers.")
            return 0

        print(f"  {len(auth_providers) + 1}. Logout from all providers")
        print()

        try:
            choice = input(f"Enter number (1-{len(auth_providers) + 1}): ").strip()
            idx = int(choice) - 1
            if idx < 0:
                print("Invalid selection", file=sys.stderr)
                return 1
            elif idx == len(auth_providers):
                # Logout all
                for pid in list(authenticated.keys()):
                    storage.delete_provider(pid)
                    print(f"  [OK] Logged out from {pid}")
                print("\nLogged out from all providers.")
                return 0
            else:
                provider_id = auth_providers[idx].id
        except (ValueError, KeyboardInterrupt):
            print("\nCancelled", file=sys.stderr)
            return 1

    # Validate provider
    if provider_id not in authenticated:
        print(f"Not logged in to {provider_id}")
        return 1

    # Perform logout
    try:
        # Try to call provider's logout method
        oauth = await _create_oauth_provider(provider_id)
        if oauth and hasattr(oauth, 'logout'):
            await oauth.logout()
    except Exception:
        pass  # Ignore errors during provider logout

    # Delete stored credentials
    if storage.delete_provider(provider_id):
        print(f"[OK] Logged out from {provider_id}")
        return 0
    else:
        print(f"[ERROR] Failed to logout from {provider_id}", file=sys.stderr)
        return 1


async def status_command(provider_id: Optional[str] = None, verbose: bool = False) -> int:
    """
    查看登录状态命令

    Args:
        provider_id: Provider ID，如果不指定则显示所有
        verbose: Show detailed information

    Returns:
        退出码
    """
    providers = get_oauth_providers()
    storage = OAuthStorage()

    auth = storage.get_all_providers()

    print("OAuth Login Status\n")
    print("=" * 60)

    if provider_id:
        # Show status for specific provider
        provider_info = None
        for p in providers:
            if p.id == provider_id:
                provider_info = p
                break

        if not provider_info:
            print(f"Unknown provider: {provider_id}")
            return 1

        _print_provider_status(provider_info, auth.get(provider_id), verbose)
    else:
        # Show status for all providers
        for p in providers:
            _print_provider_status(p, auth.get(p.id), verbose)
            print()

    return 0


def _print_provider_status(provider: ProviderInfo, data: Optional[Dict[str, Any]], verbose: bool) -> None:
    """Print status for a single provider"""
    if data and data.get("type") == "oauth":
        # Load credentials to check expiration
        storage = OAuthStorage()
        creds = storage.load_provider(provider.id)

        if creds and not creds.is_expired():
            status = "[AUTHENTICATED]"
            status_color = "green"
        elif creds and creds.is_expired():
            status = "[EXPIRED]"
            status_color = "yellow"
        else:
            status = "[INVALID]"
            status_color = "red"

        print(f"{provider.name}: {status}")
        print(f"  Provider ID: {provider.id}")

        if verbose and creds:
            # Show token details
            if creds.expires_at:
                expires_dt = datetime.fromtimestamp(creds.expires_at)
                now = datetime.now()
                if expires_dt > now:
                    remaining = expires_dt - now
                    print(f"  Expires: {expires_dt.strftime('%Y-%m-%d %H:%M:%S')} (in {remaining})")
                else:
                    print(f"  Expired: {expires_dt.strftime('%Y-%m-%d %H:%M:%S')}")

            if data.get("authenticated_at"):
                print(f"  Authenticated: {data['authenticated_at']}")

            if creds.token_type:
                print(f"  Token Type: {creds.token_type}")

            # Show partial token (for debugging)
            if verbose > 1 and creds.access_token:
                token_preview = creds.access_token[:20] + "..." if len(creds.access_token) > 20 else creds.access_token
                print(f"  Access Token: {token_preview}")
    else:
        print(f"{provider.name}: [NOT LOGGED IN]")
        print(f"  Provider ID: {provider.id}")
        print(f"  Description: {provider.description}")
        if provider.requires_client_id:
            print("  Note: Requires client ID")


async def refresh_command(provider_id: Optional[str] = None) -> int:
    """
    刷新token命令

    Args:
        provider_id: Provider ID，如果不指定则刷新所有

    Returns:
        退出码
    """
    providers = get_oauth_providers()
    storage = OAuthStorage()

    auth = storage.get_all_providers()
    authenticated = {pid: data for pid, data in auth.items() if data.get("type") == "oauth"}

    if not authenticated:
        print("No authenticated providers to refresh.")
        return 0

    # Select provider
    if provider_id is None:
        # Refresh all that support it
        refreshed = 0
        for pid, data in authenticated.items():
            provider_info = None
            for p in providers:
                if p.id == pid:
                    provider_info = p
                    break

            if provider_info and provider_info.supports_refresh:
                try:
                    result = await _refresh_provider_token(pid, provider_info, storage)
                    if result:
                        refreshed += 1
                except Exception as e:
                    print(f"[ERROR] Failed to refresh {pid}: {e}")

        print(f"\nRefreshed {refreshed} token(s)")
        return 0

    # Refresh specific provider
    provider_info = None
    for p in providers:
        if p.id == provider_id:
            provider_info = p
            break

    if not provider_info:
        print(f"Unknown provider: {provider_id}")
        return 1

    if provider_id not in authenticated:
        print(f"Not logged in to {provider_info.name}")
        return 1

    if not provider_info.supports_refresh:
        print(f"{provider_info.name} does not support token refresh.")
        print("Please logout and login again.")
        return 1

    try:
        result = await _refresh_provider_token(provider_id, provider_info, storage)
        return 0 if result else 1
    except Exception as e:
        print(f"[ERROR] Failed to refresh token: {e}", file=sys.stderr)
        return 1


async def _refresh_provider_token(provider_id: str, provider_info: ProviderInfo, storage: OAuthStorage) -> bool:
    """Refresh token for a specific provider"""
    print(f"Refreshing token for {provider_info.name}...")

    creds = storage.load_provider(provider_id)
    if not creds or not creds.refresh_token:
        print(f"  [SKIP] No refresh token available for {provider_id}")
        return False

    try:
        # Create provider instance and refresh
        oauth = await _create_oauth_provider(provider_id)
        if not oauth:
            print(f"  [ERROR] Could not create OAuth instance for {provider_id}")
            return False

        # Call refresh method
        if hasattr(oauth, 'refresh'):
            new_creds = await oauth.refresh(creds)
            storage.save_provider(provider_id, new_creds)
            print(f"  [OK] Token refreshed for {provider_id}")
            return True
        else:
            print(f"  [SKIP] Provider does not support refresh")
            return False

    except Exception as e:
        print(f"  [ERROR] Refresh failed: {e}")
        return False


async def list_command() -> int:
    """列出命令"""
    providers = get_oauth_providers()
    storage = OAuthStorage()
    auth = storage.load()

    print("Available OAuth providers:\n")
    print(f"{'ID':<25} {'Name':<20} {'Status':<20}")
    print("-" * 65)

    for p in providers:
        data = auth.get(p.id)
        if data and data.get("type") == "oauth":
            creds = storage.load_provider(p.id)
            if creds and not creds.is_expired():
                status = "authenticated"
            elif creds and creds.is_expired():
                status = "expired"
            else:
                status = "invalid"
        else:
            status = "not authenticated"

        print(f"{p.id:<25} {p.name:<20} {status}")

    print()
    return 0


async def models_command(provider: Optional[str] = None) -> int:
    """
    模型列表命令

    Args:
        provider: 可选，按provider筛选
    """
    print("Available models:\n")

    providers_list = [provider] if provider else get_providers()

    for prov in providers_list:
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
    storage = OAuthStorage()
    auth_file = storage.auth_file

    print("Koda AI CLI Configuration\n")
    print("=" * 60)
    print(f"\nConfiguration Directory: {DEFAULT_CONFIG_DIR}")
    print(f"Auth File: {auth_file}")
    print(f"Auth File Exists: {auth_file.exists()}")

    if auth_file.exists():
        auth = storage.load()
        print(f"\nStored Providers: {len([k for k, v in auth.items() if v.get('type') == 'oauth'])}")

        for provider_id, data in auth.items():
            if data.get("type") == "oauth":
                creds = storage.load_provider(provider_id)
                status = "valid" if creds and not creds.is_expired() else "expired/invalid"
                print(f"  - {provider_id}: {status}")

    print("\nEnvironment Variables:")
    env_vars = [
        "ANTHROPIC_CLIENT_ID",
        "GITHUB_COPILOT_CLIENT_ID",
        "GOOGLE_ANTIGRAVITY_CLIENT_ID",
        "GOOGLE_GEMINI_CLI_CLIENT_ID",
        "OPENAI_CODEX_CLIENT_ID",
        "KODA_DEBUG",
    ]
    for var in env_vars:
        value = os.environ.get(var)
        if value:
            print(f"  {var}: {'*' * 8} (set)")
        else:
            print(f"  {var}: (not set)")

    print()
    return 0


def main() -> int:
    """主入口"""
    parser = argparse.ArgumentParser(
        prog="koda-ai",
        description="Koda AI CLI - OAuth and model management",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  koda-ai login                  # Interactive login
  koda-ai login anthropic        # Login to specific provider
  koda-ai status                 # View all login statuses
  koda-ai status anthropic -v    # Verbose status for provider
  koda-ai logout                 # Interactive logout
  koda-ai refresh                # Refresh all tokens
  koda-ai list                   # List all providers

For more information, visit: https://github.com/example/koda
        """,
    )

    subparsers = parser.add_subparsers(dest="command", help="Commands")

    # login command
    login_parser = subparsers.add_parser("login", help="Login to an OAuth provider")
    login_parser.add_argument(
        "provider",
        nargs="?",
        help="Provider ID (anthropic, github-copilot, google-gemini-cli, openai-codex)",
    )
    login_parser.add_argument(
        "--client-id", "-c",
        help="OAuth client ID (for providers that require it)",
    )

    # logout command
    logout_parser = subparsers.add_parser("logout", help="Logout from an OAuth provider")
    logout_parser.add_argument(
        "provider",
        nargs="?",
        help="Provider ID to logout from",
    )

    # status command
    status_parser = subparsers.add_parser("status", help="View login status")
    status_parser.add_argument(
        "provider",
        nargs="?",
        help="Provider ID to check status for",
    )
    status_parser.add_argument(
        "--verbose", "-v",
        action="count",
        default=0,
        help="Show detailed status (use -vv for more details)",
    )

    # refresh command
    refresh_parser = subparsers.add_parser("refresh", help="Refresh OAuth tokens")
    refresh_parser.add_argument(
        "provider",
        nargs="?",
        help="Provider ID to refresh (omit to refresh all)",
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
        return asyncio.run(login_command(args.provider, getattr(args, 'client_id', None)))

    elif command == "logout":
        return asyncio.run(logout_command(args.provider))

    elif command == "status":
        return asyncio.run(status_command(args.provider, args.verbose))

    elif command == "refresh":
        return asyncio.run(refresh_command(args.provider))

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
