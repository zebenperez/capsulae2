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

    if user != None:
        kwargs["user"] = user

    if employee != None:
        kwargs["employees__in"] = [employee]

    note_list = Note.objects.filter(**kwargs)
    return today, note_list

