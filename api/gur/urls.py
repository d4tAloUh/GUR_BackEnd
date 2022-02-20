from django.urls import path
from rest_framework_simplejwt import views as jwt_views

from api.gur.views.account import (
    UserRegistrationApiView, UserAccountApiView,
    CourierAccountApiView
)
from api.gur.views.courier import (
    CourierLastOrderApiView, CourierFreeOrderApiView,
    CourierUpdateFreeOrderApiView, CourierLocationUpdateApiView,
    CourierOrderListApiView, CourierOrderApiView
)
from api.gur.views.dishes import (
    DishApiView, DishExactApiView
)
from api.gur.views.order import (
    OrderApiView, OrderCreationApiView,
    OrderSameCreationApiView, UserOrderListApiView,
    UserOrderApiView, OrderDishCreateApiView,
    OrderDishApiView, OrderDishClearApiView,
    OrderStatusApiView
)
from api.gur.views.restaurant import (
    RestaurantApiView, RestaurantAdminApiView
)

urlpatterns = [
    # Restaurant api
    path(r'restaurants', RestaurantApiView.as_view(), name='restaurants'),
    path(r'restaurants/<int:pk>', RestaurantAdminApiView.as_view(), name='restaurants-admin'),

    path(r'restaurant-dishes/<int:pk>', DishApiView.as_view(), name='restaurant-dishes'),
    path(r'restaurant-dishes-exact/<int:pk>', DishExactApiView.as_view(), name='restaurant-dishes-exact'),

    path(r'orders', OrderApiView.as_view(), name='orders-retrieve'),
    path(r'orders/<int:pk>', OrderCreationApiView.as_view(), name='orders-create'),
    path(r'orders/recreate/<int:pk>', OrderSameCreationApiView.as_view(), name='orders-recreate'),

    path(r'user-orders', UserOrderListApiView.as_view(), name='user-orders'),
    path(r'user-orders/<int:pk>', UserOrderApiView.as_view(), name='user-orders-key'),

    path(r'order-dishes', OrderDishCreateApiView.as_view(), name='order-dish-create'),
    path(r'order-dishes/<int:order_pk>', OrderDishApiView.as_view(), name='order-dish-detail'),
    path(r'order-dishes/clear/<int:order_pk>', OrderDishClearApiView.as_view(), name='order-dish-clear'),

    path(r'order-statuses/<int:pk>', OrderStatusApiView.as_view(), name='order-statuses'),

    path(r'register', UserRegistrationApiView.as_view(), name='register'),
    path(r'user-profile', UserAccountApiView.as_view(), name='user-profile'),
    path(r'courier-profile', CourierAccountApiView.as_view(), name='courier-profile'),

    path(r'courier/orders/current', CourierLastOrderApiView.as_view(), name='courier-current-order'),
    path(r'courier/orders/free', CourierFreeOrderApiView.as_view(), name='courier-free-orders'),
    path(r'courier/orders/free/<int:pk>', CourierUpdateFreeOrderApiView.as_view(), name='courier-free-order-update'),
    path(r'courier/location/<int:order_pk>', CourierLocationUpdateApiView.as_view(), name='courier-location'),

    path(r'courier-orders', CourierOrderListApiView.as_view(), name='courier-orders'),
    path(r'courier-orders/<int:pk>', CourierOrderApiView.as_view(), name='courier-orders-key'),
    # Token
    path(r'token', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path(r'token/refresh', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
]
