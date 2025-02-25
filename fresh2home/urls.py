from django.contrib import admin
from django.urls import path,include
from django.conf.urls.static import static
from django.conf import settings

urlpatterns = [
    path('adminn/', admin.site.urls),
    path('accounts/', include('allauth.urls')),
    path("admin/",include("admin_side.urls")),
    path("",include("user_side.urls")),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
