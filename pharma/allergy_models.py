from django.db import models

from .models import Pacientes
from medication.models import AtcsAempsCache 


class Excipientesedo(models.Model):
    codigoedo = models.IntegerField(unique=True, verbose_name='Código')
    edo = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = 'EXCIPIENTESEDO'
        verbose_name = 'excipiente EDO'
        verbose_name_plural = 'excipientes EDO'

    def is_alergic(self, paciente):
        result = False
        try:
            result = (AlergiasExcipientes.objects.filter(n_orden=paciente.n_historial, edo=self).exists())
        except Exception as e:
            print ("ERROR in Excipientesedo :> %s" % e)
            pass

        return result

    def __str__(self):
        return (self.edo)

class PrincipiosActivos(models.Model):
    nroprincipioactivo = models.IntegerField(db_column='NROPRINCIPIOACTIVO', unique=True, primary_key=True, verbose_name='Número')
    codigoprincipioactivo = models.CharField(db_column='CODIGOPRINCIPIOACTIVO', unique=True, max_length=255, verbose_name='Código')
    principioactivo = models.CharField(db_column='PRINCIPIOACTIVO', unique=True, max_length=255, verbose_name='Nombre')

    def __str__ (self):
        return "%s" % self.principioactivo

    def is_alergic(self, paciente):
        result = False
        try:
            result = (AlergiasPrincipios.objects.filter(paciente=paciente, principio_activo=self).exists())
        except Exception as e:
            print ("ERROR: %s" % e)
            pass
        return result

    class Meta:
        managed = False
        db_table = 'PRINCIPIOS_ACTIVOS'
        verbose_name = 'Principio Activo'
        verbose_name_plural = 'Principios Activos'

class AlergiasExcipientes(models.Model):
    edo = models.ForeignKey(Excipientesedo, on_delete=models.SET_NULL, db_column='codigoedo', to_field='codigoedo', null=True)
    n_orden = models.ForeignKey(Pacientes, on_delete=models.CASCADE, to_field='n_historial', db_column='n_orden', related_name="alergias_excipientes")

    def __str__(self):
        return self.edo.edo

    class Meta:
        managed = False
        db_table = 'alergias_excipientes'
        verbose_name = 'alergia a excipiente'
        verbose_name_plural = 'alergias a excipientes'

class AlergiasPrincipios(models.Model):
    principio_activo = models.ForeignKey(PrincipiosActivos, on_delete=models.SET_NULL, null=True)
    paciente = models.ForeignKey(Pacientes, on_delete=models.CASCADE, null=True, related_name="alergias_principios")

    class Meta:
        # managed = False
        db_table = 'alergias_principios'
        verbose_name = 'alergia a principio'
        verbose_name_plural = 'alergias a principio'

    def __str__(self):
        return self.principio_activo.principioactivo

#class AlergiasLectura(models.Model):
#    cod = models.CharField(max_length=255, blank=True, null=True)
#    principio = models.CharField(max_length=255, blank=True, null=True)
#
#    class Meta:
#        managed = False
#        db_table = 'alergias_lectura'
#
#class AlergiasPacientes(models.Model):
#    n_orden = models.ForeignKey(Pacientes, on_delete=models.CASCADE, to_field='n_historial', null=True)
#    #codigoatc = models.ForeignKey(Atc, db_column='CODIGOATC', to_field='codigoatc', blank=True, null=True, help_text="No utilice este campo")
#    atc = models.ForeignKey(AtcsAempsCache, on_delete=models.SET_NULL, to_field='codigo', blank=True, null=True, verbose_name="Principio Activo", related_name="alergias")
#
#    class Meta:
#        # managed = False
#        db_table = 'alergias_pacientes'
#
