from django.urls import path
from rest_framework_simplejwt import views as jwt_views

from .views.account import (
    UserRegistrationApiView, UserAccountApiView, CourierAccountApiView,
)

urlpatterns = [
    path(r'register', UserRegistrationApiView.as_view(), name='register'),
    path(r'user-profile', UserAccountApiView.as_view(), name='user-profile'),
    path(r'courier-profile', CourierAccountApiView.as_view(), name='courier-profile'),

    # Token
    path(r'token', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path(r'token/refresh', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
]
