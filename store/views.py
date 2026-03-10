from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _ 

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, set_obj_field
from .models import Product, Provider, ProductType

#import time
#import threading


'''
    Products
'''
def get_products_context():
    return {'items': Product.objects.all()[:50]}

@group_required("admins",)
def products(request):
    return render(request, "products/products.html", get_products_context())

@group_required("admins",)
def products_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "products/products-list.html", get_products_context())

@group_required("admins",)
def product_view(request, obj_id):
    obj = get_or_none(Product, obj_id)
    product_type_list = ProductType.objects.all()
    provider_list = Provider.objects.all()
    context = {'obj': obj, 'product_type_list': product_type_list, 'provider_list': provider_list}
    return render(request, "products/product-view.html", context)

@group_required("admins",)
def product_datas(request):
    obj = get_or_none(Product, request.GET["obj_id"])
    product_type_list = ProductType.objects.all()
    provider_list = Provider.objects.all()
    context = {'obj': obj, 'product_type_list': product_type_list, 'provider_list': provider_list}
    return render(request, "products/product-datas.html", context)

@group_required("admins",)
def product_prices(request):
    obj = get_or_none(Product, request.GET["obj_id"])
    return render(request, "products/product-prices.html", {'obj': obj,})

@group_required("admins",)
def product_stock(request):
    obj = get_or_none(Product, request.GET["obj_id"])
    return render(request, "products/product-stock.html", {'obj': obj,})

'''
    Providers
'''
def get_providers_context():
    return {'items': Provider.objects.all()}

@group_required("admins","managers")
def providers(request):
    return render(request, "providers/providers.html", get_providers_context())

@group_required("admins","managers")
def providers_list(request):
    return render(request, "providers/providers-list.html", get_providers_context())

@group_required("admins","managers")
def providers_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "providers/providers-list.html", get_providers_context())

@group_required("admins","managers")
def providers_form(request):
    obj_id = get_param(request.GET, "obj_id")
    obj = get_or_none(Provider, obj_id)
    #if obj == None:
    #    obj = Procedure.objects.create()
    return render(request, "providers/providers-form.html", {'obj': obj})

@group_required("admins","managers")
def providers_remove(request):
    obj = get_or_none(Provider, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "providers/providers-list.html", get_providers_context())


