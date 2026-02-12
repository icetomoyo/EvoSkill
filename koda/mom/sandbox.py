"""
Sandbox - Isolated execution environment
Equivalent to Pi Mono's sandbox.ts
"""
import os
import subprocess
import tempfile
import signal
import asyncio
from typing import Dict, List, Optional, Any
from pathlib import Path
from dataclasses import dataclass, field
import shutil
import logging

logger = logging.getLogger(__name__)


@dataclass
class ResourceLimits:
    """
    Resource limits for sandbox execution

    Equivalent to Pi Mono's ResourceLimits
    """
    # Time limits
    timeout_seconds: float = 60.0
    cpu_time_seconds: Optional[float] = None

    # Memory limits (in MB)
    memory_mb: Optional[int] = None
    stack_mb: Optional[int] = None

    # File system limits
    max_file_size_mb: Optional[int] = None
    max_open_files: Optional[int] = None

    # Process limits
    max_processes: Optional[int] = None


@dataclass
class SandboxConfig:
    """
    Sandbox configuration

    Equivalent to Pi Mono's SandboxConfig
    """
    # Execution mode
    use_docker: bool = False
    docker_image: str = "python:3.11-slim"

    # Resource limits
    limits: ResourceLimits = field(default_factory=ResourceLimits)

    # Environment
    env: Dict[str, str] = field(default_factory=dict)
    working_dir: Optional[str] = None

    # Network
    network_enabled: bool = False
    allowed_hosts: List[str] = field(default_factory=list)

    # Security
    read_only_paths: List[str] = field(default_factory=list)
    writable_paths: List[str] = field(default_factory=list)

    # Docker specific
    docker_options: Dict[str, Any] = field(default_factory=dict)
    auto_remove_container: bool = True

    # Host specific
    restrict_path: bool = True
    allowed_commands: List[str] = field(default_factory=list)


@dataclass
class ExecutionResult:
    """
    Result of command execution

    Equivalent to Pi Mono's ExecutionResult
    """
    stdout: str = ""
    stderr: str = ""
    exit_code: int = 0
    success: bool = True
    timed_out: bool = False
    killed: bool = False
    duration_ms: float = 0.0
    resource_usage: Dict[str, Any] = field(default_factory=dict)


def killProcessTree(pid: int, include_parent: bool = True) -> List[int]:
    """
    Kill a process tree starting from the given PID

    Equivalent to Pi Mono's killProcessTree

    Args:
        pid: Process ID to kill
        include_parent: Whether to kill the parent process too

    Returns:
        List of killed PIDs
    """
    killed_pids = []

    try:
        # Get all child processes
        try:
            import psutil
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)

            # Kill children first
            for child in children:
                try:
                    child.terminate()
                    killed_pids.append(child.pid)
                except psutil.NoSuchProcess:
                    pass

            # Wait for graceful termination
            gone, alive = psutil.wait_procs(children, timeout=3)

            # Force kill remaining
            for child in alive:
                try:
                    child.kill()
                except psutil.NoSuchProcess:
                    pass

            # Kill parent if requested
            if include_parent:
                try:
                    parent.terminate()
                    parent.wait(timeout=3)
                    killed_pids.append(pid)
                except psutil.NoSuchProcess:
                    pass
                except psutil.TimeoutExpired:
                    try:
                        parent.kill()
                        killed_pids.append(pid)
                    except psutil.NoSuchProcess:
                        pass

        except ImportError:
            # Fallback without psutil
            # Use platform-specific commands
            import platform
            system = platform.system()

            if system == "Linux":
                # Use pkill to kill process tree
                subprocess.run(["pkill", "-TERM", "-P", str(pid)],
                               capture_output=True, timeout=5)
                killed_pids.append(pid)
            elif system == "Darwin":
                # macOS also supports pkill
                subprocess.run(["pkill", "-TERM", "-P", str(pid)],
                               capture_output=True, timeout=5)
                killed_pids.append(pid)
            elif system == "Windows":
                # Windows: use taskkill
                subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                               capture_output=True, timeout=5)
                killed_pids.append(pid)

    except Exception as e:
        logger.warning(f"Error killing process tree {pid}: {e}")

    return killed_pids


class BaseExecutor:
    """Base class for executors"""

    def __init__(self, config: Optional[SandboxConfig] = None):
        self.config = config or SandboxConfig()

    async def execute(
        self,
        command: List[str],
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None
    ) -> ExecutionResult:
        """Execute a command"""
        raise NotImplementedError

    def cleanup(self) -> None:
        """Clean up resources"""
        pass


class HostExecutor(BaseExecutor):
    """
    Execute commands on the host system

    Equivalent to Pi Mono's HostExecutor
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        super().__init__(config)
        self._temp_dir: Optional[Path] = None
        self._processes: Dict[int, subprocess.Popen] = {}

    async def execute(
        self,
        command: List[str],
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute command on host

        Args:
            command: Command and arguments
            timeout: Timeout in seconds
            env: Additional environment variables
            cwd: Working directory
            input_data: Input to pass to stdin

        Returns:
            ExecutionResult with output and status
        """
        import time

        start_time = time.time()
        timeout = timeout or self.config.limits.timeout_seconds

        # Merge environment
        run_env = os.environ.copy()
        if self.config.env:
            run_env.update(self.config.env)
        if env:
            run_env.update(env)

        # Restrict PATH if configured
        if self.config.restrict_path:
            run_env["PATH"] = "/usr/bin:/bin"

        # Determine working directory
        work_dir = cwd or self.config.working_dir or os.getcwd()

        result = ExecutionResult()
        process = None

        try:
            process = subprocess.Popen(
                command,
                cwd=work_dir,
                env=run_env,
                stdin=subprocess.PIPE if input_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            self._processes[process.pid] = process

            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=timeout
                )

                result.stdout = stdout
                result.stderr = stderr
                result.exit_code = process.returncode
                result.success = process.returncode == 0

            except subprocess.TimeoutExpired:
                result.timed_out = True
                result.success = False
                result.exit_code = -1
                result.stderr = f"Command timed out after {timeout}s"

                # Kill the process tree
                if process.pid:
                    killProcessTree(process.pid, include_parent=True)

        except FileNotFoundError as e:
            result.success = False
            result.exit_code = -1
            result.stderr = f"Command not found: {command[0]}"

        except Exception as e:
            result.success = False
            result.exit_code = -1
            result.stderr = str(e)

        finally:
            if process and process.pid in self._processes:
                del self._processes[process.pid]

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def get_running_processes(self) -> List[int]:
        """Get list of running process PIDs"""
        return list(self._processes.keys())

    def kill_all(self) -> List[int]:
        """Kill all running processes"""
        killed = []
        for pid in list(self._processes.keys()):
            killed.extend(killProcessTree(pid, include_parent=True))
            if pid in self._processes:
                del self._processes[pid]
        return killed

    def cleanup(self) -> None:
        """Clean up all resources"""
        self.kill_all()
        if self._temp_dir and self._temp_dir.exists():
            shutil.rmtree(self._temp_dir, ignore_errors=True)


@dataclass
class VolumeMount:
    """
    Docker volume mount configuration

    Equivalent to Pi Mono's VolumeMount
    """
    host_path: str
    container_path: str
    read_only: bool = False

    def to_docker_arg(self) -> List[str]:
        """Convert to docker -v argument"""
        mode = "ro" if self.read_only else "rw"
        return ["-v", f"{self.host_path}:{self.container_path}:{mode}"]


@dataclass
class NetworkConfig:
    """
    Docker network configuration

    Equivalent to Pi Mono's NetworkConfig
    """
    mode: str = "none"  # none, bridge, host, or custom network name
    aliases: List[str] = field(default_factory=list)
    ports: Dict[str, str] = field(default_factory=dict)  # host:container

    def to_docker_args(self) -> List[str]:
        """Convert to docker network arguments"""
        args = []
        args.extend(["--network", self.mode])

        for alias in self.aliases:
            args.extend(["--network-alias", alias])

        for host_port, container_port in self.ports.items():
            args.extend(["-p", f"{host_port}:{container_port}"])

        return args


class DockerExecutor(BaseExecutor):
    """
    Execute commands in Docker containers

    Equivalent to Pi Mono's DockerExecutor

    Features:
    - Container lifecycle management
    - Volume mounting
    - Network configuration
    - Image management
    - Resource limits
    """

    def __init__(self, config: Optional[SandboxConfig] = None):
        super().__init__(config)
        self._containers: Dict[str, Dict[str, Any]] = {}
        self._pulled_images: set = set()
        self._check_docker()

    def _check_docker(self) -> None:
        """Check if Docker is available"""
        try:
            result = subprocess.run(
                ["docker", "--version"],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode != 0:
                logger.warning("Docker not available")
        except (subprocess.TimeoutExpired, FileNotFoundError):
            logger.warning("Docker command not found")

    def pull_image(self, image: Optional[str] = None) -> bool:
        """
        Pull a Docker image.

        Args:
            image: Image to pull (uses config.docker_image if not specified)

        Returns:
            True if successful
        """
        image = image or self.config.docker_image
        if image in self._pulled_images:
            return True

        try:
            result = subprocess.run(
                ["docker", "pull", image],
                capture_output=True,
                text=True,
                timeout=300  # 5 minutes max
            )
            if result.returncode == 0:
                self._pulled_images.add(image)
                return True
            logger.warning(f"Failed to pull image {image}: {result.stderr}")
            return False
        except Exception as e:
            logger.error(f"Error pulling image {image}: {e}")
            return False

    def image_exists(self, image: Optional[str] = None) -> bool:
        """
        Check if a Docker image exists locally.

        Args:
            image: Image to check (uses config.docker_image if not specified)

        Returns:
            True if image exists
        """
        image = image or self.config.docker_image
        try:
            result = subprocess.run(
                ["docker", "image", "inspect", image],
                capture_output=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def ensure_image(self, image: Optional[str] = None) -> bool:
        """
        Ensure an image is available, pulling if necessary.

        Args:
            image: Image to ensure (uses config.docker_image if not specified)

        Returns:
            True if image is available
        """
        if self.image_exists(image):
            return True
        return self.pull_image(image)

    def list_images(self) -> List[Dict[str, Any]]:
        """
        List locally available Docker images.

        Returns:
            List of image info dictionaries
        """
        try:
            result = subprocess.run(
                ["docker", "images", "--format", "{{.Repository}}:{{.Tag}}\t{{.ID}}\t{{.Size}}"],
                capture_output=True,
                text=True,
                timeout=30
            )
            if result.returncode != 0:
                return []

            images = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    parts = line.split("\t")
                    if len(parts) >= 3:
                        images.append({
                            "name": parts[0],
                            "id": parts[1],
                            "size": parts[2],
                        })
            return images
        except Exception as e:
            logger.error(f"Error listing images: {e}")
            return []

    def add_volume_mount(self, host_path: str, container_path: str, read_only: bool = False) -> None:
        """
        Add a volume mount to the configuration.

        Args:
            host_path: Path on host system
            container_path: Path inside container
            read_only: Mount as read-only
        """
        mount = VolumeMount(host_path=host_path, container_path=container_path, read_only=read_only)
        mounts = self.config.docker_options.get("volume_mounts", [])
        mounts.append(mount)
        self.config.docker_options["volume_mounts"] = mounts

    def set_network_config(self, config: NetworkConfig) -> None:
        """
        Set network configuration.

        Args:
            config: NetworkConfig instance
        """
        self.config.docker_options["network_config"] = config

    async def execute(
        self,
        command: List[str],
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None,
        volumes: Optional[List[VolumeMount]] = None,
        network: Optional[NetworkConfig] = None
    ) -> ExecutionResult:
        """
        Execute command in Docker container

        Args:
            command: Command and arguments
            timeout: Timeout in seconds
            env: Additional environment variables
            cwd: Working directory inside container
            input_data: Input to pass to stdin
            volumes: Volume mounts (overrides config)
            network: Network configuration (overrides config)

        Returns:
            ExecutionResult with output and status
        """
        import time

        start_time = time.time()
        timeout = timeout or self.config.limits.timeout_seconds
        image = self.config.docker_image

        # Ensure image is available
        if not self.ensure_image(image):
            return ExecutionResult(
                success=False,
                exit_code=-1,
                stderr=f"Failed to ensure Docker image: {image}",
                duration_ms=(time.time() - start_time) * 1000
            )

        # Build docker command
        docker_cmd = ["docker", "run"]

        # Auto remove if configured
        if self.config.auto_remove_container:
            docker_cmd.append("--rm")

        # Add environment variables
        run_env = {**self.config.env, **(env or {})}
        for key, value in run_env.items():
            docker_cmd.extend(["-e", f"{key}={value}"])

        # Add resource limits
        if self.config.limits.memory_mb:
            docker_cmd.extend(["--memory", f"{self.config.limits.memory_mb}m"])

        if self.config.limits.cpu_time_seconds:
            docker_cmd.extend(["--ulimit", f"cpu={int(self.config.limits.cpu_time_seconds)}"])

        if self.config.limits.max_processes:
            docker_cmd.extend(["--ulimit", f"nproc={self.config.limits.max_processes}"])

        if self.config.limits.max_open_files:
            docker_cmd.extend(["--ulimit", f"nofile={self.config.limits.max_open_files}"])

        # Add volume mounts
        volume_mounts = volumes or self.config.docker_options.get("volume_mounts", [])
        for mount in volume_mounts:
            if isinstance(mount, VolumeMount):
                docker_cmd.extend(mount.to_docker_arg())
            elif isinstance(mount, str):
                # Legacy string format
                docker_cmd.extend(["-v", mount])

        # Legacy volume option
        if "volume" in self.config.docker_options and not volume_mounts:
            docker_cmd.extend(["-v", self.config.docker_options["volume"]])

        # Network settings
        net_config = network or self.config.docker_options.get("network_config")
        if net_config:
            docker_cmd.extend(net_config.to_docker_args())
        elif not self.config.network_enabled:
            docker_cmd.append("--network=none")

        # Working directory
        if cwd:
            docker_cmd.extend(["-w", cwd])

        # Security options
        if self.config.read_only_paths or self.config.writable_paths:
            # Use tmpfs for writable paths
            for path in self.config.writable_paths:
                docker_cmd.extend(["--tmpfs", path])

        # Custom docker options (skip our special keys)
        skip_keys = {"volume_mounts", "network_config", "volume"}
        for key, value in self.config.docker_options.items():
            if key in skip_keys:
                continue
            if isinstance(value, bool) and value:
                docker_cmd.append(f"--{key}")
            else:
                docker_cmd.extend([f"--{key}", str(value)])

        # Image and command
        docker_cmd.append(image)
        docker_cmd.extend(command)

        result = ExecutionResult()
        container_id = None

        try:
            process = subprocess.Popen(
                docker_cmd,
                stdin=subprocess.PIPE if input_data else None,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            # Track container if not auto-removing
            if not self.config.auto_remove_container:
                # Container ID would be captured from docker run output
                # For tracking, we'd need to use docker inspect
                pass

            try:
                stdout, stderr = process.communicate(
                    input=input_data,
                    timeout=timeout
                )

                result.stdout = stdout
                result.stderr = stderr
                result.exit_code = process.returncode
                result.success = process.returncode == 0

            except subprocess.TimeoutExpired:
                result.timed_out = True
                result.success = False
                result.exit_code = -1
                result.stderr = f"Command timed out after {timeout}s"

                # Kill the container
                if container_id:
                    self._kill_container(container_id)
                else:
                    # Kill process tree
                    if process.pid:
                        killProcessTree(process.pid, include_parent=True)

        except FileNotFoundError:
            result.success = False
            result.exit_code = -1
            result.stderr = "Docker command not found"

        except Exception as e:
            result.success = False
            result.exit_code = -1
            result.stderr = str(e)

        result.duration_ms = (time.time() - start_time) * 1000
        return result

    def _kill_container(self, container_id: str) -> bool:
        """Kill a Docker container"""
        try:
            subprocess.run(
                ["docker", "kill", container_id],
                capture_output=True,
                timeout=10
            )
            return True
        except Exception as e:
            logger.warning(f"Failed to kill container {container_id}: {e}")
            return False

    def list_containers(self) -> List[str]:
        """List running containers started by this executor"""
        return list(self._containers.keys())

    def cleanup(self) -> None:
        """Clean up all containers"""
        for container_id in list(self._containers.keys()):
            self._kill_container(container_id)
            del self._containers[container_id]


class Sandbox:
    """
    Sandbox environment for isolated execution

    Features:
    - File system isolation
    - Resource limits
    - Timeout control
    - Docker or host execution
    """

    def __init__(
        self,
        root_dir: Optional[Path] = None,
        config: Optional[SandboxConfig] = None
    ):
        self.config = config or SandboxConfig()

        # Set up root directory
        if root_dir is None:
            self.root_dir = Path(tempfile.mkdtemp(prefix="koda_sandbox_"))
            self._cleanup = True
        else:
            self.root_dir = Path(root_dir)
            self.root_dir.mkdir(parents=True, exist_ok=True)
            self._cleanup = False

        # Create executor based on config
        if self.config.use_docker:
            self._executor = DockerExecutor(self.config)
        else:
            self._executor = HostExecutor(self.config)

    async def execute(
        self,
        command: List[str],
        timeout: Optional[float] = None,
        env: Optional[Dict[str, str]] = None,
        cwd: Optional[str] = None,
        input_data: Optional[str] = None
    ) -> ExecutionResult:
        """
        Execute command in sandbox

        Args:
            command: Command and arguments
            timeout: Timeout in seconds
            env: Environment variables
            cwd: Working directory (relative to sandbox root)
            input_data: Input to pass to stdin

        Returns:
            ExecutionResult with output and status
        """
        # Resolve working directory
        work_dir = None
        if cwd:
            work_dir = str(self.root_dir / cwd)
        else:
            work_dir = str(self.root_dir)

        # If using Docker, mount the sandbox directory
        if self.config.use_docker and isinstance(self._executor, DockerExecutor):
            # Add volume mount to docker options
            self.config.docker_options["volume"] = f"{self.root_dir}:/workspace"

        return await self._executor.execute(
            command=command,
            timeout=timeout,
            env=env,
            cwd=work_dir,
            input_data=input_data
        )

    def write_file(self, path: str, content: str) -> None:
        """Write file in sandbox"""
        file_path = self.root_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding='utf-8')

    def write_binary_file(self, path: str, content: bytes) -> None:
        """Write binary file in sandbox"""
        file_path = self.root_dir / path
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_bytes(content)

    def read_file(self, path: str) -> Optional[str]:
        """Read file from sandbox"""
        file_path = self.root_dir / path
        if file_path.exists():
            return file_path.read_text(encoding='utf-8')
        return None

    def read_binary_file(self, path: str) -> Optional[bytes]:
        """Read binary file from sandbox"""
        file_path = self.root_dir / path
        if file_path.exists():
            return file_path.read_bytes()
        return None

    def list_files(self, path: str = "") -> List[str]:
        """List files in sandbox directory"""
        dir_path = self.root_dir / path
        if dir_path.exists() and dir_path.is_dir():
            return [f.name for f in dir_path.iterdir()]
        return []

    def delete_file(self, path: str) -> bool:
        """Delete file in sandbox"""
        file_path = self.root_dir / path
        if file_path.exists():
            if file_path.is_dir():
                shutil.rmtree(file_path, ignore_errors=True)
            else:
                file_path.unlink()
            return True
        return False

    def cleanup(self) -> None:
        """Clean up sandbox directory"""
        self._executor.cleanup()
        if self._cleanup and self.root_dir.exists():
            shutil.rmtree(self.root_dir, ignore_errors=True)

    def get_executor(self) -> BaseExecutor:
        """Get the underlying executor"""
        return self._executor

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.cleanup()


# Async versions of key functions for use with async/await
async def execute_in_sandbox(
    command: List[str],
    sandbox: Optional[Sandbox] = None,
    **kwargs
) -> ExecutionResult:
    """
    Convenience function to execute command in sandbox

    Args:
        command: Command to execute
        sandbox: Sandbox instance (creates temporary one if None)
        **kwargs: Additional arguments for execute()

    Returns:
        ExecutionResult
    """
    if sandbox is None:
        with Sandbox() as s:
            return await s.execute(command, **kwargs)
    return await sandbox.execute(command, **kwargs)
