from rest_framework import serializers
from ..models import Dish


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ['id', 'restaurant',
                  'name', 'description', 'price',
                  'gramme', 'dish_photo']


class DishInOrderSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField()

    class Meta:
        model = Dish
        fields = ['id', 'restaurant', 'name',
                  'description', 'price', 'gramme',
                  'dish_photo', 'quantity']
