from django.contrib import admin
from django.contrib.auth.views import LogoutView
from django.conf import settings
from django.urls import include, path

from horarios.views import HorariosLoginView

urlpatterns = [
    path('admin/', admin.site.urls),
    path('login/', HorariosLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),
    path('', include('horarios.urls')),
]

if settings.DEBUG:
    urlpatterns.insert(1, path('__debug__/', include('debug_toolbar.urls')))
