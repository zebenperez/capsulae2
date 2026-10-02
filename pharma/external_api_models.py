"""Models used exclusively by the public integration API."""
import secrets

from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth.models import User
from django.db import models


class ExternalApiCredential(models.Model):
    """A revocable API key restricted to one patient owner/organisation."""

    name = models.CharField(max_length=100)
    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="external_api_credentials")
    key_prefix = models.CharField(max_length=12, unique=True, db_index=True, editable=False)
    key_hash = models.CharField(max_length=256, editable=False)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        verbose_name = "Credencial API externa"
        verbose_name_plural = "Credenciales API externas"

    @classmethod
    def issue(cls, *, owner, name):
        """Create a credential and return ``(credential, plaintext_key)``.

        The plaintext key is deliberately never persisted and must be delivered
        to the integrator only once.
        """
        prefix = secrets.token_urlsafe(6)
        secret = secrets.token_urlsafe(32)
        plaintext_key = "cap_%s_%s" % (prefix, secret)
        credential = cls.objects.create(
            owner=owner,
            name=name,
            key_prefix=prefix,
            key_hash=make_password(plaintext_key),
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
