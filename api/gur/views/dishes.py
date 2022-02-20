from rest_framework.response import Response
from rest_framework import status

from rest_framework.generics import (
    ListAPIView, CreateAPIView, DestroyAPIView,
    UpdateAPIView, RetrieveAPIView
)
from rest_framework.permissions import IsAuthenticated

from ..models import (
    Dish, Restaurant, RestaurantAdmin
)
from ..serializers.dishes import (
    DishSerializer
)
from ..serializers.restaurant import RestaurantSerializer
from ..services.common import pass_test as restaurant_admin_pass_test


class DishApiView(ListAPIView, CreateAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticated]

    def list(self, request, *args, **kwargs):
        try:
            restaurant = Restaurant.objects.get(rest_id=self.kwargs.get('pk'))
            dishes = Dish.objects.filter(restaurant_id=restaurant)
            dish_serializer = DishSerializer(dishes, many=True)
            rest_serializer = RestaurantSerializer(restaurant)
            return Response({"dishes": dish_serializer.data,
                             "restaurant": rest_serializer.data}, status=200)
        except Restaurant.DoesNotExist:
            return Response({"error": "Такого ресторану не існує"}, status=status.HTTP_404_NOT_FOUND)

    def create(self, request, *args, **kwargs):
        if not restaurant_admin_pass_test(self.request):
            return Response(status=status.HTTP_404_NOT_FOUND)
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        admin_rest_ids = RestaurantAdmin.objects.get_admin_restaurant_ids(
            user=self.request.user
        )

        if not self.request.user.is_superuser and \
                serializer.validated_data["restaurant_id"].rest_id not in admin_rest_ids:
            return Response(
                {"error": "Ви не можете створити страви для іншого ресторану"},
                status=status.HTTP_403_FORBIDDEN
            )

        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class DishExactApiView(RetrieveAPIView, DestroyAPIView, UpdateAPIView):
    queryset = Dish.objects.all()
    serializer_class = DishSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        if not restaurant_admin_pass_test(self.request):
            return Response(status=status.HTTP_404_NOT_FOUND)
        try:
            instance = Dish.objects.get(dish_id=self.kwargs.get('pk'))
            serializer = self.get_serializer(instance)
            return Response({"dish": serializer.data})
        except Dish.DoesNotExist:
            return Response({"error": "Такої страви не існує"}, status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        if not restaurant_admin_pass_test(self.request):
            return Response(status=status.HTTP_404_NOT_FOUND)
        dish_id = self.kwargs.get('pk', None)
        if dish_id is None:
            return Response({"error": "Страва має бути вказана"}, status=status.HTTP_400_BAD_REQUEST)
        admin_rest_ids = RestaurantAdmin.objects.get_admin_restaurant_ids(
            user=self.request.user
        )
        try:
            instance = Dish.objects.get(dish_id=dish_id)
            if not self.request.user.is_superuser and instance.restaurant_id.rest_id not in admin_rest_ids:
                return Response({"error": "Ви не можете видалити страви іншого ресторану"},
                                status=status.HTTP_403_FORBIDDEN)
            self.perform_destroy(instance)
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Dish.DoesNotExist:
            return Response({"error": "Такої страви не існує"}, status=status.HTTP_404_NOT_FOUND)

    def update(self, request, *args, **kwargs):
        if not restaurant_admin_pass_test(self.request):
            return Response(status=status.HTTP_404_NOT_FOUND)
        dish_id = self.kwargs.get('pk', None)
        if dish_id is None:
            return Response({"error": "Страва має бути вказана"}, status=status.HTTP_400_BAD_REQUEST)
        admin_rest_ids = RestaurantAdmin.objects.get_admin_restaurant_ids(
            user=self.request.user
        )
        try:
            instance = Dish.objects.get(dish_id=dish_id)

            if not self.request.user.is_superuser and instance.restaurant_id.rest_id not in admin_rest_ids:
                return Response({"error": "Ви не можете змінити страви іншого ресторану"},
                                status=status.HTTP_403_FORBIDDEN)
            request.data["restaurant_id"] = instance.restaurant_id.rest_id
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_update(serializer)
            return Response(serializer.data)
        except Dish.DoesNotExist:

            return Response({"error": "Такої страви не існує"}, status=status.HTTP_404_NOT_FOUND)
