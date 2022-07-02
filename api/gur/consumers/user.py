from channels.db import database_sync_to_async
from ..models.models import Order
from .base import BaseConsumer


class UserConsumer(BaseConsumer):

    async def receive_json(self, content, **kwargs):
        command = content.get("command")
        if command == "connect_to_order_client":
            user_id = await self.get_user_id(
                content.get("token")
            )
            order_id = content.get("order_id")
            should_connect_to_order = await self.user_has_permission_to_order(
                user_id, order_id
            )
            if should_connect_to_order:
                await self.channel_layer.group_add(
                    f"order_{order_id}",
                    self.channel_name
                )
                self.groups.append(f"order_{order_id}")
            else:
                await self.close()

    async def event_location(self, event):
        await self.send_json(
            {
                'type': 'event.location',
                'content': event['content']
            }
        )

    async def event_orderstatus(self, event):
        await self.send_json(
            {
                'type': 'event.orderstatus',
                'content': event['content']
            }
        )

    @database_sync_to_async
    def user_has_permission_to_order(self, user_id, order_id):
        return Order.objects.filter(
            id=order_id,
            user__id=user_id
        ).exists()
