import json
from datetime import datetime
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.models import F, Prefetch
from django.db.transaction import atomic
from rest_framework.generics import RetrieveAPIView, ListAPIView, UpdateAPIView, CreateAPIView, get_object_or_404

from ..models import Order, Dish, OrderStatus, CourierAccount
from ..permissions import IsCourier
from ..serializers.courier import CourierLocationSerializer, CourierFreeOrderUpdateSerializer
from ..serializers.order import (
    CourierOrderDetailSerializer,
    OrderWithFirstStatusSerializer,
)


class CourierCurrentOrderApiView(RetrieveAPIView):
    serializer_class = CourierOrderDetailSerializer
    permission_classes = [IsCourier]

    def get_object(self):
        queryset = Order.objects.filter(
            courier__user=self.request.user,
            statuses__status="D"
        ).exclude(
            statuses__status__in=OrderStatus.FINISHED_STATUSES
        ).prefetch_related(
            Prefetch(
                "order_dishes__dish",
                queryset=Dish.objects.annotate(
                    quantity=F('order_dishes__quantity')
                ),
                to_attr="order_dishes"
            ),
        )
        return get_object_or_404(queryset)


class CourierFreeOrderListApiView(ListAPIView):
    serializer_class = CourierOrderDetailSerializer
    permission_classes = [IsCourier]

    def get_queryset(self):
        return Order.objects.filter(
            courier__isnull=True,
            statuses__status="P"
        ).exclude(
            statuses__status__in=OrderStatus.FINISHED_STATUSES
        )


class CourierUpdateFreeOrderApiView(UpdateAPIView):
    permission_classes = [IsCourier]
    serializer_class = CourierFreeOrderUpdateSerializer

    def get_queryset(self):
        return Order.objects.filter(
            statuses__status=OrderStatus.PREPARING
        ).exclude(
            statuses__status__in=OrderStatus.FINISHED_STATUSES
        ).prefetch_related("statuses")

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["courier"] = CourierAccount.objects.prefetch_related(
            "orders"
        ).get(user=self.request.user)
        return context

    @atomic
    def perform_update(self, serializer):
        instance = serializer.save()
        order_status = OrderStatus.objects.create(order=instance, status="D")
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"order_{instance.order_id}",
            {
                'type': 'event.orderstatus',
                'content': json.dumps({
                    "status": order_status.status,
                    "timestamp": datetime.fromtimestamp(
                        order_status.created_at.created_at()
                    ).strftime('%Y-%m-%d %H:%M:%S')
                }, indent=4, default=str)
            }
        )

        async_to_sync(channel_layer.group_send)(
            "courier_queue",
            {
                'type': 'event.ordertaken',
                'content': instance.order_id
            }
        )


class CourierLocationUpdateApiView(CreateAPIView):
    serializer_class = CourierLocationSerializer
    permission_classes = [IsCourier]

    def perform_create(self, serializer):
        courier_account = get_object_or_404(
            CourierAccount.objects.all(),
            **{"user": self.request.user}
        )
        order = get_object_or_404(
            Order.objects.filter(
                courier=courier_account
            ),
            **{"id": self.kwargs["order_id"]}
        )
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"order_{order.id}",
            {
                'type': 'event.location',
                'content': {
                    "latitude": serializer.validated_data['location'][1],
                    "longitude": serializer.validated_data['location'][0]
                }
            })
        serializer.save(courier=courier_account)


class CourierOrderListApiView(ListAPIView):
    serializer_class = OrderWithFirstStatusSerializer
    permission_classes = [IsCourier]

    def get_queryset(self):
        return Order.objects.filter(
            courier_id__user=self.request.user
        ).order_by('-created_at').prefetch_related(
            Prefetch(
                "statuses",
                OrderStatus.objects.order_by("-created_at"),
                to_attr="last_status"
            )
        )


class CourierRetrieveOrderApiView(RetrieveAPIView):
    serializer_class = CourierOrderDetailSerializer
    permission_classes = [IsCourier]

    def get_queryset(self):
        return Order.objects.filter(
            courier__user=self.request.user,
        ).prefetch_related(
            Prefetch(
                "order_dishes__dish",
                queryset=Dish.objects.annotate(
                    quantity=F('order_dishes__quantity')
                ),
                to_attr="order_dishes"
            ),
        )
