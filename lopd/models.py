import os
from django.db import models

#local_imports
from pharma.models import Pacientes
from account.models import Company


class LOPDConsents(models.Model):
    date = models.DateTimeField(verbose_name="Fecha Creación", auto_now_add=True)
    document = models.FileField(upload_to="lopd_files", verbose_name="Documento firmado")
    paciente = models.ForeignKey(Pacientes, verbose_name="pacientes", on_delete=models.CASCADE, related_name="lopd")
    company = models.ForeignKey(Company,verbose_name="empresa",on_delete=models.SET_NULL,related_name="lopd",null=True,blank=True)

    @property
    def filename(self):
        return os.path.basename(self.document.name)
	
    class Meta:
        ordering = ["-date"]


