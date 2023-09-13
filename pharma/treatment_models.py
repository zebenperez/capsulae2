from django.db import models
from django.utils.translation import ugettext as _
from datetime import datetime

from .models import Pacientes


class Viasadministracion(models.Model):
    cod_nacion = models.IntegerField()
    cod_via_admin = models.IntegerField()
    description = models.CharField(max_length=255, blank=True, null=True)
    visible = models.BooleanField(default = False)

    def __str__(self):
        return "%s" % self.description

    class Meta:
        db_table = 'VIASADMINISTRACION'
        verbose_name = 'vía de administración'
        verbose_name_plural = 'vías de administración'

class Tratamiento(models.Model):
    m = models.FloatField(verbose_name='mañana', blank=True, null=True, default=0)
    t = models.FloatField(verbose_name='tarde', blank=True, null=True, default=0)
    n = models.FloatField(verbose_name='noche', blank=True, null=True, default=0)
    o = models.FloatField(verbose_name='otros', blank=True, null=True, default=0)
    fecha_inicio = models.DateField(verbose_name='Fecha Inicio', default=datetime.now)
    fecha_fin = models.DateField(default=datetime.max)
    observaciones = models.CharField(verbose_name=_('Observaciones'), max_length = 200, blank=True, null=True, default="")
    activo = models.NullBooleanField(blank=True, null=True, default=True)

    #principio = models.ForeignKey(PrincipiosActivos, null=True, blank=True)
    #edo = models.ForeignKey(Excipientesedo, db_column='codigoedo', to_field='codigoedo', null=True, blank=True)
    via = models.ForeignKey(Viasadministracion, on_delete=models.SET_NULL, blank=True, null=True)
    paciente = models.ForeignKey(Pacientes, on_delete=models.CASCADE, null=True, related_name='tratamientos')

    #DEPRECATED
    codigo = models.CharField(max_length=7, blank=True, null=True, default="")
    cod_localizacion = models.CharField(max_length=1, blank=True, null=True, default="")

    def __str__(self):
        return "%s - %s"%(self.pk, self.paciente)

    @property
    def name(self):
        try:
            return self.medicamentos.all().first().name
        except Exception as e:
            #print ("[Tratamiento name property error] %s"%str(e))
            try:
                return self.complementos.all().first().name
            except Exception as e:
                return "--"

    @property
    def reg_code(self):
        try:
            return self.medicamentos.all().first().code
        except Exception:
            return "--"

    @property
    def cn(self):
        try:
            return self.medicamentos.all().first().cn
        except Exception:
            return "--"
    @property
    def atcs(self):
        try:
            return self.medicamentos.all().first().atcs
        except Exception as e:
            print ("[Tratamiento name property error] %s"%str(e))
        return "--"

    @property
    def atcs_last(self):
        try:
            atcs = self.medicamentos.all().first().atcs.split(",")
            return atcs[len(atcs)-1]
        except Exception as e:
            print ("[Tratamiento name property error] %s"%str(e))
        return "--"


#    @property
#    def edo_alergic(self):
#        if (self.edo is not None):
#            return (self.edo.is_alergic(self.paciente))
#        else:
#            return False

#    @property
#    def principio_alergic(self):
#        if (self.principio is not None):
#            return (self.principio.is_alergic(self.paciente))
#        else:
#            return False

    @property
    def med_alergic(self):
        for med in self.medicamentos.all():
            if (med.is_alergic):
                return True
        return False

    @property
    def not_finish(self):
        return (self.fecha_fin == date.max)

    @property
    def duplicity_warning(self):
        if not self.activo :
            return []

        treatments = self.paciente.tratamientos.filter(activo=True).exclude(pk = self.pk)
        self_atcs = []
        duplicities = []
        for meds in self.medicamentos.all():
            self_atcs.append(meds.get_level_5_atc)
        for item in treatments:
            item_meds = item.medicamentos.all()
            for imeds in item_meds:
                item_atcs = imeds.get_level_5_atc
                for code in item_atcs:
                    for atc in self_atcs :
                        for c in  atc:
                            if code == c:
                                duplicities.append(imeds.name+" - "+code)
        return duplicities

    @property
    def in_pillbox(self):
        try:
#            pillboxes = PillboxTreatment.objects.filter(treatment=self, pillbox__active = True)
            pillboxes = self.pillbox_treatments.filter(pillbox__active = True)
            for pillbox in pillboxes:
                if pillbox.include_in_spd:
                    return True
        except:
            return False
        return False

    def is_complement(self):
        return (self.complementos.all().count() > 0)

    class Meta:
        db_table = 'tratamiento'
        verbose_name = 'tratamiento'
        verbose_name_plural = 'tratamientos'
        ordering = ['medicamentos__atcs','-fecha_inicio']

class MedicamentoTratamiento(models.Model):
    name = models.CharField(max_length=350)
    cn = models.CharField(max_length=10, default="") # código nacional
    code = models.CharField(max_length=10) # numero de registro
    principles = models.TextField(default='')
    atcs = models.TextField(default="")

    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.CASCADE, null=True, related_name='medicamentos')

    @property
    def get_level_5_atc(self):
        atcs = []
        for code in self.atcs.split(","):
            if len(code) > 5:
                atcs.append(code[:5])
        return atcs

#    @property
#    def is_alergic(self):
#        paciente = self.tratamiento.paciente
#        result = False
#        try:
#            principles_list = self.principles.split(',')
#            for principle in principles_list:
#                principio_list = PrincipiosActivos.objects.filter(principioactivo=principle)
#                for principio in principio_list:
#                    result = (AlergiasPrincipios.objects.filter(paciente=paciente, principio_activo=principio).exists())
#                    if result:
#                        break
#                if result:
#                    break
#        except Exception as e:
#            print ("ERROR: %s" % e)
#            pass
#        return result
#

class ComplementoTratamiento(models.Model):
    name = models.CharField(max_length=350)
    code = models.CharField(max_length=10)
    principles = models.TextField(default='')

    tratamiento = models.ForeignKey(Tratamiento, on_delete=models.CASCADE, null=True, related_name='complementos')

