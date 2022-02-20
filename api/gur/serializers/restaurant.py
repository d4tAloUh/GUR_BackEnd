from rest_framework import serializers
from ..models import Restaurant
from drf_extra_fields.geo_fields import PointField


class RestaurantSerializer(serializers.ModelSerializer):
    location = PointField(required=True, error_messages={'required': 'Необхідно вказати локацію ресторану.',
                                                         'invalid': 'Неправильно вказана локація ресторану.',
                                                         'null': 'Необхідно вказати локацію ресторану.'})
    name = serializers.CharField(error_messages={'blank': 'Необхідно вказати назву ресторану.',
                                                 'invalid': 'Неправильно вказана назва ресторану.'})
    rest_address = serializers.CharField(error_messages={'blank': 'Необхідно вказати адресу ресторану.',
                                                         'invalid': 'Неправильно вказана адреса ресторану.'})

    class Meta:
        model = Restaurant
        fields = ['rest_id', 'name', 'open_from',
                  'open_to', 'rest_photo', 'is_open',
                  'rest_address', 'location']


class RestaurantSerializerForOrder(serializers.ModelSerializer):
    class Meta:
        model = Restaurant
        fields = ['rest_id', 'name', 'rest_address']


class RestaurantSerializerForCourier(serializers.ModelSerializer):
    location = PointField(required=True, error_messages={'required': 'Необхідно вказати локацію ресторану',
                                                         'invalid': 'Неправильно вказана локація ресторану'})

    class Meta:
        model = Restaurant
        fields = ['name', 'rest_address', 'location']
