from django.db import models
from pharma.models import Pacientes
import uuid
# Create your models here.

class TelegramUserChat(models.Model):
    code = models.SlugField(verbose_name="Codigo", max_length=50, unique="True")
    creation_date = models.DateTimeField(verbose_name="Fecha de creación", auto_now_add=True, null=True, blank=True)
    patient = models.ForeignKey(Pacientes, verbose_name="Paciente", related_name="patient_telegram", on_delete=models.CASCADE, blank=True, null=True)
    telegram_chat_id = models.SlugField(verbose_name="telegram_id", max_length=50, unique="True")
    confirmed = models.BooleanField(verbose_name="Confirmado", default=False, blank=True)
    observations = models.CharField(verbose_name="Observaciones", max_length=50, blank=True, default="")

    def __str__(self):
        return self.code

    class Meta:
        verbose_name = "Chat Telegram Usuario"
        verbose_name_plural = "Chats Telegram Usuario"

    def save(self, *args, **kwargs):
        if not self.pk:
            self.code = uuid.uuid4().hex[:8]
        super(TelegramUserChat, self).save(*args, **kwargs)

