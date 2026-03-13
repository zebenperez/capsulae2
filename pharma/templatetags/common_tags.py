from django.utils.safestring import mark_safe
from django.urls import reverse
from django import template

from capsulae2.settings import BASE_DIR
from capsulae2.commons import show_exc, user_in_group
from account.models import UserMenu

from datetime import datetime, timedelta

import string, random

register = template.Library()

'''
    Filters
'''
@register.filter
def in_group(user, group):
    try:
        return user.groups.filter(name=group).exists()
    except:
        return False

@register.filter
def random_str(nchars='128'):
    try:
        n = int(nchars)
    except:
        n = 128
    return (''.join(random.choice(string.ascii_letters) for i in range(n)))

@register.filter
def have_menu(user, code):
    total = UserMenu.objects.filter(user=user, menus__code = code).count()
    return (total > 0)

#@register.filter
#def have_menu(user_project, menu):
#    up = user_project.split("|")
#    pu = ProjectUser.objects.filter(username=up[0], project_uuid=up[1]).first()
#    if pu == None:
#        return False
#    return menu in pu.menus

@register.filter
def addstr(arg1,arg2):
    return(mark_safe(str(arg1)+str(arg2)))

@register.filter
def sub_days(date, sub_days):
    try:
        d = date - timedelta(days=int(sub_days))
        return d
    except Exception as e :
        return None

@register.filter
def jsfloat(value):
    return str(value).replace(',','.')

@register.filter
def substr(text, pos):
    return(text[pos:])

'''
    Simple Tags
'''
@register.simple_tag
def userqr_code(request, paciente):
    import pyqrcode
    url = pyqrcode.create(paciente.n_historial)
    rpath = "/media/lopd_codebars/"
    filename = "%s.svg"%paciente.n_historial
    url.svg("%s%s%s"%(BASE_DIR, rpath, filename), scale=4)
    out="%s://%s/media/lopd_codebars/%s"%(request.scheme, request.get_host(), filename)
    return out

@register.simple_tag(takes_context=True)
def current_exact(context, url, **kwargs):
    request = context['request']
    reverseurl = reverse(url, kwargs=eval(str(kwargs)))
    if reverseurl == request.get_full_path() :
        return "active current"
    else:
        return ""

'''
    Inclusion Tags
'''
@register.inclusion_tag('main-menu.html')
def get_main_menu(user):
    groups = ["admins", "managers", "employee"]
    #if user.groups.filter(name="admins").exists() or user.groups.filter(name="managers").exists() or user.is_superuser:
    if user.groups.filter(name__in=groups).exists() or user.is_superuser:
        return {'user': user, 'menu': "admins"}
    return {}

    #try:
#        if user.groups.filter(name="guests").exists():
#            return {'user': user, 'menu': "guests"}
#        if user.groups.filter(name="categories").exists():
#            obj = CategoryUser.objects.filter(username=user.username).first()
#            if obj != None: 
#                return {'user': user, 'menu': "categories", 'view_cat': obj.view_cat}
#                return {'user': user, 'menu': "categories", "category": obj.category}
#        if user.groups.filter(name="projects").exists():
#            obj = ProjectUser.objects.filter(username=user.username).first()
#            if obj != None: 
#                return {'user': user, 'menu': "projects", "project": obj.project}
        #if user.groups.filter(name="admins").exists() or user.is_superuser:
        #    return {'user': user, 'menu': "admins"}
    #except:
    #    return {}

@register.inclusion_tag('web/second-menu.html')
def get_second_menu(user):
    try:
#        if user.groups.filter(name="guests").exists():
#            return {'user': user, 'menu': "guests"}
#        if user.groups.filter(name="projects").exists():
#            obj = ProjectUser.objects.filter(username=user.username).first()
#            if obj != None: 
#                return {'user': user, 'menu': "projects", "project": obj.project}
        if user.groups.filter(name="admins").exists() or user.is_superuser:
            return {'user': user, 'menu': "admins"}
    except Exception as e:
        return {}

