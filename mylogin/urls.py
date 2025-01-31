#from django.conf.urls import url
from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

urlpatterns = [
    path('tokensignin/', views.tokensignin, name='tokensign'),
    path('check_remote_user/', views.check_remote_user, name='check_remote_user'),
    path('get_remote_user/', views.get_remote_user, name='get_remote_user'),
    path('remote-auth/', views.remote_auth, name='mylogin-remote-auth'),

    path('remote-test/<slug:username>/', views.remote_test, name='mylogin-remote-test'),
    path('remote-test/', views.remote_test, name='mylogin-remote-test'),

    path('check_cip/', views.check_cip, name='check_cip'),
    path('create_paciente/', views.create_paciente, name='create_paciente'),
    path('update_paciente/', views.update_paciente, name='update_paciente'),

#    url(r'^tokensignin/$', views.tokensignin, name='tokensign'),
#    url(r'^check_remote_user/', views.check_remote_user, name='check_remote_user'),
#    url(r'^get_remote_user/', views.get_remote_user, name='get_remote_user'),
#    url(r'^remote-auth/$', views.remote_auth, name='mylogin-remote-auth'),
#    #url(r'^remote-auth/(?P<username>[\w\-]+)/$', views.remote_auth, name='mylogin-remote-auth'),
#    url(r'^remote-test/(?P<username>[\w\-]+)/$', views.remote_test, name='mylogin-remote-test'),
#    url(r'^remote-test/$', views.remote_test, name='mylogin-remote-test'),
]
