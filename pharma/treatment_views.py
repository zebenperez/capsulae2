from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.template.loader import render_to_string

from datetime import datetime, timedelta
from weasyprint import HTML, CSS

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from community.models import Organization, PatientOrg, Procedure, PatientProcedure
from medication.medication_lib import get_medication
from medication.models import PresentationsPrescriptionsAempsCache as AempsCache
from .models import Pacientes
from .treatment_models import Tratamiento, MedicamentoTratamiento, ComplementoTratamiento
from .pharma_lib import get_values_to_interactions_print, get_values_to_summary_print


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

@group_required("admins","managers")
def patient_complement_form(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        obj = get_or_none(Tratamiento, request.GET["obj_id"]) if "obj_id" in request.GET else Tratamiento.objects.create(paciente=patient)
        ct = ComplementoTratamiento.objects.create(tratamiento=obj) if obj.complementos.all().first() == None else obj.complementos.all().first()

        return render(request, "patient/treatments/complement-form.html", {'obj': obj, 'complement': ct})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_treatments_print(request, patient_id):
    try:
        patient = get_or_none(Pacientes, patient_id)
        context = get_values_to_summary_print(patient, request.get_host())
        context["request"] = request

        html_template = render_to_string('patient/treatments/treatments-print.html', context)
        pdf_file = HTML(string=html_template).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = 'filename="tratamientos.pdf"'
        response['Content-Transfer-Encoding'] = 'binary'
        return response

        #return render(request, "patient/treatments/treatments-print.html", context)
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_treatments_print_tags(request, patient_id):
    try:
        patient = get_or_none(Pacientes, patient_id)
        tratamientos = Tratamiento.objects.filter(paciente=patient, activo=True)

        context = {'url_base' : request.get_host(), 'tratamientos': tratamientos, 'paciente': patient}
        return render(request, "patient/treatments/treatments-print-tags.html", context)
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_summary(request, patient_id):
    try:
        patient = get_or_none(Pacientes, patient_id)
        context = get_values_to_summary_print(patient, request.get_host())
        return render(request, "patient/treatments/summary-print.html", context)
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_interactions_comment(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
    if patient == None:
        return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})
    return render(request, "patient/treatments/interactions-comment.html", {'obj': patient,})

@group_required("admins","managers")
def patient_interactions_print(request):
    try:
        patient = get_or_none(Pacientes, request.POST["patient_id"])
        comments = request.POST["comments"]
        context = get_values_to_interactions_print(patient, comments, request.get_host())
        return render(request, "patient/treatments/interactions-print.html", context)
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_timeline(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        tratamientos = Tratamiento.objects.filter(paciente=patient).order_by('fecha_inicio')
        #1.generar un listado de objetos donde la fecha sera la de inicio o fin dependiendo de si el tratamiento esta activo o no.
        #2.los elementos deben tener los campos fecha , activo, nombre, fecha_inicio, fecha_fin
        #3.El listado debe estar odendaro por la fecha

        titems = []
        for t in tratamientos:
            med = t.medicamentos.first()
            name = med.name if med != None else ""
            date = t.fecha_inicio if t.activo else t.fecha_fin

            item = {'name':name, 'date':date, 'year': date.year, 'activo':t.activo, 'fecha_inicio':t.fecha_inicio}
            titems.append(item)

        titems = sorted(titems, key=lambda k: k['date'], reverse=True)
        return render(request, "patient/treatments/timeline.html", {'tratamientos': titems})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

