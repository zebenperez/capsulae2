from django.contrib.auth.models import User
from django.db import models
from django.utils import timezone
from datetime import datetime, date


class Book(models.Model):
    isbn = models.CharField(max_length=255, verbose_name="ISBN", default="", blank=True)
    title = models.TextField(verbose_name="Título", default="", blank=True)
    subtitle = models.TextField(verbose_name="Título", default="", blank=True)
    authors = models.TextField(verbose_name="Autores", default="", blank=True)
    serie = models.TextField(verbose_name="Serie", default="", blank=True)
    publisher_code = models.TextField(verbose_name="Editorial Código", default="", blank=True)
    publisher_name = models.TextField(verbose_name="Editorial", default="", blank=True)

    class Meta:
        verbose_name="Libro"
        verbose_name_plural = "Libros"


