from django.http import HttpResponse
from django.shortcuts import render, redirect
#from django.template.loader import render_to_string
from django.urls import reverse
from dateutil.relativedelta import relativedelta
#from weasyprint import HTML

#import html2text
import datetime
import requests
import numpy as np
import pytz

from capsulae2.commons import show_exc, get_param, get_or_none
from capsulae2.decorators import group_required
from account.models import Profile, Company#, Settings
from store.models import Product, Invoice, InvoiceLine, Client, StoreOutflow


@group_required("managers")
def index(request):
    try:
        comp = request.user.company
        invoice = Invoice.objects.filter(company=comp, typeinv="PRETPV").order_by('pk').last()
        if invoice is None:
            hashinv = Invoice.newhash()
            number  = Invoice.next_number(comp, "PRETPV")
            invoice = Invoice(number=number, hashinv=hashinv, typeinv="PRETPV", company=comp)
            invoice.save()
        context = {'invoice':invoice, 'orders':Invoice.objects.filter(company=comp, typeinv="ORDERWEB").count(), 'company':comp}
        return render(request, "tpv/index.html", context)
    except Exception as e:
        print (show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
#def tpv_add_product(request, product_id, hashinv):
def tpv_add_product(request):
    invoice = None
    try:
        product_id = get_param(request.GET, "product_id")
        hashinv = get_param(request.GET, "hashinv")
        invoice = Invoice.objects.get(hashinv = hashinv)
        product = Product.objects.get(pk = product_id)

        inv_line = InvoiceLine.objects.filter(product=product, invoice=invoice).first()
        if inv_line == None:
            inv_line = InvoiceLine(units=0, unit_price=product.last_pvp, tax=product.get_tax, product=product, invoice=invoice)
        inv_line.units += 1
        inv_line.save()
    except Exception as e:
        print (show_exc(e))
    return render(request, "tpv/tpv-main.html", {'invoice':invoice})

@group_required("managers")
def change_units_tpv_line(request):
    invoice = None
    try:
        inv_line = InvoiceLine.objects.get(pk=request.GET["obj_id"])
        product = inv_line.product
        invoice = inv_line.invoice
        field = request.GET["field"]
        if field == "units":
            inv_line.units = float(request.GET["value"])
        if field == "tax":
            inv_line.tax = float(request.GET["value"])
        if field == "discount":
            inv_line.discount = float(request.GET["value"])
        inv_line.save()
    except Exception as e:
        print (show_exc(e))
    return render(request, "tpv/tpv-main.html", {'invoice':invoice})

@group_required("managers")
#def remove_tpv_line(request, id_line):
def remove_tpv_line(request):
    invoice = None
    try:
        #inv_line = InvoiceLine.objects.get(pk=id_line)
        inv_line = get_or_none(InvoiceLine, get_param(request.GET, "id_line"))
        product = inv_line.product
        invoice = inv_line.invoice
        inv_line.delete()
    except Exception as e:
        print (show_exc(e))
    return render(request, "tpv/tpv-main.html", {'invoice':invoice})

@group_required("managers")
def client_by_code(request):
    invoice = None
    try:
        invoice = Invoice.objects.get(hashinv=request.GET['hashinv'])
        client = Client.objects.get(code=request.GET['value'])
        invoice.client = client
        invoice.client_name = client.name
        invoice.client_dni = client.dni
        invoice.client_addr = client.address
        invoice.save()
        return render(request, "tpv/client-datas.html", {'client': client})
        #return HttpResponse ("{} - {}".format(client.name, client.phone))
    except Exception as e:
        print (show_exc(e))
        return HttpResponse ("No hemos encontrado el cliente")

@group_required("managers")
def change_regulated(request):
    invoice = None
    try:
        invoice = Invoice.objects.get(hashinv=request.GET['hashinv'])
        invoice.regulated = (request.GET['value'] == "yes")
        invoice.save()
        return HttpResponse ("Saved")
    except Exception as e:
        print (show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
def change_method(request):
    invoice = None
    try:
        invoice = Invoice.objects.get(hashinv=request.GET['hashinv'])
        invoice.cash = (request.GET['value'] == "yes")
        invoice.save()
        return HttpResponse ("Saved")
    except Exception as e:
        print (show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
def confirm_sale(request, hashinv):
    invoice = None
    try:
        invoice = Invoice.objects.get(hashinv=hashinv)
        invoice.typeinv = "TPV"
        invoice.number = Invoice.next_number(request.user.company, "TPV")
        invoice.paid = True
        invoice.date = datetime.datetime.now()
        invoice.payment_date = datetime.datetime.now()
        invoice.save()

        for line in invoice.lines.all():
            outflow = StoreOutflow(quantity=line.units, unit_price=line.unit_price, ref=invoice.hashinv, product=line.product, client=invoice.client, tax=line.tax)
            outflow.save()
        return redirect(reverse("print-sale", kwargs={'hashinv':hashinv}))
        return redirect("get-sales")
    except Exception as e:
        print (show_exc(e))
        return redirect("tpv-index")

@group_required("managers")
def cancel_sale(request, hashinv):
    invoice = None
    try:
        invoice = Invoice.objects.get(hashinv=hashinv)
        invoice.delete()
        return redirect("tpv-index")
    except Exception as e:
        print (show_exc(e))
        return redirect("tpv-index")

@group_required("managers")
def remove_sale(request, hashinv):
    invoice = None
    try:
        invoice = Invoice.objects.get(hashinv=hashinv)
        outflows = StoreOutflow.objects.filter(ref=hashinv)
        for outflow in outflows:
            outflow.delete()
        invoice.delete()
        return redirect("get-sales")
    except Exception as e:
        print (show_exc(e))
        return redirect("get-sales")

@group_required("managers")
def sales(request, days=7):
    try:
        company = request.user.company
        limit_date = datetime.datetime.now() - relativedelta(days=days)
        sales = Invoice.objects.filter(company=company, typeinv = 'TPV', date__gte = limit_date, date__lte = datetime.datetime.now()).order_by('-date')
        return render(request, "tpv/sales.html", {'items':sales})
    except Exception as e:
        print (show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
def orders(request, days=10):
    try:
        company = request.user.company
        limit_date = datetime.datetime.now() - relativedelta(days=days)
        sales = Invoice.objects.filter(typeinv='ORDERWEB', date__gte=limit_date, date__lte=datetime.datetime.now(), company=company).order_by('-date')
        return render(request, "tpv/orders.html", {'items':sales})
    except Exception as e:
        print (show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

def order_detail(request, hashinv):
    item = Invoice.objects.get(hashinv = hashinv)
    return render(request, "tpv/detail.html", {'item':item})

def order_confirm(request, hashinv, cash=1):
    item = Invoice.objects.get(hashinv = hashinv)
    item.number  = Invoice.next_number(item.company, "TPV")
    item.date = datetime.datetime.now()
    item.payment_date= datetime.datetime.now()
    item.typeinv = "TPV"
    item.paid = True
    item.cash = (cash == 1)
    item.save()
    return redirect(reverse('get-sales'))

def order_ready(request, hashinv):
    invoice = None
    try:
        invoice = Invoice.objects.get(hashinv=hashinv)
        invoice.paid = not(invoice.paid)
        invoice.payment_date= datetime.datetime.now()
        invoice.save()

        try:
            if (invoice.paid):
                profile = Profile.get_profile(request)
                #domain = Settings.objects.get(profile = profile, key='domain-virtual-shop').value
                domain = ""
                url = f'https://{domain}/cms/shop/virtual-shop/processed/'
                data = {'apikey':invoice.company.apikey, 'hashinv':invoice.hashinv}
                r = requests.post(url, data=data)
                jsondata = json.loads(r.text)
        except Exception as e:
            print (show_exc(e))

        return redirect("get-orders")
    except Exception as e:
        print (show_exc(e))
        return redirect("tpv-index")

@group_required("managers")
def print_sale(request, hashinv):
    try:
        invoice = Invoice.objects.get(hashinv=hashinv)
        height = invoice.lines.count() * 5 + 120
        width = 50
        profile = request.user.employee_profile
        local_hour = datetime.datetime.now(pytz.timezone('Atlantic/Canary')).hour
        diff = local_hour - invoice.date.hour
        date = invoice.date if diff == 0 else invoice.date + datetime.timedelta(hours=diff)
        context = {'invoice':invoice, 'width':width, 'height':height, 'cash':invoice.cash, 'profile':profile, 'idate': date}
        return (render(request, "tpv/recibo.html", context))
#        try:
#            #template = Settings.objects.get(profile = profile, key='recibo_template').value
#            template = ""
#            return (render(request, template, context))
#        except Exception as e:
#            template = "tpv/recibo.html"
#            return (render(request, template, context))
    except Exception as e:
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
def print_invoice_sale(request, hashinv):
    try:
        invoice = Invoice.objects.get(hashinv=hashinv)
        #height = invoice.lines.count() * 5 + 120
        #width = 50
        profile = request.user.employee_profile
        diff = datetime.datetime.now(pytz.timezone('Atlantic/Canary')).hour - invoice.date.hour
        date = invoice.date if diff == 0 else invoice.date + datetime.timedelta(hours=diff)
        context = {'invoice':invoice, 'cash':invoice.cash, 'idate': date}
        #context = {'invoice':invoice, 'width':width, 'height':height, 'cash':invoice.cash, 'profile':profile, 'idate': date}
        try:
            #template = Settings.objects.get(profile=profile, key='invoice_template').value
            template = ""
            return (render(request, template, context))
        except Exception as e:
            return (render(request, "tpv/recibo.html", context))
    except Exception as e:
        print(show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
def print_invoice_client(request):
    try:
        invoice = Invoice.objects.get(hashinv=request.GET["hashinv"])
        return (render(request, "tpv/client-form.html", {"invoice": invoice}))
    except Exception as e:
        print(show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
def print_invoice_client_save(request):
    try:
        name = request.POST["name"]
        dni = request.POST["dni"]
        addr = request.POST["address"]
        invoice = Invoice.objects.get(id=request.POST["invoice"])
        invoice.client_name = name
        invoice.client_dni = dni
        invoice.client_addr = addr
        invoice.save()
        return redirect(reverse("print-invoice-sale", kwargs={"hashinv": invoice.hashinv}))
    except Exception as e:
        print(show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

def get_months():
    today = datetime.date.today()

    month_list = []
    for i in range(12):
        month = today - relativedelta(months=i)
        month_list.append(month.strftime('%Y-%m'))
    return month_list

@group_required("managers")
def zeta(request, month=""):
    try:
        company = request.user.company
        #date_range = [datetime.datetime.now() - relativedelta(days=days), datetime.datetime.now()]

        dt = datetime.datetime.strptime(month, "%Y-%m") if month != "" else datetime.datetime.now()
        ini_date = datetime.datetime(dt.year, dt.month, 1, 0, 0, 0)
        end_date = ((ini_date + relativedelta(months=1)) - relativedelta(days=1)).replace(hour=23, minute=59, second=59)
        date_range = [ini_date, end_date]

        sales = Invoice.objects.filter(company=company, payment_date__range=date_range, paid=True).order_by('-payment_date')
        sales_array = [[int(item.payment_date.strftime('%Y%m%d')), item.get_base(), item.get_taxes(), item.total(), int(item.cash)] for item in sales]
        sales_array = np.array(sales_array)
        summary = []
        try:
            date_list = np.unique(sales_array[:,0])
            for day in date_list:
                in_day = (sales_array[:,0] == day)
                total = sales_array[in_day]
                cash = sales_array[(sales_array[:,4] == 1) & (in_day)]
                cc = sales_array[(sales_array[:,4] == 0) & (in_day)]
                summary.append([datetime.datetime.strptime(f'{day:.0f}', '%Y%m%d'), len(total), np.sum(total[:,1]), np.sum(total[:,2]), np.sum(total[:,3]), len(cc), np.sum(cc[:,1]), np.sum(cc[:,2]), np.sum(cc[:,3]), len(cash), np.sum(cash[:,1]), np.sum(cash[:,2]), np.sum(cash[:,3]) ])
        except:
            day = int(datetime.datetime.today().strftime('%Y%m%d'))
            summary.append([datetime.datetime.strptime(f'{day:.0f}', '%Y%m%d'), 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])

        summary = sorted(summary, key=lambda x:x[0])

        return render(request, "tpv/zeta.html", {'summary':summary, 'month_list': get_months(), 'current_month': dt.strftime('%Y-%m')})
    except Exception as e:
        print(show_exc(e))
        return (render(request, "error_exception.html", {'exc':str(e)}))

@group_required("managers")
def get_orders_number(request):
    try:
        comp= Company.get_current(request)
        n_orders = Invoice.objects.filter(company=comp, typeinv="ORDERWEB").count()
        return HttpResponse(f'{n_orders}')
    except Exception as e:
        print (show_exc(e))
        return (HttpResponse('NaN'))

@group_required("managers")
def save_paid_amount(request):
    try:
        invoice_id = request.GET["invoice_id"]
        paid = request.GET["paid"]
        diff = request.GET["diff"]
        invoice = Invoice.objects.get(id=invoice_id)
        invoice.paid_amount = float(paid)
        invoice.diff_amount = float(diff)
        invoice.save()
    except Exception as e:
        print (show_exc(e))
    return HttpResponse ("")

'''
    Get product
'''
#def add_storeinflow_to_purchase(purchase, product):
#    si = StoreInflow.objects.filter(product = product, purchase = purchase).first()
#    if si == None:
#        si = StoreInflow(product = product, purchase = purchase)
#        si.unit_price = product.last_cost.pvp
#        si.discount = get_last_field_value(si, "discount")
#        si.tax = get_last_field_value(si, "tax")
#        si.quantity = 1
#    else:
#        si.quantity += 1
#    si.save()

@group_required("admins","managers")
def product_by_code(request):
    try:
        comp = request.user.company
    except Exception as e:
        return render(request, "error_exception.html", {'exc':show_exc(e)})

    product = Product.objects.filter(code = request.GET['value'].strip(), company=comp).first()
    if product == None:
        return render(request, "simple-error-plane.html", {'msg': "Producto no encontrado!"})

    invoice = get_or_none(Invoice, get_param(request.GET, 'hashinv'), "hashinv")
    return render(request, "tpv/tpv-add-product.html", {'product':product, 'invoice':invoice})

#@group_required("admins","managers")
#def product_by_code(request):
#    try:
#        comp = request.user.company
#    except Exception as e:
#        return render(request, "error_exception.html", {'exc':show_exc(e)})
#
#    if "purchase_id" in request.GET.keys():
#        purchase = get_object("purchase", request.GET["purchase_id"])
#        if purchase != None:
#            product = Product.objects.filter(code = request.GET['code'].strip(), company=comp).first()
#            if product == None:
#                return render(request, "error_exception.html", {'exc': 'Product not found!'})
#            add_storeinflow_to_purchase(purchase, product)
#            return render(request, "purchases/storeinflows.html", {'purchase': purchase, 'new': True})
#    else:
#        try:
#            product = Product.objects.get(code = request.GET['value'].strip(), company=comp)
#            invoice = Invoice.objects.get(hashinv = request.GET['hashinv'])
#            return render(request, "tpv/tpv-add-product.html", {'product':product, 'invoice':invoice})
#        except Exception as e:
#            print(e)
#            return render(request, "error_exception.html", {'exc':show_exc(e)})
#
#    return render(request, "common_error.html", {})
#
