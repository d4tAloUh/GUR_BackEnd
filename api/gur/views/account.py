from django.contrib.auth import get_user_model

from ..serializers.user import (
    UserAccountSerializer,
    CourierAccountSerializer, UserSerializer
)
from ..models import (
    UserAccount,
    CourierAccount
)
from rest_framework.generics import (
    RetrieveUpdateAPIView, CreateAPIView
)
from rest_framework.permissions import IsAuthenticated

User = get_user_model()


class UserAccountApiView(RetrieveUpdateAPIView):
    serializer_class = UserAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        instance, _ = UserAccount.objects.select_related(
            "user"
        ).prefetch_related("restaurant_admins").get_or_create(
            user=self.request.user
        )
        return instance


class CourierAccountApiView(RetrieveUpdateAPIView):
    serializer_class = CourierAccountSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        instance, _ = CourierAccount.objects.get_or_create(
            user=self.request.user
        )
        return instance


class UserRegistrationApiView(CreateAPIView):
    queryset = User.objects.all()
    serializer_class = UserSerializer
