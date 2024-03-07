from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.utils.translation import ugettext_lazy as _ 
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from datetime import datetime, timedelta

from capsulae2.commons import get_or_none, show_exc, user_in_group
from capsulae2.decorators import group_required
from account.models import Company
from .common_lib import get_month_shifts, get_journeys_hours
from .models import Shift, Journey

import logging
logger = logging.getLogger(__name__)


'''
    Events
'''
def get_perms(user, groups):
    if "employee" in groups:
        return {"clone_shifts": False, "create_shifts": False, "remove_shifts": False}
    elif "managers" in groups:
        return {"clone_shifts": True, "create_shifts": True, "remove_shifts": True}
    elif "admins" in groups:
        return {"clone_shifts": True, "create_shifts": True, "remove_shifts": True}
    else:
        return {"clone_shifts": False, "create_shifts": False, "remove_shifts": False}

#    if hasattr(request, "employee"):
#        return {"clone_shifts": False, "create_shifts": False}
#    elif hasattr(request, "manager"):
#        return {"clone_shifts": True, "create_shifts": True}
#    else:
#        return {"clone_shifts": False, "create_shifts": False}

def get_shift_context(user, year=None, month=None):
    groups = user.groups.all().values_list('name', flat=True)
    perms = get_perms(user, groups)
    today, s_list = get_month_shifts(year,month,user) if "managers" in groups or "admins" in groups else get_month_shifts(year,month,None,user)
    shift_list = []
    for shift in s_list:
        shift_list += shift.date_split()
    return {
        'shift_list': shift_list,
        'today': today, 
        'current_year': datetime.today().year, 
        'next_year': (datetime.today().year + 1),
        'perms': perms
    }
#    if hasattr(request, "employee"):
#        today, shift_list = get_month_shifts(year, month, request.user)
#        return { 'shift_list': shift_list, 'today': today, 'perms': perms }
#    elif hasattr(request, "managers"):
#        today, shift_list = get_month_shifts(year, month)
#        return {
#            'shift_list': shift_list,
#            'today': today, 
#            'current_year': datetime.today().year, 
#            'next_year': (datetime.today().year + 1),
#            'perms': perms
#        }

def get_date(values):
    if "date" in values and len(values["date"]) == 10:
        return datetime.strptime(values["date"], "%Y-%m-%d")
    if "date" in values and len(values["date"]) == 20:
        return datetime.strptime(values["date"], "%Y-%m-%dT%H:%M:%SZ")
    return datetime.now()

@group_required("admins","managers","employee")
def index(request):
    return render(request, "shifts/index.html", get_shift_context(request.user))

@group_required("admins","managers","employee")
def shift_calendar(request):
    return render(request, "shifts/shift-calendar.html", get_shift_context(request.user))

@group_required("admins","managers","employee")
def calendar(request):
    if "obj_id" in request.GET:
        shift = get_or_none(Event, request.GET["obj_id"])
        year = str(shift.ini_date.year) if shift != None else None
        month = str(shift.ini_date.month) if shift != None else None
    else:
        year = request.GET["year"] if "year" in request.GET else None
        month = request.GET["month"] if "month" in request.GET else None
    return render(request, "shifts/load-shifts.html", get_shift_context(request.user, year, month))

@group_required("admins","managers","employee")
def get_shift(request, shift_id=None):
    obj = None
    if shift_id != None:
        obj = get_or_none(Shift, shift_id)
    elif "obj_id" in request.GET:
        obj = get_or_none(Shift, request.GET["obj_id"])
    groups = request.user.groups.all().values_list('name', flat=True)
    perms = get_perms(request.user, groups)
    context = {'obj': obj, 'perms': perms}
    template = "shifts/shift-details.html"

    if user_in_group(request.user, "managers") or user_in_group(request.user, "admins"):
        comp = Company.get_by_user(request.user)
        emp_list = []
        if obj == None:
            date = get_date(request.GET)
            obj = Shift.objects.create(ini_date=date, end_date=date, user=request.user)
            #obj = Shift.objects.create(name="---", ini_date=date, end_date=date)
            #obj.employees.set(emp_list)
            context["obj"] = obj
        context["emp_list"] = comp.users.all()
        template = "shifts/shift-form.html"
    return render(request, template, context)

@group_required("admins","managers","employee")
def add_employee(request):
    try:
        obj = get_or_none(Shift, request.GET["obj_id"])
        user = User.objects.get(pk=request.GET["value"])
        if user in obj.employees.all():
            obj.employees.remove(user)
        else:
            obj.employees.add(user)
        #obj.employees.clear()
        #for val in request.GET.getlist("value[]"):
        #    user = User.objects.get(pk=val)
        #    obj.employees.add(user)
        return HttpResponse("")
    except Exception as e:
        print(e)
        return HttpResponse("Error!")

@group_required("admins","managers","employee")
def remove_shift(request, shift_id):
    #year = month = None
    #if "obj_id" in request.GET:
        #obj = get_or_none(Event, request.GET["obj_id"])
    try:
        obj = get_or_none(Shift, shift_id)
        year = str(obj.ini_date.year)
        month = str(obj.ini_date.month)
        obj.delete()
    except Exception as e:
        print(e)
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))
    return redirect("shifts-index")
    #return render(request, "cam/load-shifts.html", get_shift_context(year, month))
    #return render(request, "shifts/shift-calendar.html", get_shift_context(request))

@group_required("admins","managers","employee")
def clone_shifts(request):
    try:
        ini_year = request.POST["ini_year"]
        end_year = request.POST["end_year"]
        ini_shifts = Event.objects.filter(ini_date__year = ini_year)
        for ev in ini_shifts:
            new_ev = Event.objects.create(ini_date=ev.ini_date.replace(year=int(end_year)), end_date=ev.end_date.replace(year=int(end_year)), name=ev.name, desc=ev.desc)
        return render(request, "shifts/load-shifts.html", get_shift_context())
    except Exception as e:
        logger.error("[cam-clone_shifts]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers","employee")
def check_updates(request):
    import subprocess

    res = ""
    try:
        result = subprocess.check_output("/var/www/django/capsulae2/check_updates.sh", shell=True, executable="/bin/bash", stderr=subprocess.STDOUT)
    except subprocess.CalledProcessError as cpe:
        result = cpe.output
    finally:
        for line in result.splitlines():
            l = line.decode()
            if "commit" in l or "Author" in l or "Date" in l:
                res = "{}<br/>{}".format(res, l)
            if len(l) == 0:
                res = "{}<br/>".format(res)
            #print(line.decode())
    return render(request, "check-updates.html", {"title": "Módulo de Turnos", "res": res})

@group_required("admins","managers","employee")
def check_log(request):
    from django.conf import settings
    import os 

    f = open(os.path.join(settings.BASE_DIR, "logs.txt"), "r", encoding='utf-8')
    text = f.read()
    return render(request, 'logs.html', {'text': text.replace("\n", "<br/>")})

'''
    Journeys
'''
@group_required("admins","managers","employee")
def journey_start(request):
    try:
        journey = Journey.objects.create(user=request.user, started=True)
        return redirect("pharma-index")
    except Exception as e:
        logger.error("[journey_start]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers","employee")
def journey_end(request):
    try:
        now = datetime.now()
        journey = Journey.objects.filter(user=request.user, started=True).first()
        if journey != None:
            journey.end_date = datetime.now()
            journey.started = False
            journey.save()
        return redirect("pharma-index")
    except Exception as e:
        logger.error("[journey_end]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers","employee")
def journey_list(request):
    try:
        user = User.objects.get(pk=request.GET["obj_id"])
        ini = datetime.strptime(request.GET["ini"], "%Y-%m-%d")
        end = datetime.strptime(request.GET["end"], "%Y-%m-%d").replace(hour=23, minute=59)
        j_list = Journey.objects.filter(user=user, ini_date__gte= ini, end_date__lte=end)
        context = {'user': user, 'journey_list': j_list, 'ini_date': ini, 'end_date': end}
        return render(request, "journeys/journey-list-details.html", context)
    except Exception as e:
        logger.error("[journey_end]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers","employee")
def journey_stats(request):
    try:
        user = User.objects.get(pk=request.GET["obj_id"])
        ini = datetime.strptime(request.GET["ini"], "%Y-%m-%d")
        end = datetime.strptime(request.GET["end"], "%Y-%m-%d")
        comp = Company.get_by_user(user)
        context = {'user': user, 'user_list': comp.users.all(), 'ini_date': ini, 'end_date': end}
        return render(request, "journeys/journey-stats-details.html", context)
    except Exception as e:
        logger.error("[journey_end]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))


