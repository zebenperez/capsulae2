from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q
from .models import Pacientes
from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none
from account.models import Company

@group_required("admins","managers")
def vulnera_list(request, comp):
    comp = get_or_none(Company, comp)
    full_query = Q()
    full_query &= (Q(**{'id_user__company': comp}) | Q(**{'id_user__user_companies__in': [comp]}))
    p_list = Pacientes.objects.filter(full_query)
    no_info_list = []
    signed_list = []
    not_signed_list = []
    for p in p_list:
        #print(p.nombre)
        info = False
        signed = False
        for lopd in p.lopd.all():
            name = lopd.document.name.lower()
            if "vulnerabilidad" in name:
                info = True
            if "vulnerabilidad" in name and ("firmado" in name or "signed" in name):
                signed = True
        if info and signed:
            signed_list.append(p)
        elif info:
            not_signed_list.append(p)
        else:
            no_info_list.append(p)
    return render(request, "patients/aux/vulnera-list.html", {"no_info_list": no_info_list, "signed_list": signed_list, "no_signed_list": not_signed_list})
