from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _ 

import datetime


class Shift(models.Model):
    ini_date = models.DateField('ini date', default=datetime.datetime.today)
    end_date = models.DateField('end date', default=datetime.datetime.today)
    ini_time = models.TimeField('ini hour', default=datetime.datetime.now)
    end_time = models.TimeField('end hour', default=datetime.datetime.now)
    name = models.CharField(max_length=600, verbose_name=_("Nombre"), default="", blank=True)
    desc = models.TextField(verbose_name=_("Descripción"), default="", blank=True)
    employees = models.ManyToManyField(User, verbose_name="Empleados", related_name="user_shifts", blank=True)
    user = models.ForeignKey(User, verbose_name=_("Usuario"), on_delete=models.CASCADE, blank=True, null=True, related_name="shifts")

    class Meta:
        verbose_name = _("Turno")
        verbose_name_plural = _("Turnos")
        ordering = ["-ini_date"]

