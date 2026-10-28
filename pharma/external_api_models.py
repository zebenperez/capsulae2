"""Models used exclusively by the public integration API."""
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models


class ExternalApiCredential(models.Model):
    """A revocable, purpose-limited API key for an external integration."""

    PURPOSE_PATIENT_LOOKUP = "patient_lookup"
    PURPOSE_STORE_CATALOG = "store_catalog"
    PURPOSE_CHOICES = (
        (PURPOSE_PATIENT_LOOKUP, "Consulta de pacientes"),
        (PURPOSE_STORE_CATALOG, "Catálogo de tienda (solo lectura)"),
    )

    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="external_api_credentials")
    key_prefix = models.CharField(max_length=12, unique=True, db_index=True, editable=False)
    key_hash = models.CharField(max_length=256, editable=False)
    purpose = models.CharField(max_length=30, choices=PURPOSE_CHOICES, default=PURPOSE_PATIENT_LOOKUP)
    catalog_company_code = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Código de la empresa cuyo catálogo puede consultar esta clave.",
    )
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Credencial API externa"
        verbose_name_plural = "Credenciales API externas"

    @classmethod
    def issue(cls, *, owner, name, purpose=PURPOSE_PATIENT_LOOKUP, catalog_company=None):
        """Create a credential and return ``(credential, plaintext_key)``.

        The plaintext key is deliberately never persisted and must be delivered
        to the integrator only once.
        """
        if purpose == cls.PURPOSE_STORE_CATALOG and catalog_company is None:
            raise ValueError("Las credenciales de catálogo requieren una empresa.")
        catalog_company_code = catalog_company.code if catalog_company else ""

        prefix = secrets.token_urlsafe(6)
        secret = secrets.token_urlsafe(32)
        plaintext_key = "cap_%s_%s" % (prefix, secret)
        credential = cls.objects.create(
            owner=owner,
            name=name,
            key_prefix=prefix,
            key_hash=make_password(plaintext_key),
            purpose=purpose,
            catalog_company_code=catalog_company_code,
        )
        return credential, plaintext_key

    def matches(self, plaintext_key):
        return self.active and check_password(plaintext_key, self.key_hash)

    def __str__(self):
        return "%s (%s)" % (self.name, self.owner)


class ExternalPatientLookupAudit(models.Model):
    credential = models.ForeignKey(ExternalApiCredential, on_delete=models.SET_NULL, null=True, blank=True)
    cip_hash = models.CharField(max_length=64)
    found = models.BooleanField(default=False)
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Auditoría de consulta externa de paciente"
        verbose_name_plural = "Auditorías de consultas externas de pacientes"
        indexes = [models.Index(fields=["credential", "created_at"])]
