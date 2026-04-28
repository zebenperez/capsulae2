from pharma.common_lib import get_config_value, get_or_create_config_value, set_config_value
from capsulae2.commons import get_or_none
from .models import AtcsAempsCache, PrescriptionAempsCache, PresentationsPrescriptionsAempsCache, PrescriptionDocAempsCache
from datetime import datetime

import math
import requests
import time


AEMPS_URL = "https://www.aemps.gob.es/cima/rest/medicamentos"
DATE_FORMAT = "%d-%m-%Y %H:%M"

class AempsUpdateParams:
    is_running = "AEMPS_IS_RUNNING"
    total_pages = "AEMPS_TOTAL_PAGES"
    current_page = "AEMPS_CURRENT_PAGE"
    last_update = "AEMPS_LAST_UPDATE"

    def start(self):
        set_config_value(self.is_running, 1)

    def stop(self):
        set_config_value(self.is_running, 0)
        self.set_last_update(datetime.now().strftime(DATE_FORMAT))
   
    def get_is_running(self):
        return get_or_create_config_value(self.is_running)

    def get_last_update(self):
        return get_or_create_config_value(self.last_update)

    def set_last_update(self, date):
        set_config_value(self.last_update, date)

    def get_total_pages(self):
        return get_or_create_config_value(self.total_pages)

    def set_total_pages(self, total):
        set_config_value(self.total_pages, total)

    def get_current_page(self):
        return get_or_create_config_value(self.current_page)

    def set_current_page(self, current):
        set_config_value(self.current_page, current)


def set_prescription_cache(medicamento):
    nregistro = medicamento['nregistro']
    prescription_cache = get_or_none(PrescriptionAempsCache, nregistro, 'nregistro')
    if prescription_cache is None:
        prescription_cache = PrescriptionAempsCache()
        #medicamentos_creados += 1
    #else:
        #medicamentos_actualizados += 1
    prescription_cache.nregistro = nregistro
    prescription_cache.nombre = medicamento['nombre']
    prescription_cache.pactivos = medicamento['pactivos']
    prescription_cache.labtitular = medicamento['labtitular']
    prescription_cache.cpresc = medicamento['cpresc'] if "cpresc" in medicamento else ""
    prescription_cache.estado = list(medicamento['estado'])[0]
    prescription_cache.huerfano = medicamento['huerfano']
    prescription_cache.triangulo = medicamento['triangulo']
    prescription_cache.conduc = medicamento['conduc']
    prescription_cache.receta = medicamento['receta']
    prescription_cache.comerc = medicamento['comerc']
    prescription_cache.save()
    return prescription_cache

def set_atcs_cache(medicamento, prescription_cache):
    atcs_ls = medicamento['atcs']
    for atc in atcs_ls:
        codigo = atc['codigo']
        atc_cache = get_or_none(AtcsAempsCache, codigo, 'codigo')
        if atc_cache is None:
            atc_cache = AtcsAempsCache()
            atc_cache.codigo = codigo
            atc_cache.nivel = atc['nivel']
            atc_cache.nombre = atc['nombre']
            atc_cache.save()
        prescription_cache.atcs.add(atc_cache)
        prescription_cache.save()

def set_presentation_cache(medicamento, prescription_cache):
    presentations_ls = medicamento.get('presentaciones', [])
    for pres in presentations_ls:
        cn = pres['cn']
        pres_cache = get_or_none(PresentationsPrescriptionsAempsCache, cn, 'cn')
        if pres_cache is None:
            pres_cache = PresentationsPrescriptionsAempsCache()
        pres_cache.cn = cn
        pres_cache.nombre = pres['nombre']
        pres_cache.estado = list(pres['estado'])[0]
        pres_cache.comerc = pres['comerc']
        pres_cache.prescription = prescription_cache
        pres_cache.save()

def set_doc_cache(medicamento, prescription_cache):
    if "docs" in medicamento:
        for doc in medicamento["docs"]:
            doc_cache = []
            try:
                url = doc.get('url', None)
                if url :
                    doc_cache = PrescriptionDocAempsCache.objects.filter(tipo=doc['tipo'], url=url, prescription=prescription_cache)
            except Exception as e:
                print ("[ERROR prescriptionDoc] %s"%(str(e)))

            doc_cache = PrescriptionDocAempsCache() if len(doc_cache) < 1 else doc_cache[0]
            try:
                doc_cache.tipo = doc.get('tipo','')
                doc_cache.url = doc.get('url', '')
                doc_cache.urlHtml = doc.get('urlHtml',"")
                doc_cache.secc = doc.get('secc', '')
                doc_cache.prescription = prescription_cache
                doc_cache.save()
            except Exception as e2:
                print ("ERROR 2 %s"%str(e2))


def update_aemps_meds_cache ():
    aup = AempsUpdateParams()
    aup.start()
    start_time = time.time()

    params = {'cargaatc':'true', 'cargapresentaciones':'true', 'cargaprincipiosactivos':'true'} 
    response = requests.get(AEMPS_URL, params)
    json = response.json()
    try:
        final_number = int(json['totalFilas'])
        perPages = int(json['tamanioPagina'])
        pages =  int(math.ceil((final_number*1.)/perPages))
        aup.set_total_pages(str(pages))

        for pag in range(0, pages):
            aup.set_current_page(str(pag))

            if pag > 0 :
                params['pagina'] = ('%d' % (pag+1))

            response = requests.get(AEMPS_URL, params)
            json = response.json()
            medicamentos_lst = json['resultados']
            for medicamento in medicamentos_lst:
                prescription_cache = set_prescription_cache(medicamento)
                set_atcs_cache(medicamento, prescription_cache)
                set_presentation_cache(medicamento, prescription_cache)
                set_doc_cache(medicamento, prescription_cache)

    except Exception as e:
        print (str(e))
        #return 1

    print("--- %s seconds ---" % (time.time() - start_time))
    aup.stop()
    return 0

def update_tasks():
    #last_stage = get_or_create_config(LAST_UPDATE_STAGE, ST_FINISHED)
    #if last_stage.value == ST_FINISHED:
    update_aemps_meds_cache()
    #append_value(LAST_UPDATE_CONSOLE, "\n [%s] fase 1 / 2 finalizada , descansando ..."% (now_date_str()))
    #time.sleep(LONG_SLEEP_TIME_SC)  
    #update_aemps_meds_cache()       
    return 0

