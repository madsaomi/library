import json
import logging

from channels.db import database_sync_to_async
from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = self.scope.get('user')
        if self.user.is_anonymous:
            await self.close()
            return

        self.group_name = f'notifications_{self.user.id}'
        await self.channel_layer.group_add(self.group_name, self.channel_name)
        await self.accept()

        unread_count = await self.get_unread_count()
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'unread_count',
                    'unread_count': unread_count,
                }
            )
        )

    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(self.group_name, self.channel_name)

    async def receive(self, text_data):
        pass

    async def send_notification(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'notification',
                    'id': event['id'],
                    'title': event['title'],
                    'body': event['body'],
                    'url': event['url'],
                    'unread_count': event['unread_count'],
                }
            )
        )

    async def unread_count_update(self, event):
        await self.send(
            text_data=json.dumps(
                {
                    'type': 'unread_count',
                    'unread_count': event['unread_count'],
                }
            )
        )

    @database_sync_to_async
    def get_unread_count(self):
        from .models import Notification

        return Notification.objects.filter(user=self.user, is_read=False).count()
