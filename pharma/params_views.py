from django.shortcuts import render, redirect, reverse

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from .params_models import BloodPressure
from .models import Pacientes


def get_cm_constants(sex, age):
    AGE_INDEXES = [16, 20, 30, 40, 50]

    ret = {'c_index': None, 'm_index': None}
    if age < 16 or not age:
        return ret

    for i, value in enumerate(AGE_INDEXES):
        if value > age:
            index = i - 1
            constants = FEMALE_CONSTANTS
            if sex == "H":
                constants = MALE_CONSTANTS

            ret['c_index'] = constants.get("C")[index]
            ret['m_index'] = constants.get("M")[index]

    return ret

'''
    Parameters
'''
@group_required("admins","managers")
def patient_params_form(request):
    try:
        patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
        if patient == None:
            return render(request, 'error_exception.html', {'exc':'Paciente no encontrado!'})

        context = get_cm_constants(patient.sexo, patient.age)
        obj = get_or_none(BloodPressure, request.GET["obj_id"]) if "obj_id" in request.GET else BloodPressure.objects.create(patient=patient)
        context["obj"] = obj
        return render(request, "patient/parameters/params-form.html", context)
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_params_form_tab(request):
    try:
        obj = get_or_none(BloodPressure, request.GET["obj_id"]) 
        if obj == None:
            return render(request, 'error_exception.html', {'exc':'Parametros no encontrado!'})

        temp = "patient/parameters/params-form-{}.html".format(request.GET["tab"])
        return render(request, temp, {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_params_remove(request):
    try:
        obj = get_or_none(BloodPressure, request.GET["obj_id"])
        patient = obj.patient
        obj.delete()

        return render(request, "patient/parameters/param-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


