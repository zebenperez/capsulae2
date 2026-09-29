from django import forms
from django.core.validators import FileExtensionValidator

from .models import CashOutflow, PaymentObligation, PaymentObligationAllocation


class PaymentObligationForm(forms.ModelForm):
    document = forms.FileField(label="Documento", required=False, validators=[
        FileExtensionValidator(allowed_extensions=[
            "pdf", "jpg", "jpeg", "png", "gif", "webp", "bmp", "tif", "tiff",
            "xls", "xlsx", "ods", "csv", "tsv",
        ])
    ])

    def clean_document(self):
        document = self.cleaned_data.get("document")
        if document and document.size > 20 * 1024 * 1024:
            raise forms.ValidationError("El documento no puede superar los 20 MB.")
        if document and not document.size:
            raise forms.ValidationError("El documento está vacío.")
        return document

    class Meta:
        model = PaymentObligation
        fields = (
            "concept",
            "payment_type",
            "creditor",
            "invoice",
            "accrual_date",
            "expected_payment_date",
            "amount",
            "status",
            "notes",
        )
        widgets = {
            "accrual_date": forms.DateInput(attrs={"type": "date"}),
            "expected_payment_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 4}),
        }


class CashOutflowForm(forms.ModelForm):
    class Meta:
        model = CashOutflow
        fields = (
            "payment_date",
            "amount",
            "bank_account",
            "payment_method",
            "reference",
            "notes",
        )
        widgets = {
            "payment_date": forms.DateInput(attrs={"type": "date"}),
            "notes": forms.Textarea(attrs={"rows": 3}),
        }
class PaymentAllocationEditForm(forms.ModelForm):
    class Meta:
        model = PaymentObligationAllocation
        fields = ("budget_line", "allocated_amount", "notes")
        labels = {"budget_line": "Partida", "allocated_amount": "Importe", "notes": "Notas"}
        widgets = {"notes": forms.Textarea(attrs={"rows": 3})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["budget_line"].queryset = self.instance.project.budget_lines.filter(child_lines__isnull=True)
        for field in self.fields.values():
            field.widget.attrs["class"] = "form-control"
