from django.shortcuts import render, redirect

from capsulae2.decorators import group_required
from capsulae2.commons import get_random_str, get_param, get_or_none, get_int, get_float, show_exc

from .models import UserPayment, UserProfile, Plan


@group_required("admins", "donor")
def donations_index(request):
    obj = UserProfile.objects.filter(user=request.user).first()
    items = UserPayment.objects.filter(user=request.user, donation=True)
    return render(request, "donations/donations.html", {'obj': obj, 'items': items})

@group_required("admins", "donor")
def donation_edit(request):
    try:
        obj = UserProfile.objects.filter(user=request.user).first()
        plan_list = Plan.objects.filter(active=True, profile__code="donation")
        return render(request, "donations/donation-form.html", {'obj': obj, "plan_list": plan_list})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins", "donor")
def donation_remove(request):
    try:
        obj = UserProfile.objects.filter(user=request.user).first()
        obj.plan = None
        obj.save()
        return redirect("donation-index")
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

