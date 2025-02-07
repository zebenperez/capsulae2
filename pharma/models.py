from django.db import models
from django.contrib.auth.models import User
from django.template.defaultfilters import slugify

from medication.models import CieCiap 

from datetime import datetime, date
import random, string


class Config(models.Model):
    key = models.SlugField(max_length=200, verbose_name="clave", unique=True)
    value = models.CharField(max_length=400, verbose_name="valor")

    class Meta:
        verbose_name="Configuracion"
        verbose_name_plural = "Configuraciones"

    def __str__(self):
        db_table = 'pharma_config'
        verbose_name = "Config"
        verbose_name_plural = "Configs"
        return self.key

def get_historial():
    return ''.join(random.choice(string.ascii_uppercase + string.digits) for _ in range(8))

def upload_form_qr(instance, filename):
    ascii_filename = str(filename.encode('ascii', 'ignore'))
    instance.filename = ascii_filename
    folder = "patients/qr/%s" % (instance.id)
    return '/'.join(['%s' % (folder), datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])

class Pacientes(models.Model):
    n_orden = models.CharField(max_length=10)
    n_historial = models.CharField(max_length=8, unique=True, blank=True, null=True, verbose_name="Nº Hisotrial", default=get_historial)   # ***
    nif = models.CharField(max_length=12, blank=True, null=True, default="")                                        # ***
    fecha_nacimiento = models.DateField(blank=True, null=True, default=datetime.today)                              # ***
    cip = models.CharField(max_length=25, blank=True, null=True, verbose_name="CIP", default="")                    # ***
    nombre = models.CharField(max_length=255, blank=True, null=True, default="")                                    # ***
    apellido = models.CharField(max_length=255, blank=True, null=True, default="")                                  # ***
    sexo = models.CharField(max_length=1)                                                                           # ***
    borrado = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=datetime.now)
    updated_at = models.DateTimeField(default=datetime.now)

    cod_postal = models.IntegerField(verbose_name="Cod. postal", blank=True, null=True, default=0)                  # ***
    domicilio = models.CharField(max_length=100, blank=True, null=True, default="")                                 # ***
    slug_address = models.SlugField(max_length=200, verbose_name="Address slug", blank=True, null=True)
    telefono1 = models.IntegerField(blank=True, null=True, verbose_name="Teléfono")                                 # ***
    email = models.EmailField(blank=True, null=True, verbose_name="Correo electrónico", default="")                 # ***

    dieta = models.TextField(blank=True, null=True)
    black_race = models.BooleanField(verbose_name="Etnia Negra", default=False)
    facultativo = models.TextField(blank=True, null=True)
    alergias = models.TextField(blank=True, null=True)
    plan_cuidados = models.TextField(blank=True, null=True)
    observaciones = models.TextField(blank=True, null=True)
    me_prescriptor = models.CharField(max_length=200, blank=True, null=True)
    fotografia = models.CharField(max_length=255, blank=True, null=True, default="")
    nass = models.CharField(max_length=30, blank=True, null=True)
    cama = models.IntegerField(blank=True, null=True)
    habitacion = models.IntegerField(blank=True, null=True)
    tipo_paciente = models.CharField(max_length=100, blank=True, null=True)
    pastillero = models.CharField(max_length=20, blank=True, null=True)
    otras_alergias = models.TextField(blank=True, null=True)
    activo = models.NullBooleanField(blank=True, null=True)
    use_poli = models.CharField(max_length=10, blank=True, null=True, default="")
    qr = models.ImageField(upload_to=upload_form_qr, blank=True, verbose_name="QR", help_text="Select file to upload")

    id_user = models.ForeignKey(User, db_column='id_user', on_delete=models.SET_NULL, blank=True, null=True)  # owner

    @property
    def age(self):
        try:
            result = date.today() - self.fecha_nacimiento
            return int(result.days / 365.2425)
        except:
            return ""

    @property
    def owner(self):
        return self.id_user

    @property
    def owner_user(self):
        try:
            return User.objects.get(id=self.id_user)
        except:
            return None

    @property
    def full_name(self):
        try:
            fullname = ""
            if self.nombre and self.nombre != "none":
                fullname = ("%s %s" % (self.nombre, self.apellido)).replace("None", "").replace("none", "")
            #print(fullname)
            return fullname
        except Exception:
            return "--"

    @property
    def is_active(self):
        return False if self.activo == False else True

    @property
    def diagnoses(self):
        return Diagnosticos.objects.filter(n_orden=self.n_historial, borrado=False).order_by('fecha_ini', 'cie_ciap__nombre')

    def get_active_treatments(self):
        return self.tratamientos.filter(activo=True).count()

    def get_active_pillboxes(self):
        return self.pillboxes.filter(active=True).count()

    def __str__(self):
        return self.n_historial if self.n_historial != None else self.nombre
        # return self.__unicode__()

    def __unicode__(self):
        return "%s, %s" % (self.apellido, self.nombre)

    def slugify_address(string):
        return slugify(string).lower().replace(" ", "")

    def save(self, *args, **kwargs):
        self.slug_address = Pacientes.slugify_address(self.domicilio)
        super(Pacientes, self).save(*args, **kwargs)

    class Meta:
        db_table = 'pacientes'
        verbose_name = 'paciente'
        verbose_name_plural = 'pacientes'
        ordering = ["nombre"]

class Paises(models.Model):
    id_idioma = models.IntegerField()
    nombre = models.CharField(max_length=150)
    x = models.FloatField()
    y = models.FloatField()

    class Meta:
        db_table = 'paises'
        verbose_name = "país"
        verbose_name_plural = "países"

    def __str__(self):
        return self.nombre

class Etnia(models.Model):
    order = models.IntegerField(verbose_name="Orden", default=0)
    name = models.CharField(verbose_name="Nombre", max_length=300, default="")

    class Meta:
        verbose_name ="Raza / Etnia"
        verbose_name_plural ="Razas / Etnias"
        ordering = ['order']

class PatientOrigin(models.Model):
    nationality = models.CharField(verbose_name="Nacionalidad", max_length=300, default="")
    patient = models.OneToOneField(Pacientes, verbose_name="Paciente", on_delete=models.CASCADE, related_name="origin", blank=True, null=True)
    country = models.ForeignKey(Paises, verbose_name="Pais", on_delete=models.SET_NULL, blank=True, null=True)
    etnia = models.ForeignKey(Etnia, verbose_name="Raza / Etnia", on_delete=models.SET_NULL, blank=True, null=True)

    class Meta:
        verbose_name ="Origen"
        verbose_name_plural ="Origenes"

class Diagnosticos(models.Model):
    cie_ciap = models.ForeignKey(CieCiap, db_column='id_cie_ciap', on_delete=models.SET_NULL, null=True, related_name="diagnoses")
    n_orden = models.CharField(max_length=10) 
    fecha_ini = models.DateField(default = date.today())
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    borrado = models.BooleanField(default=False)
        
    class Meta:
        managed = False
        db_table = 'diagnosticos'
        verbose_name = 'diagnostico'
        verbose_name_plural = 'diagnosticos'

