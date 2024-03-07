from django import template
from django.utils import timezone

from account.models import Company
from shifts2.models import Journey
from shifts2.common_lib import get_journeys_hours

import os

register = template.Library()


'''
    Filters
'''
@register.filter
def journey_started(user):
    return (Journey.objects.filter(user=user, started=True).count() > 0)

'''
    Simple Tags
'''
@register.simple_tag
def journey_hours(user, ini, end):
    return get_journeys_hours(user, ini, end)

'''
    Inclusion Tags
'''
@register.inclusion_tag('journeys/journey-list.html')
def get_journey_list(user):
    end = timezone.now()
    ini = end.replace(day=1, hour=0, minute=0)
    end = end.replace(hour=23, minute=59)
    j_list = Journey.objects.filter(user=user, ini_date__gte= ini, end_date__lte=end)
    return {'user': user, 'journey_list': j_list, 'ini_date': ini, 'end_date': end}
 
@register.inclusion_tag('journeys/journey-stats.html')
def get_journey_stats(user):
    end = timezone.now()
    ini = end.replace(day=1, hour=0, minute=0)
    end = end.replace(hour=23, minute=59)
    comp = Company.get_by_user(user)
    return {'user': user, 'user_list': comp.users.all(), 'ini_date': ini, 'end_date': end}
 
