import csv
import hashlib
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import Q
from django.http import Http404, HttpResponse, HttpResponseBadRequest, HttpResponseNotAllowed
from django.shortcuts import get_object_or_404, render, redirect, reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _ 

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, set_obj_field
from .models import Client, Price, Product, Provider, ProductType, PurchaseDeliveryNote, StoreInflow
from .access import STORE_COMPANY_SESSION_KEY, accessible_store_companies, active_store_company

#import time
#import threading


@group_required("admins", "managers")
def store_company_select(request):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])
    company = accessible_store_companies(request.user).filter(pk=request.POST.get('company_id')).first()
    if company is None:
        return HttpResponseBadRequest('No tienes acceso al almacén seleccionado.')
    request.session[STORE_COMPANY_SESSION_KEY] = company.pk
    next_url = request.POST.get('next', '')
    if url_has_allowed_host_and_scheme(next_url, {request.get_host()}):
        return redirect(next_url)
    return redirect('products')


def store_company(request):
    company = active_store_company(request)
    if company is None:
        raise Http404('No tienes acceso a ningún almacén.')
    return company


'''
    Products
'''
def get_products_context(company, search_value=""):
    products = Product.objects.filter(company=company)
    if search_value:
        products = products.filter(
            Q(code__icontains=search_value)
            | Q(name__icontains=search_value)
        )
    return {'items': products[:50]}

@group_required("admins",)
def products(request):
    return render(request, "products/products.html", get_products_context(store_company(request)))

@group_required("admins",)
def products_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "products/products-list.html", get_products_context(store_company(request), search_value))


def get_company_product(request, obj_id):
    return get_object_or_404(Product, pk=obj_id, company=store_company(request))

@group_required("admins",)
def product_new(request):
    if request.method == "POST":
        obj = Product.objects.create(
            code=request.POST.get("code", "").strip(),
            name=request.POST.get("name", "").strip(),
            company=store_company(request),
        )
        return redirect(reverse('product-view', kwargs={'obj_id': obj.id}))
    return render(request, "products/product-new.html")


def albaran_text(content):
    """Decode supplier CSVs, normally exported as Windows-1252/Latin-1."""
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return content.decode(encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("No se ha podido leer la codificación del archivo.")


def albaran_decimal(value):
    try:
        return Decimal((value or "0").strip().replace(".", "").replace(",", "."))
    except InvalidOperation:
        raise ValueError("Importe no válido: {}".format(value))


def albaran_ean(value):
    return "".join(char for char in (value or "") if char.isdigit())


@group_required("admins",)
def purchase_delivery_notes(request):
    notes = PurchaseDeliveryNote.objects.filter(company=store_company(request)).select_related('provider', 'imported_by')
    return render(request, "delivery-notes/delivery-notes.html", {'items': notes})


@group_required("admins",)
def purchase_delivery_note_detail(request, obj_id):
    note = get_object_or_404(PurchaseDeliveryNote, pk=obj_id, company=store_company(request))
    inflows = note.inflows.select_related('product').order_by('product__name', 'pk')
    return render(request, "delivery-notes/delivery-note-detail.html", {'note': note, 'inflows': inflows})


@group_required("admins",)
def purchase_delivery_note_remove(request, obj_id):
    """Remove an erroneous import and the stock movements it created."""
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])

    note = get_object_or_404(PurchaseDeliveryNote, pk=obj_id, company=store_company(request))
    document_ref_prefix = "ALBARAN:{}:{}:".format(
        note.document_type,
        note.document_number,
    )
    inflows = StoreInflow.objects.filter(
        Q(purchase_delivery_note=note)
        | Q(ref__startswith=document_ref_prefix, product__company=note.company)
    )
    inflows_count = inflows.count()
    source_file = note.source_file

    # StoreInflow deliberately uses SET_NULL for its delivery-note relation, so
    # remove the movements explicitly.  Include matching orphan movements too:
    # imports created before this action could have their note deleted while
    # leaving the stock entries behind.
    with transaction.atomic():
        inflows.delete()
        note.delete()

    if source_file:
        source_file.delete(save=False)

    messages.success(
        request,
        "Albarán eliminado y {} entradas de stock retiradas.".format(inflows_count),
    )
    return redirect("purchase-delivery-notes")


@group_required("admins",)
def product_albaran_import(request):
    company = store_company(request)
    if request.method == "GET":
        return render(request, "products/product-albaran-import.html")
    if request.method != "POST":
        return HttpResponseNotAllowed(["GET", "POST"])

    upload = request.FILES.get("file")
    if upload is None:
        return HttpResponseBadRequest("Selecciona un archivo CSV de albarán.")

    try:
        content = upload.read()
        rows = list(csv.DictReader(albaran_text(content).splitlines(), delimiter=";"))
        required_columns = {"TIPO_DOCUMENTO", "NUM_DOCUMENTO", "FECHA", "EAN", "TITULO", "PVP", "UNIDADES", "IMPORTE"}
        if not rows or not required_columns.issubset(rows[0].keys()):
            return HttpResponseBadRequest("El CSV no tiene el formato de albarán esperado.")

        documents = {
            (row["TIPO_DOCUMENTO"].strip(), row["NUM_DOCUMENTO"].strip())
            for row in rows
        }
        if len(documents) != 1:
            raise ValueError("El archivo debe contener un único albarán con tipo y número.")
        document_type, document_number = next(iter(documents))
        if not document_type or not document_number:
            raise ValueError("El albarán debe indicar tipo y número de documento.")
        document_date = datetime.strptime(rows[0]["FECHA"].strip(), "%d-%m-%Y").date()
        file_hash = hashlib.sha256(content).hexdigest()

        if PurchaseDeliveryNote.objects.filter(
            company=company,
            document_type=document_type,
            document_number=document_number,
        ).exists():
            raise ValueError("Este albarán ya está registrado.")
        if PurchaseDeliveryNote.objects.filter(company=company, file_hash=file_hash).exists():
            raise ValueError("Este archivo ya ha sido importado.")

        created_products = updated_products = movements = skipped = 0
        total_amount = Decimal("0")
        providers = set()
        with transaction.atomic():
            delivery_note = PurchaseDeliveryNote.objects.create(
                company=company,
                imported_by=request.user,
                document_type=document_type,
                document_number=document_number,
                document_date=document_date,
                source_file=ContentFile(content, name=upload.name),
                file_hash=file_hash,
            )
            for row_number, row in enumerate(rows, start=2):
                ean = albaran_ean(row["EAN"])
                units = int(albaran_decimal(row["UNIDADES"]))
                if not ean or not row["TITULO"].strip() or units <= 0:
                    skipped += 1
                    continue

                document_ref = "ALBARAN:{}:{}:{}".format(
                    row["TIPO_DOCUMENTO"].strip(), row["NUM_DOCUMENTO"].strip(), row_number
                )
                # This is the import idempotency key: importing the same file
                # twice cannot increase stock a second time.
                if StoreInflow.objects.filter(ref=document_ref, product__company=company).exists():
                    skipped += 1
                    continue

                publisher = row.get("EDITORIAL/FABRICANTE", "").strip()[:200]
                provider = None
                if publisher:
                    provider, _ = Provider.objects.get_or_create(company=company, name=publisher)
                    providers.add(provider)

                product = Product.objects.filter(company=company, code=ean).first()
                if product is None:
                    product = Product.objects.create(
                        company=company,
                        code=ean,
                        ext_code=row.get("ISBN", "").strip()[:200],
                        name=row["TITULO"].strip()[:200],
                        extra1=row.get("AUTOR", "").strip()[:200],
                        provider=provider,
                    )
                    created_products += 1
                else:
                    # Do not overwrite product data maintained manually; use the
                    # delivery data only to complete missing fields.
                    changes = []
                    for field, value in {
                        "ext_code": row.get("ISBN", "").strip()[:200],
                        "extra1": row.get("AUTOR", "").strip()[:200],
                        "provider": provider,
                    }.items():
                        if value and not getattr(product, field):
                            setattr(product, field, value)
                            changes.append(field)
                    if changes:
                        product.save(update_fields=changes)
                        updated_products += 1

                date = datetime.strptime(row["FECHA"].strip(), "%d-%m-%Y")
                total = albaran_decimal(row["IMPORTE"])
                StoreInflow.objects.create(
                    purchase_delivery_note=delivery_note,
                    product=product,
                    quantity=units,
                    unit_price=total / units,
                    discount=albaran_decimal(row.get("DESCUENTO", "0")),
                    tax=albaran_decimal(row.get("IVA", "0")),
                    delivery_date=date,
                    reception_date=date,
                    ref=document_ref,
                    comments="{} {}".format(row["TIPO_DOCUMENTO"].strip(), row["NUM_DOCUMENTO"].strip()),
                )
                Price.objects.create(product=product, amount=albaran_decimal(row["PVP"]), sale=True, date=date)
                Price.objects.create(product=product, amount=total / units, sale=False, date=date)
                movements += 1
                total_amount += total

            delivery_note.lines_count = movements
            delivery_note.units_count = sum(inflow.quantity for inflow in delivery_note.inflows.all())
            delivery_note.total_amount = total_amount
            delivery_note.created_products = created_products
            delivery_note.updated_products = updated_products
            delivery_note.skipped_lines = skipped
            if len(providers) == 1:
                delivery_note.provider = providers.pop()
            delivery_note.save()
    except (ValueError, KeyError) as error:
        return HttpResponseBadRequest("No se ha importado el albarán: {}".format(error))

    messages.success(
        request,
        "Albarán importado: {} entradas, {} productos nuevos, {} actualizados y {} líneas omitidas.".format(
            movements, created_products, updated_products, skipped
        ),
    )
    return redirect("purchase-delivery-note-detail", obj_id=delivery_note.pk)

@group_required("admins",)
def product_remove(request, obj_id):
    if request.method != "POST":
        return HttpResponseNotAllowed(["POST"])
    get_company_product(request, obj_id).delete()
    return redirect('products')

@group_required("admins",)
def product_view(request, obj_id):
    obj = get_company_product(request, obj_id)
    product_type_list = ProductType.objects.filter(company=store_company(request))
    provider_list = Provider.objects.filter(company=store_company(request))
    context = {'obj': obj, 'product_type_list': product_type_list, 'provider_list': provider_list}
    return render(request, "products/product-view.html", context)

@group_required("admins",)
def product_datas(request):
    obj = get_company_product(request, request.GET["obj_id"])
    product_type_list = ProductType.objects.filter(company=store_company(request))
    provider_list = Provider.objects.filter(company=store_company(request))
    context = {'obj': obj, 'product_type_list': product_type_list, 'provider_list': provider_list}
    return render(request, "products/product-datas.html", context)

@group_required("admins",)
def product_prices(request):
    obj = get_company_product(request, request.GET["obj_id"])
    prices = obj.prices.order_by('-date')
    return render(request, "products/product-prices.html", {'obj': obj, 'prices': prices})

@group_required("admins",)
def product_price_new(request):
    obj = get_company_product(request, request.GET["obj_id"])
    return render(request, "products/product-price-new.html", {'obj': obj,})

@group_required("admins",)
def product_price_summary(request, obj_id):
    obj = get_company_product(request, obj_id)
    return render(request, "products/product-price-summary.html", {'obj': obj})

@group_required("admins",)
def product_stock_summary(request, obj_id):
    obj = get_company_product(request, obj_id)
    return render(request, "products/product-stock-summary.html", {'obj': obj})

@group_required("admins",)
def product_stock(request):
    obj = get_company_product(request, request.GET["obj_id"])
    return render(request, "products/product-stock.html", {'obj': obj,})

'''
    Providers
'''
def get_providers_context(company, search_value=""):
    providers = Provider.objects.filter(company=company)
    if search_value:
        providers = providers.filter(
            Q(code__icontains=search_value)
            | Q(name__icontains=search_value)
            | Q(phone__icontains=search_value)
            | Q(email__icontains=search_value)
        )
    return {'items': providers}

@group_required("admins","managers")
def providers(request):
    return render(request, "providers/providers.html", get_providers_context(store_company(request)))

@group_required("admins","managers")
def providers_list(request):
    return render(request, "providers/providers-list.html", get_providers_context(store_company(request)))

@group_required("admins","managers")
def providers_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "providers/providers-list.html", get_providers_context(store_company(request), search_value))

@group_required("admins","managers")
def providers_form(request):
    obj_id = get_param(request.GET, "obj_id")
    obj = Provider.objects.filter(pk=obj_id, company=store_company(request)).first() if obj_id else None
    #if obj == None:
    #    obj = Procedure.objects.create()
    return render(request, "providers/providers-form.html", {'obj': obj})

@group_required("admins","managers")
def providers_remove(request):
    obj = Provider.objects.filter(pk=request.GET["obj_id"], company=store_company(request)).first() if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "providers/providers-list.html", get_providers_context(store_company(request)))

'''
    Clients
'''
def get_clients_context(company, search_value=""):
    clients = Client.objects.filter(company=company)
    if search_value:
        clients = clients.filter(
            Q(code__icontains=search_value)
            | Q(name__icontains=search_value)
            | Q(dni__icontains=search_value)
            | Q(phone__icontains=search_value)
            | Q(email__icontains=search_value)
            | Q(address__icontains=search_value)
        )
    return {'items': clients}

@group_required("admins", "managers")
def clients(request):
    return render(request, "clients/clients.html", get_clients_context(store_company(request)))

@group_required("admins", "managers")
def clients_list(request):
    return render(request, "clients/clients-list.html", get_clients_context(store_company(request)))

@group_required("admins", "managers")
def clients_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "clients/clients-list.html", get_clients_context(store_company(request), search_value))

@group_required("admins", "managers")
def clients_form(request):
    obj_id = get_param(request.GET, "obj_id")
    # An empty obj_id is sent when the "Crear cliente" action opens a new
    # form.  Do not pass it to a numeric primary-key lookup.
    obj = (
        Client.objects.filter(pk=obj_id, company=store_company(request)).first()
        if obj_id
        else None
    )
    return render(request, "clients/clients-form.html", {'obj': obj})

@group_required("admins", "managers")
def clients_remove(request):
    obj_id = get_param(request.GET, "obj_id")
    if obj_id:
        Client.objects.filter(pk=obj_id, company=store_company(request)).delete()
    return render(request, "clients/clients-list.html", get_clients_context(store_company(request)))
