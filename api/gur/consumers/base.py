from channels.generic.websocket import AsyncJsonWebsocketConsumer
import jwt
from django.conf import settings
from rest_framework_simplejwt.tokens import UntypedToken


class BaseConsumer(AsyncJsonWebsocketConsumer):

    async def connect(self):
        await self.accept()

    async def disconnect(self, code):
        await self.close(code)

    async def get_user_id(self, token):
        token = UntypedToken(token)
        user_id = jwt.decode(
            jwt=token.token,
            key=settings.SECRET_KEY,
            algorithms=["HS256"]
        )["user_id"]
        return user_id
