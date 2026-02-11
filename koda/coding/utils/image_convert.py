"""
Image Convert Utilities
Equivalent to Pi Mono's packages/coding-agent/src/utils/image-convert.ts

Image format conversion utilities.
"""
import base64
import io
from pathlib import Path
from typing import Optional, Union, Tuple
from dataclasses import dataclass


@dataclass
class ImageInfo:
    """Image information"""
    width: int
    height: int
    format: str
    mode: str
    size_bytes: int


class ImageConverter:
    """
    Image format conversion.
    
    Converts between image formats and encodes to base64.
    Requires Pillow library.
    
    Example:
        >>> converter = ImageConverter()
        >>> base64_str = converter.to_base64("image.png")
        >>> converter.convert("image.png", "output.jpg", quality=85)
    """
    
    def __init__(self):
        self._pillow_available = self._check_pillow()
    
    def _check_pillow(self) -> bool:
        """Check if Pillow is installed"""
        try:
            from PIL import Image
            return True
        except ImportError:
            return False
    
    def is_available(self) -> bool:
        """Check if image conversion is available"""
        return self._pillow_available
    
    def get_info(self, image_path: Union[str, Path]) -> Optional[ImageInfo]:
        """
        Get image information.
        
        Args:
            image_path: Path to image
            
        Returns:
            ImageInfo or None if unavailable
        """
        if not self._pillow_available:
            return None
        
        try:
            from PIL import Image
            
            path = Path(image_path)
            with Image.open(path) as img:
                return ImageInfo(
                    width=img.width,
                    height=img.height,
                    format=img.format or "Unknown",
                    mode=img.mode,
                    size_bytes=path.stat().st_size
                )
        except Exception:
            return None
    
    def convert(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        format: Optional[str] = None,
        quality: int = 85,
        **kwargs
    ) -> bool:
        """
        Convert image format.
        
        Args:
            input_path: Input image path
            output_path: Output image path
            format: Target format (jpeg, png, webp, etc.)
            quality: JPEG quality (1-100)
            
        Returns:
            True if successful
        """
        if not self._pillow_available:
            raise ImportError("Pillow is required for image conversion. Install with: pip install Pillow")
        
        try:
            from PIL import Image
            
            input_path = Path(input_path)
            output_path = Path(output_path)
            
            with Image.open(input_path) as img:
                # Convert mode if necessary
                if img.mode in ('RGBA', 'P') and format == 'JPEG':
                    # JPEG doesn't support transparency
                    img = img.convert('RGB')
                elif img.mode == 'P':
                    img = img.convert('RGB')
                
                # Determine format from extension if not specified
                if format is None:
                    format = output_path.suffix.lstrip('.').upper()
                    if format == 'JPG':
                        format = 'JPEG'
                
                # Save with appropriate options
                save_kwargs = {}
                if format == 'JPEG':
                    save_kwargs['quality'] = quality
                    save_kwargs['optimize'] = True
                elif format == 'PNG':
                    save_kwargs['optimize'] = True
                elif format == 'WEBP':
                    save_kwargs['quality'] = quality
                
                save_kwargs.update(kwargs)
                
                img.save(output_path, format=format, **save_kwargs)
                return True
                
        except Exception as e:
            print(f"Image conversion failed: {e}")
            return False
    
    def to_base64(
        self,
        image_path: Union[str, Path],
        format: Optional[str] = None
    ) -> Optional[str]:
        """
        Convert image to base64 string.
        
        Args:
            image_path: Path to image
            format: Output format (defaults to input format)
            
        Returns:
            Base64 encoded string or None
        """
        if not self._pillow_available:
            # Fallback: read binary and encode
            try:
                with open(image_path, 'rb') as f:
                    return base64.b64encode(f.read()).decode()
            except Exception:
                return None
        
        try:
            from PIL import Image
            
            input_path = Path(image_path)
            
            with Image.open(input_path) as img:
                # Determine format
                if format is None:
                    format = img.format or 'PNG'
                
                # Convert to RGB if necessary
                if img.mode in ('RGBA', 'P'):
                    img = img.convert('RGB')
                
                # Save to buffer
                buffer = io.BytesIO()
                img.save(buffer, format=format)
                buffer.seek(0)
                
                return base64.b64encode(buffer.read()).decode()
                
        except Exception:
            return None
    
    def from_base64(
        self,
        base64_string: str,
        output_path: Union[str, Path]
    ) -> bool:
        """
        Save base64 string to image file.
        
        Args:
            base64_string: Base64 encoded image
            output_path: Output file path
            
        Returns:
            True if successful
        """
        try:
            output_path = Path(output_path)
            output_path.parent.mkdir(parents=True, exist_ok=True)
            
            image_data = base64.b64decode(base64_string)
            output_path.write_bytes(image_data)
            return True
        except Exception:
            return False
    
    def resize(
        self,
        input_path: Union[str, Path],
        output_path: Union[str, Path],
        width: Optional[int] = None,
        height: Optional[int] = None,
        max_size: Optional[Tuple[int, int]] = None
    ) -> bool:
        """
        Resize image.
        
        Args:
            input_path: Input image path
            output_path: Output image path
            width: New width (optional)
            height: New height (optional)
            max_size: Max (width, height) to fit within
            
        Returns:
            True if successful
        """
        if not self._pillow_available:
            raise ImportError("Pillow is required for image resizing")
        
        try:
            from PIL import Image
            
            with Image.open(input_path) as img:
                # Calculate new size
                if max_size:
                    img.thumbnail(max_size, Image.Resampling.LANCZOS)
                elif width or height:
                    w = width or img.width
                    h = height or img.height
                    img = img.resize((w, h), Image.Resampling.LANCZOS)
                
                img.save(output_path)
                return True
                
        except Exception:
            return False


# Convenience functions
def image_to_base64(image_path: Union[str, Path]) -> Optional[str]:
    """Convert image to base64"""
    converter = ImageConverter()
    return converter.to_base64(image_path)


def convert_image(
    input_path: Union[str, Path],
    output_path: Union[str, Path],
    **kwargs
) -> bool:
    """Convert image format"""
    converter = ImageConverter()
    return converter.convert(input_path, output_path, **kwargs)


__all__ = [
    "ImageConverter",
    "ImageInfo",
    "image_to_base64",
    "convert_image",
]
