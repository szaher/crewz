"""
Artifact preview generator service.

Generates previews for various file types with Redis caching.
"""

import json
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional, Dict, Any
from uuid import UUID
from enum import Enum

from sqlalchemy.orm import Session

from ..models.artifact import Artifact, ArtifactType


logger = logging.getLogger(__name__)


class PreviewType(str, Enum):
    """Types of previews that can be generated."""
    JSON = "json"
    TABLE = "table"
    IMAGE = "image"
    TEXT = "text"
    CODE = "code"
    PDF = "pdf"
    UNSUPPORTED = "unsupported"


class PreviewGenerator:
    """
    Generate previews for different artifact types.

    Features:
    - JSON: Syntax-highlighted with pygments
    - CSV: Pandas table (max 100 rows)
    - Images: Pillow thumbnail (max 800x600)
    - PDF: First page thumbnail via PyMuPDF
    - Code: Syntax-highlighted with pygments
    - Redis caching with 1-hour TTL
    """

    # Maximum file size for preview generation (10MB per NFR-002)
    MAX_PREVIEW_SIZE_BYTES = 10 * 1024 * 1024

    # Image thumbnail dimensions
    MAX_THUMBNAIL_SIZE = (800, 600)

    # CSV preview row limit
    MAX_CSV_ROWS = 100

    # Text preview character limit
    MAX_TEXT_CHARS = 50000


    def __init__(self, redis_client=None):
        """
        Initialize preview generator.

        Args:
            redis_client: Optional Redis client for caching (if None, no caching)
        """
        self.redis_client = redis_client
        self.cache_ttl = 3600  # 1 hour


    def _get_cache_key(self, artifact_id: UUID) -> str:
        """Generate Redis cache key for artifact preview."""
        return f"artifact_preview:{artifact_id}"


    async def generate_preview(
        self,
        artifact: Artifact,
        file_path: Path,
        force_regenerate: bool = False
    ) -> Dict[str, Any]:
        """
        Generate preview for artifact.

        Args:
            artifact: Artifact model instance
            file_path: Path to artifact file (local filesystem)
            force_regenerate: Skip cache and regenerate preview

        Returns:
            dict: Preview data with structure:
                {
                    "preview_type": PreviewType,
                    "content": <preview-specific structure>,
                    "cached": bool,
                    "generated_at": ISO timestamp
                }

        Raises:
            ValueError: If file is too large or unsupported
        """
        from datetime import datetime

        # Check cache first (unless force regenerate)
        if not force_regenerate and self.redis_client:
            cached = await self._get_cached_preview(artifact.id)
            if cached:
                logger.debug(f"Retrieved cached preview for artifact {artifact.id}")
                return {**cached, "cached": True}

        # Validate file size
        if artifact.file_size_bytes > self.MAX_PREVIEW_SIZE_BYTES:
            raise ValueError(
                f"File too large for preview ({artifact.file_size_bytes} bytes). "
                f"Maximum: {self.MAX_PREVIEW_SIZE_BYTES} bytes"
            )

        # Generate preview based on artifact type
        try:
            if artifact.artifact_type == ArtifactType.DATA:
                preview = await self._generate_data_preview(artifact, file_path)
            elif artifact.artifact_type == ArtifactType.IMAGE:
                preview = await self._generate_image_preview(artifact, file_path)
            elif artifact.artifact_type == ArtifactType.CODE:
                preview = await self._generate_code_preview(artifact, file_path)
            elif artifact.artifact_type == ArtifactType.DOCUMENT:
                preview = await self._generate_document_preview(artifact, file_path)
            else:
                preview = {
                    "preview_type": PreviewType.UNSUPPORTED,
                    "content": {"message": f"Preview not supported for {artifact.artifact_type}"},
                    "cached": False
                }

            # Add timestamp
            preview["generated_at"] = datetime.utcnow().isoformat()

            # Cache the preview
            if self.redis_client:
                await self._cache_preview(artifact.id, preview)

            logger.info(f"Generated {preview['preview_type']} preview for artifact {artifact.id}")
            return preview

        except Exception as e:
            logger.error(f"Failed to generate preview for artifact {artifact.id}: {e}")
            return {
                "preview_type": PreviewType.UNSUPPORTED,
                "content": {"error": str(e)},
                "cached": False,
                "generated_at": datetime.utcnow().isoformat()
            }


    async def _generate_data_preview(self, artifact: Artifact, file_path: Path) -> Dict[str, Any]:
        """Generate preview for data files (JSON, CSV, etc.)."""
        ext = artifact.file_extension.lower().lstrip(".")

        if ext == "json":
            return await self._generate_json_preview(file_path)
        elif ext == "csv":
            return await self._generate_csv_preview(file_path)
        elif ext in ["yaml", "yml"]:
            return await self._generate_yaml_preview(file_path)
        else:
            # Fallback to text preview
            return await self._generate_text_preview(file_path)


    async def _generate_json_preview(self, file_path: Path) -> Dict[str, Any]:
        """Generate JSON preview with syntax highlighting."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse to validate JSON
            data = json.loads(content)

            # Pretty-print with indentation
            formatted = json.dumps(data, indent=2, ensure_ascii=False)

            # Try to apply syntax highlighting if pygments available
            try:
                from pygments import highlight
                from pygments.lexers import JsonLexer
                from pygments.formatters import HtmlFormatter

                highlighted = highlight(
                    formatted,
                    JsonLexer(),
                    HtmlFormatter(style="monokai", noclasses=True)
                )

                return {
                    "preview_type": PreviewType.JSON,
                    "content": {
                        "raw": formatted[:self.MAX_TEXT_CHARS],
                        "highlighted": highlighted[:self.MAX_TEXT_CHARS * 2],  # HTML is larger
                        "truncated": len(formatted) > self.MAX_TEXT_CHARS
                    },
                    "cached": False
                }
            except ImportError:
                logger.warning("Pygments not available, returning raw JSON")
                return {
                    "preview_type": PreviewType.JSON,
                    "content": {
                        "raw": formatted[:self.MAX_TEXT_CHARS],
                        "truncated": len(formatted) > self.MAX_TEXT_CHARS
                    },
                    "cached": False
                }

        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")


    async def _generate_csv_preview(self, file_path: Path) -> Dict[str, Any]:
        """Generate CSV preview as table using pandas."""
        try:
            import pandas as pd

            # Read CSV with row limit
            df = pd.read_csv(file_path, nrows=self.MAX_CSV_ROWS)

            # Get basic stats
            total_rows = sum(1 for _ in open(file_path)) - 1  # Subtract header
            truncated = total_rows > self.MAX_CSV_ROWS

            return {
                "preview_type": PreviewType.TABLE,
                "content": {
                    "columns": df.columns.tolist(),
                    "rows": df.values.tolist(),
                    "total_rows": total_rows,
                    "displayed_rows": len(df),
                    "truncated": truncated,
                    "dtypes": df.dtypes.astype(str).to_dict()
                },
                "cached": False
            }

        except Exception as e:
            raise ValueError(f"Failed to read CSV: {e}")


    async def _generate_yaml_preview(self, file_path: Path) -> Dict[str, Any]:
        """Generate YAML preview."""
        try:
            import yaml

            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()

            # Parse YAML
            data = yaml.safe_load(content)

            # Convert back to formatted YAML
            formatted = yaml.dump(data, default_flow_style=False, allow_unicode=True)

            return {
                "preview_type": PreviewType.TEXT,
                "content": {
                    "text": formatted[:self.MAX_TEXT_CHARS],
                    "truncated": len(formatted) > self.MAX_TEXT_CHARS,
                    "language": "yaml"
                },
                "cached": False
            }

        except Exception as e:
            raise ValueError(f"Failed to parse YAML: {e}")


    async def _generate_image_preview(self, artifact: Artifact, file_path: Path) -> Dict[str, Any]:
        """Generate image thumbnail using Pillow."""
        try:
            from PIL import Image

            with Image.open(file_path) as img:
                # Get original dimensions
                original_size = img.size

                # Create thumbnail
                img.thumbnail(self.MAX_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

                # Convert to base64
                buffer = BytesIO()
                img_format = img.format or "PNG"
                img.save(buffer, format=img_format)
                buffer.seek(0)
                thumbnail_b64 = base64.b64encode(buffer.read()).decode("utf-8")

                return {
                    "preview_type": PreviewType.IMAGE,
                    "content": {
                        "thumbnail": f"data:image/{img_format.lower()};base64,{thumbnail_b64}",
                        "original_size": original_size,
                        "thumbnail_size": img.size,
                        "format": img_format,
                        "mode": img.mode
                    },
                    "cached": False
                }

        except Exception as e:
            raise ValueError(f"Failed to generate image preview: {e}")


    async def _generate_code_preview(self, artifact: Artifact, file_path: Path) -> Dict[str, Any]:
        """Generate code preview with syntax highlighting."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(self.MAX_TEXT_CHARS)

            truncated = file_path.stat().st_size > self.MAX_TEXT_CHARS

            # Detect language from extension
            ext = artifact.file_extension.lower().lstrip(".")
            language_map = {
                "py": "python",
                "js": "javascript",
                "ts": "typescript",
                "java": "java",
                "cpp": "cpp",
                "c": "c",
                "go": "go",
                "rs": "rust",
                "sh": "bash",
                "sql": "sql",
                "rb": "ruby",
                "php": "php"
            }
            language = language_map.get(ext, "text")

            # Try to apply syntax highlighting if pygments available
            try:
                from pygments import highlight, lexers
                from pygments.formatters import HtmlFormatter

                lexer = lexers.get_lexer_by_name(language)
                highlighted = highlight(
                    content,
                    lexer,
                    HtmlFormatter(style="monokai", noclasses=True, linenos=True)
                )

                return {
                    "preview_type": PreviewType.CODE,
                    "content": {
                        "raw": content,
                        "highlighted": highlighted,
                        "language": language,
                        "truncated": truncated
                    },
                    "cached": False
                }
            except ImportError:
                logger.warning("Pygments not available, returning raw code")
                return {
                    "preview_type": PreviewType.CODE,
                    "content": {
                        "raw": content,
                        "language": language,
                        "truncated": truncated
                    },
                    "cached": False
                }

        except Exception as e:
            raise ValueError(f"Failed to generate code preview: {e}")


    async def _generate_document_preview(self, artifact: Artifact, file_path: Path) -> Dict[str, Any]:
        """Generate document preview (PDF, text, etc.)."""
        ext = artifact.file_extension.lower().lstrip(".")

        if ext == "pdf":
            return await self._generate_pdf_preview(file_path)
        elif ext in ["txt", "md"]:
            return await self._generate_text_preview(file_path)
        else:
            raise ValueError(f"Document type {ext} not supported for preview")


    async def _generate_pdf_preview(self, file_path: Path) -> Dict[str, Any]:
        """Generate PDF preview (first page thumbnail)."""
        try:
            import fitz  # PyMuPDF

            doc = fitz.open(file_path)
            page_count = len(doc)

            if page_count == 0:
                raise ValueError("PDF has no pages")

            # Render first page as image
            page = doc[0]
            pix = page.get_pixmap(matrix=fitz.Matrix(2, 2))  # 2x zoom for better quality

            # Convert to PNG bytes
            png_bytes = pix.tobytes("png")

            # Create thumbnail with Pillow
            from PIL import Image
            img = Image.open(BytesIO(png_bytes))
            img.thumbnail(self.MAX_THUMBNAIL_SIZE, Image.Resampling.LANCZOS)

            # Convert to base64
            buffer = BytesIO()
            img.save(buffer, format="PNG")
            buffer.seek(0)
            thumbnail_b64 = base64.b64encode(buffer.read()).decode("utf-8")

            doc.close()

            return {
                "preview_type": PreviewType.PDF,
                "content": {
                    "thumbnail": f"data:image/png;base64,{thumbnail_b64}",
                    "page_count": page_count,
                    "thumbnail_size": img.size
                },
                "cached": False
            }

        except Exception as e:
            raise ValueError(f"Failed to generate PDF preview: {e}")


    async def _generate_text_preview(self, file_path: Path) -> Dict[str, Any]:
        """Generate plain text preview."""
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read(self.MAX_TEXT_CHARS)

            truncated = file_path.stat().st_size > self.MAX_TEXT_CHARS

            return {
                "preview_type": PreviewType.TEXT,
                "content": {
                    "text": content,
                    "truncated": truncated
                },
                "cached": False
            }

        except UnicodeDecodeError:
            raise ValueError("File is not valid UTF-8 text")


    async def _get_cached_preview(self, artifact_id: UUID) -> Optional[Dict[str, Any]]:
        """Retrieve cached preview from Redis."""
        try:
            cache_key = self._get_cache_key(artifact_id)
            cached_json = await self.redis_client.get(cache_key)
            if cached_json:
                return json.loads(cached_json)
            return None
        except Exception as e:
            logger.warning(f"Failed to retrieve cached preview: {e}")
            return None


    async def _cache_preview(self, artifact_id: UUID, preview: Dict[str, Any]):
        """Cache preview in Redis with TTL."""
        try:
            cache_key = self._get_cache_key(artifact_id)
            await self.redis_client.setex(
                cache_key,
                self.cache_ttl,
                json.dumps(preview)
            )
        except Exception as e:
            logger.warning(f"Failed to cache preview: {e}")


# Singleton instance
_preview_generator: Optional[PreviewGenerator] = None


def get_preview_generator(redis_client=None) -> PreviewGenerator:
    """Get or create singleton preview generator."""
    global _preview_generator
    if _preview_generator is None:
        _preview_generator = PreviewGenerator(redis_client=redis_client)
    return _preview_generator
