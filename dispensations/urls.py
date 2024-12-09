from django.urls import path
from . import views


urlpatterns = [
    path('dispensations/view/', views.dispensations_view, name='patient-dispensations-view'),
    path('dispensations/remove/', views.dispensations_remove, name='patient-dispensations-remove'),
    path('dispensations/upload/', views.dispensations_upload, name='patient-dispensations-upload'),
    path('dispensations/farmatic/upload/', views.farmatic_upload, name='patient-farmatic-upload'),
]
