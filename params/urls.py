from django.conf.urls import url
from params import views

urlpatterns = [
    url(r'^tension/(?P<paciente_id>\d+)/$', views.registro_tension, name="registro_tension"),
    url(r'^tension/chart/(?P<paciente_id>\d+)/$', views.registro_tension_chart, name="registro_tension_chart"),
    url(r'^tension/print/(?P<paciente_id>\d+)/$', views.registro_tension_print, name="registro_tension_print"),
    url(r'^tension/plot/pick/(?P<paciente_id>\d+)/$', views.pick_plots_to_print, name="pick_plots"),

    url(r'^tension/nuevo/(?P<paciente_id>\d+)/$', views.tension_edit_form_ajax, name="tension_add"),
    url(r'^tension/edit/(?P<paciente_id>\d+)/(?P<tension_id>\d+)', views.tension_edit_form_ajax, name="tension_edit"),
    url(r'^tension/save/', views.tension_edit_form_ajax, name="tension_save_form"),
    url(r'^tension/remove/(?P<tension_id>\d+)/$', views.tension_remove, name="tension_remove"),

]
