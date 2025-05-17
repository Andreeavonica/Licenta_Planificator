from channels.generic.websocket import AsyncWebsocketConsumer
import json

class BoardConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.channel_layer.group_add("live_board", self.channel_name)
        await self.accept()

    async def disconnect(self, close_code):
        await self.channel_layer.group_discard("live_board", self.channel_name)

    async def send_status_update(self, event):
        await self.send(text_data=json.dumps({
            "event_id": event["event_id"],
            "status_live": event["status_live"],
        }))
