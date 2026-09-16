import os

from django import forms
from django.conf import settings

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
        fields = ("project", "code", "name", "description", "approved_budget")


class ChildBudgetLineForm(forms.ModelForm):
    class Meta:
        model = BudgetLine
        fields = ("project", "parent", "code", "name", "description", "approved_budget")


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
        fields = ("project", "financier", "budget_line", "amount", "percentage", "notes")


class InvoiceForm(forms.ModelForm):
    class Meta:
        model = Invoice
        fields = (
            "provider_tax_id",
            "number",
            "issue_date",
            "payment_date",
            "concept",
            "taxable_base",
            "taxes",
            "iva_amount",
            "igic_amount",
            "irpf_amount",
            "currency",
            "document_pdf",
            "status",
            "notes",
        )


class InvoiceImportForm(forms.Form):
    invoice_pdf = forms.FileField(label="Factura PDF")

    def clean_invoice_pdf(self):
        uploaded_file = self.cleaned_data["invoice_pdf"]
        max_size = int(getattr(settings, "INVOICE_IMPORT_MAX_PDF_SIZE", os.getenv("INVOICE_IMPORT_MAX_PDF_SIZE", 10 * 1024 * 1024)))
        filename = uploaded_file.name or ""
        extension = os.path.splitext(filename)[1].lower()
        if extension != ".pdf":
            raise forms.ValidationError("El archivo debe tener extensión PDF.")
        if uploaded_file.content_type != "application/pdf":
            raise forms.ValidationError("El archivo debe tener tipo MIME application/pdf.")
        if uploaded_file.size > max_size:
            raise forms.ValidationError("El archivo supera el tamaño máximo permitido.")

        uploaded_file.seek(0)
        signature = uploaded_file.read(5)
        uploaded_file.seek(0)
        if signature != b"%PDF-":
            raise forms.ValidationError("El archivo no parece ser un PDF válido.")
        return uploaded_file


class InvoiceAllocationForm(forms.ModelForm):
    class Meta:
        model = InvoiceAllocation
        fields = (
            "invoice",
            "project",
            "activity",
            "budget_line",
            "allocated_amount",
            "allocated_percentage",
            "allocation_date",
            "notes",
        )
