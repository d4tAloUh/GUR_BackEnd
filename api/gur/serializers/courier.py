from django.conf import settings
from django.db.transaction import atomic
from drf_extra_fields.geo_fields import PointField
from rest_framework import serializers
from rest_framework.exceptions import ValidationError

from ..models import CourierLocation, Order, OrderStatus


class CourierLocationSerializer(serializers.ModelSerializer):
    location = PointField(required=True)

    class Meta:
        model = CourierLocation
        fields = ['location']


class CourierFreeOrderUpdateSerializer(serializers.ModelSerializer):
    courier_location = PointField(required=True, srid=4326)

    class Meta:
        model = Order
        fields = ['courier_location']

    @atomic
    def update(self, instance, validated_data):
        courier_location = validated_data.get("courier_location")

        if courier_location.coordinates.distance(
                instance.delivery_location
        ).m > settings.POSSIBLE_COURIER_DISTANCE:
            raise ValidationError("You are too far from order")

        courier_account = self.context["courier"]

        if courier_account.orders.exclude(
                statuses__status__in=OrderStatus.FINISHED_STATUSES
        ).exists():
            raise ValidationError("You have an active order")

        if not instance.statuses.filter(
                status=OrderStatus.PREPARING
        ).exists():
            raise ValidationError("Order is not available for delivering")

        validated_data["courier"] = courier_account
        return super().update(instance, validated_data)
