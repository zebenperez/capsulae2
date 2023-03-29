from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify

from weasyprint import HTML 

from datetime import datetime, timedelta

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc

from .models import Pacientes
from .spd_models import Pillbox, PillboxTreatment, PillboxDeliver, PillboxDeliverMed
from .treatment_models import Tratamiento 
from .common_lib import PILLBOX_ADVISE


'''
    SPD
'''
@group_required("admins",)
def spd_form(request):
    try:
        patient = get_or_none(Pacientes, request.GET["patient_id"])
        treatment_list = Tratamiento.objects.filter(paciente=patient, activo=True)
        
        if "obj_id" in request.GET:
            obj = get_or_none(Pillbox, request.GET['obj_id'])  
        else:
            obj = Pillbox.objects.create(patient=patient)
            for treatment in treatment_list:
                PillboxTreatment.objects.create(pillbox = obj, treatment = treatment)
        return render(request, "patient/spd/spd-form.html", {'obj': obj, 'treatment_list': treatment_list})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def spd_remove(request):
    try:
        pillbox = get_or_none(Pillbox, request.GET["obj_id"])
        patient = pillbox.patient
        pillbox.delete()
        return render(request, "patient/spd/spd-list.html", {'obj': patient, 'advice_days': PILLBOX_ADVISE})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def spd_toggle_treatment(request):
    try:
        treatment = get_or_none(Tratamiento, request.GET["treatment_id"])
        pillbox = get_or_none(Pillbox, request.GET["pillbox_id"])

        pt_list = PillboxTreatment.objects.filter(pillbox = pillbox, treatment = treatment)
        if len(pt_list) > 0:
            pt_list.delete()
        else:
            PillboxTreatment.objects.create(pillbox = pillbox, treatment = treatment)
        return render(request, "patient/spd/spd-form-row.html", {'pillbox': pillbox, 'treatment': treatment})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def spd_toggle_treatment_blister(request):
    try:
        treatment = get_or_none(Tratamiento, request.GET["treatment_id"])
        pillbox = get_or_none(Pillbox, request.GET["pillbox_id"])
        obj = PillboxTreatment.objects.filter(pillbox = pillbox, treatment = treatment).first()
        if obj != None:
            obj.include_in_spd = not obj.include_in_spd
            obj.save()
        return render(request, "patient/spd/spd-form-row.html", {'pillbox': pillbox, 'treatment': treatment})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def spd_active_toggle(request):
    try:
        obj = get_or_none(Pillbox, request.GET["obj_id"])
        obj.active = not obj.active
        obj.save()
        return render(request, "patient/spd/spd-list.html", {'obj': obj.patient, 'advice_days': PILLBOX_ADVISE})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

'''
    Blisters
'''
@group_required("admins",)
def spd_blisters(request):
    try:
        obj = get_or_none(Pillbox, request.GET["obj_id"])
        deliveries = obj.pillbox_delivers.all().order_by('-deliver_date')
        return render(request, "patient/spd/spd-blisters.html", {'obj': obj, 'deliveries': deliveries})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def spd_blister_form(request):
    try:
        pillbox = get_or_none(Pillbox, request.GET["pillbox_id"])
        now = datetime.now()
        expiration_date = now + timedelta(days=90)
        
        if "obj_id" in request.GET:
            obj = get_or_none(PillboxDeliver, request.GET['obj_id'])  
        else:
            obj = PillboxDeliver.objects.create(pillbox=pillbox)
            obj.code = PillboxDeliver.generate_code(str(pillbox.pk))
            obj.creation_date = now
            obj.deliver_date = now
            obj.finish_date = now + timedelta(days=7)
            obj.save()
            for treatment in pillbox.pillbox_treatments.all():
                PillboxDeliverMed.objects.create(treatment=treatment, pillbox_deliver=obj, expiration_date=expiration_date)

        return render(request, "patient/spd/spd-blister-form.html", {'obj': obj, 'expiration_date': expiration_date})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def spd_blister_remove(request):
    try:
        obj = get_or_none(PillboxDeliver, request.GET['obj_id'])  
        pillbox = obj.pillbox
        obj.delete()

        deliveries = pillbox.pillbox_delivers.all().order_by('-deliver_date')
        return render(request, "patient/spd/spd-blisters.html", {'obj': pillbox, 'deliveries': deliveries})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def spd_blister_print(request, pd_id):
    try:
        obj = get_or_none(PillboxDeliver, pd_id)  

        patient = obj.pillbox.patient
        spd_treatments = [item.patient_treatment for item in obj.deliver_meds.filter(treatment__include_in_spd=True)]
        no_spd_treatments = [item.patient_treatment for item in obj.deliver_meds.filter(treatment__include_in_spd=False)]

        #prin_in = AlergiasPrincipios.objects.filter(paciente=patient)
        #excp_in = AlergiasExcipientes.objects.filter(n_orden=patient)
        prin_in = []
        excp_in = []

        context = {
            'tratamientos_spd': spd_treatments, 
            'tratamientos_no_spd': no_spd_treatments, 
            'paciente': patient, 
            'code': obj.code,
            'url_base': request.get_host(), 
            'alergies': list(excp_in) + list(prin_in), 
            'request': request
        }
        html_template = render_to_string('patient/spd/spd-blister-print.html', context)
        filename = 'filename="%s_%s_%s.pdf"' % (slugify(obj.pillbox.patient.full_name), obj.code, obj.deliver_date.strftime("%Y%m%d"))

        pdf_file = HTML(string=html_template).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = filename  
        response['Content-Transfer-Encoding'] = 'binary'

        return response
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


