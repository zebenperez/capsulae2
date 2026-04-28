from .models import PresentationsPrescriptionsAempsCache


def get_cn_query(cn):
    query = {}
    if 'CAPSX' in cn:
        query['prescription__nregistro__icontains'] = cn
    else:
        if cn.isdigit() or ("|" in cn):
            if "|" in cn:
                cn = parse_qr(cn).get("cn", "")[1:]  # El codigo de barras incluido en el QR empieza por 0 y tiene 14 dititos en lugar de 13
            if len(cn) == 13:
                cn = cn[6:-1]
            query['cn'] = cn
    return query
 
def medicamentos_search_aemps(params, in_status=None, max_size=100000):
    error = None
    result = []
    medicamentos = []
    try:
        if 'cn' in params:
            query = get_cn_query(params['cn'])
            if len(query) > 0:
                medicamentos = PresentationsPrescriptionsAempsCache.objects.filter(**query)
        elif 'nregistro' in params:
            medicamentos = PresentationsPrescriptionsAempsCache.objects.filter(prescription__nregistro=params['nregistro'])
        else:
            queries = {}
            if 'nombre' in params:
                queries['nombre__icontains'] = params['nombre']
                queries['prescription__nombre__icontains'] = params['nombre']
            if 'atc' in params:
                queries['prescription__atcs__codigo__icontains'] = params['atc']
            medicamentos = PresentationsPrescriptionsAempsCache.objects.filter(**queries)
             
        medicamentos = medicamentos[:max_size]
        for med in medicamentos:
            item = med.toJSON()
            if in_status is None:
                result.append(item)
            elif med.prescription.estado in in_status:
                result.append(item)
    except Exception as e:
        print("ERROR EN medicamentos_search_aemps: %s" % show_exc(e))
        error = "%s" % e
    return result, error

def get_medication(search_value):
    medicamentos = []
    params_names = ['cn', 'nombre', 'nregistro', 'atc']
    try:
        for param in params_names:
            params = {param:search_value}
            medicamentos_aux, error  = medicamentos_search_aemps(params, in_status=None, max_size=100)
            medicamentos = medicamentos + medicamentos_aux
    except Exception as e:
        print ("ERR :"+str(e))
        error = "%s: %s. %s." % (_("Problemas al conectar con la base de datos de medicamentos: "), str(e), _("Inténtelo más tarde"))

    return medicamentos


