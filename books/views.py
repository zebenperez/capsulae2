from django.http import HttpResponse
from django.shortcuts import render
from django.template.loader import render_to_string
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _ 

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
#from .medication_lib import get_medication
#from .medication_update_lib import AempsUpdateParams, update_tasks
from .books_update_lib import BookUpdateParams,  update_tasks
from .models import Book

import time
import threading


'''
    Medication
'''
def get_update_params():
    aup = BookUpdateParams()
    dic = {}
    dic["last_update"] = aup.get_last_update()
    dic["is_running"] = aup.get_is_running()
    dic["total_pages"] = aup.get_total_pages()
    dic["current_page"] = aup.get_current_page()
    return dic

@group_required("admins",)
def books(request):
    return render(request, "books/books.html", {'items': [], 'update_params': get_update_params()})

@group_required("admins",)
def books_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "books/books-list.html", {'items': get_medication(search_value)})

#@group_required("admins",)
#def medication_print_tag(request, medication_id):
#    med = get_or_none(AempsCache, medication_id)
#    med_json = med.toJSON()
#    name = request.GET.get('name',"")
#
#    ficha = None
#    for code in med_json["atcs"]:
#        if len(code) > 5:
#            ficha = FichaPrincipioActivo.objects.filter(cod_atc=code, validate_date__lte=timezone.now()).first()
#
#    med_dic = {'tratamiento': {}, 'ficha': ficha}
#    med_dic['medicamento'] = { 'name' : med_json["name"], 'principles': med_json["principles"], 'atcs': med_json["atcs"], }
#
#    html_template = render_to_string('medication/med_tag_print.html', {'url_base': request.get_host(), 'lista_medicamentos': [med_dic]})
#    return HttpResponse(html_template)
#
'''
    Cache
'''
@group_required("admins",)
def update_cache(request):
    verification_code = request.GET.get('vc',None)

    if verification_code != "rALmmfHjZ5RDWjc5srqdyUTF0sssZbHAmVGslWElDDG1QqoNlH" and not request.user.is_superuser:
        return HttpResponse("Not allowed")

    #update_tasks()
    thread = threading.Thread(target=update_tasks)
    thread.start()
    time.sleep(5)

    return render(request, "books/update-cache-box.html", {'update_params': get_update_params()})

@group_required("admins",)
def update_cache_box(request):
    return render(request, "books/update-cache-box.html", {'update_params': get_update_params()})

