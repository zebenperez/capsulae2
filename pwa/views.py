from django.shortcuts import render, redirect
from django.urls import reverse
from django.http import HttpResponse
from django.contrib.auth import login, logout
from django.contrib.auth.models import User
from datetime import datetime

from capsulae2.decorators import group_required_pwa
from capsulae2.commons import user_in_group, get_or_none, show_exc
from pharma.models import Pacientes
from account.models import EmployeeProfile


#@group_required_pwa("employee", "admins")
@group_required_pwa("employee")
def index(request):
    try:
        return redirect(reverse('pwa-manager'))
    except:
        return redirect(reverse('pwa-login'))

def pin_login(request, patient_id=""):
    CONTROL_KEY = "SZRf2QMpIfZHPEh0ib7YoDlnnDp5HtjDqbAw"
    msg = ""  
    if request.method == "POST":
        context =  {}
        msg = "Operación no permitida"
        pin = request.POST.get('pin', None)
        control_key = request.POST.get('control_key', None)
        if pin != None and control_key != None:
            if control_key == CONTROL_KEY:
                try:
                    #Acceso de paciente
                    pat = Pacientes.objects.filter(nif=pin).first()
                    if pat != None:
                        return redirect(reverse('pwa-patient', kwargs={'patient_id': pat.id}))

                    #Acceso de usuarios "pharma"
                    emp = get_or_none(EmployeeProfile, pin, "pin")
                    login(request, emp.user)
                    request.session['pwa_app_session'] = True
                    if patient_id != "":
                        return redirect(reverse('pwa-manager', kwargs={'patient_id': patient_id}))
                    else:
                        return redirect(reverse('pwa-manager'))
                except Exception as e:
                    msg = "Pin no válido"
                    print(show_exc(e))
            else:
                msg = "Bad control"
    return render(request, "pwa-login.html", {'msg': msg})

def pin_logout(request):
    logout(request)
    return redirect(reverse('pwa-login'))

'''
    MANAGERS
'''
#@group_required_pwa("employee", "admins")
#@group_required_pwa("employee")
def manager_home(request, patient_id=None):
    if not request.user.is_authenticated:
        return redirect(reverse('pwa-login', kwargs={'patient_id': patient_id}))
    employee = EmployeeProfile.objects.get(user=request.user)
    if patient_id != None:
        patient = get_or_none(Pacientes, patient_id)
    else:
        patient  = None
    return render(request, "pwa/manager/home.html", {"obj": patient, "employee": employee})

'''
    PATIENTS
'''
def patient_home(request, patient_id):
    patient = get_or_none(Pacientes, patient_id)
    if patient == None:
        return render(request, "pwa/pwa-error.html", {})
    return render(request, "pwa/patient/home.html", {"obj": patient,})

def patient_books(request, patient_id):
    patient = get_or_none(Pacientes, patient_id)
    if patient == None:
        return render(request, "pwa/pwa-error.html", {})
    return render(request, "pwa/patient/books.html", {"obj": patient,})

def patient_books_print(request, patient_id):
    patient = get_or_none(Pacientes, patient_id)
    if patient == None:
        return render(request, "pwa/pwa-error.html", {})
    return render(request, "bibliomecum/receipts-print.html", {'obj': patient, 'comp': ''})


