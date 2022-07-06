from rest_framework import serializers
from ..models import Dish, OrderDish


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


class OrderedDishSerializer(serializers.ModelSerializer):
    dish = DishSerializer()

    class Meta:
        model = OrderDish
        fields = ['quantity', 'dish']

    def to_representation(self, instance):
        representation = super().to_representation(instance)
        dish_keys = representation.pop("dish", {})
        representation.update(dish_keys)
        return representation
