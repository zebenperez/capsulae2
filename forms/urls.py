from django.urls import path
from . import views


urlpatterns = [
    path('regulariza/<int:org>', views.regulariza, name="forms-regulariza"),
	path('regulariza/save/', views.regulariza_save, name="forms-regulariza-save"),
]
