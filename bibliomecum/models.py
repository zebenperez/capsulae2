from django.db import models
from pharma.models import Pacientes
from datetime import datetime


class BiblioReceipt(models.Model):
    date = models.DateTimeField(verbose_name="Fecha", auto_now_add=True, null=True, blank=True)
    #atc = models.CharField(verbose_name="ATC", max_length=100, blank=True, null=True, default="")
    #ciap = models.CharField(verbose_name="CIAP", max_length=100, blank=True, null=True, default="")
    advices = models.TextField(verbose_name="Consejos de uso", blank=True, null=True, default="")
    contras = models.TextField(verbose_name="Consejos de uso", blank=True, null=True, default="")
    patient = models.ForeignKey(Pacientes,verbose_name="Paciente", related_name="biblio_receipts", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Receta de libros"
        verbose_name_plural = "Recetas de libros"

class BiblioReceiptAtc(models.Model):
    atc = models.CharField(verbose_name="ATC", max_length=100, blank=True, null=True, default="")
    name = models.CharField(verbose_name="Nombre", max_length=100, blank=True, null=True, default="")
    receipt = models.ForeignKey(BiblioReceipt, verbose_name="Paciente", related_name="atcs", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "ATC"
        verbose_name_plural = "ATCs"

class BiblioReceiptCiap(models.Model):
    ciap = models.CharField(verbose_name="CIAP", max_length=100, blank=True, null=True, default="")
    name = models.CharField(verbose_name="Nombre", max_length=100, blank=True, null=True, default="")
    receipt = models.ForeignKey(BiblioReceipt, verbose_name="Paciente", related_name="ciaps", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "CIAP"
        verbose_name_plural = "CIAPs"

class BiblioReceiptBook(models.Model):
    isbn = models.CharField(verbose_name="ISBN", max_length=100, blank=True, null=True, default="")
    name = models.CharField(verbose_name="Nombre", max_length=100, blank=True, null=True, default="")
    receipt = models.ForeignKey(BiblioReceipt, verbose_name="Paciente", related_name="books", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Libro"
        verbose_name_plural = "Libros"

