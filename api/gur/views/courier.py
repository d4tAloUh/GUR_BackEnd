import json
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from django.contrib.gis.geos import GEOSGeometry
from django.contrib.gis.db.models.functions import Distance
from django.db import transaction
from django.db.models import Q, F
from rest_framework.generics import RetrieveAPIView, ListAPIView, UpdateAPIView, CreateAPIView

from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.status import HTTP_400_BAD_REQUEST, HTTP_404_NOT_FOUND, HTTP_201_CREATED

from ..models import Order, Dish, OrderStatus, UserAccount, CourierAccount
from ..serializers.courier import CourierLocationSerializer
from ..serializers.dishes import DishInOrderSerializer
from ..serializers.order import CourierFreeOrderSerializer, OrderCourierSerializer, OrderWithFirstStatusSerializer, \
    CourierOrderWithStatusSerializer
from ..serializers.user import UserForCourierAccountSerializer
from ..services.order import get_dishes_in_order_with_quantity


class CourierLastOrderApiView(RetrieveAPIView):
    serializer_class = CourierFreeOrderSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        try:
            post_delivery_orders = OrderStatus.objects.filter \
                (order_id__courier_id__user=request.user, status__in=["C", "F"]) \
                .values_list("order_id", flat=True)
            instance = Order.objects.filter(courier_id__user=request.user, orderstatus__status="D").exclude(
                order_id__in=post_delivery_orders)[0]
            serializer = self.get_serializer(instance)
            dishes_in_order = get_dishes_in_order_with_quantity(instance.order_id)
            serialized_dishes = DishInOrderSerializer(dishes_in_order, many=True)
            user_profile_serialized = UserForCourierAccountSerializer(UserAccount.objects.get(order=instance))
            return Response(data={"order": serializer.data,
                                  "dishes": serialized_dishes.data,
                                  "profile": user_profile_serialized.data}, status=200)
        except IndexError:
            return Response(data={"order": None}, status=200)


class CourierFreeOrderApiView(ListAPIView):
    queryset = Order.objects.all()
    serializer_class = CourierFreeOrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(courier_id__isnull=True, orderstatus__status="P")


class CourierUpdateFreeOrderApiView(UpdateAPIView):
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    serializer_class = CourierFreeOrderSerializer

    def update(self, request, *args, **kwargs):
        try:
            courier_account = CourierAccount.objects.get(user=request.user)
            order_location = GEOSGeometry(
                f'POINT({request.data["courier_location"]["longitude"]} {request.data["courier_location"]["latitude"]})',
                srid=4326)
            with transaction.atomic():
                instance = Order.objects.filter(order_id=self.kwargs.get("pk")).annotate(
                    distance=Distance('delivery_location', order_location))[0]
                if instance.courier_id is not None:
                    raise UserWarning("Це замовлення неможливо доставити")
                if instance.distance.m > settings.POSSIBLE_COURIER_DISTANCE:
                    raise UserWarning("Ви дуже далеко знаходитесь від замовлення")
                if Order.objects.filter(~Q(orderstatus__status__in=["C", "F"]),
                                        courier_id=courier_account).exists():
                    raise UserWarning("Ви наразі доставляєте замовлення")
                if not OrderStatus.objects.filter(status="P", order_id=instance).exists():
                    raise UserWarning("Це замовлення ще не створене")
            serializer = OrderCourierSerializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            with transaction.atomic():
                serializer.save(courier_id=courier_account)
                order_status = OrderStatus.objects.create(order_id=instance, status="D")

            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"order_{instance.order_id}",
                {
                    'type': 'event.orderstatus',
                    'content': json.dumps({
                        "status": order_status.status,
                        "timestamp": datetime.fromtimestamp(order_status.created_at.created_at()).strftime(
                            '%Y-%m-%d %H:%M:%S')
                    }, indent=4, default=str)
                })

            async_to_sync(channel_layer.group_send)(
                f"courier_queue",
                {
                    'type': 'event.ordertaken',
                    'content': instance.order_id
                })

            return Response(self.get_serializer(instance).data)
        except UserWarning as e:
            return Response({"error": str(e)}, status=HTTP_400_BAD_REQUEST)
        except (CourierAccount.DoesNotExist, Order.DoesNotExist, IndexError) as e:
            print("free order caputre:", e)
            return Response(status=HTTP_404_NOT_FOUND)
        except KeyError:
            return Response({"error": "Неправильно задана локація"}, status=HTTP_404_NOT_FOUND)


class CourierLocationUpdateApiView(CreateAPIView):
    serializer_class = CourierLocationSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            courier_account = CourierAccount.objects.get(user=request.user)
            order = Order.objects.get(order_id=self.kwargs['order_pk'], courier_id=courier_account)
            channel_layer = get_channel_layer()
            async_to_sync(channel_layer.group_send)(
                f"order_{order.order_id}",
                {
                    'type': 'event.location',
                    'content': {
                        "latitude": serializer.validated_data['location'][1],
                        "longitude": serializer.validated_data['location'][0]
                    }
                })
            serializer.save(courier=courier_account)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=HTTP_201_CREATED, headers=headers)
        except CourierAccount.DoesNotExist:
            return Response(status=HTTP_404_NOT_FOUND)
        except Order.DoesNotExist:
            return Response({"error": "Цього замовлення не існує"}, status=HTTP_404_NOT_FOUND)


class CourierOrderListApiView(ListAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderWithFirstStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            courier_id__user=self.request.user
        ).order_by('-created_tm')


class CourierOrderApiView(RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = CourierOrderWithStatusSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.courier_id.user != request.user:
            return Response(status=HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        dishes_in_order = get_dishes_in_order_with_quantity(instance.order_id)
        serialized_dishes = DishInOrderSerializer(dishes_in_order, many=True)
        user_profile_serialized = UserForCourierAccountSerializer(
            UserAccount.objects.get(order=instance)
        )
        return Response(
            data={"order": serializer.data,
                  "dishes": serialized_dishes.data,
                  "profile": user_profile_serialized.data},
            status=200)
