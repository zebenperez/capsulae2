from django.contrib import admin

from .models import (
    Activity,
    ActivityUser,
    BudgetLine,
    Expense,
    File,
    Financier,
    FinancierContribution,
    Folder,
    Income,
    Indicator,
    Invoice,
    InvoiceAllocation,
    InvoiceDocument,
    Objective,
    Project,
    ProjectFinancier,
    Result,
    Text,
)


class ObjectiveInline(admin.TabularInline):
    model = Objective
    extra = 0
    fields = ("code", "name", "objective_type", "status", "progress_percentage")


class BudgetLineInline(admin.TabularInline):
    model = BudgetLine
    extra = 0
    fields = ("parent", "code", "name", "approved_budget", "modified_budget")


class ProjectFinancierInline(admin.TabularInline):
    model = ProjectFinancier
    extra = 0
    autocomplete_fields = ("financier",)
    fields = ("financier", "committed_amount", "granted_amount", "disbursed_amount", "agreement_date")


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "status", "country", "approved_budget", "executed_budget", "manager")
    list_filter = ("status", "country", "start_date", "finish_date")
    search_fields = ("code", "name", "country", "region", "locality")
    autocomplete_fields = ("manager", "technical_manager", "financial_manager")
    readonly_fields = ("executed_budget", "execution_percentage", "completed_activities_count")
    inlines = (ObjectiveInline, BudgetLineInline, ProjectFinancierInline)


class IndicatorInline(admin.TabularInline):
    model = Indicator
    extra = 0
    autocomplete_fields = ("responsible",)
    readonly_fields = ("compliance_percentage",)


class ActivityInline(admin.TabularInline):
    model = Activity
    extra = 0
    fields = ("code", "name", "responsible", "status", "progress_percentage")
    autocomplete_fields = ("responsible",)


class ResultInline(admin.TabularInline):
    model = Result
    extra = 0
    fields = ("description", "status", "compliance_percentage")


@admin.register(Objective)
class ObjectiveAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "project", "objective_type", "status", "progress_percentage")
    list_filter = ("objective_type", "status", "project")
    search_fields = ("code", "name", "description", "project__name", "project__code")
    autocomplete_fields = ("project",)
    inlines = (IndicatorInline, ActivityInline, ResultInline)


@admin.register(Indicator)
class IndicatorAdmin(admin.ModelAdmin):
    list_display = ("name", "objective", "target", "current_value", "unit", "compliance_percentage", "last_update")
    list_filter = ("unit", "measurement_frequency", "last_update")
    search_fields = ("name", "description", "objective__name", "objective__project__name")
    autocomplete_fields = ("objective", "responsible")
    readonly_fields = ("compliance_percentage",)


@admin.register(Activity)
class ActivityAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "project", "objective", "responsible", "status", "progress_percentage")
    list_filter = ("status", "project", "planned_start_date", "planned_end_date")
    search_fields = ("code", "name", "desc", "project__name", "objective__name")
    autocomplete_fields = ("project", "objective", "responsible")


@admin.register(Result)
class ResultAdmin(admin.ModelAdmin):
    list_display = ("objective", "status", "compliance_percentage", "description")
    list_filter = ("status", "objective__project")
    search_fields = ("description", "expected_result", "obtained_result", "objective__name")
    autocomplete_fields = ("objective",)


@admin.register(BudgetLine)
class BudgetLineAdmin(admin.ModelAdmin):
    list_display = ("full_code", "name", "project", "parent", "approved_budget", "modified_budget", "executed_amount", "available_balance")
    list_filter = ("project",)
    search_fields = ("code", "name", "description", "project__name", "project__code", "parent__name")
    autocomplete_fields = ("project", "parent")
    readonly_fields = ("executed_amount", "available_balance")


@admin.register(Financier)
class FinancierAdmin(admin.ModelAdmin):
    list_display = ("name", "financier_type", "tax_id", "contact_person", "email", "phone")
    list_filter = ("financier_type",)
    search_fields = ("name", "tax_id", "contact_person", "email")


@admin.register(ProjectFinancier)
class ProjectFinancierAdmin(admin.ModelAdmin):
    list_display = ("project", "financier", "committed_amount", "granted_amount", "disbursed_amount", "available_amount")
    list_filter = ("project", "financier__financier_type")
    search_fields = ("project__name", "project__code", "financier__name", "financier__tax_id")
    autocomplete_fields = ("project", "financier")
    readonly_fields = ("allocated_amount", "available_amount")


@admin.register(FinancierContribution)
class FinancierContributionAdmin(admin.ModelAdmin):
    list_display = ("project", "financier", "budget_line", "sub_budget_line", "amount", "percentage", "available_amount")
    list_filter = ("project", "financier")
    search_fields = ("project__name", "financier__name", "budget_line__name", "sub_budget_line__name")
    autocomplete_fields = ("project", "financier", "budget_line", "sub_budget_line")
    readonly_fields = ("allocated_to_invoices", "available_amount")


class InvoiceDocumentInline(admin.TabularInline):
    model = InvoiceDocument
    extra = 0


class InvoiceAllocationInline(admin.TabularInline):
    model = InvoiceAllocation
    extra = 0
    autocomplete_fields = ("project", "activity", "budget_line", "sub_budget_line", "financier")


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = ("number", "provider", "project", "activity", "issue_date", "total_amount", "allocated_amount", "status")
    list_filter = ("status", "currency", "issue_date", "payment_date", "project")
    search_fields = ("number", "provider", "concept", "project__name", "activity__name")
    autocomplete_fields = ("project", "activity")
    readonly_fields = ("allocated_amount", "pending_amount")
    inlines = (InvoiceDocumentInline, InvoiceAllocationInline)


@admin.register(InvoiceAllocation)
class InvoiceAllocationAdmin(admin.ModelAdmin):
    list_display = ("invoice", "project", "activity", "sub_budget_line", "financier", "allocated_amount", "allocated_percentage")
    list_filter = ("project", "financier", "allocation_date")
    search_fields = ("invoice__number", "invoice__provider", "activity__name", "sub_budget_line__name", "financier__name")
    autocomplete_fields = ("invoice", "project", "activity", "budget_line", "sub_budget_line", "financier")


admin.site.register(InvoiceDocument)
admin.site.register(Text)
admin.site.register(ActivityUser)
admin.site.register(Income)
admin.site.register(Expense)
admin.site.register(Folder)
admin.site.register(File)
