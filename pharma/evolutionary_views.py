from django.core.mail import send_mail
from django.http import HttpResponse
from django.shortcuts import render, reverse
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

from weasyprint import HTML 

from datetime import datetime, timedelta

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from capsulae2.email_lib import send_derivation_email

from account.models import Company
from community.models import Organization
from .models import Pacientes
from .evolutionary_models import Evolutionary 


'''
    Evolutionary
'''
@group_required("admins", "managers")
def evolutionary_form(request):
    try:
        patient = get_or_none(Pacientes, request.GET["patient_id"])
        if "obj_id" in request.GET:
            obj = get_or_none(Evolutionary, request.GET['obj_id'])  
        else:
            obj = Evolutionary.objects.create(patient=patient)
        return render(request, "patient/evolutionary/evo-form.html", {'obj': obj})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins", "managers")
def evolutionary_remove(request):
    try:
        evo = get_or_none(Evolutionary, request.GET["obj_id"])
        patient = evo.patient
        evo.delete()
        return render(request, "patient/evolutionary/evo-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Derivación
'''
def evolutionary_referral_form(request, history_num, evolutionary_id=None, view=False):
    """
        Muestra el formulario de derivación para el paciente cuyo numero de historial
        coincide con el <history_num> pasado como parámetro

        :param request: Objeto tipo <Django.request>
        :param history_num str: Numero de historial único del paciente
    """

    patient = Pacientes.objects.filter(n_historial=history_num).first()
    context = {'view': bool(view)}
    context['patient'] = patient
    context['company'] = Company.objects.filter(manager=patient.id_user).first()
    if request.user.is_superuser:
        context['org_list'] = Organization.objects.all()
    else:
        context['org_list'] = Organization.objects.filter(comp=context["company"])
    if evolutionary_id != None:
        ev = Evolutionary.objects.get(pk=evolutionary_id)
        #print(ev.matter)
        context["evolutionary"] = ev
        context["professional"] = ev.observations[(ev.observations.find("Profesional:")+12):ev.observations.find("Observaciones:")-5]
        context["observations"] = ev.observations[(ev.observations.find("Observaciones:")+14):]
        context["organization"] = ev.matter[(ev.matter.find("Derivación a: ")+14):]
    return render(request, "patient/evolutionary/evo-referral-form.html", context)


def evolutionary_send_form(request):
    msg = "Formulario enviado correctamente"
    val = ""
    try:
        if request.POST:
            patient = get_or_none(Pacientes, request.POST["patient"])
            company = request.POST["company"]
            org_list = request.POST["organization"].split("|")

            #val = "{}Organización: {}<br/>".format(val, request.POST["organization"])
            val = set_field(request.POST, val, "field1", "¿La persona vive sola?")
            val = set_field(request.POST, val, "field2", "¿Vive con alguna persona cuidadora de similar edad y/o personas con discapacidad,con problemas de salud mental, menores de edad?")
            val = set_field(request.POST, val, "field3", "¿Cuenta con una red social en la que poder apoyarse?")
            val = set_field(request.POST, val, "field4", "¿Existe barrera idiomática?")
            val = set_field(request.POST, val, "field5", "¿Migrante?")
            val = set_field(request.POST, val, "field6", "¿Está en situación de dependencia?")
            val = set_field(request.POST, val, "field7", "¿Población excluida de Tarjeta Sanitaria?")
            val = set_field(request.POST, val, "field8", "¿Recibe algún tipo de ayuda?")
            val = set_field(request.POST, val, "field9", "¿Discapacidad reconocida?")
            val = set_field(request.POST, val, "field10", "¿Cuenta con una vivienda que reúna las condiciones de habitabilidad?")
            val = "{}<br/>Profesional: {}".format(val, request.POST["prof"])
            val = "{}<br/>Observaciones: {}".format(val, request.POST["obs"])
            ev = Evolutionary.objects.create(patient=patient, observations=val, matter="Derivación a: {}".format(org_list[0]))

            if org_list[1] != "":
                html = "Derivación del paciente <strong>{} {}</strong> con los siguientes datos:<br/><br/>".format(patient.nombre, patient.apellido)
                html = "{}{}<br/><br/>".format(html, val)
                link = "Puede ver la hoja de derivación a través de <a href='{}'>este enlace</a>".format(request.build_absolute_uri(reverse('evolutionary-referral-form', kwargs={'history_num':patient.n_historial, 'evolutionary_id': ev.id})))
                html = "{}{}".format(html, link)
                #send_mail('Derivación de paciente', 'Derivación de paciente', 'info@capsulae.org', [org_list[1]], html_message=html)
                send_derivation_email([org_list[1]], html)
            else:
                msg = "ERROR: email not found!"
    except Exception as e:
        print(e)
        msg = "ERROR: {}".format(e)
    return render(request, "patient/evolutionary/evo-send-form.html", {'msg': msg})

def set_field(dic, val, field, text):
    if field in dic:
        list_fields = ["field3", "field8", "field10"]
        if field in list_fields:
            return "{}{}: No<br/>".format(val, text) if dic[field] == "1" else "{}{}: Si<br/>".format(val, text)
        else:
            return "{}{}: Si<br/>".format(val, text) if dic[field] == "1" else "{}{}: No<br/>".format(val, text)
    else:
        return "{}{}: <br/>".format(val, text)

