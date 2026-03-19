from django.db import models
from datetime import date, datetime
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

def upload_evolutionary_file(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "patients/evolutionary/%s" % (instance.id)
    return '/'.join(['%s' % (folder), datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class EvolutionaryDoc(models.Model):
    obs = models.TextField(verbose_name="Descripción del fichero", blank=True, null=True, default="")
    doc = models.FileField(upload_to=upload_evolutionary_file, blank=True, verbose_name="Fichero", help_text="Select file to upload")
    evolutionary = models.ForeignKey(Evolutionary, verbose_name="Evolutivo", on_delete=models.CASCADE, null=True, related_name="docs")

    class Meta:
        verbose_name = "Documento de evolutivo"
        verbose_name_plural = "Documentos de evolutivo"


