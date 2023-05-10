from django.core.files import File
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.template.loader import render_to_string

from datetime import datetime, timedelta
from weasyprint import HTML, CSS

import os

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from capsulae2.settings import MEDIA_ROOT
from account.models import Company
from lopd.models import LOPDConsents
from community.models import Organization, PatientOrg
from medication.medication_lib import get_medication
from medication.models import PresentationsPrescriptionsAempsCache as AempsCache
from .models import Pacientes, Paises, Etnia, PatientOrigin
from .spd_models import Pillbox
from .treatment_models import Tratamiento, MedicamentoTratamiento
from .evolutionary_models import Evolutionary
from .common_lib import PILLBOX_ADVISE


@group_required("admins","managers")
def index(request):
    return render(request, "index.html", {})

'''
    Patients
'''
def get_patients(user, search_value="", start=0, end=50):
    filters_to_search = ["n_historial__icontains", "nombre__icontains", "apellido__icontains", "cip__icontains"]

    full_query = Q()
    if search_value != "":
        for myfilter in filters_to_search:
            full_query |= Q(**{myfilter: search_value})
    full_query &= Q(**{'id_user': user.id})

    # Pacientes con lopd firmada
    lopd_patient_ids = LOPDConsents.objects.all().distinct().values_list('paciente', flat=True)
    lopd_list = list(Pacientes.objects.filter(full_query).filter(id__in=lopd_patient_ids)[start:end])

    # Pacientes sin lopd firmada pero creados en los últimos 15 días
    limit = datetime.today() - timedelta(days=15)
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
def patient_remove(request):
    obj = get_or_none(Pacientes, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "patients/patient-list.html", get_patient_context(request.user))


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
    return render(request, "patient/patient-form.html", {'obj': patient, 'country_list': Paises.objects.all(), 'etnia_list': Etnia.objects.all()})

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
def add_medication_to_treatment(treatment, medic):
    medic_json = medic.toJSON()
    mt, created = MedicamentoTratamiento.objects.get_or_create(tratamiento=treatment)
    mt.name = medic_json["name"]
    mt.cn = medic_json["cn"]
    mt.code = medic_json["code"]
    mt.principles = medic_json["principles"]
    mt.atcs = ','.join([item["codigo"] for item in medic_json["atcs"]])
    mt.save()

@group_required("admins","managers")
def patient_treatment_form(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        obj = get_or_none(Tratamiento, request.GET["obj_id"]) if "obj_id" in request.GET else Tratamiento.objects.create(paciente=patient)

        medic = get_or_none(AempsCache, get_param(request.GET, "medication_id"))
        if medic != None:
            add_medication_to_treatment(obj, medic)

        return render(request, "patient/treatments/treatment-form.html", {'obj': obj, 'med': obj.medicamentos.first()})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_treatment_remove(request):
    try:
        obj = get_or_none(Tratamiento, request.GET["obj_id"])
        patient = obj.paciente
        obj.delete()

        return render(request, "patient/treatments/treatment-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers")
def patient_treatment_medication_search(request):
    patient_id = get_param(request.GET, "patient_id")
    search_value = get_param(request.GET, "value")
    return render(request, "patient/treatments/medication-list.html", {'patient_id': patient_id, 'items': get_medication(search_value)})


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

