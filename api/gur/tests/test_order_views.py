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
        OrderDish.objects.create(dish_id=1, order_id=1, quantity=2)
        OrderDish.objects.create(dish_id=1, order_id=2, quantity=2)

    def get_header_for_user(self, user):
        token = AccessToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_user_last_open_order_created(self):
        url = reverse('orders-retrieve')

        response = self.client.get(url, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['id'], 3, response.data)

    def test_get_user_last_open_order_retrieved(self):
        url = reverse('orders-retrieve')

        response = self.client.get(url, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['id'], 2, response.data)
        self.assertEqual(len(response.data['dishes']), 1, response.data)

    def test_update_non_existing_order(self):
        url = reverse('orders-create', kwargs={"pk": 31})

        response = self.client.put(url, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_not_open_order(self):
        url = reverse('orders-create', kwargs={"pk": 1})

        response = self.client.put(url, data={
            "delivery_location": {
                'longitude': '29.2967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address"
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
        self.assertEqual(len(response.data), 1)

    def test_update_order_without_dishes(self):
        url = reverse('orders-retrieve')

        response = self.client.get(url, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK)

        url = reverse('orders-create', kwargs={"pk": response.data['id']})
        response = self.client.put(url, {
            "delivery_location": {
                'longitude': '29.2967171',
                'latitude': "50.4595135"
            },
            "delivery_address": "test delivery address"
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)

        self.assertEqual(len(response.data), 1)

    def test_update_order_without_location(self):
        url = reverse('orders-create', kwargs={"pk": 2})

        response = self.client.put(url, {
            "delivery_address": "test delivery address "
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data), 1)

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
        self.assertEqual(len(response.data), 1)

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
        self.assertEqual(len(response.data), 1)

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
        self.assertEqual(response.data['id'], 2, response.data)
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
        self.assertEqual(len(response.data), 1)

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
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

        self.assertEqual(response.data['id'], 4, response.data)
        self.assertEqual(response.data['restaurant_id'], 1, response.data)
        self.assertEqual(len(response.data['dishes']), 1, response.data)

    def test_update_ordered_dish_not_existing_order(self):
        url = reverse('order-dish-detail', kwargs={"pk": 42})

        response = self.client.put(url, {
            "dish": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_ordered_wrong_dish(self):
        url = reverse('order-dish-detail', kwargs={"pk": 3})

        response = self.client.put(url, {
            "dish": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_ordered_dish_wrong_order(self):
        url = reverse('order-dish-detail', kwargs={"pk": 1})

        response = self.client.put(url, {
            "dish": 1,
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_ordered_dish_already_closed(self):
        url = reverse('order-dish-detail', kwargs={"pk": 1})

        response = self.client.put(url, {
            "dish": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data), 1)

    def test_delete_ordered_dish_wrong_order(self):
        url = reverse('order-dish-detail', kwargs={"pk": 4})

        response = self.client.delete(url, {
            "dish": 1,
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

    def test_delete_non_existing_ordered_dish(self):
        url = reverse('order-dish-detail', kwargs={"pk": 1})

        response = self.client.delete(url, {
            "dish": 3,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_delete_ordered_dish_from_closed_order(self):
        url = reverse('order-dish-detail', kwargs={"pk": 1})

        response = self.client.delete(url, {
            "dish": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_delete_ordered_dish_successfully(self):
        url = reverse('order-dish-detail', kwargs={"pk": 2})

        response = self.client.delete(url, {
            "dish": 1,
        }, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)

    def test_create_ordered_dish_wrong_order(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order': 2,
            "dish": 2,
            "quantity": 5
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_create_ordered_dish_without_dish_id(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order': 2,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['dish'][0], "This field is required.", response.content)

    def test_create_ordered_dish_without_order(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            "dish_id": 2,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['order'][0], "This field is required.", response.content)

    def test_create_ordered_dish_from_other_restaurant(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order': 2,
            "dish_id": 3,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(len(response.data), 1)

    def test_create_ordered_dish_to_closed_order(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order': 1,
            "dish_id": 2,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(len(response.data), 1)

    def test_create_ordered_dish_which_already_exists(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order': 1,
            "dish_id": 1,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(len(response.data), 1)

    def test_create_ordered_dish_to_non_existing_order(self):
        url = reverse('order-dish-create')

        response = self.client.post(url, {
            'order': 31,
            "dish_id": 1,
            "quantity": 5
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_clear_closed_order(self):
        url = reverse('order-dish-clear', kwargs={'pk': 1})

        response = self.client.delete(url, {}, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(len(response.data), 1)

    def test_clear_order_wrong(self):
        url = reverse('order-dish-clear', kwargs={'pk': 1})

        response = self.client.delete(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_clear_successfully(self):
        url = reverse('order-dish-clear', kwargs={'pk': 2})

        response = self.client.delete(url, {}, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)
        dishes = OrderDish.objects.filter(order_id=2)
        self.assertEqual(len(dishes), 0)

    def test_get_user_post_open_orders(self):
        url = reverse('user-orders')

        response = self.client.get(url, {}, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 1)

    def test_get_exact_order_wrong(self):
        url = reverse('user-orders-key', kwargs={'pk': 2})

        response = self.client.get(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_get_exact_order_successfully(self):
        url = reverse('user-orders-key', kwargs={'pk': 2})

        response = self.client.get(url, {}, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['id'], 2)
        self.assertEqual(len(response.data['dishes']), 1)


class OrderStatusViewTests(APITestCase):
    fixtures = ['restaurant_dishes.json', 'orders.json']

    def setUp(self):
        user1 = CustomUser.objects.get(id=1)
        self.second_header = self.get_header_for_user(user1)

        user = CustomUser.objects.get(id=2)
        self.header = self.get_header_for_user(user)

        OrderDish.objects.create(dish_id=1, order_id=1, quantity=2)
        OrderDish.objects.create(dish_id=1, order_id=2, quantity=2)

        self.courier = CourierAccount.objects.create(user_id=2)
        Order.objects.filter(pk=2).update(courier=self.courier)

    def get_header_for_user(self, user):
        token = AccessToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_order_statuses_wrong(self):
        url = reverse('order-statuses', kwargs={'order_id': 4})

        response = self.client.get(url, {}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_get_order_statuses_successfully(self):
        url = reverse('order-statuses', kwargs={'order_id': 1})

        response = self.client.get(url, {}, **self.second_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 4, response.data)

    def test_create_order_status_to_closed_order(self):
        url = reverse('order-statuses', kwargs={'order_id': 1})
        Order.objects.filter(pk=1).update(courier_id=self.courier)
        response = self.client.post(url, {
            'status': 'C'
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(len(response.data), 1)

    def test_create_order_status_which_is_not_delivered_by_you(self):
        url = reverse('order-statuses', kwargs={'order_id': 1})

        response = self.client.post(url, {
            'status': 'C'
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_create_non_possible_order_status(self):
        url = reverse('order-statuses', kwargs={'order_id': 2})

        response = self.client.post(url, {
            'status': 'O'
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertEqual(len(response.data), 1)

    def test_create_order_status_non_courier_account(self):
        url = reverse('order-statuses', kwargs={'order_id': 2})

        response = self.client.post(url, {
            'status': 'F'
        }, **self.second_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
