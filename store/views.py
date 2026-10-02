import csv
import hashlib
import os
from datetime import datetime
from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.files.base import ContentFile
from django.db import transaction
from django.db.models import OuterRef, Q, Subquery
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


@login_required
def store_company_select(request):
    """Select an accessible warehouse without invoking the group middleware.

    The destination is still checked against the companies assigned to the
    authenticated user below.
    """
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
    latest_pvp = Price.objects.filter(
        product_id=OuterRef('product_id'), sale=True,
    ).order_by('-date', '-pk').values('amount')[:1]
    inflows = note.inflows.select_related('product__provider').annotate(
        product_pvp=Subquery(latest_pvp),
    ).order_by('product__name', 'pk')
    warehouses = accessible_store_companies(request.user).exclude(pk=note.company_id)
    return render(request, "delivery-notes/delivery-note-detail.html", {
        'note': note,
        'inflows': inflows,
        'warehouses': warehouses,
        # A note ID belongs to the current warehouse.  After changing it,
        # return to the list instead of trying to open that foreign note.
        'store_company_next': reverse('purchase-delivery-notes'),
    })


def update_delivery_note_totals(note):
    """Keep a delivery note's displayed totals aligned with its real lines."""
    inflows = note.inflows.all()
    note.lines_count = inflows.count()
    note.units_count = sum(inflow.quantity for inflow in inflows)
    note.total_amount = sum(
        (inflow.unit_price * inflow.quantity for inflow in inflows),
        Decimal('0'),
    )
    note.save(update_fields=['lines_count', 'units_count', 'total_amount'])


def delivery_note_for_company(note, company, user):
    """Return the matching note in ``company``, creating it when needed."""
    target_note = PurchaseDeliveryNote.objects.filter(
        company=company,
        document_type=note.document_type,
        document_number=note.document_number,
    ).first()
    if target_note is not None:
        return target_note, False

    source_file = note.source_file
    source_file.open('rb')
    try:
        file_content = source_file.read()
    finally:
        source_file.close()
    target_note = PurchaseDeliveryNote.objects.create(
        company=company,
        imported_by=user,
        document_type=note.document_type,
        document_number=note.document_number,
        document_date=note.document_date,
        source_file=ContentFile(file_content, name=os.path.basename(source_file.name)),
        file_hash=note.file_hash,
    )
    return target_note, True


def product_for_company(product, company):
    """Find the destination product by code, or create its warehouse copy."""
    target_product = Product.objects.filter(company=company, code=product.code).first()
    if target_product is not None:
        return target_product
    return Product.objects.create(
        company=company,
        code=product.code,
        name=product.name,
        ext_code=product.ext_code,
        extra1=product.extra1,
        extra2=product.extra2,
        location=product.location,
        units_in_box=product.units_in_box,
        min_to_purchase=product.min_to_purchase,
        quantity=product.quantity,
        deprecated=product.deprecated,
        online=product.online,
        alta_date=product.alta_date,
        baja_date=product.baja_date,
        expiry_date=product.expiry_date,
        picture=product.picture.name if product.picture else None,
    )


@group_required("admins",)
def purchase_delivery_note_lines(request, obj_id):
    if request.method != 'POST':
        return HttpResponseNotAllowed(['POST'])

    note = get_object_or_404(PurchaseDeliveryNote, pk=obj_id, company=store_company(request))
    individual_inflow_id = request.POST.get('remove_inflow_id')
    individual_update_id = request.POST.get('update_inflow_id')
    if individual_inflow_id:
        # The row action always affects exactly that row, even if other
        # checkboxes remain selected from a prior batch operation.
        inflow_ids = [individual_inflow_id]
    elif individual_update_id:
        inflow_ids = [individual_update_id]
    else:
        inflow_ids = request.POST.getlist('inflow_ids')
    inflows = note.inflows.filter(pk__in=inflow_ids).select_related('product')
    if not inflows.exists():
        messages.error(request, 'Selecciona al menos una línea.')
        return redirect('purchase-delivery-note-detail', obj_id=note.pk)

    action = 'remove' if individual_inflow_id else ('update' if individual_update_id else request.POST.get('action'))
    if action == 'remove':
        count = inflows.count()
        with transaction.atomic():
            inflows.delete()
            update_delivery_note_totals(note)
        messages.success(request, '{} línea(s) eliminada(s) y retirada(s) del stock.'.format(count))
    elif action == 'update':
        quantities = {}
        try:
            for inflow in inflows:
                quantity = int(request.POST['quantity_{}'.format(inflow.pk)])
                if quantity <= 0:
                    raise ValueError
                quantities[inflow.pk] = quantity
        except (KeyError, TypeError, ValueError):
            messages.error(request, 'La cantidad debe ser un número entero mayor que cero.')
            return redirect('purchase-delivery-note-detail', obj_id=note.pk)
        with transaction.atomic():
            for inflow in inflows:
                inflow.quantity = quantities[inflow.pk]
                inflow.save(update_fields=['quantity'])
            update_delivery_note_totals(note)
        messages.success(request, '{} cantidad(es) actualizada(s).'.format(len(quantities)))
    elif action == 'move':
        target_company = accessible_store_companies(request.user).filter(
            pk=request.POST.get('target_company')
        ).exclude(pk=note.company_id).first()
        if target_company is None:
            messages.error(request, 'Selecciona un almacén de destino válido.')
            return redirect('purchase-delivery-note-detail', obj_id=note.pk)
        with transaction.atomic():
            target_note, _ = delivery_note_for_company(note, target_company, request.user)
            count = 0
            for inflow in inflows:
                StoreInflow.objects.create(
                    purchase_delivery_note=target_note,
                    product=product_for_company(inflow.product, target_company),
                    quantity=inflow.quantity,
                    tax=inflow.tax,
                    discount=inflow.discount,
                    unit_price=inflow.unit_price,
                    delivery_date=inflow.delivery_date,
                    order_date=inflow.order_date,
                    reception_date=inflow.reception_date,
                    ref=inflow.ref,
                    comments=inflow.comments,
                )
                count += 1
            inflows.delete()
            update_delivery_note_totals(note)
            update_delivery_note_totals(target_note)
        messages.success(request, '{} línea(s) movida(s) al almacén {}.'.format(count, target_company.name))
    else:
        messages.error(request, 'Acción no válida.')
    return redirect('purchase-delivery-note-detail', obj_id=note.pk)


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

        delivery_note = PurchaseDeliveryNote.objects.filter(
            company=company,
            document_type=document_type,
            document_number=document_number,
        ).first()
        if delivery_note is not None and delivery_note.file_hash != file_hash:
            raise ValueError("Ya existe un albarán con ese tipo y número.")
        if delivery_note is None and PurchaseDeliveryNote.objects.filter(company=company, file_hash=file_hash).exists():
            raise ValueError("Este archivo ya ha sido importado.")

        created_products = updated_products = movements = skipped = 0
        providers = set()
        with transaction.atomic():
            if delivery_note is None:
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
                        # AUTOR is kept in the product's Extra 1 / Autor field.
                        # As with the publisher, only fill a blank catalogue
                        # value so manual corrections are preserved.
                        "extra1": row.get("AUTOR", "").strip()[:200],
                        # EDITORIAL/FABRICANTE is stored in the product's
                        # provider relation.  Existing catalogue data wins;
                        # an empty provider is completed from the delivery.
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
                pvp = albaran_decimal(row["PVP"])
                # The product sheet reads its PVP from sale prices.  Reusing
                # the price for the same document date keeps an imported
                # delivery idempotent while updating the visible product PVP.
                sale_prices = Price.objects.filter(product=product, sale=True, date=date)
                if sale_prices.exists():
                    sale_prices.update(amount=pvp)
                else:
                    Price.objects.create(product=product, amount=pvp, sale=True, date=date)
                Price.objects.create(product=product, amount=total / units, sale=False, date=date)
                movements += 1

            update_delivery_note_totals(delivery_note)
            delivery_note.created_products += created_products
            delivery_note.updated_products += updated_products
            delivery_note.skipped_lines = skipped
            if len(providers) == 1:
                delivery_note.provider = providers.pop()
            delivery_note.save(update_fields=['created_products', 'updated_products', 'skipped_lines', 'provider'])
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
