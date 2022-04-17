from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import CustomUser, UserAccount, OrderDish, Order, OrderStatus, CourierAccount
from rest_framework_simplejwt.tokens import AccessToken
from freezegun import freeze_time


class OrderViewTests(APITestCase):
    fixtures = ['restaurant_dishes.json', 'orders.json']

    def setUp(self):
        user1 = CustomUser.objects.get(id=1)
        self.second_header = self.get_header_for_user(user1)
        user = CustomUser.objects.get(id=2)
        self.header = self.get_header_for_user(user)
        OrderDish.objects.create(dish_id_id=1, order_id_id=1, quantity=2)
        OrderDish.objects.create(dish_id_id=1, order_id_id=2, quantity=2)

    def get_header_for_user(self, user):
        token = AccessToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_user_last_open_order_created(self):
        url = reverse('orders-retrieve')

        response = self.client.get(url, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['order']['order_id'], 3, response.data)

    def test_get_user_last_open_order_retrieved(self):
        url = reverse('orders-retrieve')

        response = self.client.get(url, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['order']['order_id'], 2, response.data)
        self.assertEqual(len(response.data['dishes']), 1, response.data)

    def test_update_non_existing_order(self):
        url = reverse('orders-create', kwargs={"pk": 31})

        response = self.client.put(url, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_not_open_order(self):
        url = reverse('orders-create', kwargs={"pk": 1})

        response = self.client.put(url, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], "Це замовлення вже створене", response.data)

    def test_update_order_without_dishes(self):
        url = reverse('orders-retrieve')

        response = self.client.get(url, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        url = reverse('orders-create', kwargs={"pk": response.data['order']['order_id']})

        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address 17, 251"
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], "Ваше замовлення пусте", response.data)

    def test_update_order_without_location(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_address": "test delivery address 17, 251"
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['delivery_location'][0], 'This field is required.', response.data)

    def test_update_order_without_address(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            },
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data["delivery_address"][0], 'This field is required.', response.data)

    def test_update_wrong_order(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address 25, 16"
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_order_with_far_location(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '25.5967171',
                'latitude': "30.4595135"
            },
            "delivery_address": "test delivery address 25, 16"
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], "Ваше місце доставки знаходиться дуже далеко від ресторану",
                         response.data)

    @freeze_time("2020-04-14 04:00:01")
    def test_update_order_when_restaurant_is_closed(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address 25, 16"
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], 'Ресторан зачинений', response.data)

    def test_update_order_successfully(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address 25, 16"
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['order_id'], 2, response.data)
        self.assertEqual(response.data['summary'], 11200, response.data)

    def test_create_same_order_wrong(self):
        url = reverse('orders-recreate', kwargs={"pk": 2})

        response = self.client.post(url, {
            "delivery_location": {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address 25, 16"
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_create_same_order_which_is_not_closed(self):
        url = reverse('orders-recreate', kwargs={"pk": 2})

        response = self.client.post(url, {}, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], "Ви не можете створити замовлення з поточного", response.content)

    def test_create_same_order_successfully(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address 25, 16"
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)

        url = reverse('orders-recreate', kwargs={"pk": 2})

        response = self.client.post(url, {}, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data['order']['order_id'], 4, response.data)
        self.assertEqual(response.data['restaurant'], 1, response.data)
        self.assertEqual(len(response.data['dishes']), 1, response.data)

    def test_update_ordered_dish_not_existing_order(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 42})

        response = self.client.put(url, {
            "dish_id": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_ordered_wrong_dish(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 3})

        response = self.client.put(url, {
            "dish_id": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_ordered_dish_wrong_order(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 1})

        response = self.client.put(url, {
            "dish_id": 1,
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_ordered_dish_already_closed(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 1})

        response = self.client.put(url, {
            "dish_id": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], 'Це замовлення неможливо змінити', response.data)

    def test_delete_ordered_dish_wrong_order(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 1})

        response = self.client.delete(url, {
            "dish_id": 1,
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_delete_non_existing_ordered_dish(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 1})

        response = self.client.delete(url, {
            "dish_id": 3,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_delete_ordered_dish_from_closed_order(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 1})

        response = self.client.delete(url, {
            "dish_id": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_delete_ordered_dish_successfully(self):
        url = reverse('order-dish-detail', kwargs={"order_pk": 2})

        response = self.client.delete(url, {
            "dish_id": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)

    def test_create_ordered_dish_wrong_order(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order_id': 2,
            "dish_id": 2,
            "quantity": 5
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_create_ordered_dish_without_dish_id(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order_id': 2,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['dish_id'][0], "This field is required.", response.content)

    def test_create_ordered_dish_without_order_id(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            "dish_id": 2,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['order_id'][0], "This field is required.", response.content)

    def test_create_ordered_dish_from_other_restaurant(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order_id': 2,
            "dish_id": 3,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], "Ви не можете робити замовлення від декількох ресторанів",
                         response.data)

    def test_create_ordered_dish_to_closed_order(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order_id': 1,
            "dish_id": 2,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], 'Це замовлення неможливо змінити',
                         response.data)

    def test_create_ordered_dish_which_already_exists(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order_id': 1,
            "dish_id": 1,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['non_field_errors'][0], 'The fields order_id, dish_id must make a unique set.',
                         response.data)

    def test_create_ordered_dish_to_non_existing_order(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order_id': 31,
            "dish_id": 1,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_clear_closed_order(self):
        url = reverse('order-dish-clear', kwargs={'order_pk': 1})

        response = self.client.delete(url, {}, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], 'Це замовлення неможливо змінити', response.data)

    def test_clear_order_wrong(self):
        url = reverse('order-dish-clear', kwargs={'order_pk': 1})

        response = self.client.delete(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_clear_successfully(self):
        url = reverse('order-dish-clear', kwargs={'order_pk': 2})

        response = self.client.delete(url, {}, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)
        dishes = OrderDish.objects.filter(order_id__order_id=2)
        self.assertEqual(len(dishes), 0)

    def test_get_user_post_open_orders(self):
        url = reverse('user-orders')

        response = self.client.get(url, {}, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 1, response.data)

    def test_get_exact_order_wrong(self):
        url = reverse('user-orders-key', kwargs={'pk': 2})

        response = self.client.get(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_get_exact_order_successfully(self):
        url = reverse('user-orders-key', kwargs={'pk': 2})

        response = self.client.get(url, {}, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['order']['order_id'], 2, response.data)
        self.assertEqual(len(response.data['dishes']), 1, response.data)


class OrderStatusViewTests(APITestCase):
    fixtures = ['restaurant_dishes.json', 'orders.json']

    def setUp(self):
        user1 = CustomUser.objects.get(id=1)
        self.second_header = self.get_header_for_user(user1)

        user = CustomUser.objects.get(id=2)
        self.header = self.get_header_for_user(user)

        OrderDish.objects.create(dish_id_id=1, order_id_id=1, quantity=2)
        OrderDish.objects.create(dish_id_id=1, order_id_id=2, quantity=2)

        self.courier = CourierAccount.objects.create(user_id=2)
        Order.objects.filter(order_id=2).update(courier_id=self.courier)

    def get_header_for_user(self, user):
        token = AccessToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_order_statuses_wrong(self):
        url = reverse('order-statuses', kwargs={'pk': 1})

        response = self.client.get(url, {}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_get_order_statuses_successfully(self):
        url = reverse('order-statuses', kwargs={'pk': 1})

        response = self.client.get(url, {}, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 4, response.data)

    def test_create_order_status_to_closed_order(self):
        url = reverse('order-statuses', kwargs={'pk': 1})
        Order.objects.filter(order_id=1).update(courier_id=self.courier)
        response = self.client.post(url, {
            'status': 'C'
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], "Це замовлення вже доставлене", response.content)

    def test_create_order_status_which_is_not_delivered_by_you(self):
        url = reverse('order-statuses', kwargs={'pk': 1})

        response = self.client.post(url, {
            'status': 'C'
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_create_non_possible_order_status(self):
        url = reverse('order-statuses', kwargs={'pk': 2})

        response = self.client.post(url, {
            'status': 'O'
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['error'], "Ви не можете робити цю дію", response.content)

    def test_create_order_status_non_courier_account(self):
        url = reverse('order-statuses', kwargs={'pk': 2})

        response = self.client.post(url, {
            'status': 'F'
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
