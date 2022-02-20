from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import CustomUser, UserAccount, RestaurantAdmin
from rest_framework_simplejwt.tokens import AccessToken


class RestaurantViewTests(APITestCase):
    fixtures = ['restaurant_dishes.json']

    def setUp(self):
        user = CustomUser.objects.create_user(email='bla@gmail.com', password='password')
        user_account = UserAccount.objects.create(user=user)
        self.header = self.get_header_for_user(user)
        RestaurantAdmin.objects.create(rest_id_id=2, user_id=user_account)

        admin_user = CustomUser.objects.create_superuser(email='bla1@gmail.com', password='password')
        UserAccount.objects.create(user=admin_user)
        self.admin_header = self.get_header_for_user(admin_user)

        non_admin_user = CustomUser.objects.create_user(email='bla31@gmail.com', password='password')
        UserAccount.objects.create(user=non_admin_user)
        self.non_admin_header = self.get_header_for_user(non_admin_user)

    def get_header_for_user(self, user):
        token = AccessToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_restaurant_near(self):
        url = reverse('restaurants')
        location = {
            'longitude': '29.251165',
            'latitude': "50.4292357"
        }
        response = self.client.get(f"{url}?longitude={location['longitude']}&latitude={location['latitude']}",
                                   **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 1, response.data)

    def test_get_all_restaurants_as_superuser(self):
        url = reverse('restaurants')

        response = self.client.get(url, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 2, response.data)

    def test_get_restaurants_as_admin_of_restaurant(self):
        url = reverse('restaurants')

        response = self.client.get(url, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data), 1, response.data)

    def test_create_restaurants_non_admin(self):
        url = reverse('restaurants')

        response = self.client.post(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_create_restaurants_successfully(self):
        url = reverse('restaurants')

        response = self.client.post(url, {
            "rest_address": "Русанівська набережна, 12, Київ, 02000",
            "name": "Абу3",
            "location": {
                'longitude': '29.251165',
                'latitude': "50.4292357"
            }
        }, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data['rest_id'], 3, response.content)

    def test_update_restaurants_successfully(self):
        url = reverse('restaurants-admin', kwargs={"pk": 1})

        response = self.client.put(url, {
            "rest_address": "Русанівська набережна, 12, Київ, 02000",
            "name": "Абу1",
            "location": {
                'longitude': '29.251165',
                'latitude': "50.4292357"
            }
        }, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['rest_id'], 1, response.content)

    def test_update_restaurants_non_admin(self):
        url = reverse('restaurants-admin', kwargs={"pk": 1})

        response = self.client.put(url, {
            "rest_address": "Русанівська набережна, 12, Київ, 02000",
            "name": "Абу1",
            "location": {
                'longitude': '29.251165',
                'latitude': "50.4292357"
            }
        }, **self.non_admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_restaurants_wrong_restaurant(self):
        url = reverse('restaurants-admin', kwargs={"pk": 1})

        response = self.client.put(url, {
            "rest_address": "Русанівська набережна, 12, Київ, 02000",
            "name": "Абу1",
            "location": {
                'longitude': '29.251165',
                'latitude': "50.4292357"
            }
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)
        self.assertEqual(response.data['error'], "Ви не можете змінити інший ресторан", response.data)

    def test_delete_not_existing_restaurant(self):
        url = reverse('restaurants-admin', kwargs={"pk": 31})

        response = self.client.delete(url, {}, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertEqual(response.data['error'], 'Такого ресторану не існує', response.data)

    def test_delete_restaurant_non_admin(self):
        url = reverse('restaurants-admin', kwargs={"pk": 1})

        response = self.client.delete(url, {}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_delete_restaurant_successfuly(self):
        url = reverse('restaurants-admin', kwargs={"pk": 1})

        response = self.client.delete(url, {}, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)