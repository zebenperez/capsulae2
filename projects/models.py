from django.db import models
from django.contrib.auth.models import User


class Project(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name", default="")
    desc = models.TextField(verbose_name="Descripción", default="")
    manager = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True) 

    def __str__(self):
        return self.name

    class Meta:
        verbose_name="Proyecto"
        verbose_name_plural = "Proyectos"

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


