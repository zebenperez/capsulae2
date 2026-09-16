import logging
import os
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.utils.dateparse import parse_date
from django.utils.text import get_valid_filename

from projects.models import Invoice, InvoiceStatus, Supplier
from projects.services.invoice_ai import InvoiceExtractionResult


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
    if not safe_name.lower().endswith(".pdf"):
        safe_name = "{}.pdf".format(safe_name)
    return safe_name


def import_invoice(data: InvoiceExtractionResult, pdf_file: UploadedFile):
    validate_required_invoice_data(data)
    amount_validation = validate_invoice_amounts(data)
    if not amount_validation["valid"]:
        logger.warning(
            "Invoice import rejected by amount validation. provider=%s number=%s expected=%s declared=%s difference=%s",
            data.nif_proveedor,
            data.numero_factura,
            amount_validation["expected_total"],
            amount_validation["declared_total"],
            amount_validation["difference"],
        )
        raise InvoiceAmountValidationError(amount_validation)

    duplicate = find_duplicate(data)
    if duplicate is not None:
        raise DuplicateInvoiceError(duplicate)

    issue_date, payment_date = validate_required_invoice_data(data)
    supplier = find_supplier(data.nif_proveedor)
    safe_name = sanitize_uploaded_filename(pdf_file)
    pdf_file.seek(0)
    pdf_file.name = safe_name

    with transaction.atomic():
        invoice = Invoice(
            provider_tax_id=data.nif_proveedor,
            number=data.numero_factura,
            issue_date=issue_date,
            payment_date=payment_date,
            concept=data.concepto,
            taxable_base=data.base,
            iva_amount=data.iva,
            igic_amount=data.igic,
            irpf_amount=data.irpf,
            taxes=data.iva + data.igic - data.irpf,
            total_amount=amount_validation["expected_total"],
            currency="EUR",
            status=InvoiceStatus.DRAFT,
        )
        invoice.physical_document = pdf_file
        try:
            invoice.full_clean()
            invoice.save()
        except ValidationError as exc:
            logger.exception("Imported invoice failed Django validation")
            raise InvoiceImportError("Los datos extraídos no han pasado la validación de la factura.") from exc

    return InvoiceImportResult(invoice=invoice, supplier=supplier, validation=amount_validation)
