from django.urls import path
from . import views, views_account, auto_views, spd_views, evolutionary_views as evo_views

urlpatterns = [
    path('index/', views.index, name='pharma-index'),

    #------------------------- VIEWS ACCOUNT -----------------------
    path('signup/', views_account.signup, name='account-signup'),
    
    #------------------------- PATIENTS --------------------
    path('patients/', views.patients, name='patients'),
    path('patients/list/', views.patient_list, name='patient-list'),
    path('patients/search/', views.patient_search, name='patient-search'),
    #path('patients/form/', views.patient_form, name='patient-form'),
    path('patients/new/', views.patient_new, name='patient-new'),
    path('patients/remove/', views.patient_remove, name='patient-remove'),

    #------------------------- PATIENT --------------------
    path('patients/view/<int:patient_id>', views.patient_view, name='patient-view'),

    path('patients/form/', views.patient_form, name='patient-form'),

    path('patients/treatment/', views.patient_treatment, name='patient-treatment'),
    path('patients/treatment-form/', views.patient_treatment_form, name='patient-treatment-form'),
    path('patients/treatment-remove/', views.patient_treatment_remove, name='patient-treatment-remove'),
    path('patients/treatment-medication-search/', views.patient_treatment_medication_search, name='patient-treatment-medication-search'),
    path('patients/complement-form/', views.patient_complement_form, name='patient-complement-form'),
    path('patients/interactions-comment/', views.patient_interactions_comment, name='patient-interactions-comment'),
    path('patients/interactions-print/', views.patient_interactions_print, name='patient-interactions-print'),

    path('patients/lopd/', views.patient_lopd, name='patient-lopd'),
    path('patients/lopd-add', views.patient_lopd_add, name='patient-lopd-add'),
    path('patients/lopd-remove', views.patient_lopd_remove, name='patient-lopd-remove'),
    path('patients/lopd-generate-document/<int:patient_id>', views.patient_lopd_generate_document, name='patient-lopd-generate-document'),
    path('patients/lopd-generate-signed-document/<int:patient_id>', views.patient_lopd_generate_signed_document, name='patient-lopd-generate-signed-document'),

    path('patients/allergy/', views.patient_allergy, name='patient-allergy'),
    path('patients/allergy/excipients', views.patient_allergy_excipients, name='patient-allergy-excipients'),
    path('patients/allergy/excipient/remove', views.patient_allergy_excipient_remove, name='patient-allergy-excipient-remove'),
    path('patients/allergy/principles', views.patient_allergy_principles, name='patient-allergy-principles'),
    path('patients/allergy/principle/remove', views.patient_allergy_principle_remove, name='patient-allergy-principle-remove'),

    path('patients/evolutionary/', views.patient_evolutionary, name='patient-evolutionary'),

    path('patients/procedure/', views.patient_procedure, name='patient-procedure'),
    path('patients/procedure-form/', views.patient_procedure_form, name='patient-procedure-form'),
    path('patients/procedure-remove/', views.patient_procedure_remove, name='patient-procedure-remove'),

    #------------------------- PATIENT ORG --------------------
    path('patients/orgs/', views.patient_orgs, name='patient-orgs'),
    path('patients/orgs/form', views.patient_org_form, name='patient-org-form'),
    path('patients/orgs/remove', views.patient_org_remove, name='patient-org-remove'),

    #------------------------- PATIENT SPD --------------------
    path('patients/spd/', views.patient_spd, name='patient-spd'),
    path('patients/spd/form', spd_views.spd_form, name='spd-form'),
    path('patients/spd/remove', spd_views.spd_remove, name='spd-remove'),
    path('patients/spd/toggle-treatment', spd_views.spd_toggle_treatment, name='spd-toggle-treatment'),
    path('patients/spd/toggle-treatment-blister', spd_views.spd_toggle_treatment_blister, name='spd-toggle-treatment-blister'),
    path('patients/spd/active-toggle', spd_views.spd_active_toggle, name='spd-active-toggle'),

    path('patients/spd/blisters', spd_views.spd_blisters, name='spd-blisters'),
    path('patients/spd/blister-form', spd_views.spd_blister_form, name='spd-blister-form'),
    path('patients/spd/blister-remove', spd_views.spd_blister_remove, name='spd-blister-remove'),
    path('patients/spd/blister-clone', spd_views.spd_blister_clone, name='spd-blister-clone'),
    path('patients/spd/blister-print/<int:pd_id>', spd_views.spd_blister_print, name='spd-blister-print'),

    path('patients/spd/search-by-qr/', spd_views.spd_search_by_qr, name='spd-search-by-qr'),

    #------------------------- PATIENT EVOLUTIONARY --------------------
    path('patients/evolutionary/', views.patient_evolutionary, name='patient-evolutionary'),
    path('patients/evolutionary/form', evo_views.evolutionary_form, name='evolutionary-form'),
    path('patients/evolutionary/remove', evo_views.evolutionary_remove, name='evolutionary-remove'),
    path('patients/evolutionary/referral-form/<slug:history_num>/', evo_views.evolutionary_referral_form, name='evolutionary-referral-form'),
    path('patients/evolutionary/referral-form/<slug:history_num>/<int:evolutionary_id>/', evo_views.evolutionary_referral_form, name='evolutionary-referral-form'),
    path('patients/evolutionary/referral-form/<slug:history_num>/<int:evolutionary_id>/<slug:view>/', evo_views.evolutionary_referral_form, name='evolutionary-referral-form'),
    path('patients/evolutionary/send-form/', evo_views.evolutionary_send_form, name='evolutionary-send-form'),

    #---------------------- AUTO -----------------------
    path('autosave_field/', auto_views.autosave_field, name='autosave_field'),
    path('autoremove_obj/', auto_views.autoremove_obj, name='autoremove_obj'),
]
