from datetime import timedelta
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.db.models.deletion import ProtectedError
from django.db.models import DecimalField, F, Q, Sum, Value
from django.db.models.functions import Coalesce
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render, redirect, reverse
from django.utils import timezone

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, validate_captcha
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
    InvoiceStatus,
    File,
    Folder,
    Project,
    ProjectFinancier,
    ProjectStatus,
    ProgressStatus,
    Text,
)

import csv


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


def get_recent_invoice_start_date():
    return timezone.localdate() - timedelta(days=365)


def get_project_ids_for_user(user):
    return list(get_projects(user).values_list("id", flat=True))


def get_recent_invoices(user):
    return (
        Invoice.objects.filter(issue_date__gte=get_recent_invoice_start_date())
        .annotate(
            allocated_amount_total=Coalesce(
                Sum("allocations__allocated_amount"),
                Value(Decimal("0.00")),
                output_field=DecimalField(max_digits=14, decimal_places=2),
            )
        )
        .order_by("-issue_date", "-id")
    )


def get_invoice_context(user):
    return {
        "invoices": get_recent_invoices(user),
        "invoice_start_date": get_recent_invoice_start_date(),
    }


def get_invoice_allocation_wizard_context(user, invoice):
    projects_qs = get_projects(user).order_by("name")
    project_ids = list(projects_qs.values_list("id", flat=True))
    budget_lines = (
        BudgetLine.objects.filter(project_id__in=project_ids)
        .select_related("project", "parent")
        .order_by("project__name", "code", "name")
    )
    contributions = (
        FinancierContribution.objects.filter(project_id__in=project_ids)
        .select_related("project", "financier", "budget_line", "sub_budget_line")
        .order_by("project__name", "financier__name", "budget_line__code", "sub_budget_line__code")
    )
    activities = Activity.objects.filter(project_id__in=project_ids).select_related("project").order_by("project__name", "name")
    remaining_amount = invoice.pending_amount if invoice else Decimal("0.00")
    allocated_amount = invoice.allocated_amount if invoice else Decimal("0.00")
    return {
        "invoice": invoice,
        "projects": projects_qs,
        "budget_lines": budget_lines,
        "contributions": contributions,
        "activities": activities,
        "allocated_amount": allocated_amount,
        "allocated_amount_display": format_decimal(allocated_amount),
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


def get_projects_dashboard_context(user):
    projects_qs = get_projects(user)
    project_ids = list(projects_qs.values_list("id", flat=True))
    projects_total = len(project_ids)
    active_projects = projects_qs.filter(status=ProjectStatus.ACTIVE).count()
    approved_budget = decimal_sum(projects_qs, "approved_budget")
    executed_budget = decimal_sum(InvoiceAllocation.objects.filter(project_id__in=project_ids), "allocated_amount")
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

    return {
        "items": projects_qs.order_by("name"),
        "financiers": get_financiers(),
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

@group_required("admins","managers", "employee")
def projects(request):
    return render(request, "projects/projects.html", get_projects_dashboard_context(request.user))

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
def invoice_list(request):
    return render(request, "projects/invoice-list.html", get_invoice_context(request.user))


@group_required("admins","managers", "employee")
def invoice_form(request):
    obj = get_or_none(Invoice, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
    return render(request, "projects/invoice-form.html", {
        "obj": obj,
    })


@group_required("admins","managers", "employee")
def invoice_save(request):
    try:
        obj = get_or_none(Invoice, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else Invoice()
        if obj == None:
            return HttpResponse("Factura no encontrada.", status=404)

        obj.provider_tax_id = get_param(request.GET, "provider_tax_id").strip().upper()
        obj.number = get_param(request.GET, "number").strip()
        obj.issue_date = get_param(request.GET, "issue_date") or None
        obj.payment_date = get_param(request.GET, "payment_date") or None
        obj.concept = get_param(request.GET, "concept").strip()
        obj.taxable_base = parse_decimal(get_param(request.GET, "taxable_base"))
        obj.taxes = parse_decimal(get_param(request.GET, "taxes"))
        obj.currency = "EUR"
        if not obj.pk:
            obj.status = InvoiceStatus.DRAFT
        obj.total_amount = obj.taxable_base + obj.taxes
        obj.full_clean()
        obj.save()
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
    invoice = get_or_none(Invoice, get_param(request.GET, "invoice_id"))
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

        contribution = get_or_none(FinancierContribution, get_param(request.GET, "financier_contribution"))
        if contribution == None or contribution.project_id != project.id:
            return HttpResponse("Debes seleccionar una aportación válida para el proyecto.", status=400)

        selected_budget_line = get_or_none(BudgetLine, get_param(request.GET, "budget_line"))
        contribution_target = contribution.sub_budget_line or contribution.budget_line
        if selected_budget_line == None or contribution_target == None or selected_budget_line.id != contribution_target.id:
            return HttpResponse("La aportación no pertenece a la partida seleccionada.", status=400)

        activity = get_or_none(Activity, get_param(request.GET, "activity")) if get_param(request.GET, "activity") else None
        if activity != None and activity.project_id != project.id:
            return HttpResponse("La actividad debe pertenecer al proyecto seleccionado.", status=400)

        allocation_mode = get_param(request.GET, "allocation_mode", "amount")
        max_available = min(invoice.pending_amount, contribution.available_amount)
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
            return HttpResponse("No se puede imputar más que el máximo disponible para esta factura y aportación.", status=400)

        allocation = InvoiceAllocation(
            invoice=invoice,
            project=project,
            activity=activity,
            budget_line=contribution.budget_line or contribution_target.root_line,
            sub_budget_line=contribution.sub_budget_line,
            financier_contribution=contribution,
            financier=contribution.financier,
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
        if project.invoice_allocations.filter(financier=obj.financier).exists():
            return HttpResponse("No se puede eliminar porque este financiador ya tiene facturas imputadas.", status=400)
        obj.delete()
        return render(request, "project/financiers/financier-list.html", get_project_financiers_context(project))
    except ProtectedError:
        return HttpResponse("No se puede eliminar porque hay aportaciones o facturas vinculadas.", status=400)
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
            "projects.budgetline": {"approved_budget", "modified_budget"},
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

    def append_tree_rows(rows, sub_line, level):
        rows.append({
            "item": sub_line,
            "level": level,
            "can_add_child": level < BudgetLine.MAX_DEPTH,
        })
        for child in children_by_parent.get(sub_line.id, []):
            append_tree_rows(rows, child, level + 1)

    for budget_line in budget_lines:
        rows = []
        for sub_line in children_by_parent.get(budget_line.id, []):
            append_tree_rows(rows, sub_line, 1)
        budget_line.tree_sub_lines = rows

    return {
        'obj': project,
        'budget_lines': budget_lines,
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
            budget_line = obj.sub_budget_line or obj.budget_line
        if budget_line == None:
            return render(request, 'error_exception.html', {'exc':'Subpartida no encontrada!'})
        return render(request, "project/budget-lines/financier-contribution-form.html", {
            "obj": obj,
            "budget_line": budget_line,
            "project": budget_line.project,
            "project_financiers": budget_line.project.project_financiers.select_related("financier").order_by("financier__name"),
            "financier_types": FinancierType.choices,
        })
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_financier_contribution_save(request):
    try:
        budget_line = get_or_none(BudgetLine, get_param(request.GET, "budget_line_id"))
        obj = get_or_none(FinancierContribution, get_param(request.GET, "obj_id")) if get_param(request.GET, "obj_id") else None
        if budget_line == None and obj != None:
            budget_line = obj.sub_budget_line or obj.budget_line
        if budget_line == None:
            return HttpResponse("Subpartida no encontrada.", status=404)

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
        obj.budget_line = budget_line.root_line
        obj.sub_budget_line = budget_line
        obj.amount = amount
        if budget_line.effective_budget:
            obj.percentage = (amount * Decimal("100")) / budget_line.effective_budget
        obj.notes = get_param(request.GET, "notes")
        obj.full_clean()
        obj.save()
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
        obj.delete()
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
    print(file_list)
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


@group_required("admins","managers", "employee")
def project_budget_line_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(BudgetLine, request.GET["obj_id"]) if "obj_id" in request.GET else BudgetLine.objects.create(
            project=project,
            code=get_next_budget_line_code(project),
        )
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
            obj = BudgetLine.objects.create(
                project=parent.project,
                parent=parent,
                code=get_next_sub_budget_line_code(parent),
            )
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
        for f in file_list:
            print(f.name)
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
        print(e)
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
