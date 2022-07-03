from rest_framework.exceptions import PermissionDenied

from rest_framework.generics import (
    ListAPIView, CreateAPIView, DestroyAPIView,
    UpdateAPIView, RetrieveAPIView
)
from ..models import (
    Dish, RestaurantAdmin
)
from ..permissions import PermissionsRequired
from ..serializers.dishes import (
    DishSerializer
)


class DishApiView(ListAPIView, CreateAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = [PermissionsRequired]
    permissions_post = ["gur.add_dish"]

    def get_queryset(self):
        return Dish.objects.filter(
            restaurant__id=self.kwargs.get('pk')
        )

    def perform_create(self, serializer):
        if not self.request.user.is_superuser or not RestaurantAdmin.objects.filter(
                rest__id=self.kwargs.get('pk'),
                user_account__user=self.request.user
        ).exists():
            raise PermissionDenied("You cannot create dishes of this restaurant")
        serializer.save()


class DishExactApiView(RetrieveAPIView, DestroyAPIView, UpdateAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = [PermissionsRequired]
    permissions_put = ["gur.change_dish"]
    permissions_patch = permissions_put
    permissions_delete = ["gur.delete_dish"]

    def perform_destroy(self, instance):
        if not self.request.user.is_superuser or not RestaurantAdmin.objects.filter(
                rest__dishes=instance,
                user_account__user=self.request.user
        ).exists():
            raise PermissionDenied("You cannot delete dishes of this restaurant")
        instance.delete()

    def perform_update(self, serializer):
        if not self.request.user.is_superuser or not RestaurantAdmin.objects.filter(
                rest__dishes=serializer.instance,
                user_account__user=self.request.user
        ).exists():
            raise PermissionDenied("You cannot change dishes of this restaurant")
        serializer.save()
