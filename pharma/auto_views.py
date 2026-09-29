from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from capsulae2.commons import get_or_none_str, set_obj_field, create_obj_str, show_exc
from store.access import active_store_company


def store_object_for_active_company(request, app, model, obj_id):
    """Limit generic autosave endpoints to the selected warehouse company."""
    if app != 'store' or model not in ('product', 'provider', 'client'):
        return None
    from store.models import Client, Product, Provider
    model_class = {'product': Product, 'provider': Provider, 'client': Client}[model]
    company = active_store_company(request)
    if company is None:
        return None
    return model_class.objects.filter(pk=obj_id, company=company).first()

#import logging
#logger = logging.getLogger(__name__)


#@login_required
def autosave_field(request):
    try:
        params = request.POST if request.method == "POST" else request.GET
        app = params["model_name"].split(".")[0]
        model = params["model_name"].split(".")[1]
        obj_id = params["obj_id"]

        field = params["field"]

        try:
            reffield = params["ref_field"]
        except:
            reffield = "pk"
        try:
            value = params["value"]
        except:
            value = params.getlist("value[]")

        obj = store_object_for_active_company(request, app, model, obj_id) or get_or_none_str(app, model, obj_id, field=reffield)
        if app == 'store' and model in ('product', 'provider', 'client') and (obj is None or obj.company != active_store_company(request)):
            return HttpResponse("Not saved, object not found!")
        if obj != None:
            set_obj_field(obj, field, value)
            obj.save()
            return HttpResponse("Saved!")
        return HttpResponse("Not saved, object not found!")
    except Exception as e:
        #logger.error("[autosave_field]: %s" % e)
        print(show_exc(e))
        return HttpResponse("Not saved, some error is happened!")
        #return render(request, 'simple-error-plane.html', {'msg': str(e)})
        #return render(request, 'simple-error.html', {'msg': str(e)})

def autosave_fields(request):
    try:
        app = request.GET["model_name"].split(".")[0]
        model = request.GET["model_name"].split(".")[1]
        obj_id = request.GET["obj_id"] if "obj_id" in request.GET else ""

        fields = []
        for key in request.GET:
            if "field_" in key:
                fields.append(key.split("_")[1])

        if obj_id == "":
            obj = create_obj_str(app, model)
            if app == 'store' and model in ('product', 'provider', 'client'):
                company = active_store_company(request)
                if company is None:
                    return HttpResponse("Not saved, company not found!")
                obj.company = company
        else:
            obj = store_object_for_active_company(request, app, model, obj_id) or get_or_none_str(app, model, obj_id, field="pk")
            if app == 'store' and model in ('product', 'provider', 'client') and (obj is None or obj.company != active_store_company(request)):
                return HttpResponse("Not saved, object not found!")

        for field in fields:
            if app == 'store' and model in ('product', 'provider', 'client') and field == 'company':
                continue
            value = request.GET[f"field_{field}"]
            set_obj_field(obj, field, value)
        obj.save()
        return HttpResponse("Saved!")
        #return HttpResponse("Not saved, object not found!")
    except Exception as e:
        #logger.error("[autosave_field]: %s" % e)
        print(show_exc(e))
        return HttpResponse("Not saved, some error is happened!")
        #return render(request, 'simple-error-plane.html', {'msg': str(e)})
        #return render(request, 'simple-error.html', {'msg': str(e)})

#@login_required
def autoremove_obj(request):
    try:
        app = request.GET["model_name"].split(".")[0]
        model = request.GET["model_name"].split(".")[1]
        obj_id = request.GET["obj_id"]

        obj = get_or_none_str(app, model, obj_id)
        if obj != None:
            obj.delete()
            return HttpResponse("")
        return HttpResponse("Not deleted, object not found!")
    except Exception as e:
        #logger.error("[autoremove_obj] %s" % e)
        return render(request, 'simple-error.html', {'msg': str(e)})
