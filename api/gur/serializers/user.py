from rest_framework import serializers
from ..models import UserAccount, CourierAccount, RestaurantAdmin
from django.contrib.auth import get_user_model


class UserAccountSerializer(serializers.ModelSerializer):
    admin = serializers.SerializerMethodField()
    partial_admin = serializers.SerializerMethodField()

    class Meta:
        model = UserAccount
        fields = ['first_name', 'tel_num', 'admin', 'partial_admin']
        extra_kwargs = {
            'first_name': {'error_messages': {
                'blank': 'Необхідно вказати ім`я.'}},
            'tel_num': {'error_messages': {
                'blank': 'Необхідно вказати номер телефону.'}}
        }

    def get_admin(self, instance):
        return instance.user.is_superuser

    def get_partial_admin(self, instance):
        return RestaurantAdmin.objects.filter(user_id__user_id=instance.user.id).exists()


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = get_user_model()
        fields = (
            'id',
            'password',
            'email',
        )
        extra_kwargs = {
            'password': {'write_only': True, 'error_messages': {
                                                'blank': 'Необхідно вказати пароль.',
                                                'invalid': 'Неправильно вказаний пароль.'}},
            'email': {'error_messages': {
                        'blank': 'Необхідно вказати емейл.',
                        'unique': 'Користувач з таким емейлом уже існує.',
                        'invalid': 'Будь ласка, вкажіть валідний емейл.'}}
        }

    def create(self, validated_data):
        user = get_user_model().objects.create_user(**validated_data)
        return user

    def update(self, instance, validated_data):
        if 'password' in validated_data:
            password = validated_data.pop('password')
            instance.set_password(password)
        return super(UserSerializer, self).update(instance, validated_data)


class CourierAccountSerializer(serializers.ModelSerializer):
    is_courier = serializers.SerializerMethodField()

    def get_is_courier(self, instance):
        return True

    class Meta:
        model = CourierAccount
        fields = ['first_name', 'tel_num', 'is_courier']
        extra_kwargs = {
            'first_name': {'error_messages': {
                'blank': 'Необхідно вказати ім`я.'}},
            'tel_num': {'error_messages': {
                'blank': 'Необхідно вказати номер телефону.'}}
        }


class UserForCourierAccountSerializer(serializers.ModelSerializer):
    class Meta:
        model = UserAccount
        fields = ['first_name', 'tel_num']
        read_only_fields = ['first_name', 'tel_num']
