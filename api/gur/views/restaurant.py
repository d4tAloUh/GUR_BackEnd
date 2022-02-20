from rest_framework.response import Response
from rest_framework import status

from ..permissions import IsAdmin
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
    permission_classes = [IsAuthenticated]

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

    def create(self, request, *args, **kwargs):
        if not request.user.is_superuser:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()

        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class RestaurantAdminApiView(UpdateAPIView, DestroyAPIView):
    queryset = Restaurant.objects.all()
    serializer_class = RestaurantSerializer
    permission_classes = [IsAdmin]

    def update(self, request, *args, **kwargs):
        try:
            rest_id = self.kwargs.get("pk", None)
            instance = Restaurant.objects.get(rest_id=rest_id)
            rest_admin = RestaurantAdmin.objects.filter(
                user_id__user=self.request.user,
                rest_id=instance
            )
            if not rest_admin.exists():
                raise RestaurantAdmin.DoesNotExist
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Restaurant.DoesNotExist:
            return Response({"error": "Такого ресторану не існує"}, status=status.HTTP_404_NOT_FOUND)
        except (UserAccount.DoesNotExist, RestaurantAdmin.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        rest_id = self.kwargs.get("pk", None)
        try:
            instance = Restaurant.objects.get(rest_id=rest_id)
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Restaurant.DoesNotExist:
            return Response({"error": "Такого ресторану не існує"}, status=status.HTTP_404_NOT_FOUND)
