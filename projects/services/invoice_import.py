import logging
import os
from dataclasses import dataclass
from datetime import datetime, timedelta
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils import timezone
from django.utils.dateparse import parse_date
from django.utils.text import get_valid_filename

from projects.models import Invoice, InvoiceStatus, PendingInvoiceImport, PendingInvoiceImportStatus, Supplier
from projects.services.invoice_ai import InvoiceExtractionResult
from projects.services.invoice_documents import ALLOWED_INVOICE_DOCUMENT_TYPES
from projects.services.invoice_documents import validate_invoice_document


logger = logging.getLogger(__name__)


class InvoiceImportError(Exception):
    pass


class DuplicateInvoiceError(InvoiceImportError):
    def __init__(self, invoice):
        self.invoice = invoice
        super().__init__("Parece que esta factura ya está registrada.")


class InvoiceAmountValidationError(InvoiceImportError):
    def __init__(self, validation):
        self.validation = validation
        super().__init__(validation["message"])


class PendingInvoiceImportUnavailable(InvoiceImportError):
    pass


@dataclass
class InvoiceImportResult:
    invoice: Invoice
    supplier: Supplier = None
    validation: dict = None


def get_amount_tolerance():
    configured = getattr(settings, "INVOICE_IMPORT_TOTAL_TOLERANCE", None) or os.getenv("INVOICE_IMPORT_TOTAL_TOLERANCE", "0.02")
    try:
        return Decimal(str(configured)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        return Decimal("0.02")


def money(value):
    if value is None:
        return None
    return Decimal(str(value)).quantize(Decimal("0.01"))


def validate_invoice_amounts(data, tolerance=None):
    tolerance = tolerance if tolerance is not None else get_amount_tolerance()
    amounts = {
        "base": data.base,
        "iva": data.iva,
        "igic": data.igic,
        "irpf": data.irpf,
        "total": data.total,
    }
    missing = [name for name, value in amounts.items() if value is None]
    if missing:
        return {
            "valid": False,
            "base": data.base,
            "iva": data.iva,
            "igic": data.igic,
            "irpf": data.irpf,
            "expected_total": None,
            "declared_total": data.total,
            "difference": None,
            "message": "No se han podido extraer todos los importes obligatorios: {}.".format(", ".join(missing)),
        }

    negative = [name for name, value in amounts.items() if value < 0]
    if negative:
        return {
            "valid": False,
            "base": data.base,
            "iva": data.iva,
            "igic": data.igic,
            "irpf": data.irpf,
            "expected_total": None,
            "declared_total": data.total,
            "difference": None,
            "message": "La factura contiene importes negativos no permitidos: {}.".format(", ".join(negative)),
        }

    expected_total = money(data.base + data.iva + data.igic - data.irpf)
    declared_total = money(data.total)
    difference = money(expected_total - declared_total)
    valid = abs(difference) <= tolerance
    return {
        "valid": valid,
        "base": data.base,
        "iva": data.iva,
        "igic": data.igic,
        "irpf": data.irpf,
        "expected_total": expected_total,
        "declared_total": declared_total,
        "difference": difference,
        "message": "Los importes son congruentes." if valid else "No se ha podido importar la factura porque los importes extraídos no son congruentes.",
    }


def parse_invoice_date(value):
    if not value:
        return None
    value = str(value).strip()
    parsed_date = parse_date(value)
    if parsed_date is not None:
        return parsed_date
    for date_format in ("%d-%m-%Y", "%d/%m/%Y", "%d.%m.%Y"):
        try:
            return datetime.strptime(value, date_format).date()
        except ValueError:
            pass
    return None


def validate_required_invoice_data(data):
    missing = []
    if not data.numero_factura:
        missing.append("número de factura")
    if not data.fecha_factura:
        missing.append("fecha de factura")
    if not data.nif_proveedor:
        missing.append("NIF/CIF del proveedor")
    if not data.concepto:
        missing.append("concepto")
    if data.base is None:
        missing.append("base")
    if data.total is None:
        missing.append("total")
    if missing:
        raise InvoiceImportError("No se han podido extraer datos obligatorios: {}.".format(", ".join(missing)))

    issue_date = parse_invoice_date(data.fecha_factura)
    if issue_date is None:
        raise InvoiceImportError("La fecha de factura extraída no tiene un formato válido.")
    payment_date = parse_invoice_date(data.fecha_pago) if data.fecha_pago else None
    if data.fecha_pago and payment_date is None:
        raise InvoiceImportError("La fecha de pago extraída no tiene un formato válido.")
    return issue_date, payment_date


def find_supplier(nif):
    if not nif:
        return None
    return Supplier.objects.filter(nif__iexact=nif).first()


def find_duplicate(data):
    if not data.nif_proveedor or not data.numero_factura:
        return None
    return Invoice.objects.filter(provider_tax_id__iexact=data.nif_proveedor, number=data.numero_factura).first()


def sanitize_uploaded_filename(uploaded_file):
    original_name = getattr(uploaded_file, "name", "") or "factura.pdf"
    basename = os.path.basename(original_name)
    safe_name = get_valid_filename(basename) or "factura.pdf"
    safe_extension = os.path.splitext(safe_name)[1].lower()
    if safe_extension not in ALLOWED_INVOICE_DOCUMENT_TYPES:
        detected_mime = getattr(uploaded_file, "invoice_document_mime", "application/pdf")
        for extension, mime_type in ALLOWED_INVOICE_DOCUMENT_TYPES.items():
            if mime_type == detected_mime:
                safe_name = "{}{}".format(os.path.splitext(safe_name)[0] or "factura", extension)
                break
    return safe_name


def get_pending_import_lifetime():
    configured = getattr(settings, "INVOICE_IMPORT_PENDING_HOURS", None) or os.getenv("INVOICE_IMPORT_PENDING_HOURS", "24")
    try:
        return timedelta(hours=max(1, int(configured)))
    except (TypeError, ValueError):
        return timedelta(hours=24)


def serialize_extracted_data(data):
    return {
        "numero_factura": data.numero_factura,
        "fecha_factura": data.fecha_factura,
        "fecha_pago": data.fecha_pago,
        "nif_proveedor": data.nif_proveedor,
        "nif_proveedor_original": data.nif_proveedor_original,
        "base": str(data.base) if data.base is not None else None,
        "igic": str(data.igic) if data.igic is not None else None,
        "iva": str(data.iva) if data.iva is not None else None,
        "irpf": str(data.irpf) if data.irpf is not None else None,
        "total": str(data.total) if data.total is not None else None,
        "concepto": data.concepto,
    }


def deserialize_extracted_data(payload):
    return InvoiceExtractionResult(
        numero_factura=payload.get("numero_factura"),
        fecha_factura=payload.get("fecha_factura"),
        fecha_pago=payload.get("fecha_pago"),
        nif_proveedor=payload.get("nif_proveedor"),
        nif_proveedor_original=payload.get("nif_proveedor_original"),
        base=money(payload.get("base")),
        igic=money(payload.get("igic")),
        iva=money(payload.get("iva")),
        irpf=money(payload.get("irpf")),
        total=money(payload.get("total")),
        concepto=payload.get("concepto"),
    )


def extracted_data_to_initial(data):
    return {
        "number": data.numero_factura or "",
        "issue_date": parse_invoice_date(data.fecha_factura),
        "payment_date": parse_invoice_date(data.fecha_pago),
        "provider_tax_id": data.nif_proveedor or "",
        "taxable_base": data.base,
        "iva_amount": data.iva,
        "igic_amount": data.igic,
        "irpf_amount": data.irpf,
        "total_amount": data.total,
        "concept": data.concepto or "",
        "currency": "EUR",
        "status": InvoiceStatus.DRAFT,
    }


def create_pending_import(owner, invoice_document):
    safe_name = sanitize_uploaded_filename(invoice_document)
    invoice_document.seek(0)
    invoice_document.name = safe_name
    return PendingInvoiceImport.objects.create(
        owner=owner,
        temporary_document=invoice_document,
        original_name=safe_name,
        detected_mime=getattr(invoice_document, "invoice_document_mime", ""),
        file_size=invoice_document.size,
        expires_at=timezone.now() + get_pending_import_lifetime(),
    )


def mark_pending_import_ready(pending_import, extracted_data):
    pending_import.set_extracted_data(serialize_extracted_data(extracted_data))
    pending_import.status = PendingInvoiceImportStatus.PENDING_REVIEW
    pending_import.error_code = ""
    pending_import.save(update_fields=["extracted_data", "status", "error_code"])


def mark_pending_import_failed(pending_import, error_code="analysis_failed"):
    pending_import.status = PendingInvoiceImportStatus.FAILED
    pending_import.error_code = error_code
    pending_import.save(update_fields=["status", "error_code"])


def begin_pending_reanalysis(owner, token):
    with transaction.atomic():
        pending_import = get_reviewable_pending_import(owner, token, lock=True)
        pending_import.status = PendingInvoiceImportStatus.PROCESSING
        pending_import.error_code = ""
        pending_import.save(update_fields=["status", "error_code"])
        return pending_import


def restore_pending_review_after_error(pending_import, error_code="reanalysis_failed"):
    PendingInvoiceImport.objects.filter(
        pk=pending_import.pk,
        status=PendingInvoiceImportStatus.PROCESSING,
    ).update(status=PendingInvoiceImportStatus.PENDING_REVIEW, error_code=error_code)


def get_reviewable_pending_import(owner, token, lock=False):
    queryset = PendingInvoiceImport.objects
    if lock:
        queryset = queryset.select_for_update()
    try:
        pending_import = queryset.get(token=token, owner=owner)
    except (PendingInvoiceImport.DoesNotExist, ValueError, TypeError):
        raise PendingInvoiceImportUnavailable("La importación pendiente no existe o no está disponible.")
    if pending_import.status != PendingInvoiceImportStatus.PENDING_REVIEW:
        raise PendingInvoiceImportUnavailable("La importación pendiente ya no está disponible.")
    if pending_import.expires_at <= timezone.now():
        raise PendingInvoiceImportUnavailable("La importación pendiente ha caducado.")
    if not pending_import.temporary_document:
        raise PendingInvoiceImportUnavailable("El documento pendiente ya no está disponible.")
    return pending_import


def complete_pending_import(owner, token, invoice_form):
    saved_document_name = None
    try:
        with transaction.atomic():
            pending_import = get_reviewable_pending_import(owner, token, lock=True)
            pending_import.temporary_document.open("rb")
            temporary_document = pending_import.temporary_document
            temporary_document.content_type = pending_import.detected_mime
            temporary_document.invoice_document_mime = pending_import.detected_mime
            validate_invoice_document(temporary_document)

            invoice = invoice_form.save(commit=False)
            invoice.status = InvoiceStatus.DRAFT
            invoice.currency = "EUR"
            invoice.physical_document.save(pending_import.original_name, temporary_document, save=False)
            saved_document_name = invoice.physical_document.name
            invoice.full_clean()
            invoice.save()

            pending_import.invoice = invoice
            pending_import.status = PendingInvoiceImportStatus.COMPLETED
            pending_import.completed_at = timezone.now()
            pending_import.save(update_fields=["invoice", "status", "completed_at"])

            temporary_name = pending_import.temporary_document.name
            temporary_storage = pending_import.temporary_document.storage

            def remove_temporary_document():
                temporary_storage.delete(temporary_name)
                PendingInvoiceImport.objects.filter(pk=pending_import.pk).update(temporary_document="")

            transaction.on_commit(remove_temporary_document)
            return invoice
    except Exception:
        if saved_document_name:
            Invoice._meta.get_field("physical_document").storage.delete(saved_document_name)
        raise
