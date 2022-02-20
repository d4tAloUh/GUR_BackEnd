from datetime import datetime

from django.contrib.auth import get_user_model
from django.contrib.gis.geos import GEOSGeometry
from django.utils import timezone
from django.contrib.auth.base_user import BaseUserManager
from django.contrib.auth.models import AbstractUser
from django.db import models
from django.core.validators import MinValueValidator, RegexValidator
from django.conf import settings
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
    email = models.EmailField(_('email address'), unique=True, error_messages={
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
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    first_name = models.CharField(max_length=70, blank=True, null=False)
    tel_num = models.CharField(max_length=12, blank=True, null=False,
                               validators=[RegexValidator(
                                   regex=r'^[0-9]*$',
                                   message=_('Будь ласка, вкажіть правильний номер телефону.'))]
                               )

    class Meta:
        abstract = True


class CourierAccount(AccountInfo):
    class Meta:
        verbose_name = "Courier account"
        verbose_name_plural = "Courier accounts"

    courier_id = models.AutoField(primary_key=True)

    def __str__(self):
        return f"{self.courier_id} - {self.first_name}(+{self.tel_num})"


class UserAccount(AccountInfo):
    class Meta:
        verbose_name = "User account"
        verbose_name_plural = "User accounts"

    account_id = models.AutoField(primary_key=True)

    def __str__(self):
        return f"{self.account_id} - {self.first_name}(+{self.tel_num})"


class RestaurantManager(models.Manager):
    def get_restaurants_to_position(self, longitude, latitude):
        user_location = GEOSGeometry(
            f'POINT({longitude} {latitude})',
            srid=4326
        )
        return self.get_queryset().filter(
            location__distance_lte=(user_location, settings.POSSIBLE_USER_DISTANCE)
        )


class Restaurant(models.Model):
    class Meta:
        verbose_name = "Restaurant"
        verbose_name_plural = "Restaurants"

    rest_id = models.AutoField(primary_key=True)
    rest_photo = models.TextField(null=True, blank=True, max_length=16383)
    rest_address = models.CharField(null=False, max_length=250, blank=False)
    name = models.CharField(null=False, max_length=150)
    open_from = models.TimeField(auto_now=False, null=True, blank=True)
    open_to = models.TimeField(auto_now=False, null=True, blank=True)
    location = gis_models.PointField(geography=True)

    objects = RestaurantManager()

    def __str__(self):
        return f"{self.name}"

    @property
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
            user_id__user=user
        ).values_list('rest_id', flat=True)


class RestaurantAdmin(models.Model):
    class Meta:
        verbose_name = "Restaurant admin"
        verbose_name_plural = "Restaurant admins"

    user_id = models.ForeignKey(UserAccount, on_delete=models.CASCADE, null=False)
    rest_id = models.ForeignKey(Restaurant, on_delete=models.CASCADE, null=False)
    objects = RestaurantAdminManager()

    def __str__(self):
        return f"{self.user_id.first_name} : {self.rest_id.name}"


class Dish(models.Model):
    class Meta:
        verbose_name = "Dish"
        verbose_name_plural = "Dishes"

    dish_id = models.AutoField(primary_key=True)
    dish_photo = models.TextField(null=True, blank=True, max_length=16383)
    restaurant_id = models.ForeignKey(Restaurant, on_delete=models.CASCADE)
    name = models.CharField(null=False, max_length=150)
    description = models.CharField(blank=True, null=True, max_length=500)
    price = models.IntegerField(validators=[MinValueValidator(1), ])
    gramme = models.IntegerField(validators=[MinValueValidator(1), ])

    def __str__(self):
        return f"{self.name}"


class Order(models.Model):
    class Meta:
        verbose_name = "Order"
        verbose_name_plural = "Orders"

    order_id = models.AutoField(primary_key=True)
    user_id = models.ForeignKey(UserAccount, on_delete=models.DO_NOTHING, null=False)
    courier_id = models.ForeignKey(CourierAccount, on_delete=models.DO_NOTHING, null=True, blank=True)
    summary = models.IntegerField(validators=[MinValueValidator(0), ], default=0)
    delivery_address = models.CharField(null=True, max_length=250, blank=False)
    delivery_location = gis_models.PointField(geography=True, null=True, blank=True)
    created_tm = models.DateTimeField(default=timezone.now)
    order_details = models.CharField(null=True, max_length=250, blank=True)

    def __str__(self):
        return f"{self.order_id} - {self.user_id.tel_num}"


class OrderDish(models.Model):
    class Meta:
        verbose_name = "Ordered dish"
        verbose_name_plural = "Ordered dishes"
        unique_together = (('order_id', 'dish_id'),)

    order_id = models.ForeignKey(Order, on_delete=models.CASCADE)
    dish_id = models.ForeignKey(Dish, on_delete=models.CASCADE)
    quantity = models.IntegerField(validators=[MinValueValidator(1), ], default=1)

    def __str__(self):
        return f"{self.order_id} - {self.quantity} {self.dish_id.name}"


class OrderStatus(models.Model):
    class Meta:
        verbose_name = "Order status"
        verbose_name_plural = "Order statuses"
        unique_together = (('order_id', 'status'),)
        ordering = ('timestamp', 'order_id',)

    OPEN = "O"
    PREPARING = "P"
    DELIVERING = "D"
    CANCELLED = "C"
    DELIVERED = "F"
    NON_OPEN_STATUSES = [PREPARING, DELIVERING, CANCELLED, DELIVERED]
    FINISHED_STATUSES = [CANCELLED, DELIVERED]
    COURIER_ORDER_STATUSES = [DELIVERING] + FINISHED_STATUSES

    status_enum = [(OPEN, "Opened order"),
                   (PREPARING, "Preparing order"),
                   (DELIVERING, "Delivering order"),
                   (CANCELLED, "Canceled order"),
                   (DELIVERED, "Delivered order")]
    order_id = models.ForeignKey(Order, on_delete=models.CASCADE)
    status = models.CharField(max_length=1, choices=status_enum)
    timestamp = models.DateTimeField(default=timezone.now)

    def __str__(self):
        return f"{self.order_id.order_id} - {self.status}"


class CourierLocation(models.Model):
    class Meta:
        verbose_name = "Courier location"
        verbose_name_plural = "Courier locations"

    id = models.AutoField(primary_key=True)
    courier = models.ForeignKey(CourierAccount, on_delete=models.DO_NOTHING, null=False)
    date = models.DateTimeField(null=False, blank=False, default=timezone.now)
    location = gis_models.PointField(geography=True, null=True, blank=True)

    def __str__(self):
        return f"{self.courier.user} - {self.location}"
