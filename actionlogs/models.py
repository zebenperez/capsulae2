from django.contrib.auth.models import User
from django.contrib.contenttypes.models import ContentType
from django.contrib.contenttypes.fields import GenericForeignKey
from django.db import models


class ActionLog (models.Model):
    user = models.ForeignKey(User, verbose_name="Usuario", related_name="user_actions", null=True, blank=True,on_delete=models.CASCADE)
    date = models.DateTimeField(verbose_name="Fecha" ,auto_now_add=True)
    url = models.URLField(verbose_name="Url origen")
    action = models.TextField(verbose_name="Accion")
    app = models.CharField(max_length=200, verbose_name="Categoria")
    object_id= models.PositiveIntegerField(blank=True, null=True)
    content_type = models.ForeignKey(ContentType, blank=True, null=True,on_delete=models.SET_NULL)
    content_object = GenericForeignKey('content_type', 'object_id')

    def __str__(self):
        return "[%s] %s  %s"%(self.user.username, self.app, self.action)


