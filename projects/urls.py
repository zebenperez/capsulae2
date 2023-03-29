from django.urls import path
from . import views

urlpatterns = [
    #------------------------- PROJECTS --------------------
    path('projects/', views.projects, name='projects'),
    path('projects/list/', views.project_list, name='project-list'),
    path('projects/search/', views.project_search, name='project-search'),
    path('projects/new/', views.project_new, name='project-new'),
    path('projects/remove/', views.project_remove, name='project-remove'),

    #------------------------- PROJECT --------------------
    path('projects/view/<int:project_id>', views.project_view, name='project-view'),
    path('projects/form/', views.project_form, name='project-form'),

    path('projects/activities/', views.project_activities, name='project-activities'),
    path('projects/activity-form/', views.project_activity_form, name='project-activity-form'),
    path('projects/activity-remove/', views.project_activity_remove, name='project-activity-remove'),
#
#    path('patients/lopd/', views.patient_lopd, name='patient-lopd'),
#    path('patients/lopd-add', views.patient_lopd_add, name='patient-lopd-add'),
#    path('patients/lopd-remove', views.patient_lopd_remove, name='patient-lopd-remove'),
#    path('patients/lopd-generate-document/<int:patient_id>', views.patient_lopd_generate_document, name='patient-lopd-generate-document'),
#    path('patients/lopd-generate-signed-document/<int:patient_id>', views.patient_lopd_generate_signed_document, name='patient-lopd-generate-signed-document'),
#
#    path('patients/allergy/', views.patient_allergy, name='patient-allergy'),
]
