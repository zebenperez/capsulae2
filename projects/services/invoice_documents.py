import os

from django.conf import settings
from django.core.exceptions import ValidationError

from PIL import Image, UnidentifiedImageError


ALLOWED_INVOICE_DOCUMENT_TYPES = {
    ".pdf": "application/pdf",
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
}
ALLOWED_INVOICE_MIME_TYPES = set(ALLOWED_INVOICE_DOCUMENT_TYPES.values())
INVOICE_DOCUMENT_ACCEPT = "application/pdf,image/png,image/jpeg,.pdf,.png,.jpg,.jpeg"
INVOICE_DOCUMENT_HELP_TEXT = "Se aceptan facturas o tickets en PDF, PNG, JPG o JPEG."
DEFAULT_INVOICE_IMPORT_MAX_DOCUMENT_SIZE = 10 * 1024 * 1024


class InvoiceDocumentValidationError(ValidationError):
    pass


def get_invoice_document_max_size():
    configured = (
        getattr(settings, "INVOICE_IMPORT_MAX_DOCUMENT_SIZE", None)
        or os.getenv("INVOICE_IMPORT_MAX_DOCUMENT_SIZE")
        or getattr(settings, "INVOICE_IMPORT_MAX_PDF_SIZE", None)
        or os.getenv("INVOICE_IMPORT_MAX_PDF_SIZE")
        or DEFAULT_INVOICE_IMPORT_MAX_DOCUMENT_SIZE
    )
    try:
        return int(configured)
    except (TypeError, ValueError):
        return DEFAULT_INVOICE_IMPORT_MAX_DOCUMENT_SIZE


def get_invoice_document_extension(uploaded_file):
    filename = getattr(uploaded_file, "name", "") or ""
    return os.path.splitext(filename)[1].lower()


def detect_invoice_document_mime(uploaded_file):
    uploaded_file.seek(0)
    signature = uploaded_file.read(16)
    uploaded_file.seek(0)
    if signature.startswith(b"%PDF-"):
        return "application/pdf"
    if signature.startswith(b"\x89PNG\r\n\x1a\n"):
        return "image/png"
    if signature.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    return None


def _validate_pdf_content(uploaded_file):
    uploaded_file.seek(0)
    content = uploaded_file.read()
    uploaded_file.seek(0)
    if not content.startswith(b"%PDF-") or b"%%EOF" not in content[-2048:]:
        raise InvoiceDocumentValidationError("El archivo no parece ser un PDF válido o está dañado.")


def _validate_image_content(uploaded_file):
    uploaded_file.seek(0)
    try:
        image = Image.open(uploaded_file)
        image.verify()
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvoiceDocumentValidationError("La imagen no se puede leer o está dañada.") from exc
    finally:
        uploaded_file.seek(0)


def validate_invoice_document(uploaded_file):
    if not uploaded_file:
        raise InvoiceDocumentValidationError("Debes seleccionar una factura o ticket.")
    if getattr(uploaded_file, "size", 0) <= 0:
        raise InvoiceDocumentValidationError("El archivo está vacío.")

    max_size = get_invoice_document_max_size()
    if uploaded_file.size > max_size:
        max_mb = max_size / (1024 * 1024)
        raise InvoiceDocumentValidationError("El archivo supera el tamaño máximo permitido ({:.0f} MB).".format(max_mb))

    extension = get_invoice_document_extension(uploaded_file)
    expected_mime = ALLOWED_INVOICE_DOCUMENT_TYPES.get(extension)
    if expected_mime is None:
        raise InvoiceDocumentValidationError("El archivo debe tener extensión PDF, PNG, JPG o JPEG.")

    browser_mime = getattr(uploaded_file, "content_type", None)
    if browser_mime and browser_mime not in ALLOWED_INVOICE_MIME_TYPES:
        raise InvoiceDocumentValidationError("El tipo MIME del archivo no está permitido.")

    detected_mime = detect_invoice_document_mime(uploaded_file)
    if detected_mime is None:
        raise InvoiceDocumentValidationError("El contenido del archivo no corresponde a un PDF, PNG o JPEG válido.")
    if detected_mime != expected_mime:
        raise InvoiceDocumentValidationError("La extensión del archivo no coincide con su contenido real.")

    if detected_mime == "application/pdf":
        _validate_pdf_content(uploaded_file)
    else:
        _validate_image_content(uploaded_file)

    uploaded_file.invoice_document_mime = detected_mime
    return uploaded_file
