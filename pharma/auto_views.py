from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.shortcuts import render
from capsulae2.commons import get_or_none_str, set_obj_field, create_obj_str, show_exc

#import logging
#logger = logging.getLogger(__name__)


#@login_required
def autosave_field(request):
    try:
        app = request.GET["model_name"].split(".")[0]
        model = request.GET["model_name"].split(".")[1]
        obj_id = request.GET["obj_id"]

        field = request.GET["field"]

        try:
            reffield = request.GET["ref_field"]
        except:
            reffield = "pk"
        try:
            value = request.GET["value"]
        except:
            value = request.GET.getlist("value[]")

        obj = get_or_none_str(app, model, obj_id, field=reffield)
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
        else:
            obj = get_or_none_str(app, model, obj_id, field="pk")

        for field in fields:
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


