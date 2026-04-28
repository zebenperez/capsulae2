from django.conf.urls import url
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    url(r'^tokensignin/$', views.tokensignin, name='tokensign'),
    url(r'^check_remote_user/', views.check_remote_user, name='check_remote_user'),
    url(r'^get_remote_user/', views.get_remote_user, name='get_remote_user'),
    url(r'^remote-auth/$', views.remote_auth, name='mylogin-remote-auth'),
    #url(r'^remote-auth/(?P<username>[\w\-]+)/$', views.remote_auth, name='mylogin-remote-auth'),
    url(r'^remote-test/(?P<username>[\w\-]+)/$', views.remote_test, name='mylogin-remote-test'),
    url(r'^remote-test/$', views.remote_test, name='mylogin-remote-test'),
]
