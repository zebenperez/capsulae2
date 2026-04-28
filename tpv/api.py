from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from capsulae2.commons import show_exc, get_or_none, get_float
from account.models import Company
from store.models import Product, Invoice, InvoiceLine, Client, StoreOutflow

import datetime
import json


@csrf_exempt
def from_cms(request):
    result = "OK"
    try:
        data=json.loads(json.loads(request.body))
        company = Company.objects.get(pk=data["company_pk"])
        email = data["fields"]["email"]
        if Client.objects.filter(company=company, email=email).exists():
            client = Client.objects.filter(company=company, email=email).first()
        else:
            client = Client.objects.filter(company=company, code='0000').first()

        products = []
        quantities = {}
        faltantes = {}
        for item in data["items"]:
            code =item["fields"]["code"] 
            product = get_or_none(Product, code, "code")
            if product:
                if product.code in quantities.keys():
                    quantities[product.code] += 1
                else:
                    quantities[product.code] = 1
            else:
                if code in faltantes.keys():
                    faltantes[code] += 1
                else:
                    faltantes[code] = 1

        for code, units in quantities.items():
            product = get_or_none(Product, code, "code")
            if product:
                if (product.in_stock < units):
                    faltantes[code] = units-product.in_stock
                quantities[code] = product.in_stock

        result = json.dumps({'servidos':quantities, 'faltantes':faltantes})
    except Exception as e:
        print (show_exc(e))
        result = json.dumps({"error":show_exc(e)})
    return HttpResponse(f'{result}\n')

@csrf_exempt
def finish_from_cms(request):
    result = "OK"
    try:
        data=json.loads(json.loads(request.body))
        company = Company.objects.get(pk=data["company_pk"])
        email = data["fields"]["email"]
        if Client.objects.filter(company=company, email=email).exists():
            client = Client.objects.filter(company=company, email=email).first()
        else:
            client = Client.objects.filter(company=company, code='0000').first()

        products = []
        quantities = {}
        faltantes = {}
        for item in data["items"]:
            code =item["fields"]["code"] 
            if Product.objects.filter(company=company, code=code).exists():
                product = Product.objects.filter(company=company, code=code).first()
                if product.code in quantities.keys():
                    quantities[product.code] += 1
                else:
                    quantities[product.code] = 1
            else:
                if code in faltantes.keys():
                    faltantes[code] += 1
                else:
                    faltantes[code] = 1

        for code, units in quantities.items():
            product = Product.objects.filter(company=company, code=code).first()
            if product:
                if (product.in_stock < units):
                    faltantes[code] = units-product.in_stock
                quantities[code] = product.in_stock

        result = json.dumps({'servidos':quantities, 'faltantes':faltantes, 'hash':data["fields"]["hash"]})
        if len(faltantes.keys()) == 0:
            invoice = None
            try:
                hashinv = Invoice.newhash()
                number  = Invoice.next_number(company, "ORDERWEB")
                invoice = Invoice(number=number, hashinv=hashinv, typeinv="ORDERWEB", company=company, client=client)
                invoice.date = datetime.datetime.now()
                invoice.save()
                for item in data["items"]:
                    fields = item["fields"]
                    code = fields["code"] 
                    product = Product.objects.filter(company=company, code=code).first()
                    line = InvoiceLine(units=1, unit_price = float(fields["pvp"]), tax=float(fields["tax"]), product=product, invoice=invoice)
                    line.save()
                    outflow = StoreOutflow(quantity=line.units, unit_price=line.unit_price, ref=invoice.hashinv, product=line.product, client=invoice.client, tax=line.tax)
                    outflow.save()
                result = json.dumps({'servidos':quantities, 'faltantes':faltantes, 'hash':invoice.hashinv})
            except Exception as e:
                print (show_exc(e))
                result = json.dumps({"error":show_exc(e)})

    except Exception as e:
        print (show_exc(e))
        result = json.dumps({"error":show_exc(e)})
    return HttpResponse(f'{result}\n')
