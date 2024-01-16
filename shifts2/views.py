from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.utils.translation import ugettext_lazy as _ 
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate
from datetime import datetime

from capsulae2.commons import get_or_none, show_exc
from capsulae2.decorators import group_required
from .common_lib import get_month_shifts
from .models import Shift

import logging
logger = logging.getLogger(__name__)


'''
    Events
'''
def get_perms(request):
    if hasattr(request, "employee"):
        return {"clone_shifts": False, "create_shifts": False}
    elif hasattr(request, "manager"):
        return {"clone_shifts": True, "create_shifts": True}
    else:
        return {"clone_shifts": False, "create_shifts": False}

def get_shift_context(request, year=None, month=None):
    perms = get_perms(request)
    today, shift_list = get_month_shifts(year, month)
    print(shift_list)
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

@group_required("admins","managers")
def index(request):
    return render(request, "shifts/index.html", get_shift_context(request))

@group_required("admins","managers")
def shift_calendar(request):
    return render(request, "shifts/shift-calendar.html", get_shift_context(request))

@group_required("admins","managers")
def calendar(request):
    if "obj_id" in request.GET:
        shift = get_or_none(Event, request.GET["obj_id"])
        year = str(shift.ini_date.year) if shift != None else None
        month = str(shift.ini_date.month) if shift != None else None
    else:
        year = request.GET["year"] if "year" in request.GET else None
        month = request.GET["month"] if "month" in request.GET else None
    return render(request, "shifts/load-shifts.html", get_shift_context(request, year, month))

@group_required("admins","managers")
def get_shift(request, shift_id=None):
    obj = None
    if shift_id != None:
        obj = get_or_none(Shift, shift_id)
    elif "obj_id" in request.GET:
        obj = get_or_none(Shift, request.GET["obj_id"])
    perms = get_perms(request)
    context = {'obj': obj, 'perms': perms}
    template = "shifts/shift-details.html"

    if hasattr(request, "manager"):
        #client_list = Client.objects.filter(discard=False)
        emp_list = []
        if obj == None:
            date = get_date(request.GET)
            obj = Shift.objects.create(name="Nuevo shifto", ini_date=date, end_date=date)
            obj.employees.set(emp_list)
            context["obj"] = obj
        context["client_list"] = client_list
        template = "shifts/shift-form.html"
    return render(request, template, context)

@group_required("admins","managers")
def remove_shift(request):
    year = month = None
    if "obj_id" in request.GET:
        obj = get_or_none(Event, request.GET["obj_id"])
        year = str(obj.ini_date.year)
        month = str(obj.ini_date.month)
        obj.delete()
    #return render(request, "cam/load-shifts.html", get_shift_context(year, month))
    return render(request, "shifts/shift-calendar.html", get_shift_context(request))

@group_required("admins","managers")
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
        return (render(request, "generic/error_exception.html", {'exc':show_exc(e)}))

