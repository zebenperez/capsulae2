from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.template.defaultfilters import slugify
from django.views.decorators.csrf import csrf_exempt


from weasyprint import HTML 

from datetime import datetime, timedelta

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, get_float
from capsulae2.settings import MEDIA_ROOT

from .models import Pacientes
from .spd_models import Pillbox, PillboxTreatment, PillboxDeliver, PillboxDeliverMed
from .treatment_models import Tratamiento 
from .common_lib import PILLBOX_ADVISE
from .pharma_lib import parse_qr
from .spd_lib import send_spd_values

import os, json


'''
    SPD
'''
@group_required("admins","managers")
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

@group_required("admins","managers")
def spd_remove(request):
    try:
        pillbox = get_or_none(Pillbox, request.GET["obj_id"])
        patient = pillbox.patient
        pillbox.delete()
        return render(request, "patient/spd/spd-list.html", {'obj': patient, 'advice_days': PILLBOX_ADVISE})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
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

@group_required("admins","managers")
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

@group_required("admins","managers")
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
@group_required("admins","managers")
def spd_blisters(request):
    try:
        obj = get_or_none(Pillbox, request.GET["obj_id"])
        deliveries = obj.pillbox_delivers.all().order_by('-deliver_date')
        return render(request, "patient/spd/spd-blisters.html", {'obj': obj, 'deliveries': deliveries})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
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

@group_required("admins","managers")
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

@group_required("admins","managers")
def spd_blister_clone(request):
    try:
        obj = get_or_none(PillboxDeliver, request.GET['obj_id'])  
        dashboard = get_param(request.GET, 'dashboard')

        now = datetime.now()
        expiration_date = now + timedelta(days=90)
        
        new_obj = PillboxDeliver.objects.create(pillbox=obj.pillbox)
        new_obj.code = PillboxDeliver.generate_code(str(obj.pillbox.pk))
        new_obj.creation_date = now
        new_obj.deliver_date = now
        new_obj.finish_date = now + timedelta(days=7)
        new_obj.save()
        for dm in obj.deliver_meds.all():
            PillboxDeliverMed.objects.create(treatment=dm.treatment, pillbox_deliver=new_obj, expiration_date=dm.expiration_date, code=dm.code)

        deliveries = new_obj.pillbox.pillbox_delivers.all().order_by('-deliver_date')
        if dashboard != "":
            return render(request, "pillbox-list-row.html", {'obj': new_obj})
        return render(request, "patient/spd/spd-blisters.html", {'obj': new_obj.pillbox, 'deliveries': deliveries})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def spd_blister_print(request, pd_id):
    try:
        obj = get_or_none(PillboxDeliver, pd_id)  

        patient = obj.pillbox.patient
        #spd_treatments = [item.patient_treatment for item in obj.deliver_meds.filter(treatment__include_in_spd=True)]
        spd_treatments = []
        for item in obj.deliver_meds.filter(treatment__include_in_spd = True):
            try:
                spd_treatments.append(item.patient_treatment)
            except Exception as e:
                pass
        no_spd_treatments = []
        for item in obj.deliver_meds.filter(treatment__include_in_spd=False):
            try:
                no_spd_treatments.append(item.patient_treatment)
            except Exception as e:
                print(e)
        #no_spd_treatments = [item.patient_treatment for item in obj.deliver_meds.filter(treatment__include_in_spd=False)]

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

@group_required("admins","managers")
def spd_blister_qr_print(request, pd_id):
    try:
        obj = get_or_none(PillboxDeliver, pd_id)  

        patient = obj.pillbox.patient
        #spd_treatments = [item.patient_treatment for item in obj.deliver_meds.filter(treatment__include_in_spd=True)]
        spd_treatments = []
        for item in obj.deliver_meds.filter(treatment__include_in_spd = True):
            try:
                spd_treatments.append(item.patient_treatment)
            except Exception as e:
                pass
        no_spd_treatments = []
        for item in obj.deliver_meds.filter(treatment__include_in_spd=False):
            try:
                no_spd_treatments.append(item.patient_treatment)
            except Exception as e:
                print(e)
        #no_spd_treatments = [item.patient_treatment for item in obj.deliver_meds.filter(treatment__include_in_spd=False)]

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
        html_template = render_to_string('patient/spd/spd-blister-qr-print.html', context)
        filename = 'filename="%s_%s_%s.pdf"' % (slugify(obj.pillbox.patient.full_name), obj.code, obj.deliver_date.strftime("%Y%m%d"))

        pdf_file = HTML(string=html_template).write_pdf()
        response = HttpResponse(pdf_file, content_type='application/pdf')
        response['Content-Disposition'] = filename  
        response['Content-Transfer-Encoding'] = 'binary'

        return response
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins", "managers")
def spd_search_by_qr(request):
    json_response = {}
    try:
        qr_data = request.GET["qr_data"]
        pd_id = request.GET["pd_id"]

        pd = get_or_none(PillboxDeliver, pd_id)
        json_response = parse_qr(qr_data)   
        for pdm in pd.deliver_meds.all():
            if pdm.treatment.treatment.cn == json_response["cn"][:-1][-6:]:
                json_response["pdm_id"] = pdm.id 
                break
    except Exception as e:
        print(e)
        json_response['error'] = "Bad request"
    return JsonResponse(json_response)

'''
    SIMULATOR
'''
@group_required("admins", "managers")
def spd_sim(request):
    try:
        pillbox_deliver_code = get_param(request.GET, "pillbox_deliver_code")
        pd = PillboxDeliver.objects.filter(code=pillbox_deliver_code).first()
        if pd == None:
            return JsonResponse({"error": True, "error_msg": "Not Found"}, status=404)
        meds = pd.deliver_meds.all()
        response = []
        for med in meds:
            treatment_spd = med.treatment
            try:
                if treatment_spd.include_in_spd:
                    treatment = Tratamiento.objects.get(pk=treatment_spd.treatment.id)
                    response.append({
                        'id': med.id,
                        'treatment': med.treatment.treatment.name,
                        'expiration_date': med.expiration_date.strftime("%Y-%m-%d"),
                        'code': med.code,
                        'cn': med.treatment.treatment.cn,
                        'morning': treatment.m,
                        'lunch': treatment.t,
                        'dinner': treatment.n,
                        'others': treatment.o,
#                        'morning': "true" if treatment.m != 0 else "false",
#                        'lunch': "true" if treatment.t != 0 else "false",
#                        'dinner': "true" if treatment.n != 0 else "false",
#                        'others': "true" if treatment.o != 0 else "false",
                    })
            except Exception as e:
                print(e)
        #print(response)
        return render(request, "patient/spd/spd-sim.html", {'response': response})
    except Exception as e:
        print(show_exc(e))
        return JsonResponse({"error": True, "error_msg": show_exc(e)}, status=500)

def get_json_dir():
    spd_json_dir = os.path.abspath(os.path.join(MEDIA_ROOT, 'spd_json'))
    if not os.path.exists(spd_json_dir):
        os.makedirs(spd_json_dir)
    return spd_json_dir

def set_json_seg(dic):
    json = {"on":True, "bri":128, "seg":[{"start":0,"stop":30,"col":[[0,0,0]]},]}
    for i in range(7):
        for j in range(4):
            #val = True if dic[f"seg{j}"][0] else False
            val = True if get_float(dic[f"seg{j}"][0]) > 0 else False
            index = (i*4)+(3-j) if i % 2 == 0 else (i*4)+j
            if val:
                seg = {"start": index, "stop": index+1, "col":[[255, 255, 255]]}
            else:
                seg = {"start": index, "stop": index+1, "col":[[0, 0, 0]]}
            json["seg"].append(seg)
    #print(json)
    return json

@group_required("admins", "managers")
def spd_sim_json(request):
    values = get_param(request.GET, "values")
    spd_name = get_param(request.GET, "spd_name")
    dic = json.loads(values)
    json_export = set_json_seg(dic)
    send_spd_values(json_export, spd_name)

    #print(json_export)
    #spd_json_dir = os.path.abspath(os.path.join(MEDIA_ROOT, 'spd_json'))
    #if not os.path.exists(spd_json_dir):
    #    os.makedirs(spd_json_dir)

    #spd_json_dir = get_json_dir()
    #with open(f"{spd_json_dir}/wled_{request.user.company.id}.json", "w", encoding="utf-8") as f:
    #    f.write(json.dumps(json_export))        
    return HttpResponse("")

@group_required("admins", "managers")
def spd_sim_clear(request):
    spd_json_dir = get_json_dir()
    with open(f"{spd_json_dir}/wled_{request.user.company.id}.json", "w", encoding="utf-8") as f:
        f.write(json.dumps({"on":False,}))        
    return HttpResponse("")

def spd_sim_json_get(request, comp):
    json = ""
    spd_json_dir = os.path.abspath(os.path.join(MEDIA_ROOT, 'spd_json'))
    with open(f"{spd_json_dir}/wled_{comp}.json", "r", encoding="utf-8") as f:
        json = f.read()
    return HttpResponse(json)

@csrf_exempt
def spd_simulator(request, api_key=None, pillbox_deliver_code=None):
    try:
        if request.method == 'POST':
            pillbox_deliver_code = request.POST.get("pillbox_deliver_code")
            api_key = request.POST.get("api_key")
            if api_key != "1234":
                return JsonResponse({"error": True, "error_msg": "Unauthorized"}, status=401)
            pd = PillboxDeliver.objects.filter(code=pillbox_deliver_code).first()
            if pd == None:
                return JsonResponse({"error": True, "error_msg": "Not Found"}, status=404)
            meds = pd.deliver_meds.all()
            json_response = []
            for med in meds:
                treatment_spd = med.treatment
                print (treatment_spd.treatment.name)
                if treatment_spd.include_in_spd:
                    treatment = Tratamiento.objects.get(pk=treatment_spd.treatment.id)
                    json_response.append({
                        'id': med.id,
                        'treatment': med.treatment.treatment.name,
                        'expiration_date': med.expiration_date.strftime("%Y-%m-%d"),
                        'code': med.code,
                        'cn': med.treatment.treatment.cn,
                        'morning': treatment.m != 0,
                        'lunch': treatment.t != 0,
                        'dinner': treatment.n != 0,
                        'others': treatment.o != 0,

                    })
            return JsonResponse(json_response, safe=False, status=200)
        else:
            return render(request, "patient/spd/spd-simulator.html")
    except Exception as e:
        print(show_exc(e))
        return JsonResponse({"error": True, "error_msg": show_exc(e)}, status=500)

