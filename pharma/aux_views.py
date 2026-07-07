from django.http import HttpResponse
from django.shortcuts import render
from django.db.models import Q
from .models import Pacientes
from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none
from account.models import Company
from community.models import PatientProcedure

import csv

@group_required("admins","managers")
def index(request):
    return render(request, "patients/aux/index.html", {})

@group_required("admins","managers")
#def vulnera_list(request, comp):
def vulnera_list(request):
    #comp = get_or_none(Company, comp)
    comp = Company.get_by_user(request.user)
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

@group_required("admins","managers")
def vulnera_list_export(request, list_type):
    comp = Company.get_by_user(request.user)
    full_query = Q()
    full_query &= (Q(**{'id_user__company': comp}) | Q(**{'id_user__user_companies__in': [comp]}))
    p_list = Pacientes.objects.filter(full_query)
    #no_info_list = []
    #signed_list = []
    #not_signed_list = []
    item_list = []
    for p in p_list:
        info = False
        signed = False
        for lopd in p.lopd.all():
            name = lopd.document.name.lower()
            if "vulnerabilidad" in name:
                info = True
            if "vulnerabilidad" in name and ("firmado" in name or "signed" in name):
                signed = True
        if info and signed and list_type == 2:
            item_list.append(p)
        elif info and list_type == 1:
            item_list.append(p)
        elif list_type == 0:
            item_list.append(p)

    response = HttpResponse( content_type='text/csv', headers={'Content-Disposition': 'attachment; filename="datos.csv"'},)

    writer = csv.writer(response)
    writer.writerow([
        'Nombre', 
        'Sexo', 
        'Pasaporte', 
        'Fecha de nacimiento', 
        'Nacionalidad', 
        'Domicilio', 
        'Localidad', 
        'Provincia', 
        'Código postal', 
        'Teléfono', 
        'Correo electrónico',
        'País de nacimiento',
        'Etnia'
    ])
    for item in item_list:
        try:
            nationality = item.origin.nationality
            country = item.origin.country
            etnia = item.origin.etnia
        except:
            nationality = ""
            country = ""
            etnia = ""
        writer.writerow([
            item.nombre,
            item.sexo,
            item.nif,
            item.fecha_nacimiento,
            nationality,
            item.domicilio,
            item.province,
            item.cod_postal,
            item.telefono1,
            item.email,
            country,
            etnia
        ])
    return response


@group_required("admins","managers")
#def procedure_not_done(request, comp):
def procedure_not_done(request):
    #comp = get_or_none(Company, comp)
    comp = Company.get_by_user(request.user)
    full_query = Q(**{'done': False})
    full_query &= (Q(**{'patient__id_user__company': comp}) | Q(**{'patient__id_user__user_companies__in': [comp]}))
    p_list = PatientProcedure.objects.filter(full_query)
    return render(request, "patients/aux/procedure-not-done.html", {"item_list": p_list,})

@group_required("admins","managers")
#def vulnera_files(request, comp):
def vulnera_files(request):
    import zipfile, os
    from io import BytesIO

    #comp = get_or_none(Company, comp)
    comp = Company.get_by_user(request.user)
    full_query = Q()
    full_query &= (Q(**{'id_user__company': comp}) | Q(**{'id_user__user_companies__in': [comp]}))
    p_list = Pacientes.objects.filter(full_query)

    files = []
    for p in p_list:
        #print(p.nombre)
        info = False
        signed = False
        for lopd in p.lopd.all().order_by("-id"):
            name = lopd.document.name.lower()
            if "vulnerabilidad" in name:
                info = True
                f = lopd.document
            if "vulnerabilidad" in name and ("firmado" in name or "signed" in name):
                signed = True
        if info and not signed:
            files.append(f)

    buffer = BytesIO()
    with zipfile.ZipFile(buffer, 'w', zipfile.ZIP_DEFLATED) as zipf:
        for f in files:
            nombre = os.path.basename(f.name)
            nombre = f"{id(f)}_{nombre}"
            with f.open('rb') as file_data:
                zipf.writestr(nombre, file_data.read())
    buffer.seek(0)

    response = HttpResponse(buffer, content_type='application/zip')
    response['Content-Disposition'] = 'attachment; filename="archivos.zip"'

    return response


