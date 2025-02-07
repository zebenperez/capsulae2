from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.models  import User
from django.contrib import auth
from django.http import HttpResponse
import random, string, datetime
from django.views.decorators.csrf import csrf_exempt
from .models import *
from django.contrib import auth, messages
#from actionlogs.views import *
#from pharma.views import CAT_LOGIN
from .decorators import *


# Create your views here.
def show_exc(e):
    import sys
    exc_type, exc_obj, exc_tb = sys.exc_info()
    return ("ERROR ===:> [%s in %s:%d]: %s" % (exc_type, exc_tb.tb_frame.f_code.co_filename, exc_tb.tb_lineno, str(e)))

def tokensignin(request):
    if (request.method == 'POST'):
        idtoken = request.POST.get('idtoken')
        signin_service = request.POST.get('service')
        email = request.POST.get('email')
        name = request.POST.get('name')
        user = None
        if User.objects.filter(username=email).exists():
            user = User.objects.get(username=email)
        else:
            user = User.objects.create_user(email, email, ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8)))
            user.first_name = name
            user.last_name = signin_service
            user.save()
        auth.login(request, user)

    return HttpResponse("%s, %s, %s, %s" % (user.pk, email, signin_service, name))
'''
    Remote
'''
@csrf_exempt
def get_remote_user(request):
    user = auth.authenticate(username=request.POST["user"], password=request.POST["password"])
    if user is not None:
        auth.login(request, user)
        if user.is_authenticated:
            dic = {"error": "false"}
            dic["groups"] = [g.name for g in user.groups.all()]
            return HttpResponse(dic)
    return HttpResponse('{"error": "true", "": "User can not be authenticated"}')

@csrf_exempt
def check_remote_user(request):
    user = auth.authenticate(username=request.POST["user"], password=request.POST["password"])
    if user is not None:
        auth.login(request, user)
        if user.is_authenticated:
            return redirect("index")
    return (render(request, "error_exception.html", {'exc':"This is not a valid user"}))
                                                               
def remote_auth(request):
    try:
        # authentication of the user, to check if it's active or None
        username = request.GET["username"] if "username" in request.GET else None
        url = request.GET["url"] if "url" in request.GET else ""
        if username != None:
            user_auth = ExternalAuth.objects.get(username=username, domain=request.META['HTTP_HOST'])
            user = User.objects.get(username=user_auth.username)
            user = User.objects.get(username=username)
            if user is not None and user_auth.request == user_auth.response:
                if user.is_active:
                    user_auth.response = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(128))
                    user_auth.response = user_auth.response.upper()
                    user_auth.update = datetime.datetime.now()
                    user_auth.save()
                    auth.login(request, user)
                    #print(f"USER {user_auth.localusername} authenticated in {user_auth.domain} as {user.username}")

                    if url != "":
                        name = url.split(":")[0];
                        param_name = url.split(":")[1].split(".")[0]
                        param_value = url.split(":")[1].split(".")[1]
                        return redirect(reverse(name, kwargs={param_name: param_value}))

                    return redirect(reverse('pharma-index'))
        return HttpResponse("Sorry. You are not authorized")
    except Exception as e:
        print (show_exc(e))
        return HttpResponse("Sorry. You are not authorized (Error: {})".format(e))

'''
    Remote LOPD
'''
from pharma.models import Pacientes
from lopd.models import LOPDConsents
import json
def check_cip(request):
    cip = request.GET["cip"] if "cip" in request.GET else ""
    comp = request.GET["company"] if "company" in request.GET else ""
    if cip != "" and comp != "":
        p = Pacientes.objects.filter(cip=cip, id_user=comp).first()
        if p != None:
            dic = {"error": "false"}
            lopd_list = []
            lopd = LOPDConsents.objects.filter(paciente=p)
            for l in lopd:
                lopd_list.append(request.build_absolute_uri(l.document.url))
            dic["id"] = p.id
            dic["code"] = p.n_historial
            dic["name"] = p.nombre
            dic["surname"] = p.apellido
            dic["nif"] = p.nif
            dic["phone"] = p.telefono1
            dic["lopd"] = lopd_list
            return HttpResponse(json.dumps(dic))
    return HttpResponse('{"error": "true", "msg": "User not found"}')

@csrf_exempt
def create_paciente(request):
    try:
        msg = ""
        if "company" in request.GET:
            user = User.objects.get(pk = request.GET["company"])
            if "cip" in request.GET:
                cip = request.GET["cip"]
                p = Pacientes.objects.filter(cip=cip, id_user=user).first()
                if p == None:
                    p = Pacientes()
                    p.fecha_nacimiento = datetime.datetime.min
                    p.created_at = datetime.datetime.now()
                    p.cod_postal = 0
                    p.sexo = ""
                    p.borrado = False
                    p.fotografia = ""
                    p.use_poli = ""
                    p.n_historial = ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))
                    p.id_user = user
                    p.nombre = request.GET["name"] if "name" in request.GET else ""
                    p.apellido = request.GET["surname"] if "surname" in request.GET else ""
                    p.nif = request.GET["nif"] if "nif" in request.GET else ""
                    try:
                        p.telefono1 = int(request.GET["phone"])
                    except:
                        p.telefono1 = 0
                    p.cip = cip
                    p.save()
                dic = {"error": "false", "id": "%s" % p.id}
                return HttpResponse(json.dumps(dic))
            else:
                msg = "CIP no reconocido"
        else:
            msg = "Empresa no reconocida"
    except Exception as e:
        msg = e
        print(e)
    return HttpResponse('{"error": "true", "msg": "%s"}' % msg)

@csrf_exempt
def update_paciente(request):
    try:
        msg = ""
        if "cip" in request.GET:
            cip = request.GET["cip"]
            p = Pacientes.objects.filter(cip=cip).first()
            if p != None:
                p.nombre = request.GET["name"] if "name" in request.GET else ""
                p.apellido = request.GET["surname"] if "surname" in request.GET else ""
                p.nif = request.GET["nif"] if "nif" in request.GET else ""
                p.telefono1 = request.GET["phone"] if "phone" in request.GET else ""
                p.save()

                dic = {"error": "false"}
                lopd_list = []
                lopd = LOPDConsents.objects.filter(paciente=p)
                for l in lopd:
                    lopd_list.append(request.build_absolute_uri(l.document.url))
                dic["id"] = p.id
                dic["code"] = p.n_historial
                dic["name"] = p.nombre
                dic["surname"] = p.apellido
                dic["nif"] = p.nif
                dic["phone"] = p.telefono1
                dic["lopd"] = lopd_list
                return HttpResponse(json.dumps(dic))
        else:
            msg = "CIP no reconocido"
    except Exception as e:
        msg = e
        print(e)
    return HttpResponse('{"error": "true", "msg": "%s"}' % msg)

'''
    Test
'''
@check_remote_auth
def remote_test(request, username=None):
    return HttpResponse("OK")
