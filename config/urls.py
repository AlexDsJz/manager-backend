from django.contrib import admin
from django.urls import path, include
from django.http import JsonResponse
from rest_framework_simplejwt.views import TokenRefreshView
from api.auth import CustomTokenObtainPairView


def health_check(request):
    return JsonResponse({'status': 'ok', 'service': 'manager-backend'})


urlpatterns = [
    path('admin/', admin.site.urls),
    path('health/', health_check, name='health-check'),
    # Auth
    path('api/v1/auth/token/', CustomTokenObtainPairView.as_view(), name='token-obtain'),
    path('api/v1/auth/token/refresh/', TokenRefreshView.as_view(), name='token-refresh'),
    # API
    path('api/v1/', include('api.routes.events')),
    path('api/v1/', include('api.routes.sat')),
]
