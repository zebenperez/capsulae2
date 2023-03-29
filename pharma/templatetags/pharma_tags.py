from django import template
from django.utils.safestring import mark_safe

from capsulae2.settings import BASE_DIR

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

