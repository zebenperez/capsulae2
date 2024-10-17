from django.contrib.auth.models import User
from django.db import models

from datetime import date, datetime, timedelta


class Config(models.Model):
    key = models.CharField(max_length=200, verbose_name="clave")
    value = models.TextField(verbose_name="valor", blank=True)

    class Meta:
        verbose_name="Configuracion"
        verbose_name_plural = "Configuraciones"

    def __str__(self):
        return self.key

class UserActivate(models.Model):
    activate_key = models.CharField(max_length=255)
    activation_date = models.DateField(default = date.max)
    valid_date = models.DateField(default=date.today() + timedelta(days=7))
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    class Meta:
        db_table = 'pharma_useractivate'
        verbose_name = "Activación de usuarios"

class CompanyOptions(models.Model):
    code = models.SlugField(verbose_name="Codigo", max_length=50, unique="True")
    name = models.CharField(verbose_name="Nombre", max_length=150, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        db_table = 'companies_companyoptions'
        verbose_name="Opciones Empresa"
        verbose_name_plural="Opciones Empresa"

class Company(models.Model):
    image = models.ImageField(upload_to="images/", verbose_name=('Image'), null=True, blank=True)
    code = models.SlugField(verbose_name="CIF", max_length=200)
    name = models.CharField(verbose_name="Nombre", max_length=200)
    main_address = models.CharField(verbose_name="Dirección principal", max_length=200, default="", blank=True)
    town = models.CharField(verbose_name="Localidad", max_length=200, default="", blank=True)
    province = models.CharField(verbose_name="Provincia", max_length=200, default="", blank=True)
    phone = models.CharField(verbose_name="Teléfono", max_length=200, default="", blank=True)
    postal_code = models.CharField(verbose_name="Código Postal", max_length=12, default="", blank=True)
    email = models.EmailField(verbose_name="Correo electrónico", max_length=200, default="", blank=True)

    manager = models.OneToOneField(User, verbose_name="Manager", on_delete=models.SET_NULL, related_name="company", blank=True, null=True)
    users = models.ManyToManyField(User, verbose_name="Empleados", related_name="user_companies", blank=True)
    company_options = models.ManyToManyField(CompanyOptions, verbose_name="Opciones", related_name="options_company", blank=True)


    @staticmethod
    def get_by_user(user):
        comp = Company.objects.filter(manager = user).first()
        if comp != None:
            return comp
        return Company.objects.filter(users__in = [user]).first()

    class Meta:
        db_table = 'companies_company'
        verbose_name="Empresa"
        verbose_name_plural = "Empresas"

    def __str__(self):
        return "%s"%(self.name)

class EmployeeType(models.Model):
    code = models.SlugField(verbose_name="code", max_length=100)
    name = models.CharField(verbose_name="nombre", max_length=100)
    weight = models.IntegerField(verbose_name="Peso", default=0)
    alone = models.BooleanField(verbose_name="Puede estar solo", default=False)
    guards = models.BooleanField(verbose_name="Hace Guardias", default=False)

    def __str__(self):
        return "%s"%(self.code)

    class Meta:
        db_table = 'companies_employeetype'
        verbose_name="Tipo de perfil"
        verbose_name_plural ="Tipos de perfil"

class EmployeeProfile(models.Model):
    active = models.BooleanField(verbose_name="Activo", default=False)
    nights = models.BooleanField(verbose_name="Hace Noches", default=False)
    shifts = models.BooleanField(verbose_name="Usuario de turnos", default=False)
    hours_per_week = models.IntegerField(verbose_name="Horas Semana", null=True, blank=True, default=0)
    min_hours_per_shift = models.IntegerField(verbose_name="Minimo de Horas por turno", null= True, blank=True, default=1)#deprecated
    max_hours_per_shift = models.IntegerField(verbose_name="Máximo de horas por turno", null= True, blank=True, default=8)
    holiday_days = models.IntegerField(verbose_name="Dias Vacaciones", null=True, blank=True, default=30)
    pin = models.CharField(verbose_name="PIN", max_length=10, default=None, null=True, unique=True)

    user = models.OneToOneField(User, verbose_name="Usuario", on_delete=models.CASCADE, related_name="employee_profile")
    user_type = models.ForeignKey(EmployeeType, verbose_name="Tipo de usuario", on_delete=models.SET_NULL, related_name="usertype", null=True)

    def __str__(self):
        return "[%s] %s %s"%(self.user.username, self.user.first_name, self.user.last_name)

    @property
    def first_name(self):
        return self.user.first_name

    @property
    def last_name(self):
        return self.user.last_name

    @property
    def email(self):
        return self.user.email

    @property
    def name(self):
        return "%s %s"%(self.first_name, self.last_name)

    @property
    def username(self):
        return self.user.username

    @property
    def is_pharma(self):
        return (self.user_type.code == "pharma")

    @property
    def company(self):
        company = None
        try:
            company = Company.objects.filter(users = self.user).first()
        except Exception as e:
            print(str(e))
        return company

    class Meta:
        db_table = 'companies_employeeprofile'
        verbose_name="Perfil Empleado"
        verbose_name_plural ="Perfiles Empleados"


class Menu(models.Model):
    code = models.SlugField(verbose_name="Codigo", max_length=50, unique="True")
    name = models.CharField(verbose_name="Nombre", max_length=150, blank=True, null=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name="Menu"
        verbose_name_plural="Menus"
        ordering = ["code"]

class UserMenu(models.Model):
    menus = models.ManyToManyField(Menu, verbose_name="Menus", related_name="users", blank=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="menus")

    class Meta:
        verbose_name = "Menu de usuario"

class Profile(models.Model):
    active = models.BooleanField(verbose_name="Activo", default=False)
    amount = models.FloatField(verbose_name="Pago mensual", blank=True, default=0)
    code = models.CharField(verbose_name="Código", max_length=50, blank=True, null=True, default="")
    name = models.CharField(verbose_name="Nombre", max_length=150, blank=True, null=True, default="")
    desc = models.TextField(verbose_name="Descripción", blank=True, null=True, default="")
    menus = models.ManyToManyField(Menu, verbose_name="Menus", related_name="profiles", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Perfil"
        verbose_name_plural="Perfiles"

class Plan(models.Model):
    active = models.BooleanField(verbose_name="Activo", default=False)
    days = models.IntegerField(verbose_name="Días", blank=True, default=0)
    amount = models.FloatField(verbose_name="Cantidad", blank=True, default=0)
    name = models.CharField(verbose_name="Nombre", max_length=150, blank=True, null=True, default="")
    desc = models.TextField(verbose_name="Descripción", blank=True, null=True, default="")
    payment_link = models.CharField(verbose_name="Enlace de pago", max_length=250, blank=True, null=True, default="")
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE, related_name="plans")

    class Meta:
        verbose_name = "Plan"
        verbose_name_plural="Planes"

class UserProfile(models.Model):
    amount = models.FloatField(verbose_name="Pago mensual", blank=True, default=0)
    profile = models.ForeignKey(Profile, on_delete=models.SET_NULL, null=True, related_name="users")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="profiles")
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, related_name="profiles", null=True)

    class Meta:
        verbose_name = "Perfil de usuario"

class UserPayment(models.Model):
    confirm = models.BooleanField(verbose_name="Cancelado", default=False)
    cancel = models.BooleanField(verbose_name="Cancelado", default=False)
    amount = models.FloatField(verbose_name="Pago", blank=True, default=0)
    pay_date = models.DateField(verbose_name="Fecha de pago", default=datetime.now)
    expire_date = models.DateField(verbose_name="Fecha de expiración", default=datetime.now)
    code = models.CharField(verbose_name="Stripe code", max_length=250, blank=True, null=True, default="")
    desc = models.CharField(verbose_name="Descripción", max_length=250, blank=True, null=True, default="")
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="payments")

    class Meta:
        verbose_name = "Pago de usuario"
        verbose_name_plural="Pagos de usuarios"


