"""
Image Resize - Pi compatible image processing

Based on: packages/coding-agent/src/utils/image-resize.ts

Uses PIL/Pillow instead of Photon (Rust/WASM) for Python compatibility.
"""
import base64
import io
from dataclasses import dataclass
from typing import Optional, Tuple
from pathlib import Path

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False


@dataclass
class ResizedImage:
    """Result of image resize operation"""
    data: str  # base64
    mimeType: str
    originalWidth: int
    originalHeight: int
    width: int
    height: int
    wasResized: bool


# Default limits (matching Pi)
DEFAULT_MAX_WIDTH = 2000
DEFAULT_MAX_HEIGHT = 2000
DEFAULT_MAX_BYTES = int(4.5 * 1024 * 1024)  # 4.5MB - below Anthropic's 5MB limit
DEFAULT_JPEG_QUALITY = 80


def format_dimension_note(result: ResizedImage) -> Optional[str]:
    """
    Format a dimension note for resized images
    
    This helps the model understand the coordinate mapping
    """
    if not result.wasResized:
        return None
    
    scale = result.originalWidth / result.width
    return (
        f"[Image: original {result.originalWidth}x{result.originalHeight}, "
        f"displayed at {result.width}x{result.height}. "
        f"Multiply coordinates by {scale:.2f} to map to original image.]"
    )


def resize_image(
    img_data: str,
    mime_type: str,
    max_width: int = DEFAULT_MAX_WIDTH,
    max_height: int = DEFAULT_MAX_HEIGHT,
    max_bytes: int = DEFAULT_MAX_BYTES,
    jpeg_quality: int = DEFAULT_JPEG_QUALITY
) -> ResizedImage:
    """
    Resize an image to fit within the specified max dimensions and file size
    
    Strategy for staying under maxBytes:
    1. First resize to maxWidth/maxHeight
    2. Try both PNG and JPEG formats, pick the smaller one
    3. If still too large, try JPEG with decreasing quality
    4. If still too large, progressively reduce dimensions
    """
    if not PIL_AVAILABLE:
        return ResizedImage(
            data=img_data,
            mimeType=mime_type,
            originalWidth=0,
            originalHeight=0,
            width=0,
            height=0,
            wasResized=False
        )
    
    try:
        input_buffer = base64.b64decode(img_data)
        img = Image.open(io.BytesIO(input_buffer))
        original_width, original_height = img.size
        original_size = len(input_buffer)
        
        # Check if already within limits
        if (original_width <= max_width and 
            original_height <= max_height and 
            original_size <= max_bytes):
            return ResizedImage(
                data=img_data,
                mimeType=mime_type,
                originalWidth=original_width,
                originalHeight=original_height,
                width=original_width,
                height=original_height,
                wasResized=False
            )
        
        # Calculate target dimensions
        target_width = original_width
        target_height = original_height
        
        if target_width > max_width:
            target_height = round(target_height * max_width / target_width)
            target_width = max_width
        
        if target_height > max_height:
            target_width = round(target_width * max_height / target_height)
            target_height = max_height
        
        def try_both_formats(width: int, height: int, quality: int) -> Tuple[str, str, int]:
            """Try PNG and JPEG, return (base64_data, mime_type, size) of smaller"""
            resized = img.resize((width, height), Image.Resampling.LANCZOS)
            
            # Try PNG
            png_buffer = io.BytesIO()
            resized.save(png_buffer, format='PNG')
            png_data = png_buffer.getvalue()
            
            # Try JPEG
            jpeg_buffer = io.BytesIO()
            if resized.mode in ('RGBA', 'LA', 'P'):
                rgb_resized = resized.convert('RGB')
                rgb_resized.save(jpeg_buffer, format='JPEG', quality=quality)
            else:
                resized.save(jpeg_buffer, format='JPEG', quality=quality)
            jpeg_data = jpeg_buffer.getvalue()
            
            if len(png_data) <= len(jpeg_data):
                return base64.b64encode(png_data).decode('utf-8'), 'image/png', len(png_data)
            else:
                return base64.b64encode(jpeg_data).decode('utf-8'), 'image/jpeg', len(jpeg_data)
        
        quality_steps = [85, 70, 55, 40]
        scale_steps = [1.0, 0.75, 0.5, 0.35, 0.25]
        
        final_width = target_width
        final_height = target_height
        best_data, best_mime, best_size = try_both_formats(target_width, target_height, jpeg_quality)
        
        if best_size <= max_bytes:
            return ResizedImage(
                data=best_data,
                mimeType=best_mime,
                originalWidth=original_width,
                originalHeight=original_height,
                width=final_width,
                height=final_height,
                wasResized=True
            )
        
        # Try decreasing quality
        for quality in quality_steps:
            best_data, best_mime, best_size = try_both_formats(target_width, target_height, quality)
            if best_size <= max_bytes:
                return ResizedImage(
                    data=best_data,
                    mimeType=best_mime,
                    originalWidth=original_width,
                    originalHeight=original_height,
                    width=final_width,
                    height=final_height,
                    wasResized=True
                )
        
        # Reduce dimensions
        for scale in scale_steps:
            final_width = max(100, round(target_width * scale))
            final_height = max(100, round(target_height * scale))
            
            if final_width < 100 or final_height < 100:
                break
            
            for quality in quality_steps:
                best_data, best_mime, best_size = try_both_formats(final_width, final_height, quality)
                if best_size <= max_bytes:
                    return ResizedImage(
                        data=best_data,
                        mimeType=best_mime,
                        originalWidth=original_width,
                        originalHeight=original_height,
                        width=final_width,
                        height=final_height,
                        wasResized=True
                    )
        
        return ResizedImage(
            data=best_data,
            mimeType=best_mime,
            originalWidth=original_width,
            originalHeight=original_height,
            width=final_width,
            height=final_height,
            wasResized=True
        )
        
    except Exception:
        return ResizedImage(
            data=img_data,
            mimeType=mime_type,
            originalWidth=0,
            originalHeight=0,
            width=0,
            height=0,
            wasResized=False
        )


def resize_image_file(file_path: Path, auto_resize: bool = True) -> Optional[ResizedImage]:
    """Read and resize an image file"""
    if not auto_resize or not PIL_AVAILABLE:
        return None
    
    try:
        ext = file_path.suffix.lower()
        mime_map = {
            '.jpg': 'image/jpeg',
            '.jpeg': 'image/jpeg',
            '.png': 'image/png',
            '.gif': 'image/gif',
            '.webp': 'image/webp'
        }
        mime_type = mime_map.get(ext, 'image/png')
        
        with open(file_path, 'rb') as f:
            img_data = base64.b64encode(f.read()).decode('utf-8')
        
        return resize_image(img_data, mime_type)
        
    except Exception:
        return None
