from rest_framework import serializers
from datetime import datetime
from ..models import Order, OrderStatus, OrderDish, Restaurant, CourierLocation
from .restaurant import RestaurantSerializerForOrder, RestaurantSerializerForCourier
from drf_extra_fields.geo_fields import PointField


class OrderRetrieveSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        fields = ['order_id', 'summary', 'order_details', 'delivery_address']
        read_only_fields = ['order_id', 'summary']


class OrderCourierSerializer(serializers.ModelSerializer):
    courier_location = PointField(required=True)

    class Meta:
        model = Order
        fields = ['order_id', 'courier_location']
        read_only_fields = ['order_id']


class OrderSerializer(serializers.ModelSerializer):
    delivery_location = PointField(required=True)

    class Meta:
        model = Order
        fields = ['order_id', 'summary', 'order_details', 'delivery_address', 'delivery_location']
        read_only_fields = ['order_id', 'summary']
        extra_kwargs = {'delivery_address': {'required': True}}


class OrderWithFirstStatusSerializer(serializers.ModelSerializer):
    order_status = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['order_id', 'summary', 'order_details', 'delivery_address', 'order_status',
                  'created_tm']
        read_only_fields = ['order_id', 'summary', 'order_details', 'delivery_address',
                            'order_status', 'restaurant']

    def get_order_status(self, obj):
        return OrderStatusSerializer(OrderStatus.objects.filter(order_id__order_id=obj.order_id)
                                     .order_by("-timestamp")[0], context=self.context).data

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['created_tm'] = datetime.fromtimestamp(
            instance.created_tm.created_at()
        ).strftime('%Y-%m-%d %H:%M:%S')
        return rep


class OrderWithStatusSerializer(serializers.ModelSerializer):
    order_status = serializers.SerializerMethodField()
    restaurant = serializers.SerializerMethodField()
    location = serializers.SerializerMethodField()
    delivery_location = PointField()

    class Meta:
        model = Order
        fields = ['order_id', 'summary', 'order_details', 'delivery_address', 'order_status',
                  'restaurant', 'created_tm', 'location', 'delivery_location']
        read_only_fields = ['order_id', 'summary', 'order_details', 'delivery_address',
                            'order_status', 'restaurant', 'location', 'delivery_location']

    def get_order_status(self, obj):
        return OrderStatusSerializer(
            OrderStatus.objects.filter(order_id__order_id=obj.order_id),
            many=True,
            context=self.context).data

    def get_restaurant(self, obj):
        try:
            return RestaurantSerializerForOrder(
                Restaurant.objects.filter(dish__orderdish__order_id=obj)[0],
                context=self.context).data
        except IndexError:
            return None

    def get_location(self, obj):
        try:
            if not OrderStatus.objects.filter(
                    order_id=obj, status__in=OrderStatus.FINISHED_STATUSES
            ).exists():
                location = CourierLocation.objects.filter(courier__order=obj).latest('date')
                return {
                    "latitude": location.location.y,
                    "longitude": location.location.x
                }
        except CourierLocation.DoesNotExist:
            return None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['created_tm'] = datetime.fromtimestamp(
            instance.created_tm.created_at()
        ).strftime('%Y-%m-%d %H:%M:%S')
        return rep


class OrderStatusSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderStatus
        fields = ['status', 'timestamp']

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['timestamp'] = datetime.fromtimestamp(
            instance.created_at.created_at()
        ).strftime('%Y-%m-%d %H:%M:%S')
        return rep


class OrderDishSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDish
        fields = ['dish_id', 'quantity']


class OrderDishWithOrderIdSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderDish
        fields = ['order_id', 'dish_id', 'quantity']


class CourierOrderWithStatusSerializer(serializers.ModelSerializer):
    order_status = serializers.SerializerMethodField()
    delivery_location = PointField(required=True)
    restaurant = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['order_id', 'summary', 'order_details',
                  'delivery_address', 'order_status',
                  'restaurant', 'created_tm', 'delivery_location']
        read_only_fields = ['order_id', 'summary',
                            'order_details', 'delivery_address',
                            'order_status', 'restaurant',
                            'delivery_location']

    def get_order_status(self, obj):
        return OrderStatusSerializer(
            OrderStatus.objects.filter(
                order_id__order_id=obj.order_id,
                status__in=OrderStatus.COURIER_ORDER_STATUSES
            ), many=True,
            context=self.context
        ).data

    def get_restaurant(self, obj):
        try:
            return RestaurantSerializerForCourier(
                Restaurant.objects.filter(dish__orderdish__order_id=obj)[0],
                context=self.context).data
        except IndexError:
            return None

    def to_representation(self, instance):
        rep = super().to_representation(instance)
        rep['created_tm'] = datetime.fromtimestamp(
            instance.created_tm.created_at()
        ).strftime('%Y-%m-%d %H:%M:%S')
        return rep


class CourierFreeOrderSerializer(serializers.ModelSerializer):
    delivery_location = PointField(required=True)
    restaurant = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = ['order_id', 'summary', 'order_details',
                  'delivery_address', 'delivery_location',
                  'restaurant']
        read_only_fields = ['order_id', 'summary']

    def get_restaurant(self, obj):
        try:
            return RestaurantSerializerForCourier(
                Restaurant.objects.filter(dish__orderdish__order_id=obj)[0],
                context=self.context).data
        except IndexError:
            return None
