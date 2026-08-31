from django.urls import path
from . import views


urlpatterns = [
    path('register/<slug:org>', views.register, name="forms-register"),
	path('register/save/', views.register_save, name="forms-register-save"),
    path('regulariza/<int:org>', views.regulariza, name="forms-regulariza"),
	path('regulariza/save/', views.regulariza_save, name="forms-regulariza-save"),
]
