from django.urls import path
from . import views


urlpatterns = [
	path('consent/upload/<int:paciente_id>/', views.consent_upload, name="lopd_consent_upload"),
    path('consent/generate/<int:paciente_id>/', views.generate_document, name='lopd_generate_consent'),
	path('sign/document/<int:paciente_id>/', views.generate_signed_document, name='lopd_generate_signed_document'),
	path('consents/patient/<int:paciente_id>/', views.patient_consents, name='lopd_consents_patient'),
	path('consent/delete/<int:paciente_id>/<int:consent_id>/', views.delete_document, name="lopd_delete_document"),
]
