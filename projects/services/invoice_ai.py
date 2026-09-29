import base64
import json
import logging
import os
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation

from django.conf import settings

from openai import OpenAI

from projects.services.invoice_documents import detect_invoice_document_mime
from projects.services.supplier_matching import normalize_tax_id


logger = logging.getLogger(__name__)

DEFAULT_INVOICE_MODEL = "gpt-5.6-luna"


class InvoiceExtractionError(Exception):
    pass


@dataclass
class InvoiceExtractionResult:
    numero_factura: str = None
    fecha_factura: str = None
    fecha_pago: str = None
    nif_proveedor: str = None
    nif_proveedor_original: str = None
    base: Decimal = None
    igic: Decimal = None
    iva: Decimal = None
    irpf: Decimal = None
    total: Decimal = None
    concepto: str = None


INVOICE_EXTRACTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "numero_factura": {"type": ["string", "null"]},
        "fecha_factura": {"type": ["string", "null"]},
        "fecha_pago": {"type": ["string", "null"]},
        "nif_proveedor": {"type": ["string", "null"]},
        "base": {"type": ["number", "null"]},
        "igic": {"type": ["number", "null"]},
        "iva": {"type": ["number", "null"]},
        "irpf": {"type": ["number", "null"]},
        "total": {"type": ["number", "null"]},
        "concepto": {"type": ["string", "null"]},
    },
    "required": [
        "numero_factura",
        "fecha_factura",
        "fecha_pago",
        "nif_proveedor",
        "base",
        "igic",
        "iva",
        "irpf",
        "total",
        "concepto",
    ],
}


INVOICE_EXTRACTION_PROMPT = """Eres un sistema de extracción de datos de facturas y tickets.

Analiza exclusivamente el documento proporcionado.

Extrae:
- número de factura o ticket
- fecha de factura
- fecha efectiva de pago, si existe
- NIF/CIF del proveedor/emisor
- base imponible total
- importe total de IGIC
- importe total de IVA
- importe total de IRPF/retención
- total final de la factura o ticket
- concepto/resumen descriptivo

Reglas:
- No inventes datos.
- Si un dato no aparece, devuelve null cuando el schema lo permita.
- IVA, IGIC e IRPF son importes monetarios, no porcentajes.
- Si IVA, IGIC o IRPF no aparecen o no pueden verificarse, devuelve null.
- Si existen varias líneas del mismo impuesto, suma sus importes.
- La fecha de vencimiento no es fecha de pago.
- Para fecha_pago devuelve únicamente una fecha que represente un pago efectuado.
- El NIF solicitado es el del proveedor/emisor, no el del cliente/receptor.
- El concepto debe ser breve pero descriptivo.
- Si el documento es ilegible, está incompleto o no parece una factura/ticket, devuelve null en los campos no verificables.
- Devuelve exclusivamente la estructura definida por el schema.
"""


def get_invoice_model():
    return getattr(settings, "OPENAI_INVOICE_MODEL", None) or os.getenv("OPENAI_INVOICE_MODEL") or DEFAULT_INVOICE_MODEL


def get_invoice_timeout():
    return int(getattr(settings, "OPENAI_INVOICE_TIMEOUT", os.getenv("OPENAI_INVOICE_TIMEOUT", 60)))


def decimal_or_none(value, field_name):
    if value is None:
        return None
    try:
        return Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError, TypeError):
        raise InvoiceExtractionError("El campo {} no contiene un importe válido.".format(field_name))


def decimal_or_zero(value, field_name):
    amount = decimal_or_none(value, field_name)
    return amount if amount is not None else Decimal("0.00")


def normalize_text(value):
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def parse_invoice_extraction_payload(payload):
    required_fields = set(INVOICE_EXTRACTION_SCHEMA["required"])
    if not isinstance(payload, dict):
        raise InvoiceExtractionError("OpenAI no devolvió una estructura válida.")
    missing_fields = required_fields.difference(payload.keys())
    if missing_fields:
        raise InvoiceExtractionError("Faltan campos en la extracción: {}.".format(", ".join(sorted(missing_fields))))

    original_tax_id = normalize_text(payload.get("nif_proveedor"))
    result = InvoiceExtractionResult(
        numero_factura=normalize_text(payload.get("numero_factura")),
        fecha_factura=normalize_text(payload.get("fecha_factura")),
        fecha_pago=normalize_text(payload.get("fecha_pago")),
        nif_proveedor=normalize_tax_id(original_tax_id) or None,
        nif_proveedor_original=original_tax_id,
        base=decimal_or_none(payload.get("base"), "base"),
        igic=decimal_or_none(payload.get("igic"), "igic"),
        iva=decimal_or_none(payload.get("iva"), "iva"),
        irpf=decimal_or_none(payload.get("irpf"), "irpf"),
        total=decimal_or_none(payload.get("total"), "total"),
        concepto=normalize_text(payload.get("concepto")),
    )
    return result


def build_invoice_openai_content(invoice_document, mime_type=None):
    mime_type = mime_type or getattr(invoice_document, "invoice_document_mime", None) or detect_invoice_document_mime(invoice_document)
    if mime_type not in ("application/pdf", "image/png", "image/jpeg"):
        raise InvoiceExtractionError("El documento no tiene un formato admitido para el análisis.")

    invoice_document.seek(0)
    document_base64 = base64.b64encode(invoice_document.read()).decode("ascii")
    invoice_document.seek(0)

    content = [{"type": "input_text", "text": INVOICE_EXTRACTION_PROMPT}]
    if mime_type == "application/pdf":
        content.append({
            "type": "input_file",
            "filename": getattr(invoice_document, "name", "factura.pdf"),
            "file_data": "data:application/pdf;base64,{}".format(document_base64),
        })
    else:
        content.append({
            "type": "input_image",
            "image_url": "data:{};base64,{}".format(mime_type, document_base64),
        })
    return content


def extract_invoice_data(invoice_document):
    api_key = getattr(settings, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise InvoiceExtractionError("OPENAI_API_KEY no está configurada.")

    client = OpenAI(api_key=api_key, timeout=get_invoice_timeout())
    try:
        response = client.responses.create(
            model=get_invoice_model(),
            input=[
                {
                    "role": "user",
                    "content": build_invoice_openai_content(invoice_document),
                }
            ],
            text={
                "format": {
                    "type": "json_schema",
                    "name": "invoice_extraction",
                    "schema": INVOICE_EXTRACTION_SCHEMA,
                    "strict": True,
                }
            },
        )
    except Exception as exc:
        logger.exception("OpenAI invoice extraction failed")
        raise InvoiceExtractionError("No se ha podido analizar la factura. Puedes intentarlo de nuevo o introducirla manualmente.") from exc

    try:
        output_text = response.output_text
    except AttributeError as exc:
        logger.exception("OpenAI invoice extraction response did not include output_text")
        raise InvoiceExtractionError("OpenAI no devolvió una respuesta interpretable.") from exc

    try:
        payload = json.loads(output_text)
    except (TypeError, json.JSONDecodeError) as exc:
        logger.exception("OpenAI invoice extraction returned invalid JSON")
        raise InvoiceExtractionError("OpenAI devolvió una respuesta con formato no válido.") from exc

    return parse_invoice_extraction_payload(payload)
