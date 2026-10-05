import io
import logging
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import tempfile

from app.core.config import get_settings
from app.core.exceptions import BadRequestError

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".txt"}
SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS


@dataclass
class ExtractedImage:
    data: bytes
    name: str = ""
    format: str = "png"
    width: int = 0
    height: int = 0


@dataclass
class DocumentPage:
    page_number: int  # 1-indexed
    text: str = ""
    images: list[ExtractedImage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)


def parse_document_pages(file_path: str) -> list[DocumentPage]:
    """Extract structured pages and embedded/scanned images from a document."""
    suffix = Path(file_path).suffix.lower()

    if suffix == ".pdf":
        return _parse_pdf_pages(file_path)
    if suffix == ".docx":
        return _parse_docx_pages(file_path)
    if suffix == ".pptx":
        return _parse_pptx_pages(file_path)
    if suffix == ".xlsx":
        return _parse_xlsx_pages(file_path)
    if suffix == ".txt":
        return _parse_txt_pages(file_path)
    if suffix in IMAGE_EXTENSIONS:
        return _parse_image_pages(file_path)

    raise BadRequestError(f"Unsupported file type: {suffix}")


def parse_document(file_path: str) -> str:
    """Extract plain text from a supported document format.

    Preserved for backward compatibility; joins all extracted page texts.
    """
    pages = parse_document_pages(file_path)
    return "\n\n".join(p.text for p in pages if p.text.strip())


def _parse_txt_pages(file_path: str) -> list[DocumentPage]:
    text = _parse_txt(file_path)
    return [DocumentPage(page_number=1, text=text, metadata={"page": 1})]


def _parse_txt(file_path: str) -> str:
    """Decodes a .txt file, detecting UTF-16 instead of assuming UTF-8 outright."""
    raw = Path(file_path).read_bytes()

    if raw.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = raw.decode("utf-16")
    elif raw.startswith(b"\xef\xbb\xbf"):
        text = raw.decode("utf-8-sig")
    else:
        sample = raw[:4000]
        if sample.count(b"\x00") > len(sample) // 4:
            try:
                text = raw.decode("utf-16-le")
            except UnicodeDecodeError:
                text = raw.decode("utf-8", errors="ignore")
        else:
            text = raw.decode("utf-8", errors="ignore")

    return text.replace("\x00", "")


def _parse_image_pages(file_path: str) -> list[DocumentPage]:
    """Parses a direct image file as a single-page document with one image to OCR."""
    from PIL import Image

    data = Path(file_path).read_bytes()
    suffix = Path(file_path).suffix.lower().lstrip(".")
    w, h = 0, 0
    fmt = suffix
    try:
        with Image.open(io.BytesIO(data)) as pil_img:
            w, h = pil_img.size
            fmt = (pil_img.format or suffix).lower()
    except Exception:
        pass

    img = ExtractedImage(
        data=data,
        name=Path(file_path).name,
        format=fmt,
        width=w,
        height=h,
    )
    return [DocumentPage(page_number=1, text="", images=[img], metadata={"page": 1})]


def _try_render_pdf_page_with_pdftoppm(file_path: str, page_number: int) -> ExtractedImage | None:
    """Renders a PDF page to PNG using pdftoppm if available."""
    try:
        with tempfile.TemporaryDirectory() as tmpdir:
            out_prefix = Path(tmpdir) / "page"
            cmd = [
                "pdftoppm",
                "-png",
                "-f",
                str(page_number),
                "-l",
                str(page_number),
                "-r",
                "150",
                file_path,
                str(out_prefix),
            ]
            res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=20)
            if res.returncode == 0:
                rendered = sorted(Path(tmpdir).glob("page-*.png"))
                if rendered:
                    data = rendered[0].read_bytes()
                    return ExtractedImage(
                        data=data,
                        name=f"rendered_page_{page_number}.png",
                        format="png",
                    )
    except Exception as exc:
        logger.debug("pdftoppm rendering failed for page %d of %s: %s", page_number, file_path, exc)
    return None


def _parse_pdf_pages(file_path: str) -> list[DocumentPage]:
    """Extracts text and embedded images page by page from a PDF."""
    from PIL import Image
    from pypdf import PdfReader

    settings = get_settings()
    min_dim = getattr(settings, "ocr_min_image_dimension", 60)

    reader = PdfReader(file_path)
    pages: list[DocumentPage] = []

    for idx, page in enumerate(reader.pages, start=1):
        page_text = (page.extract_text() or "").strip()
        extracted_images: list[ExtractedImage] = []

        try:
            for img in page.images:
                img_bytes = img.data
                try:
                    with Image.open(io.BytesIO(img_bytes)) as pil_img:
                        w, h = pil_img.size
                        # Filter out tiny icons, spacers, dots, bullets
                        if w >= min_dim and h >= min_dim:
                            fmt = (pil_img.format or "PNG").lower()
                            extracted_images.append(
                                ExtractedImage(
                                    data=img_bytes,
                                    name=getattr(img, "name", f"img_{idx}_{len(extracted_images)}"),
                                    format=fmt,
                                    width=w,
                                    height=h,
                                )
                            )
                except Exception:
                    if len(img_bytes) > 2048:
                        extracted_images.append(
                            ExtractedImage(
                                data=img_bytes,
                                name=getattr(img, "name", f"img_{idx}_{len(extracted_images)}"),
                            )
                        )
        except Exception as exc:
            logger.warning("Error reading images from page %d of %s: %s", idx, file_path, exc)

        # Scanned PDF fallback: if page has no extracted text AND no embedded images extracted by pypdf
        if not page_text and not extracted_images:
            rendered = _try_render_pdf_page_with_pdftoppm(file_path, idx)
            if rendered:
                extracted_images.append(rendered)

        pages.append(
            DocumentPage(
                page_number=idx,
                text=page_text,
                images=extracted_images,
                metadata={"page": idx},
            )
        )

    return pages


def _parse_docx_pages(file_path: str) -> list[DocumentPage]:
    import docx

    document = docx.Document(file_path)
    paragraphs = [p.text.strip() for p in document.paragraphs if p.text.strip()]

    # Extract tables
    for table in document.tables:
        table_rows = []
        for row in table.rows:
            cells = [c.text.strip() for c in row.cells]
            if any(cells):
                table_rows.append(" | ".join(cells))
        if table_rows:
            paragraphs.append("\n".join(table_rows))

    text = "\n\n".join(paragraphs)

    # Extract embedded images
    images: list[ExtractedImage] = []
    settings = get_settings()
    min_dim = getattr(settings, "ocr_min_image_dimension", 60)
    try:
        from PIL import Image

        for rel in document.part.rels.values():
            if "image" in rel.target_ref.lower():
                img_data = rel.target_part.blob
                try:
                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        w, h = pil_img.size
                        if w >= min_dim and h >= min_dim:
                            images.append(
                                ExtractedImage(
                                    data=img_data,
                                    name=rel.target_ref,
                                    format=(pil_img.format or "png").lower(),
                                    width=w,
                                    height=h,
                                )
                            )
                except Exception:
                    pass
    except Exception as exc:
        logger.debug("Failed extracting docx images: %s", exc)

    return [DocumentPage(page_number=1, text=text, images=images, metadata={"page": 1})]


def _parse_pptx_pages(file_path: str) -> list[DocumentPage]:
    from pptx import Presentation
    from pptx.enum.shapes import MSO_SHAPE_TYPE

    presentation = Presentation(file_path)
    pages: list[DocumentPage] = []
    settings = get_settings()
    min_dim = getattr(settings, "ocr_min_image_dimension", 60)

    for idx, slide in enumerate(presentation.slides, start=1):
        slide_texts: list[str] = []
        slide_images: list[ExtractedImage] = []

        for shape in slide.shapes:
            if shape.has_text_frame:
                slide_texts.append(shape.text_frame.text)
            if shape.has_table:
                for row in shape.table.rows:
                    cells = [c.text.strip() for c in row.cells]
                    if any(cells):
                        slide_texts.append(" | ".join(cells))
            if shape.shape_type == MSO_SHAPE_TYPE.PICTURE:
                try:
                    img_data = shape.image.blob
                    from PIL import Image

                    with Image.open(io.BytesIO(img_data)) as pil_img:
                        w, h = pil_img.size
                        if w >= min_dim and h >= min_dim:
                            slide_images.append(
                                ExtractedImage(
                                    data=img_data,
                                    name=shape.name or f"slide_{idx}_img",
                                    format=(pil_img.format or "png").lower(),
                                    width=w,
                                    height=h,
                                )
                            )
                except Exception:
                    pass

        pages.append(
            DocumentPage(
                page_number=idx,
                text="\n".join(t for t in slide_texts if t.strip()),
                images=slide_images,
                metadata={"page": idx},
            )
        )

    return pages


def _parse_xlsx_pages(file_path: str) -> list[DocumentPage]:
    from openpyxl import load_workbook

    workbook = load_workbook(file_path, data_only=True, read_only=True)
    pages: list[DocumentPage] = []

    for idx, sheet in enumerate(workbook.worksheets, start=1):
        lines: list[str] = [f"=== Sheet: {sheet.title} ==="]
        for row in sheet.iter_rows(values_only=True):
            cells = [str(cell) for cell in row if cell is not None]
            if cells:
                lines.append(" | ".join(cells))
        pages.append(
            DocumentPage(
                page_number=idx,
                text="\n".join(lines),
                metadata={"page": idx, "sheet_name": sheet.title},
            )
        )

    return pages
