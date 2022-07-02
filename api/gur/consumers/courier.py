from channels.db import database_sync_to_async

from ..models.models import CourierAccount

from .base import BaseConsumer


class CourierConsumer(BaseConsumer):

    @database_sync_to_async
    def should_accept_connection(self, user_id):
        return CourierAccount.objects.filter(id=user_id).exists()

    async def receive_json(self, content, **kwargs):
        command = content.get("command")
        if command == "connect_to_order_queue":
            user_id = await self.get_user_id(content.get("token"))
            should_accept = await self.should_accept_connection(user_id)
            if should_accept:
                await self.channel_layer.group_add(
                    f"courier_queue",
                    self.channel_name
                )
                self.groups.append(f"courier_queue")
            else:
                await self.close()

    async def event_neworder(self, event):
        await self.send_json(
            {
                'type': 'event.neworder',
                'content': event['content']
            }
        )

    async def event_ordertaken(self, event):
        await self.send_json(
            {
                'type': 'event.ordertaken',
                'content': event['content']
            }
        )