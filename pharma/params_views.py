from django.shortcuts import render, redirect, reverse
from datetime import datetime
from dateutil.relativedelta import relativedelta

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from .params_models import BloodPressure
from .models import Pacientes


def get_cm_constants(sex, age):
    AGE_INDEXES = [16, 20, 30, 40, 50]
    MALE_CONSTANTS = {
        'C': [1.1620, 1.1631, 1.1422, 1.1620, 1.1715],
        'M': [0.0630, 0.0632, 0.0544, 0.07, 0.0779],
    }
    FEMALE_CONSTANTS = {
        'C': [1.1549, 1.1599, 1.1423, 1.1333, 1.1339],
        'M': [0.0678, 0.0717, 0.0632, 0.0612, 0.0645],
    }

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

@group_required("admins","managers")
def patient_params_print(request):
    try:
        obj = get_or_none(Pacientes, request.GET["patient_id"])
        return render(request, "patient/parameters/pick-plots-to-print.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def patient_params_print_pdf(request):
    context = {'request': request}
    try:
        paciente = Pacientes.objects.get(pk=get_param(request.GET, "patient_id"))

        now = datetime.now()
        e_date = now + relativedelta(months=+1)
        start_date = "%s-%s-01" % (now.year, now.month)
        end_date = "%s-%s-01" % (e_date.year, e_date.month)
        #next_month = now.month if now.month < 12 else 0
        #year = now.year if now.month < 12 else now.year +1
        #end_date = "%s-%s-01" % (year, next_month + 1)

        #start_date = request.GET.get('start_date', start_date)
        #end_date = request.GET.get('end_date', end_date)
        context['paciente'] = paciente
        #TABLE_SIZE = 25
        #registros = BloodPressure.objects.filter(date__range=[start_date, end_date], patient=paciente).order_by("-date")[:TABLE_SIZE]
        item_list = BloodPressure.objects.filter(patient=paciente).order_by("-date")
        context['registros'] = item_list
        #num_regs = len(registros)
        #if num_regs < TABLE_SIZE:
        #    end_range = TABLE_SIZE - (num_regs + 1)
        #    context['range'] = range(0, end_range)
        # plots
        plots_get = request.GET.getlist("items[]", [])
        plots = []
        for item in plots_get:
            #obj={'key':item,'label':request.GET.get("{}_label".format(item),""),'color':request.GET.get("{}_color".format(item),"")}
            label = get_param(request.GET, "{}_label".format(item))
            color = get_param(request.GET,"{}_color".format(item))
            plots.append({'key': item, 'label': label, 'color': color})
        context['plots'] = plots

        return render(request, "patient/parameters/params-print.html", context)
    except Exception as e:
        #context['error'] = "Ha habido un error al mostrar la tabla %s " % (str(e))
        print(str(e))
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

#    html = ""
#    if 'print_report' in request.GET:
#        html = "registro_tension_print.html"
#    elif 'print_graph' in request.GET:
#        html = "registro_tension_print_graph.html"
#    return render(request, html, context)

