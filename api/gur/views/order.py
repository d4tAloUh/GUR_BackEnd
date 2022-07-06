from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.db.transaction import atomic
from django.utils.functional import cached_property
from rest_framework import status
from django.db.models import F, Q, Prefetch, Exists, OuterRef
from rest_framework.exceptions import ValidationError

from rest_framework.response import Response

from rest_framework.generics import (
    ListAPIView, CreateAPIView, DestroyAPIView,
    RetrieveUpdateDestroyAPIView, RetrieveAPIView, UpdateAPIView, get_object_or_404
)

from ..serializers.order import (
    OrderSerializer, OrderRetrieveSerializer,
    CourierOrderDetailSerializer,
    OrderDishSerializer, OrderStatusSerializer, OrderWithFirstStatusSerializer,
    OrderWithStatusSerializer,
    OrderDishWithOrderIdSerializer, OrderRecreationDetailSerializer
)
from rest_framework.permissions import IsAuthenticated

from ..models import (
    Order, Dish, OrderStatus,
    OrderDish, CourierAccount
)
from ..services.order import (
    send_order_status_update, get_order_or_create
)


class OrderApiView(RetrieveAPIView):
    serializer_class = OrderRetrieveSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        order, _ = get_order_or_create(self.request.user.id)
        return order


class OrderCreationApiView(UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user__user=self.request.user
        ).exclude(
            Exists(
                OrderStatus.objects.filter(
                    ~Q(status=OrderStatus.OPEN),
                    order=OuterRef("pk"),
                )
            ),
        ).prefetch_related(
            Prefetch(
                "order_dishes",
                queryset=OrderDish.objects.select_related(
                    "dish"
                )
            ),
        )

    def perform_update(self, serializer):
        instance = serializer.save()
        # send this order to all connected couriers
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"courier_queue",
            {
                'type': 'event.neworder',
                'content': CourierOrderDetailSerializer(
                    instance
                ).data
            })


class OrderRecreationApiView(CreateAPIView):
    serializer_class = OrderRecreationDetailSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user__user=self.request.user
        )

    @atomic
    def create(self, request, *args, **kwargs):
        prev_order = self.get_object()
        order, _ = get_order_or_create(user_id=request.user.id)
        if order == prev_order:
            raise ValidationError("You cannot recreate order from the current")

        # remove all dishes from current order
        OrderDish.objects.filter(order_id=order).delete()

        order_dishes = OrderDish.objects.filter(
            order=prev_order
        )
        if not order_dishes.exists():
            raise ValidationError("Last order does not have any dishes")

        order_dishes_to_create = []
        for ordered_dish in order_dishes:
            order_dishes_to_create.append(
                OrderDish(
                    order=order,
                    quantity=ordered_dish.quantity,
                    dish=ordered_dish.dish
                )
            )
        OrderDish.objects.bulk_create(order_dishes_to_create)
        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class OrderDishApiView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrderDishSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return get_object_or_404(
            OrderDish.objects.all(),
            order__id=self.kwargs.get("pk"),
            dish__id=self.request.data.get("dish")
        )

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        order_is_not_open = OrderStatus.objects.filter(
            order__order_dishes=instance,
            order__user__user=request.user
        ).exclude(status=OrderStatus.OPEN).exists()
        if order_is_not_open:
            raise ValidationError("This order cannot be changed")
        instance.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderDishCreateApiView(CreateAPIView):
    serializer_class = OrderDishWithOrderIdSerializer
    permission_classes = [IsAuthenticated]


class OrderDishClearApiView(DestroyAPIView):
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user__user=self.request.user
        ).annotate(
            is_not_updatable=Exists(
                OrderStatus.objects.filter(
                    order=OuterRef("pk")
                ).exclude(status=OrderStatus.OPEN)
            )
        )

    @atomic
    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_not_updatable:
            raise ValidationError("This order cannot be updated")
        OrderDish.objects.filter(order=instance).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderStatusApiView(CreateAPIView, ListAPIView):
    serializer_class = OrderStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderStatus.objects.filter(
            order=self.order
        )

    @cached_property
    def order(self):
        query = Order.objects.select_related(
            "courier"
        ).prefetch_related("statuses")
        return get_object_or_404(query, id=self.kwargs['order_id'])

    def get_serializer_context(self):
        context = super().get_serializer_context()
        context["order"] = self.order
        return context


class UserOrderListApiView(ListAPIView):
    serializer_class = OrderWithFirstStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            Exists(
                OrderStatus.objects.filter(
                    order=OuterRef("pk")
                ).exclude(status=OrderStatus.OPEN)
            ),
            user_id__user=self.request.user
        ).distinct().order_by('-created_at')


class UserOrderApiView(RetrieveAPIView):
    serializer_class = OrderWithStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user__user=self.request.user
        ).prefetch_related(
            Prefetch(
                "order_dishes",
                queryset=OrderDish.objects.select_related(
                    "dish"
                )
            ),
            "statuses"
        )
