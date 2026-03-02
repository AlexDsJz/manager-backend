from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'manager-backend'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    path('api/v1/', include('api.routes.events')),
    path('api/v1/', include('api.routes.sat')),
]
