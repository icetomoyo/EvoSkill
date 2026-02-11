"""
Package Manager
Equivalent to Pi Mono's packages/coding-agent/src/core/package-manager.ts

Manages skill packages installation and updates.
"""
import os
import json
import shutil
import asyncio
from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field, asdict
from urllib.parse import urlparse

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class Package:
    """A skill package"""
    name: str
    version: str
    description: str = ""
    author: str = ""
    url: str = ""
    dependencies: List[str] = field(default_factory=list)
    install_path: Optional[str] = None


@dataclass
class PackageLock:
    """Lock file entry for installed package"""
    name: str
    version: str
    resolved: str
    integrity: str = ""


class PackageRegistry:
    """Registry of available packages"""
    
    def __init__(self, registry_url: str = "https://registry.koda.dev"):
        self._registry_url = registry_url
        self._cache: Dict[str, Package] = {}
    
    async def search(self, query: str, limit: int = 20) -> List[Package]:
        """Search for packages in registry"""
        # For now, return from cache or empty
        results = []
        query_lower = query.lower()
        
        for name, pkg in self._cache.items():
            if query_lower in name.lower() or query_lower in pkg.description.lower():
                results.append(pkg)
        
        return results[:limit]
    
    async def get_package(self, name: str) -> Optional[Package]:
        """Get package info from registry"""
        if not HAS_AIOHTTP:
            return None
        
        if name in self._cache:
            return self._cache[name]
        
        # Try to fetch from registry
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{self._registry_url}/packages/{name}"
                ) as response:
                    if response.status == 200:
                        data = await response.json()
                        pkg = Package(**data)
                        self._cache[name] = pkg
                        return pkg
        except Exception:
            pass
        
        return None
    
    def register_local(self, package: Package):
        """Register a local package"""
        self._cache[package.name] = package


class PackageManager:
    """
    Manages skill packages.
    
    Provides install, uninstall, update, and list operations.
    
    Example:
        >>> pm = PackageManager()
        >>> await pm.install("web-search")
        >>> pm.list_installed()
        ['web-search']
    """
    
    def __init__(
        self,
        packages_dir: Optional[str] = None,
        registry_url: str = "https://registry.koda.dev"
    ):
        """
        Initialize package manager.
        
        Args:
            packages_dir: Directory to install packages (default: ~/.koda/packages)
            registry_url: Package registry URL
        """
        self._packages_dir = Path(packages_dir or os.path.expanduser("~/.koda/packages"))
        self._packages_dir.mkdir(parents=True, exist_ok=True)
        
        self._registry = PackageRegistry(registry_url)
        self._lock_file = self._packages_dir / "koda-lock.json"
        self._installed: Dict[str, PackageLock] = {}
        
        self._load_lock()
    
    def _load_lock(self):
        """Load lock file with installed packages"""
        if self._lock_file.exists():
            try:
                with open(self._lock_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    for name, entry in data.get("packages", {}).items():
                        self._installed[name] = PackageLock(**entry)
            except (json.JSONDecodeError, TypeError):
                self._installed = {}
    
    def _save_lock(self):
        """Save lock file"""
        data = {
            "packages": {
                name: asdict(lock) for name, lock in self._installed.items()
            }
        }
        with open(self._lock_file, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
    
    async def install(
        self,
        package_name: str,
        version: Optional[str] = None,
        force: bool = False
    ) -> bool:
        """
        Install a package.
        
        Args:
            package_name: Package name or URL
            version: Specific version to install
            force: Reinstall if already installed
            
        Returns:
            True if installation succeeded
        """
        # Check if already installed
        if package_name in self._installed and not force:
            print(f"Package {package_name} already installed. Use --force to reinstall.")
            return False
        
        # Get package info
        if package_name.startswith("http://") or package_name.startswith("https://"):
            # Install from URL
            pkg = await self._install_from_url(package_name, version)
        elif package_name.startswith("file://") or os.path.exists(package_name):
            # Install from local path
            pkg = await self._install_from_path(package_name)
        else:
            # Install from registry
            pkg = await self._install_from_registry(package_name, version)
        
        if pkg:
            # Update lock file
            self._installed[pkg.name] = PackageLock(
                name=pkg.name,
                version=pkg.version,
                resolved=pkg.url or pkg.name,
            )
            self._save_lock()
            return True
        
        return False
    
    async def _install_from_registry(
        self,
        name: str,
        version: Optional[str]
    ) -> Optional[Package]:
        """Install package from registry"""
        if not HAS_AIOHTTP:
            print("aiohttp required for installing from registry")
            return None
        
        pkg = await self._registry.get_package(name)
        if not pkg:
            print(f"Package not found: {name}")
            return None
        
        target_version = version or pkg.version
        
        # Download and install
        try:
            async with aiohttp.ClientSession() as session:
                download_url = f"{self._registry._registry_url}/packages/{name}/download/{target_version}"
                
                async with session.get(download_url) as response:
                    if response.status == 200:
                        install_path = self._packages_dir / name
                        install_path.mkdir(exist_ok=True)
                        
                        # Save package content
                        content = await response.read()
                        # TODO: Extract zip/tar archive
                        
                        pkg.install_path = str(install_path)
                        print(f"Installed {name}@{target_version}")
                        return pkg
                    else:
                        print(f"Failed to download {name}: {response.status}")
        except Exception as e:
            print(f"Error installing {name}: {e}")
        
        return None
    
    async def _install_from_url(
        self,
        url: str,
        version: Optional[str]
    ) -> Optional[Package]:
        """Install package from URL"""
        if not HAS_AIOHTTP:
            print("aiohttp required for installing from URL")
            return None
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        # Extract package name from URL
                        parsed = urlparse(url)
                        name = Path(parsed.path).stem
                        
                        install_path = self._packages_dir / name
                        install_path.mkdir(exist_ok=True)
                        
                        # Save content
                        content = await response.read()
                        # TODO: Extract if archive
                        
                        pkg = Package(
                            name=name,
                            version=version or "0.0.0",
                            url=url,
                            install_path=str(install_path),
                        )
                        print(f"Installed {name} from {url}")
                        return pkg
        except Exception as e:
            print(f"Error installing from URL: {e}")
        
        return None
    
    async def _install_from_path(self, path: str) -> Optional[Package]:
        """Install package from local path"""
        source_path = Path(path.replace("file://", ""))
        
        if not source_path.exists():
            print(f"Path not found: {source_path}")
            return None
        
        # Read package.json or similar
        pkg_info = self._read_package_info(source_path)
        
        name = pkg_info.get("name", source_path.name)
        install_path = self._packages_dir / name
        
        # Copy files
        if source_path.is_dir():
            if install_path.exists():
                shutil.rmtree(install_path)
            shutil.copytree(source_path, install_path)
        else:
            install_path.mkdir(exist_ok=True)
            shutil.copy2(source_path, install_path)
        
        pkg = Package(
            name=name,
            version=pkg_info.get("version", "0.0.0"),
            description=pkg_info.get("description", ""),
            install_path=str(install_path),
        )
        print(f"Installed {name} from {source_path}")
        return pkg
    
    def _read_package_info(self, path: Path) -> Dict[str, Any]:
        """Read package info from directory"""
        # Try various config files
        for config_file in ["package.json", "skill.json", "skill.yaml", "skill.yml"]:
            config_path = path / config_file if path.is_dir() else path.parent / config_file
            if config_path.exists():
                try:
                    with open(config_path, "r", encoding="utf-8") as f:
                        if config_file.endswith(".json"):
                            return json.load(f)
                        else:
                            # Simple YAML parsing
                            return self._parse_simple_yaml(f.read())
                except Exception:
                    pass
        return {}
    
    def _parse_simple_yaml(self, content: str) -> Dict[str, str]:
        """Parse simple YAML content"""
        result = {}
        for line in content.split("\n"):
            stripped = line.strip()
            if not stripped or stripped.startswith("#"):
                continue
            if ":" in stripped:
                key, value = stripped.split(":", 1)
                result[key.strip()] = value.strip()
        return result
    
    async def uninstall(self, package_name: str) -> bool:
        """
        Uninstall a package.
        
        Args:
            package_name: Package to uninstall
            
        Returns:
            True if uninstalled successfully
        """
        if package_name not in self._installed:
            print(f"Package not installed: {package_name}")
            return False
        
        # Remove files
        lock = self._installed[package_name]
        if lock.resolved.startswith("/") or lock.resolved.startswith("."):
            install_path = Path(lock.resolved)
        else:
            install_path = self._packages_dir / package_name
        
        if install_path.exists():
            shutil.rmtree(install_path, ignore_errors=True)
        
        # Update lock file
        del self._installed[package_name]
        self._save_lock()
        
        print(f"Uninstalled {package_name}")
        return True
    
    async def update(self, package_name: Optional[str] = None) -> List[str]:
        """
        Update packages.
        
        Args:
            package_name: Specific package to update, or None for all
            
        Returns:
            List of updated packages
        """
        updated = []
        
        packages_to_update = [package_name] if package_name else list(self._installed.keys())
        
        for name in packages_to_update:
            if name not in self._installed:
                continue
            
            current = self._installed[name]
            
            # Check for newer version
            latest = await self._registry.get_package(name)
            if latest and latest.version != current.version:
                # Reinstall
                if await self.install(name, force=True):
                    updated.append(name)
        
        return updated
    
    def list_installed(self) -> List[Package]:
        """List all installed packages"""
        packages = []
        
        for name, lock in self._installed.items():
            pkg = Package(
                name=name,
                version=lock.version,
                install_path=lock.resolved if lock.resolved.startswith("/") else str(self._packages_dir / name),
            )
            packages.append(pkg)
        
        return packages
    
    def is_installed(self, package_name: str) -> bool:
        """Check if a package is installed"""
        return package_name in self._installed
    
    def get_install_path(self, package_name: str) -> Optional[Path]:
        """Get installation path for a package"""
        if package_name not in self._installed:
            return None
        
        lock = self._installed[package_name]
        if lock.resolved.startswith("/"):
            return Path(lock.resolved)
        return self._packages_dir / package_name


__all__ = [
    "Package",
    "PackageLock",
    "PackageRegistry",
    "PackageManager",
]
