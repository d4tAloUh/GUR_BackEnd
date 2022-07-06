from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.db.models import F
from django.db.transaction import atomic
from rest_framework import serializers
from datetime import datetime

from rest_framework.exceptions import ValidationError, PermissionDenied

from .dishes import DishInOrderSerializer, OrderedDishSerializer
from .user import UserForCourierAccountSerializer
from ..models import Order, OrderStatus, OrderDish, Restaurant, CourierLocation, Dish
from .restaurant import RestaurantSerializerForOrder, RestaurantSerializerForCourier
from drf_extra_fields.geo_fields import PointField

from ..services.order import get_order_summary, order_is_available_to_add


class OrderRetrieveSerializer(serializers.ModelSerializer):
    dishes = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'summary', 'dishes',
                  'order_details', 'delivery_address']

    def get_dishes(self, obj: Order):
        if hasattr(obj, "dishes"):
            # prefetched in queryset
            dishes = obj.dishes
        else:
            dishes = Dish.objects.filter(
                order_dishes__order=obj
            ).annotate(
                quantity=F('order_dishes__quantity')
            )
        return DishInOrderSerializer(
            dishes,
            many=True,
            context=self.context
        ).data


class OrderSerializer(serializers.ModelSerializer):
    delivery_location = PointField(required=True)

    class Meta:
        model = Order
        fields = ['id', 'summary', 'order_details',
                  'delivery_address', 'delivery_location']
        read_only_fields = ['order', 'summary']
        extra_kwargs = {'delivery_address': {'required': True}}

    @atomic
    def update(self, instance, validated_data):
        instance = super().update(instance, validated_data)
        if not instance.order_dishes.exists():
            raise ValidationError("The order is empty")

        order_location = GEOSGeometry(
            f'POINT({validated_data["delivery_location"][0]} {validated_data["delivery_location"][1]})',
            srid=4326
        )
        first_dish = instance.order_dishes.first()
        restaurant = Restaurant.objects.filter(
            dishes__order_dishes=first_dish,
            location__dwithin=(order_location, settings.POSSIBLE_USER_DISTANCE)
        ).first()

        if not restaurant:
            raise ValidationError("The restaurant is too far away")

        if not restaurant.is_open:
            raise ValidationError("The restaurant is closed")

        OrderStatus.objects.create(status="P", order=instance)
        instance.summary = get_order_summary(instance.id)
        instance.save(update_fields=["summary"])

        return instance


class OrderWithFirstStatusSerializer(serializers.ModelSerializer):
    order_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'summary', 'order_details',
                  'delivery_address', 'order_status',
                  'created_at']

    def get_order_status(self, obj):
        if hasattr(obj, "last_status"):
            return OrderStatusSerializer(
                # [0] as it was prefetched
                obj.last_status[0], context=self.context
            ).data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['created_at'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return rep


class OrderWithStatusSerializer(serializers.ModelSerializer):
    order_status = serializers.SerializerMethodField()
    restaurant = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    dishes = serializers.SerializerMethodField()
    delivery_location = PointField()

    class Meta:
        model = Order
        fields = ['id', 'summary', 'order_details',
                  'delivery_address', 'order_status',
                  'restaurant', 'created_at', 'dishes',
                  'location', 'delivery_location']

    def get_dishes(self, obj: Order):
        return OrderedDishSerializer(
            obj.order_dishes.all(),
            many=True,
            context=self.context
        ).data

    def get_order_status(self, obj):
        return OrderStatusSerializer(
            obj.statuses,
            many=True,
            context=self.context
        ).data

    def get_restaurant(self, obj: Order):
        return RestaurantSerializerForCourier(
            Restaurant.objects.filter(
                dishes__order_dishes__order=obj
            ).first(),
            context=self.context
        ).data

    def get_location(self, obj):
        try:
            if not obj.statuses.filter(
                    status__in=OrderStatus.FINISHED_STATUSES
            ).exists():
                location = CourierLocation.objects.filter(
                    courier__orders=obj
                ).latest('created_at')
                return {
                    "latitude": location.location.y,
                    "longitude": location.location.x
                }
        except CourierLocation.DoesNotExist:
            return None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['created_at'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return rep


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['status', 'created_at']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['timestamp'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return rep

    def validate(self, attrs):
        order = self.context.get("order")
        if order.courier and order.courier.user == self.context["request"].user:
            if attrs['status'] == OrderStatus.CANCELLED:
                if order.statuses.filter(
                        status=OrderStatus.DELIVERED
                ).exists():
                    raise ValidationError("This order is already delivered")
            elif attrs['status'] == OrderStatus.DELIVERED:
                if order.statuses.filter(
                        status=OrderStatus.CANCELLED
                ).exists():
                    raise ValidationError("This order is already canceled")
            else:
                raise ValidationError("Invalid status transition")
        elif not self.context["request"].user.is_superuser:
            raise PermissionDenied
        return attrs


class OrderDishSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDish
        fields = ['dish', 'quantity']

    def update(self, instance, validated_data):
        order_is_available_to_add(
            instance.order.id,
            validated_data['dish'].id,
            self.context["request"].user.id
        )
        return super().update(instance, validated_data)


class OrderDishWithOrderIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDish
        fields = ['order', 'dish', 'quantity']

    def create(self, validated_data):
        order_is_available_to_add(
            validated_data["order"].id,
            validated_data['dish'].id,
            self.context["request"].user.id
        )
        return super().create(validated_data)


class CourierOrderDetailSerializer(serializers.ModelSerializer):
    delivery_location = PointField(required=True)
    restaurant = serializers.SerializerMethodField()
    dishes = serializers.SerializerMethodField()
    user = UserForCourierAccountSerializer()

    class Meta:
        model = Order
        fields = ['id', 'user', 'created_at', 'summary',
                  'order_details', 'delivery_address',
                  'delivery_location', 'restaurant', 'dishes',
                  'created_at']

    def get_dishes(self, obj: Order):
        return OrderedDishSerializer(
            obj.order_dishes.all(),
            many=True,
            context=self.context
        ).data

    def get_restaurant(self, obj: Order):
        return RestaurantSerializerForCourier(
            Restaurant.objects.filter(
                dishes__order_dishes__order=obj
            ).first(),
            context=self.context
        ).data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['created_at'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return rep


class OrderRecreationDetailSerializer(serializers.ModelSerializer):
    restaurant_id = serializers.SerializerMethodField()
    dishes = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['id', 'restaurant_id', 'created_at', 'dishes']

    def get_dishes(self, obj: Order):
        return OrderedDishSerializer(
            obj.order_dishes.all(),
            many=True,
            context=self.context
        ).data

    def get_restaurant_id(self, obj: Order):
        restaurant = Restaurant.objects.filter(
            dishes__order_dishes__order=obj
        ).first()
        return restaurant and restaurant.id

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['created_at'] = instance.created_at.strftime('%Y-%m-%d %H:%M:%S')
        return rep
