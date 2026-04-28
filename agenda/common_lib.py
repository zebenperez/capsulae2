from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.files.base import ContentFile
from datetime import datetime
from .models import Note


'''
    NOTES 
'''
def get_month_notes(year=None, month=None, user=None, employee=None):
    today = datetime.today()
    if year != None and month != None:
        if len(year) == 2:
            year = "20%s" % year 
        today = datetime.strptime("%s %s %s" % (year, month, 1), "%Y %m %d")
    kwargs = {"ini_date__year": today.year, "ini_date__month": today.month}
    kwargs_prev = {"ini_date__year": today.year, "ini_date__month": today.month-1}
    kwargs_next = {"ini_date__year": today.year, "ini_date__month": today.month+1}

    if user != None:
        kwargs["user"] = user
        kwargs_prev["user"] = user
        kwargs_next["user"] = user

    if employee != None:
        kwargs["employees__in"] = [employee]
        kwargs_prev["employees__in"] = [employee]
        kwargs_next["employees__in"] = [employee]

    note_list = list(Note.objects.filter(**kwargs))+list(Note.objects.filter(**kwargs_prev))+list(Note.objects.filter(**kwargs_next))
    return today, note_list

