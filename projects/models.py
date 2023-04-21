from django.db import models
from django.contrib.auth.models import User

import datetime


class Project(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name", default="")
    end_date = models.CharField(max_length=255, verbose_name="Fecha de ejecución", default="")
    desc = models.TextField(verbose_name="Descripción", default="")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True) 

    def __str__(self):
        return self.name

    class Meta:
        verbose_name="Proyecto"
        verbose_name_plural = "Proyectos"

class Text(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name", default="")
    desc = models.TextField(verbose_name="Descripción", default="")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name="texts")  

    def __str__(self):
        return self.name

    class Meta:
        verbose_name="Texto alternativo"
        verbose_name_plural = "Textos alternativos"

class Activity(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name", default="")
    desc = models.TextField(verbose_name="Descripción", default="")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name="activities")  

    def __str__(self):
        return self.name

    class Meta:
        verbose_name="Actividad"
        verbose_name_plural = "Actividades"

class Income(models.Model):
    desc = models.TextField(verbose_name="Descripción", default="")
    amount = models.TextField(verbose_name="Importe", default=0)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name="incomes")  

    def __str__(self):
        return self.name

    class Meta:
        verbose_name="Ingreso"
        verbose_name_plural = "Ingresos"

class Expense(models.Model):
    desc = models.TextField(verbose_name="Descripción", default="")
    amount = models.TextField(verbose_name="Importe", default=0)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name="expenses")  

    def __str__(self):
        return self.name

    class Meta:
        verbose_name="Gasto"
        verbose_name_plural = "Gastos"

class Folder(models.Model):
    read_only = models.BooleanField(verbose_name='Solo lectura', default=False)
    name = models.CharField(max_length=200, verbose_name="Nombre", default="", blank=True)
    parent = models.ForeignKey('self', verbose_name="Carpeta", on_delete=models.CASCADE, blank=True, null=True, related_name="childs")
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, blank=True, null=True, related_name="folders")

    class Meta:
        verbose_name = "Carpeta"
        verbose_name_plural = "Carpetas"
        ordering = ["-name"]

def upload_client_file(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "projects/files/%s" % (instance.id)
    if instance.folder != None:
        folder = "%s/%s" % (folder, instance.folder.id)
    return '/'.join(['%s' % (folder), datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class File(models.Model):
    moved = models.BooleanField(verbose_name='Movido', default=False)
    name = models.CharField(max_length=255, verbose_name="Nombre", default="", blank=True)
    proj_file = models.FileField(upload_to=upload_client_file, blank=True, verbose_name="Fichero", help_text="Select file to upload")
    folder = models.ForeignKey(Folder, verbose_name="Carpeta", on_delete=models.CASCADE, blank=True, null=True, related_name="files")
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, blank=True, null=True, related_name="files")

    class Meta:
        verbose_name = "Fichero"
        verbose_name_plural = "Ficheros"
        ordering = ["id"]


