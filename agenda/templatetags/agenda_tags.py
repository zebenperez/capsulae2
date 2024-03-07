from django import template
from django.utils import timezone

from account.models import Company
from agenda.models import Note

import os

register = template.Library()


'''
    Inclusion Tags
'''
@register.inclusion_tag('notes/note-list.html')
def get_note_list(user):
    end = timezone.now()
    ini = end.replace(hour=0, minute=0)
    end = end.replace(hour=23, minute=59)
    n_list = Note.objects.filter(employees__in=[user], ini_date__gte=ini, end_date__lte=end)
    return {'user': user, 'note_list': n_list, 'ini_date': ini, 'end_date': end}
 
