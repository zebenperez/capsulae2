from decimal import Decimal, InvalidOperation

from django import template
from django.utils.safestring import mark_safe
from projects.common_lib import get_folder_path_link

register = template.Library()


@register.simple_tag()
def get_folder_pathway(folder, project_id):
    return mark_safe(get_folder_path_link(folder, folder, project_id))


@register.filter()
def date_es(value):
    if not value:
        return ""
    months = [
        "",
        "enero",
        "febrero",
        "marzo",
        "abril",
        "mayo",
        "junio",
        "julio",
        "agosto",
        "septiembre",
        "octubre",
        "noviembre",
        "diciembre",
    ]
    date_value = value.date() if hasattr(value, "date") else value
    return "{} de {} de {}".format(date_value.day, months[date_value.month], date_value.year)


@register.filter()
def money_es(value, currency="€"):
    if value in (None, ""):
        value = Decimal("0.00")
    try:
        amount = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return value
    formatted = "{:,.2f}".format(amount).replace(",", "X").replace(".", ",").replace("X", ".")
    return "{} {}".format(formatted, currency or "€")
