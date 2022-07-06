import datetime
import json

from django.db import transaction
from django.db.models import Sum, F, Prefetch
from django.http import Http404
from rest_framework.exceptions import ValidationError

from ..models import Order, OrderStatus, UserAccount, OrderDish, Dish
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer


def send_order_status_update(order_status):
    channel_layer = get_channel_layer()
    async_to_sync(channel_layer.group_send)(
        f"order_{order_status.order_id.order_id}",
        {
            'type': 'event.orderstatus',
            'content': json.dumps({
                "status": order_status.status,
                "timestamp": datetime.datetime.fromtimestamp(order_status.created_at.created_at()).strftime(
                    '%Y-%m-%d %H:%M:%S')
            }, indent=4, sort_keys=True, default=str)
        })


def order_is_available_to_add(order_id, dish_id, user_id=None):
    current_order = Order.objects.get(id=order_id)
    order_is_not_open = OrderStatus.objects.filter(
        order=current_order
    ).exclude(status="O")
    if user_id is not None and current_order.user.user_id != user_id:
        raise Http404
    if order_is_not_open:
        raise ValidationError("This order cannot be updated")

    dishes_from_other_rest = Dish.objects.filter(
        order_dishes__order__id=order_id
    ).values_list(
        'restaurant__id', flat=True
    ).exclude(restaurant=Dish.objects.get(id=dish_id).restaurant)

    if dishes_from_other_rest.exists():
        raise ValidationError("You can't create order from different restaurants")


def get_order_or_create(user_id: int):
    not_open_orders = OrderStatus.objects.filter(
        order__user__user__id=user_id
    ).exclude(status="O").values_list("order__id", flat=True)

    open_orders = OrderStatus.objects.filter(
        order__user__user__id=user_id, status="O"
    ).exclude(order__id__in=not_open_orders).values("order")

    # There is an open order by user
    if open_orders.exists():
        return Order.objects.prefetch_related(
            Prefetch(
                "order_dishes__dish",
                queryset=Dish.objects.annotate(
                    quantity=F('order_dishes__quantity')
                ),
                to_attr="dishes"
            ),
        ).get(id=open_orders[0]['order']), False

    else:
        new_order = Order()
        new_order.user = UserAccount.objects.get(user_id=user_id)
        with transaction.atomic():
            new_order.save()
            OrderStatus.objects.create(order=new_order, status="O")
        return new_order, True


def get_order_summary(order_id):
    dishes_cost = OrderDish.objects.filter(
        order__id=order_id
    ).annotate(
        result=F('dish_id__price') * F('quantity')
    ).aggregate(Sum('result'))
    # TODO: change to CASE
    if len(dishes_cost) and dishes_cost['result__sum'] is not None:
        summary = dishes_cost['result__sum']
    else:
        summary = 0

    return summary
