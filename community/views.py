#import requests
from django.contrib.auth.models import User, Group
from django.http import HttpResponse
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
from capsulae2.commons import get_or_none, get_param, show_exc, user_in_group
from capsulae2.email_lib import send_new_password_email
from pharma.models import Pacientes
from account.models import Company, Profile, UserProfile, UserMenu
#from account.email_lib import send_new_password_email
from .models import PatientFcoc, PatientFci, PatientActivity, PatientOrg, Procedure
from .models import Organization, OrganizationAddress, OrganizationInfo, OrganizationSocial, OrganizationResource

#from .forms import OrganizationForm
#from generic.views import get_session_feedback

import random, string, csv


'''
    Organizations
'''
def get_organizations(user, search_value=""):
    filters_to_search = ["name__icontains",]

    full_query = Q()
    if search_value != "":
        for myfilter in filters_to_search:
            full_query |= Q(**{myfilter: search_value})
    #full_query &= Q(**{'manager': user.id})

    if user_in_group(user, "admins"):
        return Organization.objects.filter(full_query)
    else:
        comp = Company.get_by_user(user)
        return Organization.objects.filter(full_query).filter(comp=comp)

def get_organization_context(user, search_value=""):
    return {'items': get_organizations(user, search_value)}

@group_required("admins","managers","employee")
def organizations(request):
    return render(request, "organizations/organizations.html", get_organization_context(request.user))

@group_required("admins","managers","employee")
def organization_list(request):
    return render(request, "organizations/organization-list.html", get_organization_context(request.user))

@group_required("admins","managers","employee")
def organization_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "organizations/organization-list.html", get_organization_context(request.user, search_value))

@group_required("admins","managers","employee")
def organization_form(request):
    obj_id = get_param(request.GET, "obj_id")
    obj = get_or_none(Organization, obj_id)
    if obj == None:
        obj = Organization.objects.create(comp=Company.get_by_user(request.user), user=request.user)
    return render(request, "organizations/organization-form.html", {'obj': obj})

@group_required("admins","managers","employee")
def organization_view(request, obj_id):
    try:
        obj = get_or_none(Organization, obj_id)
        try:
            info = obj.info
        except:
            info = OrganizationInfo.objects.create(org=obj)
        try:
            addr = obj.address
        except:
            addr = OrganizationAddress.objects.create(org=obj)
        try:
            social = obj.social
        except:
            social = OrganizationSocial.objects.create(org=obj)
        try:
            res = obj.resource
        except:
            res = OrganizationResource.objects.create(org=obj)
        context = {'obj': obj, 'info': info, 'addr': addr, 'social': social, 'res': res}
        return render(request, "organizations/organization-view.html", context)
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers","employee")
def organization_remove(request):
    obj = get_or_none(Organization, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "organizations/organization-list.html", get_organization_context(request.user))

@group_required("admins","managers","employee")
def organization_print(request):
    context = get_organization_context(request.user)
    context["company"] = Company.get_by_user(request.user)
    return render(request, "organizations/organization-print.html", context)

@group_required("admins","managers","employee")
def organization_csv(request):
    #context["company"] = Company.get_by_user(request.user)
    try:
        context = get_organization_context(request.user)

        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="organizations.csv"'},
        )

        writer = csv.writer(response)
        writer.writerow([
            'Nombre', 
            'Año de creación', 
            'Breve descripción', 
            'Correo electrónico', 
            'teléfono', 
            'Persona de contacto', 
            'Vía de derivación', 
            'Observaciones', 
            'Mismo lugar', 
            'Tipo de vía', 
            'Nombre de la vía',
            'Número',
            'Puerta',
            'Código postal',
            'Barrio',
            'Barrio otro lugar',
            'Localización actividad',
            'facebook',
            'instagram',
            'twitter',
            'youtube',
            'ambit',
            'activities',
            'participate',
            'health',
            'improvements',
            'resources',
            'free',
            'owner',
            'group',
            'group_other',
        ])
        for item in context["items"]:
            try:
                same_place = item.address.same_place
                street_type = item.address.street_type
                street_name = item.address.street_name
                number = item.address.number
                door = item.address.door
                postal_code = item.address.postal_code
                place = item.address.place
                place_other = item.address.place_other
                activity_place = item.address.activity_place
                facebook = item.social.facebook
                instagram = item.social.instagram
                twitter = item.social.twitter
                youtube = item.social.youtube
                ambit = item.info.ambit
                activities = item.info.activities
                participate = item.info.participate
                health = item.info.health
                improvements = item.info.improvements
                resources = item.info.resources
                free = item.resource.free
                owner = item.resource.owner
                group = item.resource.group
                group_other = item.resource.group_other
                description = item.resource.description
            except:
                same_place = ""
                street_type = ""
                street_name = ""
                number = ""
                door = ""
                postal_code = ""
                place = ""
                place_other = ""
                activity_place = ""
                facebook = ""
                instagram = ""
                twitter = ""
                youtube = ""
                ambit = ""
                activities = ""
                participate = ""
                health = ""
                improvements = ""
                resources = ""
                free = ""
                owner = ""
                group = ""
                group_other = ""
                description = ""
            writer.writerow([
                item.name, 
                item.year, 
                description,
                item.email, 
                item.phone, 
                item.contact, 
                item.derivation_way, 
                item.derivation, 
                same_place, 
                street_type, 
                street_name, 
                number, 
                door, 
                postal_code, 
                place, 
                place_other, 
                activity_place,
                facebook,
                instagram,
                twitter,
                youtube,
                ambit,
                activities,
                participate,
                health,
                improvements,
                resources,
                free,
                owner,
                group,
                group_other
            ])
        return response
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins")
def organization_share_users(request):
    try:
        obj = get_or_none(Organization, request.GET["obj_id"])
        user_list = User.objects.filter(groups__name='managers')
        return render(request, "organizations/organization-share.html", {'obj': obj, 'user_list': user_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def organization_share(request):
    try:
        obj = get_or_none(Organization, request.GET["obj_id"])
        user = get_or_none(User, request.GET["user"])
        new_org = obj
        new_org.pk = None
        new_org.user = user
        new_org.comp = Company.get_by_user(user)
        new_org.save()
        return redirect("organization-list")
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins")
def organization_create_user(request):
    try:
        obj = get_or_none(Organization, request.GET["obj_id"])
        if obj.email == "":
            return render(request, "organizations/organization-create-user.html", {'msg': "Se necesita un correo para crear el usuario!",})

        if User.objects.filter(username=obj.email).exists():
            return render(request, "organizations/organization-create-user.html", {'msg': "Este usuario ya existe!",})

        # Create User
        password = ''.join(random.SystemRandom().choice(string.ascii_uppercase + string.digits) for _ in range(8))
        user = User.objects.create_user(obj.email, obj.email, password)
        user.first_name = obj.name
        user.save()
        # Assign manager group
        manager_group = Group.objects.get(name='managers')
        manager_group.user_set.add(user)
        # Assign profile
        prof = Profile.objects.filter(code="asoc").first()
        if prof != None:
            pu, created = UserProfile.objects.get_or_create(user=user, profile=prof)
            um, created = UserMenu.objects.get_or_create(user=user)
            for menu in prof.menus.all():
                um.menus.add(menu)
        # Send Password
        send_new_password_email(password, [user.email])

        return render(request, "organizations/organization-create-user.html", {'msg': 'El usuario ha sido creado correctamente!'})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def organization_register(request, username):
    user = User.objects.filter(username = username).first()
    if user == None:
        return render(request, 'error_exception.html', {'exc': "Formulario no disponible!"})
    return render(request, "organizations/organization-register-form.html", {'username': username, 'company': Company.get_by_user(user)})

def organization_register_send(request):
    try:
        if request.POST:
            user = User.objects.filter(username = request.POST["username"]).first()
            comp = Company.get_by_user(user)
            org = Organization(user=user, comp=comp)
            org.reviewed = False 
            org.name = request.POST["name"]
            org.year = request.POST["year"]
            #org.address = request.POST["address"]
            org.email = request.POST["email"]
            org.phone = request.POST["phone"]
            org.contact = request.POST["contact"]
            org.contact_resp = request.POST["contact_resp"]
            org.in_charge = request.POST["in_charge"]
            org.in_charge_resp = request.POST["in_charge_resp"]
            #org.derivation_way = request.POST["derivation_way"]
            #org.derivation = request.POST["derivation"]
            org.save()

            addr = OrganizationAddress(org=org)
            addr.street_type = request.POST["street_type"] 
            addr.street_name = request.POST["street_name"] 
            addr.number = request.POST["number"] 
            addr.door = request.POST["door"] 
            addr.postal_code = request.POST["postal_code"] 
            #addr.place = request.POST["place2"] if request.POST["place"] == "otro" else request.POST["place"]
            addr.place = request.POST["place"]
            addr.place_other = request.POST["place2"] 
            addr.same_place = True if request.POST["same_place"] == "1" else False 
            addr.activity_place = request.POST["activity_place"] 
            addr.save()

            social = OrganizationSocial(org=org)
            social.facebook = request.POST["facebook"] 
            social.instagram = request.POST["instagram"] 
            social.twitter = request.POST["twitter"] 
            social.youtube = request.POST["youtube"] 
            social.save()

            info = OrganizationInfo(org=org)
            #info.ambit = request.POST["ambit"]
            info.activities = request.POST["activities"]
            info.participate = request.POST["participate"]
            info.health = request.POST["health"]
            info.improvements = request.POST["improvements"]
            info.resources = request.POST["resources"]
            info.save()

            #groups = "{};{}".format(";".join(request.POST.getlist("group")), request.POST["group2"])
            groups = ";".join(request.POST.getlist("group"))
            res = OrganizationResource(org=org)
            res.free = True if request.POST["free"] == "1" else False 
            res.owner = request.POST["owner"]
            res.group = groups
            res.group_other = request.POST["group2"]
            res.description = request.POST["description"]
            res.save()
 
        return render(request, "organizations/organization-register-sended.html", {})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def organization_register_tos(request):
    return render(request, "organizations/organization-register-{}.html".format(request.GET["temp"]), {})


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

@group_required("admins","managers","employee")
def procedures(request):
    return render(request, "procedures/procedures.html", get_procedure_context())

@group_required("admins","managers","employee")
def procedure_list(request):
    return render(request, "procedures/procedure-list.html", get_procedure_context())

@group_required("admins","managers","employee")
def procedure_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "procedures/procedure-list.html", get_procedure_context(search_value))

@group_required("admins","managers","employee")
def procedure_form(request):
    obj_id = get_param(request.GET, "obj_id")
    obj = get_or_none(Procedure, obj_id)
    if obj == None:
        obj = Procedure.objects.create()
    return render(request, "procedures/procedure-form.html", {'obj': obj})

@group_required("admins","managers","employee")
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

