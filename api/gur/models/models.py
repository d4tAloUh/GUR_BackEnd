from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.conf import settings
from django.utils.functional import cached_property
from django.utils.translation import gettext_lazy as _
import django.contrib.gis.db.models as gis_models


class CustomUserManager(BaseUserManager):
    def create_user(self, email, password, **extra_fields):
        if not email:
            raise ValueError(_('Необхідно вказати електронну пошту'))
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save()
        return user

    def create_superuser(self, email, password, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('is_active', True)
        if extra_fields.get('is_staff') is not True:
            raise ValueError(_('Superuser must have is_staff=True.'))
        if extra_fields.get('is_superuser') is not True:
            raise ValueError(_('Superuser must have is_superuser=True.'))
        return self.create_user(email, password, **extra_fields)


class CustomUser(AbstractUser):
    username = None
    first_name = None
    last_name = None
    email = models.EmailField(
        verbose_name=_('Email address'),
        unique=True,
        error_messages={
            'unique': _("Користувач з таким емейлом уже існує."),
            'blank': _("Необхідно вказати емейл."),
            'invalid': _("Будь ласка, вкажіть валідний емейл.")
        }, )
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    objects = CustomUserManager()

    def __str__(self):
        return self.email


User = get_user_model()


class AccountInfo(models.Model):
    user = models.ForeignKey(
        User,
        verbose_name=_('factory'),
        related_name='accounts',
        on_delete=models.CASCADE
    )
    first_name = models.CharField(
        verbose_name=_('First name'),
        max_length=70,
        blank=True, null=True
    )
    tel_num = models.CharField(
        verbose_name=_('Telephone number'),
        max_length=12,
        blank=True, null=True,
        validators=[
            RegexValidator(
                regex=r'^[0-9]*$',
                message=_('Будь ласка, вкажіть правильний номер телефону.')
            )
        ]
    )

    class Meta:
        abstract = True


class CourierAccount(AccountInfo):
    class Meta:
        verbose_name = "Courier account"
        verbose_name_plural = "Courier accounts"

    def __str__(self):
        return f"{self.id} - {self.first_name}(+{self.tel_num})"


class UserAccount(AccountInfo):
    class Meta:
        verbose_name = "User account"
        verbose_name_plural = "User accounts"

    def __str__(self):
        return f"{self.id} - {self.first_name}(+{self.tel_num})"


class RestaurantManager(models.Manager):
    def get_restaurants_to_position(self, longitude, latitude):
        user_location = GEOSGeometry(
            f'POINT({longitude} {latitude})',
            srid=4326
        )
        return self.get_queryset().filter(
            location__distance_lte=(
                user_location,
                settings.POSSIBLE_USER_DISTANCE
            )
        )


class Restaurant(models.Model):
    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"

    rest_photo = models.TextField(
        verbose_name=_('Restaurant photo'),
        null=True, blank=True,
        max_length=16383
    )
    rest_address = models.CharField(
        verbose_name=_('Restaurant address'),
        max_length=250
    )
    name = models.CharField(
        verbose_name=_('Restaurant name'),
        max_length=150
    )
    open_from = models.TimeField(
        verbose_name=_('Restaurant opening time'),
        null=True, blank=True
    )
    open_to = models.TimeField(
        verbose_name=_('Restaurant closing time'),
        null=True, blank=True
    )
    location = gis_models.PointField(
        verbose_name=_('Restaurant location'),
        geography=True
    )

    objects = RestaurantManager()

    def __str__(self):
        return f"{self.name}"

    @cached_property
    def is_open(self):
        if self.open_from is not None and self.open_to is not None:
            now = datetime.now().time()
            if self.open_from > self.open_to:
                return not (self.open_from > now > self.open_to)
            else:
                return self.open_from < now < self.open_to
        return True


class RestaurantAdminManager(models.Manager):
    def get_admin_restaurant_ids(self, user):
        return self.get_queryset().filter(
            user_account__user=user
        ).values_list('id', flat=True)


class RestaurantAdmin(models.Model):
    class Meta:
        verbose_name = "Restaurant admin"
        verbose_name_plural = "Restaurant admins"

    user_account = models.ForeignKey(
        UserAccount,
        verbose_name=_('User'),
        related_name='restaurant_admins',
        on_delete=models.CASCADE
    )
    rest = models.ForeignKey(
        Restaurant,
        verbose_name=_('Restaurant'),
        related_name='restaurant_admins',
        on_delete=models.CASCADE
    )
    objects = RestaurantAdminManager()

    def __str__(self):
        return f"{self.user_account.first_name} : {self.rest.name}"


class Dish(models.Model):
    class Meta:
        verbose_name = "Dish"
        verbose_name_plural = "Dishes"

    dish_photo = models.TextField(
        verbose_name=_('Dish photo'),
        null=True, blank=True,
        max_length=16383
    )
    restaurant = models.ForeignKey(
        Restaurant,
        verbose_name=_('Restaurant'),
        related_name='dishes',
        on_delete=models.CASCADE
    )
    name = models.CharField(
        verbose_name=_('Name'),
        null=True, blank=True,
        max_length=150
    )
    description = models.CharField(
        verbose_name=_('Description'),
        blank=True, null=True,
        max_length=500
    )
    price = models.IntegerField(
        verbose_name=_('Price'),
        validators=[MinValueValidator(1), ]
    )
    gramme = models.IntegerField(
        verbose_name=_('Grammes'),
        validators=[MinValueValidator(1), ]
    )

    def __str__(self):
        return f"{self.name}"


class Order(models.Model):
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    user = models.ForeignKey(
        UserAccount,
        verbose_name=_('User'),
        related_name='orders',
        on_delete=models.PROTECT,
    )
    courier = models.ForeignKey(
        CourierAccount,
        verbose_name=_('Courier'),
        related_name='orders',
        on_delete=models.SET_NULL,
        null=True, blank=True
    )
    summary = models.IntegerField(
        verbose_name=_('Summary'),
        validators=[MinValueValidator(0), ],
        default=0
    )
    delivery_address = models.CharField(
        verbose_name=_('Delivery address'),
        null=True, blank=True,
        max_length=250,
    )
    delivery_location = gis_models.PointField(
        verbose_name=_('Delivery location'),
        geography=True,
        null=True, blank=True
    )
    created_at = models.DateTimeField(
        verbose_name=_('Created at'),
        default=timezone.now
    )
    order_details = models.CharField(
        verbose_name=_('Order details'),
        null=True, blank=True,
        max_length=250,
    )

    def __str__(self):
        return f"{self.id} - {self.user.tel_num}"


class OrderDish(models.Model):
    class Meta:
        verbose_name = "Ordered dish"
        verbose_name_plural = "Ordered dishes"
        unique_together = (('order', 'dish'),)

    order = models.ForeignKey(
        Order,
        verbose_name=_('Order'),
        related_name='order_dishes',
        on_delete=models.CASCADE
    )
    dish = models.ForeignKey(
        Dish,
        verbose_name=_('Dish'),
        related_name='order_dishes',
        on_delete=models.CASCADE
    )
    quantity = models.IntegerField(
        verbose_name=_('Quantity'),
        validators=[MinValueValidator(1), ],
        default=1
    )

    def __str__(self):
        return f"{self.order} - {self.quantity} {self.dish.name}"


class OrderStatus(models.Model):
    class Meta:
        verbose_name = "Order status"
        verbose_name_plural = "Order statuses"
        unique_together = (('order', 'status'),)
        ordering = ('timestamp', 'order',)

    OPEN = "O"
    PREPARING = "P"
    DELIVERING = "D"
    CANCELLED = "C"
    DELIVERED = "F"
    NON_OPEN_STATUSES = [PREPARING, DELIVERING, CANCELLED, DELIVERED]
    FINISHED_STATUSES = [CANCELLED, DELIVERED]
    COURIER_ORDER_STATUSES = [DELIVERING] + FINISHED_STATUSES

    STATUS_CHOICES = [
        (OPEN, "Opened order"),
        (PREPARING, "Preparing order"),
        (DELIVERING, "Delivering order"),
        (CANCELLED, "Canceled order"),
        (DELIVERED, "Delivered order")
    ]
    order = models.ForeignKey(
        Order,
        verbose_name=_('Order'),
        related_name='statuses',
        on_delete=models.CASCADE
    )
    status = models.CharField(
        max_length=1,
        verbose_name=_('Status'),
        choices=STATUS_CHOICES
    )
    created_at = models.DateTimeField(
        default=timezone.now
    )

    def __str__(self):
        return f"{self.order.id} - {self.status}"


class CourierLocation(models.Model):
    class Meta:
        verbose_name = "Courier location"
        verbose_name_plural = "Courier locations"

    courier = models.ForeignKey(
        CourierAccount,
        verbose_name=_('Courier'),
        related_name='locations',
        on_delete=models.CASCADE
    )
    created_at = models.DateTimeField(
        verbose_name=_('created_at'),
        default=timezone.now
    )
    location = gis_models.PointField(
        verbose_name=_('Location'),
        geography=True,
    )

    def __str__(self):
        return f"{self.courier.user} - {self.location}"
