from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView


urlpatterns = [
    path('admin/', admin.site.urls),
    path("__debug__/", include("debug_toolbar.urls")),
    path('', TemplateView.as_view(template_name="index.html"), name="index"),

    # Applications Urls
    path('custom-admin/', include("customadmin.urls", namespace="customadmin")),
    path('', include('embermail.interface.users.urls', namespace='users')),
    path('campaigns/', include('embermail.interface.campaigns.urls', namespace='campaigns')),
    path('', include('embermail.interface.payment.urls', namespace='payment')),
    path('templates/', include('embermail.interface.templates.urls', namespace='templates')),
    path('profiles/', include('embermail.interface.profiles.urls', namespace='profiles')),
]
