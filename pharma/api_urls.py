from django.urls import path

from . import external_api


urlpatterns = [
    path("patients/lookup/", external_api.patient_by_cip, name="external-patient-by-cip"),
    path("store/products/", external_api.store_products, name="external-store-products"),
    path("publications/", external_api.publications, name="external-publications"),
]
