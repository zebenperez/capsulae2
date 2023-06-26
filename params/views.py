#!/usr/bin/python
# -*- coding: utf-8 -*-

# general imports
import logging

from datetime import datetime

# django imports
from django.shortcuts import render, redirect
from django.contrib.auth.decorators import login_required

# local imports
from pharma.models import Pacientes, Diagnosticos
from generic.utils import *
from .forms import *
from .framingham import framingham
from .models import BloodPressure


logger = logging.getLogger(__name__)

# Create your views here.
# ---------------------------
#  Durnin y Womersley TABLE
# ---------------------------
AGE_INDEXES = [16, 20, 30, 40, 50]
MALE_CONSTANTS = {
    'C': [1.1620, 1.1631, 1.1422, 1.1620, 1.1715],
    'M': [0.0630, 0.0632, 0.0544, 0.07, 0.0779],
}

FEMALE_CONSTANTS = {
    'C': [1.1549, 1.1599, 1.1423, 1.1333, 1.1339],
    'M': [0.0678, 0.0717, 0.0632, 0.0612, 0.0645],
}


# ---------------------------
# Utils
# ---------------------------

def get_cm_constants(sex, age):
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


# ---------------------------
# Views
# ---------------------------


@login_required(login_url="/pharma/index")
def registro_tension(request, paciente_id):
    context = {}
    try:
        start_date = None
        end_date = None
        paciente = Pacientes.objects.get(pk=paciente_id)
        registros = BloodPressure.objects.filter(patient=paciente).order_by('-creation_date')

        if request.method == "POST":
            start_date = request.POST.get('start_date', start_date)
            end_date = request.POST.get('end_date', end_date)
            start_date = datetime.strptime(start_date, "%Y-%m-%d")
            end_date = datetime.strptime(end_date, "%Y-%m-%d")
            registros = registros.filter(creation_date__range=[start_date, end_date])

        else:
            try:
                registros = registros[:40]
                if len(registros) > 0:

                    end_date = registros[0].creation_date
                    start_date = registros[len(registros) - 1].creation_date
            except Exception as e:
                print(str(e))

        context['paciente'] = paciente
        context['region'] = calcular_region(paciente)
        # context['registros'] = BloodPressure.objects.filter(creation_date__range=[start_date, end_date], patient=paciente)
        context['registros'] = registros
        context['start_date'] = start_date
        context['end_date'] = end_date

    except Exception as e:
        context['error'] = "Ha habido un error al cargar los datos"
        print("[EXCP registro-tension ] " + str(e))

    return render(request, "registro_tension.html", context)

def calcular_region(paciente):
    cp = str(paciente.cod_postal)
    region = "p"  # Indica que se van a usar las tablas de la Peninsula
    #  Mira a ver si los CP empiezan por 38 ( SC de Tenerife ) o 35 ( Las Palmas de Gran Canaria )
    if (cp.find("38") == 0 or cp.find("35") == 0):
        region = "c"
    return region

@login_required(login_url="/pharma/index")
def registro_tension_chart(request, paciente_id):
    context = {}
    try:
        now = datetime.now()
        paciente = Pacientes.objects.get(pk=paciente_id)
        start_date = "%s-%s-01" % (now.year, now.month)
        end_date = "%s-%s-01" % (now.year, now.month + 1)
        start_date = request.GET.get('start_date', start_date)
        end_date = request.GET.get('end_date', end_date)
        context['paciente'] = paciente
        context['registros'] = BloodPressure.objects.filter(creation_date__range=[start_date, end_date], patient=paciente).order_by('creation_date')

    except Exception as e:
        context['error'] = "Ha habido un error al mostrar la gráfica %s " % (str(e))
        print(str(e))

    return render(request, "registro_tension_chart.html", context)

@login_required(login_url="/pharma/index")
def pick_plots_to_print(request, paciente_id):
    context = {'paciente_id': paciente_id,
        'start_date': request.GET.get("start_date", None),
        'end_date': request.GET.get("end_date", None),
    }
    return render(request, "pick_plots_to_print.html", context)

@login_required(login_url="/pharma/index")
def registro_tension_print(request, paciente_id):
    context = {'request': request}
    try:
        now = datetime.now()
        paciente = Pacientes.objects.get(pk=paciente_id)
        start_date = "%s-%s-01" % (now.year, now.month)
        
        next_month = now.month if now.month < 12 else 0
        year = now.year if now.month < 12 else now.year +1 
        
        
        end_date = "%s-%s-01" % (year, next_month + 1)

        start_date = request.GET.get('start_date', start_date)
        end_date = request.GET.get('end_date', end_date)
        print("%s %s"%(start_date, end_date)) 
        context['paciente'] = paciente
        TABLE_SIZE = 27
        registros = BloodPressure.objects.filter(date__range=[start_date, end_date], patient=paciente).order_by("-date")[:TABLE_SIZE]
        context['registros'] = registros
        print(registros)
        num_regs = len(registros)
        if num_regs < TABLE_SIZE:
            end_range = TABLE_SIZE - (num_regs + 1)
            context['range'] = range(0, end_range)

        # plots
        plots_get = request.GET.getlist("items[]", [])
        plots = []
        for item in plots_get:
            obj = {'key': item, 'label': request.GET.get("{0}_label".format(item), ""), 'color': request.GET.get("{0}_color".format(item), "")}
            plots.append(obj)
        context['plots'] = plots

    except Exception as e:
        context['error'] = "Ha habido un error al mostrar la tabla %s " % (str(e))
        print(str(e))

    html = ""
    if 'print_report' in request.GET:
        html = "registro_tension_print.html"
    elif 'print_graph' in request.GET:
        html = "registro_tension_print_graph.html"

    return render(request, html, context)

def calculo_framingham(bpressure_max, col, paciente, region):
    if len(col) < 1 or len(bpressure_max) < 1:
        return 0

    colesterol = 0
    diabetes = False
    fumador = False
    tension = float(bpressure_max)
    colesterol = float(col)
    # p = Pacientes.objects.get(pk = paciente_id)
    sexo = paciente.sexo
    edad = paciente.edad
    diagnosticos = Diagnosticos.objects.filter(n_orden=paciente.n_historial, borrado=False).order_by('fecha_ini', 'cie_ciap__nombre')
    for item in diagnosticos:
        # Si es Fumador
        if item.cie_ciap.ciap == "P17":
            fumador = True
        # Si es diabetico
        if (item.cie_ciap.ciap == "T89" or item.cie_ciap.ciap == "T90" or item.cie_ciap.ciap == "T99"):
            diabetes = True
    f = framingham(edad, sexo, diabetes, fumador, tension, colesterol, region)
    return f


@login_required(login_url="/pharma/index")
def tension_edit_form_ajax(request, paciente_id=None, tension_id=None):
    context = {}
    form = None
    paciente = get_or_none(Pacientes, request.POST.get('patient', paciente_id))
    tension = get_or_none(BloodPressure, request.POST.get('tension', tension_id))
    region = calcular_region(paciente)

    if paciente is not None:
        context = get_cm_constants(paciente.sexo, paciente.edad)
        if tension is not None:
            form = BloodPresureForm(instance=tension)
        else:
            form = BloodPresureForm(initial={'patient': paciente.pk})

        if request.method == "POST":
            post_cp = request.POST.copy()
            post_cp["framingham"] = calculo_framingham(request.POST.get("bpressure_max", ""), request.POST.get("total_cholesterol", ""), paciente, region)
            form = BloodPresureForm(post_cp)
            if tension is not None:
                form = BloodPresureForm(post_cp, instance=tension)

            if form.is_valid():
                form.save()
                context['success'] = True

            else:
                context['error'] = "Ha habido un error en el formulario"
    else:
        context['error'] = "El paciente indicado no existe"

    context['tension'] = tension
    context['form'] = form
    context['paciente'] = paciente
    context['region'] = region

    return render(request, "tension_edit_form.html", context)


@login_required(login_url="/pharma/index")
def tension_remove(request, tension_id):

    tension = BloodPressure.objects.get(pk=tension_id)
    paciente = tension.patient
    tension.delete()

    return redirect('registro_tension', paciente.pk)

# DEPRECATED
# def leertabla(tension, colesterol, tabla):
#     valor = 0
#     posicion = 0

#     if colesterol < 4.1:
#         col = 0
#     if (colesterol >= 4.1 and colesterol <= 5.1):
#         col = 1
#     if (colesterol >= 5.2 and colesterol <= 6.1):
#         col = 2
#     if (colesterol >= 6.2 and colesterol <= 7.1):
#         col = 3
#     if (colesterol > 7.1):
#         col = 4

#     if (tension <= 160):
#         if col == 0:
#             posicion = 0
#         if col == 1:
#             posicion = 1
#         if col == 2:
#             posicion = 2
#         if col == 3:
#             posicion = 3
#         if col == 4:
#             posicion = 4

#     if (tension <= 130 and tension >= 139):
#         if col == 0:
#             posicion = 10
#         if col == 1:
#             posicion = 11
#         if col == 2:
#             posicion = 12
#         if col == 3:
#             posicion = 13
#         if col == 4:
#             posicion = 14

#     if (tension <= 120 and tension >= 129):
#         if col == 0:
#             posicion = 15
#         if col == 1:
#             posicion = 16
#         if col == 2:
#             posicion = 17
#         if col == 3:
#             posicion = 18
#         if col == 4:
#             posicion = 19

#     if (tension < 120):
#         if col == 0:
#             posicion = 20
#         if col == 1:
#             posicion = 21
#         if col == 2:
#             posicion = 22
#         if col == 3:
#             posicion = 23
#         if col == 4:
#             posicion = 24

#     url = "f_tabla" + str(tabla) + ".csv"
#     path = os.path.join(settings.BASE_DIR, 'media', url)
#     if (os.path.exists(path)):
#         with open(path) as File:
#             reader = csv.reader(File, delimiter=',')
#             for row in reader:
#                  print(row)
#             valor = row[posicion]
#     return valor



# def leertabla2():
#     valor = 0
#     path = os.path.join(settings.BASE_DIR, 'media', 'f_tabla1.csv')

#     if (os.path.exists(path)):
#         with open(path) as File:  
#             reader = csv.reader(File, delimiter=',')
#             for row in reader:
#                 print(row)
#     valor = row[0]
#     return valor


