from .models import Config

PILLBOX_ADVISE = 7  # days
LOPD_LIMIT = 15  # days

def get_config_value(key, default=""):
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

def parse_qr(qr_data):
    values = {}
    BAR_CODE = "01"
    BATCH_CODE = "10"
    EXPIRATION_DATE = "17"
    SN = "21"
    qr_blocks = qr_data.splitlines() if qr_data.find("|") == -1 else qr_data.split("|") #separa la cadena segun el caracter 'group-separator' <GS> o por una linea vertical
    for block in qr_blocks:
        blocksize = len(block)
        ptr = 0 if  blocksize > 3 else None
        while ptr != None and ptr < blocksize:
            key = block[ptr:ptr+2]
            ptr += 2
            if key == BAR_CODE:
                values['cn'] = block[ptr:ptr+14] #posicion del puntero mas 14+1 digitos(el codigo de barras tiene longitud 14)
                ptr=ptr+14
            if key == EXPIRATION_DATE:
                values['expiration_date'] = block[ptr:ptr+6] #la fecha tiene longitud 6 por lo que sumamos 6+1
                ptr=ptr+6
            if key == BATCH_CODE:
                values['batch_code']= block[ptr:] #batch code no tiene longitud definido por lo que finalizara con la cadena
                ptr=None
            if key == SN :
                values['sn'] = block[ptr:] # Serial number no tienen longitud predefinida por lo que finalizara con la cadena
                ptr=None
    return values

