from django.http import HttpResponse
from django.shortcuts import render, redirect

from capsulae2.decorators import group_required
from capsulae2.commons import get_int, get_float, get_or_none, get_param, show_exc
from .models import *
from account.models import Company

def clean(val):
    return val.rstrip().lstrip()

@group_required("admins",)
def import_db(request):
    return render(request, "import/import.html")

def comp_map(comp_id):
    if comp_id == "1":
        #return Company.objects.filter(cif="08875218R").first()
        return Company.objects.get(pk=2)
    return None

@group_required("admins",)
def import_db_file(request):
    try:
        f = request.FILES["file"]
        db = request.POST["db"]

        lines = f.read().decode('utf').splitlines()
        i = 0
        for line in lines:
            if i > 0:
                print(line)
                l = line.split(",")
                #print(l[1])
                if db == "type":
                    comp = comp_map(l[5])
                    if comp != None:
                        online = True if l[4] == "t" else False
                        ProductType.objects.get_or_create(ext_code=clean(l[0]), online=online, name=clean(l[1]), company=comp)
                elif db == "prov":
                    comp = comp_map(l[5])
                    if comp != None:
                        Provider.objects.get_or_create(ext_code=clean(l[0]), name=clean(l[1]), code=clean(l[2]), email=clean(l[3]), phone=clean(l[4]), company=comp)
                elif db == "prod":
                    comp = comp_map(l[18])
                    if comp != None:
                        pt = ProductType.objects.filter(ext_code=l[2]).first()
                        prov = Provider.objects.filter(ext_code=l[8]).first()
                        prod, created = Product.objects.get_or_create(ext_code=clean(l[0]), code=clean(l[3]), name=clean(l[1]), product_type=pt, provider=prov, company=comp)
                        prod.deprecated = True if l[5] == "t" else False
                        prod.online = True if l[11] == "t" else False
                        prod.min_to_purchase = get_int(l[12]) 
                        prod.quantity = get_int(l[13])
                        prod.units_in_box = get_int(l[17])
                        #prod.alta_date = 
                        #prod.baja_date = 
                        #prod.expiry_date = 
                        prod.extra1 = clean(l[6])
                        prod.extra2 = clean(l[7])
                        prod.location = clean(l[10])
                        prod.save()
            i += 1

        return redirect("import")
    except Exception as e:
        print(e)
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

    return render(request, "import.html")
