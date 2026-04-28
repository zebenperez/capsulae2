from django.conf import settings
from django.contrib.auth.models import User, Group
from django.core.files.base import ContentFile
from datetime import datetime
from .models import Shift, Journey


'''
    Shifts
'''
def get_month_shifts(year=None, month=None, user=None, employee=None):
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

    shift_list = Shift.objects.filter(**kwargs)
    return today, shift_list

def get_journeys_hours(user, ini_date, end_date):
    j_list = Journey.objects.filter(user=user, ini_date__gte = ini_date, end_date__lte = end_date)
    hours = 0
    for shift in j_list:
        diff = shift.end_date - shift.ini_date
        seconds = diff.total_seconds()
        hours += divmod(seconds, 3600)[0]
    return hours

