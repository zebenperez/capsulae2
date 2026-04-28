import os
from django.db import models

#local_imports
from pharma.models import Pacientes


class LOPDConsents(models.Model):
    date = models.DateTimeField(verbose_name="Fecha Creación", auto_now_add=True)
    document = models.FileField(upload_to="lopd_files", verbose_name="Documento firmado")
    paciente = models.ForeignKey(Pacientes, verbose_name="pacientes", on_delete=models.CASCADE, related_name="lopd")

    @property
    def filename(self):
        return os.path.basename(self.document.name)
	
    class Meta:
        ordering = ["-date"]


