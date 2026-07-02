from datetime import date
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.test import TestCase

from .models import (
    Activity,
    BudgetLine,
    Financier,
    FinancierContribution,
    FinancierType,
    Indicator,
    Invoice,
    InvoiceAllocation,
    Objective,
    ObjectiveType,
    Project,
    ProjectFinancier,
    ProgressStatus,
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
            project=self.project,
            activity=self.activity,
            provider="Proveedor SL",
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

    def test_cross_project_activity_is_rejected(self):
        other_project = Project.objects.create(code="OTHER", name="Otro", approved_budget=Decimal("100.00"))
        invoice = Invoice(
            project=other_project,
            activity=self.activity,
            provider="Proveedor SL",
            number="F-002",
            issue_date=date(2026, 2, 1),
            concept="Servicios",
            taxable_base=Decimal("10.00"),
            taxes=Decimal("0.00"),
            total_amount=Decimal("10.00"),
        )
        with self.assertRaises(ValidationError):
            invoice.full_clean()

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
