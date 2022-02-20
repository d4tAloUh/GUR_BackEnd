from api.gur.models import RestaurantAdmin, UserAccount


def pass_test(request):
    try:
        if not RestaurantAdmin.objects.filter(
                user_id=UserAccount.objects.get(user_id=request.user.id)).exists() \
                and not request.user.is_superuser:
            return False
        return True
    except UserAccount.DoesNotExist:
        return False
