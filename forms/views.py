from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from django.views.decorators.csrf import csrf_exempt

from capsulae2.commons import get_param, get_or_none
from pharma.models import Pacientes, PatientOrigin, Etnia, Paises
from account.models import Company
from community.models import Procedure, PatientProcedure, PatientProcedureDoc
from capsulae2.email_lib import send_import_doc_email


def regulariza(request, org):
    etnias = Etnia.objects.all()
    countries = Paises.objects.all()
    return render(request, "forms/regulariza.html", {'comp': org, 'countries': countries, 'etnias': etnias})

def regulariza_save(request):
    comp = get_or_none(Company, get_param(request.POST, "comp"))
    if request.POST and comp != None:
        name = get_param(request.POST, "name")
        sex = get_param(request.POST, "sex")
        passport = get_param(request.POST, "passport")
        born_date = get_param(request.POST, "born_date")
        nationality = get_param(request.POST, "nationality")
        locality = get_param(request.POST, "locality")
        address = get_param(request.POST, "address")
        province = get_param(request.POST, "province")
        cp = get_param(request.POST, "cp")
        phone = get_param(request.POST, "phone")
        email = get_param(request.POST, "email")
        languaje = get_param(request.POST, "languaje")
        etnia = get_or_none(Etnia, get_param(request.POST, "etnia"))
        country = get_or_none(Paises, get_param(request.POST, "country"))
        privacy = get_param(request.POST, "privacy")
        tos = get_param(request.POST, "tos")
        doc = request.FILES["doc"] if "doc" in request.FILES else None
        #print(f"{name} {sex} {passport} {tos} {privacy}")
        #print(doc)
        p = Pacientes.objects.filter(nif=passport).first()
        if p == None:
            p = Pacientes(nif=passport, id_user=comp.manager)
            p.nombre = name
            if sex != "":
                p.sexo = "H" if sex == "hombre" else "M"
            p.fecha_nacimiento = born_date
            p.locality = locality
            p.domicilio = address
            p.province = province
            p.cod_postal = cp
            p.telefono1 = phone
            p.email = email
            p.save()

            po = PatientOrigin(patient = p)
            po.nationality = nationality
            po.etnia = etnia
            po.country = country
            po.save()

            if doc is not None:
                procedure = Procedure.objects.filter(code="01").first()
                patpro = PatientProcedure.objects.create(procedure=procedure, obs="Creada solicitud", patient=p)
                patprodoc = PatientProcedureDoc.objects.create(procedure=patpro, doc=doc)

            try:
                send_import_doc_email(request.META['HTTP_HOST'], [p.email], p.full_name, f.name)
            except:
                pass

            return render(request, "forms/regulariza-save.html", {'comp': comp.id,})
        else:
            return render(request, "forms/regulariza-save.html", {'err': "Este usuario ya ha sido dado de alta!."})
    return render(request, "forms/regulariza-save.html", {'err': "Se ha producido un error, disculpe las molestias!."})

