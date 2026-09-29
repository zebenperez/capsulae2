from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from account.models import Company
from .models import Client, Price, Product, Provider
from .views import get_clients_context, get_products_context, get_providers_context


class ProviderSearchTests(TestCase):
    def setUp(self):
        self.matching_provider = Provider.objects.create(
            code="PROV-001",
            name="Distribuciones Acme",
            phone="600123456",
            email="ventas@acme.test",
        )
        Provider.objects.create(
            code="PROV-002",
            name="Otro proveedor",
            phone="600654321",
            email="contacto@otro.test",
        )

    def test_provider_search_matches_all_visible_provider_fields(self):
        for search_value in ("prov-001", "acme", "123456", "ventas@"):
            with self.subTest(search_value=search_value):
                items = get_providers_context(search_value)["items"]
                self.assertEqual(list(items), [self.matching_provider])


class ClientSearchTests(TestCase):
    def setUp(self):
        self.matching_client = Client.objects.create(
            code="CLI-001",
            name="Cliente Acme",
            dni="12345678A",
            phone="600123456",
            email="cliente@acme.test",
            address="Calle Principal 1",
        )
        Client.objects.create(code="CLI-002", name="Otro cliente")

    def test_client_search_matches_all_visible_client_fields(self):
        for search_value in ("cli-001", "acme", "12345678", "123456", "cliente@", "principal"):
            with self.subTest(search_value=search_value):
                items = get_clients_context(None, search_value)["items"]
                self.assertEqual(list(items), [self.matching_client])


class ProductSearchTests(TestCase):
    def setUp(self):
        self.matching_product = Product.objects.create(
            code="PROD-001",
            name="Producto Acme",
        )
        Product.objects.create(code="PROD-002", name="Otro producto")

    def test_product_search_matches_code_and_name(self):
        for search_value in ("prod-001", "acme"):
            with self.subTest(search_value=search_value):
                items = get_products_context(None, search_value)["items"]
                self.assertEqual(list(items), [self.matching_product])

    def test_product_search_is_limited_to_the_active_company(self):
        company = Company.objects.create(code="COMP-ONE", name="Empresa uno")
        other_company = Company.objects.create(code="COMP-TWO", name="Empresa dos")
        visible_product = Product.objects.create(code="2233", name="Producto visible", company=company)
        Product.objects.create(code="2233", name="Producto ajeno", company=other_company)

        items = get_products_context(company, "2233")["items"]

        self.assertEqual(list(items), [visible_product])

    def test_product_new_url_is_available(self):
        self.assertEqual(reverse("product-new"), "/store/products/new/")

    def test_product_remove_url_is_available(self):
        self.assertEqual(
            reverse("product-remove", kwargs={"obj_id": self.matching_product.id}),
            f"/store/products/remove/{self.matching_product.id}/",
        )


class ProductPriceTests(TestCase):
    def test_last_prices_use_the_most_recent_dates(self):
        product = Product.objects.create(code="PROD-PRICE", name="Producto con precios")
        older_date = timezone.now() - timedelta(days=1)
        Price.objects.create(product=product, sale=True, amount="10.00", date=older_date)
        Price.objects.create(product=product, sale=False, amount="5.00", date=older_date)
        Price.objects.create(
            product=product, sale=True, amount="12.00", date=timezone.now()
        )
        Price.objects.create(
            product=product, sale=False, amount="7.00", date=timezone.now()
        )

        self.assertEqual(product.last_pvp, 12)
        self.assertEqual(product.last_cost, 7)
