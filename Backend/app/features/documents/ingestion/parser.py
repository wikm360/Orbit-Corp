import io
import logging
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from dataclasses import dataclass, field
from pathlib import Path
import subprocess
import time
import tempfile

from app.core.config import get_settings
from app.core.exceptions import BadRequestError
from app.features.documents.ingestion.text_layer import TEXT_OK, TEXT_VISUAL_PERSIAN, assess_text_layer, fix_visual_persian

logger = logging.getLogger(__name__)

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tif", ".tiff"}
# Legacy/odd office formats are converted to their OOXML twin with LibreOffice first (see converter.py).
LEGACY_OFFICE_EXTENSIONS = {".xls", ".xlsm", ".ods", ".doc", ".rtf", ".odt", ".ppt", ".odp"}
DOCUMENT_EXTENSIONS = {".pdf", ".docx", ".pptx", ".xlsx", ".csv", ".txt"} | LEGACY_OFFICE_EXTENSIONS
SUPPORTED_EXTENSIONS = DOCUMENT_EXTENSIONS | IMAGE_EXTENSIONS

# A sheet is split into pages of this many rows (header row repeated on each) so a retrieved chunk is self-describing.
XLSX_ROWS_PER_PAGE = 60


@dataclass
class ExtractedImage:
    data: bytes
    name: str = ""
    format: str = "png"
    width: int = 0
    height: int = 0


# `metadata.text_layer` of a text-less page-sized-image page: read by whole-page OCR (see `_parse_pdf_range`).
TEXT_SCAN = "scan"
# An image at least this many px on its shorter side counts as a page-sized scan (logos/icons are far smaller).
_SCAN_MIN_IMAGE_SIDE = 400

# Below this a process pool costs more than it saves.
_MIN_PAGES_FOR_PARALLEL_PARSE = 8


@dataclass
class DocumentPage:
    page_number: int  # 1-indexed
    text: str = ""
    images: list[ExtractedImage] = field(default_factory=list)
    metadata: dict = field(default_factory=dict)
    # PDF only: the extracted text layer is unusable (see ingestion/text_layer.py); the OCR step should replace it.
    needs_ocr: bool = False


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
    if suffix == ".csv":
        return _parse_csv_pages(file_path)
    if suffix in LEGACY_OFFICE_EXTENSIONS:
        from app.features.documents.ingestion.converter import converted_copy

        with converted_copy(file_path) as modern:
            return parse_document_pages(modern)
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
    settings = get_settings()
    dpi = str(getattr(settings, "pdf_render_dpi", 200))
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
                dpi,
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
    """Extracts text and embedded images page by page from a PDF.

    Decoding scanned page images is CPU-bound (~1s/page), so long PDFs are split into page ranges parsed by several
    processes (`PDF_PARSE_WORKERS`); any pool failure falls back to the single-process path."""
    from pypdf import PdfReader

    settings = get_settings()
    workers = max(1, getattr(settings, "pdf_parse_workers", 1))
    total = len(PdfReader(file_path).pages)
    started = time.monotonic()

    if workers > 1 and total >= _MIN_PAGES_FOR_PARALLEL_PARSE:
        try:
            size = max(1, -(-total // (workers * 3)))  # several small ranges per process: page cost varies
            ranges = [(file_path, lo, min(lo + size - 1, total)) for lo in range(1, total + 1, size)]
            ctx = multiprocessing.get_context("fork")
            with ProcessPoolExecutor(max_workers=workers, mp_context=ctx) as pool:
                results = list(pool.map(_parse_pdf_range_star, ranges))
            pages = [page for chunk_pages, _ in results for page in chunk_pages]
            spent = {k: sum(r[1][k] for r in results) for k in ("text", "images", "render")}
            _log_pdf_parse(file_path, len(pages), started, spent, workers)
            return pages
        except Exception as exc:  # noqa: BLE001
            logger.warning("Parallel PDF parse failed for %s (%s); falling back to a single process.", file_path, exc)

    pages, spent = _parse_pdf_range(file_path, 1, total)
    _log_pdf_parse(file_path, len(pages), started, spent, 1)
    return pages


def _log_pdf_parse(file_path: str, page_count: int, started: float, spent: dict, workers: int) -> None:
    logger.info(
        "PDF parse %s: %d pages in %.1fs with %d process(es) (CPU-seconds: text extraction %.1f, embedded images %.1f, "
        "pdftoppm fallback %.1f)",
        file_path,
        page_count,
        time.monotonic() - started,
        workers,
        spent["text"],
        spent["images"],
        spent["render"],
    )


def _has_page_sized_image(page) -> bool:
    """True if the page's resources hold an image XObject of at least `_SCAN_MIN_IMAGE_SIDE` px (read from the PDF
    dictionary - nothing is decoded). Images nested in form XObjects are not inspected (-> the per-image path)."""
    try:
        for xobject in page["/Resources"]["/XObject"].get_object().values():
            obj = xobject.get_object()
            if obj.get("/Subtype") == "/Image" and min(int(obj.get("/Width", 0)), int(obj.get("/Height", 0))) >= _SCAN_MIN_IMAGE_SIDE:
                return True
    except Exception:  # noqa: BLE001 - missing/odd resources: fall back to the per-image path
        pass
    return False


def _parse_pdf_range_star(args: tuple[str, int, int]) -> tuple[list[DocumentPage], dict]:
    return _parse_pdf_range(*args)


def _parse_pdf_range(file_path: str, first: int, last: int) -> tuple[list[DocumentPage], dict]:
    """Parses pages `first..last` (1-indexed, inclusive); returns the pages and per-phase CPU seconds."""
    from PIL import Image, ImageOps
    from pypdf import PdfReader

    settings = get_settings()
    min_dim = getattr(settings, "ocr_min_image_dimension", 60)
    # Only when the OCR step will actually read the page; otherwise keep the old per-image behaviour.
    scan_by_page_ocr = bool(getattr(settings, "ocr_enabled", True) and getattr(settings, "ocr_replace_bad_text_layer", True))

    reader = PdfReader(file_path)
    pages: list[DocumentPage] = []
    spent = {"text": 0.0, "images": 0.0, "render": 0.0}

    for idx in range(first, last + 1):
        page = reader.pages[idx - 1]
        rotation = getattr(page, "rotation", 0) or 0
        phase = time.monotonic()
        page_text = (page.extract_text() or "").strip()
        text_layer = assess_text_layer(page_text)
        spent["text"] += time.monotonic() - phase
        phase = time.monotonic()
        if text_layer == TEXT_VISUAL_PERSIAN:
            # Fallback text if OCR is off/fails; the OCR step replaces it with a far better reading.
            page_text = fix_visual_persian(page_text)
        extracted_images: list[ExtractedImage] = []

        # A page with no text whose content is a page-sized image is a scan. Whole-page OCR (render + one vision call, done
        # by the OCR step like any `needs_ocr` page) reads it correctly; the embedded images must NOT be sent one by one:
        # scanners/"MRC" compressors split a page into background + foreground layers (+ mask) that are unreadable or
        # misread alone (measured: one layer came back as a different project's text), and decoding them is the slowest
        # part of parsing (~1.2s/page) and doubles the vision calls.
        scan_whole_page = (
            not page_text
            and scan_by_page_ocr
            and _has_page_sized_image(page)
        )
        if scan_whole_page:
            text_layer = TEXT_SCAN
        # A page flagged needs_ocr is re-read whole by the OCR step, which never looks at its embedded images (they are
        # discarded when the replacement succeeds), so decoding them here is wasted CPU.
        skip_images = scan_by_page_ocr and text_layer != TEXT_OK

        try:
            for img in ([] if skip_images else page.images):
                img_bytes = img.data
                try:
                    with Image.open(io.BytesIO(img_bytes)) as pil_img:
                        pil_img = ImageOps.exif_transpose(pil_img)
                        if rotation in (90, 180, 270):
                            pil_img = pil_img.rotate(-rotation, expand=True)
                            buf = io.BytesIO()
                            pil_img.save(buf, format="PNG")
                            img_bytes = buf.getvalue()

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

        spent["images"] += time.monotonic() - phase

        # Scanned PDF fallback: if page has no extracted text AND no embedded images extracted by pypdf
        if not page_text and not extracted_images and not scan_whole_page:  # (a scan page is rendered by the OCR step)
            phase = time.monotonic()
            rendered = _try_render_pdf_page_with_pdftoppm(file_path, idx)
            spent["render"] += time.monotonic() - phase
            if rendered:
                extracted_images.append(rendered)

        pages.append(
            DocumentPage(
                page_number=idx,
                text=page_text,
                images=extracted_images,
                metadata={"page": idx} if text_layer == TEXT_OK else {"page": idx, "text_layer": text_layer},
                needs_ocr=text_layer != TEXT_OK,
            )
        )

    return pages, spent


def render_pdf_page(file_path: str, page_number: int) -> ExtractedImage | None:
    """Public wrapper: render one PDF page to a PNG image (None if `pdftoppm` is unavailable or fails)."""
    return _try_render_pdf_page_with_pdftoppm(file_path, page_number)


def _docx_cell_text(cell) -> str:
    return " ".join(p.text.strip() for p in cell.paragraphs if p.text.strip())


def _docx_table_text(table) -> str:
    rows = []
    for row in table.rows:
        cells, seen = [], set()
        for cell in row.cells:
            if id(cell._tc) in seen:  # a merged cell is returned once per grid column it spans
                continue
            seen.add(id(cell._tc))
            cells.append(_docx_cell_text(cell))
        if any(cells):
            rows.append(" | ".join(cells))
    return "\n".join(rows)


def _parse_docx_pages(file_path: str) -> list[DocumentPage]:
    import docx
    from docx.table import Table
    from docx.text.paragraph import Paragraph

    document = docx.Document(file_path)
    # Body order (paragraphs and tables interleaved) with headings kept as markdown, so a table stays next to the
    # sentence that introduces it instead of being appended at the end.
    paragraphs: list[str] = []
    for child in document.element.body.iterchildren():
        if child.tag.endswith("}p"):
            paragraph = Paragraph(child, document)
            text = paragraph.text.strip()
            if not text:
                continue
            style = (paragraph.style.name if paragraph.style is not None else "") or ""
            if style.lower().startswith("heading ") and style[8:].strip().isdigit():
                text = f"{'#' * min(int(style[8:]), 6)} {text}"
            paragraphs.append(text)
        elif child.tag.endswith("}tbl"):
            table_text = _docx_table_text(Table(child, document))
            if table_text:
                paragraphs.append(table_text)

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


def _table_pages(tables, first_page: int = 1) -> list[DocumentPage]:
    """Pages of `XLSX_ROWS_PER_PAGE` rows per sheet, each row written as `column: value` (see spreadsheet.record_pages)."""
    from app.features.documents import spreadsheet

    pages: list[DocumentPage] = []
    for table in tables:
        for text, file_rows in spreadsheet.record_pages(table, XLSX_ROWS_PER_PAGE):
            number = first_page + len(pages)
            pages.append(
                DocumentPage(
                    page_number=number,
                    text=text,
                    metadata={"page": number, "sheet_name": table.name, "rows": file_rows},
                )
            )
    return pages


def _parse_xlsx_pages(file_path: str) -> list[DocumentPage]:
    """One or more pages per non-empty sheet; columns are named from the header row so values keep their meaning."""
    from app.features.documents import spreadsheet

    pages = _table_pages(spreadsheet.read_xlsx_tables(file_path))
    return pages or [DocumentPage(page_number=1, text="", metadata={"page": 1})]


def _parse_csv_pages(file_path: str) -> list[DocumentPage]:
    from app.features.documents import spreadsheet

    pages = _table_pages(spreadsheet.read_csv_tables(file_path))
    return pages or [DocumentPage(page_number=1, text="", metadata={"page": 1})]
