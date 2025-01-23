from django.http import HttpResponse
from django.shortcuts import render, redirect

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, user_in_group
from pharma.models import Pacientes
from .models import BiblioReceipt, BiblioReceiptBook, BiblioReceiptAtc, BiblioReceiptCiap


'''
    BiblioReceipts
'''
@group_required("admins","managers")
def receipts_form(request):
    patient = get_or_none(Pacientes, get_param(request.GET, "patient_id"))
    if patient == None:
        return render(request, 'error_exception.html', {'exc': 'Paciente no encontrado!'})

    obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
    if obj == None:
        obj = BiblioReceipt.objects.create(patient=patient)
    return render(request, "bibliomecum/receipts-form.html", {'obj': obj})

@group_required("admins","managers")
def receipts_isbn_add(request):
    try:
        obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
        book = BiblioReceiptBook.objects.create(receipt=obj)
        return render(request, "bibliomecum/receipts-isbn-list.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def receipts_isbn_remove(request):
    try:
        obj = get_or_none(BiblioReceiptBook, get_param(request.GET, "obj_id"))
        receipt = obj.receipt
        obj.delete()
        return render(request, "bibliomecum/receipts-isbn-list.html", {'obj': receipt})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def receipts_atc_add(request):
    try:
        obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
        atc = get_param(request.GET, "atc")
        name = get_param(request.GET, "name")
        book = BiblioReceiptAtc.objects.create(receipt=obj, atc=atc, name=name)
        return render(request, "bibliomecum/receipts-atc-list.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def receipts_atc_remove(request):
    try:
        obj = get_or_none(BiblioReceiptAtc, get_param(request.GET, "obj_id"))
        receipt = obj.receipt
        obj.delete()
        return render(request, "bibliomecum/receipts-atc-list.html", {'obj': receipt})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def receipts_ciap_add(request):
    try:
        obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
        ciap = get_param(request.GET, "ciap")
        name = get_param(request.GET, "name")
        book = BiblioReceiptCiap.objects.create(receipt=obj, ciap=ciap, name=name)
        return render(request, "bibliomecum/receipts-ciap-list.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def receipts_ciap_remove(request):
    try:
        obj = get_or_none(BiblioReceiptCiap, get_param(request.GET, "obj_id"))
        receipt = obj.receipt
        obj.delete()
        return render(request, "bibliomecum/receipts-ciap-list.html", {'obj': receipt})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def receipts_remove(request):
    try:
        obj = get_or_none(BiblioReceipt, request.GET["obj_id"]) if "obj_id" in request.GET else None
        patient = obj.patient
        obj.delete()
        return render(request, "bibliomecum/receipts-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def receipts_print(request, obj_id):
    try:
        obj = get_or_none(BiblioReceipt, obj_id)
        return render(request, "bibliomecum/receipts-print.html", {'obj': obj, 'comp': request.user.company})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


