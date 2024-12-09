"""capsulae2 URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import path, include
from django.views.generic.base import RedirectView

urlpatterns = [
    path('', RedirectView.as_view(pattern_name='pharma-index')),
    path('pharma/', include('pharma.urls')),
    path('account/', include('account.urls')),
    path('medication/', include('medication.urls')),
    path('project/', include('projects.urls')),
    path('mylogin/', include('mylogin.urls'), name="mylogin"),
    path('community/', include('community.urls')),
    path('shifts/', include('shifts2.urls')),
    path('notes/', include('agenda.urls')),
    path('dispensations/', include('dispensations.urls')),

    path('accounts/login/', auth_views.LoginView.as_view(template_name='home.html'), name='auth_login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='/pharma/index/'), name='auth_logout'),
    path('admin/', admin.site.urls),
]

from django.conf import settings
from django.conf.urls.static import static
from django.contrib.staticfiles.urls import staticfiles_urlpatterns
if settings.DEBUG == True:
    urlpatterns += staticfiles_urlpatterns()
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)

