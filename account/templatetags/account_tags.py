from django import template

from account.models import Profile, Plan

register = template.Library()

'''
    Inclusion Tags
'''
@register.inclusion_tag('login-profile-list.html')
def get_profile_select():
    profile_list = Profile.objects.filter(active=True)
    plan_list = Plan.objects.filter(active=True)
    return {'profile_list': profile_list, 'plan_list': plan_list}
 
