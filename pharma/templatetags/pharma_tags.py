from django import template
from django.utils.safestring import mark_safe
from datetime import datetime, timedelta

from capsulae2.settings import BASE_DIR
from pharma.models import Pacientes
from pharma.spd_models import Pillbox
from medication.models import FichaPrincipioActivo
from account.models import UserProfile
#from shifts2.models import Journey

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
            return company.image.url
            #url = "/media/companies/{}/logo.png".format(company.code)
            #if os.path.exists("{}{}".format(BASE_DIR, url)):
            #    return url
    except Exception as e:
        print("COMPANY LOGO %s"%(e))
    return ""

@register.filter
def get_ficha(tratamiento):
    med = tratamiento.medicamentos.first()
    if med != None:
        atc = ""
        for code in med.atcs.split(","):
            if len(code) > 5:
                atc = code
        ficha = FichaPrincipioActivo.objects.filter(cod_atc=atc)
        if len(ficha) > 0:
            return ficha[0]
    return None

@register.filter
def is_pharma(user):
    up = UserProfile.objects.filter(user=user).first()
    return (up != None and up.profile != None and up.profile.code == "pharma")

#@register.filter
#def journey_started(user):
#    return (Journey.objects.filter(user=user, started=True).count() > 0)

@register.filter
def get_patients(user):
    return Pacientes.objects.filter(id_user=user).count()

'''
    Simple Tags
'''
@register.simple_tag
def userqr_code(request, paciente):
    import pyqrcode
    url = pyqrcode.create(paciente.n_historial)
    rpath = "/media/codebars/"
    filename = "{}.svg".format(paciente.n_historial)
    url.svg("{}{}{}".format(BASE_DIR, rpath, filename), scale=4)
    out="{}://{}{}{}".format(request.scheme, request.get_host(), rpath, filename)
    return out

@register.simple_tag
def get_atcs_for_print(dictionary, key, salto=True):
    result = ""
    for atc in dictionary.get(str(key)):
        if (salto):
            result = "%s<br>%s" % (result, atc)
        else:
            result = "%s%s" % (result, atc)
    return mark_safe(result)


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
 
#@register.inclusion_tag('journey-list.html')
#def get_journey_list(user):
#    j_list = Journey.objects.filter(user=user)[:10]
#
#    return {'journey_list': j_list}
 
