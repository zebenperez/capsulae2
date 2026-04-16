from django.urls import path
from . import views, views_account, auto_views, spd_views, evolutionary_views as evo_views, treatment_views as t_views, params_views
from . import telegram_views, diagnoses_views

urlpatterns = [
    path('index/', views.index, name='pharma-index'),
    path('home/', views.home, name='pharma-home'),

    #------------------------- VIEWS ACCOUNT -----------------------
    #path('signup/', views_account.signup, name='account-signup'),
    
    #------------------------- PATIENTS --------------------
    path('patients/', views.patients, name='patients'),
    path('patients/list/', views.patient_list, name='patient-list'),
    path('patients/search/', views.patient_search, name='patient-search'),
    #path('patients/form/', views.patient_form, name='patient-form'),
    path('patients/new/', views.patient_new, name='patient-new'),
    path('patients/remove/', views.patient_remove, name='patient-remove'),
    path('patients/soft-remove/', views.patient_soft_remove, name='patient-soft-remove'),
    path('patients/remove-msg/', views.patient_remove_msg, name='patient-remove-msg'),
    path('patients/evolutionaries/', views.patient_evolutionaries, name='patient-evolutionaries'),
    path('patients/evolutionaries-csv/', views.patient_evolutionaries_csv, name='patient-evolutionaries-csv'),

    #------------------------- PATIENT --------------------
    path('patients/view/<int:patient_id>', views.patient_view, name='patient-view'),

    path('patients/form/', views.patient_form, name='patient-form'),
    path('patients/qr-generate/', views.patient_qr_generate, name='patient-qr-generate'),

    path('patients/lopd/', views.patient_lopd, name='patient-lopd'),
    path('patients/lopd-add', views.patient_lopd_add, name='patient-lopd-add'),
    path('patients/lopd-remove', views.patient_lopd_remove, name='patient-lopd-remove'),
    path('patients/lopd-generate-document/<int:patient_id>', views.patient_lopd_generate_document, name='patient-lopd-generate-document'),
    path('patients/lopd-generate-document2/<int:patient_id>', views.patient_lopd_generate_document2, name='patient-lopd-generate-document2'),
    path('patients/lopd-generate-document3/<int:patient_id>', views.patient_lopd_generate_document3, name='patient-lopd-generate-document3'),
    path('patients/lopd-generate-signed-document/<int:patient_id>', views.patient_lopd_generate_signed_document, name='patient-lopd-generate-signed-document'),
    path('patients/lopd-generate-signed-document3/<int:patient_id>', views.patient_lopd_generate_signed_document3, name='patient-lopd-generate-signed-document3'),

    path('patients/allergy/', views.patient_allergy, name='patient-allergy'),
    path('patients/allergy/excipients', views.patient_allergy_excipients, name='patient-allergy-excipients'),
    path('patients/allergy/excipient/remove', views.patient_allergy_excipient_remove, name='patient-allergy-excipient-remove'),
    path('patients/allergy/excipients/search', views.patient_allergy_excipients_search, name='patient-allergy-excipients-search'),
    path('patients/allergy/excipients/list/search', views.patient_allergy_excipient_list_search, name='patient-allergy-excipient-list-search'),
    path('patients/allergy/principles', views.patient_allergy_principles, name='patient-allergy-principles'),
    path('patients/allergy/principle/remove', views.patient_allergy_principle_remove, name='patient-allergy-principle-remove'),
    path('patients/allergy/principles/search', views.patient_allergy_principles_search, name='patient-allergy-principles-search'),
    path('patients/allergy/principles/list/search', views.patient_allergy_principles_list_search, name='patient-allergy-principles-list-search'),

    #path('patients/evolutionary/', views.patient_evolutionary, name='patient-evolutionary'),

    path('patients/procedure/', views.patient_procedure, name='patient-procedure'),
    path('patients/procedure-form/', views.patient_procedure_form, name='patient-procedure-form'),
    path('patients/procedure-remove/', views.patient_procedure_remove, name='patient-procedure-remove'),
    path('patients/procedure-file-add/', views.patient_procedure_file_add, name='patient-procedure-file-add'),
    path('patients/procedure-file-remove/', views.patient_procedure_file_remove, name='patient-procedure-file-remove'),

    path('patients/dispensations/', views.patient_dispensations, name='patient-dispensations'),

    path('patients/bibliomecum/', views.patient_bibliomecum, name='patient-bibliomecum'),

    #------------------------- TREATMENT --------------------
    path('patients/treatment/', views.patient_treatment, name='patient-treatment'),
    path('patients/treatment-form/', t_views.patient_treatment_form, name='patient-treatment-form'),
    path('patients/treatment-remove/', t_views.patient_treatment_remove, name='patient-treatment-remove'),
    path('patients/treatment-soft-remove/', t_views.patient_treatment_soft_remove, name='patient-treatment-soft-remove'),
    path('patients/treatment-medication-search/', t_views.patient_treatment_medication_search, name='patient-treatment-medication-search'),
    path('patients/complement-form/', t_views.patient_complement_form, name='patient-complement-form'),
    path('patients/interactions-comment/', t_views.patient_interactions_comment, name='patient-interactions-comment'),
    path('patients/interactions-print/', t_views.patient_interactions_print, name='patient-interactions-print'),
    path('patients/summary/<int:patient_id>/', t_views.patient_summary, name='patient-summary'),
    path('patients/treatments/print/<int:patient_id>/', t_views.patient_treatments_print, name='patient-treatments-print'),
    path('patients/treatments/print-tags/<int:patient_id>/', t_views.patient_treatments_print_tags, name='patient-treatments-print-tags'),
    path('patients/timeline/', t_views.patient_timeline, name='patient-timeline'),

    #------------------------- PATIENT ORG --------------------
    path('patients/orgs/', views.patient_orgs, name='patient-orgs'),
    path('patients/orgs/form', views.patient_org_form, name='patient-org-form'),
    path('patients/orgs/remove', views.patient_org_remove, name='patient-org-remove'),

    #------------------------- PATIENT SHARED --------------------
    path('patients/shared/form', views.patient_shared_form, name='patient-shared-form'),
    path('patients/shared/save', views.patient_shared_save, name='patient-shared-save'),
    path('patients/shared/remove', views.patient_shared_remove, name='patient-shared-remove'),
    path('patients/shared/lopd/<int:obj_id>', views.patient_shared_lopd, name='patient-shared-lopd'),

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
    path('patients/spd/blister-qr-print/<int:pd_id>', spd_views.spd_blister_qr_print, name='spd-blister-qr-print'),

    path('patients/spd/search-by-qr/', spd_views.spd_search_by_qr, name='spd-search-by-qr'),
    path('patients/spd/sim/', spd_views.spd_sim, name='spd-sim'),
    path('patients/spd/sim-clear/', spd_views.spd_sim_clear, name='spd-sim-clear'),
    path('patients/spd/sim/json/', spd_views.spd_sim_json, name='spd-sim-json'),
    path('patients/spd/sim/json-get/<int:comp>/', spd_views.spd_sim_json_get, name='spd-sim-json-get'),
    path('sim/api/', spd_views.spd_simulator, name='spd-simulator'),

    #------------------------- PATIENT EVOLUTIONARY --------------------
    path('patients/evolutionary/', views.patient_evolutionary, name='patient-evolutionary'),
    path('patients/evolutionary/form', evo_views.evolutionary_form, name='evolutionary-form'),
    path('patients/evolutionary/remove', evo_views.evolutionary_remove, name='evolutionary-remove'),
    path('patients/evolutionary/referral-form/<slug:history_num>/', evo_views.evolutionary_referral_form, name='evolutionary-referral-form'),
    path('patients/evolutionary/referral-form/<slug:history_num>/<int:evolutionary_id>/', evo_views.evolutionary_referral_form, name='evolutionary-referral-form'),
    path('patients/evolutionary/referral-form/<slug:history_num>/<int:evolutionary_id>/<slug:view>/', evo_views.evolutionary_referral_form, name='evolutionary-referral-form'),
    path('patients/evolutionary/send-form/', evo_views.evolutionary_send_form, name='evolutionary-send-form'),
    path('patients/evolutionary/file-add/', evo_views.evolutionary_file_add, name='evolutionary-file-add'),
    path('patients/evolutionary/file-remove/', evo_views.evolutionary_file_remove, name='evolutionary-file-remove'),

    #------------------------- PARAMETERS --------------------
    path('patients/params/', views.patient_params, name='patient-params'),
    path('patients/params-form/', params_views.patient_params_form, name='patient-params-form'),
    path('patients/params-form-tab/', params_views.patient_params_form_tab, name='patient-params-form-tab'),
    path('patients/params-remove/', params_views.patient_params_remove, name='patient-params-remove'),
    path('patients/params-print/<int:patient_id>', params_views.patient_params_print, name='patient-params-print'),
    #path('patients/params-print-pdf/', params_views.patient_params_print_pdf, name='patient-params-print-pdf'),

    #------------------------- TELEGRAM --------------------
    path('patients/telegram/', views.patient_telegram, name='patient-telegram'),
    path('patients/telegram-register/', telegram_views.patient_telegram_register, name='patient-telegram-register'),
    path('patients/telegram-register-send/', telegram_views.patient_telegram_register_send, name='patient-telegram-register-send'),
    path('patients/telegram-register-check/', telegram_views.patient_telegram_register_check, name='patient-telegram-register-check'),
    path('patients/telegram-register-remove/', telegram_views.patient_telegram_register_remove, name='patient-telegram-register-remove'),
    path('patients/telegram-message/', telegram_views.patient_telegram_message, name='patient-telegram-message'),
    path('patients/telegram-message-send/', telegram_views.patient_telegram_message_send, name='patient-telegram-message-send'),
    path('patients/telegram-web-hook/', telegram_views.telegram_web_hook, name='telegram-web-hook'),
    path('patients/telegram/pillbox-deliver-notification/', telegram_views.pillbox_deliver_notification, name='patient-telegram-pillbox-deliver-notification'),
    path('patients/telegram/treatment-notification/', telegram_views.treatment_notification, name='patient-telegram-treatment-notification'),
    path('patients/telegram/params-notification/', telegram_views.params_notification, name='patient-telegram-params-notification'),

    #------------------------- DIAGNOSIS --------------------
    path('patients/diagnoses/', views.patient_diagnoses, name='patient-diagnoses'),
    path('patients/diagnoses/form/', diagnoses_views.patient_diagnoses_form, name='patient-diagnoses-form'),
    path('patients/diagnoses/remove/', diagnoses_views.patient_diagnoses_remove, name='patient-diagnoses-remove'),
    path('patients/diagnoses/search/', diagnoses_views.patient_diagnoses_search, name='patient-diagnoses-search'),

    #------------------------- API --------------------
    path('patients/api/get-patients/', views.patient_api_get_patients, name='patient-api-get-patients'),

    #---------------------- AUTO -----------------------
    path('autosave_field/', auto_views.autosave_field, name='autosave_field'),
    path('autosave_fields/', auto_views.autosave_fields, name='autosave_fields'),
    path('autoremove_obj/', auto_views.autoremove_obj, name='autoremove_obj'),
]
