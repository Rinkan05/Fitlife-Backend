from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('gimnasio.urls')),
]

handler404 = 'gimnasio.views.pagina_no_encontrada_view'
