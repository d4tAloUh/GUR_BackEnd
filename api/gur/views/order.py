from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from rest_framework import status
from django.db.models import F, Q, Prefetch, Exists, OuterRef
from rest_framework.exceptions import ValidationError

from rest_framework.response import Response

from rest_framework.generics import (
    ListAPIView, CreateAPIView, DestroyAPIView,
    RetrieveUpdateDestroyAPIView, RetrieveAPIView, UpdateAPIView
)

from ..serializers.dishes import DishInOrderSerializer
from ..serializers.order import (
    OrderSerializer, OrderRetrieveSerializer,
    CourierOrderDetailWithStatusSerializer,
    OrderDishSerializer, OrderStatusSerializer, OrderWithFirstStatusSerializer,
    OrderWithStatusSerializer,
    OrderDishWithOrderIdSerializer
)
from rest_framework.permissions import IsAuthenticated

from ..models import (
    Order, Dish, OrderStatus,
    OrderDish, Restaurant, CourierAccount
)
from ..services.order import (
    send_order_status_update, get_order_or_create,
    order_is_available_to_add, get_order_summary
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
        ).exclude(~Q(statuses__status=OrderStatus.OPEN)).prefetch_related(
            Prefetch(
                "order_dishes__dish",
                queryset=Dish.objects.annotate(
                    quantity=F('orderdish__quantity')
                ),
                to_attr="dishes"
            ),
        )

    def perform_update(self, serializer):
        serializer.save()
        # send this order to all connected couriers
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"courier_queue",
            {
                'type': 'event.neworder',
                'content': CourierOrderDetailWithStatusSerializer(
                    serializer.instance
                ).data
            })


class OrderRecreationApiView(CreateAPIView):
    serializer_class = OrderRetrieveSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user__user=self.request.user
        )

    def create(self, request, *args, **kwargs):
        prev_order = self.get_object()
        order, created = get_order_or_create(request.user.id)
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
                    order_id=order,
                    quantity=ordered_dish.quantity,
                    dish_id=ordered_dish.dish_id
                )
            )
        OrderDish.objects.bulk_create(order_dishes_to_create)
        serializer = self.get_serializer(order)
        return Response(serializer.data)


class OrderDishApiView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrderDishSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return OrderDish.objects.get(
            order__id=self.kwargs.get("order_pk"),
            dish__id=self.request.data["dish_id"]
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

    def destroy(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.is_not_updatable:
            raise UserWarning("This order cannot be updated")
        OrderDish.objects.filter(order=instance).delete()
        return Response(status=status.HTTP_204_NO_CONTENT)


class OrderStatusApiView(CreateAPIView, ListAPIView):
    serializer_class = OrderStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderStatus.objects.filter(
            order__id=self.kwargs['order_id'],
            order__user__user=self.request.user
        )

    def create(self, request, *args, **kwargs):
        try:
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            serializer.validated_data['order_id'] = Order.objects.get(order_id=self.kwargs.get('pk'))
            if serializer.validated_data["order_id"].courier_id == CourierAccount.objects.get(user=request.user):
                if serializer.validated_data['status'] == OrderStatus.CANCELLED:
                    if OrderStatus.objects.filter(
                            order_id=serializer.validated_data["order_id"],
                            status=OrderStatus.DELIVERED
                    ).exists():
                        raise UserWarning("Це замовлення вже доставлене")
                elif serializer.validated_data['status'] == OrderStatus.DELIVERED:
                    if OrderStatus.objects.filter(
                            order_id=serializer.validated_data["order_id"],
                            status=OrderStatus.CANCELLED
                    ).exists():
                        raise UserWarning("Це замовлення вже скасоване")
                else:
                    raise UserWarning("Ви не можете робити цю дію")
            # do not allow changing order status
            elif not request.user.is_superuser:
                return Response(status=status.HTTP_404_NOT_FOUND)
            order_status = serializer.save()
            send_order_status_update(order_status)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except UserWarning as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except CourierAccount.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class UserOrderListApiView(ListAPIView):
    serializer_class = OrderWithFirstStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user_id__user=self.request.user
        ).exclude(
            statuses__status=OrderStatus.OPEN
        ).distinct().order_by('-created_tm')


class UserOrderApiView(RetrieveAPIView):
    serializer_class = OrderWithStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user__user=self.request.user
        ).prefetch_related(
            Prefetch(
                "order_dishes__dish",
                queryset=Dish.objects.annotate(
                    quantity=F('orderdish__quantity')
                ),
                to_attr="dishes"
            ),
            "statuses"
        )
