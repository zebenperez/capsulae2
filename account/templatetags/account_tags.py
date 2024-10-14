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

@register.inclusion_tag('account/donation-plans.html')
def get_donation_select():
    profile = Profile.objects.filter(active=True, code="donation").first()
    plan_list = Plan.objects.filter(active=True, profile=profile)
    return {'plan_list': plan_list}
 
