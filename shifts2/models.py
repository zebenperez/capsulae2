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

    @property
    def employee_list(self):
        emp_list = [item.first_name for item in self.employees.all()]
        return "{}".format("|".join(emp_list))

    class Meta:
        verbose_name = _("Turno")
        verbose_name_plural = _("Turnos")
        ordering = ["-ini_date"]

class Journey(models.Model):
    started = models.BooleanField(verbose_name=_('Cerrada'), default=False)
    ini_date = models.DateTimeField('ini date', default=datetime.datetime.now)
    end_date = models.DateTimeField('end date', default=datetime.datetime.now)
    user = models.ForeignKey(User, verbose_name=_("Usuario"), on_delete=models.CASCADE, blank=True, null=True, related_name="journeys")

    class Meta:
        verbose_name = _("Jornada laboral")
        verbose_name_plural = _("Jornadas laborales")
        ordering = ["-ini_date"]

