from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
import logging
import os
import uuid
from urllib.parse import urlencode

from django.contrib.auth.models import User
from django.core.paginator import Paginator
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models.deletion import ProtectedError
from django.db.models import Count, DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import FileResponse, HttpResponse, JsonResponse
from django.shortcuts import render, redirect, reverse
from django.utils import timezone
from django.views.decorators.clickjacking import xframe_options_exempt

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, validate_captcha
from .forms import InvoiceForm, InvoiceImportForm
from .models import (
    Activity,
    ActivityUser,
    BudgetLine,
    Expense,
    Financier,
    FinancierContribution,
    FinancierType,
    Indicator,
    Income,
    Invoice,
    InvoiceAllocation,
    PaymentObligationAllocation,
    InvoiceStatus,
    InvoiceStatusChange,
    File,
    Folder,
    money_sum,
    Project,
    ProjectFinancier,
    ProjectStatus,
    ProgressStatus,
    Supplier,
    Text,
)
from .services.invoice_ai import InvoiceExtractionError, extract_invoice_data
from .services.invoice_documents import (
    ALLOWED_INVOICE_DOCUMENT_TYPES,
    detect_invoice_document_mime,
    validate_invoice_document,
)
from .services.supplier_matching import match_suppliers, normalize_tax_id
from .services.invoice_import import (
    InvoiceImportError,
    PendingInvoiceImportUnavailable,
    begin_pending_reanalysis,
    complete_pending_import,
    create_pending_import,
    deserialize_extracted_data,
    extracted_data_to_initial,
    get_reviewable_pending_import,
    mark_pending_import_failed,
    mark_pending_import_ready,
    restore_pending_review_after_error,
    validate_invoice_amounts,
)

import csv


logger = logging.getLogger(__name__)


'''
    Projects
'''
def get_projects(user, search_value=""):
    filters_to_search = ["name__icontains",]

    full_query = Q()
    if search_value != "":
        for myfilter in filters_to_search:
            full_query |= Q(**{myfilter: search_value})
    full_query &= Q(**{'manager': user.id})

    return Project.objects.filter(full_query)

def get_project_context(user, search_value=""):
    return {'items': get_projects(user, search_value)}


def get_financiers(search_value=""):
    full_query = Q()
    if search_value != "":
        full_query |= Q(name__icontains=search_value)
        full_query |= Q(tax_id__icontains=search_value)
        full_query |= Q(contact_person__icontains=search_value)
        full_query |= Q(email__icontains=search_value)
    return Financier.objects.filter(full_query).order_by("name")


def get_financier_context(search_value=""):
    return {"items": get_financiers(search_value)}


def get_suppliers(search_value=""):
    full_query = Q()
    if search_value != "":
        full_query |= Q(name__icontains=search_value)
        full_query |= Q(nif__icontains=search_value)
        full_query |= Q(contact_person__icontains=search_value)
        full_query |= Q(email__icontains=search_value)
        full_query |= Q(phone__icontains=search_value)
    return Supplier.objects.filter(full_query).order_by("name")


def get_supplier_context(search_value=""):
    return {"items": get_suppliers(search_value)}


def get_supplier_tax_ids():
    return {str(item["id"]): item["nif"] for item in Supplier.objects.values("id", "nif")}


def get_recent_invoice_start_date():
    return timezone.localdate() - timedelta(days=365)


def get_project_ids_for_user(user):
    return list(get_projects(user).values_list("id", flat=True))


def get_recent_invoices(user, all_dates=False):
    return (
        Invoice.objects.filter(**({} if all_dates else {"issue_date__gte": get_recent_invoice_start_date()}))
        .select_related("supplier")
        .annotate(
            allocated_amount_total=Coalesce(
                Sum("allocations__allocated_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            ),
            allocation_count=Count("allocations", distinct=True),
        )
        .order_by("-issue_date", "-id")
    )


def attach_invoice_suppliers(invoices):
    invoice_items = list(invoices)
    unresolved = [invoice for invoice in invoice_items if invoice.supplier_id is None]
    supplier_nifs = {normalize_tax_id(invoice.provider_tax_id) for invoice in unresolved if normalize_tax_id(invoice.provider_tax_id)}
    suppliers = {
        normalize_tax_id(supplier.nif): supplier
        for supplier in Supplier.objects.only("id", "name", "nif")
        if normalize_tax_id(supplier.nif) in supplier_nifs
    }
    for invoice in unresolved:
        fallback_supplier = suppliers.get(normalize_tax_id(invoice.provider_tax_id))
        if fallback_supplier is not None:
            invoice.supplier = fallback_supplier
    return invoice_items


def get_invoice_context(user, params=None):
    from .forms import InvoiceFilterForm
    form = InvoiceFilterForm(params)
    invoices = get_recent_invoices(user, all_dates=True)
    if form.is_valid():
        filters = form.cleaned_data
        if filters["invoice_from"]:
            invoices = invoices.filter(issue_date__gte=filters["invoice_from"])
        if filters["invoice_to"]:
            invoices = invoices.filter(issue_date__lte=filters["invoice_to"])
        if filters["invoice_status"]:
            invoices = invoices.filter(status=filters["invoice_status"])
        invoices = invoices.filter(total_amount__gte=filters["invoice_min"] or Decimal("0"))
        query = filters["invoice_q"]
        if query:
            supplier_ids = Supplier.objects.filter(name__icontains=query).values_list("nif", flat=True)
            invoices = invoices.filter(Q(number__icontains=query) | Q(locator__icontains=query) | Q(invoice_code__icontains=query) | Q(provider_tax_id__icontains=query) | Q(provider_tax_id__in=supplier_ids))
    else:
        invoices = invoices.none()
    return {
        "invoices": attach_invoice_suppliers(invoices),
        "invoice_filter_form": form,
        "invoice_start_date": get_recent_invoice_start_date(),
    }


def get_invoice_allocation_wizard_context(user, invoice):
    projects_qs = get_projects(user).order_by("name")
    project_ids = list(projects_qs.values_list("id", flat=True))
    budget_lines = (
        BudgetLine.objects.filter(project_id__in=project_ids)
        .annotate(child_count=Count("child_lines"))
        .filter(child_count=0)
        .select_related("project", "parent")
        .order_by("project__name", "code", "name")
    )
    for budget_line in budget_lines:
        budget_line.invoice_allocation_available = max(budget_line.available_balance, Decimal("0.00"))
    activities = Activity.objects.filter(project_id__in=project_ids).select_related("project").order_by("project__name", "name")
    remaining_amount = invoice.pending_amount if invoice else Decimal("0.00")
    allocated_amount = invoice.allocated_amount if invoice else Decimal("0.00")
    total_amount = invoice.total_amount if invoice else Decimal("0.00")
    return {
        "invoice": invoice,
        "projects": projects_qs,
        "budget_lines": budget_lines,
        "activities": activities,
        "allocated_amount": allocated_amount,
        "allocated_amount_display": format_decimal(allocated_amount),
        "total_amount_display": format_decimal(total_amount),
        "remaining_amount": remaining_amount,
        "remaining_amount_display": format_decimal(remaining_amount),
    }


def parse_decimal(value, default="0.00"):
    try:
        return Decimal(str(value or default).replace(",", "."))
    except (InvalidOperation, ValueError):
        return Decimal(default)


def decimal_sum(queryset, field):
    return queryset.aggregate(total=Sum(field))["total"] or Decimal("0.00")


def percent_value(value, total):
    if not total:
        return Decimal("0.00")
    return min((value * Decimal("100")) / total, Decimal("100.00"))


def format_decimal(value):
    value = value or Decimal("0.00")
    return "{:,.2f}".format(value).replace(",", "X").replace(".", ",").replace("X", ".")


def form_errors_text(form):
    messages = []
    for field_name, field_errors in form.errors.items():
        label = form.fields[field_name].label if field_name in form.fields else "Error"
        messages.extend("{}: {}".format(label, error) for error in field_errors)
    return " ".join(messages)


def form_errors_payload(form):
    error_data = form.errors.get_json_data(escape_html=True)
    return {
        "success": False,
        "errors": {
            field_name: [error["message"] for error in field_errors]
            for field_name, field_errors in error_data.items()
            if field_name != "__all__"
        },
        "non_field_errors": [
            error["message"] for error in error_data.get("__all__", [])
        ],
    }


def validation_error_payload(error):
    if hasattr(error, "message_dict"):
        errors = {
            field_name: list(field_errors)
            for field_name, field_errors in error.message_dict.items()
            if field_name != "__all__"
        }
        non_field_errors = list(error.message_dict.get("__all__", []))
    else:
        errors = {}
        non_field_errors = list(error.messages)
    return {"success": False, "errors": errors, "non_field_errors": non_field_errors}


def get_payment_obligations(params=None):
    from .models import PaymentObligation

    params = params or {}
    ordering = params.get("ordering") or "due_asc"
    ordering_map = {
        "due_asc": ("expected_payment_date", "id"),
        "due_desc": ("-expected_payment_date", "-id"),
        "amount_desc": ("-amount", "expected_payment_date", "id"),
        "amount_asc": ("amount", "expected_payment_date", "id"),
        "creditor": ("creditor", "expected_payment_date", "id"),
    }
    obligations = PaymentObligation.objects.select_related("project", "financier", "budget_line", "invoice").order_by(
        *ordering_map.get(ordering, ordering_map["due_asc"])
    )
    query = (params.get("q") or "").strip()
    if query:
        obligations = obligations.filter(
            Q(concept__icontains=query)
            | Q(creditor__icontains=query)
            | Q(cash_outflows__reference__icontains=query)
        ).distinct()
    status = params.get("status") or ""
    if status:
        obligations = obligations.filter(status=status)
    payment_type = params.get("payment_type") or ""
    if payment_type:
        obligations = obligations.filter(payment_type=payment_type)
    project_id = params.get("project") or ""
    if project_id:
        obligations = obligations.filter(Q(project_id=project_id) | Q(allocations__project_id=project_id)).distinct()
    financier_id = params.get("financier") or ""
    if financier_id:
        obligations = obligations.filter(financier_id=financier_id)
    creditor = (params.get("creditor") or "").strip()
    if creditor:
        obligations = obligations.filter(creditor__icontains=creditor)
    date_from = params.get("date_from") or ""
    if date_from:
        obligations = obligations.filter(expected_payment_date__gte=date_from)
    date_to = params.get("date_to") or ""
    if date_to:
        obligations = obligations.filter(expected_payment_date__lte=date_to)
    return obligations


def get_payment_summary():
    from .models import CashOutflow, PaymentObligation, PaymentObligationStatus

    today = timezone.localdate()
    month_start = today.replace(day=1)
    next_month = (month_start + timedelta(days=32)).replace(day=1)
    obligations = list(PaymentObligation.objects.exclude(status=PaymentObligationStatus.CANCELLED))
    month_outflows = CashOutflow.objects.filter(payment_date__gte=month_start, payment_date__lt=next_month)
    pending_total = sum((obligation.amount_pending for obligation in obligations), Decimal("0.00"))
    pending_count = sum(1 for obligation in obligations if obligation.amount_pending > 0)
    overdue_items = [obligation for obligation in obligations if obligation.is_overdue]
    next_30_items = [
        obligation
        for obligation in obligations
        if obligation.expected_payment_date
        and today <= obligation.expected_payment_date <= today + timedelta(days=30)
        and obligation.amount_pending > 0
    ]
    overdue_total = sum((obligation.amount_pending for obligation in overdue_items), Decimal("0.00"))
    next_30_total = sum(
        (
            obligation.amount_pending
            for obligation in next_30_items
        ),
        Decimal("0.00"),
    )
    paid_this_month = decimal_sum(
        month_outflows,
        "amount",
    )
    return {
        "pending_total": pending_total,
        "pending_count": pending_count,
        "paid_this_month": paid_this_month,
        "paid_this_month_count": month_outflows.count(),
        "overdue_total": overdue_total,
        "overdue_count": len(overdue_items),
        "next_30_total": next_30_total,
        "next_30_count": len(next_30_items),
    }


def get_payment_treasury_context(params=None):
    from .models import PaymentObligationStatus, PaymentObligationType

    today = timezone.localdate()
    params = params or {}
    obligations = get_payment_obligations(params)
    paginator = Paginator(obligations, 5)
    payment_page = paginator.get_page(params.get("page") or 1)
    payment_tab = "treasury" if params.get("tab") == "treasury" else "obligations"
    tab_params = {key: params.get(key) for key in ("q", "status", "payment_type", "project", "financier", "creditor", "date_from", "date_to", "ordering", "page") if params.get(key)}
    tab_params["section"] = "payments"
    obligations_url = reverse("projects") + "?" + urlencode(dict(tab_params, tab="obligations"))
    treasury_url = reverse("projects") + "?" + urlencode(dict(tab_params, tab="treasury"))
    page_items = list(payment_page.object_list)
    tax_ids = {normalize_tax_id(item.creditor) for item in page_items}
    tax_ids.update(normalize_tax_id(item.invoice.provider_tax_id) for item in page_items if item.invoice_id)
    suppliers = {normalize_tax_id(supplier.nif): supplier for supplier in Supplier.objects.filter(nif__in=tax_ids)}
    for item in page_items:
        supplier = suppliers.get(normalize_tax_id(item.creditor))
        if supplier is None and item.invoice_id:
            supplier = suppliers.get(normalize_tax_id(item.invoice.provider_tax_id))
        item.creditor_name = supplier.name if supplier else item.creditor
        item.creditor_tax_id = supplier.nif if supplier else ""
        allocations = list(item.invoice.allocations.select_related("project")) if item.invoice_id else list(item.allocations.select_related("project"))
        item.budget_allocation_amount = sum((allocation.allocated_amount for allocation in allocations), Decimal("0.00"))
        names = list(dict.fromkeys(allocation.project.name for allocation in allocations))
        item.project_names = ", ".join(names) or (item.project.name if item.project_id else "—")
        item.can_delete = not item.cash_outflows.exists() and not item.allocations.exists()
    groups = get_treasury_forecast_groups(today)
    upcoming = sorted((item for group in groups if group["code"] != "overdue" for item in group["items"]), key=lambda item: (item.expected_payment_date, item.pk))[:5]
    return {
        "payment_obligations": page_items,
        "payment_tab": payment_tab,
        "payment_obligations_url": obligations_url,
        "payment_treasury_url": treasury_url,
        "payment_upcoming": upcoming,
        "payment_upcoming_url": reverse("projects") + "?" + urlencode({"section": "payments", "tab": "obligations", "ordering": "due_asc", "date_from": today.isoformat()}),
        "payment_page": payment_page,
        "payment_total_count": paginator.count,
        "payment_page_range": paginator.page_range,
        "payment_summary": get_payment_summary(),
        "payment_statuses": PaymentObligationStatus.choices,
        "payment_types": PaymentObligationType.choices,
        "payment_ordering_options": (
            ("due_asc", "Fecha prevista (más próxima)"),
            ("due_desc", "Fecha prevista (más lejana)"),
            ("amount_desc", "Importe (mayor primero)"),
            ("amount_asc", "Importe (menor primero)"),
            ("creditor", "Acreedor"),
        ),
        "payment_projects": Project.objects.order_by("name"),
        "payment_financiers": Financier.objects.order_by("name"),
        "payment_filters": params,
        "treasury_groups": groups,
    }


def get_treasury_forecast_groups(today=None):
    from .models import PaymentObligation, PaymentObligationStatus

    today = today or timezone.localdate()
    groups = [
        ("overdue", "Vencidas", None, today - timedelta(days=1)),
        ("next_7", "Próximos 7 días", today, today + timedelta(days=7)),
        ("next_30", "8 - 30 días", today + timedelta(days=8), today + timedelta(days=30)),
        ("next_60", "31 - 60 días", today + timedelta(days=31), today + timedelta(days=60)),
        ("later", "Más adelante", today + timedelta(days=61), None),
    ]
    obligations = [
        obligation
        for obligation in PaymentObligation.objects.exclude(status=PaymentObligationStatus.CANCELLED).order_by("expected_payment_date")
        if obligation.amount_pending > 0
    ]
    rows = []
    for code, label, start_date, end_date in groups:
        if start_date and end_date:
            items = [item for item in obligations if start_date <= item.expected_payment_date <= end_date]
        elif end_date:
            items = [item for item in obligations if item.expected_payment_date <= end_date]
        else:
            items = [item for item in obligations if item.expected_payment_date >= start_date]
        rows.append({
            "code": code,
            "label": label,
            "count": len(items),
            "amount": sum((item.amount_pending for item in items), Decimal("0.00")),
            "items": items,
            "next_date": items[0].expected_payment_date if items else None,
        })
    return rows


def get_projects_dashboard_context(user, payment_params=None):
    projects_qs = get_projects(user)
    project_ids = list(projects_qs.values_list("id", flat=True))
    projects_total = len(project_ids)
    active_projects = projects_qs.filter(status=ProjectStatus.ACTIVE).count()
    approved_budget = decimal_sum(projects_qs, "approved_budget")
    executed_budget = decimal_sum(InvoiceAllocation.objects.filter(project_id__in=project_ids), "allocated_amount")
    executed_budget += decimal_sum(PaymentObligationAllocation.objects.filter(project_id__in=project_ids), "allocated_amount")
    pending_budget = max(approved_budget - executed_budget, Decimal("0.00"))
    execution_percentage = percent_value(executed_budget, approved_budget)
    execution_angle = int((execution_percentage * Decimal("3.6")).quantize(Decimal("1")))

    activities_qs = Activity.objects.filter(project_id__in=project_ids)
    indicators_qs = Indicator.objects.filter(objective__project_id__in=project_ids)

    invoices_qs = Invoice.objects.all()
    activities_total = activities_qs.count()
    indicators_total = indicators_qs.count()

    activity_statuses = []
    for status, label, color in [
        (ProgressStatus.COMPLETED, "Completadas", "#85479c"),
        (ProgressStatus.IN_PROGRESS, "En ejecución", "#3f7dd9"),
        (ProgressStatus.DELAYED, "Retrasadas", "#f47b2b"),
        (ProgressStatus.NOT_STARTED, "No iniciadas", "#85479c"),
    ]:
        count = activities_qs.filter(status=status).count()
        activity_statuses.append({
            "label": label,
            "count": count,
            "percentage": percent_value(Decimal(count), Decimal(activities_total)),
            "color": color,
        })

    indicator_cards = [
        {
            "label": "En progreso",
            "icon": "fa-check",
            "class": "success",
            "count": indicators_qs.filter(current_value__gt=0, current_value__lt=F("target")).count() if indicators_total else 0,
        },
        {
            "label": "Con riesgo",
            "icon": "fa-exclamation",
            "class": "warning",
            "count": indicators_qs.filter(current_value__lt=F("target")).count() if indicators_total else 0,
        },
        {
            "label": "En retraso",
            "icon": "fa-times",
            "class": "danger",
            "count": activities_qs.filter(status=ProgressStatus.DELAYED).count(),
        },
        {
            "label": "Sin iniciar",
            "icon": "fa-info",
            "class": "info",
            "count": indicators_qs.filter(current_value=0).count() if indicators_total else 0,
        },
    ]
    for card in indicator_cards:
        card["percentage"] = percent_value(Decimal(card["count"]), Decimal(indicators_total or activities_total))

    financier_rows = []
    project_financiers = (
        ProjectFinancier.objects.filter(project_id__in=project_ids)
        .values("financier__name")
        .annotate(amount=Sum("committed_amount"))
        .order_by("-amount")[:5]
    )
    for row in project_financiers:
        amount = row["amount"] or Decimal("0.00")
        financier_rows.append({
            "name": row["financier__name"] or "Sin financiador",
            "amount": amount,
            "percentage": percent_value(amount, approved_budget),
        })

    project_execution = []
    for project in projects_qs.order_by("name")[:8]:
        executed = project.executed_budget
        project_execution.append({
            "project": project,
            "executed_percentage": percent_value(executed, project.approved_budget),
            "executed": executed,
            "pending": max(project.approved_budget - executed, Decimal("0.00")),
        })

    invoice_items = get_recent_invoices(user)
    latest_invoices = invoice_items[:5]
    pending_invoices = sum(1 for invoice in invoices_qs if invoice.pending_amount > 0)
    delayed_activities = activities_qs.filter(status=ProgressStatus.DELAYED).count()
    stale_indicators = indicators_qs.filter(last_update__isnull=True).count() if indicators_total else 0

    context = {
        "items": projects_qs.order_by("name"),
        "financiers": get_financiers(),
        "suppliers": get_suppliers(),
        "invoices": invoice_items,
        "invoice_start_date": get_recent_invoice_start_date(),
        "projects_total": projects_total,
        "active_projects": active_projects,
        "approved_budget": approved_budget,
        "executed_budget": executed_budget,
        "pending_budget": pending_budget,
        "execution_percentage": execution_percentage,
        "execution_angle": execution_angle,
        "activities_total": activities_total,
        "activities_in_progress": activities_qs.filter(status=ProgressStatus.IN_PROGRESS).count(),
        "indicators_total": indicators_total,
        "activity_statuses": activity_statuses,
        "indicator_cards": indicator_cards,
        "financier_rows": financier_rows,
        "project_execution": project_execution,
        "latest_invoices": latest_invoices,
        "pending_invoices": pending_invoices,
        "delayed_activities": delayed_activities,
        "stale_indicators": stale_indicators,
        "approved_budget_display": format_decimal(approved_budget),
        "executed_budget_display": format_decimal(executed_budget),
        "pending_budget_display": format_decimal(pending_budget),
    }
    context.update(get_payment_treasury_context(payment_params))
    context.update(get_invoice_context(user, payment_params))
    return context

@group_required("admins","managers", "employee")
def projects(request):
    return render(request, "projects/projects.html", get_projects_dashboard_context(request.user, request.GET))

@group_required("admins","managers", "employee")
def project_list(request):
    return render(request, "projects/project-list.html", get_project_context(request.user))

@group_required("admins","managers", "employee")
def project_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "projects/project-list.html", get_project_context(request.user, search_value))

@group_required("admins","managers", "employee")
def project_new(request):
    obj = Project.objects.create(manager=request.user)
    #po, created = PatientOrigin.objects.get_or_create(patient=obj)
    return redirect(reverse('project-view', kwargs={'project_id': obj.id}))

@group_required("admins","managers", "employee")
def project_remove(request):
    obj = get_or_none(Project, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "projects/project-list.html", get_project_context(request.user))


@group_required("admins","managers", "employee")
def financier_list(request):
    return render(request, "projects/financier-list.html", get_financier_context())


@group_required("admins","managers", "employee")
def financier_search(request):
    search_value = get_param(request.GET, "s-financier")
    return render(request, "projects/financier-list.html", get_financier_context(search_value))


@group_required("admins","managers", "employee")
def financier_form(request):
    try:
        obj = get_or_none(Financier, request.GET["obj_id"]) if "obj_id" in request.GET else Financier.objects.create(name="")
        return render(request, "projects/financier-form.html", {"obj": obj, "financier_types": FinancierType.choices})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def financier_remove(request):
    try:
        obj = get_or_none(Financier, request.GET["obj_id"]) if "obj_id" in request.GET else None
        if obj != None:
            obj.delete()
        return render(request, "projects/financier-list.html", get_financier_context())
    except ProtectedError:
        return HttpResponse("No se puede eliminar este financiador porque está vinculado a proyectos o facturas.", status=400)


@group_required("admins","managers", "employee")
def supplier_list(request):
    return render(request, "projects/supplier-list.html", get_supplier_context())


@group_required("admins","managers", "employee")
def supplier_search(request):
    search_value = get_param(request.GET, "s-supplier")
    return render(request, "projects/supplier-list.html", get_supplier_context(search_value))


@group_required("admins","managers", "employee")
def supplier_form(request):
    obj = get_or_none(Supplier, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
    return render(request, "projects/supplier-form.html", {"obj": obj})


@group_required("admins","managers", "employee")
def supplier_save(request):
    try:
        obj = get_or_none(Supplier, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else Supplier()
        if obj == None:
            return HttpResponse("Proveedor no encontrado.", status=404)

        obj.name = get_param(request.GET, "name").strip()
        obj.nif = normalize_tax_id(get_param(request.GET, "nif"))
        obj.address = get_param(request.GET, "address").strip()
        obj.email = get_param(request.GET, "email").strip()
        obj.phone = get_param(request.GET, "phone").strip()
        obj.contact_person = get_param(request.GET, "contact_person").strip()
        obj.full_clean()
        obj.save()
        return render(request, "projects/supplier-list.html", get_supplier_context())
    except ValidationError as e:
        if hasattr(e, "message_dict"):
            messages = []
            for field_errors in e.message_dict.values():
                messages.extend(field_errors)
            return HttpResponse(" ".join(messages), status=400)
        return HttpResponse(" ".join(e.messages), status=400)
    except Exception as e:
        return HttpResponse(show_exc(e), status=400)


@group_required("admins","managers", "employee")
def supplier_remove(request):
    obj = get_or_none(Supplier, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
    if obj != None:
        obj.delete()
    return render(request, "projects/supplier-list.html", get_supplier_context())


@group_required("admins","managers", "employee")
def invoice_list(request):
    return render(request, "projects/invoice-list.html", get_invoice_context(request.user, request.GET))


@group_required("admins","managers", "employee")
def invoice_form(request):
    obj = get_or_none(Invoice, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
    form = InvoiceForm(instance=obj, user=request.user)
    return render(request, "projects/invoice-form.html", {
        "obj": obj,
        "form": form,
        "supplier_tax_ids": get_supplier_tax_ids(),
    })


def get_invoice_review_context(user, pending_import, extracted_data):
    invoice_data = extracted_data_to_initial(extracted_data)
    supplier_match = match_suppliers(
        extracted_data.nif_proveedor_original or extracted_data.nif_proveedor,
        Supplier.objects.all(),
    )
    if supplier_match.unique_exact:
        invoice_data["supplier"] = supplier_match.unique_exact.id
        invoice_data["provider_tax_id"] = supplier_match.unique_exact.nif
    elif len(supplier_match.exact_matches) > 1:
        logger.warning("Multiple suppliers share a normalized tax identifier. matches=%s", len(supplier_match.exact_matches))
    amount_validation = validate_invoice_amounts(extracted_data)
    return {
        "form": InvoiceForm(initial=invoice_data, user=user),
        "pending_import": pending_import,
        "amount_warning": None if amount_validation["valid"] else amount_validation,
        "automatic_review": True,
        "supplier_match": supplier_match,
        "supplier_tax_ids": get_supplier_tax_ids(),
    }


@group_required("admins","managers", "employee")
def invoice_import(request):
    if request.method == "GET":
        return render(request, "projects/invoice-import-form.html", {
            "form": InvoiceImportForm(),
        })

    form = InvoiceImportForm(request.POST, request.FILES)
    if not form.is_valid():
        return render(request, "projects/invoice-import-form.html", {
            "form": form,
        }, status=400)

    invoice_document = form.cleaned_data["invoice_document"]
    pending_import = create_pending_import(request.user, invoice_document)
    try:
        pending_import.temporary_document.open("rb")
        pending_import.temporary_document.content_type = pending_import.detected_mime
        pending_import.temporary_document.invoice_document_mime = pending_import.detected_mime
        extracted_data = extract_invoice_data(pending_import.temporary_document)
        mark_pending_import_ready(pending_import, extracted_data)
        return render(request, "projects/invoice-form.html", get_invoice_review_context(
            request.user, pending_import, extracted_data
        ))
    except (InvoiceExtractionError, InvoiceImportError) as exc:
        mark_pending_import_failed(pending_import)
        logger.warning("Invoice import analysis failed")
        form.add_error("invoice_document", str(exc))
        return render(request, "projects/invoice-import-form.html", {
            "form": form,
        }, status=400)
    except Exception:
        mark_pending_import_failed(pending_import, "unexpected_analysis_error")
        logger.exception("Unexpected invoice import error")
        form.add_error("invoice_document", "No se ha podido analizar la factura. Puedes intentarlo de nuevo o introducirla manualmente.")
        return render(request, "projects/invoice-import-form.html", {
            "form": form,
        }, status=400)


@group_required("admins","managers", "employee")
def invoice_import_reanalyze(request, token):
    if request.method != "POST":
        return HttpResponse("Método no permitido.", status=405)
    try:
        pending_import = begin_pending_reanalysis(request.user, token)
        pending_import.temporary_document.open("rb")
        pending_import.temporary_document.content_type = pending_import.detected_mime
        pending_import.temporary_document.invoice_document_mime = pending_import.detected_mime
        validate_invoice_document(pending_import.temporary_document)
        extracted_data = extract_invoice_data(pending_import.temporary_document)
        mark_pending_import_ready(pending_import, extracted_data)
        pending_import.refresh_from_db()
        return render(request, "projects/invoice-form.html", get_invoice_review_context(
            request.user, pending_import, extracted_data
        ))
    except PendingInvoiceImportUnavailable as exc:
        return HttpResponse(str(exc), status=409)
    except (InvoiceExtractionError, InvoiceImportError, ValidationError) as exc:
        if "pending_import" in locals():
            restore_pending_review_after_error(pending_import)
        logger.warning("Invoice reanalysis failed")
        return HttpResponse(str(exc), status=400)
    except Exception:
        if "pending_import" in locals():
            restore_pending_review_after_error(pending_import, "unexpected_reanalysis_error")
        logger.exception("Unexpected invoice reanalysis error")
        return HttpResponse("No se ha podido reanalizar el documento. Inténtalo de nuevo.", status=500)
@group_required("admins","managers", "employee")
def invoice_status_form(request):
    try:
        invoice = get_or_none(Invoice, get_param(request.GET, "invoice_id"))
        if invoice == None:
            return HttpResponse("Factura no encontrada.", status=404)
        return render(request, "projects/invoice-status-form.html", {
            "invoice": invoice,
            "invoice_statuses": InvoiceStatus.choices,
        })
    except Exception:
        logger.exception("Invoice status form failed")
        return HttpResponse("Ha ocurrido un error inesperado. Por favor, comunícalo al administrador.", status=500)


@group_required("admins","managers", "employee")
def invoice_traceability(request):
    invoice = get_or_none(Invoice, get_param(request.GET, "invoice_id"))
    if invoice == None:
        return HttpResponse("Factura no encontrada.", status=404)
    return render(request, "projects/invoice-traceability.html", {
        "invoice": invoice,
        "status_changes": invoice.status_changes.select_related("changed_by"),
        "allocations": invoice.allocations.select_related("project", "budget_line"),
        "physical_document": get_invoice_physical_document_context(invoice),
    })


def format_file_size(size):
    if size >= 1024 * 1024:
        return "{:.1f} MB".format(size / (1024 * 1024)).replace(".", ",")
    return "{} KB".format(max(1, round(size / 1024)))


def get_invoice_physical_document_context(invoice):
    if not invoice.physical_document:
        return None
    extension = os.path.splitext(invoice.physical_document.name)[1].lower()
    try:
        size = invoice.physical_document.size
        document = invoice.physical_document.open("rb")
        try:
            detected_mime = detect_invoice_document_mime(document)
        finally:
            document.close()
    except Exception:
        return {"unavailable": True}
    if detected_mime != ALLOWED_INVOICE_DOCUMENT_TYPES.get(extension):
        return {"unavailable": True}
    return {
        "format": extension.lstrip(".").upper() or "ARCHIVO",
        "size": format_file_size(size),
        "mime": detected_mime,
    }


@group_required("admins", "managers", "employee")
def invoice_physical_document_form(request):
    invoice = get_or_none(Invoice, get_param(request.GET, "invoice_id"))
    if invoice is None:
        return HttpResponse("Factura no encontrada.", status=404)
    return render(request, "projects/invoice-import-form.html", {
        "attachment_mode": True,
        "replacing_document": bool(invoice.physical_document),
        "invoice": invoice,
        "form": InvoiceImportForm(),
    })


@group_required("admins", "managers", "employee")
def invoice_physical_document_viewer(request):
    invoice = get_or_none(Invoice, get_param(request.GET, "invoice_id"))
    if invoice is None or not invoice.physical_document:
        return HttpResponse("Documento no encontrado.", status=404)
    document_context = get_invoice_physical_document_context(invoice)
    if not document_context or document_context.get("unavailable") or not document_context.get("mime"):
        return HttpResponse("El documento no está disponible o no se puede leer.", status=404)
    return render(request, "projects/invoice-document-viewer.html", {
        "invoice": invoice,
        "physical_document": document_context,
    })


@group_required("admins", "managers", "employee")
@xframe_options_exempt
def invoice_physical_document_file(request, invoice_id):
    invoice = get_or_none(Invoice, invoice_id)
    if invoice is None or not invoice.physical_document:
        return HttpResponse("Documento no encontrado.", status=404)
    try:
        document = invoice.physical_document.open("rb")
        detected_mime = detect_invoice_document_mime(document)
        if detected_mime not in ALLOWED_INVOICE_DOCUMENT_TYPES.values():
            document.close()
            return HttpResponse("El documento no está disponible o no se puede leer.", status=404)
        document.seek(0)
        disposition = "attachment" if request.GET.get("download") == "1" else "inline"
        extension = next(ext for ext, mime in ALLOWED_INVOICE_DOCUMENT_TYPES.items() if mime == detected_mime)
        response = FileResponse(document, content_type=detected_mime)
        response["Content-Disposition"] = '{}; filename="factura-{}{}"'.format(disposition, invoice.id, extension)
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        response["Content-Security-Policy"] = "frame-ancestors 'self'"
        return response
    except (FileNotFoundError, OSError, ValueError):
        return HttpResponse("El documento no está disponible o no se puede leer.", status=404)


@group_required("admins","managers", "employee")
def invoice_save(request):
    request_data = (request.POST if request.method == "POST" else request.GET).copy()
    if not request_data.get("total_amount"):
        request_data["total_amount"] = str(
            parse_decimal(request_data.get("taxable_base"))
            + parse_decimal(request_data.get("iva_amount"))
            + parse_decimal(request_data.get("igic_amount"))
            - parse_decimal(request_data.get("irpf_amount"))
        )
    pending_token = request_data.get("pending_import", "").strip()
    obj_id = request_data.get("obj_id", "").strip()
    try:
        obj = get_or_none(Invoice, obj_id) if obj_id else Invoice()
        if obj == None:
            return HttpResponse("Factura no encontrada.", status=404)
        form = InvoiceForm(request_data, instance=obj, user=request.user)
        if not form.is_valid():
            pending_import = None
            if pending_token:
                try:
                    pending_import = get_reviewable_pending_import(request.user, pending_token)
                except PendingInvoiceImportUnavailable:
                    pass
            return render(request, "projects/invoice-form.html", {
                "obj": obj if obj.pk else None,
                "form": form,
                "pending_import": pending_import,
                "automatic_review": bool(pending_import),
                "amount_warning": {"message": "Los importes detectados no cuadran y deben revisarse."} if form.errors.get("total_amount") else None,
                "supplier_tax_ids": get_supplier_tax_ids(),
            }, status=400)

        if pending_token:
            invoice = complete_pending_import(request.user, pending_token, form)
        else:
            invoice = form.save()
        response = render(request, "projects/invoice-list.html", get_invoice_context(request.user))
        response["X-Capsulae-Message"] = "Factura guardada correctamente."
        response["X-Capsulae-Invoice-Id"] = str(invoice.id)
        return response
    except PendingInvoiceImportUnavailable as exc:
        return HttpResponse(str(exc), status=409)
    except ValidationError as exc:
        return HttpResponse(" ".join(exc.messages), status=400)
    except Exception:
        logger.exception("Invoice save failed")
        return HttpResponse("Ha ocurrido un error inesperado. Por favor, comunícalo al administrador.", status=500)


@group_required("admins","managers", "employee")
def pending_invoice_document(request, token):
    try:
        pending_import = get_reviewable_pending_import(request.user, token)
        document = pending_import.temporary_document.open("rb")
        response = FileResponse(document, content_type=pending_import.detected_mime)
        response["Content-Disposition"] = 'inline; filename="{}"'.format(pending_import.original_name.replace('"', ""))
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response
    except PendingInvoiceImportUnavailable:
        return HttpResponse("Documento no encontrado.", status=404)


@group_required("admins","managers", "employee")
def invoice_remove(request):
    try:
        obj = get_or_none(Invoice, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
        if obj == None:
            return HttpResponse("Factura no encontrada.", status=404)
        if obj.allocations.exists():
            return HttpResponse("No se puede eliminar una factura con imputaciones.", status=400)

        if obj.physical_document:
            obj.physical_document.delete(save=False)
        obj.delete()
        return render(request, "projects/invoice-list.html", get_invoice_context(request.user))
    except Exception as e:
        logger.exception("Invoice removal failed")
        return HttpResponse(show_exc(e), status=400)


@group_required("admins","managers", "employee")
def invoice_physical_document_upload(request):
    new_document_name = None
    try:
        invoice = get_or_none(Invoice, request.POST.get("obj_id"))
        if invoice == None:
            return HttpResponse("Factura no encontrada.", status=404)
        traceability_upload = "invoice_document" in request.FILES
        uploaded_file = request.FILES.get("invoice_document") or request.FILES.get("file")
        if uploaded_file == None:
            return HttpResponse("Debes seleccionar un documento físico.", status=400)

        validate_invoice_document(uploaded_file)

        old_document_name = invoice.physical_document.name if invoice.physical_document else ""
        extension = os.path.splitext(uploaded_file.name)[1].lower()
        field = Invoice._meta.get_field("physical_document")
        generated_name = field.generate_filename(invoice, "invoice-{}-{}{}".format(invoice.id, uuid.uuid4().hex, extension))
        new_document_name = field.storage.save(generated_name, uploaded_file)
        try:
            with transaction.atomic():
                invoice.physical_document.name = new_document_name
                invoice.save(update_fields=["physical_document"])
        except Exception:
            field.storage.delete(new_document_name)
            new_document_name = None
            raise
        new_document_name = None
        if old_document_name and old_document_name != new_document_name:
            try:
                field.storage.delete(old_document_name)
            except Exception:
                logger.warning("Could not delete replaced invoice document %s", old_document_name)
        if traceability_upload:
            response = render(request, "projects/invoice-traceability.html", {
                "invoice": invoice,
                "status_changes": invoice.status_changes.select_related("changed_by"),
                "allocations": invoice.allocations.select_related("project", "budget_line"),
                "physical_document": get_invoice_physical_document_context(invoice),
            })
        else:
            response = render(request, "projects/invoice-list.html", get_invoice_context(request.user))
        response["X-Capsulae-Message"] = "Documento físico guardado correctamente."
        return response
    except ValidationError as exc:
        return HttpResponse(" ".join(exc.messages), status=400)
    except Exception:
        if new_document_name:
            Invoice._meta.get_field("physical_document").storage.delete(new_document_name)
        logger.exception("Invoice physical document upload failed")
        return HttpResponse("Ha ocurrido un error inesperado. Por favor, comunícalo al administrador.", status=500)


@group_required("admins","managers", "employee")
def payment_list(request):
    return render(request, "projects/payment-list.html", get_payment_treasury_context(request.GET))


@group_required("admins","managers", "employee")
def payment_form(request):
    from .models import PaymentObligation, PaymentObligationStatus, PaymentObligationType
    from .payment_forms import PaymentObligationForm

    obj = get_or_none(PaymentObligation, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else PaymentObligation(
        payment_type=PaymentObligationType.OTHER,
        status=PaymentObligationStatus.PENDING,
    )
    return render(request, "projects/payment-form.html", {
        "obj": obj,
        "form": PaymentObligationForm(instance=obj),
    })


@group_required("admins","managers", "employee")
def payment_save(request):
    from .models import PaymentObligation, PaymentObligationDocument
    from .payment_forms import PaymentObligationForm

    try:
        params = request.POST if request.method == "POST" else request.GET
        obj = get_or_none(PaymentObligation, get_param(params, "obj_id")) if get_param(params, "obj_id") else PaymentObligation()
        if obj == None:
            return JsonResponse({"message": "Obligación de pago no encontrada."}, status=404)
        form = PaymentObligationForm(params, request.FILES, instance=obj)
        if not form.is_valid():
            return JsonResponse(form_errors_payload(form), status=400)
        obligation = form.save(commit=False)
        obligation.full_clean()
        with transaction.atomic():
            obligation.save()
            document = form.cleaned_data.get("document")
            if document:
                PaymentObligationDocument.objects.create(
                    payment_obligation=obligation, name=document.name[:255], document=document,
                )
        return render(request, "projects/payment-list.html", get_payment_treasury_context({}))
    except ValidationError as e:
        return JsonResponse(validation_error_payload(e), status=400)
    except Exception:
        logger.exception("Payment obligation save failed")
        return JsonResponse({"message": "Ha ocurrido un error inesperado. Por favor, comunícalo al administrador."}, status=500)


@group_required("admins","managers", "employee")
def payment_detail(request):
    from .models import PaymentObligation

    obj = get_or_none(PaymentObligation, get_param(request.GET, "obj_id"))
    if obj == None:
        return HttpResponse("Obligación de pago no encontrada.", status=404)
    return render(request, "projects/payment-detail.html", {
        "obj": obj,
        "cash_outflows": obj.cash_outflows.all(),
    })


@group_required("admins", "managers", "employee")
def payment_allocation_manage(request):
    from .models import PaymentObligation
    from .payment_forms import PaymentAllocationEditForm

    if request.method not in ("GET", "POST"):
        return HttpResponse(status=405)
    params = request.POST if request.method == "POST" else request.GET
    action = params.get("action", "edit")
    if action not in ("edit", "delete"):
        return HttpResponse("Acción no válida.", status=400, content_type="text/plain")
    try:
        with transaction.atomic():
            allocation = PaymentObligationAllocation.objects.get(pk=params.get("allocation_id"))
            obligation = PaymentObligation.objects.select_for_update().get(pk=allocation.payment_obligation_id)
            project = get_projects(request.user).select_for_update().get(pk=allocation.project_id)
            allocation = PaymentObligationAllocation.objects.select_for_update().get(pk=allocation.pk)
            if project.status != ProjectStatus.ACTIVE:
                raise ValidationError("Solo se pueden modificar o eliminar imputaciones de proyectos activos.")
            form = PaymentAllocationEditForm(request.POST if request.method == "POST" and action == "edit" else None, instance=allocation)
            if request.method == "POST":
                # Serialize balance changes with other operations on this budget line.
                BudgetLine.objects.select_for_update().get(pk=allocation.budget_line_id)
                if action == "delete":
                    allocation.delete()
                else:
                    if not form.is_valid():
                        return HttpResponse(form_errors_text(form), status=400, content_type="text/plain")
                    form.save()
                return render(request, "projects/payment-detail.html", {"obj": obligation, "cash_outflows": obligation.cash_outflows.all()})
            return render(request, "projects/payment-allocation-manage.html", {"allocation": allocation, "form": form, "action": action})
    except ValidationError as error:
        return HttpResponse(" ".join(error.messages), status=400, content_type="text/plain")
    except (ValueError, TypeError, PaymentObligationAllocation.DoesNotExist, PaymentObligation.DoesNotExist, Project.DoesNotExist):
        return HttpResponse("Imputación no encontrada o sin permiso de acceso.", status=404, content_type="text/plain")
    except Exception:
        logger.exception("Payment allocation update failed")
        return HttpResponse("No se pudo modificar la imputación. Comunícalo al administrador.", status=500, content_type="text/plain")


@group_required("admins", "managers", "employee")
def payment_allocation_wizard(request):
    from .models import PaymentObligation

    obligation = get_or_none(PaymentObligation, request.GET.get("obj_id"))
    if obligation is None:
        return HttpResponse("Obligación no encontrada.", status=404, content_type="text/plain")
    if obligation.invoice_id or obligation.status == "cancelled":
        return HttpResponse("Solo se pueden imputar obligaciones sin factura y no canceladas.", status=400, content_type="text/plain")
    context = get_invoice_allocation_wizard_context(request.user, None)
    context.update({
        "payment_obligation": obligation,
        "invoice": {"total_amount": obligation.amount},
        "allocated_amount": obligation.allocated_amount,
        "allocated_amount_display": format_decimal(obligation.allocated_amount),
        "total_amount_display": format_decimal(obligation.amount),
        "remaining_amount": obligation.unallocated_amount,
        "remaining_amount_display": format_decimal(obligation.unallocated_amount),
    })
    return render(request, "projects/invoice-allocation-wizard.html", context)


@group_required("admins", "managers", "employee")
def payment_allocation_save(request):
    from .models import PaymentObligation

    if request.method != "POST":
        return HttpResponse(status=405)
    try:
        with transaction.atomic():
            obligation = PaymentObligation.objects.select_for_update().get(pk=request.POST.get("payment_obligation_id"))
            project = get_projects(request.user).get(pk=request.POST.get("project"))
            line = BudgetLine.objects.select_for_update().get(pk=request.POST.get("budget_line"), project=project)
            activity = None
            if request.POST.get("activity"):
                activity = Activity.objects.get(pk=request.POST["activity"], project=project)
            mode = request.POST.get("allocation_mode", "amount")
            if mode not in ("amount", "percentage"):
                raise ValidationError("Modo de imputación no válido.")
            amount = Decimal(request.POST.get("allocated_percentage" if mode == "percentage" else "allocated_amount", "0").replace(",", "."))
            if not amount.is_finite() or amount <= 0:
                raise ValidationError("Introduce un importe o porcentaje mayor que cero.")
            if mode == "percentage":
                if amount > 100:
                    raise ValidationError("El porcentaje no puede superar el 100%.")
                amount = (obligation.amount * amount / Decimal("100")).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            PaymentObligationAllocation.objects.create(payment_obligation=obligation, project=project, budget_line=line, activity=activity, allocated_amount=amount)
        return render(request, "projects/payment-list.html", get_payment_treasury_context({}))
    except ValidationError as error:
        return HttpResponse(" ".join(error.messages), status=400, content_type="text/plain")
    except (ValueError, InvalidOperation, PaymentObligation.DoesNotExist, Project.DoesNotExist, BudgetLine.DoesNotExist, Activity.DoesNotExist):
        return HttpResponse("Revisa el proyecto, la partida y el importe de la imputación.", status=400, content_type="text/plain")
    except Exception:
        logger.exception("Payment obligation allocation failed")
        return HttpResponse("No se pudo guardar la imputación. Comunícalo al administrador.", status=500, content_type="text/plain")


@group_required("admins","managers", "employee")
def payment_remove(request):
    from .models import PaymentObligation

    try:
        obj = get_or_none(PaymentObligation, get_param(request.GET, "obj_id"))
        if obj == None:
            return HttpResponse("Obligación de pago no encontrada.", status=404)
        if obj.allocations.exists():
            return HttpResponse("No se puede eliminar una obligación con imputaciones.", status=400, content_type="text/plain")
        if obj.cash_outflows.exists():
            return HttpResponse("No se puede eliminar una obligación con pagos registrados.", status=400)
        obj.delete()
        return render(request, "projects/payment-list.html", get_payment_treasury_context({}))
    except Exception as e:
        logger.exception("Payment obligation remove failed")
        return HttpResponse(show_exc(e), status=400)


@group_required("admins","managers", "employee")
def cash_outflow_form(request):
    from .models import PaymentObligation
    from .payment_forms import CashOutflowForm

    obligation = get_or_none(PaymentObligation, get_param(request.GET, "payment_obligation_id"))
    if obligation == None:
        return HttpResponse("Obligación de pago no encontrada.", status=404)
    initial = {
        "payment_date": timezone.localdate(),
        "amount": max(obligation.amount_pending, Decimal("0.00")),
    }
    return render(request, "projects/cash-outflow-form.html", {
        "obligation": obligation,
        "form": CashOutflowForm(initial=initial),
    })


@group_required("admins","managers", "employee")
def cash_outflow_save(request):
    from .models import PaymentObligation, PaymentObligationStatus
    from .payment_forms import CashOutflowForm

    try:
        obligation_id = get_param(request.GET, "payment_obligation_id")
        with transaction.atomic():
            obligation = PaymentObligation.objects.select_for_update().filter(pk=obligation_id).first()
            if obligation == None:
                return HttpResponse("Obligación de pago no encontrada.", status=404)
            if obligation.status == PaymentObligationStatus.CANCELLED:
                return HttpResponse("No se pueden registrar pagos sobre obligaciones canceladas.", status=400)

            form = CashOutflowForm(request.GET)
            if not form.is_valid():
                return HttpResponse(form_errors_text(form), status=400)
            cash_outflow = form.save(commit=False)
            cash_outflow.payment_obligation = obligation
            current_paid = money_sum(obligation.cash_outflows.all(), "amount")
            remaining_amount = obligation.amount - current_paid
            if cash_outflow.amount > remaining_amount:
                return HttpResponse("El pago no puede superar el saldo pendiente de la obligación.", status=400)
            cash_outflow.full_clean()
            cash_outflow.save()

        obligation.refresh_from_db()
        return render(request, "projects/payment-detail.html", {
            "obj": obligation,
            "cash_outflows": obligation.cash_outflows.all(),
        })
    except ValidationError as e:
        if hasattr(e, "message_dict"):
            messages = []
            for field_errors in e.message_dict.values():
                messages.extend(field_errors)
            return HttpResponse(" ".join(messages), status=400)
        return HttpResponse(" ".join(e.messages), status=400)
    except Exception as e:
        logger.exception("Cash outflow save failed")
        return HttpResponse(show_exc(e), status=400)


@group_required("admins","managers", "employee")
def invoice_status_save(request):
    try:
        invoice_id = get_param(request.GET, "invoice_id")
        new_status = get_param(request.GET, "status")
        valid_statuses = dict(InvoiceStatus.choices)
        if new_status not in valid_statuses:
            return HttpResponse("Debes seleccionar un estado válido.", status=400)

        with transaction.atomic():
            invoice = Invoice.objects.select_for_update().filter(pk=invoice_id).first()
            if invoice == None:
                return HttpResponse("Factura no encontrada.", status=404)
            original_status = invoice.status
            if original_status == new_status:
                return HttpResponse("Debes seleccionar un estado diferente al actual.", status=400)

            Invoice.objects.filter(pk=invoice.pk).update(status=new_status)
            InvoiceStatusChange.objects.create(
                invoice=invoice,
                changed_by=request.user if request.user.is_authenticated else None,
                original_status=original_status,
                final_status=new_status,
            )
        return render(request, "projects/invoice-list.html", get_invoice_context(request.user))
    except ValidationError as e:
        if hasattr(e, "message_dict"):
            messages = []
            for field_errors in e.message_dict.values():
                messages.extend(field_errors)
            return HttpResponse(" ".join(messages), status=400)
        return HttpResponse(" ".join(e.messages), status=400)
    except Exception as e:
        return HttpResponse(show_exc(e), status=400)


@group_required("admins","managers", "employee")
def invoice_allocation_wizard(request):
    invoice_id = get_param(request.GET, "invoice_id") or get_param(request.GET, "invoiceId")
    invoice = get_or_none(Invoice, invoice_id)
    if invoice == None:
        return HttpResponse("Factura no encontrada.", status=404)
    return render(request, "projects/invoice-allocation-wizard.html", get_invoice_allocation_wizard_context(request.user, invoice))


@group_required("admins","managers", "employee")
def invoice_allocation_save(request):
    try:
        invoice = get_or_none(Invoice, get_param(request.GET, "invoice_id"))

        if invoice == None:
            return HttpResponse("Factura no encontrada.", status=404)
        if invoice.pending_amount <= 0:
            return HttpResponse("La factura ya está completamente imputada.", status=400)

        project = get_or_none(Project, get_param(request.GET, "project"))
        allowed_project_ids = get_project_ids_for_user(request.user)
        if project == None or project.id not in allowed_project_ids:
            return HttpResponse("Debes seleccionar un proyecto válido.", status=400)

        selected_budget_line = get_or_none(BudgetLine, get_param(request.GET, "budget_line"))
        if selected_budget_line == None or selected_budget_line.project_id != project.id:
            return HttpResponse("Debes seleccionar una partida válida para el proyecto.", status=400)
        if selected_budget_line.child_lines.exists():
            return HttpResponse("Solo pueden imputarse facturas a partidas sin subpartidas.", status=400)

        activity = get_or_none(Activity, get_param(request.GET, "activity")) if get_param(request.GET, "activity") else None
        if activity != None and activity.project_id != project.id:
            return HttpResponse("La actividad debe pertenecer al proyecto seleccionado.", status=400)

        allocation_mode = get_param(request.GET, "allocation_mode", "amount")
        max_available = min(invoice.pending_amount, max(selected_budget_line.available_balance, Decimal("0.00")))
        if allocation_mode == "percentage":
            allocated_percentage = parse_decimal(get_param(request.GET, "allocated_percentage"))
            if allocated_percentage <= 0:
                return HttpResponse("El porcentaje a imputar debe ser mayor que cero.", status=400)
            allocated_amount = ((invoice.total_amount * allocated_percentage) / Decimal("100")).quantize(
                Decimal("0.01"),
                rounding=ROUND_HALF_UP,
            )
        else:
            allocated_amount = parse_decimal(get_param(request.GET, "allocated_amount"))
        if allocated_amount <= 0:
            return HttpResponse("El importe a imputar debe ser mayor que cero.", status=400)
        if allocated_amount > max_available:
            return HttpResponse("No se puede imputar más que el máximo disponible para esta factura y partida.", status=400)

        allocation = InvoiceAllocation(
            invoice=invoice,
            project=project,
            activity=activity,
            budget_line=selected_budget_line,
            allocated_amount=allocated_amount,
        )
        allocation.full_clean()
        allocation.save()
        return render(request, "projects/invoice-list.html", get_invoice_context(request.user))
    except ValidationError as e:
        if hasattr(e, "message_dict"):
            messages = []
            for field_errors in e.message_dict.values():
                messages.extend(field_errors)
            return HttpResponse(" ".join(messages), status=400)
        return HttpResponse(" ".join(e.messages), status=400)
    except Exception as e:
        return HttpResponse(show_exc(e), status=400)

'''
    Project
'''
@group_required("admins","managers", "employee")
def project_view(request, project_id):
    project = get_or_none(Project, project_id)
    return render(request, "project/project-view.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_shell(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/project-shell.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_tab_counts(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    if project == None:
        return JsonResponse({"error": "Proyecto no encontrado."}, status=404)
    return JsonResponse({
        "texts": project.texts.count(),
        "activities": project.activities.count(),
        "financiers": project.project_financiers.count(),
        "budget_lines": project.budget_lines.filter(parent__isnull=True).count(),
        "incomes": project.incomes.count(),
        "expenses": project.expenses.count(),
    })

@group_required("admins","managers", "employee")
def project_details(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/project-details.html", {'obj': project})


def get_project_financiers_context(project):
    project_financiers = project.project_financiers.select_related("financier").order_by("financier__name")
    committed_amount = decimal_sum(project_financiers, "committed_amount")
    granted_amount = decimal_sum(project_financiers, "granted_amount")
    disbursed_amount = decimal_sum(project_financiers, "disbursed_amount")
    pending_execution = max((project.approved_budget or Decimal("0.00")) - project.executed_budget, Decimal("0.00"))
    return {
        "obj": project,
        "project_financiers": project_financiers,
        "financier_summary": {
            "approved_budget": project.approved_budget or Decimal("0.00"),
            "committed_amount": committed_amount,
            "granted_amount": granted_amount,
            "disbursed_amount": disbursed_amount,
            "pending_execution": pending_execution,
            "financier_count": project_financiers.count(),
        },
    }


@group_required("admins","managers", "employee")
def project_financiers(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/financiers/financier-list.html", get_project_financiers_context(project))


@group_required("admins","managers", "employee")
def project_financier_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        obj = get_or_none(ProjectFinancier, get_param(request.GET, "obj_id")) if "obj_id" in request.GET else None
        if project == None and obj != None:
            project = obj.project
        return render(request, "project/financiers/financier-form.html", {
            "obj": obj,
            "project": project,
            "financiers": Financier.objects.order_by("name"),
            "financier_types": FinancierType.choices,
        })
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_financier_save(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return HttpResponse("Proyecto no encontrado.", status=404)

        financier_id = get_param(request.GET, "financier")
        if financier_id == "__new__":
            financier_name = get_param(request.GET, "new_financier_name")
            if financier_name == "":
                return HttpResponse("Debes indicar el nombre del nuevo financiador.", status=400)
            financier = Financier.objects.create(
                name=financier_name,
                financier_type=get_param(request.GET, "new_financier_type", FinancierType.OTHER),
                tax_id=get_param(request.GET, "new_financier_tax_id"),
                contact_person=get_param(request.GET, "new_financier_contact"),
                email=get_param(request.GET, "new_financier_email"),
            )
        else:
            financier = get_or_none(Financier, financier_id)
        if financier == None:
            return HttpResponse("Financiador no encontrado.", status=404)

        obj = get_or_none(ProjectFinancier, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
        if obj == None:
            obj, created = ProjectFinancier.objects.get_or_create(project=project, financier=financier)
        else:
            obj.financier = financier

        obj.committed_amount = parse_decimal(get_param(request.GET, "committed_amount"))
        obj.granted_amount = parse_decimal(get_param(request.GET, "granted_amount"))
        obj.disbursed_amount = parse_decimal(get_param(request.GET, "disbursed_amount"))
        agreement_date = get_param(request.GET, "agreement_date")
        obj.agreement_date = agreement_date or None
        obj.full_clean()
        obj.save()
        return render(request, "project/financiers/financier-list.html", get_project_financiers_context(project))
    except Exception as e:
        if hasattr(e, "message_dict"):
            messages = []
            for field_errors in e.message_dict.values():
                messages.extend(field_errors)
            return HttpResponse(" ".join(messages), status=400)
        return HttpResponse(show_exc(e), status=400)


@group_required("admins","managers", "employee")
def project_financier_remove(request):
    try:
        obj = get_or_none(ProjectFinancier, get_param(request.GET, "obj_id"))
        if obj == None:
            return HttpResponse("Financiador de proyecto no encontrado.", status=404)
        project = obj.project
        if project.financier_contributions.filter(financier=obj.financier).exists():
            return HttpResponse("No se puede eliminar porque este financiador ya tiene aportaciones en partidas.", status=400)
        obj.delete()
        return render(request, "project/financiers/financier-list.html", get_project_financiers_context(project))
    except ProtectedError:
        return HttpResponse("No se puede eliminar porque hay aportaciones vinculadas.", status=400)
    except Exception as e:
        return HttpResponse(show_exc(e), status=400)

@group_required("admins","managers", "employee")
def project_form(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    users = User.objects.filter(is_active=True).order_by("username")
    return render(request, "project/project-form.html", {'obj': project, 'users': users, 'status_choices': ProjectStatus.choices})

@group_required("admins","managers", "employee")
def project_budget_autosave(request):
    try:
        model_name = get_param(request.GET, "model_name")
        obj_id = get_param(request.GET, "obj_id")
        field = get_param(request.GET, "field")
        value = get_param(request.GET, "value")
        model_map = {
            "projects.project": Project,
            "projects.budgetline": BudgetLine,
        }
        allowed_fields = {
            "projects.project": {"approved_budget"},
            "projects.budgetline": {"approved_budget"},
        }
        model = model_map.get(model_name)
        if model == None or field not in allowed_fields.get(model_name, set()):
            return HttpResponse("Campo presupuestario no permitido.", status=400)

        obj = get_or_none(model, obj_id)
        if obj == None:
            return HttpResponse("No se pudo guardar: objeto no encontrado.", status=404)

        try:
            decimal_value = Decimal(str(value).replace(",", ".") if value != "" else "0")
        except (InvalidOperation, ValueError):
            return HttpResponse("El presupuesto debe ser un número válido.", status=400)

        if decimal_value < 0:
            return HttpResponse("El presupuesto no puede ser negativo.", status=400)

        setattr(obj, field, decimal_value)
        obj.clean()
        obj.save(update_fields=[field])
        return HttpResponse("Guardado")
    except Exception as e:
        if hasattr(e, "message_dict"):
            messages = []
            for field_errors in e.message_dict.values():
                messages.extend(field_errors)
            return HttpResponse(" ".join(messages), status=400)
        return HttpResponse(show_exc(e), status=400)

@group_required("admins","managers", "employee")
def project_texts(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/texts/text-list.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_activities(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/activities/activity-list.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_budget(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/budget/budget-list.html", {'obj': project})

def get_budget_lines_context(project):
    budget_lines = list(project.budget_lines.filter(parent__isnull=True).order_by("code", "name"))
    sub_lines = list(project.budget_lines.filter(parent__isnull=False).select_related("parent").order_by("code", "name"))
    children_by_parent = {}
    for sub_line in sub_lines:
        children_by_parent.setdefault(sub_line.parent_id, []).append(sub_line)
    allocation_totals = {
        row["budget_line_id"]: row["amount"] or Decimal("0.00")
        for row in project.invoice_allocations.values("budget_line_id").annotate(amount=Sum("allocated_amount"))
    }
    for row in project.payment_allocations.values("budget_line_id").annotate(amount=Sum("allocated_amount")):
        key = row["budget_line_id"]
        allocation_totals[key] = allocation_totals.get(key, Decimal("0.00")) + row["amount"]
    contribution_totals = {}
    for row in project.financier_contributions.values("budget_line_id", "financier_id").annotate(amount=Sum("amount")):
        budget_line_id = row["budget_line_id"]
        financier_id = row["financier_id"]
        amount = row["amount"] or Decimal("0.00")
        contribution_totals.setdefault(budget_line_id, {})[financier_id] = amount

    def percentage_of(numerator, denominator):
        numerator = numerator or Decimal("0.00")
        denominator = denominator or Decimal("0.00")
        if denominator == 0:
            return Decimal("0.00")
        return (numerator * Decimal("100")) / denominator

    def css_percentage(value):
        value = value or Decimal("0.00")
        return "{:.2f}".format(max(Decimal("0.00"), min(value, Decimal("100.00"))))

    def funding_state(amount, percentage):
        if (amount or Decimal("0.00")) <= 0:
            return "none"
        if (percentage or Decimal("0.00")) >= Decimal("100.00"):
            return "complete"
        return "partial"

    def assigned_budget_display_for(budget_line):
        children = children_by_parent.get(budget_line.id, [])
        if children:
            return sum((child.approved_budget for child in children), Decimal("0.00"))
        return budget_line.approved_budget

    def executed_amount_for(budget_line):
        children = children_by_parent.get(budget_line.id, [])
        child_total = sum((executed_amount_for(child) for child in children), Decimal("0.00"))
        return allocation_totals.get(budget_line.id, Decimal("0.00")) + child_total

    def financed_amounts_by_financier_for(budget_line):
        children = children_by_parent.get(budget_line.id, [])
        if not children:
            return dict(contribution_totals.get(budget_line.id, {}))

        totals = {}
        for child in children:
            for financier_id, amount in financed_amounts_by_financier_for(child).items():
                totals[financier_id] = totals.get(financier_id, Decimal("0.00")) + amount
        return totals

    def display_available_balance_for(budget_line):
        children = children_by_parent.get(budget_line.id, [])
        if not children:
            return budget_line.approved_budget - allocation_totals.get(budget_line.id, Decimal("0.00"))

        return sum(
            (display_available_balance_for(child) for child in children),
            Decimal("0.00"),
        )

    def prepare_budget_line_row(budget_line):
        child_count = len(children_by_parent.get(budget_line.id, []))
        budget_line.child_line_count = child_count
        budget_line.can_assign_financing = child_count == 0
        budget_line.has_child_lines = child_count > 0
        budget_line.available_balance_label = "Saldo disponible" if budget_line.can_assign_financing else "Disponible acumulado"
        budget_line.display_assigned_budget = assigned_budget_display_for(budget_line)
        budget_line.display_executed_amount = executed_amount_for(budget_line)
        budget_line.display_available_balance = display_available_balance_for(budget_line)
        budget_line.financed_amounts_by_financier = financed_amounts_by_financier_for(budget_line)
        budget_line.financed_amount = sum(
            budget_line.financed_amounts_by_financier.values(),
            Decimal("0.00"),
        )
        budget_line.funding_percentage = percentage_of(budget_line.financed_amount, budget_line.display_assigned_budget)
        budget_line.funding_percentage_display = format_percentage(budget_line.funding_percentage)
        budget_line.funding_bar_percentage_css = css_percentage(budget_line.funding_percentage)
        budget_line.funding_state = funding_state(budget_line.financed_amount, budget_line.funding_percentage)

    def append_tree_rows(rows, sub_line, level):
        prepare_budget_line_row(sub_line)
        rows.append({
            "item": sub_line,
            "level": level,
            "can_add_child": level < BudgetLine.MAX_DEPTH,
            "has_child_lines": sub_line.has_child_lines,
        })
        for child in children_by_parent.get(sub_line.id, []):
            append_tree_rows(rows, child, level + 1)

    for budget_line in budget_lines:
        prepare_budget_line_row(budget_line)
        rows = []
        for sub_line in children_by_parent.get(budget_line.id, []):
            append_tree_rows(rows, sub_line, 1)
        budget_line.tree_sub_lines = rows

    funding_states = set()
    for budget_line in budget_lines:
        funding_states.add(budget_line.funding_state)
        for row in budget_line.tree_sub_lines:
            funding_states.add(row["item"].funding_state)

    approved_budget = project.approved_budget or Decimal("0.00")
    approved_in_budget_lines = decimal_sum(project.budget_lines.filter(parent__isnull=True), "approved_budget")
    leaf_line_ids = [
        budget_line.id
        for budget_line in list(budget_lines) + sub_lines
        if not children_by_parent.get(budget_line.id)
    ]
    assigned_to_leaf_lines = decimal_sum(project.budget_lines.filter(id__in=leaf_line_ids), "approved_budget")
    executed_amount = sum(allocation_totals.values(), Decimal("0.00"))
    available_amount = sum((budget_line.display_available_balance for budget_line in budget_lines), Decimal("0.00"))
    pending_assignment = max(approved_budget - approved_in_budget_lines, Decimal("0.00"))
    assigned_percentage = percentage_of(assigned_to_leaf_lines, approved_budget)
    executed_percentage = percentage_of(executed_amount, approved_budget)
    available_percentage = percentage_of(available_amount, approved_budget)
    pending_percentage = percentage_of(pending_assignment, approved_budget)

    return {
        'obj': project,
        'budget_lines': budget_lines,
        'budget_line_summary': {
            'approved_budget': approved_budget,
            'approved_in_budget_lines': approved_in_budget_lines,
            'assigned_to_leaf_lines': assigned_to_leaf_lines,
            'executed_amount': executed_amount,
            'available_amount': available_amount,
            'pending_assignment': pending_assignment,
            'assigned_percentage': assigned_percentage,
            'assigned_percentage_display': format_percentage(assigned_percentage),
            'assigned_percentage_css': css_percentage(assigned_percentage),
            'executed_percentage_display': format_percentage(executed_percentage),
            'available_percentage_display': format_percentage(available_percentage),
            'pending_percentage_display': format_percentage(pending_percentage),
            'show_funding_legend': {"complete", "partial", "none"}.issubset(funding_states),
            'budget_line_count': len(budget_lines),
            'sub_budget_line_count': len(sub_lines),
        },
    }


def format_percentage(value):
    value = value or Decimal("0.00")
    value = value.quantize(Decimal("0.1"), rounding=ROUND_HALF_UP)
    return str(value).replace(".", ",")


def get_financier_contribution_context(budget_line, obj=None):
    contributions = list(
        budget_line.financier_contributions
        .select_related("financier")
        .order_by("financier__name", "id")
    )
    project_financiers = list(budget_line.project.project_financiers.select_related("financier").order_by("financier__name"))
    for project_financier in project_financiers:
        project_financier.form_available_amount = project_financier.available_amount
        if obj and obj.financier_id == project_financier.financier_id:
            project_financier.form_available_amount += obj.amount
    budget_amount = budget_line.effective_budget or Decimal("0.00")
    contributed_amount = sum((contribution.amount for contribution in contributions), Decimal("0.00"))
    pending_amount = budget_amount - contributed_amount
    if budget_amount:
        financing_percentage = (contributed_amount * Decimal("100")) / budget_amount
    else:
        financing_percentage = Decimal("0.00")
    financing_bar_percentage = max(Decimal("0.00"), min(financing_percentage, Decimal("100.00")))
    form_available_amount = max(
        budget_amount - contributed_amount + (obj.amount if obj else Decimal("0.00")),
        Decimal("0.00"),
    )
    return {
        "obj": obj,
        "budget_line": budget_line,
        "project": budget_line.project,
        "project_financiers": project_financiers,
        "financier_types": FinancierType.choices,
        "contributions": contributions,
        "contributions_count": len(contributions),
        "budget_amount": budget_amount,
        "contributed_amount": contributed_amount,
        "pending_amount": pending_amount,
        "financing_percentage": financing_percentage,
        "financing_percentage_display": format_percentage(financing_percentage),
        "financing_bar_percentage": financing_bar_percentage,
        "financing_bar_percentage_css": "{:.2f}".format(financing_bar_percentage),
        "form_available_amount": form_available_amount,
    }


@group_required("admins","managers", "employee")
def project_budget_lines(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/budget-lines/budget-line-list.html", get_budget_lines_context(project))


@group_required("admins","managers", "employee")
def project_financier_contribution_form(request):
    try:
        budget_line = get_or_none(BudgetLine, get_param(request.GET, "budget_line_id"))
        obj = get_or_none(FinancierContribution, get_param(request.GET, "obj_id")) if "obj_id" in request.GET else None
        if budget_line == None and obj != None:
            budget_line = obj.budget_line
        if budget_line == None:
            return render(request, 'error_exception.html', {'exc':'Partida presupuestaria no encontrada!'})
        if budget_line.child_lines.exists():
            return render(request, 'error_exception.html', {'exc':'Solo puede asignarse financiación a partidas sin subpartidas.'})
        return render(request, "project/budget-lines/financier-contribution-form.html", get_financier_contribution_context(budget_line, obj))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_financier_contribution_save(request):
    try:
        budget_line = get_or_none(BudgetLine, get_param(request.GET, "budget_line_id"))
        obj = get_or_none(FinancierContribution, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
        if budget_line == None and obj != None:
            budget_line = obj.budget_line
        if budget_line == None:
            return HttpResponse("Partida presupuestaria no encontrada.", status=404)
        if budget_line.child_lines.exists():
            return HttpResponse("Solo puede asignarse financiación a partidas sin subpartidas.", status=400)

        project = budget_line.project
        financier_id = get_param(request.GET, "financier")
        amount = parse_decimal(get_param(request.GET, "amount"))
        if amount <= 0:
            return HttpResponse("La cantidad aportada debe ser mayor que cero.", status=400)

        if financier_id == "__new__":
            financier_name = get_param(request.GET, "new_financier_name")
            if financier_name == "":
                return HttpResponse("Debes indicar el nombre del nuevo financiador.", status=400)
            financier = Financier.objects.create(
                name=financier_name,
                financier_type=get_param(request.GET, "new_financier_type", FinancierType.OTHER),
                tax_id=get_param(request.GET, "new_financier_tax_id"),
                contact_person=get_param(request.GET, "new_financier_contact"),
                email=get_param(request.GET, "new_financier_email"),
            )
            ProjectFinancier.objects.create(
                project=project,
                financier=financier,
                committed_amount=amount,
                granted_amount=amount,
            )
        else:
            project_financier = get_or_none(ProjectFinancier, financier_id)
            if project_financier == None or project_financier.project_id != project.id:
                return HttpResponse("Financiador de proyecto no encontrado.", status=404)
            financier = project_financier.financier

        if obj == None:
            obj = FinancierContribution(project=project, financier=financier)
        else:
            obj.financier = financier
        obj.budget_line = budget_line
        obj.amount = amount
        if budget_line.effective_budget:
            obj.percentage = (amount * Decimal("100")) / budget_line.effective_budget
        obj.notes = get_param(request.GET, "notes")
        obj.full_clean()
        obj.save()
        if get_param(request.GET, "return_modal") == "1":
            return render(request, "project/budget-lines/financier-contribution-form.html", get_financier_contribution_context(budget_line))
        return render(request, "project/budget-lines/budget-line-list.html", get_budget_lines_context(project))
    except Exception as e:
        if hasattr(e, "message_dict"):
            messages = []
            for field_errors in e.message_dict.values():
                messages.extend(field_errors)
            return HttpResponse(" ".join(messages), status=400)
        return HttpResponse(show_exc(e), status=400)


@group_required("admins","managers", "employee")
def project_financier_contribution_remove(request):
    try:
        obj = get_or_none(FinancierContribution, get_param(request.GET, "obj_id"))
        if obj == None:
            return HttpResponse("Aportación no encontrada.", status=404)
        project = obj.project
        budget_line = obj.budget_line
        obj.delete()
        if get_param(request.GET, "return_modal") == "1":
            return render(request, "project/budget-lines/financier-contribution-form.html", get_financier_contribution_context(budget_line))
        return render(request, "project/budget-lines/budget-line-list.html", get_budget_lines_context(project))
    except ProtectedError:
        return HttpResponse("No se puede eliminar esta aportación porque está vinculada a facturas.", status=400)
    except Exception as e:
        return HttpResponse(show_exc(e), status=400)

@group_required("admins","managers", "employee")
def project_drive(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    folder_list = project.folders.filter(parent__isnull=True)
    file_list = project.files.filter(folder__isnull=True)
    return render(request, "project/drive/drive.html", {'obj': project, 'folder_list': folder_list, 'file_list': file_list})

'''
    Texts
'''
@group_required("admins","managers", "employee")
def project_text_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Text, request.GET["obj_id"]) if "obj_id" in request.GET else Text.objects.create(project=project)
        return render(request, "project/texts/text-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_text_remove(request):
    try:
        obj = get_or_none(Text, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/texts/text-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Activities
'''
@group_required("admins","managers", "employee")
def project_activity_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Activity, request.GET["obj_id"]) if "obj_id" in request.GET else Activity.objects.create(project=project)
        return render(request, "project/activities/activity-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_activity_remove(request):
    try:
        obj = get_or_none(Activity, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/activities/activity-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

#@group_required("admins","managers")
def project_activity_register(request, activity_id):
    try:
        obj = get_or_none(Activity, activity_id)
        return render(request, "project/activities/register-form.html", {'obj': obj, 'end': False})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def project_activity_set_register(request):
    try:
        activity_id = request.POST["activity_id"]
        name = request.POST["name"]
        email = request.POST["email"]

        obj = get_or_none(Activity, activity_id)
        end = False
        msg = ""
        if validate_captcha(request) or True:
            au = ActivityUser.objects.filter(activity=obj, name=name, email=email).first()
            if au == None:
                au = ActivityUser.objects.create(activity=obj, name=name, email=email)
                end = True
            else:
                msg = "Este usuario ya se ha registrado!"
        else:
            msg = "Debe indicar que no es un robot!"
        return render(request, "project/activities/register-form.html", {'obj': obj, "end": end, "msg": msg})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_activity_register_list(request):
    try:
        obj = get_or_none(Activity, request.GET["obj_id"])
        return render(request, "project/activities/register-list.html", {'obj': obj,})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_activity_register_export(request, activity_id):
    try:
        obj = get_or_none(Activity, activity_id)

        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="{}_{}.csv"'.format(obj.project.name, obj.name)},
        )

        writer = csv.writer(response)
        writer.writerow(['Nombre', 'Correo electrónico'])
        for item in obj.users.all():
            writer.writerow([item.name, item.email])
        return response
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Budget
'''
def get_next_budget_line_code(project):
    prefix = "P"
    next_number = project.budget_lines.filter(parent__isnull=True).count() + 1
    code = "{}{:03d}".format(prefix, next_number)
    while project.budget_lines.filter(code=code).exists():
        next_number += 1
        code = "{}{:03d}".format(prefix, next_number)
    return code


def get_next_sub_budget_line_code(parent):
    prefix = "S"
    next_number = parent.child_lines.count() + 1
    code = "{}{:03d}".format(prefix, next_number)
    while parent.project.budget_lines.filter(code=code).exists():
        next_number += 1
        code = "{}{:03d}".format(prefix, next_number)
    return code


def move_parent_financing_and_allocations_to_child(parent, child):
    contributions = list(parent.financier_contributions.all())
    allocations = list(parent.invoice_allocations.all()) + list(parent.payment_allocations.all())
    if not contributions and not allocations:
        return
    total_amount = sum((contribution.amount for contribution in contributions), Decimal("0.00"))
    total_allocated = sum((allocation.allocated_amount for allocation in allocations), Decimal("0.00"))
    inherited_budget = max(total_amount, total_allocated)
    if inherited_budget > 0 and not child.effective_budget:
        child.approved_budget = inherited_budget
        child.save(update_fields=["approved_budget"])
    budget_limit = child.effective_budget
    for contribution in contributions:
        contribution.budget_line = child
        if budget_limit:
            contribution.percentage = (contribution.amount * Decimal("100")) / budget_limit
        contribution.save(update_fields=["budget_line", "percentage"])
    for allocation in allocations:
        allocation.budget_line = child
        allocation.save(update_fields=["budget_line"])


def get_or_create_root_budget_line_draft(project):
    draft = (
        project.budget_lines
        .filter(
            parent__isnull=True,
            name="",
            description="",
            approved_budget=Decimal("0.00"),
        )
        .annotate(
            child_count=Count("child_lines"),
            contribution_count=Count("financier_contributions"),
            allocation_count=Count("invoice_allocations"),
            payment_allocation_count=Count("payment_allocations"),
        )
        .filter(child_count=0, contribution_count=0, allocation_count=0, payment_allocation_count=0)
        .order_by("-id")
        .first()
    )
    if draft:
        return draft

    return BudgetLine.objects.create(
        project=project,
        code=get_next_budget_line_code(project),
    )


@group_required("admins","managers", "employee")
def project_budget_line_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(BudgetLine, request.GET["obj_id"]) if "obj_id" in request.GET else get_or_create_root_budget_line_draft(project)
        return render(request, "project/budget-lines/budget-line-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_budget_line_remove(request):
    try:
        obj = get_or_none(BudgetLine, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/budget-lines/budget-line-list.html", get_budget_lines_context(project))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_sub_budget_line_form(request):
    try:
        if "obj_id" in request.GET:
            obj = get_or_none(BudgetLine, request.GET["obj_id"])
            if obj == None:
                return render(request, 'error_exception.html', {'exc':'Subpartida no encontrada!'})
        else:
            parent = get_or_none(BudgetLine, get_param(request.GET, "parent_id"))
            if parent == None:
                parent = get_or_none(BudgetLine, get_param(request.GET, "budget_line_id"))
            if parent == None:
                return render(request, 'error_exception.html', {'exc':'Partida presupuestaria padre no encontrada!'})
            if parent.level >= BudgetLine.MAX_DEPTH:
                return render(request, 'error_exception.html', {'exc':'El límite máximo de anidamiento de subpartidas es 4.'})
            with transaction.atomic():
                obj = BudgetLine.objects.create(
                    project=parent.project,
                    parent=parent,
                    code=get_next_sub_budget_line_code(parent),
                )
                move_parent_financing_and_allocations_to_child(parent, obj)
        return render(request, "project/budget-lines/sub-budget-line-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_sub_budget_line_remove(request):
    try:
        obj = get_or_none(BudgetLine, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/budget-lines/budget-line-list.html", get_budget_lines_context(project))
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_income_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Income, request.GET["obj_id"]) if "obj_id" in request.GET else Income.objects.create(project=project)

        return render(request, "project/budget/income-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_income_remove(request):
    try:
        obj = get_or_none(Income, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/budget/budget-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_expense_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Expense, request.GET["obj_id"]) if "obj_id" in request.GET else Expense.objects.create(project=project)

        return render(request, "project/budget/expense-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_expense_remove(request):
    try:
        obj = get_or_none(Expense, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/budget/budget-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

'''
    Drive
'''
@group_required("admins","managers", "employee")
def project_folder_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        if "obj_id" in request.GET:
            obj = get_or_none(Folder, request.GET["obj_id"])  
        else:
            parent = get_or_none(Folder, request.GET["parent_id"]) if request.GET["parent_id"]  != "" else None 
            obj = Folder.objects.create(project=project, parent=parent)
        return render(request, "project/drive/folder-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_folder_change(request):
    try:
        obj_id = request.GET["obj_id"]
        #enter = request.GET["enter"]

        obj = get_or_none(Folder, obj_id)
        #folder = obj if enter == "True" else obj.parent
        
        folder_list = obj.childs.all()
        file_list = obj.files.all()
        return render(request, "project/drive/drive.html", {"obj": obj.project, 'folder': obj,'folder_list': folder_list, 'file_list': file_list})
        #return render(request, "project/drive/drive.html", {"obj": obj.project, 'folder': folder,'folder_list': folder.childs.all()})
        #perms = get_perms(request, folder)
        #return render(request, "project/drive/index.html", {"obj": obj.client, 'folder': folder, 'perms': perms})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_folder_remove(request):
    try:
        obj_id = request.GET["obj_id"]
        folder_id = request.GET["folder_id"]

        obj = get_or_none(Folder, obj_id)
        if obj != None:
            project = obj.project
            obj.delete()
        folder = get_or_none(Folder, folder_id)
        folder_list = folder.childs.all() if folder != None else project.folders.filter(parent__isnull=True)
        file_list = folder.files.all() if folder != None else project.files.filter(folder__isnull=True)

        return render(request, "project/drive/drive.html", {"obj": project, 'folder': folder,'folder_list': folder_list, 'file_list': file_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_list(request):
    try:
        obj_id = request.GET["obj_id"]
        obj = get_or_none(File, obj_id)
        file_list = obj.folder.files.all() if obj.folder != None else obj.project.files.filter(folder__isnull=True)
        return render(request, "project/drive/file-list.html", {"obj": obj.project, 'folder': obj.folder, 'file_list': file_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_add(request):
    try:
        obj_id = request.POST["obj_id"]
        field = request.POST["field"]
        folder_id = request.POST["folder"]
        file_list = request.FILES.getlist('file')

        obj = get_or_none(Project, obj_id)
        folder = get_or_none(Folder, folder_id)
        for f in file_list:
            #f_encrypt = encrypt(f, request.user.username)
            #obj_file = File(project=obj, proj_file=f_encrypt, name=f_encrypt.name, folder=folder)
            obj_file = File(project=obj, proj_file=f, name=f.name, folder=folder)
            obj_file.save()

        file_list = folder.files.all() if folder != None else obj.files.filter(folder__isnull=True)
        return render(request, "project/drive/file-list.html", {"obj": obj, 'folder': folder, 'file_list': file_list})
    except Exception as e:
        logger.exception("Project file upload failed")
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers", "employee")
def project_file_form(request):
    try:
        obj = get_or_none(File, request.GET["obj_id"])  
        return render(request, "project/drive/file-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_remove(request):
    try:
        obj_id = request.GET["obj_id"]

        obj = get_or_none(File, obj_id)
        if obj != None:
            project = obj.project
            folder = obj.folder
            obj.delete()
        file_list = folder.files.all() if folder != None else project.files.filter(folder__isnull=True)

        return render(request, "project/drive/file-list.html", {"obj": project, 'folder': folder, 'file_list': file_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_get(request, obj_id):
    try:
        f = get_or_none(File, obj_id) 
        #f_out = decrypt(f.client_file, f.client.password)
        #response = HttpResponse(f_out, 'application/force-download')
        #response['Content-Disposition'] = 'attachment; filename="%s"' % (f_out.name)
        response = HttpResponse(f, 'application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % (f.name)
        return response 
    except Exception as e:
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))


def test_api(request):
    try:
        import os
        import openai
        openai.api_key = os.getenv('OPENAI_API_KEY', 'your_openai_api_key_here')
        if "your_openai_api_key_here" in openai.api_key:
            return JsonResponse({"message": "Test API failed", "error": "OpenAI API key is not set properly"})
        # response = openai.Completion.create(
        #     model="text-davinci-003",
        #     prompt="Say hello",
        #     max_tokens=5
        # )
        return JsonResponse({"message": "Test API successful"})
    except Exception as e:
        return JsonResponse({"message": "Test API failed", "error": str(e)})
