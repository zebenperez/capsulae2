from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, user_in_group
from pharma.models import Pacientes
from medication.medication_lib import get_medication
from medication.models import CieCiap
from .models import BiblioReceipt, BiblioReceiptBook, BiblioReceiptAtc, BiblioReceiptCiap
from .isbn_lib import isbn_search as isearch, title_author_search as tasearch


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


'''
    ISBNs
'''
#@group_required("admins","managers")
#def title_author_search(request):
#    try:
#        obj = get_or_none(BiblioReceipt, get_param(request.POST, "obj_id"))
#        title = get_param(request.POST, "title")
#        author = get_param(request.POST, "author")
#        title, author, isbn = tasearch(title, author)
#        if title != "":
#            book = BiblioReceiptBook.objects.create(receipt=obj, isbn=isbn, name=title, author=author)
#        return render(request, "bibliomecum/receipts-isbn-list.html", {'obj': obj})
#    except Exception as e:
#        print(e)
#        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def isbn_search(request):
    try:
        obj = get_or_none(BiblioReceipt, get_param(request.POST, "obj_id"))
        isbn = get_param(request.POST, "s_isbn")
        title = get_param(request.POST, "title")
        author = get_param(request.POST, "author")
        if isbn != "":
            isbn = isbn.replace('-','')
            title, author = isearch(isbn)
        else:
            title, author, isbn = tasearch(title, author)
        if title != "":
            book = BiblioReceiptBook.objects.create(receipt=obj, isbn=isbn, name=title, author=author)
        return render(request, "bibliomecum/receipts-isbn-list.html", {'obj': obj})
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

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

'''
    ATCs
'''
@group_required("admins","managers")
def atc_search(request):
    obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
    search_value = get_param(request.GET, "value")
    context = {'obj': obj, 'items': get_medication(search_value)}
    return render(request, "bibliomecum/medication-list.html", context)

@group_required("admins","managers")
def atc_patient(request):
    obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
    return render(request, "bibliomecum/atc-list.html", {'obj': obj,})

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

'''
    CIAPs
'''
def get_diagnoses(value):
    return CieCiap.objects.filter(Q(nombre__icontains=value) | Q(cie__icontains=value) | Q(ciap__icontains=value))

@group_required("admins","managers")
def ciap_search(request):
    obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
    search_value = get_param(request.GET, "value")
    print("--1--")
    print(search_value)
    print(get_diagnoses(search_value))
    context = {'obj': obj, 'items': get_diagnoses(search_value)}
    return render(request, "bibliomecum/cie_ciap-list.html", context)

@group_required("admins","managers")
def ciap_patient(request):
    obj = get_or_none(BiblioReceipt, get_param(request.GET, "obj_id"))
    return render(request, "bibliomecum/ciap-list.html", {'obj': obj,})

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


