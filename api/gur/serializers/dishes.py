from rest_framework import serializers
from ..models import Dish


class DishSerializer(serializers.ModelSerializer):
    class Meta:
        model = Dish
        fields = ['dish_id', 'restaurant_id',
                  'name', 'description', 'price',
                  'gramme', 'dish_photo']
        extra_kwargs = {
            'name': {'error_messages': {
                'blank': 'Необхідно вказати назву страви.'}},
            'price': {'error_messages': {
                'null': 'Необхідно вказати ціну.',
                'min_value': 'Ціна має бути >= %(limit_value)s'}},
            'gramme': {'error_messages': {
                'null': 'Необхідно вказати кількість.',
                'min_value': 'Кількість має бути >= %(limit_value)s'}}
        }


class DishInOrderSerializer(serializers.ModelSerializer):
    quantity = serializers.IntegerField()

    class Meta:
        model = Dish
        fields = ['dish_id', 'restaurant_id', 'name',
                  'description', 'price', 'gramme',
                  'dish_photo', 'quantity']
        read_only_fields = ['quantity']
