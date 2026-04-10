from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc, validate_captcha
from .models import Activity, ActivityUser, Expense, Income, File, Folder, Project, Text

import csv


'''
    Projects
'''
def get_projects(user, search_value=""):
    filters_to_search = ["name__icontains",]

    full_query = Q()
    if search_value != "":
        for myfilter in filters_to_search:
            full_query |= Q(**{myfilter: search_value})
    full_query &= Q(**{'manager': user.id})

    return Project.objects.filter(full_query)

def get_project_context(user, search_value=""):
    return {'items': get_projects(user, search_value)}

@group_required("admins","managers", "employee")
def projects(request):
    return render(request, "projects/projects.html", {})

@group_required("admins","managers", "employee")
def project_list(request):
    return render(request, "projects/project-list.html", get_project_context(request.user))

@group_required("admins","managers", "employee")
def project_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "projects/project-list.html", get_project_context(request.user, search_value))

@group_required("admins","managers", "employee")
def project_new(request):
    obj = Project.objects.create(manager=request.user)
    #po, created = PatientOrigin.objects.get_or_create(patient=obj)
    return redirect(reverse('project-view', kwargs={'project_id': obj.id}))

@group_required("admins","managers", "employee")
def project_remove(request):
    obj = get_or_none(Project, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "projects/project-list.html", get_project_context(request.user))

'''
    Project
'''
@group_required("admins","managers", "employee")
def project_view(request, project_id):
    project = get_or_none(Project, project_id)
    return render(request, "project/project-view.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_details(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/project-details.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_form(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/project-form.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_texts(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/texts/text-list.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_activities(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/activities/activity-list.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_budget(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/budget/budget-list.html", {'obj': project})

@group_required("admins","managers", "employee")
def project_drive(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    folder_list = project.folders.filter(parent__isnull=True)
    file_list = project.files.filter(folder__isnull=True)
    print(file_list)
    return render(request, "project/drive/drive.html", {'obj': project, 'folder_list': folder_list, 'file_list': file_list})

'''
    Texts
'''
@group_required("admins","managers", "employee")
def project_text_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Text, request.GET["obj_id"]) if "obj_id" in request.GET else Text.objects.create(project=project)
        return render(request, "project/texts/text-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_text_remove(request):
    try:
        obj = get_or_none(Text, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/texts/text-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Activities
'''
@group_required("admins","managers", "employee")
def project_activity_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Activity, request.GET["obj_id"]) if "obj_id" in request.GET else Activity.objects.create(project=project)
        return render(request, "project/activities/activity-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_activity_remove(request):
    try:
        obj = get_or_none(Activity, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/activities/activity-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

#@group_required("admins","managers")
def project_activity_register(request, activity_id):
    try:
        obj = get_or_none(Activity, activity_id)
        return render(request, "project/activities/register-form.html", {'obj': obj, 'end': False})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

def project_activity_set_register(request):
    try:
        activity_id = request.POST["activity_id"]
        name = request.POST["name"]
        email = request.POST["email"]

        obj = get_or_none(Activity, activity_id)
        end = False
        msg = ""
        if validate_captcha(request) or True:
            au = ActivityUser.objects.filter(activity=obj, name=name, email=email).first()
            if au == None:
                au = ActivityUser.objects.create(activity=obj, name=name, email=email)
                end = True
            else:
                msg = "Este usuario ya se ha registrado!"
        else:
            msg = "Debe indicar que no es un robot!"
        return render(request, "project/activities/register-form.html", {'obj': obj, "end": end, "msg": msg})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_activity_register_list(request):
    try:
        obj = get_or_none(Activity, request.GET["obj_id"])
        return render(request, "project/activities/register-list.html", {'obj': obj,})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_activity_register_export(request, activity_id):
    try:
        obj = get_or_none(Activity, activity_id)

        response = HttpResponse(
            content_type='text/csv',
            headers={'Content-Disposition': 'attachment; filename="{}_{}.csv"'.format(obj.project.name, obj.name)},
        )

        writer = csv.writer(response)
        writer.writerow(['Nombre', 'Correo electrónico'])
        for item in obj.users.all():
            writer.writerow([item.name, item.email])
        return response
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


'''
    Budget
'''
@group_required("admins","managers", "employee")
def project_income_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Income, request.GET["obj_id"]) if "obj_id" in request.GET else Income.objects.create(project=project)

        return render(request, "project/budget/income-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_income_remove(request):
    try:
        obj = get_or_none(Income, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/budget/budget-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_expense_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Expense, request.GET["obj_id"]) if "obj_id" in request.GET else Expense.objects.create(project=project)

        return render(request, "project/budget/expense-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_expense_remove(request):
    try:
        obj = get_or_none(Expense, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/budget/budget-list.html", {'obj': project})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

'''
    Drive
'''
@group_required("admins","managers", "employee")
def project_folder_form(request):
    try:
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        if "obj_id" in request.GET:
            obj = get_or_none(Folder, request.GET["obj_id"])  
        else:
            parent = get_or_none(Folder, request.GET["parent_id"]) if request.GET["parent_id"]  != "" else None 
            obj = Folder.objects.create(project=project, parent=parent)
        return render(request, "project/drive/folder-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})


@group_required("admins","managers", "employee")
def project_folder_change(request):
    try:
        obj_id = request.GET["obj_id"]
        #enter = request.GET["enter"]

        obj = get_or_none(Folder, obj_id)
        #folder = obj if enter == "True" else obj.parent
        
        folder_list = obj.childs.all()
        file_list = obj.files.all()
        return render(request, "project/drive/drive.html", {"obj": obj.project, 'folder': obj,'folder_list': folder_list, 'file_list': file_list})
        #return render(request, "project/drive/drive.html", {"obj": obj.project, 'folder': folder,'folder_list': folder.childs.all()})
        #perms = get_perms(request, folder)
        #return render(request, "project/drive/index.html", {"obj": obj.client, 'folder': folder, 'perms': perms})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_folder_remove(request):
    try:
        obj_id = request.GET["obj_id"]
        folder_id = request.GET["folder_id"]

        obj = get_or_none(Folder, obj_id)
        if obj != None:
            project = obj.project
            obj.delete()
        folder = get_or_none(Folder, folder_id)
        folder_list = folder.childs.all() if folder != None else project.folders.filter(parent__isnull=True)
        file_list = folder.files.all() if folder != None else project.files.filter(folder__isnull=True)

        return render(request, "project/drive/drive.html", {"obj": project, 'folder': folder,'folder_list': folder_list, 'file_list': file_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_list(request):
    try:
        obj_id = request.GET["obj_id"]
        obj = get_or_none(File, obj_id)
        file_list = obj.folder.files.all() if obj.folder != None else obj.project.files.filter(folder__isnull=True)
        for f in file_list:
            print(f.name)
        return render(request, "project/drive/file-list.html", {"obj": obj.project, 'folder': obj.folder, 'file_list': file_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_add(request):
    try:
        obj_id = request.POST["obj_id"]
        field = request.POST["field"]
        folder_id = request.POST["folder"]
        file_list = request.FILES.getlist('file')

        obj = get_or_none(Project, obj_id)
        folder = get_or_none(Folder, folder_id)
        for f in file_list:
            #f_encrypt = encrypt(f, request.user.username)
            #obj_file = File(project=obj, proj_file=f_encrypt, name=f_encrypt.name, folder=folder)
            obj_file = File(project=obj, proj_file=f, name=f.name, folder=folder)
            obj_file.save()

        file_list = folder.files.all() if folder != None else obj.files.filter(folder__isnull=True)
        return render(request, "project/drive/file-list.html", {"obj": obj, 'folder': folder, 'file_list': file_list})
    except Exception as e:
        print(e)
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers", "employee")
def project_file_form(request):
    try:
        obj = get_or_none(File, request.GET["obj_id"])  
        return render(request, "project/drive/file-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_remove(request):
    try:
        obj_id = request.GET["obj_id"]

        obj = get_or_none(File, obj_id)
        if obj != None:
            project = obj.project
            folder = obj.folder
            obj.delete()
        file_list = folder.files.all() if folder != None else project.files.filter(folder__isnull=True)

        return render(request, "project/drive/file-list.html", {"obj": project, 'folder': folder, 'file_list': file_list})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers", "employee")
def project_file_get(request, obj_id):
    try:
        f = get_or_none(File, obj_id) 
        #f_out = decrypt(f.client_file, f.client.password)
        #response = HttpResponse(f_out, 'application/force-download')
        #response['Content-Disposition'] = 'attachment; filename="%s"' % (f_out.name)
        response = HttpResponse(f, 'application/force-download')
        response['Content-Disposition'] = 'attachment; filename="%s"' % (f.name)
        return response 
    except Exception as e:
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))


