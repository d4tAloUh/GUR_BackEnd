from django.urls import re_path
from rest_framework_simplejwt import views as jwt_views

from .views.account import (
    UserRegistrationApiView, UserAccountApiView,
    CourierAccountApiView
)
from .views.courier import (
    CourierCurrentOrderApiView, CourierFreeOrderListApiView,
    CourierUpdateFreeOrderApiView, CourierLocationUpdateApiView,
    CourierOrderListApiView, CourierRetrieveOrderApiView
)
from .views.dishes import (
    DishApiView, DishExactApiView
)
from .views.order import (
    OrderApiView, OrderCreationApiView,
    OrderRecreationApiView, UserOrderListApiView,
    UserOrderApiView, OrderDishCreateApiView,
    OrderDishApiView, OrderDishClearApiView,
    OrderStatusApiView
)
from .views.restaurant import (
    RestaurantApiView, RestaurantAdminApiView
)

urlpatterns = [
    # Restaurant api
    re_path(
        r'restaurants$',
        RestaurantApiView.as_view(),
        name='restaurants'
    ),
    re_path(
        r'restaurants/(?P<pk>(\d+))$',
        RestaurantAdminApiView.as_view(),
        name='restaurants-admin'
    ),

    re_path(
        r'restaurants/(?P<pk>(\d+))/dishes$',
        DishApiView.as_view(),
        name='restaurant-dishes'
    ),
    re_path(
        r'restaurants/(?P<restaurant_id>(\d+))/dishes/(?P<pk>(\d+))$',
        DishExactApiView.as_view(),
        name='restaurant-dishes-exact'
    ),

    re_path(
        r'orders$',
        OrderApiView.as_view(),
        name='orders-retrieve'
    ),
    re_path(
        r'orders/(?P<pk>(\d+))$',
        OrderCreationApiView.as_view(),
        name='orders-create'
    ),
    re_path(
        r'orders/(?P<pk>(\d+))/recreate$',
        OrderRecreationApiView.as_view(),
        name='orders-recreate'
    ),

    re_path(
        r'user-orders$',
        UserOrderListApiView.as_view(),
        name='user-orders'
    ),
    re_path(
        r'user-orders/(?P<pk>(\d+))$',
        UserOrderApiView.as_view(),
        name='user-orders-key'
    ),

    re_path(
        r'order-dishes$',
        OrderDishCreateApiView.as_view(),
        name='order-dish-create'
    ),
    re_path(
        r'order-dishes/(?P<pk>(\d+))$',
        OrderDishApiView.as_view(),
        name='order-dish-detail'
    ),
    re_path(
        r'order-dishes/(?P<pk>(\d+))/clear$',
        OrderDishClearApiView.as_view(),
        name='order-dish-clear'
    ),

    re_path(
        r'order-statuses/(?P<order_id>(\d+))$',
        OrderStatusApiView.as_view(),
        name='order-statuses'
    ),

    re_path(r'register$', UserRegistrationApiView.as_view(), name='register'),
    re_path(r'user-profile$', UserAccountApiView.as_view(), name='user-profile'),
    re_path(r'courier-profile$', CourierAccountApiView.as_view(), name='courier-profile'),

    re_path(
        r'courier/orders/current$',
        CourierCurrentOrderApiView.as_view(),
        name='courier-current-order'
    ),
    re_path(
        r'courier/orders/free/(?P<pk>(\d+))$',
        CourierUpdateFreeOrderApiView.as_view(),
        name='courier-free-order-update'
    ),
    re_path(
        r'courier/orders/free$',
        CourierFreeOrderListApiView.as_view(),
        name='courier-free-orders'
    ),

    re_path(
        r'courier/location/(?P<order_id>(\d+))',
        CourierLocationUpdateApiView.as_view(),
        name='courier-location'
    ),

    re_path(r'courier-orders$', CourierOrderListApiView.as_view(), name='courier-orders'),
    re_path(
        r'courier-orders/(?P<pk>(\d+))$',
        CourierRetrieveOrderApiView.as_view(),
        name='courier-orders-key'
    ),

    # Token
    re_path(r'token$', jwt_views.TokenObtainPairView.as_view(), name='token_obtain_pair'),
    re_path(r'token/refresh$', jwt_views.TokenRefreshView.as_view(), name='token_refresh'),
]
