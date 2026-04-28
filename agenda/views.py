from django.http import HttpResponse
from django.shortcuts import render, redirect, reverse
from django.utils.translation import ugettext_lazy as _ 
from django.contrib.auth.models import User
from datetime import datetime, timedelta

from capsulae2.commons import get_or_none, show_exc, user_in_group
from capsulae2.decorators import group_required
from account.models import Company
from .common_lib import get_month_notes
from .models import Note, Status, NoteFile

import logging
logger = logging.getLogger(__name__)


'''
    Events
'''
def get_perms(user, groups):
    if "employee" in groups:
        return {"clone_notes": False, "create_notes": False, "remove_notes": False}
    elif "managers" in groups:
        return {"clone_notes": True, "create_notes": True, "remove_notes": True}
    elif "admins" in groups:
        return {"clone_notes": True, "create_notes": True, "remove_notes": True}
    else:
        return {"clone_notes": False, "create_notes": False, "remove_notes": False}

def get_note_context(user, year=None, month=None):
    groups = user.groups.all().values_list('name', flat=True)
    perms = get_perms(user, groups)
    today, s_list = get_month_notes(year,month,user) if "managers" in groups or "admins" in groups else get_month_notes(year,month,None,user)
    note_list = []
    for note in s_list:
        note_list += note.date_split()
    return {
        'note_list': note_list,
        'common_list': Note.objects.filter(common=True),
        'today': today, 
        'current_year': datetime.today().year, 
        'next_year': (datetime.today().year + 1),
        'perms': perms
    }

#def get_date(values):
#    if "date" in values and len(values["date"]) == 10:
#        return datetime.strptime(values["date"], "%Y-%m-%d")
#    if "date" in values and len(values["date"]) == 20:
#        return datetime.strptime(values["date"], "%Y-%m-%dT%H:%M:%SZ")
#    return datetime.now()

@group_required("admins","managers","employee")
def index(request):
    return render(request, "notes/index.html", get_note_context(request.user))

@group_required("admins","managers","employee")
def note_calendar(request):
    return render(request, "notes/note-calendar.html", get_note_context(request.user))

@group_required("admins","managers","employee")
def calendar(request):
    if "obj_id" in request.GET:
        note = get_or_none(Event, request.GET["obj_id"])
        year = str(note.ini_date.year) if note != None else None
        month = str(note.ini_date.month) if note != None else None
    else:
        year = request.GET["year"] if "year" in request.GET else None
        month = request.GET["month"] if "month" in request.GET else None
    return render(request, "notes/load-notes.html", get_note_context(request.user, year, month))

@group_required("admins","managers","employee")
def get_note(request, note_id=None):
    obj = None
    if note_id != None:
        obj = get_or_none(Note, note_id)
    elif "obj_id" in request.GET:
        obj = get_or_none(Note, request.GET["obj_id"])
    groups = request.user.groups.all().values_list('name', flat=True)
    perms = get_perms(request.user, groups)
    context = {'obj': obj, 'perms': perms, 'status_list': Status.objects.all()}
    template = "notes/note-details.html"

    if user_in_group(request.user, "managers") or user_in_group(request.user, "admins"):
        comp = Company.get_by_user(request.user)
        emp_list = []
        if obj == None:
            ini = datetime.now()
            end = ini + timedelta(hours=1)
            obj = Note.objects.create(ini_date=ini, end_date=end, user=request.user)
            context["obj"] = obj
        context["emp_list"] = comp.users.all()
        template = "notes/note-form.html"
    return render(request, template, context)

@group_required("admins","managers", "employee")
def update_dates(request):
    try:
        note = get_or_none(Note, request.GET["obj_id"])
        ini = datetime.strptime(request.GET["value"], '%Y-%m-%dT%H:%M')
        end = ini + timedelta(hours=1)
        note.ini_date = ini
        note.end_date = end
        note.save()
        return HttpResponse("")
    except Exception as e:
        return HttpResponse("Error: {}".format(e))

@group_required("admins","managers")
def create_note(request, note_id):
    try:
        note = get_or_none(Note, note_id)
        ini = datetime.now()
        end = ini + timedelta(hours=1)
        obj = Note.objects.create(name=note.name, desc=note.desc, ini_date=ini, end_date=end, user=request.user)

        comp = Company.get_by_user(request.user)
        employees = comp.users.all()
        for emp in employees:
            obj.employees.add(emp)
        return redirect("notes-index")
    except Exception as e:
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers","employee")
def add_employee(request):
    try:
        obj = get_or_none(Note, request.GET["obj_id"])
        user = User.objects.get(pk=request.GET["value"])
        if user in obj.employees.all():
            obj.employees.remove(user)
        else:
            obj.employees.add(user)
        return HttpResponse("")
    except Exception as e:
        print(e)
        return HttpResponse("Error!")

@group_required("admins","managers","employee")
def remove_note(request, note_id):
    try:
        obj = get_or_none(Note, note_id)
        year = str(obj.ini_date.year)
        month = str(obj.ini_date.month)
        obj.delete()
    except Exception as e:
        print(e)
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))
    return redirect("notes-index")

#@group_required("admins","managers","employee")
#def clone_notes(request):
#    try:
#        ini_year = request.POST["ini_year"]
#        end_year = request.POST["end_year"]
#        ini_notes = Event.objects.filter(ini_date__year = ini_year)
#        for ev in ini_notes:
#            i_date = ev.ini_date.replace(year=int(end_year))
#            e_date = ev.end_date.replace(year=int(end_year))
#            new_ev = Event.objects.create(ini_date=i_date, end_date=e_date, name=ev.name, desc=ev.desc)
#        return render(request, "notes/load-notes.html", get_note_context())
#    except Exception as e:
#        logger.error("[cam-clone_notes]" + str(e))
#        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers","employee")
def note_list(request):
    try:
        user = User.objects.get(pk=request.GET["obj_id"])
        ini = datetime.strptime(request.GET["ini"], "%Y-%m-%d")
        end = datetime.strptime(request.GET["end"], "%Y-%m-%d").replace(hour=23, minute=59)
        n_list = Note.objects.filter(employees__in=[user], ini_date__gte= ini, end_date__lte=end)
        context = {'user': user, 'note_list': n_list, 'ini_date': ini, 'end_date': end}
        return render(request, "notes/note-list-details.html", context)
    except Exception as e:
        logger.error("[journey_end]" + str(e))
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

'''
    FILES
'''
@group_required("admins","managers")
def file_list(request):
    try:
        obj = get_or_none(Note, request.GET["obj_id"])
        return render(request, "notes/note-files.html", {"obj": obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def file_add(request):
    try:
        obj_id = request.POST["obj_id"]
        file_list = request.FILES.getlist('file')

        obj = get_or_none(Note, obj_id)
        for f in file_list:
            obj_file = NoteFile(note=obj, note_file=f, name=f.name)
            obj_file.save()
        return render(request, "notes/note-files.html", {"obj": obj})
    except Exception as e:
        print(e)
        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers")
def file_form(request):
    try:
        obj = get_or_none(NoteFile, request.GET["obj_id"])  
        return render(request, "notes/file-form.html", {'obj': obj})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

@group_required("admins","managers")
def file_remove(request):
    try:
        obj = get_or_none(NoteFile, request.GET["obj_id"])
        if obj != None:
            note = obj.note
            obj.delete()
        return render(request, "notes/note-files.html", {"obj": note})
    except Exception as e:
        return render(request, 'error_exception.html', {'exc':show_exc(e)})

#@group_required("admins","managers")
#def file_get(request, obj_id):
#    try:
#        f = get_or_none(NoteFile, obj_id) 
#        response = HttpResponse(f.note_file, 'application/force-download')
#        response['Content-Disposition'] = 'attachment; filename="%s"' % (f.name)
#        return response 
#    except Exception as e:
#        return (render(request, "error_exception.html", {'exc':show_exc(e)}))

@group_required("admins","managers","employee")
def check_log(request):
    from django.conf import settings
    import os 

    f = open(os.path.join(settings.BASE_DIR, "logs.txt"), "r", encoding='utf-8')
    text = f.read()
    text_notes = "\n".join(x for x in text.splitlines() if "note" in x)
    return render(request, 'logs.html', {'text': text_notes.replace("\n", "<br/>")})


