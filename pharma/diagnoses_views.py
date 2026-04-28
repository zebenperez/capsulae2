from django.db.models import Q
from django.shortcuts import render, redirect, reverse

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from medication.models import CieCiap
from .models import Pacientes, Diagnosticos


'''
    Diagnoses
'''
def get_diagnoses(value):
    return CieCiap.objects.filter(Q(nombre__icontains=value) | Q(cie__icontains=value) | Q(ciap__icontains=value))

@group_required("admins","managers")
def patient_diagnoses_form(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        obj_id = get_param(request.GET, 'obj_id')
        if obj_id != "":
            obj = get_or_none(Diagnosticos, obj_id)
        else:
            cie_ciap = get_or_none(CieCiap, get_param(request.GET, 'cie_ciap'))
            if cie_ciap == None:
                return render(request, 'error_exception.html', {'exc': 'Diagnosis not found!'})
            obj, created = Diagnosticos.objects.get_or_create(n_orden=patient.n_historial, cie_ciap=cie_ciap)
        return render(request, "patient/diagnoses/diagnoses-form.html", {'obj': obj, 'patient': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_diagnoses_search(request):
    patient_id = get_param(request.GET, "patient_id")
    search_value = get_param(request.GET, "value")
    return render(request, "patient/diagnoses/cie_ciap-list.html", {'patient_id': patient_id, 'items': get_diagnoses(search_value)})

@group_required("admins","managers")
def patient_diagnoses_remove(request):
    try:
        obj = get_or_none(Diagnosticos, request.GET["obj_id"])
        patient = get_or_none(Pacientes, obj.n_orden, "n_historial")
        obj.delete()

        return render(request, "patient/diagnoses/diagnosis-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


