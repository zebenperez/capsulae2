from django.db import models
from django.contrib.auth.models import User
from django.utils.translation import ugettext_lazy as _ 

from datetime import datetime, timedelta


class CalendarNote():
    def __init__(self, pk, name, employee_list, ini_date, end_date):
        self.pk = pk
        self.name = name
        self.employee_list = employee_list
        self.ini_date = ini_date
        self.end_date = end_date

class Status(models.Model):
    code = models.CharField(max_length=50, verbose_name=_("Código"), default="", blank=True)
    name = models.CharField(max_length=600, verbose_name=_("Nombre"), default="", blank=True)

    class Meta:
        verbose_name = _("Estado")
        verbose_name_plural = _("Estados")
        ordering = ["code"]

class Note(models.Model):
    common = models.BooleanField(verbose_name=_("Común"), default=False)
    ini_date = models.DateTimeField('ini date', default=datetime.now)
    end_date = models.DateTimeField('end date', default=datetime.now)
    name = models.CharField(max_length=600, verbose_name=_("Nombre"), default="", blank=True)
    desc = models.TextField(verbose_name=_("Descripción"), default="", blank=True)
    employees = models.ManyToManyField(User, verbose_name="Empleados", related_name="user_notes", blank=True)
    user = models.ForeignKey(User, verbose_name=_("Usuario"), on_delete=models.CASCADE, blank=True, null=True, related_name="notes")
    status = models.ForeignKey(Status, verbose_name=_("Estado"), on_delete=models.SET_NULL, blank=True, null=True)

    @property
    def employee_list(self):
        emp_list = [item.first_name for item in self.employees.all()]
        return "{}".format("|".join(emp_list))

    def date_split(self):
        diff = self.end_date - self.ini_date
        if diff.days == -1:
            return [CalendarNote(self.pk, self.name, self.employee_list, self.ini_date, self.end_date)]

        note_list = []
        ini_date = self.ini_date
        for d in range(diff.days + 1):
            date = ini_date + timedelta(d)
            cs = CalendarNote(self.pk, self.name, self.employee_list, date, date)
            note_list.append(cs)
        return note_list

    class Meta:
        verbose_name = _("Nota")
        verbose_name_plural = _("Notas")
        ordering = ["-ini_date"]

def upload_note_file(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "notes/files/%s" % (instance.id)
    return '/'.join(['%s' % (folder), datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class NoteFile(models.Model):
    name = models.CharField(max_length=255, verbose_name="Nombre", default="", blank=True)
    note_file = models.FileField(upload_to=upload_note_file, blank=True, verbose_name="Fichero", help_text="Select file to upload")
    note = models.ForeignKey(Note, verbose_name="Nota", on_delete=models.CASCADE, blank=True, null=True, related_name="files")

    class Meta:
        verbose_name = "Fichero"
        verbose_name_plural = "Ficheros"
        ordering = ["id"]

