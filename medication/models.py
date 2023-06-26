from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import datetime, date


PRESCRIPTION_STATUS = {'aut': 'Autorizado', 'susp': 'Suspendido', 'rev': 'Revocado'}


class Atc(models.Model):
    codigoatc = models.CharField(db_column='CODIGOATC', max_length=64, verbose_name='código', unique=True)  #  Field name made lowercase.
    descatc = models.CharField(db_column='DESCATC', max_length=255, blank=True, null=True, verbose_name='descripción')  #  Field name made lowercase.

    class Meta:
        db_table = 'ATC'
        verbose_name = 'ATC'
        verbose_name_plural = 'ATC\'s'

    def __str__(self):
        return ("%s" % self.descatc)

class AtcsAempsCache(models.Model):
    codigo = models.CharField(verbose_name="Codigo", max_length=20, unique=True)
    nombre = models.CharField(verbose_name="Nombre", max_length=300)
    nivel = models.IntegerField(verbose_name="Nivel")
        
    def __str__(self):
        return ("%s - %s" % (self.codigo, self.nombre))
    
    def toJSON(self):
        obj = {'codigo': self.codigo, 'nombre': self.nombre, 'nivel': self.nivel}
        return obj

    class Meta:
        db_table = 'pharma_atcsaempscache'
        verbose_name = "AEMPS cache ATC"
        verbose_name_plural = "AEMPS cache ATCS"
        ordering = ['codigo', 'nivel', 'nombre']


class PrescriptionAempsCache(models.Model):
    comerc = models.BooleanField(verbose_name="Comercializado", default=False)
    receta = models.BooleanField(verbose_name="Receta", default=False)
    conduc = models.BooleanField(verbose_name="Conducción", default=False)
    triangulo = models.BooleanField(verbose_name="triangulo", default=False)
    huerfano = models.BooleanField(verbose_name="huerfano", default=False)
    nregistro = models.CharField(verbose_name="Registro", max_length=50, unique=True)
    nombre = models.CharField(verbose_name="Nombre", max_length=400)
    labtitular = models.CharField(verbose_name="Laboratorio", max_length=200)
    cpresc = models.CharField(verbose_name="Codigo prescripcion", max_length=300)
    estado = models.CharField(verbose_name="Estado", max_length=20)
    pactivos = models.TextField(verbose_name="Principios Activos")

    atcs = models.ManyToManyField(AtcsAempsCache, verbose_name="Atcs cache", related_name="prescriptions")

    def __str__(self):
        return "%s - %s" % (self.nregistro, self.nombre)

    def get_atcs_csv(self):
        atcs_qs = self.atcs.all()
        atcs = ""
        for item in atcs_qs:
            atcs += "%s " % (item.codigo)

        atcs = atc.strip().replace(" ",",")
        return atcs

    class Meta:
        db_table = 'pharma_prescriptionaempscache'
        verbose_name="AEMPS Cache Prescripciones"
        verbose_name_plural ="AEMPS cache Prescripciones"

class PresentationsPrescriptionsAempsCache(models.Model):
    cn = models.IntegerField(unique=True, verbose_name="Codigo nacional")
    nombre = models.CharField(verbose_name="Nombre", max_length=400)
    estado = models.CharField(verbose_name="Estado", max_length=20)
    comerc = models.BooleanField(verbose_name="comerc", default=False)
    prescription = models.ForeignKey(PrescriptionAempsCache, on_delete=models.CASCADE, verbose_name="Prescription Cache", related_name="presentations")

    def __str__(self):
        return "[%s] - %s"%(self.cn, self.nombre)

    def toJSON(self):
        atcs_qs = self.prescription.atcs.all()
        atcs_ls = []
        family = ""
        atc = ""
        for item in atcs_qs:
            if item.nivel == 5:
                atc = item.codigo
            if item.nivel == 4:
                family = item.nombre

            atcs_ls.append(item.toJSON())

        docs_qs = self.prescription.docs.all()
        ft = ""
        prospect =""

        for doc in docs_qs:
            if doc.tipo == 1:
                ft = doc.url
            if doc.tipo == 2:
                prospect = doc.url

        obj = {'id': self.id, 'name':self.nombre, 'principles': self.prescription.pactivos, 'labs': self.prescription.labtitular, 'cn': self.cn,
                'status': PRESCRIPTION_STATUS[self.prescription.estado], 'pres_conditions':'', 'market_state':'', 'code':self.prescription.nregistro ,
                'atcs':atcs_ls, 'ft': ft, 'prospect': prospect, 'family': family, 'cod_atc': atc }

        return obj

    class Meta:
        db_table = 'pharma_presentationsprescriptionsaempscache'
        verbose_name = "AEMPS cache presentacion prescripcion"
        verbose_name_plural = "AEMPS cache presentaciones prescripciones"

class PrescriptionDocAempsCache(models.Model):
    secc = models.BooleanField(verbose_name="secc")
    tipo = models.IntegerField(verbose_name="Tipo")
    url = models.CharField(verbose_name="Url", max_length=300)
    urlHtml = models.CharField(verbose_name="UrlHtml", max_length=300)
    prescription = models.ForeignKey(PrescriptionAempsCache, on_delete=models.CASCADE, verbose_name="Prescription Cache", related_name="docs")

    class Meta:
        db_table = 'pharma_prescriptiondocaempscache'
        verbose_name ="AEMPS cache Docs prescription"
        verbose_name_plural ="AEMPS cache Docs prescription"

class FichaPrincipioActivo(models.Model):
    cod_atc = models.CharField(max_length=20)
    efecto_secundario = models.TextField(verbose_name="Efectos secundario", blank=True, default="", null=True)
    consejos = models.TextField(verbose_name="Consejos", blank=True)
    validate_date = models.DateTimeField(verbose_name="Fecha de validación", default=datetime.max , blank=True)
    deleted = models.BooleanField(verbose_name="Borrado", default=False)

    class Meta:
        managed = True
        db_table = 'ficha_principio_activo'
        verbose_name = 'Ficha de Princio Activo'
        verbose_name_plural = 'Fichas de Principio Activo'

    def __str__(self):
        return "%s" % self.cod_atc

    @property
    def get_pactivos(self):
        try:
            prescriptions = Prescription.objects.filter(cod_atc=self.cod_atc)
            for item in prescriptions:
                if item.pactivo != None and len(item.pactivo) > 2:
                    return item.pactivo
            return ""
        except Exception as e:
            print (str(e))
            return ""

    @property
    def is_validated(self):
        try:
            return self.validate_date <= timezone.now()
        except Exception:
            return self.validate_date <= datetime.now()

    def save(self, *args, **kwargs):
        self.consejos = self.consejos.upper()
        try:
            is_validated = False
            try:
                is_validated = self.validate_date <= datetime.now()
            except Exception:
                is_validated = self.validate_date <= timezone.now()
            if is_validated:
                 FichaPrincipioActivo.objects.filter(cod_atc=self.cod_atc).exclude(pk=self.pk).update(validate_date=datetime.max)
        except Exception as e:
            print (str(e))
        super(FichaPrincipioActivo, self).save(*args, **kwargs)

class CieCiap(models.Model):
    nombre = models.CharField(max_length=255, unique=True)
    cie = models.CharField(max_length=255, blank=True, null=True)
    ciap = models.CharField(max_length=255, blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'cie_ciap'
        verbose_name = 'CIE&CIAP'
        verbose_name_plural = 'CIE\'s&CIAP\'s'

    def __str__(self):
        return ("%s [CIE : %s] [CIAP : %s]" % (self.nombre, self.cie, self.ciap))

class Diagnosticos(models.Model):
    cie_ciap = models.ForeignKey(CieCiap, on_delete=models.SET_NULL, db_column='id_cie_ciap', null=True)
    n_orden = models.CharField(max_length=10)
    fecha_ini = models.DateField(default = date.today())
    observaciones = models.CharField(max_length=255, blank=True, null=True)
    borrado = models.BooleanField(default=False)

    class Meta:
        managed = False
        db_table = 'diagnosticos'
        verbose_name = 'diagnostico'
        verbose_name_plural = 'diagnosticos' 

class InteraMedEnf(models.Model):
    deleted = models.BooleanField(verbose_name='Borrado', default=False)
    excluye_incluye = models.BooleanField()
    and_or = models.BooleanField()
    condicion = models.IntegerField(db_column='CONDICION', blank=True, null=True, verbose_name='Edad')  
    deleted_date = models.DateTimeField(default=date.max, verbose_name='Fecha de borrado', blank=True)
    validate_date = models.DateField(default=date.max, verbose_name='Fecha de validación', blank=True)
    cie = models.CharField(db_column='CIE', max_length=255, blank=True, null=True)
    ciap = models.CharField(db_column='CIAP', max_length=255, blank=True, null=True)  
    fuente = models.CharField(db_column='FUENTE', max_length=255, blank=False, null=True, verbose_name="Fuente")
    mensaje_pato = models.TextField(db_column='MENSAJE_PATO', max_length=990, blank=True, null=True, verbose_name = 'Advertencia')

    atc = models.ForeignKey('AtcsAempsCache',to_field="codigo",on_delete=models.SET_NULL,blank=True,null=True,verbose_name="Principio Activo",related_name="intera_med_enf")
    patologia = models.ForeignKey(CieCiap,to_field='nombre',db_column='PATOLOGIA', on_delete=models.SET_NULL, max_length=255, blank=False, null=True, verbose_name="Patología")
    codprincipi = models.ForeignKey(Atc,to_field='codigoatc',db_column='CODPRINCIPI', on_delete=models.SET_NULL, max_length=255, blank=True, null=True, verbose_name="Old P.A.", help_text="No utilice este campo , en su lugar utilice Principio Activo")  #  DEPRECATED
    deleted_user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='+')
    validate_user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='med_enf_validations')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    @property
    def is_validated(self):
        return (self.validate_date <= date.today())

    class Meta:
        managed = True
        db_table = 'intera_med_enf'
        verbose_name = 'Interacción medicamento-enfermedad'
        verbose_name_plural = 'Interacciones medicamento-enfermedad'

class InteraMedMed(models.Model):
    deleted = models.BooleanField(verbose_name='Borrado', default=False)
    validate_date = models.DateField(default=date.max, verbose_name='Fecha de validación', blank=True)
    deleted_date = models.DateTimeField(default=date.max, verbose_name='Fecha de borrado', blank=True)
    principio_1 = models.CharField(db_column='PRINCIPIO_1', max_length=255, blank=True, null=True)  #  DEPRECAETD Field name made lowercase.
    principio_2 = models.CharField(db_column='PRINCIPIO_2', max_length=255, blank=True, null=True)  #  DEPRECATED Field name made lowercase.
    nombre = models.CharField(db_column='NOMBRE', max_length=255, blank=True, null=True)  
    intsig = models.CharField(db_column='INTSIG', max_length=255, blank=True, null=True)  
    fuente = models.CharField(db_column='FUENTE', max_length=900, blank=True, null=True)  
    efecto_previsible = models.TextField(db_column='EFECTO_PREVISIBLE', blank=True, null=True)  
    importancia_clinica = models.TextField(db_column='IMPORTANCIA_CLINICA', blank=True, null=True)  

    atc1 = models.ForeignKey('AtcsAempsCache', to_field="codigo", on_delete=models.SET_NULL, blank=True, null=True, related_name="ineteramedmed2", verbose_name="Medicamento")
    atc2 = models.ForeignKey('AtcsAempsCache', to_field="codigo", on_delete=models.SET_NULL, blank=True, null=True, related_name="ineteramedmed1", verbose_name="Medicamento")
    cod1 = models.ForeignKey(Atc, db_column='COD1', to_field='codigoatc', on_delete=models.SET_NULL, blank=True, null=True, related_name='+', verbose_name = 'old med', help_text="No utilizar este campo")
    cod2 = models.ForeignKey(Atc, db_column='COD2', to_field='codigoatc', on_delete=models.SET_NULL, blank=True, null=True, related_name='+', verbose_name = 'old med', help_text="No utilizr este campo")
    validate_user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='med_med_validations')
    owner = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    deleted_user = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True, related_name='+')

    @property
    def is_validated(self):
        return (self.validate_date <= date.today())

    class Meta:
        managed = True
        db_table = 'interaciones_mm'
        verbose_name = 'Interacción medicamento-medicamento'
        verbose_name_plural = 'Interaccciones medicamento-medicamento'
        ordering = ['-id']


