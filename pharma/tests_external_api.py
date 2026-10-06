from datetime import date, datetime, timedelta, timezone as dt_timezone
import json

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from .external_api_models import ExternalApiCredential, ExternalPatientLookupAudit
from .models import Pacientes
from store.models import Product


class ExternalPatientByCipTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="owner")
        self.other_owner = User.objects.create_user(username="other-owner")
        self.patient = Pacientes.objects.create(
            n_orden="1",
            n_historial="HIST0001",
            cip="CIP-123",
            nombre="Ana",
            apellido="García",
            fecha_nacimiento=date(1980, 5, 14),
            sexo="F",
            id_user=self.owner,
        )
        self.credential, self.key = ExternalApiCredential.issue(owner=self.owner, name="Plataforma de prueba")

    def request(self, cip="CIP-123", key=None):
        return self.client.post(
            reverse("external-patient-by-cip"),
            data=json.dumps({"cip": cip}),
            content_type="application/json",
            HTTP_AUTHORIZATION="Bearer %s" % (self.key if key is None else key),
            REMOTE_ADDR="192.0.2.1",
        )

    def test_returns_minimum_patient_data_for_credential_owner(self):
        response = self.request()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "cip": "CIP-123",
            "patient": {
                "patient_id": self.patient.pk,
                "external_id": "HIST0001",
                "name": "Ana",
                "surname": "García",
                "birth_date": "1980-05-14",
            },
        })
        audit = ExternalPatientLookupAudit.objects.get()
        self.assertTrue(audit.found)
        self.assertEqual(audit.credential, self.credential)
        self.assertEqual(audit.ip_address, "192.0.2.1")
        self.credential.refresh_from_db()
        self.assertIsNotNone(self.credential.last_used_at)

    def test_does_not_disclose_a_patient_from_another_owner(self):
        Pacientes.objects.filter(pk=self.patient.pk).update(id_user=self.other_owner)

        response = self.request()

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json(), {"code": "patient_not_found"})
        self.assertFalse(ExternalPatientLookupAudit.objects.get().found)

    def test_cip_matching_is_case_insensitive(self):
        self.patient.cip = "cip-123"
        self.patient.save(update_fields=["cip"])

        response = self.request()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["cip"], "CIP-123")

    def test_rejects_missing_or_invalid_credentials(self):
        response = self.client.post(reverse("external-patient-by-cip"), data="{}", content_type="application/json")
        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json(), {"code": "invalid_credentials"})

        response = self.request(key="cap_invalid_key")
        self.assertEqual(response.status_code, 401)

    def test_rejects_inactive_credential_and_invalid_cip(self):
        self.credential.active = False
        self.credential.save(update_fields=["active"])
        self.assertEqual(self.request().status_code, 401)

        self.credential.active = True
        self.credential.save(update_fields=["active"])
        response = self.request(cip="not valid")
        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json(), {"code": "invalid_cip"})


class ExternalPublicationsTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="mulema")
        self.credential, self.key = ExternalApiCredential.issue(
            owner=owner,
            name="Mulema WordPress publications",
        )
        self.base_time = datetime(2026, 10, 6, 10, 0, tzinfo=dt_timezone.utc)

    def product(self, *, code, remote_store=True, offset=0):
        return Product.objects.create(
            code=code,
            name=code.title(),
            extra1="Autor",
            extra2="Descripción",
            alta_date=self.base_time + timedelta(minutes=offset),
            remote_store=remote_store,
        )

    def request(self, **params):
        return self.client.get(
            reverse("external-publications"),
            params,
            HTTP_AUTHORIZATION="Bearer %s" % self.key,
            REMOTE_ADDR="192.0.2.1",
        )

    def test_returns_only_products_marked_for_the_remote_store_in_descending_order(self):
        older = self.product(code="older", offset=-1)
        newer = self.product(code="newer", offset=1)
        self.product(code="private", remote_store=False, offset=2)

        response = self.request(site="MULEMA", limit="6")

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"results": [
            {
                "title": newer.name,
                "slug": "newer",
                "excerpt": "Autor",
                "content": "Descripción",
                "image_url": "",
                "published_at": newer.alta_date.isoformat(),
                "url": "",
            },
            {
                "title": older.name,
                "slug": "older",
                "excerpt": "Autor",
                "content": "Descripción",
                "image_url": "",
                "published_at": older.alta_date.isoformat(),
                "url": "",
            },
        ]})

    def test_validates_credentials_site_and_limit_and_caps_limit_at_twelve(self):
        for index in range(13):
            self.product(code="post-%s" % index, offset=index)

        self.assertEqual(self.client.get(reverse("external-publications")).status_code, 401)
        self.assertEqual(self.request().json(), {"code": "invalid_site"})
        self.assertEqual(self.request(site="mulema", limit="bad").json(), {"code": "invalid_limit"})
        self.assertEqual(len(self.request(site="mulema", limit="999").json()["results"]), 12)
        self.assertEqual(len(self.request(site="mulema", limit="0").json()["results"]), 1)
