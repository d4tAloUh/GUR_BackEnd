# Generated by Django 3.1.13 on 2022-02-03 16:35

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('gur', '0001_initial'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='courieraccount',
            options={'verbose_name': 'Courier account', 'verbose_name_plural': 'Courier accounts'},
        ),
        migrations.AlterModelOptions(
            name='courierlocation',
            options={'verbose_name': 'Courier location', 'verbose_name_plural': 'Courier locations'},
        ),
        migrations.AlterModelOptions(
            name='dish',
            options={'verbose_name': 'Dish', 'verbose_name_plural': 'Dishes'},
        ),
        migrations.AlterModelOptions(
            name='order',
            options={'verbose_name': 'Order', 'verbose_name_plural': 'Orders'},
        ),
        migrations.AlterModelOptions(
            name='orderdish',
            options={'verbose_name': 'Ordered dish', 'verbose_name_plural': 'Ordered dishes'},
        ),
        migrations.AlterModelOptions(
            name='orderstatus',
            options={'ordering': ('timestamp', 'order_id'), 'verbose_name': 'Order status', 'verbose_name_plural': 'Order statuses'},
        ),
        migrations.AlterModelOptions(
            name='restaurant',
            options={'verbose_name': 'Restaurant', 'verbose_name_plural': 'Restaurants'},
        ),
        migrations.AlterModelOptions(
            name='restaurantadmin',
            options={'verbose_name': 'Restaurant admin', 'verbose_name_plural': 'Restaurant admins'},
        ),
        migrations.AlterModelOptions(
            name='useraccount',
            options={'verbose_name': 'User account', 'verbose_name_plural': 'User accounts'},
        ),
    ]
