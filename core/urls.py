from django.contrib import admin
from django.urls import path, include
from drf_spectacular.views import (
    SpectacularAPIView,
    SpectacularSwaggerView,
    SpectacularRedocView
)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/users/', include('apps.user.urls')),
    path('internal/', admin.site.urls),
    path('api/schema/', SpectacularAPIView.as_view(), name="schema"),
    path('api/schema/swagger-ui', SpectacularSwaggerView.as_view(url_name="schema"), name="swagger-ui"),
    path('api/schema/redoc', SpectacularRedocView.as_view(url_name="schema"), name="redoc"),
    path('api/apartments/', include('apps.apartments.urls')),
    path("api/reviews/", include("apps.reviews.urls")),
    path("api/bookings/", include("apps.bookings.urls")),
    
]
