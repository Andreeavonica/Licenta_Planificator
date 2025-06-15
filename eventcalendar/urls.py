
from django.contrib import admin
from django.urls import path, include

from .views import DashboardView


from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path("", DashboardView.as_view(), name="dashboard"),
    path("admin/", admin.site.urls),
    path("accounts/", include("accounts.urls")),
    path("", include("calendarapp.urls")),
]
urlpatterns += static(settings.STATIC_URL, document_root=os.path.join(settings.BASE_DIR, 'static'))
