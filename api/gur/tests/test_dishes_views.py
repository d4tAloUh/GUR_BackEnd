from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from ..models import CustomUser, UserAccount, Dish, RestaurantAdmin
from rest_framework_simplejwt.tokens import AccessToken


class DishesViewTests(APITestCase):
    fixtures = ['restaurant_dishes.json']

    def setUp(self):
        user = CustomUser.objects.create_user(email='bla@gmail.com', password='password')
        UserAccount.objects.create(user=user)
        self.header = self.get_header_for_user(user)

        admin_user = CustomUser.objects.create_superuser(email='bla1@gmail.com', password='password')
        UserAccount.objects.create(user=admin_user)
        self.admin_header = self.get_header_for_user(admin_user)

        part_admin = CustomUser.objects.create_user(email='bla12@gmail.com', password='password')
        part_admin_account = UserAccount.objects.create(user=part_admin)
        RestaurantAdmin.objects.create(rest_id_id=2, user_id=part_admin_account)
        self.part_admin_header = self.get_header_for_user(part_admin)

    def get_header_for_user(self, user):
        token = AccessToken.for_user(user)
        return {'HTTP_AUTHORIZATION': f'Bearer {token}'}

    def test_get_all_dishes_from_existing_restaurant(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 1})

        response = self.client.get(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(len(response.data['dishes']), 2, response.data)
        self.assertEqual(response.data['restaurant']['rest_id'], 1, response.data)

    def test_get_all_dishes_from_non_existing_restaurant(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 31})

        response = self.client.get(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_create_new_dish_non_admin(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 2})

        response = self.client.post(url, {}, **self.header, format='json')

        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_create_new_dish_admin_non_existing_restaurant(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 31})

        response = self.client.post(url, {
            "dish_photo": "https://ik.imagekit.io/alouh/Restaurants/BankaBar/banka__Tqb8LtHK1xh.jpg",
            "restaurant_id": 31,
            "name": "Наливка \"Груша\"",
            "description": "",
            "price": 3200,
            "gramme": 130
        }, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)

    def test_create_new_dish_admin(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 1})

        response = self.client.post(url, {
            "dish_photo": "https://ik.imagekit.io/alouh/Restaurants/BankaBar/banka__Tqb8LtHK1xh.jpg",
            "restaurant_id": 1,
            "name": "Наливка \"Груша\"",
            "description": "",
            "price": 3200,
            "gramme": 130
        }, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_201_CREATED, response.content)

    def test_create_new_dish_admin_without_name(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 1})

        response = self.client.post(url, {
            "dish_photo": "https://ik.imagekit.io/alouh/Restaurants/BankaBar/banka__Tqb8LtHK1xh.jpg",
            "restaurant_id": 1,
            "description": "",
            "price": 3200,
            "gramme": 130
        }, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['name'][0], 'This field is required.', response.content)

    def test_create_new_dish_admin_without_price(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 1})

        response = self.client.post(url, {
            "dish_photo": "https://ik.imagekit.io/alouh/Restaurants/BankaBar/banka__Tqb8LtHK1xh.jpg",
            "restaurant_id": 1,
            "name": "Наливка \"Груша\"",
            "description": "",
            "gramme": 130
        }, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['price'][0], 'This field is required.', response.content)

    def test_create_new_dish_admin_without_gramme(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 1})

        response = self.client.post(url, {
            "dish_photo": "https://ik.imagekit.io/alouh/Restaurants/BankaBar/banka__Tqb8LtHK1xh.jpg",
            "restaurant_id": 1,
            "name": "Наливка \"Груша\"",
            "description": "",
            "price": 3200,
        }, **self.admin_header, format='json')

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['gramme'][0], 'This field is required.', response.content)

    def test_create_new_dish_admin_with_wrong_gramme(self):
        url = reverse('restaurant-dishes', kwargs={'pk': 1})

        response = self.client.post(url, {
            "dish_photo": "https://ik.imagekit.io/alouh/Restaurants/BankaBar/banka__Tqb8LtHK1xh.jpg",
            "restaurant_id": 1,
            "name": "Наливка \"Груша\"",
            "description": "",
            "price": 3200,
            "gramme": "bla"
        }, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST, response.content)
        self.assertEqual(response.data['gramme'][0], 'A valid integer is required.', response.content)

    def test_retrieve_exact_dish_non_admin(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        response = self.client.get(url, {}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_retrieve_exact_dish_wrong_pk(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 51})
        response = self.client.get(url, {}, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertEqual(response.data['error'], "Такої страви не існує", response.data)

    def test_retrieve_exact_dish(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        response = self.client.get(url, {}, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        self.assertEqual(response.data['dish']['dish_id'], 1, response.data)

    def test_update_existing_dish(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        prev_dish = Dish.objects.get(dish_id=1)
        response = self.client.put(url, {
            "name": "Наливка \"Груша\"",
            "price": 3900,
            "gramme": prev_dish.gramme
        }, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_200_OK, response.content)
        new_dish = Dish.objects.get(dish_id=1)
        self.assertEqual(new_dish.name, "Наливка \"Груша\"", new_dish.name)
        self.assertEqual(new_dish.dish_photo, prev_dish.dish_photo, new_dish.dish_photo)
        self.assertEqual(new_dish.price, 3900, new_dish.price)
        self.assertEqual(new_dish.gramme, prev_dish.gramme, new_dish.price)

    def test_update_dish_non_admin(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        response = self.client.put(url, {
            "name": "Наливка \"Груша\"",
            "price": 3900,
        }, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_update_non_existing_dish(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 13})
        response = self.client.put(url, {
            "name": "Наливка \"Груша\"",
            "price": 3900,
            "gramme": 120
        }, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertEqual(response.data['error'], "Такої страви не існує", response.content)

    def test_update_dish_from_other_restaurant(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        response = self.client.put(url, {
            "name": "Наливка \"Груша\"",
            "price": 3900,
            "gramme": 120
        }, **self.part_admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)
        self.assertEqual(response.data['error'], "Ви не можете змінити страви іншого ресторану", response.content)

    def test_destroy_dish_non_admin(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        response = self.client.delete(url, {}, **self.header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)

    def test_destroy_existing_dish(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        response = self.client.delete(url, {}, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_204_NO_CONTENT, response.content)

    def test_destroy_non_existing_dish(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 31})
        response = self.client.delete(url, {}, **self.admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_404_NOT_FOUND, response.content)
        self.assertEqual(response.data['error'], "Такої страви не існує", response.content)

    def test_destroy_dish_from_other_restaurant(self):
        url = reverse('restaurant-dishes-exact', kwargs={'pk': 1})
        response = self.client.delete(url, {}, **self.part_admin_header, format='json')
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN, response.content)
        self.assertEqual(response.data['error'], "Ви не можете видалити страви іншого ресторану", response.content)