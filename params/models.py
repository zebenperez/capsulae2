from django.db import models

from pharma.models import Pacientes
# Create your models here.

class BloodPressure(models.Model):
    patient = models.ForeignKey(Pacientes, related_name="blood_pressure", on_delete=models.CASCADE, verbose_name="Paciente")
    creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True)
    date = models.DateTimeField(verbose_name="Fecha")
    observations = models.CharField(verbose_name="Observaciones", max_length=200, blank=True, null=True, default="")
    weight = models.DecimalField(max_digits=6, decimal_places=2, verbose_name="Peso (Kg)", blank=True, null=True)
    height = models.DecimalField(verbose_name="Altura (m)", blank=True, null=True, decimal_places=2, max_digits=4)
    bmi = models.DecimalField(verbose_name="IMC", max_digits=6, decimal_places=2, blank=True, null=True)
    glicosylated = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Glicosilada (HbA1c) est.", blank=True, null=True)
    glucose = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Glucemia basal (mg/dl)", blank=True, null=True)
    hearth_rate = models.IntegerField(verbose_name="Pulso", blank=True, null=True)
    bpressure_min = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Pa min (mm/Hg)", blank=True, null=True)
    bpressure_max = models.DecimalField(max_digits=10, verbose_name="Pa max (mm/Hg)", decimal_places=2, blank=True, null=True)
    inr = models.DecimalField(max_digits=10, verbose_name="INR", decimal_places=3, blank=True, null=True)
    fem = models.DecimalField(max_digits=10, verbose_name="FEM (l/m)", decimal_places=3, blank=True, null=True)
    fev1 = models.DecimalField(max_digits=10, verbose_name="FEV1 (l/seg)", decimal_places=3, blank=True, null=True)
    fev6 = models.DecimalField(max_digits=10, verbose_name="FEV6 (l/seg)", decimal_places=3, blank=True, null=True)
    coef_fev1_fev6 = models.DecimalField(max_digits=10, verbose_name="FEV1 / FEV6", decimal_places=3, blank=True, null=True)
    epe = models.DecimalField(max_digits=10, verbose_name="Edad Pulmonar Estimada", decimal_places=3, blank=True, null=True)
    total_cholesterol = models.DecimalField(max_digits=10, verbose_name="Col.Total (mg/dl)", decimal_places=3, blank=True, null=True)
    hdl = models.DecimalField(max_digits=10, verbose_name="HDL (mg/dl)", decimal_places=3, blank=True, null=True)
    ldl = models.DecimalField(max_digits=10, verbose_name="LDL (mg/dl)", decimal_places=3, blank=True, null=True)
    framingham = models.DecimalField(max_digits=10, verbose_name="Framingham", decimal_places=3, blank=True, null=True)
    triglycerides = models.DecimalField(max_digits=10, verbose_name="Triglicéridos (mg/dl)", decimal_places=3, blank=True, null=True, default=0)
    uric_acid = models.DecimalField(max_digits=10, verbose_name="Ácido úrico (mg/dl)", decimal_places=3, blank=True, null=True)
    serin_creatine_index = models.DecimalField(max_digits=10, verbose_name="Índice de Creatina Sérica (mg/dl)", decimal_places=3, blank=True, null=True)
    mdrd_4 = models.DecimalField(max_digits=10, verbose_name="MDRD-4 (ml/min/1.73m^2)", decimal_places=3, blank=True, null=True, help_text="Filtrado Glomerular estimado")
    mdrd_4_ims = models.DecimalField(max_digits=10, verbose_name="MDRD-4 IMS (ml/min/1.73m^2)", decimal_places=3, blank=True, null=True)
    cdk_epi_creatinine = models.DecimalField(max_digits=10, verbose_name="CDK-EPI-CREATININA (ml/min/1.73m^2)", decimal_places=3, blank=True, null=True)
    got = models.DecimalField(max_digits=10, verbose_name="GOT (U/l)", decimal_places=3, blank=True, null=True)
    gpt = models.DecimalField(max_digits=10, verbose_name="GPT (U/l)", decimal_places=3, blank=True, null=True)
    got_gpt = models.DecimalField(max_digits=10, verbose_name="GOT / GPT", decimal_places=3, blank=True, null=True)
    ggt = models.DecimalField(max_digits=10, verbose_name="GGT (U/l)", decimal_places=3, blank=True, null=True)
    alkaline_phosphatase = models.DecimalField(max_digits=10, verbose_name="Fosfatasa alcalina (U/l)", decimal_places=3, blank=True, null=True)
    eva = models.IntegerField(verbose_name="EVA", blank=True, null=True)
    bicipital = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Pl. Bicipital", blank=True, null=True)
    tricipital = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Pl. Tricipital", blank=True, null=True)
    suprailiac = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Pl. Suprailiaco", blank=True, null=True)
    subscapular = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Pl. SubEscapular", blank=True, null=True)
    abdominal = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Pl. Abdominal", blank=True, null=True)
    belt = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Per. Cintura", blank=True, null=True)
    hip = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Per. Cadera", blank=True, null=True)
    belt_hip_index = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Ind. Cint/Cad", blank=True, null=True)
    fat_index = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="% Graso", blank=True, null=True)
    fat_weight = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Kg Grasa", blank=True, null=True)
    muscle_weight = models.DecimalField(max_digits=10, decimal_places=4, verbose_name="Kg Musculo", blank=True, null=True)


    def __unicode__(self):
        return "%s -[%s]" % (self.patient.n_historial, self.creation_date.strftime("%d-%m-%Y"))

    class Meta:
        db_table = "pharma_bloodpressure"
        verbose_name = "Ficha Tension"
        verbose_name_plural = "Fichas de Tension"
        ordering = ['-creation_date']
