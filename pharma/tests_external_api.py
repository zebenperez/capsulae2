from datetime import date, datetime, timedelta, timezone as dt_timezone
import json

from django.contrib.auth.models import User
from django.contrib.auth.hashers import make_password
from django.test import TestCase
from django.urls import reverse

from .external_api_models import ExternalApiCredential, ExternalPatientLookupAudit
from .models import Pacientes
from account.models import Company
from store.models import Price, Product, ProductType, StoreInflow, StoreOutflow


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

    def test_accepts_a_key_with_an_underscore_in_its_generated_prefix(self):
        key = "cap_ab_cd123_secret"
        credential = ExternalApiCredential.objects.create(
            owner=self.owner,
            name="Clave con separador",
            key_prefix="ab_cd123",
            key_hash=make_password(key),
        )

        response = self.request(key=key)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ExternalPatientLookupAudit.objects.get().credential, credential)


class ExternalPublicationsTests(TestCase):
    def setUp(self):
        owner = User.objects.create_user(username="mulema")
        self.credential, self.key = ExternalApiCredential.issue(
            owner=owner,
            name="Mulema WordPress publications",
        )
        self.base_time = datetime(2026, 10, 6, 10, 0, tzinfo=dt_timezone.utc)

    def product(self, *, code, remote_store=True, offset=0, product_type=None):
        return Product.objects.create(
            code=code,
            name=code.title(),
            extra1="Autor",
            extra2="Descripción",
            alta_date=self.base_time + timedelta(minutes=offset),
            remote_store=remote_store,
            product_type=product_type,
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

    def test_filters_publications_by_product_type_using_tipo_or_categoria(self):
        news = ProductType.objects.create(name="Noticias")
        events = ProductType.objects.create(name="Eventos")
        news_post = self.product(code="news-post", product_type=news, offset=2)
        self.product(code="event-post", product_type=events, offset=1)
        self.product(code="untyped-post", offset=3)

        by_name = self.request(site="mulema", tipo="noticias")
        by_id = self.request(site="mulema", categoria=str(events.pk))

        self.assertEqual([row["slug"] for row in by_name.json()["results"]], [news_post.code])
        self.assertEqual([row["slug"] for row in by_id.json()["results"]], ["event-post"])


class ExternalStoreProductsTests(TestCase):
    def setUp(self):
        self.owner = User.objects.create_user(username="mulema-catalog")
        self.company = Company.objects.create(code="mulema", name="Mulema")
        self.other_company = Company.objects.create(code="other", name="Otra tienda")
        self.product_type = ProductType.objects.create(
            company=self.company,
            name="Productos pelo afro",
            ext_code="productos-pelo-afro",
            online=True,
        )
        self.credential, self.key = ExternalApiCredential.issue(
            owner=self.owner,
            name="Mulema catálogo solo lectura",
            purpose=ExternalApiCredential.PURPOSE_STORE_CATALOG,
            catalog_company=self.company,
        )

    def product(self, code="sku-123", **fields):
        values = {
            "code": code,
            "name": "Champú nutritivo",
            "extra2": "Descripción breve",
            "company": self.company,
            "product_type": self.product_type,
            "online": True,
            "remote_store": True,
        }
        values.update(fields)
        product = Product.objects.create(**values)
        Price.objects.create(product=product, sale=True, amount="12.50")
        return product

    def request(self, key=None, **params):
        query = {"company": "mulema", "tipo": "productos-pelo-afro", "page": 1, "per_page": 24}
        query.update(params)
        return self.client.get(
            reverse("external-store-products"),
            query,
            HTTP_AUTHORIZATION="Bearer %s" % (self.key if key is None else key),
        )

    def test_returns_only_published_products_of_authorized_company_and_type(self):
        product = self.product()
        StoreInflow.objects.create(product=product, quantity=3)
        self.product(code="hidden", remote_store=False)
        self.product(code="offline", online=False)
        self.product(code="deprecated", deprecated=True)
        other_type = ProductType.objects.create(company=self.company, ext_code="otra-categoria")
        self.product(code="wrong-type", product_type=other_type)
        self.product(code="other-company", company=self.other_company)

        response = self.request()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "results": [{
                "id": "sku-123",
                "slug": "champu-nutritivo",
                "name": "Champú nutritivo",
                "description": "Descripción breve",
                "price": "12.50",
                "currency": "EUR",
                "image_url": "",
                "in_stock": True,
                "url": "http://testserver/store/products/champu-nutritivo/",
            }],
            "page": 1,
            "per_page": 24,
            "total": 1,
        })

    def test_stock_and_pagination_are_applied(self):
        first = self.product(code="first", name="A producto")
        second = self.product(code="second", name="B producto")
        StoreInflow.objects.create(product=first, quantity=1)
        StoreOutflow.objects.create(product=first, quantity=1)
        for index in range(23):
            self.product(code="more-%s" % index, name="C producto %s" % index)

        first_page = self.request()
        second_page = self.request(page=2)

        self.assertEqual(first_page.json()["total"], 25)
        self.assertFalse(first_page.json()["results"][0]["in_stock"])
        self.assertEqual(len(first_page.json()["results"]), 24)
        self.assertEqual([row["id"] for row in second_page.json()["results"]], ["more-9"])

    def test_rejects_invalid_credentials_scope_company_and_parameters(self):
        self.assertEqual(self.client.get(reverse("external-store-products")).status_code, 401)
        self.assertEqual(self.request(page=0).json(), {"code": "invalid_pagination"})
        self.assertEqual(self.request(per_page=25).json(), {"code": "invalid_pagination"})
        self.assertEqual(self.request(tipo="").json(), {"code": "invalid_tipo"})
        self.assertEqual(self.request(company="other").status_code, 403)

        patient_credential, patient_key = ExternalApiCredential.issue(owner=self.owner, name="Paciente")
        self.assertEqual(self.request(key=patient_key).status_code, 403)

        other_credential, other_key = ExternalApiCredential.issue(
            owner=self.owner,
            name="Otra empresa",
            purpose=ExternalApiCredential.PURPOSE_STORE_CATALOG,
            catalog_company=self.other_company,
        )
        self.assertEqual(self.request(key=other_key).status_code, 403)

        other_type = ProductType.objects.create(
            company=self.other_company,
            ext_code="productos-pelo-afro",
        )
        self.product(company=self.other_company, product_type=other_type, code="other-sku")
        response = self.request(key=other_key, company="other")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["results"][0]["id"], "other-sku")
