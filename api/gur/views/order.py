from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.conf import settings
from rest_framework import status
from django.contrib.gis.geos import GEOSGeometry
from django.db import transaction
from django.db.models import F

from rest_framework.response import Response

from rest_framework.generics import (
    ListAPIView, CreateAPIView, DestroyAPIView,
    RetrieveUpdateDestroyAPIView, RetrieveAPIView, UpdateAPIView
)

from ..serializers.dishes import DishInOrderSerializer
from ..serializers.order import (
    OrderSerializer, OrderRetrieveSerializer,
    CourierFreeOrderSerializer,
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
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def retrieve(self, request, *args, **kwargs):
        try:
            order, created = get_order_or_create(request.user.id)
        except Exception as e:
            print("Retrieve /orders/ exception", e)
            return Response(data={"error": "Сталася помилка"}, status=400)
        serializer = OrderRetrieveSerializer(order)
        if not created:
            dishes_in_order = Dish.objects.filter(orderdish__order_id__order_id=order.order_id).annotate(
                quantity=F('orderdish__quantity'))
            serialized_dishes = DishInOrderSerializer(dishes_in_order, many=True)

            return Response(data={"order": serializer.data,
                                  "dishes": serialized_dishes.data}, status=200)

        return Response(data={"order": serializer.data}, status=200)


class OrderCreationApiView(UpdateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def update(self, request, *args, **kwargs):
        # Finding this order and checking access
        try:
            instance = Order.objects.get(order_id=self.kwargs.get("pk"), user_id__user_id=request.user.id)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

        if OrderStatus.objects.filter(order_id__order_id=self.kwargs.get("pk"), status="P").exists():
            return Response({"error": "Це замовлення вже створене"}, status=status.HTTP_400_BAD_REQUEST)

        serializer = self.get_serializer(instance, data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        # setting order status
        try:
            dishes = OrderDish.objects.filter(order_id=instance)

            if not dishes.exists():
                raise UserWarning("Ваше замовлення пусте")

            order_location = GEOSGeometry(
                f'POINT({serializer.validated_data["delivery_location"][0]} {serializer.validated_data["delivery_location"][1]})',
                srid=4326)
            restaurant = Restaurant.objects.filter(
                dish__dish_id=dishes[0].dish_id.dish_id,
                location__dwithin=(order_location, settings.POSSIBLE_USER_DISTANCE)
            )

            if not restaurant:
                raise UserWarning("Ваше місце доставки знаходиться дуже далеко від ресторану")

            if not restaurant[0].is_open():
                raise UserWarning("Ресторан зачинений")

        except UserWarning as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Restaurant.DoesNotExist:
            return Response({"error": "Цього ресторану вже не існує"}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            OrderStatus.objects.create(status="P", order_id=instance)
            instance.summary = get_order_summary(instance.order_id)
            instance.save(update_fields=["summary"])

        # send this order to all connected couriers
        channel_layer = get_channel_layer()
        async_to_sync(channel_layer.group_send)(
            f"courier_queue",
            {
                'type': 'event.neworder',
                'content': CourierFreeOrderSerializer(instance).data
            })
        return Response(serializer.data)


class OrderSameCreationApiView(CreateAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]

    def create(self, request, *args, **kwargs):
        try:
            if not Order.objects.filter(order_id=self.kwargs.get('pk'), user_id__user=request.user).exists():
                raise Order.DoesNotExist
            order, created = get_order_or_create(request.user.id)
            if order.order_id == self.kwargs.get('pk'):
                raise UserWarning("Ви не можете створити замовлення з поточного")
            # remove all dishes from current order
            OrderDish.objects.filter(order_id=order).delete()

            order_dishes = OrderDish.objects.filter(order_id=self.kwargs.get('pk'))
            if not order_dishes:
                raise UserWarning("В цьому замовленні немає страв")
            order_dishes_to_create = []
            for ordered_dish in order_dishes:
                order_dishes_to_create.append(
                    OrderDish(
                        order_id=order,
                        quantity=ordered_dish.quantity,
                        dish_id=ordered_dish.dish_id)
                )
            OrderDish.objects.bulk_create(order_dishes_to_create)

            dishes_in_order = Dish.objects.filter(
                orderdish__order_id__order_id=order.order_id
            ).annotate(
                quantity=F('orderdish__quantity')
            )
            serialized_dishes = DishInOrderSerializer(dishes_in_order, many=True)
            serializer = OrderRetrieveSerializer(order)
            return Response(
                data={"order": serializer.data,
                      "dishes": serialized_dishes.data,
                      "restaurant": dishes_in_order[0].restaurant_id.rest_id},
                status=status.HTTP_201_CREATED)
        except UserWarning as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class OrderDishApiView(RetrieveUpdateDestroyAPIView):
    serializer_class = OrderDishSerializer
    lookup_field = 'order_id'
    lookup_url_kwarg = 'order_pk'
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return OrderDish.objects.get(
            order_id__order_id=self.kwargs.get("order_pk"),
            dish_id__dish_id=self.request.data["dish_id"]
        )

    def update(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            serializer = self.get_serializer(instance, data=request.data)
            serializer.is_valid(raise_exception=True)
            order_is_available_to_add(self.kwargs.get("order_pk"),
                                      serializer.validated_data['dish_id'].dish_id,
                                      request.user.id)
            self.perform_update(serializer)
            return Response(serializer.data)
        except UserWarning as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response({"error": "Такого замовлення не існує"}, status=status.HTTP_400_BAD_REQUEST)
        except OrderDish.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            order = Order.objects.get(
                orderdish=instance,
                user_id__user=request.user
            )
            order_is_not_open = OrderStatus.objects.filter(
                order_id=order
            ).exclude(status=OrderStatus.OPEN).exists()
            if order_is_not_open:
                raise UserWarning("Це замовлення неможливо змінити")
            instance.delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserWarning as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except (OrderDish.DoesNotExist, Order.DoesNotExist):
            return Response(status=status.HTTP_404_NOT_FOUND)


class OrderDishCreateApiView(CreateAPIView):
    serializer_class = OrderDishWithOrderIdSerializer
    permission_classes = [IsAuthenticated]
    queryset = OrderDish.objects.all()

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            order_is_available_to_add(
                serializer.validated_data['order_id'].order_id,
                serializer.validated_data['dish_id'].dish_id,
                request.user.id
            )
            self.perform_create(serializer)
            headers = self.get_success_headers(serializer.data)
            return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
        except UserWarning as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response(
                {"error": "Такого замовлення не існує"},
                status=status.HTTP_404_NOT_FOUND
            )


class OrderDishClearApiView(DestroyAPIView):
    serializer_class = OrderSerializer
    lookup_field = 'order_id'
    lookup_url_kwarg = 'order_pk'
    permission_classes = [IsAuthenticated]

    def destroy(self, request, *args, **kwargs):
        try:
            instance = Order.objects.get(
                order_id=self.kwargs['order_pk'],
                user_id__user=request.user
            )
            order_is_not_open = OrderStatus.objects.filter(
                order_id=instance
            ).exclude(status=OrderStatus.OPEN).exists()
            if order_is_not_open:
                raise UserWarning("Це замовлення неможливо змінити")
            OrderDish.objects.filter(order_id=instance).delete()
            return Response(status=status.HTTP_204_NO_CONTENT)
        except UserWarning as err:
            return Response({"error": str(err)}, status=status.HTTP_400_BAD_REQUEST)
        except Order.DoesNotExist:
            return Response(status=status.HTTP_404_NOT_FOUND)


class OrderStatusApiView(CreateAPIView, ListAPIView):
    queryset = OrderStatus.objects.all()
    serializer_class = OrderStatusSerializer
    lookup_field = 'order_id'
    lookup_url_kwarg = 'pk'
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return OrderStatus.objects.filter(
            order_id__order_id=self.kwargs['pk']
        )

    def list(self, request, *args, **kwargs):
        if not Order.objects.filter(
                order_id=self.kwargs['pk'],
                user_id__user=request.user
        ).exists():
            return Response(status=status.HTTP_404_NOT_FOUND)

        queryset = self.filter_queryset(self.get_queryset())

        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)

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
    queryset = Order.objects.all()
    serializer_class = OrderWithFirstStatusSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Order.objects.filter(
            user_id__user=self.request.user,
            orderstatus__status__in=OrderStatus.NON_OPEN_STATUSES
        ).distinct().order_by('-created_tm')


class UserOrderApiView(RetrieveAPIView):
    queryset = Order.objects.all()
    serializer_class = OrderWithStatusSerializer
    permission_classes = [IsAuthenticated]
    lookup_field = 'order_id'
    lookup_url_kwarg = 'pk'

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()

        if instance.user_id.user != request.user:
            return Response(status=status.HTTP_404_NOT_FOUND)

        serializer = self.get_serializer(instance)
        dishes_in_order = Dish.objects.filter(
            orderdish__order_id__order_id=instance.order_id
        ).annotate(
            quantity=F('orderdish__quantity')
        )
        serialized_dishes = DishInOrderSerializer(dishes_in_order, many=True)

        return Response(
            data={"order": serializer.data,
                  "dishes": serialized_dishes.data},
            status=status.HTTP_200_OK
        )
