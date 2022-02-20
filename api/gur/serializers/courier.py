from drf_extra_fields.geo_fields import PointField
from rest_framework import serializers
from ..models import CourierLocation


class CourierLocationSerializer(serializers.ModelSerializer):
    location = PointField(required=True)

    class Meta:
        model = CourierLocation
        fields = ['location']