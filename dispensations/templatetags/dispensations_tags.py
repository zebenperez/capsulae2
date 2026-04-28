from django import template
from medication.models import PresentationsPrescriptionsAempsCache as PPAC

import collections

register=template.Library()


@register.inclusion_tag('patient/dispensations/atc_menu.html')
def atc_menu(dispensations):
    atc_list =  {}
    for d in dispensations:
        try:
            obj = PPAC.objects.filter(cn = int(d.code)).first()
        except:
            obj = None
        if obj != None:
            for atc in obj.prescription.atcs.all():
                if len(atc.codigo) == 7:
                    if atc.nombre not in atc_list.keys():
                        atc_list[atc.nombre] = [d.code]
                    else:
                        atc_list[atc.nombre].append(d.code)
    atc_list = collections.OrderedDict(sorted(atc_list.items()))
    return {'atc_list': atc_list}

