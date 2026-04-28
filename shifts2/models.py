from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _ 

from datetime import datetime, timedelta


class CalendarShift():
    def __init__(self, pk, name, employee_list, ini_date, ini_time, end_date, end_time):
        self.pk = pk
        self.name = name
        self.employee_list = employee_list
        self.ini_date = ini_date
        self.end_date = end_date
        self.ini_time = ini_time
        self.end_time = end_time

class Shift(models.Model):
    ini_date = models.DateField('ini date', default=datetime.today)
    end_date = models.DateField('end date', default=datetime.today)
    ini_time = models.TimeField('ini hour', default=datetime.now)
    end_time = models.TimeField('end hour', default=datetime.now)
    name = models.CharField(max_length=600, verbose_name=_("Nombre"), default="", blank=True)
    desc = models.TextField(verbose_name=_("Descripción"), default="", blank=True)
    employees = models.ManyToManyField(User, verbose_name="Empleados", related_name="user_shifts", blank=True)
    user = models.ForeignKey(User, verbose_name=_("Usuario"), on_delete=models.CASCADE, blank=True, null=True, related_name="shifts")

    @property
    def employee_list(self):
        emp_list = [item.first_name for item in self.employees.all()]
        return "{}".format("|".join(emp_list))

    def date_split(self):
        diff = self.end_date - self.ini_date
        if diff.days == -1:
            return [CalendarShift(self.pk, self.name, self.employee_list, self.ini_date, self.ini_time, self.end_date, self.end_time)]

        shift_list = []
        ini_date = self.ini_date
        for d in range(diff.days + 1):
            date = ini_date + timedelta(d)
            cs = CalendarShift(self.pk, self.name, self.employee_list, date, self.ini_time, date, self.end_time)
            shift_list.append(cs)
        return shift_list

    class Meta:
        verbose_name = _("Turno")
        verbose_name_plural = _("Turnos")
        ordering = ["-ini_date"]

class Journey(models.Model):
    started = models.BooleanField(verbose_name=_('Cerrada'), default=False)
    ini_date = models.DateTimeField('ini date', default=datetime.now)
    end_date = models.DateTimeField('end date', default=datetime.now)
    user = models.ForeignKey(User, verbose_name=_("Usuario"), on_delete=models.CASCADE, blank=True, null=True, related_name="journeys")

    class Meta:
        verbose_name = _("Jornada laboral")
        verbose_name_plural = _("Jornadas laborales")
        ordering = ["-ini_date"]

