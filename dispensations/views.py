from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt
from datetime import datetime
import threading

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from capsulae2.logs_lib import write_log
from account.models import Company
from pharma.common_lib import get_or_create_config_value, set_config_value
from .models import Dispensation
from .import_lib import get_json_datas, get_json_datas_farmatic, set_patient_json, set_dispensations_json

IMPORT_KEY = "IMPORT_UNYCOP"
IMPORT_FARMATIC_KEY = "IMPORT_FARMATIC"

'''
    Dispensations
'''
def set_dispensations(comp, file_name, datas):
    if comp is None:
        return False
    msg = ""
    cip = ""
    conf = get_or_create_config_value(IMPORT_KEY)
    set_config_value(IMPORT_KEY, "START")
    for idx, item in enumerate(datas["dispensations"]):
        try:
            patient = set_patient_json(item, comp.manager)
            if patient == None:
                msg = "ERROR con el paciente {}".format(item["cip"])
            elif patient.cip != cip:
                msg = "Paciente {}:".format(patient.cip)
                cip = patient.cip

            disp = set_dispensations_json(item, patient)
            if disp == None:
                msg = "-- ERROR importando dispensación {}".format(item["code"]) 
            else:
                msg = "-- Paciente: {} {} - Dispensación {} [{}]:".format(patient.nombre, patient.apellido, disp.name, disp.code)
            set_config_value(IMPORT_KEY, "{} {}".format(patient.nombre, patient.apellido))
        except Exception as e:
            print(e)
            msg = "ERROR con el paciente {}".format(item["cip"])
        write_log(msg, file_name, comp.id)
    set_config_value(IMPORT_KEY, "END")
    return msg

def set_dispensations_farmatic(comp, file_name, datas):
    if comp is None:
        return False
    msg = ""
    cip = ""
    conf = get_or_create_config_value(IMPORT_FARMATIC_KEY)
    set_config_value(IMPORT_FARMATIC_KEY, "START")
    for idx, item in enumerate(datas["dispensations"]):
        try:
            patient = set_patient_json(item, comp.manager, False)
            if patient == None:
                msg = "ERROR con el paciente {}".format(item["cip"])
            elif patient.cip != cip:
                msg = "Paciente {}:".format(patient.cip)
                cip = patient.cip

            disp = set_dispensations_json(item, patient)
            if disp == None:
                msg = "-- ERROR importando dispensación {}".format(item["code"]) 
            else:
                msg = "-- Dispensación {}:".format(disp.code)
            set_config_value(IMPORT_FARMATIC_KEY, "{} {}".format(patient.nombre, patient.apellido))
        except Exception as e:
            print(e)
            msg = "ERROR con el paciente {}".format(item["cip"])
        write_log(msg, file_name, comp.id)
    set_config_value(IMPORT_FARMATIC_KEY, "END")
    return msg

@group_required("admins", "managers")
def dispensations_view(request):
    try:
        disp = get_or_none(Dispensation, get_param(request.GET, "obj_id"))
        return render(request, "patient/dispensations/dispensations-view.html", {'item': disp})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins", "managers")
def dispensations_remove(request):
    try:
        disp = get_or_none(Dispensation, get_param(request.GET, "obj_id"))
        patient = disp.patient
        disp.delete()
        return render(request, "patient/dispensations/dispensations-list.html", {'obj': patient})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def dispensations_upload_back(comp, f):
    file_name = "{}_{}".format(datetime.now().strftime("%Y%m%d%H%M"), f.name)
    write_log("--- INICIANDO IMPORTACIÓN ---", file_name, comp.id)
    try:
        datas = get_json_datas(f, ods=f.name.endswith('.ods'))
        #msg = set_dispensations(comp, file_name, datas)
        thread = threading.Thread(target=set_dispensations, args=(comp, file_name, datas))
        thread.start()
    except Exception as e:
        write_log("{}".format(str(e)), file_name, comp.id)
    #write_log(comp.id, file_name, "--- FINALIZANDO IMPORTACIÓN ---")
 
@group_required("admins", "managers")
def dispensations_upload(request):
    msg = ""
    comp = Company.objects.filter(manager = request.user).first()
    try:
        file_list = request.FILES.getlist('file')
        for f in file_list:
            dispensations_upload_back(comp, f)
            #thread = threading.Thread(target=dispensations_upload_back, args=(comp, f))
            #thread.start()
            #time.sleep(5)

        #file_list = request.FILES.getlist('file')
        #for f in file_list:
            #print(f)
            #msg = set_dispensations(comp, get_json_datas(f, ods=f.name.endswith('.ods')))
    except Exception as e:
        msg = "ERROR: {}".format(e)
    return render(request, "profile/profile-dispensations-form.html", {"msg": msg})
    #return render(request, "upload_info.html", {"msg": msg})

def farmatic_upload_back(comp, f):
    file_name = "{}_{}".format(datetime.now().strftime("%Y%m%d%H%M"), f.name)
    write_log("--- INICIANDO IMPORTACIÓN ---", file_name, comp.id)
    try:
        datas = get_json_datas_farmatic(f)
        thread = threading.Thread(target=set_dispensations_farmatic, args=(comp, file_name, datas))
        thread.start()
    except Exception as e:
        print(e)
        write_log("{}".format(str(e)), file_name, comp.id)
    #write_log(comp.id, file_name, "--- FINALIZANDO IMPORTACIÓN ---")
 
@group_required("admins", "managers")
def farmatic_upload(request):
    msg = ""
    comp = Company.objects.filter(manager = request.user).first()
    try:
        file_list = request.FILES.getlist('file')
        for f in file_list:
            print(f)
            farmatic_upload_back(comp, f)
            #datas = get_json_datas_farmatic(f)
            #msg = set_dispensations_farmatic(comp, file_name, datas)
    except Exception as e:
        msg = "ERROR: {}".format(e)
    return render(request, "profile/profile-dispensations-farmatic-form.html", {"msg": msg})
    #return redirect(reverse("profile-view"))
 
#@csrf_exempt
#def dispensations_set(request):
#    comp = Company.objects.filter(code=request.POST["cif"]).first()
#    err = set_dispensations(comp, json.loads(request.POST["datas"]))
#    return HttpResponse('{"error": "false"}') if not error else HttpResponse('{"error": "true", "": "User can not be authenticated"}')

