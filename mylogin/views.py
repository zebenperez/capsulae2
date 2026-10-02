from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib.auth.models  import User
from django.contrib import auth
from django.http import HttpResponse, HttpResponseForbidden
from django.conf import settings
from django.views.decorators.http import require_GET
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding
import base64, binascii, os, re, time
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

def _wordpress_sso_b64decode(value):
    if not isinstance(value, str) or not value:
        raise ValueError('invalid token encoding')
    return base64.urlsafe_b64decode(value + '=' * (-len(value) % 4))

WORDPRESS_SSO_PATIENT_PATH_RE = re.compile(r'^/pharma/patients/view/[1-9][0-9]*$')

def _wordpress_sso_issuers():
    registry_path = getattr(settings, 'WORDPRESS_SSO_ISSUERS_PATH', os.path.join(settings.BASE_DIR, 'mylogin', 'wordpress_sso_issuers.json'))
    with open(registry_path, encoding='utf-8') as registry_file:
        issuers = json.load(registry_file)
    if not isinstance(issuers, dict):
        raise ValueError('invalid issuer registry')
    return issuers

def _wordpress_sso_claims(token):
    if not isinstance(token, str) or len(token) > 4096:
        raise ValueError('invalid token')
    parts = token.split('.')
    if len(parts) != 3:
        raise ValueError('invalid token')
    signed = (parts[0] + '.' + parts[1]).encode('ascii')
    header = json.loads(_wordpress_sso_b64decode(parts[0]).decode('utf-8'))
    claims = json.loads(_wordpress_sso_b64decode(parts[1]).decode('utf-8'))
    signature = _wordpress_sso_b64decode(parts[2])
    if not isinstance(header, dict) or header.get('alg') != 'RS256' or not isinstance(claims, dict) or not isinstance(claims.get('iss'), str):
        raise ValueError('invalid token')
    issuer_config = _wordpress_sso_issuers().get(claims['iss'])
    if not isinstance(issuer_config, dict) or header.get('kid') != issuer_config.get('kid'):
        raise ValueError('unknown issuer')
    key_name = issuer_config.get('public_key')
    if not isinstance(key_name, str) or os.path.basename(key_name) != key_name:
        raise ValueError('invalid issuer key')
    key_path = os.path.join(settings.BASE_DIR, 'mylogin', key_name)
    with open(key_path, 'rb') as key_file:
        public_key = serialization.load_pem_public_key(key_file.read())
    public_key.verify(signature, signed, padding.PKCS1v15(), hashes.SHA256())
    now = int(time.time())
    for claim in ('iat', 'nbf', 'exp'):
        if not isinstance(claims.get(claim), int) or isinstance(claims.get(claim), bool):
            raise ValueError('invalid token')
    if (claims.get('aud') != 'capsulae2' or
            not isinstance(claims.get('sub'), str) or not claims['sub'].startswith('wordpress:') or
            not isinstance(claims.get('email'), str) or not claims['email'] or
            claims['iat'] < now - 70 or claims['iat'] > now + 10 or
            claims['nbf'] > now + 10 or claims['exp'] < now or claims['exp'] - claims['iat'] > 70):
        raise ValueError('invalid token')
    return claims

@require_GET
def wordpress_sso(request):
    """Create a Django session from a short-lived JWT emitted by WordPress."""
    try:
        claims = _wordpress_sso_claims(request.GET.get('token', ''))
        users = User.objects.filter(email__iexact=claims['email'], is_active=True)
        if users.count() != 1:
            raise ValueError('unmapped user')
        user = users.first()
        if not (user.is_superuser or user.groups.filter(name__in=['admins', 'managers', 'employee', 'donor']).exists()):
            raise ValueError('unauthorized user')
        auth.login(request, user, backend='django.contrib.auth.backends.ModelBackend')
        next_path = request.GET.get('next', '')
        if WORDPRESS_SSO_PATIENT_PATH_RE.fullmatch(next_path):
            return redirect(next_path)
        return redirect('pharma-index')
    except (ValueError, TypeError, OSError, UnicodeDecodeError, binascii.Error, json.JSONDecodeError, InvalidSignature):
        return HttpResponseForbidden('Acceso no autorizado.')

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
                    try:
                        now = datetime.datetime.now()
                        current_year = int(now.strftime("%y"))
                        year = int(cip[4:6])
                        year = "19{}".format(year) if year > current_year else "20{}".format(year)
                        p.fecha_nacimiento = datetime.datetime(int(year), int(cip[6:8]), int(cip[8:10]))
                    except Exception as e:
                        #print(e)
                        p.fecha_nacimiento = datetime.datetime.min
                    p.created_at = now
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
