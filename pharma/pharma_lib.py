from django.db.models import Q
from datetime import date, datetime

from .treatment_models import Tratamiento
from .allergy_models import AlergiasExcipientes, AlergiasPrincipios
from .params_models import BloodPressure
from medication.models import Diagnosticos, CieCiap, InteraMedMed, InteraMedEnf

from medication.medication_lib import medicamentos_search_aemps

import re

# - AlergiasPrincipios - AlergiasExcipientes

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

def interamedmed(paciente):
    code_list = []
    result = []
    tratamientos = paciente.tratamientos.filter(activo=True)
    for tratamiento in tratamientos:
        medicamentos = tratamiento.medicamentos.all()
        for medicamento in medicamentos:
            if (medicamento.code not in code_list):
                code_list.append(medicamento.code)
    med_atcs = {}
    for code in code_list:
        params={'nregistro':code}
        list_med, error = medicamentos_search_aemps(params)
        med_atcs_01 = []
        if (len(list_med)>0):
            med = list_med[0]
            for atc in med['atcs']:
                if atc['codigo'] not in med_atcs_01:
                    med_atcs_01.append(atc['codigo'])
            med_atcs[med['name']] = med_atcs_01

    result = []
    list_keys = list(med_atcs.keys())
    for idx,key in enumerate(list_keys):
        for key_02 in list_keys[idx+1:]:
            interamedmeds = InteraMedMed.objects.filter(atc1__in = med_atcs[key], atc2__in = med_atcs[key_02]) or InteraMedMed.objects.filter(atc2__in = med_atcs[key], atc1__in = med_atcs[key_02])
            interamedmeds = interamedmeds.filter(deleted = False, validate_date__lte = datetime.now())
            if (len(interamedmeds) > 0):
                result.append([key, key_02, interamedmeds])

    return result

def get_values_to_summary_print(paciente, host):
    tratamientos = Tratamiento.objects.filter(paciente=paciente, fecha_fin__gte=date.today(), activo=True).order_by('medicamentos__atcs')
    registros = BloodPressure.objects.filter(patient = paciente)[:40]
    
    prin_in = AlergiasPrincipios.objects.filter(paciente = paciente)
    excp_in = AlergiasExcipientes.objects.filter(n_orden=paciente)

    counter = 0
    interacciones = {}

    context= {
        'tratamientos':tratamientos, 
        'paciente':paciente, 
        'interacciones':interacciones,
        'simple_report':True, 
        #'html_view': html_view,
        'url_base':host, 
        'alergies':list(excp_in) + list(prin_in), 
        'registros': registros, 
        #'request':request
    }

    return context

def get_values_to_interactions_print(paciente, comments, host):
    tratamientos = Tratamiento.objects.filter(paciente=paciente,fecha_fin__gte=date.today(), activo=True).order_by('medicamentos__atcs')
    registros = BloodPressure.objects.filter(patient=paciente)[:40]
    diagnosticos = Diagnosticos.objects.filter(n_orden=paciente.n_historial, borrado=False)
    oldman = CieCiap.objects.get(cie='1xxx') #1xxxx codigo de advertencia pacientes ancianos
    sec_warning = CieCiap.objects.get(cie='1xxxx')#1xxx codigo de advertencias de seguridad generales
    oldman = None
    sec_warning = None

    counter = 0         
    interacciones = {}
    medmed = {}
    secwar = {}
    list_cie = []
    list_ciap = []
    list_pato = []
    for diagnostico in diagnosticos:
        list_cie.append(diagnostico.cie_ciap.cie)
        list_ciap.append(diagnostico.cie_ciap.ciap)
        list_pato.append(diagnostico.cie_ciap.cie)
    
    if '1xxxx' not in list_cie:
        list_ciap.append('1xxxx')
        list_cie.append('1xxxx')
        list_pato.append(sec_warning)

    if (paciente.age >= 70):
        if '1xxx' not in list_cie:
            list_ciap.append('1xxx')
            list_cie.append('1xxx')
            list_pato.append(oldman)
    counter_medmed = 0
    medmed = interamedmed(paciente)

    tratamientos_duplicados = []
    for tratamiento in tratamientos:
        counter += 1
        list_interacc = []
        list_inter_med_med = []
        list_secwar = []
        medicamentos_in_trat =tratamiento.medicamentos.all()

        #FIXME : si el tratamiento pudiera tener mas de un farmaco, esto habria que cambiarlo
        duplicities = tratamiento.duplicity_warning
        if len(duplicities) > 0:
            tratamientos_duplicados.append({'med': medicamentos_in_trat[0], 'duplicities':  tratamiento.duplicity_warning})

        for medicamento in medicamentos_in_trat:
            list_aux = []
            #list_medmed = []
            aux_secwar = []
            params = {'nregistro':medicamento.code}
            list_med, error = medicamentos_search_aemps(params)
            for med in list_med:
                str_atc = '<strong>%s</strong> : ' % med['name']
                str_atc_med = '<strong>%s</strong> : ' % med['name']
                str_atc_secwar = '<strong>%s</strong> : ' % med['name']
                for atc in med['atcs']:
                    intermedenf = InteraMedEnf.objects.filter(atc = atc['codigo']).filter(Q(cie__in=list_cie)|Q(ciap__in=list_ciap)|Q(patologia__cie__in=list_cie)| Q(patologia__ciap__in=list_ciap)|Q(patologia__in=list_pato))
                    intermedenf = intermedenf.filter(deleted=False, validate_date__lte = datetime.now())
                    for interaccion in intermedenf:
                        mensaje = re.sub("[\\n]+", ". ", interaccion.mensaje_pato)
                        mensaje ="<br/>%s. %s" % (interaccion.patologia.nombre, mensaje)
                        mensaje ="%s.<br/><br/><div style='margin-left:20%%;font-size:0.8em;'><i>%s</i></div>" % (mensaje, interaccion.fuente)
                        if (interaccion.cie not in ['1xxx','1xxxx']):
                            if (mensaje not in list_aux):
                                list_aux.append(mensaje)
                        else:
                            if (mensaje not in aux_secwar):
                                aux_secwar.append(mensaje)

            if (len(list_aux) > 0):
                str_atc = "%s %s" % (str_atc, ''.join(list_aux))
                list_interacc.append(str_atc)
            if (len(aux_secwar) > 0):
                str_atc_secwar = "%s %s" % (str_atc_secwar, ''.join(aux_secwar))
                list_secwar.append(str_atc_secwar)

        if (len(list_interacc) > 0):
            interacciones['%d' % tratamiento.pk] = list_interacc
        if (len(list_secwar) > 0):
            secwar['%d' % tratamiento.pk] = list_secwar

    prin_in = AlergiasPrincipios.objects.filter(paciente = paciente)
    excp_in = AlergiasExcipientes.objects.filter(n_orden=paciente)

    context= {
        'tratamientos':tratamientos, 
        'paciente':paciente, 
        'interacciones':interacciones, 
        'url_base': host,
        'medmed': medmed, 
        'secwar':secwar, 
        'alergies': list(excp_in) + list(prin_in), 
        'comments':comments, 
        'diagnosticos':diagnosticos,
        'duplicities': tratamientos_duplicados, 
        #'html_view': html_view, 
        'registros': registros, 
        #'request':request
    }
    return context
