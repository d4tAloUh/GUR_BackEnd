from rest_framework import serializers
from ..models import Restaurant
from drf_extra_fields.geo_fields import PointField


class RestaurantSerializer(serializers.ModelSerializer):
    location = PointField(required=True)

    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'open_from',
                  'open_to', 'rest_photo', 'is_open',
                  'rest_address', 'location']


class RestaurantSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['id', 'name', 'rest_address']


class RestaurantSerializerForCourier(serializers.ModelSerializer):
    location = PointField(required=True)

    class Meta:
        model = Restaurant
        fields = ['name', 'rest_address', 'location']
