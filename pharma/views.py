from django.core.files import File
#from django.contrib.auth import logout
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.template.loader import render_to_string

from datetime import datetime, timedelta
from weasyprint import HTML, CSS

import os, csv

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from capsulae2.settings import MEDIA_ROOT
from capsulae2.capsulae_lib import check_user_payment
#from account.models import Company, UserPayment
from account.models import Company
from lopd.models import LOPDConsents
from community.models import Organization, PatientOrg, Procedure, PatientProcedure
from medication.medication_lib import get_medication
from medication.models import PresentationsPrescriptionsAempsCache as AempsCache
from dispensations.models import Dispensation
from .models import Pacientes, Paises, Etnia, PatientOrigin
from .spd_models import Pillbox
from .treatment_models import Tratamiento, MedicamentoTratamiento, ComplementoTratamiento
from .evolutionary_models import Evolutionary
from .allergy_models import AlergiasExcipientes, AlergiasPrincipios, Excipientesedo, PrincipiosActivos
from .common_lib import LOPD_LIMIT, PILLBOX_ADVISE, get_config_value
from .pharma_lib import get_values_to_interactions_print, get_values_to_summary_print
from .telegram_models import TelegramUserChat


#def check_user_payment(user):
#    now = datetime.now()
#    up = UserPayment.objects.filter(user = user, expire_date__gte = now).first()
#    if up == None:
#        return False
#    return True

@group_required("admins","managers","employee","donor")
def index(request):
#    if  not check_user_payment(request.user):
#        if request.user.is_superuser:
#            return(redirect('/admin/'))
#        else:
#            logout(request)
#        return redirect('pharma-payment-error')
#    if not check_user_payment(request.user):
#        logout(request)
#        return redirect('pharma-payment-error')
    return render(request, "index.html", {})

def home(request):
    return render(request, "home.html", {})

#def payment_error(request):
#    up = UserPayment.objects.all().order_by('-expire_date').first()
#    return render(request, "error-payments.html", {'payment': up})

'''
    Patients
'''
def get_patients(user, search_value="", start=0, end=50):
    #filters_to_search = ["n_historial__icontains", "nombre__icontains", "apellido__icontains", "cip__icontains"]
    filters_to_search = ["n_historial__icontains", "cip__icontains"]

    full_query = Q()
    if search_value != "":
        for myfilter in filters_to_search:
            full_query |= Q(**{myfilter: search_value})

        search_list = search_value.split(" ", 1)
        name_query = Q(**{"nombre__icontains": search_list[0]})
        if len(search_list) > 1:
            name_query &= Q(**{"apellido__icontains": search_list[1]})
        else:
            name_query |= Q(**{"apellido__icontains": search_list[0]})
        full_query |= name_query

    full_query &= Q(**{'id_user': user.id})

    # Pacientes con lopd firmada
    lopd_patient_ids = LOPDConsents.objects.all().distinct().values_list('paciente', flat=True)
    lopd_list = list(Pacientes.objects.filter(full_query).filter(id__in=lopd_patient_ids)[start:end])

    # Pacientes sin lopd firmada pero creados en los últimos 15 días
    try:
        lopd_limit = int(get_config_value("LOPD_{}".format(user.id), LOPD_LIMIT))
    except:
        lopd_limit = LOPD_LIMIT
    limit = datetime.today() - timedelta(days=lopd_limit)
    date_list = list(Pacientes.objects.filter(full_query).exclude(id__in=lopd_patient_ids).filter(created_at__gte=limit))

    return date_list + lopd_list

def get_patient_context(user, search_value="", start=0, end=50):
    if (search_value == ""):
        return {'items': get_patients(user, search_value, start, end), 'start': (start+end), 'end': (end+end)}
    return {'items': get_patients(user, search_value, start, end),}

@group_required("admins","managers")
def patients(request):
    return render(request, "patients/patients.html", {})
    #return render(request, "patients/patients.html", get_patient_context(request.user))

@group_required("admins","managers")
def patient_list(request):
    start = int(request.GET["start"]) if "start" in request.GET else 0
    end = int(request.GET["end"]) if "end" in request.GET else 50
    return render(request, "patients/patient-list.html", get_patient_context(request.user, "", start, end))

@group_required("admins","managers")
def patient_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "patients/patient-list.html", get_patient_context(request.user, search_value))

@group_required("admins","managers")
def patient_new(request):
    obj = Pacientes.objects.create(id_user=request.user)
    po, created = PatientOrigin.objects.get_or_create(patient=obj)
    return redirect(reverse('patient-view', kwargs={'patient_id': obj.id}))

@group_required("admins","managers")
def patient_remove_msg(request):
    context = {'user': request.user, 'patient': get_or_none(Pacientes, request.GET["obj_id"])}
    return render(request, "patients/patient-remove-dialog.html", context)

@group_required("admins","managers")
def patient_soft_remove(request):
    obj = get_or_none(Pacientes, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.activo = False
        obj.save()
        #obj.delete()
    return render(request, "patients/patient-list.html", get_patient_context(request.user))

@group_required("admins","managers")
def patient_remove(request):
    obj = get_or_none(Pacientes, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "patients/patient-list.html", get_patient_context(request.user))

@group_required("admins", "managers")
def patient_evolutionaries(request):
    ev_list = Evolutionary.objects.filter(matter__contains="Derivación", patient__id_user = request.user.id)
    return render(request, "patients/evolutionary/evo-list.html", {'ev_list': ev_list})

def get_obs_answer(question, text):
    if "{}: Si".format(question) in text:
        return "Si"
    if "{}: No".format(question) in text:
        return "No"
    return "-"

@group_required("admins")
def patient_evolutionaries_csv(request):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="derivaciones.csv"'

    writer = csv.writer(response, delimiter='|')
    ev_list = Evolutionary.objects.filter(matter__contains="Derivación")

    header = [
        'Paciente', 
        'Genero', 
        'Teléfono', 
        'Asunto', 
        'Fecha', 
        'Profesional',
        'Organización',
        '¿La persona vive sola?',
        '¿Vive con alguna persona cuidadora de similar edad y/o personas con discapacidad,con problemas de salud mental, menores de edad?',
        '¿Cuenta con una red social en la que poder apoyarse?',
        '¿Existe barrera idiomática?',
        '¿Migrante?',
        '¿Está en situación de dependencia?',
        '¿Población excluida de Tarjeta Sanitaria?',
        '¿Recibe algún tipo de ayuda?',
        '¿Discapacidad reconocida?',
        '¿Cuenta con una vivienda que reúna las condiciones de habitabilidad?',
        'Observaciones'
    ]

    #writer.writerow(['Paciente', 'Genero', 'Teléfono', 'Asunto', 'Fecha', 'Observaciones'])
    writer.writerow(header)
    for ev in ev_list:
        name = "{} {}".format(ev.patient.nombre, ev.patient.apellido)
        prof = ev.observations[(ev.observations.find("Profesional:")+12):ev.observations.find("Observaciones:")-5]
        obs = ev.observations[(ev.observations.find("Observaciones:")+14):] if "Observaciones:" in ev.observations else ev.observations
        q1 = get_obs_answer("¿La persona vive sola?", ev.observations)
        q2 = get_obs_answer("¿Vive con alguna persona cuidadora de similar edad y/o personas con discapacidad,con problemas de salud mental, menores de edad?", ev.observations)
        q3 = get_obs_answer("¿Cuenta con una red social en la que poder apoyarse?", ev.observations)
        q4 = get_obs_answer("¿Existe barrera idiomática?", ev.observations)
        q5 = get_obs_answer("¿Migrante?", ev.observations)
        q6 = get_obs_answer("¿Está en situación de dependencia?", ev.observations)
        q7 = get_obs_answer("¿Población excluida de Tarjeta Sanitaria?", ev.observations)
        q8 = get_obs_answer("¿Recibe algún tipo de ayuda?", ev.observations)
        q9 = get_obs_answer("¿Discapacidad reconocida?", ev.observations)
        q10 = get_obs_answer("¿Cuenta con una vivienda que reúna las condiciones de habitabilidad?", ev.observations)
        org = ev.matter[(ev.matter.find("Derivación a: ")+14):]
        writer.writerow([name, ev.patient.sexo, ev.patient.telefono1, ev.matter, ev.date, prof, org, q1, q2, q3, q4, q5, q6, q7, q8, q9, q10, obs])
    return response

'''
    Patient
'''
@group_required("admins","managers")
def patient_view(request, patient_id):
    patient = get_or_none(Pacientes, patient_id)
    po, created = PatientOrigin.objects.get_or_create(patient=patient)
    return render(request, "patient/patient-view.html", {'obj': patient, 'country_list': Paises.objects.all(), 'etnia_list': Etnia.objects.all()})

@group_required("admins","managers")
def patient_form(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/patient-personal.html", {'obj': patient, 'country_list': Paises.objects.all(), 'etnia_list': Etnia.objects.all()})

@group_required("admins","managers")
def patient_treatment(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/treatments/treatment-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_allergy(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/allergies/allergy-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_lopd(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/lopd/lopd-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_spd(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/spd/spd-list.html", {'obj': patient, 'advice_days': PILLBOX_ADVISE})

@group_required("admins","managers")
def patient_evolutionary(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/evolutionary/evo-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_procedure(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/procedures/procedure-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_params(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/parameters/param-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_telegram(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/telegram/chat-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_diagnoses(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/diagnoses/diagnosis-list.html", {'obj': patient})

@group_required("admins","managers")
def patient_dispensations(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/dispensations/dispensations-list.html", {'obj': patient})


'''
    Patient Org
'''
@group_required("admins","managers")
def patient_orgs(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "obj_id"))
    return render(request, "patient/patient-orgs.html", {'obj': patient})

@group_required("admins","managers")
def patient_org_form(request):
    try:
        patient = get_or_none(Pacientes, request.GET["patient_id"])
        
        if "obj_id" in request.GET:
            obj = get_or_none(PatientOrg, request.GET['obj_id'])  
        else:
            obj = PatientOrg.objects.create(patient=patient)
        org_list = Organization.objects.all()
        return render(request, "patient/patient-org-form.html", {'obj': obj, 'org_list': org_list})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_org_remove(request):
    try:
        po = get_or_none(PatientOrg, request.GET["obj_id"])
        patient = po.patient
        po.delete()
        return render(request, "patient/patient-orgs.html", {'obj': patient, 'advice_days': PILLBOX_ADVISE})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Treatment
'''
#def add_medication_to_treatment(treatment, medic):
#    medic_json = medic.toJSON()
#    mt, created = MedicamentoTratamiento.objects.get_or_create(tratamiento=treatment)
#    mt.name = medic_json["name"]
#    mt.cn = medic_json["cn"]
#    mt.code = medic_json["code"]
#    mt.principles = medic_json["principles"]
#    mt.atcs = ','.join([item["codigo"] for item in medic_json["atcs"]])
#    mt.save()
#
#@group_required("admins","managers")
#def patient_treatment_form(request):
#    try:
#        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
#        if patient == None:
#            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})
#
#        obj = get_or_none(Tratamiento, request.GET["obj_id"]) if "obj_id" in request.GET else Tratamiento.objects.create(paciente=patient)
#
#        medic = get_or_none(AempsCache, get_param(request.GET, "medication_id"))
#        if medic != None:
#            add_medication_to_treatment(obj, medic)
#
#        return render(request, "patient/treatments/treatment-form.html", {'obj': obj, 'med': obj.medicamentos.first()})
#    except Exception as e:
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
#@group_required("admins","managers")
#def patient_treatment_soft_remove(request):
#    try:
#        obj = get_or_none(Tratamiento, request.GET["obj_id"])
#        obj.activo = False
#        obj.save()
#
#        return render(request, "patient/treatments/treatment-list.html", {'obj': obj.patient})
#    except Exception as e:
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
#@group_required("admins","managers")
#def patient_treatment_remove(request):
#    try:
#        obj = get_or_none(Tratamiento, request.GET["obj_id"])
#        patient = obj.paciente
#        obj.delete()
#
#        return render(request, "patient/treatments/treatment-list.html", {'obj': patient})
#    except Exception as e:
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
#@group_required("admins","managers")
#def patient_treatment_medication_search(request):
#    patient_id = get_param(request.GET, "patient_id")
#    search_value = get_param(request.GET, "value")
#    return render(request, "patient/treatments/medication-list.html", {'patient_id': patient_id, 'items': get_medication(search_value)})
#
#@group_required("admins","managers")
#def patient_complement_form(request):
#    try:
#        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
#        if patient == None:
#            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})
#
#        obj = get_or_none(Tratamiento, request.GET["obj_id"]) if "obj_id" in request.GET else Tratamiento.objects.create(paciente=patient)
#        ct = ComplementoTratamiento.objects.create(tratamiento=obj) if obj.complementos.all().first() == None else obj.complementos.all().first()
#
#        return render(request, "patient/treatments/complement-form.html", {'obj': obj, 'complement': ct})
#    except Exception as e:
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
#@group_required("admins","managers")
#def patient_treatments_print(request, patient_id):
#    try:
#        patient = get_or_none(Pacientes, patient_id)
#        context = get_values_to_summary_print(patient, request.get_host())
#
#        html_template = render_to_string('patient/treatments/treatments-print.html', context)
#        pdf_file = HTML(string=html_template).write_pdf()
#        response = HttpResponse(pdf_file, content_type='application/pdf')
#        response['Content-Disposition'] = 'filename="tratamientos.pdf"'
#        response['Content-Transfer-Encoding'] = 'binary'
#        return response
#
#        #return render(request, "patient/treatments/treatments-print.html", context)
#    except Exception as e:
#        print(e)
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
#@group_required("admins","managers")
#def patient_treatments_print_tags(request, patient_id):
#    try:
#        patient = get_or_none(Pacientes, patient_id)
#        tratamientos = Tratamiento.objects.filter(paciente=patient, activo=True)
#
#        context = {'url_base' : request.get_host(), 'tratamientos': tratamientos, 'paciente': patient}
#        return render(request, "patient/treatments/treatments-print-tags.html", context)
#    except Exception as e:
#        print(e)
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
#@group_required("admins","managers")
#def patient_summary(request, patient_id):
#    try:
#        patient = get_or_none(Pacientes, patient_id)
#        context = get_values_to_summary_print(patient, request.get_host())
#        return render(request, "patient/treatments/summary-print.html", context)
#    except Exception as e:
#        print(e)
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
#@group_required("admins","managers")
#def patient_interactions_comment(request):
#    patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
#    if patient == None:
#        return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})
#    return render(request, "patient/treatments/interactions-comment.html", {'obj': patient,})
#
#@group_required("admins","managers")
#def patient_interactions_print(request):
#    try:
#        patient = get_or_none(Pacientes, request.POST["patient_id"])
#        comments = request.POST["comments"]
#        context = get_values_to_interactions_print(patient, comments, request.get_host())
#        return render(request, "patient/treatments/interactions-print.html", context)
#    except Exception as e:
#        print(e)
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})
#
'''
    Procedure
'''
@group_required("admins","managers")
def patient_procedure_form(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        obj = get_or_none(PatientProcedure, request.GET["obj_id"]) if "obj_id" in request.GET else PatientProcedure.objects.create(patient=patient)
        return render(request, "patient/procedures/procedure-form.html", {'obj': obj, 'procedure_list': Procedure.objects.all()})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers")
def patient_procedure_remove(request):
    try:
        obj = get_or_none(PatientProcedure, request.GET["obj_id"])
        patient = obj.patient
        obj.delete()

        return render(request, "patient/procedures/procedure-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})



'''
    Allergy
'''
@group_required("admins","managers")
def patient_allergy_excipients(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        if "obj_id" in request.GET:
            edo = get_or_none(Excipientesedo, request.GET["obj_id"])
            AlergiasExcipientes.objects.create(n_orden=patient, edo=edo)

        edo_list = [item.edo.codigoedo for item in patient.alergias_excipientes.all()]
        item_list = Excipientesedo.objects.all().exclude(codigoedo__in=edo_list)
        return render(request, "patient/allergies/excipient-list.html", {'obj': patient, 'item_list': item_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_allergy_principles(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        if "obj_id" in request.GET:
            pa = get_or_none(PrincipiosActivos, request.GET["obj_id"], "codigoprincipioactivo")
            AlergiasPrincipios.objects.create(paciente=patient, principio_activo=pa)

        p_list = []
        for item in patient.alergias_principios.all():
            if item.principio_activo != None:
                p_list.append(item.principio_activo.codigoprincipioactivo)
        item_list = PrincipiosActivos.objects.all().exclude(codigoprincipioactivo__in=p_list)
        return render(request, "patient/allergies/principles-list.html", {'obj': patient, 'item_list': item_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers")
def patient_allergy_excipient_remove(request):
    try:
        obj = get_or_none(AlergiasExcipientes, request.GET["obj_id"])
        patient = obj.n_orden
        obj.delete()

        ae_list = AlergiasExcipientes.objects.filter(n_orden = patient.id)
        return render(request, "patient/allergies/allergy-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_allergy_principle_remove(request):
    try:
        obj = get_or_none(AlergiasPrincipios, request.GET["obj_id"])
        patient = obj.paciente
        obj.delete()

        return render(request, "patient/allergies/allergy-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_allergy_excipients_search(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        value = get_param(request.GET, "s-name")
        if value != "":
            item_list = patient.alergias_excipientes.filter(edo__edo__icontains=value)
        else:
            item_list = patient.alergias_excipientes.all()

        return render(request, "patient/allergies/allergy-list-excipient-list.html", {'exp_list': item_list,})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_allergy_principles_search(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        value = get_param(request.GET, "s-name-pri")
        if value != "":
            item_list = patient.alergias_principios.filter(principio_activo__principioactivo__icontains=value)
        else:
            item_list = patient.alergias_principios.all()

        print(item_list)
        return render(request, "patient/allergies/allergy-list-principles-list.html", {'pri_list': item_list,})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_allergy_excipient_list_search(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        if "obj_id" in request.GET:
            edo = get_or_none(Excipientesedo, request.GET["obj_id"])
            AlergiasExcipientes.objects.create(n_orden=patient, edo=edo)

        value = get_param(request.GET, "s-exc-name")

        edo_list = [item.edo.codigoedo for item in patient.alergias_excipientes.all()]
        item_list = Excipientesedo.objects.filter(edo__icontains=value).exclude(codigoedo__in=edo_list)
        return render(request, "patient/allergies/excipient-list-rows.html", {'obj': patient, 'item_list': item_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_allergy_principles_list_search(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        if "obj_id" in request.GET:
            pa = get_or_none(PrincipiosActivos, request.GET["obj_id"], "codigoprincipioactivo")
            AlergiasPrincipios.objects.create(paciente=patient, principio_activo=pa)

        value = get_param(request.GET, "s-pri-name")

        p_list = []
        for item in patient.alergias_principios.all():
            if item.principio_activo != None:
                p_list.append(item.principio_activo.codigoprincipioactivo)
        item_list = PrincipiosActivos.objects.filter(principioactivo__icontains=value).exclude(codigoprincipioactivo__in=p_list)
        return render(request, "patient/allergies/principles-list-rows.html", {'obj': patient, 'item_list': item_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Lopd
'''
@group_required("admins","managers")
def patient_lopd_add(request):
    try:
        obj_id = request.POST["obj_id"]
        signed_doc = request.FILES["file"]

        patient = get_or_none(Pacientes, obj_id)
        if patient != None:
            lopd = LOPDConsents.objects.create(paciente = patient, document = signed_doc)
        return render(request, "patient/lopd/lopd-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'msg': str(e)})

@group_required("admins","managers")
def patient_lopd_remove(request):
    try:
        obj_id = request.GET["obj_id"]
        obj = get_or_none(LOPDConsents, obj_id)
        patient = obj.paciente
        obj.document.delete(save=True)
        obj.delete()

        return render(request, "patient/lopd/lopd-list.html", {'obj': patient})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'msg': str(e)})

@group_required("admins","managers")
def patient_lopd_generate_document(request, patient_id):
    context={}

    try:
        patient = Pacientes.objects.get(pk=patient_id)
        context['patient'] = patient
        context['company'] = request.user.company
    except Exception as e:
        print(e)

    return render(request, "patient/lopd/lopd-document-template.html", context)


def patient_lopd_generate_signed_document(request, patient_id):
    context = {}
    response ="<h3>400 BAD REQUEST</h3>"
    if request.method =="POST":
        company_id = get_param(request.POST, "company", None)
        signature = get_param(request.POST, "patient_signature", None)
        check1 = get_param(request.POST, "check1", "True")
        check2 = get_param(request.POST, "check2", "True")
        check3 = get_param(request.POST, "check3", "True")
        prof_signature = get_param(request.POST, 'professional_signature', None)
        #if company_id != None and signature != None:
        if company_id != None:
            patient = Pacientes.objects.get(pk = patient_id)
            company = Company.objects.get(pk = company_id)

            check1 = "checked.png" if check1 == "True" else "unchecked.png"
            check2 = "checked.png" if check2 == "True" else "unchecked.png"
            check3 = "checked.png" if check3 == "True" else "unchecked.png"

            context = {
                'request' : request,
                'patient' : patient,
                'company' : company,
                'signature': signature,
                'check1_img': check1,
                'check2_img': check2,
                'check3_img': check3,
                'signing': True,
                'host': "%s://%s"%(request.scheme, request.META['HTTP_HOST']),

            }
            html_template = render_to_string("patient/lopd/lopd-signed-template.html", context)

            lopd_dir = os.path.abspath(os.path.join(MEDIA_ROOT, 'lopd_files'))
            if not os.path.exists(lopd_dir):
                os.makedirs(lopd_dir)

            date_str = datetime.now().strftime("%d%m%Y%H%M")
            filename = "signed_consent_{0}_{1}.pdf".format(patient.nif, date_str)
            filepath = os.path.join(lopd_dir,filename)

            consent = LOPDConsents(paciente=patient)
            with open(filepath, 'wb+') as pdf_file :
                filepath = os.path.join(lopd_dir, filename )
                pdf_content = HTML(string=html_template).write_pdf()
                pdf_file.write(pdf_content)
                consent.document.save(filename, File(pdf_file), save=True)
                consent.save()

            response = HttpResponse(pdf_content, content_type="application/pdf")
            response['Content-Disposition'] = 'filename="{0}"'.format(filename)
            response['Content-Transfer-Encoding']= 'binary'
            return response

    return HttpResponse(response)


