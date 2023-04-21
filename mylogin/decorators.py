from functools import wraps
from django.shortcuts import render, redirect
from django.http import HttpResponse, JsonResponse
import datetime
import logging
logger = logging.getLogger(__name__)
from django.contrib.auth.models  import User
from django.core.exceptions import PermissionDenied

from capsulae2.commons import show_exc
from .models import *
import random, string, datetime

def check_remote_login(f):
    @wraps(f)
    def wrap(request, *args, **kwargs):
        try:
            domain = kwargs['domain']
            try:
                user_auth = ExternalAuth.objects.get(domain=domain, localusername=request.user.username)
            except Exception as e:
                user_auth = ExternalAuth(domain=domain, localusername=request.user.username, username=request.user.username, response=random_string(128))
            user_auth.request = user_auth.response
            user_auth.update = datetime.datetime.now()
            user_auth.save()
        except Exception as e:
            print(show_exc(e))
        return f(request, *args, **kwargs)

    return wrap

def check_remote_auth(f):
    @wraps(f)
    def wrap(request, *args, **kwargs):
        try:

            if "username" in kwargs.keys():
                username = kwargs['username']
            elif "user" in kwargs.keys():
                username = kwargs['user']
            elif "username" in request.POST.keys():
                username = request.POST.get('username')
            elif "user" in request.POST.keys():
                username = request.POST.get('user')
            else:
                username = request.user.username
            domain = request.META['HTTP_HOST'] 
            user = User.objects.get(username=username)
            user_auth = ExternalAuth.objects.get(domain=domain, localusername=username)
            if user.is_active and user_auth.request == user_auth.response:
                user_auth.response = ''.join(random.choice(string.ascii_letters + string.digits) for x in range(128))
                user_auth.response = user_auth.response.upper()
                user_auth.update = datetime.datetime.now()
                user_auth.save()
                #auth.login(request, user)
                return f(request, *args, **kwargs)
        except Exception as e:
            return HttpResponse('{"error": "true", "msg": "%s"}' % (show_exc(e)))
        return HttpResponse('{"error": "true", "msg": "You are not authorized"}')

    return wrap
