"""
Download Functionality
Equivalent to Pi Mono's packages/mom/src/download.ts

File download from URLs with progress tracking.
"""
import asyncio
from pathlib import Path
from typing import Optional, Callable
from dataclasses import dataclass

try:
    import aiohttp
    HAS_AIOHTTP = True
except ImportError:
    HAS_AIOHTTP = False


@dataclass
class DownloadResult:
    """Download result"""
    success: bool
    file_path: Optional[str] = None
    error: Optional[str] = None
    bytes_downloaded: int = 0
    total_bytes: int = 0


ProgressCallback = Callable[[int, int], None]  # (downloaded, total)


async def download_file(
    url: str,
    destination: str,
    headers: Optional[dict] = None,
    timeout: int = 300,
    on_progress: Optional[ProgressCallback] = None,
) -> DownloadResult:
    """
    Download file from URL.
    
    Args:
        url: URL to download from
        destination: Local path to save file
        headers: Optional HTTP headers
        timeout: Download timeout in seconds
        on_progress: Progress callback (downloaded, total)
        
    Returns:
        DownloadResult with status and info
    """
    if not HAS_AIOHTTP:
        return DownloadResult(
            success=False,
            error="aiohttp is required for download_file. Install with: pip install aiohttp"
        )
    
    try:
        dest_path = Path(destination)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        
        async with aiohttp.ClientSession() as session:
            async with session.get(
                url,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=timeout),
            ) as response:
                if response.status != 200:
                    return DownloadResult(
                        success=False,
                        error=f"HTTP {response.status}: {response.reason}",
                    )
                
                total = int(response.headers.get("Content-Length", 0))
                downloaded = 0
                
                with open(dest_path, "wb") as f:
                    async for chunk in response.content.iter_chunked(8192):
                        f.write(chunk)
                        downloaded += len(chunk)
                        
                        if on_progress:
                            on_progress(downloaded, total)
                
                return DownloadResult(
                    success=True,
                    file_path=str(dest_path),
                    bytes_downloaded=downloaded,
                    total_bytes=total or downloaded,
                )
    
    except asyncio.TimeoutError:
        return DownloadResult(
            success=False,
            error=f"Download timeout after {timeout}s",
        )
    except Exception as e:
        return DownloadResult(
            success=False,
            error=str(e),
        )


async def download_with_retry(
    url: str,
    destination: str,
    headers: Optional[dict] = None,
    max_retries: int = 3,
    on_progress: Optional[ProgressCallback] = None,
) -> DownloadResult:
    """
    Download file with retry.
    
    Args:
        url: URL to download from
        destination: Local path to save file
        headers: Optional HTTP headers
        max_retries: Maximum number of retries
        on_progress: Progress callback
        
    Returns:
        DownloadResult
    """
    last_error = None
    
    for attempt in range(max_retries):
        result = await download_file(url, destination, headers, on_progress=on_progress)
        
        if result.success:
            return result
        
        last_error = result.error
        
        if attempt < max_retries - 1:
            # Exponential backoff
            wait = 2 ** attempt
            await asyncio.sleep(wait)
    
    return DownloadResult(
        success=False,
        error=f"Failed after {max_retries} attempts. Last error: {last_error}",
    )


def is_downloadable_url(url: str) -> bool:
    """
    Check if URL is likely downloadable (not a webpage).
    
    Args:
        url: URL to check
        
    Returns:
        True if likely a downloadable file
    """
    # Common file extensions
    file_extensions = [
        ".pdf", ".doc", ".docx", ".xls", ".xlsx", ".ppt", ".pptx",
        ".zip", ".tar", ".gz", ".rar", ".7z",
        ".jpg", ".jpeg", ".png", ".gif", ".svg", ".webp",
        ".mp3", ".mp4", ".avi", ".mov", ".mkv",
        ".py", ".js", ".ts", ".java", ".cpp", ".c", ".h",
        ".json", ".xml", ".yaml", ".yml", ".toml",
        ".txt", ".md", ".csv", ".log",
    ]
    
    url_lower = url.lower()
    return any(url_lower.endswith(ext) for ext in file_extensions)
