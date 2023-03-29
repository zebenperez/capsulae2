#  !/usr/bin/python
#  -*- coding: utf-8 -*-

import logging
from datetime import datetime, timedelta
from django.views.decorators.csrf import csrf_exempt
from django.db.models import Q
from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render, redirect
from django.template.loader import render_to_string
from weasyprint import HTML  # , CSS
from django.template.defaultfilters import slugify
# i local-imports
from .decorators import *
from .models import *
from .utils import *
from .pillbox_forms import *
from .med_utils import parse_qr

import csv 

logger = logging.getLogger(__name__)
#  -----------------------
#   Utilities
#  -----------------------

def validate_date(date, date_format="%Y-%m-%d"):
    try:
        return datetime.strptime(date, date_format)
    except Exception:
        return None

# -----------------------
#  CONSTANTS
# -----------------------


LOGIN_URL = settings.LOGIN_URL
PILLBOX_ADVISE = 7  # days

# ------------------------
#  VISTAS
# ------------------------
@login_required(login_url=LOGIN_URL)
def pastilleros(request, paciente_id):

    context = {}
    try:
        paciente = Pacientes.objects.get(pk=paciente_id)
        context['paciente'] = paciente
        context['pastilleros'] = Pillbox.objects.filter(patient=paciente)
        context['advice_days'] = PILLBOX_ADVISE

    except Exception as e:
        logger.error(str(e))

    return render(request, "pastilleros.html", context)

@login_required(login_url=LOGIN_URL)
def pastilleros_nuevo(request, paciente_id):
    context = {}
    try:
        paciente = Pacientes.objects.get(pk=paciente_id)
        context['paciente'] = paciente
        tratamientos = Tratamiento.objects.filter(paciente=paciente, activo=True)
        context['tratamientos_pastillero'] = tratamientos  # en un pastillero nuevo, los tratamientos incluidos son todos
        context['tratamientos'] = tratamientos
    except Exception as e:
        logger.error(str(e))

    return render(request, "pastillero_nuevo.html", context)

@login_required(login_url=LOGIN_URL)
@csrf_exempt
def pastilleros_editar(request, pastillero_id):
    context = {}
    try:
        pillbox = Pillbox.objects.get(pk=pastillero_id)

        if request.method == "POST":
            ptreatments = pillbox.pillbox_treatments.all()
            ptreatments.update(include_in_spd=False)
            size = ptreatments.count()
            for i in range(1, size + 1):
                in_spd = request.POST.get("include_in_spd-%s" % i, None)
                treatment = request.POST.get("tratamientos-%s" % i, None)
                if in_spd and treatment:
                    ptreatments.filter(treatment__pk=treatment).update(include_in_spd=True)

        context['pastillero'] = pillbox
        context['paciente'] = pillbox.patient
        context['tratamientos'] = [item.treatment for item in pillbox.pillbox_treatments.all()]
        context['tratamientos_spd'] = pillbox.pillbox_treatments.filter(include_in_spd=True).values_list("treatment__pk", flat=True)
        context['tratamientos_pastillero'] = pillbox.pillbox_treatments.filter().values_list("treatment__pk", flat=True)
        context['edit'] = True

    except Exception as e:
        logger.error(str(e))
    return render(request, "pastillero_nuevo.html", context)

#  Sustituye los tratamientos en el pastillero por aquellos en el listado pasado
def save_pillbox_treatments(pillbox, patient_id, datas):
    treatments_num = Tratamiento.objects.filter(paciente__id=patient_id).count()
    PillboxTreatment.objects.filter(pillbox=pillbox).delete()
    saved_forms = 0
    for i in range(1, treatments_num + 1):
        trat_id = datas.get("tratamientos-%s" % i, None)
        if trat_id:
            trat = get_or_none(Tratamiento, trat_id)
            include_spd = bool(datas.get("include_in_spd-%s" % i, False))
            PillboxTreatment.objects.create(pillbox=pillbox, treatment=trat, include_in_spd=include_spd)
            saved_forms += 1
    return saved_forms

@login_required(login_url=LOGIN_URL)
def pastilleros_guardar(request):
    context = {}
    if request.method == "POST":
        paciente = get_or_none(Pacientes, request.POST.get('patient', ""))
        pillbox_id = request.POST.get('pastillero_id', None)

        form = PillboxForm(request.POST, initial={'active': True})
        pillbox_id = request.POST.get('pastillero_id', None)

        context['form'] = form
        context['paciente'] = paciente

        if pillbox_id is not None:
            pillbox = Pillbox.objects.get(pk=pillbox_id)
            form = PillboxForm(request.POST, instance=pillbox)

        if form.is_valid():
            pillbox = form.save()
            save_pillbox_treatments(pillbox, paciente.pk, request.POST.copy())
            patient_pillbox = Pillbox.objects.filter(patient=paciente).exclude(pk=pillbox.pk)
            patient_pillbox.update(active=False)
            return render(request, "pastillero_ok.html", context)
        else:
            logger.warning(form.errors)
            context['errors'] = form.errors

        # context= {'form':form, 'paciente':paciente}
    return render(request, 'pastillero_nuevo.html', context)

@login_required(login_url=LOGIN_URL)
@user_is_owner
def pastillero_delete(request, pastillero_id):
    pastillero = Pillbox.objects.get(pk=pastillero_id)
    paciente = pastillero.patient
    pastillero.delete()
    return redirect('pastilleros', paciente.pk)

@login_required(login_url=LOGIN_URL)
@user_is_owner
def pastillero_active_toggle(request, pastillero_id):
    pastillero = Pillbox.objects.get(pk=pastillero_id)
    paciente = pastillero.patient
    pastillero.active = not pastillero.active
    pastillero.save()
    return redirect('pastilleros', paciente.pk)

def entrega_pastillero_form(request, pastillero_id, template, modal=False):
    context = {}
    pillbox = get_or_none(Pillbox, pastillero_id)
    if pillbox:
        now = datetime.now()
        context['pastillero'] = pillbox
        context['paciente'] = pillbox.patient
        context['creation_date'] = now
        context['finish_date'] = now + timedelta(days=7)
        context['expiration_date'] = now + timedelta(days=90)
        context['code'] = PillboxDeliver.generate_code(str(pillbox.pk))
        context['tratamientos_spd'] = pillbox.pillbox_treatments.filter(include_in_spd=True)
        context['tratamientos_no_spd'] = pillbox.pillbox_treatments.exclude(include_in_spd=True)
        context['tratamientos_warning'] = pillbox.check_treatments()
        context['modal'] = modal if modal is True else None
    else:
        context['error'] = "El pastillero indicado no se encuentra en la base de datos"

    return render(request, template, context)

@login_required(login_url=LOGIN_URL)
@user_is_owner
def entrega_pastillero_nueva(request, pastillero_id):
    return entrega_pastillero_form(request, pastillero_id, "entrega_pastillero_nuevo.html")

@login_required(login_url=LOGIN_URL)
@user_is_owner
def entrega_pastillero_nueva_modal(request, pastillero_id):
    return entrega_pastillero_form(request, pastillero_id, "entrega_pastillero_nuevo_modal.html", True)

@login_required(login_url=LOGIN_URL)
@user_is_owner
def entrega_pastillero_guardar(request):
    context = {}
    if request.method == 'POST':
        form = PillboxDeliverForm(request.POST)
        if form.is_valid():
            deliver = form.save()
            meds_count = int(request.POST.get("treatments_count", 0))
            context['paciente'] = deliver.pillbox.patient
            for i in range(1, meds_count + 1):
                trat = get_or_none(PillboxTreatment, request.POST.get("deliver-med-%i" % i, None))
                batch = request.POST.get("deliver-code-%i" % i, "")
                expiration_date = validate_date(request.POST.get("deliver-expiration-%i" % i, None))
                if trat:
                    PillboxDeliverMed.objects.create(pillbox_deliver=deliver, treatment=trat, code=batch, expiration_date=expiration_date)
                    context['success'] = True

            if request.POST.get("modal", None):
                context['modal'] = True
                return render(request, "entrega_pastillero_ok.html", context)

            return redirect('entregas_pastillero_all', deliver.pillbox.pk)
        else:
            logger.warning(form.errors)

    return render(request, "entrega_pastillero_nuevo.html", context)

@login_required(login_url=LOGIN_URL)
@user_is_owner
def entregas_pastillero_all(request, pastillero_id):
    context = {}

    pastillero = Pillbox.objects.get(pk=pastillero_id)
    context['entregas'] = pastillero.pillbox_delivers.all().order_by('-deliver_date')
    context['pastillero'] = pastillero

    return render(request, "entregas_pastilleros_all.html", context)

@login_required(login_url=LOGIN_URL)
@user_is_owner
def entrega_pastillero_eliminar(request, entrega_pastillero_id):
    entrega = PillboxDeliver.objects.get(pk=entrega_pastillero_id)
    pastillero_id = entrega.pillbox.pk
    entrega.delete()
    return redirect('entregas_pastillero_all', pastillero_id)

def deliver_details(request, deliver_id):
    context = {}
    deliver = get_or_none(PillboxDeliver, deliver_id)
    context['deliver'] = deliver
    context['tratamientos_spd'] = deliver.deliver_meds.filter(treatment__include_in_spd=True)
    context['tratamientos_no_spd'] = deliver.deliver_meds.filter(treatment__include_in_spd=False)
    return context

@login_required(login_url=LOGIN_URL)
def entrega_pastillero_editar(request, entrega_pastillero_id):
    context = deliver_details(request, entrega_pastillero_id)
    return render(request, "entrega_pastillero_edit.html", context)

@login_required(login_url=LOGIN_URL)
def entrega_pastillero_ver(request, entrega_pastillero_id):
    context = deliver_details(request, entrega_pastillero_id)
    context['modal'] = True
    return render(request, "entrega_pastillero_edit.html", context)

@login_required
def imprimir_hoja_spd(request, entrega_pastillero_id):
    deliver = get_or_none(PillboxDeliver, entrega_pastillero_id)
    patient = deliver.pillbox.patient
    spd_treatments = [item.patient_treatment for item in deliver.deliver_meds.filter(treatment__include_in_spd=True)]
    no_spd_treatments = [item.patient_treatment for item in deliver.deliver_meds.filter(treatment__include_in_spd=False)]

    prin_in = AlergiasPrincipios.objects.filter(paciente=patient)
    excp_in = AlergiasExcipientes.objects.filter(n_orden=patient)

    context = {
        'tratamientos_spd': spd_treatments, 'tratamientos_no_spd': no_spd_treatments, 'paciente': patient, 'code': deliver.code,
        'url_base': request.get_host(), 'alergies': list(excp_in) + list(prin_in), 'request': request}
    html_template = render_to_string('entrega_spd_print.html', context)
    filename = 'filename="%s_%s_%s.pdf"' % (slugify(deliver.pillbox.patient.full_name), deliver.code, deliver.deliver_date.strftime("%Y%m%d"))

    pdf_file = HTML(string=html_template).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = filename  # 'filename="%s_%s_%s.pdf"'%(deliver.pillbox.patient.full_name, deliver.code, deliver.deliver_date.strftime("%Y%m%d"))
    response['Content-Transfer-Encoding'] = 'binary'

    return response

def get_pillbox_delivers_search_filters(post):
    filters = {}
    q_filters = Q()
    start_date = post.get("start_date", None)
    end_date = post.get("end_date", None)
    search_str = post.get("search_str", "")

    if start_date:
        filters['pillbox_delivers__finish_date__gte'] = datetime.strptime(start_date, "%Y-%m-%d")
    else:
        filters['pillbox_delivers__finish_date__gte'] = datetime.now().date() - timedelta(days=1)
    if end_date:
        filters['pillbox_delivers__finish_date__lte'] = datetime.strptime(end_date, "%Y-%m-%d")

    if search_str and len(search_str) > 0:
        print("search_str_is_set")
        if len(search_str) < 14:
            q_filters |= Q(patient__n_historial__iexact=search_str)
            q_filters |= Q(pillbox_delivers__code__iexact=search_str)
        else:
            batch_code = parse_qr(search_str).get("batch_code", None)
            if batch_code:
                print("El codigo recuperado es:")
                print(batch_code)
                filters["pillbox_delivers__deliver_meds__code"] = batch_code
    return filters, q_filters

@login_required()
def pillbox_delivers_panel_ajax(request):
    context = {}
    now = datetime.now().date() - timedelta(days=365)
    pillboxes = []
    if request.method == "POST":
        context['filters'] = request.POST.copy()
        filters, q_filters = get_pillbox_delivers_search_filters(request.POST.copy())
        pillboxes = Pillbox.objects.filter(patient__id_user=request.user).filter(**filters).filter(q_filters)
    else:
        pillboxes = Pillbox.objects.filter(patient__id_user=request.user, active=True, pillbox_delivers__finish_date__gte=now)

    pillboxes = pillboxes.distinct()
    delivers = [pillbox.last_deliver for pillbox in pillboxes]
    delivers = sorted(delivers, key=lambda d: d.finish_date)

    context['delivers'] = delivers
    context['start_date'] = now
    return render(request, "pillbox_panel_ajax.html", context)

def print_spd(deliver, request, include_no_spd=True):
    patient = deliver.pillbox.patient
    no_spd_treatments = []
    if include_no_spd:
        no_spd_treatments = [item.patient_treatment for item in deliver.deliver_meds.filter(treatment__include_in_spd=False)]

    spd_treatments = [item.patient_treatment for item in deliver.deliver_meds.filter(treatment__include_in_spd=True)]
    prin_in = AlergiasPrincipios.objects.filter(paciente=patient)
    excp_in = AlergiasExcipientes.objects.filter(n_orden=patient)

    context = {
        'tratamientos_spd': spd_treatments, 'tratamientos_no_spd': no_spd_treatments, 'paciente': patient, 'code': deliver.code,
        'url_base': request.get_host(), 'alergies': list(excp_in) + list(prin_in), 'request': request}
    html_template = render_to_string('entrega_spd_print.html', context)

    return html_template

@login_required
def print_group_spd(request, entrega_pastillero_id):
    deliver = get_or_none(PillboxDeliver, entrega_pastillero_id)
    slug_address = deliver.pillbox.patient.slug_address

    html_template = ""
    if len(slug_address) > 3 :
        pillbox_group = Pillbox.objects.filter(patient__slug_address=slug_address, active=True)
        for pillbox in pillbox_group:
            try:
                html_template += print_spd(pillbox.last_deliver, request, False)
            except Exception as e:
                print("ERROR "+str(e))
                pass
    else:
        html_template += print_spd(deliver, request, False)
    
    filename = 'filename="%s_%s_%s_GROUP.pdf"' % (slugify(deliver.pillbox.patient.full_name), deliver.code, deliver.deliver_date.strftime("%Y%m%d"))
    pdf_file = HTML(string=html_template).write_pdf()
    response = HttpResponse(pdf_file, content_type='application/pdf')
    response['Content-Disposition'] = filename  # 'filename="%s_%s_%s.pdf"'%(deliver.pillbox.patient.full_name, deliver.code, deliver.deliver_date.strftime("%Y%m%d"))
    response['Content-Transfer-Encoding'] = 'binary'

    return response

@login_required
def patients_address_repair(request):
    pacientes = Pacientes.objects.all()
    for item in pacientes:
        item.save()

    return HttpResponse("_hecho_")
#  DEPRECATED 01-05-2020 Braulio
#  @login_required(login_url=LOGIN_URL)
#  @user_is_owner
#  def imprimir_etiqueta_pastillero(request, pastillero_id):
#      context= {'url_base': request.get_host()}
#      pastillero = Pillbox.objects.get(pk=pastillero_id)
#      pillbox_treats_id = []
#      for item in pastillero.pillbox_treatments.all():
#          pillbox_treats_id.append(item.treatment.id)
#      context['tratamientos'] = tratamientos
#      context['paciente'] = pastillero.patient

#      return render(request, "etiqueta_pastillero.html", context)

@login_required
def change_description_pillbox(request):
    if request.method == "POST":
        pillbox_id = request.POST.get("pastillero_id",0)
        pillbox = Pillbox.objects.get(pk=pillbox_id)
        pillbox.description = request.POST.get("description","")
        pillbox.save()
    return render(request, 'change-desc-pillbox.html', {'item':pillbox})
'''
    row:
        id hospital
        nombre hospital
        planta
        habitación
        id paciente
        nombre del paciente
        fecha de nacimiento del paciente YYYY-MM-DD
        nombre del doctor
        fecha de inicio de producción YYYY-MM-DD
        fecha de fin de producción YYYY-MM-DD
        mnemonic -> código de la medicación
        grupo terapeutico VMP
        grupo terapeutico VMPP
        grupo terapeutico nivel 3
        grupo terapeutico nivel 4
        grupo terapeutico nivel 5
        nombre de medicina
        medicamento fuera de blister -> 0 no, 1 si
        tomar si se precisa -> 0 no, 1 si (toma opcional)
        posología especial -> 0 no, 1 si 
        dosis (el separador decimal es un .)
        día de toma -> YYYY-MM-DD
        hora de toma -> hh:mm
        nombre de toma -> desayuno, almuerzo...
        comentarios
        tipo de medicina -> compridos, jarabe...
        cantidad de la caja (el separador decimal es un .)
        ID de la seguridad social
        número de teléfono del paciente
        email del paciente
        color
        forma
        detalles
'''
def set_file_row(treatment, ini_date, end_date, out_spd, dose, day, hour, name, obs):

    medicamentos = PresentationsPrescriptionsAempsCache.objects.filter(prescription__nregistro=treatment.reg_code)
    patient_name = "%s %s" % (treatment.paciente.nombre, treatment.paciente.apellido)
    treatment_type =""
    treatment_amount =""
    if "," in treatment.name:
        val = treatment.name.rsplit(",", 1)[1].lstrip()
        if " " in val: 
            treatment_type = val.split(" ")[1]
            treatment_amount = val.split(" ")[0]
    else:
        med = treatment.medicamentos.all().first()
        if med != None:
            atcs = med.atcs.split(",")
            p = Prescription.objects.filter(cod_atc=atcs[len(atcs)-1]).first()
            if p != None and p.nro_conte != None:
                val = p.nro_conte.lstrip()
                if " " in val: 
                    treatment_type = val.split(" ")[1]
                    treatment_amount = val.split(" ")[0]
    return [
        '0',
        'La Comunitaria',
        'La Comunitaria',
        '',
        treatment.paciente.id,
        patient_name,
        treatment.paciente.fecha_nacimiento.strftime("%Y-%m-%d"),
        '',
        ini_date.strftime("%Y-%m-%d"),
        end_date.strftime("%Y-%m-%d"),
        treatment.cn,
        '',
        '',
        '',
        '',
        '',
        treatment.name.replace(";", " "),
        out_spd,
        '0',
        '0',
        dose,
        day.strftime("%Y-%m-%d"),
        hour,
        name,
        obs,
        treatment_type,
        treatment_amount,
        treatment.paciente.cip,
        treatment.paciente.telefono1,
        treatment.paciente.email,
        '',
        '',
        '',
    ]

@login_required
def create_file(request, entrega_pastillero_id):
    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = 'attachment; filename="somefilename.csv"'

    writer = csv.writer(response, delimiter=';')
    #row = set_file_row()
    #writer.writerow(row)
    #writer.writerow(['First row', 'Foo', 'Bar', 'Baz'])
    #writer.writerow(['Second row', 'A', 'B', 'C', '"Testing"', "Here's a quote"])
    try:
        deliver = get_or_none(PillboxDeliver, entrega_pastillero_id)
        in_spd = deliver.deliver_meds.filter(treatment__include_in_spd=True)
        out_spd = deliver.deliver_meds.filter(treatment__include_in_spd=False)

        ini_date = deliver.deliver_date
        end_date = deliver.finish_date
        delta = end_date - ini_date
        obs = deliver.observations
        for t in in_spd:
            treatment = t.treatment.treatment
            for i in range(delta.days + 1):
                day = ini_date + timedelta(days=i)
                if treatment.m > 0:
                    row = set_file_row(treatment, ini_date, end_date, 0, "%s" % treatment.m, day, "08:00", "mañana", obs)
                    writer.writerow(row)
                if treatment.t > 0:
                    row = set_file_row(treatment, ini_date, end_date, 0, "%s" % treatment.t, day, "14:00", "tarde", obs)
                    writer.writerow(row)
                if treatment.n > 0:
                    row = set_file_row(treatment, ini_date, end_date, 0, "%s" % treatment.n, day, "20:00", "noche", obs)
                    writer.writerow(row)
                if treatment.o > 0:
                    row = set_file_row(treatment, ini_date, end_date, 0, "%s" % treatment.o, day, "23:00", "otra", obs)
                    writer.writerow(row)
                #print(row)
    except Exception as e:
        logger.error(str(e))

    return response


