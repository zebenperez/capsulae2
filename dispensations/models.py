from django.db import models
from datetime import datetime
from pharma.models import Pacientes


'''
    DISPENSATIONS
'''
class Dispensation(models.Model):
    date = models.DateTimeField(max_length=20, verbose_name="Fecha", default=datetime.min)
    code = models.CharField(max_length=50, verbose_name="Código de dispensación", default="")
    name = models.CharField(max_length=200, verbose_name="Denominación", default="")
    order = models.CharField(max_length=10, verbose_name="Orden", default="")
    units = models.CharField(max_length=10, verbose_name="Unidades", default="")
    pvp = models.CharField(max_length=10, verbose_name="PVP", default="")
    bill_pvp = models.CharField(max_length=10, verbose_name="PVP de facturación", default="")
    amount = models.CharField(max_length=10, verbose_name="Importe bruto", default="")
    ini_date = models.DateTimeField(max_length=20, verbose_name="Fecha de inicio de dispensación", default=datetime.min)
    end_date = models.DateTimeField(max_length=20, verbose_name="Fecha de fin de dispensación", default=datetime.min)
    next_date = models.DateTimeField(max_length=20, verbose_name="Fecha de próxima dispensación", default=datetime.min)
    num = models.CharField(max_length=10, verbose_name="Número de dispensación", default="")
    pre_code = models.CharField(max_length=50, verbose_name="Código de prescripción", default="")
    pre_name = models.CharField(max_length=200, verbose_name="Denominación de prescripción", default="")
    pre_pvp = models.CharField(max_length=10, verbose_name="PVP prescrito", default="")
    pre_bill_pvp = models.CharField(max_length=10, verbose_name="PVP de facturación prescrito", default="")
    pre_amount = models.CharField(max_length=10, verbose_name="Importe prescrito", default="")

    patient = models.ForeignKey(Pacientes, on_delete=models.CASCADE, verbose_name='Paciente', blank=True, null=True , related_name="dispensations")

    def __str__(self):
        return self.name

    def is_in_treatments(self):
        for item in self.patient.tratamientos.filter(activo=True):
            if item.cn == self.code:
                return True
        return False

    class Meta:
        db_table = 'dispensations_dispensation'
        verbose_name = 'Dispensación'
        verbose_name_plural = 'Dispensaciones'
        ordering = ['-date']

