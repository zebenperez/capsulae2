import calendar
from decimal import Decimal
from django.utils import timezone

from django import forms
from django.core.exceptions import ValidationError

from projects.services.invoice_documents import (
    INVOICE_DOCUMENT_ACCEPT,
    INVOICE_DOCUMENT_HELP_TEXT,
    validate_invoice_document,
)
from projects.services.invoice_import import get_amount_tolerance
from projects.services.supplier_matching import normalize_tax_id


class InvoiceFilterForm(forms.Form):
    invoice_q = forms.CharField(label="Buscar", required=False)
    invoice_from = forms.DateField(label="Desde", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    invoice_to = forms.DateField(label="Hasta", required=False, widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"))
    invoice_status = forms.ChoiceField(label="Estado", required=False)
    invoice_min = forms.DecimalField(label="Importe mínimo", required=False, min_value=0, max_digits=14, decimal_places=2)

    def __init__(self, params=None):
        from .models import InvoiceStatus
        today = timezone.localdate()
        start_year, start_month = divmod(today.year * 12 + today.month - 1 - 6, 12)
        start_date = today.replace(year=start_year, month=start_month + 1, day=1)
        values = {"invoice_from": start_date.isoformat(), "invoice_to": today.replace(day=calendar.monthrange(today.year, today.month)[1]).isoformat(), "invoice_min": "0"}
        if params is not None:
            values.update({key: params.get(key) for key in self.base_fields if key in params})
        super().__init__(data=values)
        self.fields["invoice_status"].choices = [("", "Todos")] + list(InvoiceStatus.choices)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
        self.fields["invoice_q"].widget.attrs["placeholder"] = "Factura, localizador, código o proveedor"

    def clean(self):
        data = super().clean()
        if data.get("invoice_from") and data.get("invoice_to") and data["invoice_from"] > data["invoice_to"]:
            raise forms.ValidationError("La fecha inicial no puede ser posterior a la fecha final.")
        return data

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
    Supplier,
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
            "supplier",
            "provider_tax_id",
            "number",
            "issue_date",
            "payment_date",
            "concept",
            "taxable_base",
            "iva_amount",
            "igic_amount",
            "irpf_amount",
            "total_amount",
        )
        widgets = {
            "issue_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "payment_date": forms.DateInput(attrs={"type": "date", "class": "form-control"}, format="%Y-%m-%d"),
            "concept": forms.Textarea(attrs={"class": "form-control"}),
        }

    def __init__(self, *args, **kwargs):
        self.user = kwargs.pop("user", None)
        super().__init__(*args, **kwargs)
        self.fields["supplier"].queryset = Supplier.objects.only("id", "name", "nif").order_by("name", "id")
        self.fields["supplier"].required = False
        self.fields["supplier"].empty_label = "Seleccionar proveedor manualmente"
        for name, field in self.fields.items():
            field.widget.attrs.setdefault("class", "form-control")
            if name in ("taxable_base", "iva_amount", "igic_amount", "irpf_amount", "total_amount"):
                field.widget.attrs.update({"step": "0.01", "min": "0"})
            if name in ("taxable_base", "iva_amount", "igic_amount", "irpf_amount"):
                field.widget.attrs["class"] += " invoice-amount"
            if name == "total_amount":
                field.widget.attrs["class"] += " invoice-total"

    def clean(self):
        cleaned_data = super().clean()
        amount_fields = ("taxable_base", "iva_amount", "igic_amount", "irpf_amount", "total_amount")
        if any(cleaned_data.get(field) is None for field in amount_fields):
            return cleaned_data

        expected_total = (
            cleaned_data["taxable_base"]
            + cleaned_data["iva_amount"]
            + cleaned_data["igic_amount"]
            - cleaned_data["irpf_amount"]
        ).quantize(Decimal("0.01"))
        declared_total = cleaned_data["total_amount"].quantize(Decimal("0.01"))
        if abs(expected_total - declared_total) > get_amount_tolerance():
            message = "El total no coincide con la base, los impuestos y la retención. Revisa los importes."
            self.add_error("total_amount", message)
            self.add_error("taxable_base", "Revisa este importe.")
            self.add_error("iva_amount", "Revisa este importe.")
            self.add_error("igic_amount", "Revisa este importe.")
            self.add_error("irpf_amount", "Revisa este importe.")

        provider_tax_id = normalize_tax_id(cleaned_data.get("provider_tax_id"))
        cleaned_data["provider_tax_id"] = provider_tax_id
        supplier = cleaned_data.get("supplier")
        if supplier is not None:
            provider_tax_id = supplier.nif
            cleaned_data["provider_tax_id"] = supplier.nif
        number = (cleaned_data.get("number") or "").strip()
        duplicate = Invoice.objects.filter(provider_tax_id__iexact=provider_tax_id, number=number)
        if self.instance.pk:
            duplicate = duplicate.exclude(pk=self.instance.pk)
        if provider_tax_id and number and duplicate.exists():
            self.add_error("number", "Ya existe una factura de este proveedor con el mismo número.")
        return cleaned_data

    def save(self, commit=True):
        invoice = super().save(commit=False)
        invoice.provider_tax_id = normalize_tax_id(invoice.provider_tax_id)
        invoice.taxes = invoice.iva_amount + invoice.igic_amount - invoice.irpf_amount
        if commit:
            invoice.save()
            self.save_m2m()
        return invoice


class InvoiceImportForm(forms.Form):
    invoice_document = forms.FileField(
        label="Factura o ticket",
        help_text=INVOICE_DOCUMENT_HELP_TEXT,
        allow_empty_file=True,
        widget=forms.ClearableFileInput(attrs={
            "accept": INVOICE_DOCUMENT_ACCEPT,
        }),
    )

    def clean_invoice_document(self):
        uploaded_file = self.cleaned_data["invoice_document"]
        try:
            return validate_invoice_document(uploaded_file)
        except ValidationError as exc:
            raise forms.ValidationError(exc.messages)


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
