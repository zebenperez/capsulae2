from datetime import date, timedelta
from decimal import Decimal
from io import BytesIO
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse
from django.utils import timezone
from PIL import Image

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
    InvoiceStatus,
    InvoiceStatusChange,
    PendingInvoiceImport,
    PendingInvoiceImportStatus,
    Objective,
    ObjectiveType,
    CashOutflow,
    PaymentFinancialState,
    PaymentObligation,
    PaymentObligationStatus,
    PaymentObligationType,
    Project,
    ProjectFinancier,
    ProgressStatus,
    Supplier,
    Text,
)
from .services.invoice_ai import (
    InvoiceExtractionError,
    InvoiceExtractionResult,
    build_invoice_openai_content,
    parse_invoice_extraction_payload,
)
from .services.invoice_import import validate_invoice_amounts
from .services.supplier_matching import (
    damerau_levenshtein_distance,
    jaro_winkler_similarity,
    match_suppliers,
    normalize_tax_id,
)
from .templatetags.project_tags import money_es


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
            budget_line=self.sub_budget_line,
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
            budget_line=self.sub_budget_line,
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
            budget_line=self.sub_budget_line,
            allocated_amount=Decimal("1000.00"),
        )
        allocation = InvoiceAllocation(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.sub_budget_line,
            allocated_amount=Decimal("500.00"),
        )
        with self.assertRaises(ValidationError):
            allocation.full_clean()

    def test_invoice_allocation_can_have_no_activity(self):
        allocation = InvoiceAllocation(
            invoice=self.invoice,
            project=self.project,
            activity=None,
            budget_line=self.sub_budget_line,
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
            iva_amount=Decimal("2.10"),
            igic_amount=Decimal("0.00"),
            irpf_amount=Decimal("1.00"),
            total_amount=Decimal("0.00"),
        )

        self.assertEqual(invoice.locator, "AB12C")
        self.assertEqual(invoice.invoice_code, "2026-{}".format(invoice.id))
        self.assertEqual(invoice.taxes, Decimal("1.10"))
        self.assertEqual(invoice.total_amount, Decimal("11.60"))

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
            budget_line=self.sub_budget_line,
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
            budget_line=self.sub_budget_line,
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
            budget_line=self.sub_budget_line,
            allocated_amount=Decimal("70.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=over_invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.sub_budget_line,
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

    def test_invoice_allocation_requires_leaf_budget_line(self):
        allocation = InvoiceAllocation(
            invoice=self.invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
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

    def test_project_financiers_tab_uses_clear_financial_labels(self):
        financier = Financier.objects.create(
            name="Caixa",
            financier_type=FinancierType.PUBLIC,
            tax_id="A00000000",
        )
        ProjectFinancier.objects.create(
            project=self.project,
            financier=financier,
            committed_amount=Decimal("30000.00"),
            granted_amount=Decimal("28000.00"),
            disbursed_amount=Decimal("25000.00"),
        )

        response = self.client.get(reverse("project-financiers"), {"obj_id": self.project.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Financiación comprometida")
        self.assertContains(response, "Fondos desembolsados")
        self.assertContains(response, "Disponible para partidas")
        self.assertContains(response, "30.000,00 €")
        self.assertContains(response, 'aria-label="Editar financiador Caixa"')
        self.assertNotContains(response, ">Comprometido</span>\n            <span class=\"project-stat-value\">1</span>")

    def test_money_es_formats_spanish_currency(self):
        self.assertEqual(money_es(Decimal("50000.00")), "50.000,00 €")
        self.assertEqual(money_es(Decimal("750.00")), "750,00 €")

    def test_budget_lines_tab_uses_clear_budget_labels(self):
        budget_line = BudgetLine.objects.create(
            project=self.project,
            code="P001",
            name="Contratación de personal",
            approved_budget=Decimal("30000.00"),
        )
        sub_line = BudgetLine.objects.create(
            project=self.project,
            parent=budget_line,
            code="S001",
            name="Técnico de campo",
            approved_budget=Decimal("3000.00"),
        )
        BudgetLine.objects.create(
            project=self.project,
            code="P002",
            name="Viajes",
            approved_budget=Decimal("5000.00"),
        )
        financier = Financier.objects.create(name="Financiador listado")
        ProjectFinancier.objects.create(
            project=self.project,
            financier=financier,
            committed_amount=Decimal("2500.00"),
            granted_amount=Decimal("2500.00"),
        )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier,
            budget_line=sub_line,
            amount=Decimal("2500.00"),
            percentage=Decimal("83.33"),
        )
        invoice = Invoice.objects.create(
            provider_tax_id="B12345678",
            number="F-LIST-001",
            issue_date=date(2026, 7, 10),
            concept="Servicios imputados",
            taxable_base=Decimal("750.00"),
            taxes=Decimal("0.00"),
            total_amount=Decimal("750.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=invoice,
            project=self.project,
            budget_line=sub_line,
            allocated_amount=Decimal("750.00"),
        )

        response = self.client.get(reverse("project-budget-lines"), {"obj_id": self.project.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "project-budget-items")
        self.assertContains(response, "PARTIDAS PRESUPUESTARIAS")
        self.assertContains(response, "2 partidas")
        self.assertContains(response, "Aprobado")
        self.assertContains(response, "Asignado")
        self.assertContains(response, "Ejecutado")
        self.assertContains(response, "Disponible")
        self.assertContains(response, "Pendiente de asignar")
        self.assertNotContains(response, "Asignado a subpartidas")
        self.assertContains(response, "Financiado")
        self.assertContains(response, "asignados de")
        self.assertContains(response, "project-budget-assignment-bar")
        self.assertContains(response, "project-funding-partial")
        self.assertContains(response, "project-funding-none")
        self.assertContains(response, "Gestionar financiación")
        self.assertContains(response, "project-budget-menu-toggle")
        self.assertContains(response, "aria-expanded=\"true\"")
        self.assertContains(response, "30.000,00 €")
        self.assertContains(response, "3.000,00 €")
        self.assertContains(response, "5.000,00 €")
        self.assertContains(response, "2.250,00 €", count=2)
        self.assertContains(response, "2.500,00 €", count=2)
        self.assertContains(response, 'aria-label="Editar partida P001 - Contratación de personal"')
        self.assertContains(response, 'aria-label="Gestionar financiación de P001.S001 - Técnico de campo"')
        self.assertContains(response, 'aria-label="Gestionar financiación de P002 - Viajes"')
        self.assertNotContains(response, 'aria-label="Gestionar financiación de P001 - Contratación de personal"')
        self.assertContains(response, "¿Seguro que quieres eliminar esta partida?")

    def test_budget_line_financed_amounts_sum_leaf_financiers_and_child_lines(self):
        from .views import get_budget_lines_context

        parent = BudgetLine.objects.create(
            project=self.project,
            code="P100",
            name="Partida padre",
            approved_budget=Decimal("5000.00"),
        )
        child = BudgetLine.objects.create(
            project=self.project,
            parent=parent,
            code="S100",
            name="Partida hoja",
            approved_budget=Decimal("5000.00"),
        )
        financier_a = Financier.objects.create(name="Financiador A")
        financier_b = Financier.objects.create(name="Financiador B")
        ProjectFinancier.objects.create(
            project=self.project,
            financier=financier_a,
            committed_amount=Decimal("5000.00"),
            granted_amount=Decimal("5000.00"),
        )
        ProjectFinancier.objects.create(
            project=self.project,
            financier=financier_b,
            committed_amount=Decimal("5000.00"),
            granted_amount=Decimal("5000.00"),
        )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier_a,
            budget_line=parent,
            amount=Decimal("900.00"),
            percentage=Decimal("18.00"),
        )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier_a,
            budget_line=child,
            amount=Decimal("100.00"),
            percentage=Decimal("2.00"),
        )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier_a,
            budget_line=child,
            amount=Decimal("150.00"),
            percentage=Decimal("3.00"),
        )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier_b,
            budget_line=child,
            amount=Decimal("200.00"),
            percentage=Decimal("4.00"),
        )

        context = get_budget_lines_context(self.project)
        parent_row = next(item for item in context["budget_lines"] if item.id == parent.id)
        child_row = parent_row.tree_sub_lines[0]["item"]

        self.assertEqual(child_row.financed_amounts_by_financier[financier_a.id], Decimal("250.00"))
        self.assertEqual(child_row.financed_amounts_by_financier[financier_b.id], Decimal("200.00"))
        self.assertEqual(child_row.financed_amount, Decimal("450.00"))
        self.assertEqual(parent_row.financed_amounts_by_financier[financier_a.id], Decimal("250.00"))
        self.assertEqual(parent_row.financed_amounts_by_financier[financier_b.id], Decimal("200.00"))
        self.assertEqual(parent_row.financed_amount, Decimal("450.00"))

    def test_financier_contribution_modal_shows_financial_summary_and_registered_contributions(self):
        budget_line = BudgetLine.objects.create(
            project=self.project,
            code="P001",
            name="Técnico de Laboratorio",
            approved_budget=Decimal("15000.00"),
        )
        financier_1 = Financier.objects.create(name="Gobierno de Canarias")
        financier_2 = Financier.objects.create(name="Cabildo de Tenerife")
        financier_3 = Financier.objects.create(name="Fondos propios")
        for financier in [financier_1, financier_2, financier_3]:
            ProjectFinancier.objects.create(
                project=self.project,
                financier=financier,
                committed_amount=Decimal("15000.00"),
                granted_amount=Decimal("15000.00"),
            )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier_1,
            budget_line=budget_line,
            amount=Decimal("5000.00"),
            percentage=Decimal("33.33"),
            notes="Financiación inicial",
        )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier_2,
            budget_line=budget_line,
            amount=Decimal("2500.00"),
            percentage=Decimal("16.67"),
        )
        FinancierContribution.objects.create(
            project=self.project,
            financier=financier_3,
            budget_line=budget_line,
            amount=Decimal("1000.00"),
            percentage=Decimal("6.67"),
            notes="Complemento",
        )

        response = self.client.get(reverse("project-financier-contribution-form"), {"budget_line_id": budget_line.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "project-financier-allocation-modal")
        self.assertContains(response, "APORTACIÓN DE FINANCIADOR A PARTIDA")
        self.assertContains(response, "P001 · Técnico de Laboratorio")
        self.assertContains(response, "aria-label=\"Cerrar\"")
        self.assertContains(response, "RESUMEN FINANCIERO")
        self.assertContains(response, "15.000,00 €")
        self.assertContains(response, "8.500,00 €", count=2)
        self.assertContains(response, "6.500,00 €", count=2)
        self.assertContains(response, "56,7 % financiado")
        self.assertContains(response, "role=\"progressbar\"")
        self.assertContains(response, "APORTACIONES REGISTRADAS")
        self.assertContains(response, "Gobierno de Canarias")
        self.assertContains(response, "Financiación inicial")
        self.assertContains(response, "Cabildo de Tenerife")
        self.assertContains(response, "—")
        self.assertContains(response, "Fondos propios")
        self.assertContains(response, "Total aportado")
        self.assertContains(response, "NUEVA APORTACIÓN")
        self.assertContains(response, "Añadir aportación")
        self.assertContains(response, "Disponible por aportar")
        self.assertContains(response, "project-contribution-error")
        self.assertNotContains(response, "Presupuesto partida / subpartida")

    def test_new_sub_budget_line_receives_parent_financing_and_invoice_allocations(self):
        budget_line = BudgetLine.objects.create(
            project=self.project,
            code="P010",
            name="Partida con financiación",
            approved_budget=Decimal("10000.00"),
        )
        financier = Financier.objects.create(name="Financiador padre")
        ProjectFinancier.objects.create(
            project=self.project,
            financier=financier,
            committed_amount=Decimal("4000.00"),
            granted_amount=Decimal("4000.00"),
        )
        contribution = FinancierContribution.objects.create(
            project=self.project,
            financier=financier,
            budget_line=budget_line,
            amount=Decimal("4000.00"),
            percentage=Decimal("40.00"),
        )
        invoice = Invoice.objects.create(
            provider_tax_id="B87654321",
            number="F-HEREDA-001",
            issue_date=date(2026, 7, 12),
            concept="Factura imputada al padre",
            taxable_base=Decimal("1000.00"),
            taxes=Decimal("0.00"),
            total_amount=Decimal("1000.00"),
        )
        allocation = InvoiceAllocation.objects.create(
            invoice=invoice,
            project=self.project,
            budget_line=budget_line,
            allocated_amount=Decimal("1000.00"),
        )

        response = self.client.get(reverse("project-sub-budget-line-form"), {"budget_line_id": budget_line.id})

        self.assertEqual(response.status_code, 200)
        child = budget_line.child_lines.get()
        contribution.refresh_from_db()
        allocation.refresh_from_db()
        self.assertEqual(contribution.budget_line, child)
        self.assertEqual(allocation.budget_line, child)
        self.assertEqual(child.approved_budget, Decimal("4000.00"))
        self.assertEqual(contribution.percentage, Decimal("100.00"))

    def test_new_budget_line_form_reuses_empty_draft(self):
        first_response = self.client.get(reverse("project-budget-line-form"), {"project_id": self.project.id})
        second_response = self.client.get(reverse("project-budget-line-form"), {"project_id": self.project.id})

        self.assertEqual(first_response.status_code, 200)
        self.assertEqual(second_response.status_code, 200)
        budget_lines = BudgetLine.objects.filter(project=self.project, parent__isnull=True)
        self.assertEqual(budget_lines.count(), 1)
        self.assertContains(second_response, 'data-obj-id="{}"'.format(budget_lines.get().id))

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
        self.assertContains(response, "01/02/2026")
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
            allocated_amount=Decimal("121.00"),
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "invoice-imputation--partial")
        self.assertContains(response, "50%")
        self.assertContains(response, "Porcentaje imputado de la factura: 50%")

    def test_supplier_crud_creates_searches_and_removes_supplier(self):
        response = self.client.get(reverse("supplier-save"), {
            "name": "Proveedor Salud",
            "nif": "b12345678",
            "address": "Calle Mayor 1",
            "email": "proveedor@example.com",
            "phone": "600111222",
            "contact_person": "Ana Contacto",
        })

        self.assertEqual(response.status_code, 200)
        supplier = Supplier.objects.get(nif="B12345678")
        self.assertEqual(supplier.name, "Proveedor Salud")
        self.assertContains(response, "Proveedor Salud")
        self.assertContains(response, "B12345678")

        response = self.client.get(reverse("supplier-search"), {"s-supplier": "Ana"})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Proveedor Salud")

        response = self.client.get(reverse("supplier-form"), {"obj_id": supplier.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Editar proveedor")
        self.assertContains(response, "Proveedor Salud")

        response = self.client.get(reverse("supplier-remove"), {"obj_id": supplier.id})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Supplier.objects.filter(pk=supplier.pk).exists())

    def test_projects_dashboard_context_includes_suppliers(self):
        supplier = Supplier.objects.create(
            name="Proveedor Dashboard",
            nif="B99999999",
            address="Calle Dashboard 1",
            email="dashboard@example.com",
            phone="600999999",
            contact_person="Contacto Dashboard",
        )
        from .views import get_projects_dashboard_context

        context = get_projects_dashboard_context(self.user)
        response = self.client.get(reverse("supplier-list"))

        self.assertEqual(response.status_code, 200)
        self.assertIn(supplier, list(context["suppliers"]))
        self.assertContains(response, "Proveedor Dashboard")

    def test_invoice_list_uses_task_oriented_invoice_layout(self):
        Invoice.objects.create(
            locator="UX001",
            provider_tax_id="B44444444",
            number="F-UX",
            issue_date=date(2026, 6, 1),
            concept="Factura para revisar jerarquia visual",
            taxable_base=Decimal("1500.00"),
            taxes=Decimal("105.00"),
            total_amount=Decimal("1605.00"),
            status=InvoiceStatus.PAID,
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Proveedor")
        self.assertNotContains(response, "NIF proveedor")
        self.assertContains(response, "Proveedor no registrado")
        self.assertContains(response, "NIF/CIF: B44444444")
        self.assertContains(response, "Concepto")
        self.assertContains(response, "Factura para revisar jerarquia visual")
        self.assertContains(response, "01/06/2026")
        self.assertContains(response, "pendiente")
        self.assertContains(response, "Base: 1.500,00 €")
        self.assertContains(response, "IVA: 105,00 €")
        self.assertContains(response, "IGIC: 0,00 €")
        self.assertContains(response, "IRPF: 0,00 €")
        self.assertContains(response, "Total: 1.605,00 €")
        self.assertContains(response, "Requiere imputación")

    def test_invoice_list_warns_when_physical_document_is_missing(self):
        invoice = Invoice.objects.create(
            locator="DOC01",
            provider_tax_id="B44444444",
            number="F-DOC",
            issue_date=date(2026, 6, 1),
            concept="Factura sin documento fisico",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Falta documento físico")
        self.assertContains(response, reverse("invoice-physical-document-upload"))
        self.assertContains(response, 'data-obj-id="{}"'.format(invoice.id))

    def test_invoice_list_shows_physical_document_loaded(self):
        invoice = Invoice.objects.create(
            locator="DOC02",
            provider_tax_id="B44444444",
            number="F-DOC-LOADED",
            issue_date=date(2026, 6, 1),
            concept="Factura con documento fisico",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )
        invoice.physical_document.save("documento-fisico.pdf", SimpleUploadedFile("documento-fisico.pdf", b"pdf"), save=True)

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Documento físico")
        self.assertNotContains(response, "Falta documento físico")

    def test_invoice_physical_document_upload_saves_file(self):
        invoice = Invoice.objects.create(
            locator="DOC03",
            provider_tax_id="B44444444",
            number="F-DOC-UPLOAD",
            issue_date=date(2026, 6, 1),
            concept="Factura para subir documento fisico",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.post(reverse("invoice-physical-document-upload"), {
            "obj_id": invoice.id,
            "file": self._pdf_upload("documento-fisico.pdf"),
        })

        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertTrue(invoice.physical_document.name.endswith(".pdf"))
        self.assertContains(response, "Documento físico")
        self.assertNotContains(response, "Falta documento físico")

    def test_invoice_list_shows_remove_action_only_without_allocations(self):
        removable_invoice = Invoice.objects.create(
            locator="DEL01",
            provider_tax_id="B44444444",
            number="F-DELETE",
            issue_date=date(2026, 6, 1),
            concept="Factura eliminable",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )
        allocated_invoice = Invoice.objects.create(
            locator="DEL02",
            provider_tax_id="B44444444",
            number="F-NO-DELETE",
            issue_date=date(2026, 6, 2),
            concept="Factura no eliminable",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=allocated_invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            allocated_amount=Decimal("100.00"),
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, reverse("invoice-remove"))
        self.assertContains(response, 'data-obj_id="{}"'.format(removable_invoice.id))
        self.assertNotContains(response, 'data-obj_id="{}"'.format(allocated_invoice.id))

    def test_invoice_remove_deletes_invoice_and_physical_document(self):
        invoice = Invoice.objects.create(
            locator="DEL03",
            provider_tax_id="B44444444",
            number="F-DELETE-DOC",
            issue_date=date(2026, 6, 1),
            concept="Factura eliminable con documento",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )
        invoice.physical_document.save("documento-fisico-delete.pdf", SimpleUploadedFile("documento-fisico-delete.pdf", b"pdf"), save=True)
        storage = invoice.physical_document.storage
        document_name = invoice.physical_document.name
        self.assertTrue(storage.exists(document_name))

        response = self.client.get(reverse("invoice-remove"), {"obj_id": invoice.id})

        self.assertEqual(response.status_code, 200)
        self.assertFalse(Invoice.objects.filter(pk=invoice.pk).exists())
        self.assertFalse(storage.exists(document_name))

    def test_invoice_remove_rejects_invoice_with_allocations(self):
        invoice = Invoice.objects.create(
            locator="DEL04",
            provider_tax_id="B44444444",
            number="F-DELETE-ALLOCATED",
            issue_date=date(2026, 6, 1),
            concept="Factura con imputacion",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )
        invoice.physical_document.save("documento-fisico-allocated.pdf", SimpleUploadedFile("documento-fisico-allocated.pdf", b"pdf"), save=True)
        document_name = invoice.physical_document.name
        storage = invoice.physical_document.storage
        InvoiceAllocation.objects.create(
            invoice=invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            allocated_amount=Decimal("100.00"),
        )

        response = self.client.get(reverse("invoice-remove"), {"obj_id": invoice.id})

        self.assertEqual(response.status_code, 400)
        self.assertTrue(Invoice.objects.filter(pk=invoice.pk).exists())
        self.assertTrue(storage.exists(document_name))
        self.assertContains(response, "No se puede eliminar una factura con imputaciones.", status_code=400)

    def test_invoice_list_resolves_supplier_by_nif(self):
        Supplier.objects.create(
            name="Proveedor Registrado",
            nif="B44444444",
            address="Calle Mayor 1",
            email="proveedor@example.com",
            phone="600111222",
            contact_person="Ana Contacto",
        )
        Invoice.objects.create(
            locator="SUP01",
            provider_tax_id="B44444444",
            number="F-SUP",
            issue_date=date(2026, 6, 1),
            concept="Factura con proveedor registrado",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Proveedor Registrado")
        self.assertNotContains(response, "Proveedor no registrado")

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
            "iva_amount": "42.00",
            "igic_amount": "7.00",
            "irpf_amount": "15.00",
        })

        self.assertEqual(response.status_code, 200)
        invoice = Invoice.objects.get(number="F-NEW")
        self.assertRegex(invoice.locator, r"^[A-Z0-9]{5}$")
        self.assertEqual(invoice.invoice_code, "2026-{}".format(invoice.id))
        self.assertEqual(invoice.provider_tax_id, "B44444444")
        self.assertEqual(invoice.iva_amount, Decimal("42.00"))
        self.assertEqual(invoice.igic_amount, Decimal("7.00"))
        self.assertEqual(invoice.irpf_amount, Decimal("15.00"))
        self.assertEqual(invoice.taxes, Decimal("34.00"))
        self.assertEqual(invoice.total_amount, Decimal("234.00"))
        self.assertContains(response, invoice.locator)

    def test_invoice_form_shows_amounts_in_number_input_format(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444",
            number="F-EDIT",
            issue_date=date(2026, 6, 1),
            concept="Factura editable",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.get(reverse("invoice-form"), {"obj_id": invoice.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'name="taxable_base" value="200.00"', html=False)
        self.assertContains(response, 'name="iva_amount" value="42.00"', html=False)
        self.assertContains(response, 'name="igic_amount" value="0.00"', html=False)
        self.assertContains(response, 'name="irpf_amount" value="0.00"', html=False)
        self.assertContains(response, 'name="total_amount" value="242.00"', html=False)

    def test_invoice_form_shows_physical_document_field(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444",
            number="F-DOC-FORM",
            issue_date=date(2026, 6, 1),
            concept="Factura editable con documento fisico",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.get(reverse("invoice-form"), {"obj_id": invoice.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Documento físico")
        self.assertContains(response, "Subir documento físico")
        self.assertContains(response, reverse("invoice-physical-document-upload"))

    def test_invoice_status_change_action_creates_trace(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444",
            number="F-STATUS",
            issue_date=date(2026, 6, 1),
            concept="Factura con estado",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
            status=InvoiceStatus.DRAFT,
        )

        response = self.client.get(reverse("invoice-status-save"), {
            "invoice_id": invoice.id,
            "status": InvoiceStatus.PENDING,
        })

        self.assertEqual(response.status_code, 200)
        invoice.refresh_from_db()
        self.assertEqual(invoice.status, InvoiceStatus.PENDING)
        change = InvoiceStatusChange.objects.get(invoice=invoice)
        self.assertEqual(change.changed_by, self.user)
        self.assertIsNotNone(change.changed_at)
        self.assertEqual(change.original_status, InvoiceStatus.DRAFT)
        self.assertEqual(change.final_status, InvoiceStatus.PENDING)
        self.assertContains(response, "Pendiente")

    def test_invoice_status_change_rejects_same_status(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444",
            number="F-SAME",
            issue_date=date(2026, 6, 1),
            concept="Factura sin cambio",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
            status=InvoiceStatus.DRAFT,
        )

        response = self.client.get(reverse("invoice-status-save"), {
            "invoice_id": invoice.id,
            "status": InvoiceStatus.DRAFT,
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvoiceStatusChange.objects.filter(invoice=invoice).count(), 0)

    def test_invoice_list_shows_traceability_action(self):
        Invoice.objects.create(
            provider_tax_id="B44444444",
            number="F-TRACE-LIST",
            issue_date=date(2026, 6, 1),
            concept="Factura con accion de trazabilidad",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.get(reverse("invoice-list"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Ver historial")
        self.assertContains(response, reverse("invoice-traceability"))

    def test_invoice_traceability_shows_status_changes(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444",
            number="F-TRACE",
            issue_date=date(2026, 6, 1),
            concept="Factura con trazabilidad",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
            status=InvoiceStatus.PENDING,
        )
        InvoiceStatusChange.objects.create(
            invoice=invoice,
            changed_by=self.user,
            original_status=InvoiceStatus.DRAFT,
            final_status=InvoiceStatus.PENDING,
        )

        response = self.client.get(reverse("invoice-traceability"), {"invoice_id": invoice.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Trazabilidad de factura")
        self.assertContains(response, "F-TRACE")
        self.assertContains(response, "Borrador")
        self.assertContains(response, "Pendiente")
        self.assertContains(response, self.user.username)

    def test_invoice_traceability_shows_empty_state(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444",
            number="F-NO-TRACE",
            issue_date=date(2026, 6, 1),
            concept="Factura sin trazabilidad",
            taxable_base=Decimal("200.00"),
            taxes=Decimal("42.00"),
            total_amount=Decimal("242.00"),
        )

        response = self.client.get(reverse("invoice-traceability"), {"invoice_id": invoice.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "No hay cambios de estado registrados para esta factura.")

    def test_invoice_traceability_offers_attachment_when_document_is_missing(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444", number="F-NO-DOC", issue_date=date(2026, 6, 1),
            concept="Factura sin documento", taxable_base=Decimal("100.00"), taxes=Decimal("21.00"), total_amount=Decimal("121.00"),
        )

        response = self.client.get(reverse("invoice-traceability"), {"invoice_id": invoice.id})

        self.assertContains(response, "Adjuntar documento")
        self.assertContains(response, "Sin documento físico")
        self.assertContains(response, reverse("invoice-physical-document-form"))

    def test_invoice_traceability_shows_document_format_and_size(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444", number="F-WITH-DOC", issue_date=date(2026, 6, 1),
            concept="Factura con documento", taxable_base=Decimal("100.00"), taxes=Decimal("21.00"), total_amount=Decimal("121.00"),
        )
        invoice.physical_document.save("traceability.pdf", self._pdf_upload("traceability.pdf"), save=True)

        response = self.client.get(reverse("invoice-traceability"), {"invoice_id": invoice.id})

        self.assertContains(response, "Ver documento")
        self.assertContains(response, "PDF · 1 KB")
        self.assertContains(response, reverse("invoice-physical-document-viewer"))

    def test_invoice_document_form_reuses_import_picker_without_openai(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444", number="F-ATTACH", issue_date=date(2026, 6, 1),
            concept="Factura a adjuntar", taxable_base=Decimal("100.00"), taxes=Decimal("21.00"), total_amount=Decimal("121.00"),
        )

        response = self.client.get(reverse("invoice-physical-document-form"), {"invoice_id": invoice.id})

        self.assertContains(response, "Seleccionar archivo")
        self.assertContains(response, "Tomar foto")
        self.assertContains(response, reverse("invoice-physical-document-upload"))
        self.assertNotContains(response, "Analizar factura")

    @patch("projects.views.extract_invoice_data")
    def test_attaching_document_does_not_extract_or_modify_invoice(self, extract_invoice_data):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444", number="F-NO-AI", issue_date=date(2026, 6, 1),
            concept="Datos intactos", taxable_base=Decimal("100.00"), taxes=Decimal("21.00"), total_amount=Decimal("121.00"),
        )
        invoice_count = Invoice.objects.count()

        response = self.client.post(reverse("invoice-physical-document-upload"), {
            "obj_id": invoice.id,
            "invoice_document": self._png_upload("documento.png"),
        })

        self.assertEqual(response.status_code, 200)
        extract_invoice_data.assert_not_called()
        self.assertEqual(Invoice.objects.count(), invoice_count)
        invoice.refresh_from_db()
        self.assertEqual(invoice.concept, "Datos intactos")
        self.assertContains(response, "Ver documento")

    def test_invalid_replacement_keeps_previous_document(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444", number="F-KEEP-DOC", issue_date=date(2026, 6, 1),
            concept="Conservar documento", taxable_base=Decimal("100.00"), taxes=Decimal("21.00"), total_amount=Decimal("121.00"),
        )
        invoice.physical_document.save("original.pdf", self._pdf_upload("original.pdf"), save=True)
        original_name = invoice.physical_document.name

        response = self.client.post(reverse("invoice-physical-document-upload"), {
            "obj_id": invoice.id,
            "invoice_document": SimpleUploadedFile("falso.pdf", b"contenido invalido", content_type="application/pdf"),
        })

        self.assertEqual(response.status_code, 400)
        invoice.refresh_from_db()
        self.assertEqual(invoice.physical_document.name, original_name)
        self.assertTrue(invoice.physical_document.storage.exists(original_name))

    def test_invoice_document_view_and_download_have_safe_headers(self):
        invoice = Invoice.objects.create(
            provider_tax_id="B44444444", number="F-PRIVATE-DOC", issue_date=date(2026, 6, 1),
            concept="Documento privado", taxable_base=Decimal("100.00"), taxes=Decimal("21.00"), total_amount=Decimal("121.00"),
        )
        invoice.physical_document.save("private.pdf", self._pdf_upload("private.pdf"), save=True)
        url = reverse("invoice-physical-document-file", args=[invoice.id])

        inline_response = self.client.get(url)
        download_response = self.client.get(url, {"download": "1"})

        self.assertEqual(inline_response.status_code, 200)
        self.assertEqual(inline_response["X-Content-Type-Options"], "nosniff")
        self.assertEqual(inline_response["Cache-Control"], "private, no-store")
        self.assertTrue(inline_response["Content-Disposition"].startswith("inline;"))
        self.assertTrue(download_response["Content-Disposition"].startswith("attachment;"))

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
            "allocated_amount": "200.00",
            "activity": "",
        })

        self.assertEqual(response.status_code, 200)
        allocation = InvoiceAllocation.objects.get(invoice=invoice)
        self.assertEqual(allocation.project, self.project)
        self.assertEqual(allocation.budget_line, self.budget_line)
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
            "allocation_mode": "percentage",
            "allocated_percentage": "50.00",
            "activity": self.activity.id,
        })

        self.assertEqual(response.status_code, 200)
        allocation = InvoiceAllocation.objects.get(invoice=invoice)
        self.assertEqual(allocation.activity, self.activity)
        self.assertEqual(allocation.allocated_amount, Decimal("121.00"))

    def test_invoice_allocation_wizard_lists_only_leaf_budget_lines(self):
        parent = BudgetLine.objects.create(
            project=self.project,
            code="2",
            name="Partida padre no seleccionable",
            approved_budget=Decimal("500.00"),
        )
        child = BudgetLine.objects.create(
            project=self.project,
            parent=parent,
            code="2.1",
            name="Partida hija seleccionable",
            approved_budget=Decimal("500.00"),
        )
        invoice = Invoice.objects.create(
            provider_tax_id="B88888888",
            number="F-LEAF",
            issue_date=date(2026, 6, 5),
            concept="Factura hoja",
            taxable_base=Decimal("100.00"),
            taxes=Decimal("21.00"),
            total_amount=Decimal("121.00"),
        )

        response = self.client.get(reverse("invoice-allocation-wizard"), {"invoice_id": invoice.id})

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "invoice-allocation-wizard")
        self.assertContains(response, "IMPUTAR FACTURA")
        self.assertContains(response, "invoice-wizard-kpi-allocated")
        self.assertContains(response, "invoice-wizard-kpi-pending")
        self.assertContains(response, "PROYECTO")
        self.assertContains(response, "PARTIDA PRESUPUESTARIA")
        self.assertContains(response, "IMPORTE A IMPUTAR")
        self.assertContains(response, "Confirmar imputación")
        self.assertContains(response, "invoice-wizard-error")
        self.assertContains(response, "Partida hija seleccionable")
        self.assertContains(response, 'value="{}"'.format(child.id))
        self.assertNotContains(response, 'value="{}"'.format(parent.id))

    def test_invoice_allocation_wizard_rejects_amount_over_budget_line_available(self):
        previous_invoice = Invoice.objects.create(
            provider_tax_id="B99999999",
            number="F-PREV",
            issue_date=date(2026, 6, 6),
            concept="Factura previa",
            taxable_base=Decimal("900.00"),
            taxes=Decimal("0.00"),
            total_amount=Decimal("900.00"),
        )
        InvoiceAllocation.objects.create(
            invoice=previous_invoice,
            project=self.project,
            activity=self.activity,
            budget_line=self.budget_line,
            allocated_amount=Decimal("900.00"),
        )
        invoice = Invoice.objects.create(
            provider_tax_id="B10101010",
            number="F-OVER-LINE",
            issue_date=date(2026, 6, 7),
            concept="Factura supera partida",
            taxable_base=Decimal("500.00"),
            taxes=Decimal("0.00"),
            total_amount=Decimal("500.00"),
        )

        response = self.client.get(reverse("invoice-allocation-save"), {
            "invoice_id": invoice.id,
            "project": self.project.id,
            "budget_line": self.budget_line.id,
            "allocation_mode": "amount",
            "allocated_amount": "150.00",
            "activity": "",
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvoiceAllocation.objects.filter(invoice=invoice).count(), 0)

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
            allocated_amount=Decimal("300.00"),
        )

        response = self.client.get(reverse("invoice-allocation-save"), {
            "invoice_id": invoice.id,
            "project": self.project.id,
            "budget_line": self.budget_line.id,
            "allocation_mode": "amount",
            "allocated_amount": "100.00",
            "activity": "",
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(InvoiceAllocation.objects.filter(invoice=invoice).count(), 1)

    def _pdf_upload(self, name="factura.pdf", content_type="application/pdf"):
        return SimpleUploadedFile(name, b"%PDF-1.4\n% factura de prueba\n%%EOF\n", content_type=content_type)

    def _image_bytes(self, image_format):
        buffer = BytesIO()
        Image.new("RGB", (1, 1), color=(255, 255, 255)).save(buffer, format=image_format)
        return buffer.getvalue()

    def _png_upload(self, name="factura.png", content_type="image/png"):
        return SimpleUploadedFile(name, self._image_bytes("PNG"), content_type=content_type)

    def _jpg_upload(self, name="ticket.jpg", content_type="image/jpeg"):
        return SimpleUploadedFile(name, self._image_bytes("JPEG"), content_type=content_type)

    def _extraction(self, **overrides):
        data = {
            "numero_factura": "F-IMP",
            "fecha_factura": "2026-06-08",
            "fecha_pago": None,
            "nif_proveedor": "B12345678",
            "base": Decimal("100.00"),
            "iva": Decimal("21.00"),
            "igic": Decimal("0.00"),
            "irpf": Decimal("0.00"),
            "total": Decimal("121.00"),
            "concepto": "Servicios importados",
        }
        data.update(overrides)
        return InvoiceExtractionResult(**data)

    def _invoice_form_data(self, pending_import=None, **overrides):
        data = {
            "provider_tax_id": "B12345678",
            "number": "F-IMP",
            "issue_date": "2026-06-08",
            "payment_date": "",
            "concept": "Servicios importados corregidos",
            "taxable_base": "100.00",
            "iva_amount": "21.00",
            "igic_amount": "0.00",
            "irpf_amount": "0.00",
            "total_amount": "121.00",
        }
        if pending_import:
            data["pending_import"] = str(pending_import.token)
        data.update(overrides)
        return data

    def test_tax_id_normalization_preserves_characters_and_handles_spanish_prefix(self):
        self.assertEqual(normalize_tax_id(" es b-123.456 78 "), "B12345678")
        self.assertEqual(normalize_tax_id("ES12345678Z"), "12345678Z")
        self.assertEqual(normalize_tax_id("ES-FOREIGN-12"), "ESFOREIGN12")
        self.assertEqual(normalize_tax_id("OIL-S5B8"), "OILS5B8")

    def test_supplier_similarity_supports_substitution_insertion_deletion_and_transposition(self):
        registered = "B12345678"
        variants = ("B12345679", "B123456789", "B1234567", "B12345768")
        for variant in variants:
            self.assertEqual(damerau_levenshtein_distance(variant, registered), 1)
            self.assertGreaterEqual(jaro_winkler_similarity(variant, registered), 0.90)

    def test_supplier_matching_requires_both_thresholds_and_rejects_distance_over_one(self):
        Supplier.objects.create(name="Proveedor candidato", nif="B12345678")

        accepted = match_suppliers("B12345679", Supplier.objects.all())
        rejected = match_suppliers("B12345990", Supplier.objects.all())

        self.assertEqual([item.name for item in accepted.suggestions], ["Proveedor candidato"])
        self.assertEqual(rejected.suggestions, ())

    @override_settings(INVOICE_SUPPLIER_SUGGESTION_LIMIT=2)
    def test_supplier_suggestions_are_stable_and_limited(self):
        Supplier.objects.bulk_create([
            Supplier(name="Zulu", nif="B12345670"),
            Supplier(name="Alfa", nif="B12345671"),
            Supplier(name="Beta", nif="B12345672"),
        ])

        result = match_suppliers("B12345679", Supplier.objects.all())

        self.assertEqual(len(result.suggestions), 2)
        self.assertEqual([item.name for item in result.suggestions], ["Alfa", "Beta"])

    def test_multiple_normalized_exact_suppliers_are_not_auto_selected(self):
        Supplier.objects.bulk_create([
            Supplier(name="Proveedor A", nif="B12345678"),
            Supplier(name="Proveedor B", nif="B-12345678"),
        ])

        result = match_suppliers("ES B12345678", Supplier.objects.all())

        self.assertIsNone(result.unique_exact)
        self.assertEqual(len(result.exact_matches), 2)
        self.assertEqual(result.suggestions, ())

    @patch("projects.views.extract_invoice_data")
    def test_unique_exact_supplier_is_preselected_with_canonical_tax_id(self, extract_invoice_data):
        supplier = Supplier.objects.create(name="Proveedor exacto", nif="B12345678")
        extract_invoice_data.return_value = self._extraction(nif_proveedor="B12345678")

        response = self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertContains(response, "Se ha identificado el proveedor Proveedor exacto")
        self.assertContains(response, 'id="invoice-supplier-match" role="status"', html=False)
        self.assertContains(response, '<option value="{}" selected>'.format(supplier.pk), html=False)
        self.assertContains(response, 'name="provider_tax_id" value="B12345678"', html=False)

    @patch("projects.views.extract_invoice_data")
    def test_approximate_supplier_requires_user_selection_and_backend_uses_canonical_value(self, extract_invoice_data):
        supplier = Supplier.objects.create(name="Proveedor similar", nif="B12345678")
        extract_invoice_data.return_value = self._extraction(nif_proveedor="B12345679")
        analysis_response = self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})
        pending_import = PendingInvoiceImport.objects.get()

        self.assertEqual(Invoice.objects.count(), 0)
        self.assertContains(analysis_response, 'id="invoice-supplier-match" role="alert"', html=False)
        response = self.client.post(reverse("invoice-save"), self._invoice_form_data(
            pending_import,
            supplier=str(supplier.pk),
            provider_tax_id="NIF-MANIPULADO",
        ))

        self.assertEqual(response.status_code, 200)
        invoice = Invoice.objects.get()
        self.assertEqual(invoice.supplier, supplier)
        self.assertEqual(invoice.provider_tax_id, "B12345678")

    @patch("projects.views.extract_invoice_data")
    def test_reanalyze_uses_pending_document_and_refreshes_review_without_creating_invoice(self, extract_invoice_data):
        extract_invoice_data.side_effect = [
            self._extraction(numero_factura="F-ORIGINAL", nif_proveedor="B38007495"),
            self._extraction(numero_factura="F-REANALIZADA", nif_proveedor="B12345678"),
        ]
        supplier = Supplier.objects.create(name="Proveedor reanalizado", nif="B12345678")
        self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})
        pending_import = PendingInvoiceImport.objects.get()

        response = self.client.post(reverse("invoice-import-reanalyze", args=[pending_import.token]))

        self.assertEqual(response.status_code, 200)
        self.assertEqual(extract_invoice_data.call_count, 2)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertContains(response, 'value="F-REANALIZADA"')
        self.assertContains(response, "Proveedor reanalizado")
        self.assertContains(response, '<option value="{}" selected>'.format(supplier.pk), html=False)
        pending_import.refresh_from_db()
        self.assertEqual(pending_import.status, PendingInvoiceImportStatus.PENDING_REVIEW)
        self.assertEqual(pending_import.extracted_data["numero_factura"], "F-REANALIZADA")

    @patch("projects.views.extract_invoice_data")
    def test_failed_reanalysis_restores_pending_review_state(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction()
        self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})
        pending_import = PendingInvoiceImport.objects.get()
        extract_invoice_data.side_effect = InvoiceExtractionError("OpenAI no respondió.")

        response = self.client.post(reverse("invoice-import-reanalyze", args=[pending_import.token]))

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.count(), 0)
        pending_import.refresh_from_db()
        self.assertEqual(pending_import.status, PendingInvoiceImportStatus.PENDING_REVIEW)

    def test_empty_tax_id_does_not_run_approximate_matching(self):
        Supplier.objects.create(name="Proveedor", nif="B12345678")
        result = match_suppliers(None, Supplier.objects.all())
        self.assertEqual(result.exact_matches, ())
        self.assertEqual(result.suggestions, ())

    def test_invoice_import_camera_controls_are_progressively_enhanced(self):
        response = self.client.get(reverse("invoice-import"))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="invoice-camera-open" hidden')
        self.assertContains(response, "Tomar foto")
        self.assertContains(response, 'id="invoice-camera-video" autoplay playsinline muted')
        self.assertContains(response, "Usar esta foto")
        self.assertContains(response, "Repetir foto")
        self.assertContains(response, 'name="invoice_document"')
        self.assertContains(response, 'typeof navigator.mediaDevices.getUserMedia === "function"')
        self.assertContains(response, 'cameraOpen.prop("hidden", false)')

    def test_invoice_import_redesign_uses_accessible_action_cards_and_disabled_submit(self):
        response = self.client.get(reverse("invoice-import"))
        html = response.content.decode()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'id="invoice-file-open"')
        self.assertContains(response, "Seleccionar archivo")
        self.assertContains(response, "PDF, PNG, JPG o JPEG")
        self.assertContains(response, "Usa la cámara del dispositivo")
        self.assertContains(response, "El documento se analizará de forma segura")
        self.assertContains(response, 'class="project-btn project-btn-primary ajax-form-file invoice-import-submit"', html=False)
        self.assertIn('disabled aria-disabled="true"', html)
        self.assertIn('fileChoice.off("click.invoiceImport").on("click.invoiceImport", function(){ input.trigger("click"); })', html)
        self.assertIn('setSubmitEnabled(true)', html)
        self.assertIn('input.val("")', html)
        self.assertIn('setSelectedMethod("camera")', html)
        self.assertIn('setSelectedMethod("file")', html)

    def test_invoice_import_camera_requests_environment_camera_only_on_click(self):
        response = self.client.get(reverse("invoice-import"))
        html = response.content.decode()

        open_function = html.index("function openCamera()")
        media_request = html.index("navigator.mediaDevices.getUserMedia({")
        click_binding = html.index('cameraOpen.off("click.invoiceCamera").on("click.invoiceCamera", openCamera)')
        self.assertGreater(media_request, open_function)
        self.assertGreater(click_binding, media_request)
        self.assertIn('facingMode: { ideal: "environment" }', html)
        self.assertIn("audio: false", html)

    def test_invoice_import_camera_creates_jpeg_in_existing_field_and_cleans_up(self):
        response = self.client.get(reverse("invoice-import"))
        html = response.content.decode()

        self.assertIn('canvas.width = width', html)
        self.assertIn('canvas.height = height', html)
        self.assertIn('}, "image/jpeg", 0.92)', html)
        self.assertIn('new File([capturedBlob], filename, { type: "image/jpeg"', html)
        self.assertIn("transfer.items.add(capturedFile)", html)
        self.assertIn("input[0].files = transfer.files", html)
        self.assertIn("validateClientFile(capturedFile)", html)
        self.assertIn("cameraStream.getTracks().forEach(function(track){ track.stop(); })", html)
        self.assertIn('hidden.bs.modal.invoiceCamera', html)
        self.assertIn('pagehide.invoiceCamera beforeunload.invoiceCamera', html)
        self.assertIn('error.name === "NotAllowedError"', html)
        self.assertIn('error.name === "NotFoundError"', html)
        self.assertIn('error.name === "NotReadableError"', html)
        self.assertIn('error.name === "OverconstrainedError"', html)

    def test_invoice_import_rejects_invalid_extension(self):
        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": SimpleUploadedFile("factura.txt", b"texto", content_type="text/plain"),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "El archivo debe tener extensión PDF, PNG, JPG o JPEG", status_code=400)

    def test_invoice_import_rejects_browser_mime_not_allowed(self):
        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": self._pdf_upload(content_type="text/plain"),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "El tipo MIME del archivo no está permitido.", status_code=400)

    def test_invoice_import_rejects_mismatched_real_content(self):
        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": SimpleUploadedFile("factura.png", b"%PDF-1.4\n%%EOF\n", content_type="image/png"),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "La extensión del archivo no coincide con su contenido real.", status_code=400)

    def test_invoice_import_rejects_empty_file(self):
        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": SimpleUploadedFile("factura.pdf", b"", content_type="application/pdf"),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "El archivo está vacío.", status_code=400)

    def test_invoice_import_rejects_damaged_file(self):
        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": SimpleUploadedFile("ticket.jpg", b"\xff\xd8\xff datos rotos", content_type="image/jpeg"),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "La imagen no se puede leer o está dañada.", status_code=400)

    @override_settings(INVOICE_IMPORT_MAX_DOCUMENT_SIZE=8)
    def test_invoice_import_rejects_too_large_file(self):
        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": self._pdf_upload(),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "El archivo supera el tamaño máximo permitido", status_code=400)

    def test_validate_invoice_amounts_accepts_iva_invoice(self):
        validation = validate_invoice_amounts(self._extraction())

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["expected_total"], Decimal("121.00"))
        self.assertEqual(validation["declared_total"], Decimal("121.00"))

    def test_validate_invoice_amounts_accepts_irpf_invoice(self):
        validation = validate_invoice_amounts(self._extraction(irpf=Decimal("15.00"), total=Decimal("106.00")))

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["expected_total"], Decimal("106.00"))

    def test_validate_invoice_amounts_accepts_igic_invoice(self):
        validation = validate_invoice_amounts(self._extraction(iva=Decimal("0.00"), igic=Decimal("7.00"), total=Decimal("107.00")))

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["expected_total"], Decimal("107.00"))

    def test_validate_invoice_amounts_allows_rounding_tolerance(self):
        validation = validate_invoice_amounts(self._extraction(total=Decimal("121.01")))

        self.assertTrue(validation["valid"])
        self.assertEqual(validation["difference"], Decimal("-0.01"))

    @patch("projects.views.extract_invoice_data")
    def test_invoice_analysis_opens_prefilled_form_without_creating_invoice(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction()

        response = self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Invoice.objects.count(), 0)
        pending_import = PendingInvoiceImport.objects.get()
        self.assertEqual(pending_import.owner, self.user)
        self.assertEqual(pending_import.status, PendingInvoiceImportStatus.PENDING_REVIEW)
        self.assertContains(response, "Hemos completado el formulario")
        self.assertContains(response, 'name="pending_import" value="{}"'.format(pending_import.token))
        self.assertContains(response, 'value="F-IMP"')
        self.assertContains(response, 'value="2026-06-08"')
        self.assertContains(response, 'value="100.00"')

    @patch("projects.views.extract_invoice_data")
    def test_invoice_analysis_leaves_unidentified_fields_empty(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction(
            fecha_pago=None, igic=None, iva=None, irpf=None, concepto=None
        )

        response = self.client.post(reverse("invoice-import"), {"invoice_document": self._png_upload()})

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertContains(response, 'name="iva_amount"', html=False)
        self.assertNotContains(response, 'name="iva_amount" value="0.00"', html=False)
        self.assertContains(response, "Los importes detectados no cuadran")

    @patch("projects.views.extract_invoice_data")
    def test_invoice_review_can_be_corrected_and_saves_original_document(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction(concepto="Texto automático")
        self.client.post(reverse("invoice-import"), {"invoice_document": self._jpg_upload(name="ticket.jpeg")})
        pending_import = PendingInvoiceImport.objects.get()

        response = self.client.post(reverse("invoice-save"), self._invoice_form_data(
            pending_import,
            concept="Texto revisado por el usuario",
        ))

        self.assertEqual(response.status_code, 200)
        invoice = Invoice.objects.get(number="F-IMP")
        self.assertEqual(invoice.concept, "Texto revisado por el usuario")
        self.assertTrue(invoice.physical_document.name.endswith(".jpeg"))
        pending_import.refresh_from_db()
        self.assertEqual(pending_import.status, PendingInvoiceImportStatus.COMPLETED)
        self.assertEqual(pending_import.invoice, invoice)

    @patch("projects.views.extract_invoice_data")
    def test_incongruent_analysis_opens_review_but_cannot_be_saved_until_corrected(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction(total=Decimal("150.00"))
        response = self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})
        pending_import = PendingInvoiceImport.objects.get()

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "no son congruentes")
        invalid = self.client.post(reverse("invoice-save"), self._invoice_form_data(
            pending_import, total_amount="150.00"
        ))
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(Invoice.objects.count(), 0)
        self.assertContains(invalid, "El total no coincide", status_code=400)

        corrected = self.client.post(reverse("invoice-save"), self._invoice_form_data(pending_import))
        self.assertEqual(corrected.status_code, 200)
        self.assertEqual(Invoice.objects.count(), 1)

    @patch("projects.views.extract_invoice_data")
    def test_pending_import_is_private_and_cannot_be_reused(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction()
        self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})
        pending_import = PendingInvoiceImport.objects.get()
        other_user = User.objects.create_superuser("other-invoice-user", "other@example.com", "test")
        self.client.force_login(other_user)

        preview = self.client.get(reverse("pending-invoice-document", args=[pending_import.token]))
        confirm = self.client.post(reverse("invoice-save"), self._invoice_form_data(pending_import))
        self.assertEqual(preview.status_code, 404)
        self.assertEqual(confirm.status_code, 409)
        self.assertEqual(Invoice.objects.count(), 0)

        self.client.force_login(self.user)
        first = self.client.post(reverse("invoice-save"), self._invoice_form_data(pending_import))
        second = self.client.post(reverse("invoice-save"), self._invoice_form_data(pending_import))
        self.assertEqual(first.status_code, 200)
        self.assertEqual(second.status_code, 400)
        self.assertEqual(Invoice.objects.count(), 1)

    @patch("projects.views.extract_invoice_data")
    def test_expired_pending_import_is_rejected_and_cleanup_removes_it(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction()
        self.client.post(reverse("invoice-import"), {"invoice_document": self._pdf_upload()})
        pending_import = PendingInvoiceImport.objects.get()
        PendingInvoiceImport.objects.filter(pk=pending_import.pk).update(expires_at=timezone.now() - timedelta(minutes=1))

        preview = self.client.get(reverse("pending-invoice-document", args=[pending_import.token]))
        save = self.client.post(reverse("invoice-save"), self._invoice_form_data(pending_import))
        self.assertEqual(preview.status_code, 404)
        self.assertEqual(save.status_code, 409)

        call_command("cleanup_pending_invoice_imports")
        self.assertFalse(PendingInvoiceImport.objects.filter(pk=pending_import.pk).exists())

    def test_invoice_extraction_parses_optional_payment_date_absent(self):
        result = parse_invoice_extraction_payload({
            "numero_factura": "T-001",
            "fecha_factura": "2026-06-08",
            "fecha_pago": None,
            "nif_proveedor": " b12345678 ",
            "base": 10,
            "igic": 0,
            "iva": 0,
            "irpf": 0,
            "total": 10,
            "concepto": "Ticket",
        })

        self.assertIsNone(result.fecha_pago)
        self.assertEqual(result.nif_proveedor, "B12345678")
        self.assertEqual(result.total, Decimal("10.00"))

    @patch("projects.views.extract_invoice_data")
    def test_invoice_import_opens_empty_review_for_unidentified_document(self, extract_invoice_data):
        extract_invoice_data.return_value = self._extraction(
            numero_factura=None,
            fecha_factura=None,
            nif_proveedor=None,
            concepto=None,
            base=None,
            total=None,
        )

        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": self._png_upload(),
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "Nueva factura")
        self.assertContains(response, "Los importes detectados no cuadran")

    @patch("projects.views.extract_invoice_data")
    def test_invoice_import_handles_openai_error(self, extract_invoice_data):
        extract_invoice_data.side_effect = InvoiceExtractionError("No se ha podido analizar la factura.")

        response = self.client.post(reverse("invoice-import"), {
            "invoice_document": self._pdf_upload(),
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(Invoice.objects.filter(number="F-IMP").count(), 0)
        self.assertContains(response, "No se ha podido analizar la factura.", status_code=400)
        self.assertEqual(PendingInvoiceImport.objects.get().status, PendingInvoiceImportStatus.FAILED)

    def test_invoice_openai_content_uses_input_file_for_pdf(self):
        content = build_invoice_openai_content(self._pdf_upload(), "application/pdf")

        self.assertEqual(content[1]["type"], "input_file")
        self.assertTrue(content[1]["file_data"].startswith("data:application/pdf;base64,"))
        self.assertIn("filename", content[1])

    def test_invoice_openai_content_uses_input_image_for_png_and_jpeg(self):
        png_content = build_invoice_openai_content(self._png_upload(), "image/png")
        jpeg_content = build_invoice_openai_content(self._jpg_upload(), "image/jpeg")

        self.assertEqual(png_content[1]["type"], "input_image")
        self.assertTrue(png_content[1]["image_url"].startswith("data:image/png;base64,"))
        self.assertEqual(jpeg_content[1]["type"], "input_image")
        self.assertTrue(jpeg_content[1]["image_url"].startswith("data:image/jpeg;base64,"))


class ProjectPaymentTreasuryTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_superuser(username="payments-admin", email="payments@example.com", password="test")
        self.project = Project.objects.create(
            code="PAY",
            name="Proyecto pagos",
            manager=self.user,
            status="active",
            approved_budget=Decimal("10000.00"),
        )
        self.budget_line = BudgetLine.objects.create(
            project=self.project,
            code="1",
            name="Tesorería",
            approved_budget=Decimal("10000.00"),
        )
        self.financier = Financier.objects.create(name="Financiador pagos")
        self.client.force_login(self.user)

    def create_obligation(self, **overrides):
        data = {
            "concept": "Obligación de prueba",
            "payment_type": PaymentObligationType.SUPPLIER,
            "creditor": "Acreedor de prueba",
            "expected_payment_date": timezone.localdate() + timedelta(days=10),
            "amount": Decimal("100.00"),
            "status": PaymentObligationStatus.PENDING,
            "project": self.project,
            "financier": self.financier,
            "budget_line": self.budget_line,
        }
        data.update(overrides)
        return PaymentObligation.objects.create(**data)

    def test_payment_obligation_initial_amounts_are_derived(self):
        obligation = self.create_obligation()

        self.assertEqual(obligation.amount_paid, Decimal("0.00"))
        self.assertEqual(obligation.amount_pending, Decimal("100.00"))
        self.assertEqual(obligation.financial_state, PaymentFinancialState.UNPAID)

    def test_cash_outflow_partial_and_remaining_payment_update_derived_balances(self):
        obligation = self.create_obligation()
        CashOutflow.objects.create(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("40.00"),
            payment_method="transfer",
        )

        self.assertEqual(obligation.amount_paid, Decimal("40.00"))
        self.assertEqual(obligation.amount_pending, Decimal("60.00"))
        self.assertEqual(obligation.financial_state, PaymentFinancialState.PARTIALLY_PAID)

        CashOutflow.objects.create(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("60.00"),
            payment_method="transfer",
        )

        self.assertEqual(obligation.amount_paid, Decimal("100.00"))
        self.assertEqual(obligation.amount_pending, Decimal("0.00"))
        self.assertEqual(obligation.financial_state, PaymentFinancialState.PAID)
        self.assertEqual(obligation.display_state["code"], "paid")

    def test_cash_outflow_rejects_amount_over_remaining_balance(self):
        obligation = self.create_obligation()
        CashOutflow.objects.create(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("80.00"),
            payment_method="transfer",
        )
        outflow = CashOutflow(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("30.00"),
            payment_method="transfer",
        )

        with self.assertRaises(ValidationError):
            outflow.full_clean()

    def test_cash_outflow_rejects_cancelled_obligation(self):
        obligation = self.create_obligation(status=PaymentObligationStatus.CANCELLED)
        outflow = CashOutflow(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("10.00"),
            payment_method="transfer",
        )

        with self.assertRaises(ValidationError):
            outflow.full_clean()

    def test_obligation_cannot_be_reduced_below_paid_amount(self):
        obligation = self.create_obligation(amount=Decimal("100.00"))
        CashOutflow.objects.create(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("70.00"),
            payment_method="transfer",
        )
        obligation.amount = Decimal("60.00")

        with self.assertRaises(ValidationError):
            obligation.full_clean()

    def test_obligation_with_payments_cannot_be_cancelled(self):
        obligation = self.create_obligation()
        CashOutflow.objects.create(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("10.00"),
            payment_method="transfer",
        )
        obligation.status = PaymentObligationStatus.CANCELLED

        with self.assertRaises(ValidationError):
            obligation.full_clean()

    def test_cash_outflow_cannot_be_deleted_normally(self):
        obligation = self.create_obligation()
        outflow = CashOutflow.objects.create(
            payment_obligation=obligation,
            payment_date=timezone.localdate(),
            amount=Decimal("10.00"),
            payment_method="transfer",
        )

        with self.assertRaises(ValidationError):
            outflow.delete()

    def test_overdue_is_derived_dynamically(self):
        obligation = self.create_obligation(expected_payment_date=timezone.localdate() - timedelta(days=1))

        self.assertTrue(obligation.is_overdue)
        self.assertEqual(obligation.display_state["code"], "overdue")

    def test_payment_list_and_detail_are_accessible(self):
        obligation = self.create_obligation()

        response = self.client.get(reverse("payment-list"))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Pagos y Tesorería")
        self.assertContains(response, "Obligación de prueba")

        response = self.client.get(reverse("payment-detail"), {"obj_id": obligation.id})
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Estado financiero")

    def test_cash_outflow_save_uses_remaining_balance(self):
        obligation = self.create_obligation(amount=Decimal("100.00"))

        response = self.client.get(reverse("cash-outflow-save"), {
            "payment_obligation_id": obligation.id,
            "payment_date": timezone.localdate().isoformat(),
            "amount": "40.00",
            "payment_method": "transfer",
            "bank_account": "ES00",
            "reference": "TR-1",
        })

        self.assertEqual(response.status_code, 200)
        obligation.refresh_from_db()
        self.assertEqual(obligation.amount_paid, Decimal("40.00"))

        response = self.client.get(reverse("cash-outflow-save"), {
            "payment_obligation_id": obligation.id,
            "payment_date": timezone.localdate().isoformat(),
            "amount": "70.00",
            "payment_method": "transfer",
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(obligation.cash_outflows.count(), 1)
