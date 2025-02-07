from django import template
from capsulae2.commons import show_exc
import datetime

register = template.Library()

@register.filter
def verified(date_str):
    try:
        date = datetime.datetime.strptime(date_str[:10], '%d-%m-%Y')
        return (date.date() <= datetime.date.today())
    except Exception as e:
        print (show_exc(e))
        return False
