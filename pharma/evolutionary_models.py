from django.db import models
from datetime import date
from .models import Pacientes


# ---------------------------------------------------
#  Evolutionary
# ---------------------------------------------------
class Evolutionary(models.Model):
    date = models.DateField(verbose_name="Fecha", default = date.today())
    creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True)
    observations = models.CharField(verbose_name="Observaciones", max_length=2500, blank=True, null=True, default="")
    matter = models.CharField(verbose_name="Asunto", max_length=250, blank=True, null=True, default="")
    patient = models.ForeignKey(Pacientes, on_delete=models.CASCADE, related_name="evolutionary", verbose_name="Paciente")

    def __unicode__(self):
        return str(self.pk)

    def __str__(self):
        return "%s-%s"%(self.pk, self.date)

    class Meta:
        verbose_name="Evolutivo"
        verbose_name_plural="Evolutivos"
        ordering=['-date']

