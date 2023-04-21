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
                                                               
#def remote_auth(request, username=None):
def remote_auth(request):
    try:
        # authentication of the user, to check if it's active or None
        username = request.GET["username"] if "username" in request.GET else None
        if username != None:
            user = User.objects.get(username=username)
            user_auth = ExternalAuth.objects.get(username=username, domain=request.META['HTTP_HOST'])

            if user is not None and user_auth.request == user_auth.response:
                if user.is_active:
                    user_auth.response = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(128))
                    user_auth.response = user_auth.response.upper()
                    user_auth.update = datetime.datetime.now()
                    user_auth.save()
                    auth.login(request, user)
                    #LogManager(user=user, app=CAT_LOGIN).save_action(request.path, "Inicio Sesión")

                    return redirect(reverse('index'))
        return HttpResponse("Sorry. You are not authorized")
    except Exception as e:
        print (show_exc(e))
        return HttpResponse("Sorry. You are not authorized")

@check_remote_auth
def remote_test(request, username=None):
    return HttpResponse("OK")
