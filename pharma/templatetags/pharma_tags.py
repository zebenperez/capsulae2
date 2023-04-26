from django import template
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta

from capsulae2.settings import BASE_DIR
from pharma.spd_models import Pillbox

import os

register = template.Library()

'''
    Filters
'''
@register.filter
def have_treatment(pillbox, treatment):
    return pillbox.have_treatment(treatment)

@register.filter
def have_treatment_in_blister(pillbox, treatment):
    return pillbox.have_treatment_in_blister(treatment)

@register.filter
def company_logo(user):
    try:
        company = user.company
        if company == None:
            company = user.user_companies.first()

        if company != None:
            url = "/media/companies/{}/logo.png".format(company.code)
            if os.path.exists("{}{}".format(BASE_DIR, url)):
                return url
    except Exception as e:
        print("COMPANY LOGO %s"%(e))
    return ""

@register.simple_tag
def userqr_code(request, paciente):
    import pyqrcode
    url = pyqrcode.create(paciente.n_historial)
    rpath = "/media/codebars/"
    filename = "{}.svg".format(paciente.n_historial)
    url.svg("{}{}{}".format(BASE_DIR, rpath, filename), scale=4)
    out="{}://{}{}{}".format(request.scheme, request.get_host(), rpath, filename)
    return out

'''
    Inclusion Tags
'''
@register.inclusion_tag('pillbox-list.html')
def get_pillbox_list(user):
    now = datetime.now().date() - timedelta(days=365)
    pillboxes = Pillbox.objects.filter(patient__id_user=user, active=True, pillbox_delivers__finish_date__gte=now).distinct()

    delivers = [pillbox.last_deliver for pillbox in pillboxes]
    delivers = sorted(delivers, key=lambda d: d.finish_date)

    return {'delivers': delivers}
 
