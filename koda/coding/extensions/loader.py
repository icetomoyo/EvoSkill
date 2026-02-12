"""
Extension Loader - Dynamic extension discovery and loading
Equivalent to Pi Mono's extension-loader.ts

Provides:
- Directory scanning for extensions
- Dynamic module import
- Metadata validation
- Dependency resolution
- Version checking
- Conflict detection
- Concurrent loading
"""
import asyncio
import importlib.util
import os
import re
import sys
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set, Type, Tuple
import hashlib

from koda.coding.extensions.types import (
    Extension,
    ExtensionManifest,
    ExtensionConfig,
    ExtensionStatus,
)


@dataclass
class DiscoveredExtension:
    """Information about a discovered extension"""
    path: Path
    module_name: str
    manifest: Optional[ExtensionManifest] = None
    extension_class: Optional[Type[Extension]] = None
    error: Optional[str] = None
    status: ExtensionStatus = ExtensionStatus.DISCOVERED
    discovered_at: datetime = field(default_factory=datetime.now)
    file_hash: Optional[str] = None
    priority: int = 100

    def compute_hash(self) -> str:
        """Compute hash of extension file for change detection"""
        if self.path.exists():
            with open(self.path, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        return ""


@dataclass
class LoadResult:
    """Result of loading an extension"""
    name: str
    success: bool
    extension: Optional[Extension] = None
    error: Optional[str] = None
    load_time_ms: float = 0.0
    warnings: List[str] = field(default_factory=list)


@dataclass
class ValidationResult:
    """Result of validating an extension"""
    valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    missing_dependencies: List[str] = field(default_factory=list)
    conflicts: List[str] = field(default_factory=list)


class ExtensionLoader:
    """
    Extension loader for discovering and loading extensions.

    Scans directories for Python modules containing Extension classes,
    validates their manifests, and resolves dependencies.

    Features:
    - Directory scanning for extension discovery
    - Dynamic module import with isolation
    - Manifest validation (name, version, dependencies)
    - Dependency resolution with topological sort
    - Conflict detection between extensions
    - Version constraint checking
    - Concurrent loading support
    - Change detection via file hashing
    """

    def __init__(
        self,
        search_paths: Optional[List[Path]] = None,
        strict_validation: bool = True,
        enable_cache: bool = True,
        max_workers: int = 4
    ):
        """
        Initialize extension loader.

        Args:
            search_paths: Directories to search for extensions
            strict_validation: Whether to enforce strict manifest validation
            enable_cache: Whether to cache loaded modules
            max_workers: Maximum workers for concurrent loading
        """
        self.search_paths = search_paths or []
        self.strict_validation = strict_validation
        self.enable_cache = enable_cache
        self.max_workers = max_workers

        # Extension storage
        self._discovered: Dict[str, DiscoveredExtension] = {}
        self._loaded: Dict[str, Extension] = {}
        self._load_configs: Dict[str, ExtensionConfig] = {}

        # Module cache
        self._module_cache: Dict[str, Any] = {}

        # Add default search paths
        if not self.search_paths:
            self._add_default_search_paths()

    def _add_default_search_paths(self) -> None:
        """Add default extension directories"""
        # Current working directory extensions
        cwd_extensions = Path.cwd() / ".koda" / "extensions"
        if cwd_extensions.exists():
            self.search_paths.append(cwd_extensions)

        # User home extensions
        home_extensions = Path.home() / ".koda" / "extensions"
        if home_extensions.exists():
            self.search_paths.append(home_extensions)

        # Built-in extensions (if exists)
        builtin_extensions = Path(__file__).parent / "builtin"
        if builtin_extensions.exists():
            self.search_paths.append(builtin_extensions)

    def add_search_path(self, path: Path) -> None:
        """Add a directory to search for extensions"""
        if path.exists() and path not in self.search_paths:
            self.search_paths.append(path)

    def discover(self) -> Dict[str, DiscoveredExtension]:
        """
        Discover all extensions in search paths.

        Returns:
            Dictionary mapping extension names to discovered extensions
        """
        self._discovered.clear()

        for search_path in self.search_paths:
            if not search_path.exists():
                continue

            for item in search_path.iterdir():
                if item.is_file() and item.suffix == ".py":
                    self._discover_module(item)
                elif item.is_dir():
                    # Check for __init__.py or extension.py
                    init_file = item / "__init__.py"
                    extension_file = item / "extension.py"

                    if extension_file.exists():
                        self._discover_module(extension_file, item.name)
                    elif init_file.exists():
                        self._discover_package(item)

        return self._discovered

    def _discover_module(
        self,
        module_path: Path,
        module_name: Optional[str] = None
    ) -> None:
        """Discover extension in a Python module"""
        if module_name is None:
            module_name = module_path.stem

        try:
            # Load module
            spec = importlib.util.spec_from_file_location(module_name, module_path)
            if not spec or not spec.loader:
                return

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            # Find Extension classes
            for attr_name in dir(module):
                attr = getattr(module, attr_name)

                # Check if it's an Extension subclass (but not Extension itself)
                if (
                    isinstance(attr, type) and
                    issubclass(attr, Extension) and
                    attr is not Extension
                ):
                    # Instantiate to get manifest
                    try:
                        instance = attr()
                        manifest = instance.get_manifest()

                        discovered = DiscoveredExtension(
                            path=module_path,
                            module_name=module_name,
                            manifest=manifest,
                            extension_class=attr,
                        )

                        # Validate
                        validation_error = self._validate_manifest(manifest)
                        if validation_error:
                            discovered.error = validation_error
                            if self.strict_validation:
                                continue

                        self._discovered[manifest.name] = discovered

                    except Exception as e:
                        self._discovered[f"{module_name}:{attr_name}"] = DiscoveredExtension(
                            path=module_path,
                            module_name=module_name,
                            error=f"Failed to instantiate extension: {str(e)}"
                        )

        except Exception as e:
            self._discovered[module_name] = DiscoveredExtension(
                path=module_path,
                module_name=module_name,
                error=f"Failed to load module: {str(e)}"
            )

    def _discover_package(self, package_path: Path) -> None:
        """Discover extension in a Python package"""
        module_name = package_path.name

        try:
            # Import package
            init_path = package_path / "__init__.py"

            # Look for extension.py or main class in __init__.py
            for py_file in package_path.glob("*.py"):
                self._discover_module(py_file, f"{module_name}.{py_file.stem}")

        except Exception as e:
            self._discovered[module_name] = DiscoveredExtension(
                path=package_path,
                module_name=module_name,
                error=f"Failed to load package: {str(e)}"
            )

    def _validate_manifest(self, manifest: ExtensionManifest) -> Optional[str]:
        """
        Validate extension manifest.

        Returns:
            Error message if validation fails, None otherwise
        """
        # Required fields
        if not manifest.name:
            return "Extension name is required"
        if not manifest.version:
            return "Extension version is required"

        # Name validation (alphanumeric, underscore, hyphen only)
        if not re.match(r'^[a-zA-Z][a-zA-Z0-9_-]*$', manifest.name):
            return f"Invalid extension name: {manifest.name} (must start with letter, alphanumeric/underscore/hyphen only)"

        # Version validation (semver-like)
        if not re.match(r'^\d+\.\d+\.\d+(-[a-zA-Z0-9.]+)?$', manifest.version):
            if not any(c.isdigit() for c in manifest.version):
                return f"Invalid version format: {manifest.version}"

        # Dependency validation (check if dependencies exist)
        for dep in manifest.depends_on:
            if dep not in self._discovered and dep not in self._loaded:
                # Will be checked again after all discoveries
                pass

        return None

    def validate_extension(self, name: str) -> ValidationResult:
        """
        Validate a discovered extension comprehensively.

        Args:
            name: Extension name to validate

        Returns:
            ValidationResult with errors, warnings, and dependency info
        """
        result = ValidationResult(valid=True)

        discovered = self._discovered.get(name)
        if not discovered:
            result.valid = False
            result.errors.append(f"Extension not found: {name}")
            return result

        if discovered.error:
            result.valid = False
            result.errors.append(discovered.error)
            return result

        manifest = discovered.manifest
        if not manifest:
            result.valid = False
            result.errors.append("No manifest found")
            return result

        # Check dependencies
        for dep in manifest.depends_on:
            if dep not in self._discovered and dep not in self._loaded:
                result.missing_dependencies.append(dep)

        if result.missing_dependencies:
            result.warnings.append(f"Missing dependencies: {result.missing_dependencies}")

        # Check conflicts
        for conflict in manifest.conflicts_with:
            if conflict in self._discovered or conflict in self._loaded:
                result.conflicts.append(conflict)

        if result.conflicts:
            result.valid = False
            result.errors.append(f"Conflicts with: {result.conflicts}")

        # Validate permissions
        if manifest.permissions:
            valid_permissions = {
                "file:read", "file:write", "shell:execute",
                "network:access", "context:read", "context:modify",
                "tool:register", "event:emit", "session:read",
                "session:modify", "settings:read", "settings:modify"
            }
            for perm in manifest.permissions:
                if perm not in valid_permissions:
                    result.warnings.append(f"Unknown permission: {perm}")

        # Validate config schema if present
        if manifest.config_schema:
            if not isinstance(manifest.config_schema, dict):
                result.errors.append("Config schema must be a dictionary")
                result.valid = False

        result.valid = result.valid and len(result.errors) == 0
        return result

    def check_conflicts(self) -> Dict[str, List[str]]:
        """
        Check for conflicts between all discovered extensions.

        Returns:
            Dict mapping extension names to list of conflicting extensions
        """
        conflicts: Dict[str, List[str]] = {}

        for name, discovered in self._discovered.items():
            if not discovered.manifest:
                continue

            ext_conflicts = []

            # Check declared conflicts
            for conflict in discovered.manifest.conflicts_with:
                if conflict in self._discovered:
                    ext_conflicts.append(conflict)

            # Check for name collisions with provides_tools
            if discovered.manifest.provides_tools:
                for other_name, other in self._discovered.items():
                    if other_name == name or not other.manifest:
                        continue

                    tool_overlap = set(discovered.manifest.provides_tools) & set(other.manifest.provides_tools)
                    if tool_overlap:
                        ext_conflicts.append(f"{other_name} (tools: {tool_overlap})")

            if ext_conflicts:
                conflicts[name] = ext_conflicts

        return conflicts

    def get_load_order(self) -> Tuple[List[str], List[str]]:
        """
        Get the order in which extensions should be loaded.

        Returns:
            Tuple of (load_order, skipped_extensions)
        """
        try:
            load_order = self.resolve_dependencies()
        except ValueError as e:
            print(f"Dependency resolution failed: {e}")
            load_order = []

        skipped = []
        valid_order = []

        for name in load_order:
            discovered = self._discovered.get(name)
            if not discovered or discovered.error:
                skipped.append(name)
                continue

            # Check if dependencies are satisfied
            manifest = discovered.manifest
            if manifest:
                deps_satisfied = all(
                    dep in valid_order or dep in self._loaded
                    for dep in manifest.depends_on
                )
                if not deps_satisfied:
                    skipped.append(name)
                    continue

            valid_order.append(name)

        return valid_order, skipped

    def resolve_dependencies(self) -> List[str]:
        """
        Resolve extension dependencies and return load order.

        Returns:
            List of extension names in load order

        Raises:
            ValueError: If circular dependency or missing dependency
        """
        # Build dependency graph
        graph: Dict[str, List[str]] = {}

        for name, discovered in self._discovered.items():
            if discovered.error or not discovered.manifest:
                continue

            deps = discovered.manifest.depends_on
            graph[name] = deps.copy()

        # Topological sort
        result: List[str] = []
        visited: set = set()
        temp_visited: set = set()

        def visit(name: str) -> None:
            if name in temp_visited:
                raise ValueError(f"Circular dependency detected: {name}")
            if name in visited:
                return

            temp_visited.add(name)

            deps = graph.get(name, [])
            for dep in deps:
                if dep not in graph:
                    raise ValueError(f"Missing dependency: {dep} (required by {name})")
                visit(dep)

            temp_visited.remove(name)
            visited.add(name)
            result.append(name)

        for name in graph:
            if name not in visited:
                visit(name)

        return result

    def load(
        self,
        extension_name: str,
        config: Optional[ExtensionConfig] = None
    ) -> Optional[Extension]:
        """
        Load a specific extension.

        Args:
            extension_name: Name of extension to load
            config: Configuration for the extension

        Returns:
            Loaded extension instance or None if not found
        """
        result = self.load_with_result(extension_name, config)
        return result.extension

    def load_with_result(
        self,
        extension_name: str,
        config: Optional[ExtensionConfig] = None
    ) -> LoadResult:
        """
        Load an extension and return detailed result.

        Args:
            extension_name: Name of extension to load
            config: Configuration for the extension

        Returns:
            LoadResult with details
        """
        start_time = datetime.now()

        discovered = self._discovered.get(extension_name)
        if not discovered:
            return LoadResult(
                name=extension_name,
                success=False,
                error=f"Extension not found: {extension_name}"
            )

        if discovered.error:
            return LoadResult(
                name=extension_name,
                success=False,
                error=discovered.error
            )

        if not discovered.extension_class:
            return LoadResult(
                name=extension_name,
                success=False,
                error="No extension class found"
            )

        # Check dependencies
        manifest = discovered.manifest
        if manifest:
            missing_deps = [
                dep for dep in manifest.depends_on
                if dep not in self._loaded
            ]
            if missing_deps:
                return LoadResult(
                    name=extension_name,
                    success=False,
                    error=f"Missing dependencies: {missing_deps}"
                )

            # Check conflicts
            conflicts = [
                c for c in manifest.conflicts_with
                if c in self._loaded
            ]
            if conflicts:
                return LoadResult(
                    name=extension_name,
                    success=False,
                    error=f"Conflicts with loaded extensions: {conflicts}"
                )

        try:
            instance = discovered.extension_class()

            if config:
                instance.configure(config)

            self._loaded[extension_name] = instance
            discovered.status = ExtensionStatus.LOADED

            end_time = datetime.now()
            load_time = (end_time - start_time).total_seconds() * 1000

            return LoadResult(
                name=extension_name,
                success=True,
                extension=instance,
                load_time_ms=load_time
            )

        except Exception as e:
            discovered.error = f"Failed to load: {str(e)}"
            discovered.status = ExtensionStatus.ERROR
            return LoadResult(
                name=extension_name,
                success=False,
                error=str(e)
            )

    def load_all(self) -> Dict[str, Extension]:
        """
        Load all discovered extensions in dependency order.

        Returns:
            Dictionary of loaded extensions
        """
        load_order, _ = self.get_load_order()

        for name in load_order:
            if name not in self._loaded:
                self.load(name)

        return self._loaded.copy()

    def load_all_with_results(self) -> Dict[str, LoadResult]:
        """
        Load all extensions and return detailed results.

        Returns:
            Dictionary mapping extension names to LoadResult
        """
        results: Dict[str, LoadResult] = {}
        load_order, skipped = self.get_load_order()

        # Mark skipped extensions
        for name in skipped:
            results[name] = LoadResult(
                name=name,
                success=False,
                error="Skipped due to missing dependencies or errors"
            )

        # Load in order
        for name in load_order:
            if name not in self._loaded:
                results[name] = self.load_with_result(name)
            else:
                results[name] = LoadResult(
                    name=name,
                    success=True,
                    extension=self._loaded[name]
                )

        return results

    async def load_concurrent(
        self,
        extension_names: Optional[List[str]] = None
    ) -> Dict[str, LoadResult]:
        """
        Load extensions concurrently (respecting dependencies).

        Args:
            extension_names: Specific extensions to load (all if None)

        Returns:
            Dictionary mapping extension names to LoadResult
        """
        if extension_names is None:
            load_order, _ = self.get_load_order()
            extension_names = load_order

        results: Dict[str, LoadResult] = {}

        # Group extensions by dependency level
        levels = self._group_by_dependency_level(extension_names)

        for level in levels:
            # Extensions in same level can be loaded concurrently
            tasks = []
            for name in level:
                if name not in self._loaded:
                    tasks.append((name, self._load_async(name)))

            # Run concurrently
            if tasks:
                for name, coro in tasks:
                    try:
                        result = await coro
                        results[name] = result
                    except Exception as e:
                        results[name] = LoadResult(
                            name=name,
                            success=False,
                            error=str(e)
                        )

        return results

    def _group_by_dependency_level(self, names: List[str]) -> List[List[str]]:
        """Group extensions by dependency level for concurrent loading"""
        levels: List[List[str]] = []
        remaining = set(names)
        completed: Set[str] = set()

        while remaining:
            # Find extensions with all dependencies satisfied
            level = []
            for name in list(remaining):
                discovered = self._discovered.get(name)
                if not discovered or not discovered.manifest:
                    continue

                deps = discovered.manifest.depends_on
                if all(d in completed or d in self._loaded for d in deps):
                    level.append(name)

            if not level:
                # Circular dependency or missing deps - add remaining
                level = list(remaining)

            levels.append(level)
            completed.update(level)
            remaining -= set(level)

        return levels

    async def _load_async(self, name: str) -> LoadResult:
        """Async wrapper for loading"""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            None,
            self.load_with_result,
            name
        )

    def reload(self, extension_name: str) -> LoadResult:
        """
        Reload an extension (unload and load again).

        Args:
            extension_name: Name of extension to reload

        Returns:
            LoadResult with details
        """
        # Unload if loaded
        if extension_name in self._loaded:
            self.unload(extension_name)

        # Re-discover to pick up changes
        discovered = self._discovered.get(extension_name)
        if discovered:
            self._discover_module(discovered.path, discovered.module_name)

        return self.load_with_result(extension_name)

    def unload(self, extension_name: str) -> bool:
        """
        Unload an extension.

        Args:
            extension_name: Name of extension to unload

        Returns:
            True if unloaded, False if not found
        """
        if extension_name not in self._loaded:
            return False

        extension = self._loaded.pop(extension_name)

        try:
            extension.deactivate()
        except Exception:
            pass  # Ignore errors during deactivation

        # Update status
        discovered = self._discovered.get(extension_name)
        if discovered:
            discovered.status = ExtensionStatus.INACTIVE

        return True

    def unload_all(self) -> None:
        """Unload all extensions"""
        for name in list(self._loaded.keys()):
            self.unload(name)

    def get_discovered(self) -> Dict[str, DiscoveredExtension]:
        """Get all discovered extensions"""
        return self._discovered.copy()

    def get_loaded(self) -> Dict[str, Extension]:
        """Get all loaded extensions"""
        return self._loaded.copy()

    def get_extension(self, name: str) -> Optional[Extension]:
        """Get a loaded extension by name"""
        return self._loaded.get(name)

    def get_extension_info(self, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed info about an extension.

        Args:
            name: Extension name

        Returns:
            Dict with extension info or None
        """
        discovered = self._discovered.get(name)
        if not discovered:
            return None

        loaded = self._loaded.get(name)

        return {
            "name": name,
            "path": str(discovered.path),
            "module_name": discovered.module_name,
            "status": discovered.status.value,
            "loaded": loaded is not None,
            "error": discovered.error,
            "manifest": {
                "name": discovered.manifest.name if discovered.manifest else None,
                "version": discovered.manifest.version if discovered.manifest else None,
                "description": discovered.manifest.description if discovered.manifest else None,
                "author": discovered.manifest.author if discovered.manifest else None,
                "depends_on": discovered.manifest.depends_on if discovered.manifest else [],
                "conflicts_with": discovered.manifest.conflicts_with if discovered.manifest else [],
                "provides_tools": discovered.manifest.provides_tools if discovered.manifest else [],
                "permissions": discovered.manifest.permissions if discovered.manifest else [],
            } if discovered.manifest else None,
        }

    def get_stats(self) -> Dict[str, Any]:
        """Get loader statistics"""
        return {
            "discovered_count": len(self._discovered),
            "loaded_count": len(self._loaded),
            "error_count": sum(1 for d in self._discovered.values() if d.error),
            "search_paths": [str(p) for p in self.search_paths],
            "extensions": {
                name: {
                    "status": d.status.value,
                    "has_error": d.error is not None
                }
                for name, d in self._discovered.items()
            }
        }


# Global loader instance
_loader: Optional[ExtensionLoader] = None


def get_extension_loader() -> ExtensionLoader:
    """Get global extension loader"""
    global _loader
    if _loader is None:
        _loader = ExtensionLoader()
    return _loader


def reset_extension_loader() -> None:
    """Reset global loader (for testing)"""
    global _loader
    if _loader:
        _loader.unload_all()
    _loader = None
