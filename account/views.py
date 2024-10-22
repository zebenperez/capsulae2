from django.contrib.auth.models import User, Group
#from django.core.mail import send_mail
from django.shortcuts import render, redirect
from django.contrib import auth
from django.http import HttpResponse
from django.conf import settings
import uuid


from capsulae2.decorators import group_required
from capsulae2.commons import get_random_str, get_param, get_or_none, get_int, get_float, show_exc
from shifts2.models import Journey
from .email_lib import send_register_email, send_new_password_email
from .models import *

from datetime import datetime, timedelta
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

def signup_create_comp(dic, user):
    comp = Company.objects.create(manager=user)
    comp.code = dic["cif"]
    comp.name = dic["name"]
    comp.main_address = dic["address"]
    comp.town = dic["town"]
    comp.province = dic["province"]
    comp.email = dic["email1"]
    comp.save()
    return comp 

def signup_create_userprofile(dic, user):
    prof = get_or_none(Profile, dic["profile"])
    if prof != None:
        pu, created = UserProfile.objects.get_or_create(user=user, profile=prof)
        um, created = UserMenu.objects.get_or_create(user=user)
        for menu in prof.menus.all():
            um.menus.add(menu)

def signup_create_userpayment(user):
    expire_date = datetime.today() + timedelta(days=90)
    up = UserPayment.objects.create(user=user, expire_date=expire_date, desc="Creación de cuenta, 90 días de cortesía")

#@group_required("admins",)
def signup(request):
    email = request.POST.get('email1','')
    confirmedemail = request.POST.get('email2','')

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
                signup_create_comp(request.POST, user)
                signup_create_userprofile(request.POST, user)
                signup_create_userpayment(user)
                send_register_email(request.META['HTTP_HOST'], useractivate.activate_key, [email])
                context = {'user':user, 'useractivate':useractivate, 'error_code':0}
            else:
                user = User.objects.get(email=email)
                context = {'user':user, 'useractivate':useractivate, 'error_code':1}
        except Exception as e:
            print(e)
            return render(request, 'error_exception.html', {'exc':show_exc(e)})
        #else:
        #    context = {'error_msg': 'Error de validación del captcha' }
    else:
        context = {'error_code':2}
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
    email = request.POST.get('email',None)
    if email is not None:
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
        useractivate.valid_date = date.today() + timedelta(days=7)
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
    Profiles
'''
@group_required("admins", "managers")
def profile_view(request):
    comp = Company.objects.filter(manager=request.user).first()
    return render(request, "profile/profile-view.html", {'obj': comp})

'''
    Payments
'''
def check_account_datas(comp):
    return (comp.code != "" and comp.name != "" and comp.main_address != "" and comp.town != "" and comp.province != "" and comp.email != "")

def payment_error(request):
    if request.user.is_authenticated:
        comp = Company.objects.filter(manager=request.user).first()
        if comp == None:
            return render(request, 'error_exception.html', {'exc': 'Organización o Empresa no encontrada!'})
        register = check_account_datas(comp)
        up = UserPayment.objects.filter(user=request.user, cancel=False).order_by('-expire_date').first()
        plan_list = Plan.objects.filter(profile__id=1).order_by("amount")
        return render(request, "account/error-payments.html", {'payment': up, 'register': register, 'obj': comp, 'plan_list': plan_list})
    return redirect("pharma-index")

#@group_required("admins", "managers")
def payment_send(request, plan_id):
    plan = get_or_none(Plan, plan_id)
    if plan == None or not request.user.is_authenticated:
        return render(request, "account/payment-confirm.html", {'error': True})

    expire_date = datetime.today() + timedelta(days=plan.days)
    up = UserPayment.objects.create(user=request.user, amount=plan.amount, expire_date=expire_date, code=get_random_str(128), desc="Pago cuota")
    return redirect(f"{plan.payment_link}?client_reference_id={up.code}")
    return render(request, "account/payment-confirm.html", {'error': False, 'obj': up})

def payment_stripe_error(request):
    return render(request, "account/payment-confirm.html", {'error': True})

def payment_stripe_success(request, code):
    up = UserPayment.objects.find(code=code).first()
    if up == None:
        return render(request, "account/payment-confirm.html", {'error': True})
    return render(request, "account/payment-confirm.html", {'error': False, 'obj': up})

def payment_stripe_verify(request, code):
    from .libstripe import ShStripe

    # Get domainname from request
    domain = request.META['HTTP_HOST']
    stripe = None
    if "capsulae.org" in domain:
        stripe = ShStripe(settings.STRIPE_REAL_SECRET_KEY, domain)
    else:
        stripe = ShStripe(settings.STRIPE_TEST_SECRET_KEY, domain)
    session = stripe.get_session(code)
    if session == None:
        return render(request, "account/payment-confirm.html", {'error': True})
    if session.payment_status == "paid":
        if session.mode == "subscription":
            subscription = stripe.get_subscription(session.subscription)
            product = stripe.get_product(subscription.plan.product)
            code = product.name.split(' ')[2]
            up = UserPayment.objects.filter(code=code).last()
            if up != None:
                up.pay_date = datetime.now()
                up.cancel = False
                up.confirm = True
                up.save()
                return render(request, "account/payment-confirm.html", {'error': False, 'obj': up})
            return render(request, "account/payment-confirm.html", {'error': True})
            
        else:
            code = ""
            try:
                product = stripe.get_product(line_items.data[0].price.product)
                product = stripe.get_product_checkout(code)
                if "Donación" in product.name:
                    code = product.name.split(' ')[2]
                else:
                    code = session.client_reference_id
            except Exception as e:
                print(show_exc(e))
                code = session.client_reference_id
            up = UserPayment.objects.filter(code=code).last()
            if up != None:
                up.pay_date = datetime.now()
                up.cancel = False
                up.confirm = True
                up.save()
                return render(request, "account/payment-confirm.html", {'error': False, 'obj': up})
            else:
                return render(request, "account/payment-confirm.html", {'error': True})
    else:
        code = session.client_reference_id
        up = UserPayment.objects.filter(code=code).last()
        if up != None:
            up.cancel = True
            up.save()
            return render(request, "account/payment-confirm.html", {'error': True})

        return render(request, "account/payment-confirm.html", {'error': True})


        # print (session.client_reference_id)
        # print (session.amount_total)
        # print (session.customer_details.email)
        # print (session.customer_details.address)

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

    um, created = UserMenu.objects.get_or_create(user=obj.user)

    user_type_list = EmployeeType.objects.all()
    user_menu = request.user.menus.first()
    menu_list = user_menu.menus.all()
    return render(request, "employees/employee-form.html", {'obj': obj, 'user_type_list': user_type_list, 'user_menu': um, 'menu_list': menu_list})

@group_required("admins","managers")
def employee_remove(request):
    obj = get_or_none(EmployeeProfile, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.user.delete()
        obj.delete()
    return render(request, "employees/employee-list.html", get_employees_context(request.user))

@group_required("admins","managers")
def employee_journeys(request):
    try:
        obj = get_or_none(EmployeeProfile, request.GET["obj_id"])
        j_list = Journey.objects.filter(user=obj.user)
        return render(request, "employees/employee-journeys.html", {'obj': obj, 'items': j_list})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

'''
    Contributions
'''
def donations(request):
    return render (request, "account/donations.html", {})

def donor_create_user(email, password, name, cif):
    user = User.objects.create_user(email, email, password)
    user.first_name = name
    user.last_name = cif
    user.save()
    return user 

def donor_add_group(user):
    manager_group = Group.objects.get(name='donor')
    manager_group.user_set.add(user)

def donor_create_userprofile(profile, user, plan, amount):
    um, created = UserMenu.objects.get_or_create(user=user)
    for menu in profile.menus.all():
        um.menus.add(menu)
    return UserProfile.objects.create(profile=profile, user=user, plan=plan, amount=amount)

def donation_send(request):
    name = request.POST.get('name-d','')
    cif = request.POST.get('cif-d','')
    email = request.POST.get('email-d1','')
    confirmedemail = request.POST.get('email-d2','')
    plan_id = request.POST.get('plan-d','')
    amount = request.POST.get('amount-d','')
    msg = ""

    user = User.objects.filter(last_name=cif).first()
    if user != None:
        return render (request, "account/donation-send.html", {"error": 1, "user": user})
    user = User.objects.filter(email=email).first()
    if user != None:
        return render (request, "account/donation-send.html", {"error": 2, "user": user})
    if (email != confirmedemail):
        return render (request, "account/donation-send.html", {"error": 3})
    plan = get_or_none(Plan, plan_id)
    if plan == None:
        return render (request, "account/donation-send.html", {"error": 4})
    profile = Profile.objects.filter(code="donation").first()
    if profile == None:
        return render (request, "account/donation-send.html", {"error": 5})

    #if validate_captcha(request):
    try:
        password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
        user = donor_create_user(email, password, name, cif)
        donor_add_group(user)
        up = donor_create_userprofile(profile, user, plan, amount)
        #signup_create_userpayment(user)
        #send_register_email(request.META['HTTP_HOST'], useractivate.activate_key, [email])
        return render (request, "account/donation-send.html", {"error": 0, "user": user, "up": up})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def donation_custom(request):
    domain = request.META['HTTP_HOST']
    custom_pvp = get_int(request.POST.get('custom-pvp',None))
    period_days = request.POST.get('period', "")
    user = User.objects.get(username=request.POST.get("user", ""))

    from .libstripe import ShStripe
    stripe = None
    if "capsulae.org" in domain:
        stripe = ShStripe(settings.STRIPE_REAL_SECRET_KEY, domain)
    else:
        stripe = ShStripe(settings.STRIPE_TEST_SECRET_KEY, domain)

    if period_days == "0":
        plan = get_or_none(Plan, request.POST.get('plan', ""))
        expire_date = datetime.today() + timedelta(days=plan.days)
        up = UserPayment.objects.create(user=user,amount=custom_pvp,expire_date=expire_date,code=get_random_str(128),desc="Donación única",donation=True)
        donation_url = stripe.create_fundec_donation_once_url(custom_pvp * 100, up.code)
        return redirect(donation_url)
    else:
        periods = {"30": "month", "365": "year", "7": "week", "1": "day", "180": "semiannual", "90": "quarter"}
        labels = {"month": "mensual", "year": "anual", "week": "semanal", "day": "diario", "semiannual": "semestral", "quarter": "trimestral"}
        duration = {"month": 30, "year": 365, "week": 7, "day": 1, "semiannual": 180, "quarter": 90}

        period = periods[period_days]

        if custom_pvp == None:
            if "shidix.es" in domain:
                custom_pvp = random.randint(1, 100)
                # return render(request, "account/donation-send.html", {'error': 6})
            else:
                return render(request, "account/donation-send.html", {'error': 6})

        expire_date = datetime.today() + timedelta(days=duration[period])
        code = str(uuid.uuid4())
        desc = f"Donación personalizada {labels[period]} {code}"
        up = UserPayment.objects.create(user=user, amount=custom_pvp, expire_date=expire_date, code=code, desc=desc, donation=True)  

        #if request.user.is_authenticated:
        #    up = UserPayment.objects.create(user=request.user, amount=custom_pvp, expire_date=expire_date, code=code, desc=f"Donación personalizada {labels[period]} {code}")  
        #else:
        #    up = UserPayment.objects.create(user=User.objects.get(username='admin'), amount=custom_pvp, expire_date=expire_date, code=code, desc=f"Donación personalizada {labels[period]} {code}")
        
        subscription_url = stripe.create_fundec_subscription_url(custom_pvp * 100, up.code, period=period)
        return redirect(subscription_url)

def test(request):
    return HttpResponse("OK")
    from .libstripe import ShStripe
    domain = request.META['HTTP_HOST']
    stripe = None
    if "capsulae.org" in domain:
        stripe = ShStripe(settings.STRIPE_REAL_SECRET_KEY, domain)
    else:
        stripe = ShStripe(settings.STRIPE_TEST_SECRET_KEY, domain)

    product = stripe.get_product_checkout("cs_live_a1ZKXoyPCgiDYMB0UGBNLw0Pt247QTJIgvdp4Ii33VBkMDQrb7t9qzpeaH")

    print (product)
    if "Donación" in product.name:
        code = product.name.split(' ')[2]
    else:
        code = "ERROR"
    return HttpResponse(code)
