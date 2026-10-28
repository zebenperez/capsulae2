"""Versioned, authenticated endpoints for external platforms."""
import hashlib
import json
import re

from django.core.cache import cache
from django.db.models import IntegerField, OuterRef, Q, Subquery, Sum, Value
from django.db.models.functions import Coalesce
from django.http import JsonResponse
from django.utils import timezone
from django.utils.text import slugify
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_POST

from .external_api_models import (
    ExternalApiCredential,
    ExternalPatientLookupAudit,
)
from .models import Pacientes
from account.models import Company
from store.models import Price, Product, StoreInflow, StoreOutflow


CIP_RE = re.compile(r"^[A-Z0-9-]{1,25}$")
RATE_LIMIT = 60
RATE_WINDOW_SECONDS = 60
CATALOG_PAGE_SIZES = (24, 48)


def _client_ip(request):
    # The reverse proxy must be configured to overwrite, not append, this header.
    return request.META.get("REMOTE_ADDR")


def _json_error(code, status):
    return JsonResponse({"code": code}, status=status)


def _rate_limited(request, key_prefix):
    bucket = int(timezone.now().timestamp() // RATE_WINDOW_SECONDS)
    cache_key = "external-patient-lookup:%s:%s:%s" % (_client_ip(request), key_prefix, bucket)
    if cache.add(cache_key, 1, timeout=RATE_WINDOW_SECONDS):
        return False
    try:
        count = cache.incr(cache_key)
    except ValueError:
        return True
    return count > RATE_LIMIT


def _authenticate(request):
    authorization = request.headers.get("Authorization", "")
    scheme, _, api_key = authorization.partition(" ")
    if scheme.lower() != "bearer" or not api_key.startswith("cap_"):
        return None
    # ``token_urlsafe`` can generate underscores in both the prefix and the
    # secret.  Do not parse it with ``split('_')``: match against the stored
    # complete prefix instead.
    for credential in ExternalApiCredential.objects.select_related("owner").filter(active=True):
        if api_key.startswith("cap_%s_" % credential.key_prefix) and credential.matches(api_key):
            return credential
    return None


@csrf_exempt
@require_POST
def patient_by_cip(request):
    """Return the minimum patient identity data accessible to this credential."""
    credential = _authenticate(request)
    if credential is None:
        return _json_error("invalid_credentials", 401)
    if credential.purpose != ExternalApiCredential.PURPOSE_PATIENT_LOOKUP:
        return _json_error("credential_not_allowed", 403)
    if _rate_limited(request, credential.key_prefix):
        return _json_error("rate_limit_exceeded", 429)

    try:
        payload = json.loads(request.body.decode("utf-8"))
        cip = payload["cip"]
    except (UnicodeDecodeError, json.JSONDecodeError, KeyError, TypeError):
        return _json_error("invalid_request", 400)
    if not isinstance(cip, str):
        return _json_error("invalid_cip", 400)

    normalized_cip = cip.strip().upper()
    if not CIP_RE.fullmatch(normalized_cip):
        return _json_error("invalid_cip", 400)

    patient = Pacientes.objects.filter(
        cip__iexact=normalized_cip,
        id_user=credential.owner,
        borrado=False,
    ).only("id", "cip", "n_historial", "nombre", "apellido", "fecha_nacimiento").first()

    ExternalPatientLookupAudit.objects.create(
        credential=credential,
        cip_hash=hashlib.sha256(normalized_cip.encode("utf-8")).hexdigest(),
        found=patient is not None,
        ip_address=_client_ip(request),
    )
    ExternalApiCredential.objects.filter(pk=credential.pk).update(last_used_at=timezone.now())

    if patient is None:
        return _json_error("patient_not_found", 404)

    return JsonResponse({
        "cip": normalized_cip,
        "patient": {
            "patient_id": patient.pk,
            "external_id": patient.n_historial,
            "name": patient.nombre or "",
            "surname": patient.apellido or "",
            "birth_date": patient.fecha_nacimiento.isoformat() if patient.fecha_nacimiento else None,
        },
    })


def _catalog_company(request):
    requested = (request.GET.get("company") or "").strip().lower()
    if not requested:
        return None, _json_error("invalid_company", 400)
    company = Company.objects.filter(code__iexact=requested).first()
    if company is None:
        # Do not disclose which store companies exist to external callers.
        return None, _json_error("company_not_allowed", 403)
    return company, None


@require_GET
def store_products(request):
    """Return the published catalogue of the configured external store only."""
    credential = _authenticate(request)
    if credential is None:
        return _json_error("invalid_credentials", 401)
    if credential.purpose != ExternalApiCredential.PURPOSE_STORE_CATALOG:
        return _json_error("credential_not_allowed", 403)
    if _rate_limited(request, "store-products:" + credential.key_prefix):
        return _json_error("rate_limit_exceeded", 429)

    company, error = _catalog_company(request)
    if error:
        return error
    if credential.catalog_company_code.lower() != company.code.lower():
        return _json_error("company_not_allowed", 403)

    product_type = (request.GET.get("tipo") or "").strip()
    if not product_type:
        return _json_error("invalid_tipo", 400)
    try:
        page = int(request.GET.get("page", ""))
        per_page = int(request.GET.get("per_page", ""))
    except (TypeError, ValueError):
        return _json_error("invalid_pagination", 400)
    if page < 1 or per_page not in CATALOG_PAGE_SIZES:
        return _json_error("invalid_pagination", 400)

    now = timezone.now()
    latest_price = Price.objects.filter(product=OuterRef("pk"), sale=True).order_by("-date", "-pk")
    inflow_total = StoreInflow.objects.filter(product=OuterRef("pk")).values("product").annotate(
        total=Sum("quantity")
    ).values("total")
    outflow_total = StoreOutflow.objects.filter(product=OuterRef("pk")).values("product").annotate(
        total=Sum("quantity")
    ).values("total")
    products = Product.objects.filter(
        company=company,
        product_type__ext_code__iexact=product_type,
        remote_store=True,
        online=True,
        deprecated=False,
        alta_date__lte=now,
        baja_date__gt=now,
    ).annotate(
        catalog_price=Subquery(latest_price.values("amount")[:1]),
        catalog_inflow=Coalesce(Subquery(inflow_total, output_field=IntegerField()), Value(0)),
        catalog_outflow=Coalesce(Subquery(outflow_total, output_field=IntegerField()), Value(0)),
    ).order_by("name", "pk")

    total = products.count()
    offset = (page - 1) * per_page
    rows = products[offset:offset + per_page]
    results = []
    for row in rows:
        slug = slugify(row.name) or row.code
        results.append({
            "id": row.code,
            "slug": slug,
            "name": row.name,
            "description": row.extra2 or "",
            "price": str(row.catalog_price if row.catalog_price is not None else 0),
            "currency": "EUR",
            "image_url": request.build_absolute_uri(row.picture.url) if row.picture else "",
            "in_stock": (row.catalog_inflow - row.catalog_outflow) > 0,
            "url": request.build_absolute_uri("/store/products/%s/" % slug),
        })
    ExternalApiCredential.objects.filter(pk=credential.pk).update(last_used_at=timezone.now())
    return JsonResponse({"results": results, "page": page, "per_page": per_page, "total": total})


@require_GET
def publications(request):
    """Return public editorial content for the requested external site."""
    credential = _authenticate(request)
    if credential is None:
        return _json_error("invalid_credentials", 401)
    if _rate_limited(request, "publications:" + credential.key_prefix):
        return _json_error("rate_limit_exceeded", 429)

    site = (request.GET.get("site") or "").strip().lower()
    try:
        limit = min(12, max(1, int(request.GET.get("limit", 6))))
    except ValueError:
        return _json_error("invalid_limit", 400)
    if not site:
        return _json_error("invalid_site", 400)

    # ``tipo`` and ``categoria`` are aliases.  Accepting either the database
    # id or the displayed name makes the endpoint practical for consumers
    # which do not keep our internal ProductType identifiers.
    product_type = (
        request.GET.get("tipo")
        or request.GET.get("categoria")
        or request.GET.get("categoría")
        or ""
    ).strip()

    # ``site`` identifies the consumer of this versioned endpoint.  The
    # catalogue currently has one remote-store flag rather than per-site tags.
    products = Product.objects.filter(remote_store=True)
    if product_type:
        product_type_filter = Q(product_type__name__iexact=product_type)
        if product_type.isdigit():
            product_type_filter |= Q(product_type_id=int(product_type))
        products = products.filter(product_type_filter)

    rows = products.order_by("-alta_date")[:limit]
    return JsonResponse({"results": [{
        "title": row.name,
        "slug": row.code,
        "excerpt": row.extra1 or "",
        "content": row.extra2 or "",
        "image_url": request.build_absolute_uri(row.picture.url) if row.picture else "",
        "published_at": row.alta_date.isoformat() if row.alta_date else None,
        "url": "",
    } for row in rows]})
