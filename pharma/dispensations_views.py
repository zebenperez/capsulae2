from django.shortcuts import render, redirect, reverse

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from .dispensations_models import Dispensation


'''
    Dispensations
'''
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

