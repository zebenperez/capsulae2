from __future__ import unicode_literals
from django.contrib.auth.models  import User
from django.utils.translation import ugettext as _

from django.db import models

# Create your models here.

class ExternalAuth(models.Model):
    username = models.CharField(max_length=100, verbose_name='Username')
    localusername = models.CharField(max_length=100, verbose_name='External Username')
    request = models.SlugField(max_length=200, verbose_name="Request")
    response = models.SlugField(max_length=200, verbose_name="Response")
    domain = models.CharField(max_length=100, verbose_name='Domain')
    update = models.DateTimeField(verbose_name = 'Last Update')

    class Meta:
        verbose_name="External Authentication"
        managed = False

