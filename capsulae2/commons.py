from django.apps import apps
from django.conf import settings
import sys
import datetime
import json
import string
import random
import unicodedata


'''
    Exceptions
'''
def show_exc(e):
    exc_type, exc_obj, exc_tb = sys.exc_info()
    return ("ERROR ===:> [%s in %s:%d]: %s" % (exc_type, exc_tb.tb_frame.f_code.co_filename, exc_tb.tb_lineno, str(e)))

'''
    Users
'''
def user_in_group(user, group):
    return user.groups.filter(name=group).exists()

'''
    Common
'''
def get_or_none(model, value, field="pk"):
    try:
        return model.objects.get(**{field: value})
    except Exception as e:
        return None

def get_or_none_str(app_name, model_name, value, field="pk"):
    try:
        model = apps.get_model(app_name, model_name)
        obj = model.objects.get(**{field: value})
        return obj
    except Exception as e:
        #logger.error("(get_object): %s" % e)
        return None

def set_obj_field(obj, field, value):
    obj_field = obj._meta.get_field(field)
    if obj_field.get_internal_type() == "ManyToManyField":
        getattr(obj, field).clear()
        for item in value:
            getattr(obj, field).add(get_or_none_str(obj._meta.app_label, obj_field.remote_field.model.__name__, item))
    elif obj_field.get_internal_type() == "ForeignKey":
        setattr(obj, field, get_or_none_str(obj._meta.app_label, obj_field.remote_field.model.__name__, value))
    elif obj_field.get_internal_type() == "FloatField":
        setattr(obj, field, value.replace(",", "."))
    elif obj_field.get_internal_type() == "DecimalField":
        setattr(obj, field, value.replace(",", "."))
    elif obj_field.get_internal_type() == "BooleanField":
        setattr(obj, field, (value == "True"))
    elif obj_field.get_internal_type() == "DateTimeField":
        if ":" in value:
            #val = datetime.datetime.strptime("{} {}".format(getattr(obj, field).strftime('%Y-%m-%d'), value), '%Y-%m-%d %H:%M')
            val = datetime.datetime.strptime(value, '%Y-%m-%dT%H:%M')
            setattr(obj, field, val)
        elif "-" in value:
            date = datetime.datetime.strptime(value, '%Y-%m-%d')
            if date >= datetime.datetime(1970,1,1):
                setattr(obj, field, date)
    else:
        setattr(obj, field, value)
    obj.save()

def get_param(dic, param, default=""):
    return dic[param] if param in dic and dic[param] != "" else default

def get_float(val):
    try:
        return float(val)
    except:
        return 0.0

def get_bool(val):
    try:
        return bool(val)
    except:
        return False

def get_int(val):
    try:
        return int(val)
    except:
        return 0

def set_session(request, key, default=""):
    request.session[key] = request.GET[key] if key in request.GET else default

def get_random_str(n):
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(n))

def validate_captcha(request):
    import urllib

    recaptcha_response = request.POST.get('g-recaptcha-response')
    url = 'https://www.google.com/recaptcha/api/siteverify'
    values = {
        'secret': settings.GOOGLE_RECAPTCHA_SECRET_KEY,
        'response': recaptcha_response
    }
    data = urllib.parse.urlencode(values).encode()
    req =  urllib.request.Request(url, data=data)
    response = urllib.request.urlopen(req)
    result = json.loads(response.read().decode())

    if result['success']:
        return True
    else:
        return False


