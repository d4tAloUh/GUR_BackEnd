from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import CustomUser, UserAccount, CourierAccount
from rest_framework_simplejwt.tokens import AccessToken


class AccountViewTests(APITestCase):

    def setUp(self):
        self.email = 'test_user@gmail.com'
        self.password = 'password'
        user = CustomUser.objects.create_user(email='bla@gmail.com', password=self.password)
        UserAccount.objects.create(user=user)
        CourierAccount.objects.create(user=user)
        self.token = AccessToken.for_user(user)
        self.header = {'HTTP_AUTHORIZATION': f'Bearer {self.token}'}

    def test_register_user_without_email(self):
        # Get URL path of register route
        url = reverse('register')

        # post data to register client
        response = self.client.post(url, {
            'password': self.password
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['email'][0], 'This field is required.', response.data)

    def test_register_user_without_password(self):
        # Get URL path of register route
        url = reverse('register')

        # post data to register client
        response = self.client.post(url, {
            'email': self.email
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['password'][0], 'This field is required.', response.data)

    def test_register_user_successful(self):
        # Get URL path of register route
        url = reverse('register')

        # post data to register client
        response = self.client.post(url, {
            'password': self.password,
            'email': self.email
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)
        self.assertEqual(response.data['email'], self.email, response.data)

    def test_register_user_which_already_exists(self):
        # Get URL path of register route
        url = reverse('register')

        # post data to register client
        response = self.client.post(url, {
            'password': self.password,
            'email': 'bla@gmail.com'
        }, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['email'][0], 'Користувач з таким емейлом уже існує.', response.data)

    def test_retrieve_user_account(self):
        url = reverse('user-profile')

        response = self.client.get(url, {}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['first_name'], '', response.data['first_name'])
        self.assertEqual(response.data['admin'], False, response.data['admin'])
        self.assertEqual(response.data['partial_admin'], False, response.data['partial_admin'])

    def test_update_user_account(self):
        url = reverse('user-profile')

        response = self.client.put(url, {'first_name': 'Igor'}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['first_name'], 'Igor', response.data['first_name'])
        self.assertEqual(response.data['tel_num'], '', response.data['tel_num'])

    def test_retrieve_courier_account(self):
        url = reverse('courier-profile')

        response = self.client.get(url, {}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['first_name'], '', response.data['first_name'])
        self.assertEqual(response.data['is_courier'], True, response.data['is_courier'])

    def test_update_courier_account(self):
        url = reverse('courier-profile')

        response = self.client.put(url, {'first_name': 'Igor'}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['first_name'], 'Igor', response.data['first_name'])
        self.assertEqual(response.data['tel_num'], '', response.data['tel_num'])