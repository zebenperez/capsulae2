from django import forms

from .models import (
    Activity,
    BudgetLine,
    Financier,
    FinancierContribution,
    Indicator,
    Invoice,
    InvoiceAllocation,
    Objective,
    Project,
    ProjectFinancier,
    Result,
)


class ProjectForm(forms.ModelForm):
    class Meta:
        model = Project
        fields = (
            "code",
            "name",
            "desc",
            "status",
            "start_date",
            "finish_date",
            "country",
            "region",
            "locality",
            "technical_manager",
            "financial_manager",
            "approved_budget",
            "notes",
        )


class ObjectiveForm(forms.ModelForm):
    class Meta:
        model = Objective
        fields = ("project", "code", "name", "description", "objective_type", "status", "progress_percentage", "notes")


class IndicatorForm(forms.ModelForm):
    class Meta:
        model = Indicator
        fields = (
            "objective",
            "name",
            "description",
            "baseline",
            "target",
            "current_value",
            "unit",
            "measurement_frequency",
            "verification_source",
            "responsible",
            "last_update",
        )


class ActivityForm(forms.ModelForm):
    class Meta:
        model = Activity
        fields = (
            "project",
            "objective",
            "code",
            "name",
            "desc",
            "responsible",
            "location",
            "planned_start_date",
            "planned_end_date",
            "real_start_date",
            "real_end_date",
            "status",
            "progress_percentage",
        )


class ResultForm(forms.ModelForm):
    class Meta:
        model = Result
        fields = ("objective", "description", "expected_result", "obtained_result", "evidence", "compliance_percentage", "status")


class BudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ("project", "code", "name", "description", "approved_budget", "modified_budget")


class ChildBudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ("project", "parent", "code", "name", "description", "approved_budget", "modified_budget")


class FinancierForm(forms.ModelForm):
    class Meta:
        model = Financier
        fields = ("name", "financier_type", "tax_id", "address", "contact_person", "email", "phone", "notes")


class ProjectFinancierForm(forms.ModelForm):
    class Meta:
        model = ProjectFinancier
        fields = (
            "project",
            "financier",
            "committed_amount",
            "granted_amount",
            "disbursed_amount",
            "agreement_date",
            "agreement_document",
        )


class FinancierContributionForm(forms.ModelForm):
    class Meta:
        model = FinancierContribution
        fields = ("project", "financier", "budget_line", "sub_budget_line", "amount", "percentage", "notes")


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = (
            "project",
            "activity",
            "provider",
            "number",
            "issue_date",
            "payment_date",
            "concept",
            "taxable_base",
            "taxes",
            "total_amount",
            "currency",
            "document_pdf",
            "status",
            "notes",
        )


class InvoiceAllocationForm(forms.ModelForm):
    class Meta:
        model = InvoiceAllocation
        fields = (
            "invoice",
            "project",
            "activity",
            "budget_line",
            "sub_budget_line",
            "financier",
            "allocated_amount",
            "allocated_percentage",
            "allocation_date",
            "notes",
        )
