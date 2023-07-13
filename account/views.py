from django.contrib.auth.models import User, Group
#from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import auth


from capsulae2.decorators import group_required
from capsulae2.commons import get_random_str, get_param, get_or_none, show_exc
from capsulae2.email_lib import send_register_email, send_new_password_email
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

def privacy_policy(request):
    return render(request, "account/privacy-policy.html", {})

'''
    Signup and register
'''
def signup_create_user(dic, email, password):
    user = User.objects.create_user(email, email, password)
    user.first_name = dic["name"]
    user.last_name = dic["cif"]
    user.save()
    return user 

def signup_add_group(user):
    manager_group = Group.objects.get(name='managers')
    manager_group.user_set.add(user)

def signup_create_useractivate(user):
    useractivate = UserActivate()
    useractivate.user = user
    useractivate.activate_key = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(128))
    useractivate.save()
    return useractivate

def signup_create_userprofile(dic, user):
    prof = get_or_none(Profile, dic["profile"])
    if prof != None:
        pu, created = UserProfile.objects.get_or_create(user=user, profile=prof)
        um, created = UserMenu.objects.get_or_create(user=user)
        for menu in prof.menus.all():
            um.menus.add(menu)

#@group_required("admins",)
def signup(request):
    email = request.POST.get('email','')
    confirmedemail = request.POST.get('confirmedemail','')

    user = None
    useractivate = None
    if (email == confirmedemail):
        #if validate_captcha(request):
        try:
            password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
            if not User.objects.filter(username=email).exists():
                user = signup_create_user(request.POST, email, password)
                signup_add_group(user)
                profile = EmployeeProfile.objects.create(user=user)
                useractivate = signup_create_useractivate(user)
                signup_create_userprofile(request.POST, user)
                send_register_email(request.META['HTTP_HOST'], useractivate.activate_key, [email])
                context = {'user':user, 'useractivate':useractivate, 'error_code':0}

                #user = User.objects.create_user(email, email, password)
                #user.first_name = request.POST.get('name')
                #user.last_name = request.POST.get('cif')
                #user.save()
                #manager_group = Group.objects.get(name='managers')
                #manager_group.user_set.add(user)
                #profile = EmployeeProfile(user=user)
                #profile.save()
                #useractivate = UserActivate()
                #useractivate.user = user
                #useractivate.activate_key = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(128))
                #useractivate.save()
                #html_message = 'Gracias por tu inter&eacute;s en Capsulae. Para la activaci&oacute;n de la cuenta pincha <a href="http://%s/pharma/activate_account/%s/">aqu&iacute;</a>' % (request.META['HTTP_HOST'], useractivate.activate_key)
                #send_mail('Registro en Capsulae', 'Registro en Capsulae', 'info@shidix.com', [email], html_message=html_message)
                #send_email('Registro en Capsulae', 'Registro en Capsulae', 'info@shidix.com', [email], html_message)
                #LogManager(user=user, app=CAT_REGISTER).save_action(request.path, "Usuario registrado sin confirmar")
            else:
                user = User.objects.get(email=email)
                context = {'user':user, 'useractivate':useractivate, 'error_code':1}
        except Exception as e:
            print(e)
            return render(request, 'error_exception.html', {'exc':show_exc(e)})
            #context = {'user':user, 'useractivate':useractivate, 'error_code':2, 'error_msg':e}
        #else:
        #    context = {'error_msg': 'Error de validación del captcha' }
    return render (request, "account/signup.html", context)


def send_new_password(request, user_id):
    user = User.objects.get(pk=user_id)
    password=''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
    user.set_password(password)
    user.activation_date = date.today()
    user.save()
    #send_mail('Tu nuevo password en Capsulae', 'Tu nuevo password en Capsulae es %s' % password, 'info@shidix.com', [user.email])
    send_new_password_email(password, [user.email])
    return redirect('pharma-index')

def send_new_password_by_email(request):
    user = User.objects.filter(email=request.POST["email"]).first()
    if user == None:
        context = {'error_code':2}
        return render (request, "account/signup.html", context)
    password=''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(16))
    user.set_password(password)
    user.activation_date = date.today()
    user.save()
    #send_mail('Tu nuevo password en Capsulae', 'Tu nuevo password en Capsulae es %s' % password, 'info@shidix.com', [user.email])
    send_new_password_email(password, [user.email])
    return render (request, "account/signup.html", {'user': user, 'error_code': 3})

def activate_account(request, activation_key):
    msg_err = []
    context = {}
    try:
        user_activate = UserActivate.objects.get(activate_key=activation_key)
        if (user_activate.valid_date < date.today()):
            msg_err.append('ACTIVATION_DATE_EXPIRED')
        else:
            user_activate.activation_date = date.today()
            auth.login(request, user_activate.user)
            user_activate.save()
            #LogManager(user=user_activate.user, app=CAT_REGISTER).save_action(request.path, "El usuario ha activado su cuenta")
    except UserActivate.DoesNotExist:
        user_activate = None
        msg_err.append('KEY_DOES_NOT_EXIST')
    context["msg_err"] = msg_err
    context["user_activate"] = user_activate
    return render (request, "account/active_account.html", context)

def change_password(request, user_id):
    user_activate = UserActivate.objects.get(pk=user_id)
    if (user_activate.user.password == request.POST.get('old_password')):
        user_activate.user.set_password(request.POST.get('password'))
        user_activate.user.activation_date = date.today()
        user_activate.user.save()

        user = auth.authenticate(username=user_activate.user.username, password=request.POST.get('password'))
        if user is not None:
            if user.is_active:
                # this is where the user login actually happens, before this the user
                # is not logged in.
                auth.login(request, user)
                #return redirect('/pharma/main_screen/%d/' % user.id)
    return redirect('pharma-index')

def reactivate(request, activation_key):
    msg_err = []
    try:
        useractivate = UserActivate.objects.get(activate_key=activation_key)
        user = useractivate.user
        useractivate.activate_key = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(128))
        useractivate.valid_date = date.today() + datetime.timedelta(days=7)
        useractivate.save()
        send_register_email(request.META['HTTP_HOST'], useractivate.activate_key, [email])
        #html_message = 'Gracias por tu inter&eacute;s en Capsulae. Para la activaci&oacute;n de la cuenta pincha <a href="http://%s/pharma/activate_account/%s/">aqu&iacute;</a>' % (request.META['HTTP_HOST'], useractivate.activate_key)
        #send_mail('Registro en Capsulae', 'Registro en Capsulae', 'info@shidix.com', [user.email], html_message=html_message)
    except UserActivate.DoesNotExist:
        user = None
        useractivate = None
        msg_err.append('KEY_DOES_NOT_EXIST')
    return render(request, "signup.html", {'user':user, 'useractivate':useractivate, 'msg_err': msg_err})

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

