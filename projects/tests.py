from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase
from django.urls import reverse

from .models import (
    Activity,
    BudgetLine,
    Expense,
    Financier,
    FinancierContribution,
    FinancierType,
    Income,
    Indicator,
    Invoice,
    InvoiceAllocation,
    Objective,
    ObjectiveType,
    Project,
    ProjectFinancier,
    ProgressStatus,
    Text,
)


class ProjectModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="manager", password="test")
        self.project = Project.objects.create(
            code="COOP-001",
            name="Proyecto de cooperación",
            status="active",
            start_date=date(2026, 1, 1),
            finish_date=date(2026, 12, 31),
            country="España",
            manager=self.user,
            technical_manager=self.user,
            financial_manager=self.user,
            approved_budget=Decimal("10000.00"),
        )
        self.objective = Objective.objects.create(
            project=self.project,
            code="OE1",
            name="Objetivo específico 1",
            objective_type=ObjectiveType.SPECIFIC,
            progress_percentage=Decimal("50.00"),
        )
        self.activity = Activity.objects.create(
            project=self.project,
            objective=self.objective,
            code="A1",
            name="Actividad 1",
            status=ProgressStatus.IN_PROGRESS,
        )
        self.budget_line = BudgetLine.objects.create(
            project=self.project,
            code="1",
            name="Personal",
            approved_budget=Decimal("6000.00"),
        )
        self.sub_budget_line = BudgetLine.objects.create(
            project=self.project,
            parent=self.budget_line,
            code="1.1",
            name="Contrataciones",
            approved_budget=Decimal("3000.00"),
        )
        self.financier = Financier.objects.create(
            name="Financiador público",
            financier_type=FinancierType.PUBLIC,
            tax_id="A00000000",
        )
        self.project_financier = ProjectFinancier.objects.create(
            project=self.project,
            financier=self.financier,
            committed_amount=Decimal("5000.00"),
            granted_amount=Decimal("5000.00"),
            disbursed_amount=Decimal("2500.00"),
        )
        self.contribution = FinancierContribution.objects.create(
            project=self.project,
            financier=self.financier,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            amount=Decimal("3000.00"),
            percentage=Decimal("100.00"),
        )
        self.invoice = Invoice.objects.create(
            locator="TST01",
            provider_tax_id="B00000000",
            number="F-001",
            issue_date=date(2026, 2, 1),
            payment_date=date(2026, 2, 15),
            concept="Servicios técnicos",
            taxable_base=Decimal("1000.00"),
            taxes=Decimal("210.00"),
            total_amount=Decimal("1210.00"),
            currency="EUR",
        )

    def test_project_creation_and_summary_values(self):
        self.assertEqual(str(self.project), "Proyecto de cooperación")
        self.assertEqual(self.project.executed_budget, Decimal("0.00"))
        self.assertEqual(self.project.completed_activities_count, 0)

    def test_indicator_compliance_percentage(self):
        indicator = Indicator.objects.create(
            objective=self.objective,
            name="Personas atendidas",
            baseline=Decimal("10.00"),
            target=Decimal("110.00"),
            current_value=Decimal("60.00"),
            unit="personas",
        )
        self.assertEqual(indicator.compliance_percentage, Decimal("50.00"))

    def test_budget_execution_and_balances(self):
        InvoiceAllocation.objects.create(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier=self.financier,
            allocated_amount=Decimal("1000.00"),
        )
        self.assertEqual(self.invoice.allocated_amount, Decimal("1000.00"))
        self.assertEqual(self.invoice.pending_amount, Decimal("210.00"))
        self.assertEqual(self.project.executed_budget, Decimal("1000.00"))
        self.assertEqual(self.budget_line.executed_amount, Decimal("1000.00"))
        self.assertEqual(self.sub_budget_line.available_balance, Decimal("2000.00"))

    def test_invoice_allocations_cannot_exceed_invoice_total(self):
        InvoiceAllocation.objects.create(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier=self.financier,
            allocated_amount=Decimal("1000.00"),
        )
        allocation = InvoiceAllocation(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier=self.financier,
            allocated_amount=Decimal("500.00"),
        )
        with self.assertRaises(ValidationError):
            allocation.full_clean()

    def test_invoice_allocation_can_have_no_activity(self):
        allocation = InvoiceAllocation(
            invoice=self.invoice,
            project=self.project,
            activity=None,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("100.00"),
        )

        allocation.full_clean()

    def test_invoice_code_and_total_are_generated(self):
        invoice = Invoice.objects.create(
            locator="ab12c",
            provider_tax_id="B11111111",
            number="F-100",
            issue_date=date(2026, 5, 2),
            concept="Servicios",
            taxable_base=Decimal("10.50"),
            taxes=Decimal("2.10"),
            total_amount=Decimal("0.00"),
        )

        self.assertEqual(invoice.locator, "AB12C")
        self.assertEqual(invoice.invoice_code, "2026-{}".format(invoice.id))
        self.assertEqual(invoice.total_amount, Decimal("12.60"))

    def test_invoice_locator_is_generated_on_create(self):
        first = Invoice.objects.create(
            provider_tax_id="B12121212",
            number="F-GEN-1",
            issue_date=date(2026, 5, 3),
            concept="Servicios",
            taxable_base=Decimal("10.00"),
            taxes=Decimal("2.00"),
            total_amount=Decimal("0.00"),
        )
        second = Invoice.objects.create(
            provider_tax_id="B12121212",
            number="F-GEN-2",
            issue_date=date(2026, 5, 4),
            concept="Servicios",
            taxable_base=Decimal("20.00"),
            taxes=Decimal("4.00"),
            total_amount=Decimal("0.00"),
        )

        self.assertRegex(first.locator, r"^[A-Z0-9]{5}$")
        self.assertRegex(second.locator, r"^[A-Z0-9]{5}$")
        self.assertNotEqual(first.locator, second.locator)

    def test_invoice_imputation_summary_without_amount_is_unknown(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B12121212",
            number="F-NO-AMOUNT",
            issue_date=date(2026, 5, 5),
            concept="Factura sin importe",
            taxable_base=Decimal("0.00"),
            taxes=Decimal("0.00"),
            total_amount=Decimal("0.00"),
        )

        summary = invoice.imputation_summary

        self.assertEqual(summary["importe_total_imputado"], Decimal("0.00"))
        self.assertIsNone(summary["porcentaje_imputado"])
        self.assertEqual(summary["estado_imputacion"], "unknown")
        self.assertEqual(summary["porcentaje_display"], "N/A")

    def test_invoice_imputation_summary_zero(self):
        summary = self.invoice.imputation_summary

        self.assertEqual(summary["importe_total_imputado"], Decimal("0.00"))
        self.assertEqual(summary["porcentaje_imputado"], Decimal("0.00"))
        self.assertEqual(summary["estado_imputacion"], "zero")
        self.assertEqual(summary["porcentaje_display"], "0%")

    def test_invoice_imputation_summary_partial(self):
        InvoiceAllocation.objects.create(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("605.00"),
        )

        summary = self.invoice.imputation_summary

        self.assertEqual(summary["importe_total_imputado"], Decimal("605.00"))
        self.assertEqual(summary["estado_imputacion"], "partial")
        self.assertEqual(summary["porcentaje_display"], "50%")

    def test_invoice_imputation_summary_complete(self):
        InvoiceAllocation.objects.create(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("1210.00"),
        )

        summary = self.invoice.imputation_summary

        self.assertEqual(summary["importe_total_imputado"], Decimal("1210.00"))
        self.assertEqual(summary["estado_imputacion"], "complete")
        self.assertEqual(summary["porcentaje_display"], "100%")

    def test_invoice_imputation_summary_over(self):
        over_invoice = Invoice.objects.create(
            locator="OVR01",
            provider_tax_id="B12121212",
            number="F-OVER",
            issue_date=date(2026, 5, 6),
            concept="Factura sobreimputada",
            taxable_base=Decimal("100.00"),
            taxes=Decimal("0.00"),
            total_amount=Decimal("100.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=over_invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("70.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=over_invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("55.00"),
        )

        summary = over_invoice.imputation_summary

        self.assertEqual(summary["importe_total_imputado"], Decimal("125.00"))
        self.assertEqual(summary["estado_imputacion"], "over")
        self.assertEqual(summary["porcentaje_display"], "125%")
        self.assertEqual(summary["barra_porcentaje_style"], "100")

    def test_financier_contribution_cannot_exceed_committed_amount(self):
        contribution = FinancierContribution(
            project=self.project,
            financier=self.financier,
            budget_line=self.budget_line,
            amount=Decimal("2500.00"),
            percentage=Decimal("50.00"),
        )
        with self.assertRaises(ValidationError):
            contribution.full_clean()

    def test_sub_budget_line_cannot_exceed_parent_budget(self):
        sub_budget_line = BudgetLine(
            project=self.project,
            parent=self.budget_line,
            code="1.2",
            name="Otra subpartida",
            approved_budget=Decimal("4000.00"),
        )
        with self.assertRaises(ValidationError):
            sub_budget_line.full_clean()

    def test_project_budget_cannot_be_lower_than_budget_lines_total(self):
        self.project.approved_budget = Decimal("5000.00")
        with self.assertRaises(ValidationError):
            self.project.full_clean()

    def test_budget_line_budget_cannot_be_lower_than_first_level_sub_lines_total(self):
        self.budget_line.approved_budget = Decimal("2500.00")
        with self.assertRaises(ValidationError):
            self.budget_line.full_clean()

    def test_nested_sub_budget_line_cannot_exceed_parent_sub_budget(self):
        child = BudgetLine.objects.create(
            project=self.project,
            parent=self.sub_budget_line,
            code="1.1.1",
            name="Contrato técnico",
            approved_budget=Decimal("1000.00"),
        )
        overflow = BudgetLine(
            project=self.project,
            parent=self.sub_budget_line,
            code="1.1.2",
            name="Contrato adicional",
            approved_budget=Decimal("2500.00"),
        )

        self.assertEqual(child.level, 2)
        with self.assertRaises(ValidationError):
            overflow.full_clean()

    def test_nested_sub_budget_line_depth_is_limited_to_four(self):
        level_2 = BudgetLine.objects.create(
            project=self.project,
            parent=self.sub_budget_line,
            code="1.1.1",
            name="Nivel 2",
            approved_budget=Decimal("1000.00"),
        )
        level_3 = BudgetLine.objects.create(
            project=self.project,
            parent=level_2,
            code="1.1.1.1",
            name="Nivel 3",
            approved_budget=Decimal("500.00"),
        )
        level_4 = BudgetLine.objects.create(
            project=self.project,
            parent=level_3,
            code="1.1.1.1.1",
            name="Nivel 4",
            approved_budget=Decimal("250.00"),
        )
        level_5 = BudgetLine(
            project=self.project,
            parent=level_4,
            code="1.1.1.1.1.1",
            name="Nivel 5",
            approved_budget=Decimal("100.00"),
        )

        self.assertEqual(level_4.level, 4)
        with self.assertRaises(ValidationError):
            level_5.full_clean()

    def test_invoice_allocation_requires_project_financier(self):
        other_financier = Financier.objects.create(name="No vinculado")
        allocation = InvoiceAllocation(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            sub_budget_line=self.sub_budget_line,
            financier=other_financier,
            allocated_amount=Decimal("100.00"),
        )
        with self.assertRaises(ValidationError):
            allocation.full_clean()


class ProjectViewTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="admin",
            email="admin@example.com",
            password="test",
        )
        self.project = Project.objects.create(
            code="TEST01",
            name="Proyecto de prueba",
            status="draft",
            start_date=date(2026, 7, 1),
            finish_date=date(2026, 7, 31),
            end_date="20/01/2023 13:00",
            approved_budget=Decimal("50000.00"),
        )
        self.client.force_login(self.user)

    def test_project_shell_renders_updated_project_header(self):
        self.project.name = "Proyecto actualizado"
        self.project.save(update_fields=["name"])

        response = self.client.get(reverse("project-shell"), {"obj_id": self.project.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Proyecto actualizado")
        self.assertContains(response, 'id="div-container"')
        self.assertContains(response, "1 de julio de 2026")
        self.assertContains(response, "31 de julio de 2026")
        self.assertNotContains(response, "July")
        self.assertNotContains(response, "20/01/2023 13:00")
        self.assertContains(response, 'data-project-tab-count="activities"')
        self.assertContains(response, 'data-count-url="{}"'.format(reverse("project-tab-counts")))

    def test_project_tab_counts_returns_current_counts(self):
        financier = Financier.objects.create(name="Financiador")
        budget_line = BudgetLine.objects.create(project=self.project, code="1", name="Partida")
        BudgetLine.objects.create(project=self.project, code="1.1", name="Subpartida", parent=budget_line)
        Activity.objects.create(project=self.project, code="A1", name="Actividad")
        Text.objects.create(project=self.project, name="Anexo")
        ProjectFinancier.objects.create(project=self.project, financier=financier)
        Income.objects.create(project=self.project, desc="Ingreso")
        Expense.objects.create(project=self.project, desc="Gasto")

        response = self.client.get(reverse("project-tab-counts"), {"obj_id": self.project.id})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            "texts": 1,
            "activities": 1,
            "financiers": 1,
            "budget_lines": 1,
            "incomes": 1,
            "expenses": 1,
        })

    def test_project_form_hides_execution_date(self):
        response = self.client.get(reverse("project-form"), {"obj_id": self.project.id})

        self.assertEqual(response.status_code, 200)
        self.assertNotContains(response, "Fecha de ejecución")
        self.assertNotContains(response, 'name="end_date"')


class ProjectInvoiceDashboardTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(
            username="invoice-admin",
            email="invoice-admin@example.com",
            password="test",
        )
        self.project = Project.objects.create(
            code="INV",
            name="Proyecto facturas",
            manager=self.user,
            status="active",
            approved_budget=Decimal("1000.00"),
        )
        self.activity = Activity.objects.create(
            project=self.project,
            code="A1",
            name="Actividad facturable",
            status=ProgressStatus.IN_PROGRESS,
        )
        self.budget_line = BudgetLine.objects.create(
            project=self.project,
            code="1",
            name="Partida facturable",
            approved_budget=Decimal("1000.00"),
        )
        self.financier = Financier.objects.create(name="Financiador wizard")
        ProjectFinancier.objects.create(
            project=self.project,
            financier=self.financier,
            committed_amount=Decimal("1000.00"),
            granted_amount=Decimal("1000.00"),
        )
        self.contribution = FinancierContribution.objects.create(
            project=self.project,
            financier=self.financier,
            budget_line=self.budget_line,
            amount=Decimal("1000.00"),
            percentage=Decimal("100.00"),
        )
        self.client.force_login(self.user)

    def test_invoice_list_shows_only_last_year_invoices(self):
        Invoice.objects.create(
            locator="REC01",
            provider_tax_id="B22222222",
            number="F-REC",
            issue_date=date(2026, 2, 1),
            concept="Factura reciente",
            taxable_base=Decimal("100.00"),
            taxes=Decimal("21.00"),
            total_amount=Decimal("121.00"),
        )
        Invoice.objects.create(
            locator="OLD01",
            provider_tax_id="B33333333",
            number="F-OLD",
            issue_date=date(2024, 1, 1),
            concept="Factura antigua",
            taxable_base=Decimal("100.00"),
            taxes=Decimal("21.00"),
            total_amount=Decimal("121.00"),
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "REC01")
        self.assertContains(response, "1 de febrero de 2026")
        self.assertNotContains(response, "February")
        self.assertNotContains(response, "OLD01")

    def test_invoice_list_shows_imputation_indicator(self):
        invoice = Invoice.objects.create(
            locator="PCT01",
            provider_tax_id="B22222222",
            number="F-PARTIAL",
            issue_date=date(2026, 2, 2),
            concept="Factura parcialmente imputada",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("121.00"),
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "invoice-imputation--partial")
        self.assertContains(response, "50%")
        self.assertContains(response, "Porcentaje imputado de la factura: 50%")

    def test_recent_invoice_query_preloads_imputed_amount(self):
        invoice = Invoice.objects.create(
            locator="ANN01",
            provider_tax_id="B22222222",
            number="F-ANNOTATED",
            issue_date=date(2026, 2, 3),
            concept="Factura anotada",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("121.00"),
        )
        from .views import get_recent_invoices

        invoice = list(get_recent_invoices(self.user).filter(pk=invoice.pk))[0]

        self.assertEqual(invoice.allocated_amount_total, Decimal("121.00"))
        with self.assertNumQueries(0):
            self.assertEqual(invoice.imputation_summary["porcentaje_display"], "50%")

    def test_invoice_save_creates_invoice_with_generated_locator_and_calculated_total(self):
        response = self.client.get(reverse("invoice-save"), {
            "provider_tax_id": "b44444444",
            "number": "F-NEW",
            "issue_date": "2026-06-01",
            "payment_date": "2026-06-10",
            "concept": "Factura nueva",
            "taxable_base": "200.00",
            "taxes": "42.00",
        })

        self.assertEqual(response.status_code, 200)
        invoice = Invoice.objects.get(number="F-NEW")
        self.assertRegex(invoice.locator, r"^[A-Z0-9]{5}$")
        self.assertEqual(invoice.invoice_code, "2026-{}".format(invoice.id))
        self.assertEqual(invoice.provider_tax_id, "B44444444")
        self.assertEqual(invoice.total_amount, Decimal("242.00"))
        self.assertContains(response, invoice.locator)

    def test_invoice_allocation_wizard_saves_allocation_without_activity(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B55555555",
            number="F-WIZ",
            issue_date=date(2026, 6, 2),
            concept="Factura imputable",
            taxable_base=Decimal("300.00"),
            taxes=Decimal("63.00"),
            total_amount=Decimal("363.00"),
        )

        response = self.client.get(reverse("invoice-allocation-save"), {
            "invoice_id": invoice.id,
            "project": self.project.id,
            "budget_line": self.budget_line.id,
            "financier_contribution": self.contribution.id,
            "allocated_amount": "200.00",
            "activity": "",
        })

        self.assertEqual(response.status_code, 200)
        allocation = InvoiceAllocation.objects.get(invoice=invoice)
        self.assertEqual(allocation.project, self.project)
        self.assertEqual(allocation.budget_line, self.budget_line)
        self.assertIsNone(allocation.sub_budget_line)
        self.assertEqual(allocation.financier_contribution, self.contribution)
        self.assertEqual(allocation.financier, self.financier)
        self.assertIsNone(allocation.activity)
        self.assertEqual(allocation.allocated_amount, Decimal("200.00"))

    def test_invoice_allocation_wizard_saves_percentage_amount(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B66666666",
            number="F-PCT",
            issue_date=date(2026, 6, 3),
            concept="Factura por porcentaje",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.get(reverse("invoice-allocation-save"), {
            "invoice_id": invoice.id,
            "project": self.project.id,
            "budget_line": self.budget_line.id,
            "financier_contribution": self.contribution.id,
            "allocation_mode": "percentage",
            "allocated_percentage": "50.00",
            "activity": self.activity.id,
        })

        self.assertEqual(response.status_code, 200)
        allocation = InvoiceAllocation.objects.get(invoice=invoice)
        self.assertEqual(allocation.activity, self.activity)
        self.assertEqual(allocation.allocated_amount, Decimal("121.00"))

    def test_invoice_allocation_wizard_rejects_amount_over_pending_invoice_total(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B77777777",
            number="F-LIMIT",
            issue_date=date(2026, 6, 4),
            concept="Factura parcialmente imputada",
            taxable_base=Decimal("300.00"),
            taxes=Decimal("63.00"),
            total_amount=Decimal("363.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            financier_contribution=self.contribution,
            financier=self.financier,
            allocated_amount=Decimal("300.00"),
        )

        response = self.client.get(reverse("invoice-allocation-save"), {
            "invoice_id": invoice.id,
            "project": self.project.id,
            "budget_line": self.budget_line.id,
            "financier_contribution": self.contribution.id,
            "allocation_mode": "amount",
            "allocated_amount": "100.00",
            "activity": "",
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvoiceAllocation.objects.filter(invoice=invoice).count(), 1)
