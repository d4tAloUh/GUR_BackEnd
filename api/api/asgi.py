"""
ASGI config for api project.

It exposes the ASGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/3.1/howto/deployment/asgi/
"""

import os
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.security.websocket import AllowedHostsOriginValidator
from django.core.asgi import get_asgi_application
from django.urls import re_path
from gur.consumers.courier import CourierConsumer
from gur.consumers.user import UserConsumer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.settings')

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": AllowedHostsOriginValidator(
        URLRouter([
            re_path(r"^socket/courier$", CourierConsumer.as_asgi()),
            re_path(r"^socket/user$", UserConsumer.as_asgi()),
        ])
    ),
})
