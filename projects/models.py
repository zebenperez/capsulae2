import datetime
from decimal import Decimal

from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models
from django.db.models import Q, Sum


MONEY_MAX_DIGITS = 14
MONEY_DECIMAL_PLACES = 2
PERCENTAGE_MAX_DIGITS = 5
PERCENTAGE_DECIMAL_PLACES = 2


class ProjectStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    ACTIVE = "active", "Activo"
    SUSPENDED = "suspended", "Suspendido"
    COMPLETED = "completed", "Finalizado"
    CANCELLED = "cancelled", "Cancelado"


class ProgressStatus(models.TextChoices):
    NOT_STARTED = "not_started", "No iniciado"
    IN_PROGRESS = "in_progress", "En curso"
    COMPLETED = "completed", "Finalizado"
    DELAYED = "delayed", "Retrasado"
    CANCELLED = "cancelled", "Cancelado"


class ObjectiveType(models.TextChoices):
    GENERAL = "general", "General"
    SPECIFIC = "specific", "Específico"


class FinancierType(models.TextChoices):
    PUBLIC = "public", "Público"
    PRIVATE = "private", "Privado"
    FOUNDATION = "foundation", "Fundación"
    INTERNATIONAL = "international", "Organismo internacional"
    OWN_FUNDS = "own_funds", "Fondos propios"
    OTHER = "other", "Otros"


class InvoiceStatus(models.TextChoices):
    DRAFT = "draft", "Borrador"
    PENDING = "pending", "Pendiente"
    PAID = "paid", "Pagada"
    JUSTIFIED = "justified", "Justificada"
    REJECTED = "rejected", "Rechazada"


def money_sum(queryset, field):
    return queryset.aggregate(total=Sum(field))["total"] or Decimal("0.00")


class Project(models.Model):
    code = models.CharField("Código", max_length=64, blank=True, db_index=True)
    name = models.CharField("Nombre", max_length=255, default="")
    desc = models.TextField("Descripción", default="", blank=True)
    status = models.CharField(
        "Estado",
        max_length=32,
        choices=ProjectStatus.choices,
        default=ProjectStatus.DRAFT,
        db_index=True,
    )
    start_date = models.DateField("Fecha de inicio", blank=True, null=True)
    end_date = models.CharField("Fecha de ejecución", max_length=255, default="", blank=True)
    finish_date = models.DateField("Fecha de fin", blank=True, null=True)
    country = models.CharField("País", max_length=120, default="", blank=True, db_index=True)
    region = models.CharField("Región", max_length=120, default="", blank=True)
    locality = models.CharField("Localidad", max_length=120, default="", blank=True)
    technical_manager = models.ForeignKey(
        User,
        verbose_name="Responsable técnico",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="technical_projects",
    )
    financial_manager = models.ForeignKey(
        User,
        verbose_name="Responsable financiero",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="financial_projects",
    )
    manager = models.ForeignKey(
        User,
        verbose_name="Responsable",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="managed_projects",
    )
    approved_budget = models.DecimalField(
        "Presupuesto aprobado",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    notes = models.TextField("Observaciones", default="", blank=True)

    def __str__(self):
        return self.name or self.code or "Proyecto"

    @property
    def description(self):
        return self.desc

    @property
    def executed_budget(self):
        return money_sum(self.invoice_allocations.all(), "allocated_amount")

    @property
    def execution_percentage(self):
        if not self.approved_budget:
            return Decimal("0.00")
        return (self.executed_budget * Decimal("100")) / self.approved_budget

    @property
    def completed_activities_count(self):
        return self.activities.filter(status=ProgressStatus.COMPLETED).count()

    @property
    def budget_lines_count(self):
        return self.budget_lines.filter(parent__isnull=True).count()

    def clean(self):
        super().clean()
        errors = {}
        if self.start_date and self.finish_date and self.finish_date < self.start_date:
            errors["finish_date"] = "La fecha de fin no puede ser anterior a la fecha de inicio."
        if self.pk and self.approved_budget is not None:
            budget_lines_total = money_sum(self.budget_lines.filter(parent__isnull=True), "approved_budget")
            if budget_lines_total > self.approved_budget:
                errors["approved_budget"] = "El presupuesto del proyecto no puede ser inferior a la suma de sus partidas."
        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Proyecto"
        verbose_name_plural = "Proyectos"
        indexes = [
            models.Index(fields=["code"]),
            models.Index(fields=["status"]),
            models.Index(fields=["country"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(approved_budget__gte=0), name="project_approved_budget_gte_0"),
        ]


class Objective(models.Model):
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, related_name="objectives")
    code = models.CharField("Código", max_length=64, db_index=True)
    name = models.CharField("Nombre", max_length=255)
    description = models.TextField("Descripción", blank=True)
    objective_type = models.CharField("Tipo", max_length=32, choices=ObjectiveType.choices)
    status = models.CharField(
        "Estado",
        max_length=32,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED,
        db_index=True,
    )
    progress_percentage = models.DecimalField(
        "Porcentaje de avance",
        max_digits=PERCENTAGE_MAX_DIGITS,
        decimal_places=PERCENTAGE_DECIMAL_PLACES,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    notes = models.TextField("Observaciones", blank=True)

    def __str__(self):
        return "%s - %s" % (self.code, self.name)

    class Meta:
        verbose_name = "Objetivo"
        verbose_name_plural = "Objetivos"
        unique_together = ("project", "code")
        indexes = [models.Index(fields=["project", "objective_type"])]
        constraints = [
            models.CheckConstraint(
                check=Q(progress_percentage__gte=0) & Q(progress_percentage__lte=100),
                name="objective_progress_between_0_100",
            ),
        ]


class Indicator(models.Model):
    objective = models.ForeignKey(Objective, verbose_name="Objetivo", on_delete=models.CASCADE, related_name="indicators")
    name = models.CharField("Nombre", max_length=255)
    description = models.TextField("Descripción", blank=True)
    baseline = models.DecimalField("Línea base", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    target = models.DecimalField("Meta", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    current_value = models.DecimalField("Valor actual", max_digits=12, decimal_places=2, default=Decimal("0.00"))
    unit = models.CharField("Unidad", max_length=64, blank=True)
    measurement_frequency = models.CharField("Frecuencia de medición", max_length=120, blank=True)
    verification_source = models.TextField("Fuente de verificación", blank=True)
    responsible = models.ForeignKey(
        User,
        verbose_name="Responsable",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="project_indicators",
    )
    last_update = models.DateField("Fecha última actualización", blank=True, null=True)

    @property
    def compliance_percentage(self):
        if self.target == self.baseline:
            return Decimal("100.00") if self.current_value >= self.target else Decimal("0.00")
        progress = (self.current_value - self.baseline) / (self.target - self.baseline)
        return max(Decimal("0.00"), min(progress * Decimal("100"), Decimal("100.00")))

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Indicador"
        verbose_name_plural = "Indicadores"
        indexes = [models.Index(fields=["objective"])]


class Activity(models.Model):
    project = models.ForeignKey(
        Project,
        verbose_name="Proyecto",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="activities",
    )
    objective = models.ForeignKey(
        Objective,
        verbose_name="Objetivo",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="activities",
    )
    code = models.CharField("Código", max_length=64, blank=True, db_index=True)
    name = models.CharField("Nombre", max_length=255, default="")
    desc = models.TextField("Descripción", default="", blank=True)
    responsible = models.ForeignKey(
        User,
        verbose_name="Responsable",
        on_delete=models.SET_NULL,
        blank=True,
        null=True,
        related_name="project_activities",
    )
    location = models.CharField("Ubicación", max_length=255, blank=True)
    planned_start_date = models.DateField("Fecha inicio prevista", blank=True, null=True)
    planned_end_date = models.DateField("Fecha fin prevista", blank=True, null=True)
    real_start_date = models.DateField("Fecha inicio real", blank=True, null=True)
    real_end_date = models.DateField("Fecha fin real", blank=True, null=True)
    status = models.CharField(
        "Estado",
        max_length=32,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED,
        db_index=True,
    )
    progress_percentage = models.DecimalField(
        "Porcentaje de avance",
        max_digits=PERCENTAGE_MAX_DIGITS,
        decimal_places=PERCENTAGE_DECIMAL_PLACES,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )

    def __str__(self):
        return self.name

    @property
    def description(self):
        return self.desc

    def clean(self):
        super().clean()
        if self.objective and self.project and self.objective.project_id != self.project_id:
            raise ValidationError({"objective": "El objetivo debe pertenecer al proyecto de la actividad."})
        if self.planned_start_date and self.planned_end_date and self.planned_end_date < self.planned_start_date:
            raise ValidationError({"planned_end_date": "La fecha fin prevista no puede ser anterior al inicio."})
        if self.real_start_date and self.real_end_date and self.real_end_date < self.real_start_date:
            raise ValidationError({"real_end_date": "La fecha fin real no puede ser anterior al inicio."})

    class Meta:
        verbose_name = "Actividad"
        verbose_name_plural = "Actividades"
        unique_together = ("project", "code")
        indexes = [models.Index(fields=["project", "status"])]
        constraints = [
            models.CheckConstraint(
                check=Q(progress_percentage__gte=0) & Q(progress_percentage__lte=100),
                name="activity_progress_between_0_100",
            ),
        ]


class Result(models.Model):
    objective = models.ForeignKey(Objective, verbose_name="Objetivo", on_delete=models.CASCADE, related_name="results")
    description = models.TextField("Descripción")
    expected_result = models.TextField("Resultado esperado")
    obtained_result = models.TextField("Resultado obtenido", blank=True)
    evidence = models.TextField("Evidencias", blank=True)
    compliance_percentage = models.DecimalField(
        "Porcentaje cumplimiento",
        max_digits=PERCENTAGE_MAX_DIGITS,
        decimal_places=PERCENTAGE_DECIMAL_PLACES,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    status = models.CharField(
        "Estado",
        max_length=32,
        choices=ProgressStatus.choices,
        default=ProgressStatus.NOT_STARTED,
        db_index=True,
    )

    def __str__(self):
        return self.description[:80]

    class Meta:
        verbose_name = "Resultado"
        verbose_name_plural = "Resultados"
        indexes = [models.Index(fields=["objective", "status"])]
        constraints = [
            models.CheckConstraint(
                check=Q(compliance_percentage__gte=0) & Q(compliance_percentage__lte=100),
                name="result_compliance_between_0_100",
            ),
        ]


class BudgetLine(models.Model):
    MAX_DEPTH = 4

    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, related_name="budget_lines")
    parent = models.ForeignKey(
        "self",
        verbose_name="Partida padre",
        on_delete=models.CASCADE,
        blank=True,
        null=True,
        related_name="child_lines",
    )
    code = models.CharField("Código", max_length=64)
    name = models.CharField("Nombre", max_length=255)
    description = models.TextField("Descripción", blank=True)
    approved_budget = models.DecimalField(
        "Presupuesto aprobado",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    modified_budget = models.DecimalField(
        "Presupuesto modificado",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )

    @property
    def is_root(self):
        return self.parent_id is None

    @property
    def root_line(self):
        line = self
        visited = {self.pk} if self.pk else set()
        while line.parent is not None:
            if line.parent.pk in visited:
                break
            visited.add(line.parent.pk)
            line = line.parent
        return line

    @property
    def level(self):
        level = 0
        parent = self.parent
        visited = {self.pk} if self.pk else set()
        while parent is not None:
            if parent.pk in visited:
                break
            visited.add(parent.pk)
            level += 1
            parent = parent.parent
        return level

    @property
    def effective_budget(self):
        return self.modified_budget if self.modified_budget else self.approved_budget

    @property
    def assigned_budget(self):
        return self.approved_budget

    @assigned_budget.setter
    def assigned_budget(self, value):
        self.approved_budget = value

    @property
    def direct_executed_amount(self):
        return money_sum(self.sub_invoice_allocations.all(), "allocated_amount")

    def descendants(self):
        items = []
        for child in self.child_lines.all():
            items.append(child)
            items.extend(child.descendants())
        return items

    @property
    def executed_amount(self):
        descendant_total = money_sum(
            InvoiceAllocation.objects.filter(sub_budget_line__in=self.descendants()),
            "allocated_amount",
        )
        return self.direct_executed_amount + descendant_total

    @property
    def child_assigned_budget(self):
        return money_sum(self.child_lines.all(), "approved_budget")

    @property
    def available_balance(self):
        return self.effective_budget - self.direct_executed_amount - self.child_assigned_budget

    def __str__(self):
        return "%s - %s" % (self.full_code, self.name)

    @property
    def full_code(self):
        codes = [self.code]
        parent = self.parent
        visited = {self.pk} if self.pk else set()
        while parent is not None:
            if parent.pk in visited:
                break
            visited.add(parent.pk)
            codes.insert(0, parent.code)
            parent = parent.parent
        return ".".join(codes)

    def has_children(self):
        return self.child_lines.exists()

    def clean(self):
        super().clean()
        errors = {}
        if self.parent_id and self.parent.project_id != self.project_id:
            errors["parent"] = "La partida padre debe pertenecer al mismo proyecto."
        if self.parent_id:
            if self.parent_id == self.pk:
                errors["parent"] = "Una partida no puede depender de sí misma."
            parent = self.parent
            while parent is not None:
                if parent.parent_id == self.pk:
                    errors["parent"] = "La jerarquía de partidas contiene un ciclo."
                    break
                parent = parent.parent
        if self.level > self.MAX_DEPTH:
            errors["parent"] = "El límite máximo de anidamiento de subpartidas es 4."
        if self.project_id and self.approved_budget is not None:
            if self.parent_id:
                current_total = money_sum(self.parent.child_lines.exclude(pk=self.pk), "approved_budget")
                budget_limit = self.parent.effective_budget
            else:
                current_total = money_sum(self.project.budget_lines.filter(parent__isnull=True).exclude(pk=self.pk), "approved_budget")
                budget_limit = self.project.approved_budget
            if current_total + self.approved_budget > budget_limit:
                errors["assigned_budget"] = "Las subpartidas no pueden superar el presupuesto de su partida padre."
                errors["approved_budget"] = "Las partidas no pueden superar el presupuesto disponible."
        if self.pk:
            child_budget_total = money_sum(self.child_lines.all(), "approved_budget")
            if child_budget_total > self.effective_budget:
                errors["approved_budget"] = "El presupuesto de la partida no puede ser inferior a la suma de sus subpartidas de primer nivel."
                errors["modified_budget"] = "El presupuesto de la partida no puede ser inferior a la suma de sus subpartidas de primer nivel."
        if errors:
            raise ValidationError(errors)

    class Meta:
        verbose_name = "Partida presupuestaria"
        verbose_name_plural = "Partidas presupuestarias"
        unique_together = ("project", "code")
        indexes = [models.Index(fields=["project", "code"]), models.Index(fields=["parent", "code"])]
        constraints = [
            models.CheckConstraint(check=Q(approved_budget__gte=0), name="budget_line_approved_gte_0"),
            models.CheckConstraint(check=Q(modified_budget__gte=0), name="budget_line_modified_gte_0"),
        ]


class Financier(models.Model):
    name = models.CharField("Nombre", max_length=255, db_index=True)
    financier_type = models.CharField("Tipo", max_length=32, choices=FinancierType.choices, default=FinancierType.OTHER)
    tax_id = models.CharField("CIF/NIF", max_length=64, blank=True, db_index=True)
    address = models.TextField("Dirección", blank=True)
    contact_person = models.CharField("Persona contacto", max_length=255, blank=True)
    email = models.EmailField("Email", blank=True)
    phone = models.CharField("Teléfono", max_length=64, blank=True)
    notes = models.TextField("Observaciones", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Financiador"
        verbose_name_plural = "Financiadores"
        indexes = [models.Index(fields=["name"]), models.Index(fields=["tax_id"])]


class ProjectFinancier(models.Model):
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, related_name="project_financiers")
    financier = models.ForeignKey(
        Financier,
        verbose_name="Financiador",
        on_delete=models.PROTECT,
        related_name="project_financiers",
    )
    committed_amount = models.DecimalField(
        "Importe comprometido",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    granted_amount = models.DecimalField(
        "Importe concedido",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    disbursed_amount = models.DecimalField(
        "Importe desembolsado",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    agreement_date = models.DateField("Fecha convenio", blank=True, null=True)
    agreement_document = models.FileField("Documento convenio", upload_to="projects/agreements/", blank=True)

    @property
    def allocated_amount(self):
        return money_sum(self.financier.budget_contributions.filter(project=self.project), "amount")

    @property
    def available_amount(self):
        return self.committed_amount - self.allocated_amount

    def __str__(self):
        return "%s - %s" % (self.project, self.financier)

    class Meta:
        verbose_name = "Financiador de proyecto"
        verbose_name_plural = "Financiadores de proyecto"
        unique_together = ("project", "financier")
        indexes = [models.Index(fields=["project", "financier"])]
        constraints = [
            models.CheckConstraint(check=Q(committed_amount__gte=0), name="project_financier_committed_gte_0"),
            models.CheckConstraint(check=Q(granted_amount__gte=0), name="project_financier_granted_gte_0"),
            models.CheckConstraint(check=Q(disbursed_amount__gte=0), name="project_financier_disbursed_gte_0"),
        ]


class FinancierContribution(models.Model):
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, related_name="financier_contributions")
    financier = models.ForeignKey(
        Financier,
        verbose_name="Financiador",
        on_delete=models.PROTECT,
        related_name="budget_contributions",
    )
    budget_line = models.ForeignKey(
        BudgetLine,
        verbose_name="Partida",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="financier_contributions",
    )
    sub_budget_line = models.ForeignKey(
        BudgetLine,
        verbose_name="Subpartida",
        on_delete=models.PROTECT,
        blank=True,
        null=True,
        related_name="sub_financier_contributions",
    )
    amount = models.DecimalField("Importe", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    percentage = models.DecimalField(
        "Porcentaje",
        max_digits=PERCENTAGE_MAX_DIGITS,
        decimal_places=PERCENTAGE_DECIMAL_PLACES,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    notes = models.TextField("Observaciones", blank=True)

    @property
    def allocated_to_invoices(self):
        return money_sum(self.project.invoice_allocations.filter(financier=self.financier), "allocated_amount")

    @property
    def available_amount(self):
        return self.amount - self.allocated_to_invoices

    def clean(self):
        super().clean()
        errors = {}
        if not self.budget_line and not self.sub_budget_line:
            errors["budget_line"] = "Debe indicarse al menos una partida o subpartida."
        if self.budget_line and self.budget_line.project_id != self.project_id:
            errors["budget_line"] = "La partida debe pertenecer al proyecto."
        if self.sub_budget_line:
            if self.sub_budget_line.project_id != self.project_id:
                errors["sub_budget_line"] = "La subpartida debe pertenecer al proyecto."
            if self.budget_line and self.sub_budget_line.root_line.id != self.budget_line_id:
                errors["sub_budget_line"] = "La subpartida debe pertenecer a la partida indicada."
        relation = ProjectFinancier.objects.filter(project=self.project, financier=self.financier).first()
        if not relation:
            errors["financier"] = "El financiador debe estar vinculado al proyecto."
        elif self.amount:
            existing_amount = Decimal("0.00")
            if self.pk:
                existing_amount = FinancierContribution.objects.get(pk=self.pk).amount
            if self.amount > relation.available_amount + existing_amount:
                errors["amount"] = "El financiador no puede aportar más de su importe comprometido."
        budget_limit = self.sub_budget_line.effective_budget if self.sub_budget_line else self.budget_line.effective_budget if self.budget_line else None
        if budget_limit is not None and self.amount:
            contribution_filter = self.project.financier_contributions.exclude(pk=self.pk)
            if self.sub_budget_line:
                current_budget_total = money_sum(contribution_filter.filter(sub_budget_line=self.sub_budget_line), "amount")
            else:
                current_budget_total = money_sum(contribution_filter.filter(budget_line=self.budget_line, sub_budget_line__isnull=True), "amount")
            if current_budget_total + self.amount > budget_limit:
                errors["amount"] = "La aportación no puede superar el presupuesto aprobado."
        if errors:
            raise ValidationError(errors)

    def __str__(self):
        return "%s - %s" % (self.financier, self.amount)

    class Meta:
        verbose_name = "Aportación de financiador"
        verbose_name_plural = "Aportaciones de financiadores"
        indexes = [
            models.Index(fields=["project", "financier"]),
            models.Index(fields=["budget_line"]),
            models.Index(fields=["sub_budget_line"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(amount__gte=0), name="financier_contribution_amount_gte_0"),
            models.CheckConstraint(
                check=Q(percentage__gte=0) & Q(percentage__lte=100),
                name="financier_contribution_pct_between_0_100",
            ),
            models.CheckConstraint(
                check=Q(budget_line__isnull=False) | Q(sub_budget_line__isnull=False),
                name="financier_contribution_has_budget_target",
            ),
        ]


class Invoice(models.Model):
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, related_name="invoices")
    activity = models.ForeignKey(Activity, verbose_name="Actividad", on_delete=models.PROTECT, related_name="invoices")
    provider = models.CharField("Proveedor", max_length=255)
    number = models.CharField("Número", max_length=120)
    issue_date = models.DateField("Fecha emisión")
    payment_date = models.DateField("Fecha pago", blank=True, null=True)
    concept = models.TextField("Concepto")
    taxable_base = models.DecimalField("Base imponible", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    taxes = models.DecimalField(
        "Impuestos",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    total_amount = models.DecimalField("Importe total", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    currency = models.CharField("Moneda", max_length=3, default="EUR")
    document_pdf = models.FileField("Documento PDF", upload_to="projects/invoices/", blank=True)
    status = models.CharField("Estado", max_length=32, choices=InvoiceStatus.choices, default=InvoiceStatus.DRAFT, db_index=True)
    notes = models.TextField("Observaciones", blank=True)

    @property
    def allocated_amount(self):
        return money_sum(self.allocations.all(), "allocated_amount")

    @property
    def pending_amount(self):
        return self.total_amount - self.allocated_amount

    def clean(self):
        super().clean()
        if self.activity and self.project and self.activity.project_id != self.project_id:
            raise ValidationError({"activity": "La actividad debe pertenecer al mismo proyecto que la factura."})
        if self.taxable_base is not None and self.taxes is not None and self.total_amount is not None:
            if self.total_amount < self.taxable_base + self.taxes:
                raise ValidationError({"total_amount": "El importe total no puede ser inferior a base imponible más impuestos."})

    def __str__(self):
        return "%s - %s" % (self.number, self.provider)

    class Meta:
        verbose_name = "Factura"
        verbose_name_plural = "Facturas"
        unique_together = ("project", "provider", "number")
        indexes = [models.Index(fields=["project", "status"]), models.Index(fields=["number"])]
        constraints = [
            models.CheckConstraint(check=Q(taxable_base__gte=0), name="invoice_taxable_base_gte_0"),
            models.CheckConstraint(check=Q(taxes__gte=0), name="invoice_taxes_gte_0"),
            models.CheckConstraint(check=Q(total_amount__gte=0), name="invoice_total_amount_gte_0"),
        ]


class InvoiceDocument(models.Model):
    invoice = models.ForeignKey(Invoice, verbose_name="Factura", on_delete=models.CASCADE, related_name="documents")
    name = models.CharField("Nombre", max_length=255)
    document = models.FileField("Documento", upload_to="projects/invoice-documents/")
    notes = models.TextField("Observaciones", blank=True)

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Documento anexo de factura"
        verbose_name_plural = "Documentos anexos de factura"


class InvoiceAllocation(models.Model):
    invoice = models.ForeignKey(Invoice, verbose_name="Factura", on_delete=models.CASCADE, related_name="allocations")
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, related_name="invoice_allocations")
    activity = models.ForeignKey(Activity, verbose_name="Actividad", on_delete=models.PROTECT, related_name="invoice_allocations")
    budget_line = models.ForeignKey(
        BudgetLine,
        verbose_name="Partida",
        on_delete=models.PROTECT,
        related_name="invoice_allocations",
    )
    sub_budget_line = models.ForeignKey(
        BudgetLine,
        verbose_name="Subpartida",
        on_delete=models.PROTECT,
        related_name="sub_invoice_allocations",
    )
    financier = models.ForeignKey(
        Financier,
        verbose_name="Financiador",
        on_delete=models.PROTECT,
        related_name="invoice_allocations",
    )
    allocated_amount = models.DecimalField("Importe imputado", max_digits=MONEY_MAX_DIGITS, decimal_places=MONEY_DECIMAL_PLACES)
    allocated_percentage = models.DecimalField(
        "Porcentaje imputado",
        max_digits=PERCENTAGE_MAX_DIGITS,
        decimal_places=PERCENTAGE_DECIMAL_PLACES,
        default=Decimal("0.00"),
        validators=[MinValueValidator(0), MaxValueValidator(100)],
    )
    allocation_date = models.DateField("Fecha imputación", default=datetime.date.today)
    notes = models.TextField("Observaciones", blank=True)

    def clean(self):
        super().clean()
        errors = {}
        if self.invoice and self.project and self.invoice.project_id != self.project_id:
            errors["invoice"] = "La factura debe pertenecer al proyecto."
        if self.activity and self.project and self.activity.project_id != self.project_id:
            errors["activity"] = "La actividad debe pertenecer al proyecto."
        if self.invoice and self.activity and self.invoice.activity_id != self.activity_id:
            errors["activity"] = "La actividad debe coincidir con la actividad de la factura."
        if self.budget_line and self.budget_line.project_id != self.project_id:
            errors["budget_line"] = "La partida debe pertenecer al proyecto."
        if self.sub_budget_line:
            if self.sub_budget_line.project_id != self.project_id:
                errors["sub_budget_line"] = "La subpartida debe pertenecer al proyecto."
            if self.budget_line and self.sub_budget_line.root_line.id != self.budget_line_id:
                errors["sub_budget_line"] = "La partida debe ser la partida padre de la subpartida."
        if self.financier and self.project:
            if not ProjectFinancier.objects.filter(project=self.project, financier=self.financier).exists():
                errors["financier"] = "El financiador debe pertenecer al proyecto."
        if self.invoice_id and self.allocated_amount:
            current_total = money_sum(self.invoice.allocations.exclude(pk=self.pk), "allocated_amount")
            if current_total + self.allocated_amount > self.invoice.total_amount:
                errors["allocated_amount"] = "La suma de imputaciones no puede superar el importe total de la factura."
        if self.sub_budget_line_id and self.allocated_amount:
            current_sub_total = money_sum(self.sub_budget_line.sub_invoice_allocations.exclude(pk=self.pk), "allocated_amount")
            if current_sub_total + self.allocated_amount + self.sub_budget_line.child_assigned_budget > self.sub_budget_line.effective_budget:
                errors["allocated_amount"] = "No puede imputarse más dinero del disponible en la subpartida."
        if self.financier_id and self.project_id and self.allocated_amount:
            financed = money_sum(
                self.project.financier_contributions.filter(financier=self.financier),
                "amount",
            )
            allocated = money_sum(
                self.project.invoice_allocations.filter(financier=self.financier).exclude(pk=self.pk),
                "allocated_amount",
            )
            if allocated + self.allocated_amount > financed:
                errors["financier"] = "No puede imputarse más dinero del financiado por el financiador."
        if errors:
            raise ValidationError(errors)

    def save(self, *args, **kwargs):
        if self.invoice_id and self.allocated_amount and self.invoice.total_amount:
            self.allocated_percentage = (self.allocated_amount * Decimal("100")) / self.invoice.total_amount
        super().save(*args, **kwargs)

    def __str__(self):
        return "%s - %s" % (self.invoice, self.allocated_amount)

    class Meta:
        verbose_name = "Imputación de factura"
        verbose_name_plural = "Imputaciones de facturas"
        indexes = [
            models.Index(fields=["project", "activity"]),
            models.Index(fields=["budget_line", "sub_budget_line"]),
            models.Index(fields=["financier"]),
        ]
        constraints = [
            models.CheckConstraint(check=Q(allocated_amount__gte=0), name="invoice_allocation_amount_gte_0"),
            models.CheckConstraint(
                check=Q(allocated_percentage__gte=0) & Q(allocated_percentage__lte=100),
                name="invoice_allocation_pct_between_0_100",
            ),
        ]


class Text(models.Model):
    name = models.CharField(max_length=255, verbose_name="Name", default="")
    desc = models.TextField(verbose_name="Descripción", default="")
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name="texts")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Texto alternativo"
        verbose_name_plural = "Textos alternativos"


class ActivityUser(models.Model):
    name = models.CharField(max_length=255, verbose_name="Full Name", default="")
    email = models.CharField(max_length=255, verbose_name="Email", default="")
    activity = models.ForeignKey(Activity, on_delete=models.CASCADE, blank=True, null=True, related_name="users")

    def __str__(self):
        return self.name

    class Meta:
        verbose_name = "Usuario de Actividad"
        verbose_name_plural = "Usuarios de Actividad"


class Income(models.Model):
    desc = models.TextField(verbose_name="Descripción", default="")
    amount = models.DecimalField(
        verbose_name="Importe",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name="incomes")

    def __str__(self):
        return self.desc[:80]

    class Meta:
        verbose_name = "Ingreso"
        verbose_name_plural = "Ingresos"
        constraints = [
            models.CheckConstraint(check=Q(amount__gte=0), name="income_amount_gte_0"),
        ]


class Expense(models.Model):
    desc = models.TextField(verbose_name="Descripción", default="")
    amount = models.DecimalField(
        verbose_name="Importe",
        max_digits=MONEY_MAX_DIGITS,
        decimal_places=MONEY_DECIMAL_PLACES,
        default=Decimal("0.00"),
    )
    project = models.ForeignKey(Project, on_delete=models.CASCADE, blank=True, null=True, related_name="expenses")

    def __str__(self):
        return self.desc[:80]

    class Meta:
        verbose_name = "Gasto"
        verbose_name_plural = "Gastos"
        constraints = [
            models.CheckConstraint(check=Q(amount__gte=0), name="expense_amount_gte_0"),
        ]


class Folder(models.Model):
    read_only = models.BooleanField(verbose_name="Solo lectura", default=False)
    name = models.CharField(max_length=200, verbose_name="Nombre", default="", blank=True)
    parent = models.ForeignKey("self", verbose_name="Carpeta", on_delete=models.CASCADE, blank=True, null=True, related_name="childs")
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, blank=True, null=True, related_name="folders")

    class Meta:
        verbose_name = "Carpeta"
        verbose_name_plural = "Carpetas"
        ordering = ["-name"]


def upload_client_file(instance, filename):
    ascii_filename = str(filename.encode("ascii", "ignore"))
    instance.filename = ascii_filename
    folder = "projects/files/%s" % (instance.id)
    if instance.folder is not None:
        folder = "%s/%s" % (folder, instance.folder.id)
    return "/".join(["%s" % (folder), datetime.datetime.now().strftime("%Y%m%d%H%M%S") + ascii_filename])


class File(models.Model):
    moved = models.BooleanField(verbose_name="Movido", default=False)
    name = models.CharField(max_length=255, verbose_name="Nombre", default="", blank=True)
    proj_file = models.FileField(upload_to=upload_client_file, blank=True, verbose_name="Fichero", help_text="Select file to upload")
    folder = models.ForeignKey(Folder, verbose_name="Carpeta", on_delete=models.CASCADE, blank=True, null=True, related_name="files")
    project = models.ForeignKey(Project, verbose_name="Proyecto", on_delete=models.CASCADE, blank=True, null=True, related_name="files")

    class Meta:
        verbose_name = "Fichero"
        verbose_name_plural = "Ficheros"
        ordering = ["id"]
