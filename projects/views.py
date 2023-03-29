from django.db.models import Q
from django.shortcuts import render, redirect, reverse

from capsulae2.decorators import group_required
from capsulae2.commons import get_or_none, get_param, show_exc
from .models import Activity, Project


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

@group_required("admins","managers")
def projects(request):
    return render(request, "projects/projects.html", {})

@group_required("admins","managers")
def project_list(request):
    return render(request, "projects/project-list.html", get_project_context(request.user))

@group_required("admins","managers")
def project_search(request):
    search_value = get_param(request.GET, "s-name")
    return render(request, "projects/project-list.html", get_project_context(request.user, search_value))

@group_required("admins","managers")
def project_new(request):
    obj = Project.objects.create(manager=request.user)
    #po, created = PatientOrigin.objects.get_or_create(patient=obj)
    return redirect(reverse('project-view', kwargs={'project_id': obj.id}))

@group_required("admins","managers")
def project_remove(request):
    obj = get_or_none(Project, request.GET["obj_id"]) if "obj_id" in request.GET else None
    if obj != None:
        obj.delete()
    return render(request, "projects/project-list.html", get_project_context(request.user))

'''
    Project
'''
@group_required("admins","managers")
def project_view(request, project_id):
    project = get_or_none(Project, project_id)
    return render(request, "project/project-view.html", {'obj': project})

@group_required("admins","managers")
def project_form(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/project-form.html", {'obj': project})

@group_required("admins","managers")
def project_activities(request):
    project = get_or_none(Project, get_param(request.GET, "obj_id"))
    return render(request, "project/activities/activity-list.html", {'obj': project})

'''
    Activities
'''
@group_required("admins","managers")
def project_activity_form(request):
    try:
        print("--a--")
        project = get_or_none(Project, get_param(request.GET, "project_id"))
        if project == None:
            return render(request, 'error_exception.html', {'exc':'Proyecto no encontrado!'})

        obj = get_or_none(Activity, request.GET["obj_id"]) if "obj_id" in request.GET else Activity.objects.create(project=project)

        print("--b--")
        return render(request, "project/activities/activity-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins",)
def project_activity_remove(request):
    try:
        obj = get_or_none(Activity, request.GET["obj_id"])
        project = obj.project
        obj.delete()
        return render(request, "project/activities/activity-list.html", {'obj': patient})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

