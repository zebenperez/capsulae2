from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.utils import timezone

from .models import BudgetLine, Invoice, InvoiceAllocation, PaymentObligation, PaymentObligationAllocation, Project


class PaymentAllocationTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="payment-allocation-test", is_superuser=True)
        self.client.force_login(self.user)
        self.projects = [Project.objects.create(name="Allocation test " + str(i), manager=self.user) for i in range(2)]
        self.lines = [BudgetLine.objects.create(project=p, code="1", name="Test", approved_budget=Decimal("100")) for p in self.projects]
        self.obligation = PaymentObligation.objects.create(concept="Test", creditor="Test", amount=Decimal("100"), expected_payment_date=timezone.localdate())

    def allocate(self, amount, index=0):
        return PaymentObligationAllocation.objects.create(payment_obligation=self.obligation, project=self.projects[index], budget_line=self.lines[index], allocated_amount=Decimal(amount))

    def test_invoice_filters(self):
        from .views import get_invoice_context
        from .forms import InvoiceFilterForm
        from .models import Supplier
        invoice = Invoice.objects.create(number="FILTER-UNIQUE", provider_tax_id="B-FILTER", issue_date=timezone.localdate(), taxable_base=Decimal("123"))
        Supplier.objects.create(name="Filter Supplier Unique", nif="B-FILTER")
        for query in (invoice.number, invoice.locator, invoice.invoice_code, "B-FILTER", "Filter Supplier Unique"):
            results = get_invoice_context(self.user, {"invoice_q": query})["invoices"]
            self.assertIn(invoice.pk, [item.pk for item in results])
        self.assertNotIn(invoice.pk, [item.pk for item in get_invoice_context(self.user, {"invoice_q": invoice.number, "invoice_min": "124"})["invoices"]])
        self.assertFalse(InvoiceFilterForm({"invoice_min": "-1"}).is_valid())
        self.assertFalse(InvoiceFilterForm({"invoice_from": "2026-09-30", "invoice_to": "2026-09-01"}).is_valid())
        form = InvoiceFilterForm()
        self.assertTrue(form.is_valid())
        self.assertEqual(form.cleaned_data["invoice_from"].day, 1)
        self.assertEqual(form.cleaned_data["invoice_to"].month, timezone.localdate().month)

    def test_invoice_default_range_six_months_back(self):
        from datetime import date
        from unittest.mock import patch
        from .forms import InvoiceFilterForm
        for today, expected in ((date(2026, 9, 16), date(2026, 3, 1)), (date(2026, 1, 31), date(2025, 7, 1))):
            with patch("projects.forms.timezone.localdate", return_value=today):
                form = InvoiceFilterForm()
                self.assertTrue(form.is_valid())
                self.assertEqual(form.cleaned_data["invoice_from"], expected)
                custom = InvoiceFilterForm({"invoice_from": "2025-02-01"})
                self.assertTrue(custom.is_valid())
                self.assertEqual(custom.cleaned_data["invoice_from"], date(2025, 2, 1))

    def test_manage_allocation_active_project(self):
        project = self.projects[0]
        project.status = "active"
        project.save()
        allocation = self.allocate("40")
        url = "/project/projects/payments/allocation-manage/"
        self.assertEqual(self.client.get(url, {"allocation_id": allocation.pk}).status_code, 200)
        self.assertEqual(self.client.post(url, {"allocation_id": allocation.pk, "allocated_amount": "60", "budget_line": self.lines[0].pk, "notes": "Updated"}).status_code, 200)
        allocation.refresh_from_db()
        self.assertEqual(allocation.allocated_amount, 60)
        self.assertEqual(self.client.post(url, {"allocation_id": allocation.pk, "allocated_amount": "101", "budget_line": self.lines[0].pk}).status_code, 400)
        self.assertEqual(self.client.get(url, {"allocation_id": allocation.pk, "action": "delete"}).status_code, 200)
        self.assertTrue(PaymentObligationAllocation.objects.filter(pk=allocation.pk).exists())
        self.assertEqual(self.client.post(url, {"allocation_id": allocation.pk, "action": "delete"}).status_code, 200)
        self.assertEqual(self.obligation.allocated_amount, 0)

    def test_manage_allocation_rechecks_project_status(self):
        allocation = self.allocate("40")
        url = "/project/projects/payments/allocation-manage/"
        for status in ("draft", "suspended", "completed", "cancelled"):
            Project.objects.filter(pk=self.projects[0].pk).update(status=status)
            for action in ("edit", "delete"):
                self.assertEqual(self.client.get(url, {"allocation_id": allocation.pk, "action": action}).status_code, 400)
                self.assertEqual(self.client.post(url, {"allocation_id": allocation.pk, "action": action, "allocated_amount": "20", "budget_line": self.lines[0].pk}).status_code, 400)
        allocation.refresh_from_db()
        self.assertEqual(allocation.allocated_amount, 40)

    def test_split_updates_project_and_budget_balances(self):
        self.allocate("40")
        self.allocate("60", 1)
        self.assertEqual(self.obligation.unallocated_amount, 0)
        self.assertEqual(self.projects[0].executed_budget, 40)
        self.assertEqual(self.lines[1].available_balance, 40)
        with self.assertRaises(ValidationError):
            self.allocate("1")

    def test_backend_blocks_invalid_project_and_invoice_association(self):
        with self.assertRaises(ValidationError):
            PaymentObligationAllocation.objects.create(payment_obligation=self.obligation, project=self.projects[1], budget_line=self.lines[0], allocated_amount=Decimal("10"))
        self.allocate("40")
        self.obligation.amount = Decimal("30")
        with self.assertRaises(ValidationError):
            self.obligation.save()
        self.obligation.amount = Decimal("100")
        invoice = Invoice.objects.create(number="TEST-ALLOC", provider_tax_id="TEST", issue_date=timezone.localdate(), taxable_base=Decimal("100"))
        self.obligation.invoice = invoice
        with self.assertRaises(ValidationError):
            self.obligation.save()

    def test_shared_budget_rejects_invoice_overallocation(self):
        self.allocate("80")
        invoice = Invoice.objects.create(number="TEST-BUDGET", provider_tax_id="TEST", issue_date=timezone.localdate(), taxable_base=Decimal("100"))
        with self.assertRaises(ValidationError):
            InvoiceAllocation.objects.create(invoice=invoice, project=self.projects[0], budget_line=self.lines[0], allocated_amount=Decimal("30"))

    def test_percentage_endpoint_and_wizard(self):
        response = self.client.get("/project/projects/payments/allocation/", {"obj_id": self.obligation.pk})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "IMPUTAR OBLIGACIÓN")
        response = self.client.post("/project/projects/payments/allocation-save/", {
            "payment_obligation_id": self.obligation.pk, "project": self.projects[0].pk,
            "budget_line": self.lines[0].pk, "allocation_mode": "percentage", "allocated_percentage": "40",
        })
        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.obligation.allocated_amount, 40)

    def test_obligation_cannot_consume_budget_used_by_invoice(self):
        invoice = Invoice.objects.create(number="TEST-SHARED", provider_tax_id="TEST", issue_date=timezone.localdate(), taxable_base=Decimal("100"))
        InvoiceAllocation.objects.create(invoice=invoice, project=self.projects[0], budget_line=self.lines[0], allocated_amount=Decimal("80"))
        with self.assertRaises(ValidationError):
            self.allocate("30")
        self.allocate("20")
        self.assertEqual(self.lines[0].available_balance, 0)

    def test_linked_and_cancelled_obligations_cannot_be_allocated(self):
        self.obligation.status = "cancelled"
        self.obligation.save()
        with self.assertRaises(ValidationError):
            self.allocate("10")
        self.obligation.status = "pending"
        self.obligation.invoice = Invoice.objects.create(number="TEST-LINKED", provider_tax_id="TEST", issue_date=timezone.localdate(), taxable_base=Decimal("100"))
        self.obligation.save()
        with self.assertRaises(ValidationError):
            self.allocate("10")

    def test_payment_tabs_render_separately_and_preserve_filters(self):
        response = self.client.get("/project/projects/payments/", {"tab": "treasury", "q": "Test", "ordering": "amount_desc"})
        self.assertContains(response, 'class="treasury-horizons"')
        self.assertNotContains(response, 'id="payment-filter-form"')
        self.assertContains(response, "q=Test")
        self.assertContains(response, "ordering=amount_desc")
        response = self.client.get("/project/projects/payments/", {"tab": "obligations", "q": "Test"})
        self.assertContains(response, 'id="payment-filter-form"')
        self.assertNotContains(response, 'class="treasury-horizons"')
        self.assertContains(response, "1 obligación de pago")

    def test_forecast_boundaries_exclude_paid_and_cancelled(self):
        from datetime import timedelta
        from .views import get_treasury_forecast_groups
        today = timezone.localdate()
        self.obligation.status = "cancelled"
        self.obligation.save()
        for days in [-1, 0, 7, 8, 30, 31, 60, 61]:
            PaymentObligation.objects.create(concept="Boundary", creditor="Test", amount=Decimal("10"), expected_payment_date=today + timedelta(days=days))
        from .models import CashOutflow
        paid = PaymentObligation.objects.create(concept="Boundary", creditor="Test", amount=Decimal("10"), expected_payment_date=today)
        CashOutflow.objects.create(payment_obligation=paid, amount=Decimal("10"), payment_date=today)
        groups = get_treasury_forecast_groups(today)
        counts = [len([item for item in group["items"] if item.concept == "Boundary"]) for group in groups]
        self.assertEqual(counts, [1, 2, 2, 2, 1])
        self.assertNotIn(self.obligation.pk, [item.pk for group in groups for item in group["items"]])
