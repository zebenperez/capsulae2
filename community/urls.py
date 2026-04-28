from django.urls import path
from community import views

urlpatterns = [
    #------------------------- ORGANIZATIONS --------------------
    path('organizations/', views.organizations, name='organizations'),
    path('organizations/list/', views.organization_list, name='organization-list'),
    path('organizations/search/', views.organization_search, name='organization-search'),
    path('organizations/form/', views.organization_form, name='organization-form'),
    path('organizations/view/<int:obj_id>/', views.organization_view, name='organization-view'),
    path('organizations/remove/', views.organization_remove, name='organization-remove'),
    path('organizations/print/', views.organization_print, name='organization-print'),
    path('organizations/csv/', views.organization_csv, name='organization-csv'),
    path('organizations/share-users/', views.organization_share_users, name='organization-share-users'),
    path('organizations/create-user/', views.organization_create_user, name='organization-create-user'),
    path('organizations/share/', views.organization_share, name='organization-share'),
    path('organizations/register-send/', views.organization_register_send, name='organization-register-send'),
    path('organizations/register/<slug:username>/', views.organization_register, name='organization-register'),
    path('organizations/register-tos/', views.organization_register_tos, name='organization-register-tos'),

    #------------------------- PROCEDURES --------------------
    path('procedures/', views.procedures, name='procedures'),
    path('procedures/list/', views.procedure_list, name='procedure-list'),
    path('procedures/search/', views.procedure_search, name='procedure-search'),
    path('procedures/form/', views.procedure_form, name='procedure-form'),
    path('procedures/remove/', views.procedure_remove, name='procedure-remove'),


#    url(r'^patient/(?P<patient_id>\d+)/$', views.patient_community, name="patient_community"),
#    url(r'^patient/activities/(?P<patient_id>\d+)$', views.patient_activities, name="patient_activities"),
#
#    url(r'^patient/fci/form/(?P<patient_id>\d+)$', views.remote_fci_form, name="remote_fci_form"),
#
#    url(r'^referral_form/(?P<history_num>\w+)/$', views.referral_form, name="referral_form"),
#    url(r'^referral_form/(?P<history_num>\w+)/(?P<evolutionary_id>\w+)/$', views.referral_form, name="referral_form"),
#    url(r'^referral_form/(?P<history_num>\w+)/(?P<evolutionary_id>\w+)/(?P<view>\w+)/$', views.referral_form, name="referral_form"),
#    url(r'^send_form/$', views.send_form, name="send_form"),
#
#    url(r'^organizations/$', views.organizations, name='organizations'),
#    url(r'^organizations/search_remote/$', views.organizations_search_remote, name='organizations_search_remote'),
#    url(r'^organizations/add/$', views.organizations_add, name='organizations_add'),
#    url(r'^organizations/save/$', views.organizations_save, name='organizations_save'),
#    url(r'^organizations/edit/(?P<item_id>\d+)/$', views.organization_edit, name='organization_edit'),
#    url(r'^organizations/delete/(?P<item_id>\d+)/$', views.organization_delete, name='organization_delete'),
#
#
#    url(r'^patientorg/add/(?P<patient_id>\d+)$', views.patientorg_add, name="patientorg_add"),
#    url(r'^patientorg/edit/(?P<patientorg_id>\d+)$', views.patientorg_edit, name="patientorg_edit"),
#    url(r'^patientorg/save/$', views.patientorg_save, name="patientorg_save"),
#    url(r'^patientorg/delete/(?P<patientorg_id>\d+)$', views.patientorg_delete, name="patientorg_delete"),
]
