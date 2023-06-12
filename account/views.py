from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.shortcuts import render

from capsulae2.decorators import group_required
from capsulae2.commons import get_random_str, get_param, get_or_none
from .models import *

import random, string

CAT_REGISTER = "Registro"


def validate_captcha(request):
    import urllib

    recaptcha_response = request.POST.get('g-recaptcha-response')
    url = 'https://www.google.com/recaptcha/api/siteverify'
    values = {
        'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        'response': recaptcha_response
    }
    data = urllib.parse.urlencode(values).encode()
    req =  urllib.request.Request(url, data=data)
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode())

    if result['success']:
        return True
    else:
        return False

@group_required("admins",)
def signup(request):
    email = request.POST.get('email','')
    confirmedemail = request.POST.get('confirmedemail','')

    user = None
    useractivate = None
    if (email == confirmedemail):
        if validate_captcha(request):
            try:
                password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
                if not User.objects.filter(username=email).exists():
                    user = User.objects.create_user(email, email, password)
                    user.first_name = request.POST.get('name')
                    user.last_name = request.POST.get('cif')
                    user.save()
                    profile = EmployeeProfile(user=user)
                    profile.save()
                    useractivate = UserActivate()
                    useractivate.user = user
                    useractivate.activate_key = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(128))
                    useractivate.save()
                    html_message = 'Gracias por tu inter&eacute;s en Capsulae. Para la activaci&oacute;n de la cuenta pincha <a href="http://%s/pharma/activate_account/%s/">aqu&iacute;</a>' % (request.META['HTTP_HOST'], useractivate.activate_key)
                    send_mail('Registro en Capsulae', 'Registro en Capsulae', 'info@shidix.com', [email], html_message=html_message)
                    context = {'user':user, 'useractivate':useractivate, 'error_code':0}
                    LogManager(user=user, app=CAT_REGISTER).save_action(request.path, "Usuario registrado sin confirmar")
                else:
                    user = User.objects.get(email=email)
                    context = {'user':user, 'useractivate':useractivate, 'error_code':1}
            except Exception as e:
                print(e)
                context = {'user':user, 'useractivate':useractivate, 'error_code':2, 'error_msg':e}
        else:
            context = {'error_msg': 'Error de validación del captcha' }
    return render (request, "account/signup.html", context)

def privacy_policy(request):
    return render(request, "account/privacy-policy.html", {})

'''
    Employees
'''
def get_employees_context(user, search_value=""):
    comp = Company.objects.filter(manager=user).first()
    if comp != None:
        if search_value != "":
            return {'items': comp.users.filter(user__username__icontains=search_value)}
        else:
            return {'items': comp.users.all()}
    return {'items': []}
    #return {'items': get_employees(user, search_value)}

@group_required("admins","managers")
def employees(request):
    return render(request, "employees/employees.html", get_employees_context(request.user))

@group_required("admins","managers")
def employee_list(request):
    return render(request, "employees/employee-list.html", get_employees_context(request.user))

@group_required("admins","managers")
def employee_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "employees/employee-list.html", get_employees_context(request.user, search_value))

@group_required("admins","managers")
def employee_form(request):
    obj_id = get_param(request.GET, "obj_id")
    obj = get_or_none(EmployeeProfile, obj_id)
    if obj == None:
        comp = Company.objects.filter(manager=request.user).first()
        if comp != None:
            user = User.objects.create_user(username=get_random_str(8))
            comp.users.add(user)
            obj = EmployeeProfile.objects.create(user=user)
    user_type_list = EmployeeType.objects.all()
    menu_list = request.user.menus.all()
    return render(request, "employees/employee-form.html", {'obj': obj, 'user_type_list': user_type_list, 'menu_list': menu_list})

@group_required("admins","managers")
def employee_remove(request):
    obj = get_or_none(EmployeeProfile, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.user.delete()
        obj.delete()
    return render(request, "employees/employee-list.html", get_employees_context(request.user))

