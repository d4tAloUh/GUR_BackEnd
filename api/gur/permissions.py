from rest_framework.permissions import BasePermission

from api.gur.models import RestaurantAdmin, CourierAccount


class IsAdmin(BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return request.user.is_superuser


class IsRestaurantAdmin(BasePermission):

    def has_object_permission(self, request, view, obj):
        if not request.user or not request.user.is_authenticated:
            return False
        return RestaurantAdmin.objects.filter(
            user__user=request.user,
            rest=obj
        ).exists() or request.user.is_superuser


class IsCourier(BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False
        return CourierAccount.objects.filter(user=request.user).exists()


class PermissionsRequired(BasePermission):

    def has_permission(self, request, view):
        if not request.user or not request.user.is_authenticated:
            return False

        required_permissions = getattr(view, 'permissions', [])
        required_permissions = required_permissions + getattr(
            view, 'permissions_' + str(request.method.lower()), []
        )
        return request.user.has_perms(required_permissions)
