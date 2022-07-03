from rest_framework.response import Response
from rest_framework import status

from ..permissions import IsAdmin, PermissionsRequired, IsRestaurantAdmin
from ..serializers.restaurant import (
    RestaurantSerializer
)
from ..models import *
from rest_framework.generics import (
    ListAPIView, CreateAPIView,
    UpdateAPIView, DestroyAPIView
)
from rest_framework.permissions import (
    IsAuthenticated
)


class RestaurantApiView(ListAPIView, CreateAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsAuthenticated & PermissionsRequired]
    permissions_post = ["gur.add_restaurant"]

    def get_queryset(self):
        longitude = self.request.query_params.get('longitude', None)
        latitude = self.request.query_params.get('latitude', None)
        if longitude is not None and latitude is not None:
            return Restaurant.objects.get_restaurants_to_position(
                longitude=longitude, latitude=latitude
            )

        if self.request.user.is_superuser:
            return Restaurant.objects.all()

        return Restaurant.objects.filter(
            restaurantadmin__user_id__user=self.request.user
        )


class RestaurantAdminApiView(UpdateAPIView, DestroyAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsRestaurantAdmin]
