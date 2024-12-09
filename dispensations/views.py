from django.shortcuts import render, redirect, reverse
from django.views.decorators.csrf import csrf_exempt

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from account.models import Company
from .models import Dispensation
from .import_lib import get_json_datas, get_json_datas_farmatic, set_patient_json, set_dispensations_json


'''
    Dispensations
'''
def set_dispensations(comp, datas):
    if comp is None:
        return False
    msg = ""
    cip = ""
    for idx, item in enumerate(datas["dispensations"]):
        try:
            patient = set_patient_json(item, comp.manager)
            if patient == None:
                msg += "<br/>ERROR con el paciente {}".format(item["cip"])
            elif patient.cip != cip:
                msg += "<br/>Paciente {}:".format(patient.cip)
                cip = patient.cip

            disp = set_dispensations_json(item, patient)
            if disp == None:
                msg += "<br/> -- ERROR importando dispensación {}".format(item["code"]) 
            else:
                msg += "<br/> -- Dispensación {}:".format(disp.code)
        except Exception as e:
            print(e)
            msg += "<br/>ERROR con el paciente {}".format(item["cip"])
    return msg

def set_dispensations_farmatic(comp, datas):
    if comp is None:
        return False
    msg = ""
    cip = ""
    for idx, item in enumerate(datas["dispensations"]):
        try:
            patient = set_patient_json(item, comp.manager)
            if patient == None:
                msg += "<br/>ERROR con el paciente {}".format(item["cip"])
            elif patient.cip != cip:
                msg += "<br/>Paciente {}:".format(patient.cip)
                cip = patient.cip

            disp = set_dispensations_json(item, patient)
            if disp == None:
                msg += "<br/> -- ERROR importando dispensación {}".format(item["code"]) 
            else:
                msg += "<br/> -- Dispensación {}:".format(disp.code)
        except Exception as e:
            print(e)
            msg += "<br/>ERROR con el paciente {}".format(item["cip"])
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

@group_required("admins", "managers")
def dispensations_upload(request):
    comp = Company.objects.filter(manager = request.user).first()
    try:
        file_list = request.FILES.getlist('file')
        for f in file_list:
            #print(f)
            msg = set_dispensations(comp, get_json_datas(f, ods=f.name.endswith('.ods')))
    except Exception as e:
        msg = "ERROR: {}".format(e)
    return render(request, "profile/profile-dispensations-form.html", {"msg": msg})
    #return render(request, "upload_info.html", {"msg": msg})

@group_required("admins", "managers")
def farmatic_upload(request):
    comp = Company.objects.filter(manager = request.user).first()
    try:
        file_list = request.FILES.getlist('file')
        for f in file_list:
            #print(f)
            msg = set_dispensations_farmatic(comp, get_json_datas_farmatic(f))
    except Exception as e:
        msg = "ERROR: {}".format(e)
    return render(request, "profile/profile-dispensations-farmatic-form.html", {"msg": msg})
 
#@csrf_exempt
#def dispensations_set(request):
#    comp = Company.objects.filter(code=request.POST["cif"]).first()
#    err = set_dispensations(comp, json.loads(request.POST["datas"]))
#    return HttpResponse('{"error": "false"}') if not error else HttpResponse('{"error": "true", "": "User can not be authenticated"}')

