"""Versioned, authenticated endpoints for external platforms."""
import hashlib
import json
import re

from django.core.cache import cache
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST

from .external_api_models import ExternalApiCredential, ExternalPatientLookupAudit
from .models import Pacientes


CIP_RE = re.compile(r"^[A-Z0-9-]{1,25}$")
RATE_LIMIT = 60
RATE_WINDOW_SECONDS = 60


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
    try:
        _, prefix, secret = api_key.split("_", 2)
    except ValueError:
        return None
    if not prefix or not secret:
        return None
    credential = ExternalApiCredential.objects.select_related("owner").filter(key_prefix=prefix).first()
    if credential is None or not credential.matches(api_key):
        return None
    return credential


@csrf_exempt
@require_POST
def patient_by_cip(request):
    """Return the minimum patient identity data accessible to this credential."""
    credential = _authenticate(request)
    if credential is None:
        return _json_error("invalid_credentials", 401)
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
