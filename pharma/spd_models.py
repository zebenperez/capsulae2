from django.db import models

from datetime import datetime, timedelta

from .models import Pacientes
from .treatment_models import Tratamiento
from account.models import EmployeeProfile
from capsulae2.commons import get_random_str


class Pillbox(models.Model):
    active = models.BooleanField(verbose_name="Activo", default=True)
    creation_date = models.DateField(verbose_name="Fecha de creación", auto_now_add=True)
    description = models.CharField(verbose_name="Descripción", max_length=200, blank=True, null=True, default="")

    patient = models.ForeignKey(Pacientes, on_delete=models.CASCADE, related_name="pillboxes", verbose_name="Paciente")

    def __str__(self):
        return "%s-%s"%(self.pk, self.description)

    @property
    def last_deliver(self):
        return self.pillbox_delivers.all().order_by('-creation_date').first()

    @property
    def last_deliver_finish_date(self):
        last_deliver = self.last_deliver
        response_date = datetime.strptime("2000-01-01", "%Y-%m-%d")
        if last_deliver:
            response_date = last_deliver.finish_date

        return time.mktime(response_date.timetuple())

    @property
    def expiration_date(self):
        last_finish_date = self.last_deliver.finish_date
        expiration_date = last_finish_date + timedelta(days=PILLBOX_EXPIRATION_DATE)
        return expiration_date

    @property
    def is_expired(self):
        now = datetime.now().date()
        is_expired = True if now > self.expiration_date else False
        return is_expired

    def check_treatments(self):
        patient_treatment_list = list(self.patient.tratamientos.filter(activo=True))
        pillbox_treatment_list = [item.treatment for item in self.pillbox_treatments.all()]
        return (list(set(patient_treatment_list) - set(pillbox_treatment_list)))

    def have_treatment(self, treatment):
        return (treatment.id in list(self.pillbox_treatments.values_list('treatment', flat=True)))

    def have_treatment_in_blister(self, treatment):
        obj = self.pillbox_treatments.filter(treatment=treatment).first()
        return obj.include_in_spd if obj != None else False

    def treatments_in_spd(self):
        return self.pillbox_treatments.filter(include_in_spd=True)

    def treatments_not_in_spd(self):
        return self.pillbox_treatments.filter(include_in_spd=False)

    class Meta:
        db_table = 'pharma_pillbox'
        verbose_name = 'Spd'
        verbose_name_plural = 'Spds'

class PillboxTreatment(models.Model):
    include_in_spd = models.BooleanField(verbose_name="Incluir en el SPD", default=True) #Incluir en el blister

    treatment = models.ForeignKey(Tratamiento, on_delete=models.SET_NULL, verbose_name="Tratamiento", related_name="pillbox_treatments", null=True)
    pillbox = models.ForeignKey(Pillbox, on_delete=models.CASCADE, related_name="pillbox_treatments")

    #def __str__(self):
    #    return self.__unicode__()

    @property
    def name(self):
        try:
            return self.treatment.medicamentos.all().first().name
        except Exception:
            return ""

    @property
    def reg_code(self):
        return self.treatment.reg_code

    class Meta:
        db_table = 'pharma_pillboxtreatment'
        verbose_name="Tratamiento pastillero"
        verbose_name_plural ="Tratamientos pastillero"
        ordering = ['-pk']

class PillboxDeliver(models.Model):
    code = models.SlugField(verbose_name="Lote", max_length=50)
    creation_date = models.DateField(verbose_name="Fecha de preparación", blank=True, null=True)
    deliver_date = models.DateField(verbose_name="Fecha de entrega", blank=True, null=True )
    finish_date = models.DateField(verbose_name="Fecha de finalizacion", blank=True, null=True)
    observations = models.TextField(verbose_name="observations", blank=True , null=True )

    pillbox = models.ForeignKey(Pillbox, on_delete=models.CASCADE, related_name="pillbox_delivers")
    prepared_by = models.ForeignKey(EmployeeProfile, verbose_name="Preparado Por", related_name="deliver_preparations", 
        on_delete=models.CASCADE, blank=True, null=True)
    reviewed_by = models.ForeignKey(EmployeeProfile, verbose_name="Revisado Por", related_name="deliver_reviews",
            on_delete=models.CASCADE, blank=True, null=True )

    def __str__(self):
        return str(self.pillbox)

    @staticmethod
    def generate_code(prefix=""):
        for i in range(30):# haremos 30 intentos para encontrar un código válido
            #code = random_string_prefix(prefix, 10)
            code = prefix + get_random_str(10)[:-len(prefix)] 
            if not PillboxDeliver.objects.filter(code=code).exists():
                return code
        return None

    @property
    def expiration_date(self):
        expiration_date = self.deliver_date + timedelta(days=90)
        return expiration_date

    class Meta:
        db_table = 'pharma_pillboxdeliver'
        verbose_name="Entrega pastillero"
        verbose_name_plural ="Entregas pastillero"

class PillboxDeliverMed(models.Model):
    code = models.SlugField(verbose_name="Lote", max_length=50, blank=True, null=True)
    expiration_date = models.DateField(verbose_name="Caducidad", blank=True, null=True)

    pillbox_deliver = models.ForeignKey(PillboxDeliver, on_delete=models.CASCADE, verbose_name="Entrega", related_name="deliver_meds")
    treatment = models.ForeignKey(PillboxTreatment, on_delete=models.SET_NULL, verbose_name="Tratamiento", related_name="treatment_delivers", null=True)

    @property
    def name (self):
        return self.treatment.name

    @property
    def reg_code(self):
        return self.treatment.reg_code

    @property
    def patient_treatment(self):
        return self.treatment.treatment

    @property
    def in_spd(self):
        return self.treatment.include_in_spd

    def __str__(self):
        try:
            return self.treatment.medicamentos.all().first().des_nomco
        except Exception:
            return "--"

    class Meta:
        db_table = 'pharma_pillboxdelivermed'
        verbose_name="Medicamento Entregado"
        verbose_name_plural="Medicamentos Entregados"

