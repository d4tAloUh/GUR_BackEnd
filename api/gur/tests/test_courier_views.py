from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import CustomUser, UserAccount, CourierAccount
from rest_framework_simplejwt.tokens import AccessToken


class CourierViewTests(APITestCase):
    fixtures = ['orders_with_users.json']

    def setUp(self):
        self.user = CustomUser.objects.create_user(email='bla@gmail.com', password='password')
        CourierAccount.objects.create(user=self.user)
        self.header = self.get_header_for_user(self.user)

        self.first_courier_user = CustomUser.objects.get(id=2)
        self.courier_header = self.get_header_for_user(self.first_courier_user)

    def get_header_for_user(self, user):
        token = AccessToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_free_orders(self):
        url = reverse('courier-free-orders')

        response = self.client.get(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 2, response.data)

    def test_get_current_courier_order(self):
        url = reverse('courier-current-order')

        response = self.client.get(url, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)

        response = self.client.get(url, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], 1)

    def test_take_free_order_with_big_distance(self):
        url = reverse('courier-free-order-update', kwargs={'pk': 3})

        response = self.client.put(url, {
            'courier_location': {
                'longitude': "13.25",
                'latitude': '5.38'
            }
        }, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertIn("courier_location", response.data)

    def test_take_order_which_is_taken(self):
        url = reverse('courier-free-order-update', kwargs={'pk': 1})

        response = self.client.put(url, {
            'courier_location': {
                'longitude': "30.5967171",
                'latitude': '50.45951349999998'
            }
        }, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertIsNotNone(response.data)

    def test_take_order_when_delivering_order(self):
        url = reverse('courier-free-order-update', kwargs={'pk': 3})

        response = self.client.put(url, {
            'courier_location': {
                'longitude': '30.5967171',
                'latitude': "50.4595135"
            }
        }, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(len(response.data), 1)

    def test_post_new_courier_location_to_wrong_order(self):
        url = reverse('courier-location', kwargs={'order_id': 3})

        response = self.client.post(url, {
            'location': {
                'longitude': "13.25",
                'latitude': '5.38'
            }
        }, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertEqual(len(response.data), 1)

    def test_post_new_courier_location_to_order(self):
        url = reverse('courier-location', kwargs={'order_id': 1})

        response = self.client.post(url, {
            'location': {
                'longitude': "13.25",
                'latitude': '5.38'
            }
        }, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data['location']['latitude'], 5.38, response.data['location'])

    def test_get_courier_orders(self):
        url = reverse('courier-orders')

        response = self.client.get(url, {}, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 1, response.content)
        self.assertEqual(response.data[0]['id'], 1, response.content)

    def test_get_courier_order_pk(self):
        url = reverse('courier-orders-key', kwargs={'pk': 1})
        response = self.client.get(url, **self.courier_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data['id'], 1)

    def test_get_courier_order_which_is_not_assigned_to_this_courier(self):
        url = reverse('courier-orders-key', kwargs={'pk': 2})

        response = self.client.get(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND)
