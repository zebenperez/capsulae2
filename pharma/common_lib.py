from .models import Config

PILLBOX_ADVISE = 7  # days

def get_config_value(key):
    try:
        config = Config.objects.get(key=key)
        return config.value
    except Exception as e:
        return ""

def get_or_create_config_value(key):
    try:
        config, created = Config.objects.get_or_create(key=key)
        return config.value
    except Exception as e:
        print(e)
        return ""

def set_config_value(key, value):
    config, created = Config.objects.get_or_create(key=key)
    config.value = value
    config.save()

