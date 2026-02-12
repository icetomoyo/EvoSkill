"""
Photon Utilities - 图片处理辅助工具

提供图片处理、尺寸检测、格式转换等功能。
需要 Pillow 库支持。
"""
import base64
import io
from dataclasses import dataclass
from pathlib import Path
from typing import Optional, Union, Tuple, List, Callable

# 检查 Pillow 是否可用
try:
    from PIL import Image, ImageOps, ImageFilter, ImageEnhance
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False
    Image = None
    ImageOps = None
    ImageFilter = None
    ImageEnhance = None


@dataclass
class ImageSize:
    """图片尺寸"""
    width: int
    height: int

    @property
    def aspect_ratio(self) -> float:
        """宽高比"""
        return self.width / self.height if self.height != 0 else 0

    @property
    def is_portrait(self) -> bool:
        """是否竖向"""
        return self.height > self.width

    @property
    def is_landscape(self) -> bool:
        """是否横向"""
        return self.width > self.height

    @property
    def is_square(self) -> bool:
        """是否正方形"""
        return self.width == self.height

    @property
    def megapixels(self) -> float:
        """百万像素"""
        return (self.width * self.height) / 1_000_000

    def __str__(self) -> str:
        return f"{self.width}x{self.height}"

    def fits_within(self, max_width: int, max_height: int) -> bool:
        """检查是否在指定尺寸内"""
        return self.width <= max_width and self.height <= max_height


@dataclass
class ImageMetadata:
    """图片元数据"""
    size: ImageSize
    format: str
    mode: str
    file_size: int
    exif: Optional[dict] = None
    dpi: Optional[Tuple[int, int]] = None


@dataclass
class ResizeResult:
    """图片调整结果"""
    data: str  # base64 编码
    original_size: ImageSize
    new_size: ImageSize
    was_resized: bool
    mime_type: str


@dataclass
class ConvertResult:
    """格式转换结果"""
    success: bool
    data: Optional[str] = None  # base64 编码
    original_format: str = ""
    new_format: str = ""
    error: Optional[str] = None


def check_pillow_available() -> bool:
    """
    检查 Pillow 库是否可用

    Returns:
        True 如果 Pillow 可用
    """
    return PIL_AVAILABLE


def get_image_size(image_path: Union[str, Path]) -> Optional[ImageSize]:
    """
    获取图片尺寸

    Args:
        image_path: 图片路径

    Returns:
        ImageSize 对象，失败返回 None

    Example:
        >>> size = get_image_size("photo.jpg")
        >>> print(f"{size.width}x{size.height}")
    """
    if not PIL_AVAILABLE:
        return _get_size_without_pillow(image_path)

    try:
        with Image.open(image_path) as img:
            return ImageSize(width=img.width, height=img.height)
    except Exception:
        return None


def _get_size_without_pillow(image_path: Union[str, Path]) -> Optional[ImageSize]:
    """不使用 Pillow 获取图片尺寸（仅支持部分格式）"""
    path = Path(image_path)

    if not path.exists():
        return None

    try:
        with open(path, "rb") as f:
            header = f.read(24)

        # PNG
        if header[:8] == b'\x89PNG\r\n\x1a\n':
            f.seek(16)
            width = int.from_bytes(f.read(4), 'big')
            height = int.from_bytes(f.read(4), 'big')
            return ImageSize(width=width, height=height)

        # JPEG (简化处理)
        if header[:2] == b'\xff\xd8':
            # JPEG 尺寸解析较复杂，需要扫描
            return None

        # GIF
        if header[:6] in (b'GIF87a', b'GIF89a'):
            width = int.from_bytes(header[6:8], 'little')
            height = int.from_bytes(header[8:10], 'little')
            return ImageSize(width=width, height=height)

        return None

    except Exception:
        return None


def get_image_metadata(image_path: Union[str, Path]) -> Optional[ImageMetadata]:
    """
    获取图片元数据

    Args:
        image_path: 图片路径

    Returns:
        ImageMetadata 对象，失败返回 None
    """
    if not PIL_AVAILABLE:
        return None

    try:
        path = Path(image_path)
        with Image.open(path) as img:
            # 获取 EXIF 数据
            exif = None
            if hasattr(img, '_getexif') and img._getexif():
                from PIL.ExifTags import TAGS
                exif = {}
                for tag_id, value in img._getexif().items():
                    tag = TAGS.get(tag_id, tag_id)
                    exif[tag] = value

            return ImageMetadata(
                size=ImageSize(width=img.width, height=img.height),
                format=img.format or "Unknown",
                mode=img.mode,
                file_size=path.stat().st_size,
                exif=exif,
                dpi=img.info.get('dpi')
            )
    except Exception:
        return None


def resize_image(
    source: Union[str, Path, bytes],
    max_width: int = 2000,
    max_height: int = 2000,
    max_bytes: int = 4 * 1024 * 1024,  # 4.5MB
    quality: int = 85,
    maintain_aspect: bool = True
) -> ResizeResult:
    """
    调整图片大小

    保持宽高比，同时限制尺寸和文件大小。

    Args:
        source: 图片路径或字节数据
        max_width: 最大宽度
        max_height: 最大高度
        max_bytes: 最大文件大小（字节）
        quality: JPEG 质量 (1-100)
        maintain_aspect: 是否保持宽高比

    Returns:
        ResizeResult 对象

    Example:
        >>> result = resize_image("large.jpg", max_width=800, max_height=600)
        >>> if result.was_resized:
        ...     print(f"Resized from {result.original_size} to {result.new_size}")
    """
    if not PIL_AVAILABLE:
        raise ImportError("Pillow is required for image resizing. Install with: pip install Pillow")

    # 加载图片
    if isinstance(source, (str, Path)):
        with Image.open(source) as img:
            return _do_resize(img, max_width, max_height, max_bytes, quality, maintain_aspect)
    else:
        # 字节数据
        img = Image.open(io.BytesIO(source))
        result = _do_resize(img, max_width, max_height, max_bytes, quality, maintain_aspect)
        img.close()
        return result


def _do_resize(
    img: "Image.Image",
    max_width: int,
    max_height: int,
    max_bytes: int,
    quality: int,
    maintain_aspect: bool
) -> ResizeResult:
    """执行图片调整"""
    original_size = ImageSize(width=img.width, height=img.height)
    original_format = img.format or "PNG"

    # 确定输出格式
    if img.mode in ('RGBA', 'LA', 'P'):
        output_format = "PNG"
        mime_type = "image/png"
    else:
        output_format = "JPEG"
        mime_type = "image/jpeg"

    # 检查是否需要调整尺寸
    needs_resize = original_size.width > max_width or original_size.height > max_height

    current_img = img.copy()

    # 调整尺寸
    if needs_resize:
        if maintain_aspect:
            current_img.thumbnail((max_width, max_height), Image.Resampling.LANCZOS)
        else:
            current_img = current_img.resize((max_width, max_height), Image.Resampling.LANCZOS)

    new_size = ImageSize(width=current_img.width, height=current_img.height)

    # 转换模式（如果需要）
    if output_format == "JPEG" and current_img.mode in ('RGBA', 'LA', 'P'):
        # 创建白色背景
        background = Image.new('RGB', current_img.size, (255, 255, 255))
        if current_img.mode == 'P':
            current_img = current_img.convert('RGBA')
        background.paste(current_img, mask=current_img.split()[-1] if current_img.mode == 'RGBA' else None)
        current_img = background

    # 保存并检查大小
    buffer = io.BytesIO()
    current_img.save(buffer, format=output_format, quality=quality, optimize=True)
    data_bytes = buffer.getvalue()

    # 如果仍然太大，降低质量
    while len(data_bytes) > max_bytes and quality > 10:
        quality -= 10
        buffer = io.BytesIO()
        current_img.save(buffer, format=output_format, quality=quality, optimize=True)
        data_bytes = buffer.getvalue()

    current_img.close()

    return ResizeResult(
        data=base64.b64encode(data_bytes).decode('utf-8'),
        original_size=original_size,
        new_size=new_size,
        was_resized=needs_resize or len(data_bytes) < len(buffer.getvalue()),
        mime_type=mime_type
    )


def convert_format(
    source: Union[str, Path, bytes],
    target_format: str,
    quality: int = 85
) -> ConvertResult:
    """
    转换图片格式

    Args:
        source: 图片路径或字节数据
        target_format: 目标格式 (JPEG, PNG, WEBP, GIF)
        quality: 质量 (1-100)

    Returns:
        ConvertResult 对象

    Example:
        >>> result = convert_format("image.png", "JPEG")
        >>> if result.success:
        ...     # 保存 result.data
    """
    if not PIL_AVAILABLE:
        return ConvertResult(
            success=False,
            error="Pillow is required for image conversion"
        )

    target_format = target_format.upper()

    try:
        # 加载图片
        if isinstance(source, (str, Path)):
            with Image.open(source) as img:
                return _do_convert(img, target_format, quality)
        else:
            img = Image.open(io.BytesIO(source))
            result = _do_convert(img, target_format, quality)
            img.close()
            return result

    except Exception as e:
        return ConvertResult(success=False, error=str(e))


def _do_convert(img: "Image.Image", target_format: str, quality: int) -> ConvertResult:
    """执行格式转换"""
    original_format = img.format or "Unknown"

    # 准备图片
    output_img = img.copy()

    # 格式特定的处理
    if target_format == "JPEG":
        if output_img.mode in ('RGBA', 'LA', 'P'):
            background = Image.new('RGB', output_img.size, (255, 255, 255))
            if output_img.mode == 'P':
                output_img = output_img.convert('RGBA')
            background.paste(output_img, mask=output_img.split()[-1] if output_img.mode == 'RGBA' else None)
            output_img = background

    # 保存到缓冲区
    buffer = io.BytesIO()
    save_kwargs = {'format': target_format}

    if target_format == "JPEG":
        save_kwargs['quality'] = quality
        save_kwargs['optimize'] = True
    elif target_format == "PNG":
        save_kwargs['optimize'] = True
    elif target_format == "WEBP":
        save_kwargs['quality'] = quality

    output_img.save(buffer, **save_kwargs)
    output_img.close()

    return ConvertResult(
        success=True,
        data=base64.b64encode(buffer.getvalue()).decode('utf-8'),
        original_format=original_format,
        new_format=target_format
    )


def create_thumbnail(
    source: Union[str, Path, bytes],
    size: Tuple[int, int] = (128, 128),
    format: str = "JPEG"
) -> Optional[str]:
    """
    创建缩略图

    Args:
        source: 图片路径或字节数据
        size: 缩略图尺寸 (width, height)
        format: 输出格式

    Returns:
        base64 编码的缩略图数据，失败返回 None
    """
    if not PIL_AVAILABLE:
        return None

    try:
        if isinstance(source, (str, Path)):
            with Image.open(source) as img:
                return _create_thumbnail(img, size, format)
        else:
            img = Image.open(io.BytesIO(source))
            result = _create_thumbnail(img, size, format)
            img.close()
            return result
    except Exception:
        return None


def _create_thumbnail(img: "Image.Image", size: Tuple[int, int], format: str) -> str:
    """创建缩略图"""
    thumb = img.copy()
    thumb.thumbnail(size, Image.Resampling.LANCZOS)

    # 格式处理
    if format == "JPEG" and thumb.mode in ('RGBA', 'LA', 'P'):
        background = Image.new('RGB', thumb.size, (255, 255, 255))
        if thumb.mode == 'P':
            thumb = thumb.convert('RGBA')
        background.paste(thumb, mask=thumb.split()[-1] if thumb.mode == 'RGBA' else None)
        thumb = background

    buffer = io.BytesIO()
    thumb.save(buffer, format=format, quality=85)
    thumb.close()

    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def apply_filter(
    source: Union[str, Path, bytes],
    filter_name: str
) -> Optional[str]:
    """
    应用图片滤镜

    Args:
        source: 图片路径或字节数据
        filter_name: 滤镜名称 (blur, sharpen, edge_enhance, emboss, etc.)

    Returns:
        base64 编码的图片数据，失败返回 None
    """
    if not PIL_AVAILABLE:
        return None

    filters = {
        'blur': ImageFilter.BLUR,
        'sharpen': ImageFilter.SHARPEN,
        'edge_enhance': ImageFilter.EDGE_ENHANCE,
        'emboss': ImageFilter.EMBOSS,
        'smooth': ImageFilter.SMOOTH,
        'detail': ImageFilter.DETAIL,
        'contour': ImageFilter.CONTOUR,
        'find_edges': ImageFilter.FIND_EDGES,
    }

    if filter_name.lower() not in filters:
        return None

    try:
        if isinstance(source, (str, Path)):
            with Image.open(source) as img:
                return _apply_filter(img, filters[filter_name.lower()])
        else:
            img = Image.open(io.BytesIO(source))
            result = _apply_filter(img, filters[filter_name.lower()])
            img.close()
            return result
    except Exception:
        return None


def _apply_filter(img: "Image.Image", filter_obj) -> str:
    """应用滤镜"""
    filtered = img.filter(filter_obj)

    buffer = io.BytesIO()
    format_name = img.format or "PNG"
    if format_name == "JPEG" and filtered.mode in ('RGBA', 'LA', 'P'):
        filtered = filtered.convert('RGB')
        format_name = "JPEG"

    filtered.save(buffer, format=format_name)
    filtered.close()

    return base64.b64encode(buffer.getvalue()).decode('utf-8')


def auto_orient(image_path: Union[str, Path]) -> Optional[str]:
    """
    根据 EXIF 信息自动旋转图片

    Args:
        image_path: 图片路径

    Returns:
        base64 编码的图片数据，失败返回 None
    """
    if not PIL_AVAILABLE:
        return None

    try:
        with Image.open(image_path) as img:
            # 使用 ImageOps 自动旋转
            oriented = ImageOps.exif_transpose(img)

            buffer = io.BytesIO()
            format_name = img.format or "PNG"
            oriented.save(buffer, format=format_name)

            return base64.b64encode(buffer.getvalue()).decode('utf-8')

    except Exception:
        return None


class PhotonProcessor:
    """
    图片处理器类

    提供面向对象的图片处理接口。

    Example:
        >>> processor = PhotonProcessor()
        >>> size = processor.get_size("photo.jpg")
        >>> result = processor.resize("photo.jpg", max_width=800)
    """

    def __init__(self):
        """初始化处理器"""
        self._available = PIL_AVAILABLE

    @property
    def available(self) -> bool:
        """检查是否可用"""
        return self._available

    def get_size(self, image_path: Union[str, Path]) -> Optional[ImageSize]:
        """获取图片尺寸"""
        return get_image_size(image_path)

    def get_metadata(self, image_path: Union[str, Path]) -> Optional[ImageMetadata]:
        """获取图片元数据"""
        return get_image_metadata(image_path)

    def resize(
        self,
        source: Union[str, Path, bytes],
        max_width: int = 2000,
        max_height: int = 2000,
        **kwargs
    ) -> ResizeResult:
        """调整图片大小"""
        return resize_image(source, max_width, max_height, **kwargs)

    def convert(
        self,
        source: Union[str, Path, bytes],
        target_format: str,
        quality: int = 85
    ) -> ConvertResult:
        """转换图片格式"""
        return convert_format(source, target_format, quality)

    def create_thumbnail(
        self,
        source: Union[str, Path, bytes],
        size: Tuple[int, int] = (128, 128)
    ) -> Optional[str]:
        """创建缩略图"""
        return create_thumbnail(source, size)

    def apply_filter(
        self,
        source: Union[str, Path, bytes],
        filter_name: str
    ) -> Optional[str]:
        """应用滤镜"""
        return apply_filter(source, filter_name)

    def auto_orient(self, image_path: Union[str, Path]) -> Optional[str]:
        """自动旋转图片"""
        return auto_orient(image_path)


__all__ = [
    "PIL_AVAILABLE",
    "check_pillow_available",
    "ImageSize",
    "ImageMetadata",
    "ResizeResult",
    "ConvertResult",
    "get_image_size",
    "get_image_metadata",
    "resize_image",
    "convert_format",
    "create_thumbnail",
    "apply_filter",
    "auto_orient",
    "PhotonProcessor",
]
