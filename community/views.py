#import requests
from django.shortcuts import render, redirect
from django.db.models import Q
#from django.core.mail import send_mail
#from django.core.urlresolvers import reverse
#from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt

# local-imports
#from .api import get_all, get_element, get_fci_form, get_organizations, FCI_FORM_SAVE
#from pharma.evolutionary_models import Evolutionary
#from accounts.models import Company

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from pharma.models import Pacientes
from .models import PatientFcoc, PatientFci, PatientActivity, Organization, PatientOrg, Procedure

#from .forms import OrganizationForm
#from generic.views import get_session_feedback


'''
    Organizations
'''
#def get_organizations(user, search_value=""):
def get_organizations(search_value=""):
    filters_to_search = ["name__icontains",]

    full_query = Q()
    if search_value != "":
        for myfilter in filters_to_search:
            full_query |= Q(**{myfilter: search_value})
    #full_query &= Q(**{'manager': user.id})

    return Organization.objects.filter(full_query)

#def get_organization_context(user, search_value=""):
    #return {'items': get_organizations(user, search_value)}
def get_organization_context(search_value=""):
    return {'items': get_organizations(search_value)}

@group_required("admins","managers")
def organizations(request):
    #return render(request, "organizations/organizations.html", {})
    return render(request, "organizations/organizations.html", get_organization_context())

@group_required("admins","managers")
def organization_list(request):
    return render(request, "organizations/organization-list.html", get_organization_context())
    #return render(request, "organizations/organization-list.html", get_organization_context(request.user))

@group_required("admins","managers")
def organization_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "organizations/organization-list.html", get_organization_context(search_value))
    #return render(request, "organizations/organization-list.html", get_organization_context(request.user, search_value))

@group_required("admins","managers")
def organization_form(request):
    #obj = Project.objects.create(manager=request.user)
    #po, created = PatientOrigin.objects.get_or_create(patient=obj)
    #return redirect(reverse('organization-view', kwargs={'organization_id': obj.id}))
    obj_id = get_param(request.GET, "obj_id")
    obj = get_or_none(Organization, obj_id)
    if obj == None:
        obj = Organization.objects.create()
    return render(request, "organizations/organization-form.html", {'obj': obj})

@group_required("admins","managers")
def organization_remove(request):
    obj = get_or_none(Organization, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "organizations/organization-list.html", get_organization_context())
    #return render(request, "organizations/organization-list.html", get_organization_context(request.user))


'''
    Procedures
'''
def get_procedures(search_value=""):
    filters_to_search = ["name__icontains",]

    full_query = Q()
    if search_value != "":
        for myfilter in filters_to_search:
            full_query |= Q(**{myfilter: search_value})

    return Procedure.objects.filter(full_query)

def get_procedure_context(search_value=""):
    return {'items': get_procedures(search_value)}

@group_required("admins","managers")
def procedures(request):
    return render(request, "procedures/procedures.html", get_procedure_context())

@group_required("admins","managers")
def procedure_list(request):
    return render(request, "procedures/procedure-list.html", get_procedure_context())

@group_required("admins","managers")
def procedure_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "procedures/procedure-list.html", get_procedure_context(search_value))

@group_required("admins","managers")
def procedure_form(request):
    obj_id = get_param(request.GET, "obj_id")
    obj = get_or_none(Procedure, obj_id)
    if obj == None:
        obj = Procedure.objects.create()
    return render(request, "procedures/procedure-form.html", {'obj': obj})

@group_required("admins","managers")
def procedure_remove(request):
    obj = get_or_none(Procedure, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "procedures/procedure-list.html", get_procedure_context())


#def patient_community(request, patient_id):
#    patient = get_or_none(Pacientes, patient_id)
#    po_list = PatientOrg.objects.filter(patient=patient)
#    return render(request, "community_patient.html", {'patient': patient, 'po_list': po_list})
#
#def patient_activities(request, patient_id):
#    context = {}
#    patient = get_or_none(Pacientes, patient_id)
#
#    items = get_all("activity")
#    context['patient'] = patient
#    context['patient_activities'] = PatientActivity.objects.filter(patient=patient)
#    context['activities_list'] = items
#    print(items)
#
#    context = get_session_feedback(context, request)
#    return render(request, 'patient_activities.html', context)
#
## ---------------------------
##  Muestra el formulario para crear el FCI remotamente y asociarlo al paciente(en el servidor de participa)
## ---------------------------
#def remote_fci_form(request, patient_id):
#    context = {}
#
#    context['patient'] = get_or_none(Pacientes, patient_id)
#    html = get_fci_form()
#    context['form_html'] = html
#    context['form_save_url'] = FCI_FORM_SAVE
#
#    return render(request, "remote_fci_form.html", context)
#
#
## def patient_fcoc_form_ajax(request, patient_id):
##     context = {}
##     patient = get_or_none(Pacientes, patient_id)
##     url = "%sfcoc/" % (PARTCIPA_REST_URL)
##     response = requests.get(url)
##     fcocs = response.json()
##     context['patient'] = patient
##     context['fcocs'] = fcocs
#
##     context = get_session_feedback(context, request)
##     return render(request, "patient_fcoc_form_ajax.html", context)
#
#'''
#    Derivación
#'''
#def referral_form(request, history_num, evolutionary_id=None, view=False):
#    """
#        Muestra el formulario de derivación para el paciente cuyo numero de historial
#        coincide con el <history_num> pasado como parámetro
#
#        :param request: Objeto tipo <Django.request>
#        :param history_num str: Numero de historial único del paciente
#    """
#
#    patient = Pacientes.objects.filter(n_historial=history_num).first()
#    context = {'view': bool(view)}
#    context['patient'] = patient 
#    #context['company'] = Company.objects.filter(Q(users=patient.id_user) | Q(manager=patient.id_user)).first()
#    context['company'] = Company.objects.filter(manager=patient.id_user).first()
#    #context['org_list'] = get_organizations()
#    context['org_list'] = Organization.objects.all()
#    if evolutionary_id != None:
#        ev = Evolutionary.objects.get(pk=evolutionary_id)
#        context["evolutionary"] = ev
#        context["professional"] = ev.observations[(ev.observations.find("Profesional:")+12):ev.observations.find("Observaciones:")-5]
#        context["observations"] = ev.observations[(ev.observations.find("Observaciones:")+14):]
#    return render(request, "referral_form.html", context)
#
#def send_form(request):
#    msg = "Formulario enviado correctamente"
#    val = ""
#    try:
#        if request.POST:
#            patient = get_or_none(Pacientes, request.POST["patient"])
#            company = request.POST["company"]
#            org_list = request.POST["organization"].split("|")
#
#            #val = "{}Organización: {}<br/>".format(val, request.POST["organization"])
#            val = set_field(request.POST, val, "field1", "¿La persona vive sola?")
#            val = set_field(request.POST, val, "field2", "¿Vive con alguna persona cuidadora de similar edad y/o personas con discapacidad,con problemas de salud mental, menores de edad?")
#            val = set_field(request.POST, val, "field3", "¿Cuenta con una red social en la que poder apoyarse?")
#            val = set_field(request.POST, val, "field4", "¿Existe barrera idiomática?")
#            val = set_field(request.POST, val, "field5", "¿Migrante?")
#            val = set_field(request.POST, val, "field6", "¿Está en situación de dependencia?")
#            val = set_field(request.POST, val, "field7", "¿Población excluida de Tarjeta Sanitaria?")
#            val = set_field(request.POST, val, "field8", "¿Recibe algún tipo de ayuda?")
#            val = set_field(request.POST, val, "field9", "¿Discapacidad reconocida?")
#            val = set_field(request.POST, val, "field10", "¿Cuenta con una vivienda que reúna las condiciones de habitabilidad?")
#            val = "{}<br/>Profesional: {}".format(val, request.POST["prof"])
#            val = "{}<br/>Observaciones: {}".format(val, request.POST["obs"])
#            ev = Evolutionary.objects.create(patient=patient, observations=val, matter="Derivación a: {}".format(org_list[0]))
#
#            if org_list[1] != "":
#                html = "Derivación del paciente <strong>{} {}</strong> con los siguientes datos:<br/><br/>".format(patient.nombre, patient.apellido)
#                html = "{}{}<br/><br/>".format(html, val)
#                link = "Puede ver la hoja de derivación a través de <a href='{}'>este enlace</a>".format(request.build_absolute_uri(reverse('referral_form', kwargs={'history_num':patient.n_historial, 'evolutionary_id': ev.id})))
#                html = "{}{}".format(html, link)
#                send_mail('Derivación de paciente', 'Derivación de paciente', 'info@capsulae.org', [org_list[1]], html_message=html)
#            else:
#                msg = "ERROR: email not found!"
#    except Exception as e:
#        print(e)
#        msg = "ERROR: {}".format(e)
#    return render(request, "send_form.html", {'msg': msg})
#
#def set_field(dic, val, field, text):
#    if field in dic: 
#        list_fields = ["field3", "field8", "field10"]
#        if field in list_fields:
#            return "{}{}: No<br/>".format(val, text) if dic[field] == "1" else "{}{}: Si<br/>".format(val, text)
#        else:
#            return "{}{}: Si<br/>".format(val, text) if dic[field] == "1" else "{}{}: No<br/>".format(val, text)
#    else:
#        return "{}{}: <br/>".format(val, text)
# 
#'''
#    Organizations
#'''
#@login_required(login_url='/pharma/index/')
#def organizations(request):
#    org_list = Organization.objects.all()
#    return render (request, 'organizations/organizations.html', {'org_list': org_list})
#
#@csrf_exempt
#def organizations_search_remote(request):
#    try:
#        value = request.POST.get('to_search', '____')
#    
#        org_list = Organization.objects.filter(name__icontains=value)
#        return render(request, "organizations/organization_list.html", {'org_list':org_list})
#    except Exception as e:
#        return render(request, "errors.html", context = {'error':"%s" % e})
#
#@login_required(login_url='/pharma/index/')
#def organizations_add(request):
#    form = OrganizationForm(instance = Organization())
#    return render (request, 'organizations/organization_form.html', {'form': form})
#
#@login_required(login_url='/pharma/index/')
#def organizations_save(request):
#    try:
#        item_id = request.POST.get("id", "")
#        org = Organization.objects.get(pk=item_id)
#        form = OrganizationForm(request.POST, instance=org)
#    except Exception as e:
#        form = OrganizationForm(request.POST)
#
#    if form.is_valid():
#        form.save()
#    #return redirect('organizations')
#    #return render (request, 'organization_form.html', {'form': form})
#    return render (request, 'organizations/organization_list.html', {'org_list': Organization.objects.all()})
#
#@login_required(login_url='/pharma/index/')
#def organization_edit(request, item_id):
#    org = Organization.objects.get(pk = item_id)
#    form = OrganizationForm(instance = org)
#    return render (request, 'organizations/organization_form.html', {'form':form , 'form_title': 'Modificar'})
#
#@login_required(login_url='/pharma/index/')
#def organization_delete(request, item_id):
#    org = Organization.objects.get(pk = item_id)
#    org.delete()
#    return redirect('organizations')
# 
#'''
#    Patient Organizations
#'''
#@login_required(login_url='/pharma/index/')
#def patientorg_add(request, patient_id):
#    return render (request, 'patientorg_form.html', {'patient_id': patient_id, 'organization_list': Organization.objects.all()})
#
#@login_required(login_url='/pharma/index/')
#def patientorg_edit(request, patientorg_id):
#    try:
#        po = PatientOrg.objects.get(pk=patientorg_id)
#        return render (request, 'patientorg_form.html', {'po': po, 'patient_id': po.patient.id, 'organization_list': Organization.objects.all()})
#    except Exception as e:
#        print(e)
#        return render(request, "errors.html", context = {'error':"%s" % e})
#
#def patientorg_save(request):
#    try:
#        item_id = request.POST.get("id", "")
#        po = PatientOrg.objects.get(pk=item_id)
#    except Exception as e:
#        po = PatientOrg()
#
#    try:
#        po.rol = request.POST.get("rol", "")
#        po.obs = request.POST.get("obs", "")
#        po.organization = Organization.objects.get(id=request.POST.get("organization_id", ""))
#        po.patient = Pacientes.objects.get(pk=request.POST.get("patient_id", ""))
#        po.save()
#
#        po_list = PatientOrg.objects.filter(patient=po.patient)
#        return render(request, "community_patient.html", {'patient': po.patient, 'po_list': po_list})
#    except Exception as e:
#        print(e)
#        return render(request, "errors.html", context = {'error':"%s" % e})
#
#@login_required(login_url='/pharma/index/')
#def patientorg_delete(request, patientorg_id):
#    try:
#        po = PatientOrg.objects.get(pk=patientorg_id)
#        patient = po.patient
#        po.delete()
#        po_list = PatientOrg.objects.filter(patient=po.patient)
#        return render(request, "community_patient.html", {'patient': patient, 'po_list': po_list})
#    except Exception as e:
#        print(e)
#        return render(request, "errors.html", context = {'error':"%s" % e})
#

