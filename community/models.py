from django.db import models
from pharma.models import Pacientes
from account.models import Company
from django.contrib.auth.models import User
from datetime import datetime


class PatientFcoc(models.Model):
    creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True, null=True, blank=True)
    name = models.CharField(verbose_name="Nombre Fichero", max_length=100)
    fcoc_code = models.SlugField(verbose_name="Codigo", max_length=50)
    patient = models.ForeignKey(Pacientes, verbose_name="Paciente", related_name="patient_fcoc", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Paciente-Fcoc"
        verbose_name_plural = "Pacientes-Fcocs"

class PatientFci(models.Model):
    creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True, null=True, blank=True)
    remote_pk = models.IntegerField(verbose_name="Identificador FCI", unique=True)
    patient = models.ForeignKey(Pacientes, verbose_name="Paciente", related_name="patient_fci", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Paciente - FCI"
        verbose_name_plural = "Paciente - FCI"

class PatientActivity(models.Model):
    creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True, null=True, blank=True)
    remote_pk = models.IntegerField(verbose_name="Id Actividad")
    name = models.CharField(verbose_name="Nombre Actividad", max_length=150, blank=True, null=True)
    patient = models.ForeignKey(Pacientes, verbose_name="Paciente", related_name="patient_activities", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Actividad del Paciente"
        verbose_name_plural = "Actividades del paciente"

class Organization(models.Model):
    reviewed = models.BooleanField(verbose_name="Realizado", default=True)
    name = models.CharField(verbose_name="Nombre", max_length=600, blank=True, null=True, default="")
    year = models.CharField(verbose_name="Año de creación", max_length=600, blank=True, null=True, default="")
    #address = models.CharField(verbose_name="Dirección", max_length=900, blank=True, null=True, default="")
    email = models.CharField(verbose_name="Correo electrónico", max_length=1600, blank=True, null=True, default="")
    phone = models.CharField(verbose_name="Teléfono", max_length=600, blank=True, null=True, default="")
    contact = models.CharField(verbose_name="Persona de contacto", max_length=600, blank=True, null=True, default="")
    contact_resp = models.CharField(verbose_name="Cargo de la persona de contacto", max_length=600, blank=True, null=True, default="")
    in_charge = models.CharField(verbose_name="Persona responsable", max_length=600, blank=True, null=True, default="")
    in_charge_resp = models.CharField(verbose_name="Cargo de la persona responsable", max_length=600, blank=True, null=True, default="")
    derivation_way = models.CharField(verbose_name="Vía de derivación", max_length=900, blank=True, null=True, default="")
    derivation = models.TextField(verbose_name="Motivos de derivación", blank=True, null=True, default="")
    user = models.ForeignKey(User, verbose_name="Usuario", related_name="organizations", on_delete=models.SET_NULL, null=True)
    comp = models.ForeignKey(Company, verbose_name="Empresa", related_name="organizations", on_delete=models.SET_NULL, null=True)

    class Meta:
        verbose_name = "Organización"
        verbose_name_plural = "Organizaciones"
        ordering = ["name"]

class OrganizationAddress(models.Model):
    same_place = models.BooleanField(verbose_name="Mismo lugar", default=True)
    street_type = models.CharField(verbose_name="Tipo de vía", max_length=600, blank=True, null=True, default="")
    street_name = models.CharField(verbose_name="Nombre de vía", max_length=600, blank=True, null=True, default="")
    number = models.CharField(verbose_name="Número", max_length=600, blank=True, null=True, default="")
    door = models.CharField(verbose_name="Puerta", max_length=600, blank=True, null=True, default="")
    postal_code = models.CharField(verbose_name="Codigo postal", max_length=600, blank=True, null=True, default="")
    place = models.CharField(verbose_name="Barrio", max_length=600, blank=True, null=True, default="")
    place_other = models.CharField(verbose_name="Barrio", max_length=600, blank=True, null=True, default="")
    activity_place = models.TextField(verbose_name="Localización de actividad", blank=True, null=True, default="")
    org = models.OneToOneField(Organization, verbose_name="Organización", on_delete=models.CASCADE, related_name="address", blank=True, null=True)

    class Meta:
        verbose_name = "Dirección de la Organización"
        verbose_name_plural = "Dirección de las Organizaciones"

class OrganizationSocial(models.Model):
    facebook = models.CharField(verbose_name="Facebook", max_length=600, blank=True, null=True, default="")
    instagram = models.CharField(verbose_name="Instagram", max_length=600, blank=True, null=True, default="")
    twitter = models.CharField(verbose_name="Twitter", max_length=600, blank=True, null=True, default="")
    youtube = models.CharField(verbose_name="Youtube", max_length=600, blank=True, null=True, default="")
    org = models.OneToOneField(Organization, verbose_name="Organización", on_delete=models.CASCADE, related_name="social", blank=True, null=True)

    class Meta:
        verbose_name = "Redes social de la Organización"
        verbose_name_plural = "Redes sociales de las Organizaciones"


class OrganizationInfo(models.Model):
    ambit = models.TextField(verbose_name="Ámbito", blank=True, null=True, default="")
    activities = models.TextField(verbose_name="Actividades", blank=True, null=True, default="")
    participate = models.TextField(verbose_name="Participación", blank=True, null=True, default="")
    health = models.TextField(verbose_name="Salud", blank=True, null=True, default="")
    improvements = models.TextField(verbose_name="Mejoras", blank=True, null=True, default="")
    resources = models.TextField(verbose_name="Recursos", blank=True, null=True, default="")
    org = models.OneToOneField(Organization, verbose_name="Organización", on_delete=models.CASCADE, related_name="info", blank=True, null=True)

    class Meta:
        verbose_name = "Información de la Organización"
        verbose_name_plural = "Información de las Organizaciones"

class OrganizationResource(models.Model):
    free = models.BooleanField(verbose_name="Gratuito", default=True)
    owner = models.CharField(verbose_name="Titularidad del recurso", max_length=600, blank=True, null=True, default="")
    group = models.CharField(verbose_name="Grupo poblacional", max_length=1600, blank=True, null=True, default="")
    group_other = models.CharField(verbose_name="Grupo poblacional", max_length=1600, blank=True, null=True, default="")
    description = models.TextField(verbose_name="Descripción", blank=True, null=True, default="")
    org = models.OneToOneField(Organization, verbose_name="Organización", on_delete=models.CASCADE, related_name="resource", blank=True, null=True)

    class Meta:
        verbose_name = "Recurso de la Organización"
        verbose_name_plural = "Recursos de las Organizaciones"


class PatientOrg(models.Model):
    rol = models.CharField(verbose_name="Nombre", max_length=600, blank=True, null=True, default="")
    obs = models.TextField(verbose_name="Motivos de derivación", blank=True, null=True, default="")
    organization = models.ForeignKey(Organization, verbose_name="Organización", on_delete=models.CASCADE, null=True)
    patient = models.ForeignKey(Pacientes, verbose_name="Paciente", related_name="patient_organizations", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Paciente Organización"
        verbose_name_plural = "Pacientes Organizaciones"

class Procedure(models.Model):
    code = models.CharField(verbose_name="Código", max_length=50, blank=True, null=True, default="")
    name = models.CharField(verbose_name="Nombre", max_length=600, blank=True, null=True, default="")
    desc = models.TextField(verbose_name="Descripción", blank=True, null=True, default="")

    class Meta:
        verbose_name = "Trámite"
        verbose_name_plural = "Tramites"

class PatientProcedure(models.Model):
    date = models.DateField(verbose_name="Fecha", blank=True, null=True, default=datetime.today)                              
    done = models.BooleanField(verbose_name="Realizado", default=False)
    obs = models.TextField(verbose_name="Motivos de derivación", blank=True, null=True, default="")
    procedure = models.ForeignKey(Procedure, verbose_name="Trámite", on_delete=models.CASCADE, null=True)
    patient = models.ForeignKey(Pacientes, verbose_name="Paciente", related_name="procedures", on_delete=models.CASCADE, null=True)

    class Meta:
        verbose_name = "Paciente Tratamiento"
        verbose_name_plural = "Pacientes Tratamientos"


