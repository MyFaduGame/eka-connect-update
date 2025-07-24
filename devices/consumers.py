import json
from channels.generic.websocket import AsyncWebsocketConsumer
from asgiref.sync import sync_to_async
from rest_framework import status
from rest_framework.response import Response

class LiveDataConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        await self.accept()
        await self.send(text_data=json.dumps({"message": "Connection established."}))

        while True:
            data = await self.get_latest_data()
            await self.send(text_data=json.dumps(data))
            await self.sleep(10)

    async def disconnect(self, close_code):
        print("WebSocket disconnected:", close_code)

    @sync_to_async
    def get_latest_data(self):
        from devices.models import DeviceData
        from devices.serializers import LiveDataSerializer
        latest = DeviceData.objects.last()
        data = LiveDataSerializer(latest)
        return data.data or {"message":"No Data Found"}
    
    async def sleep(self, seconds):
        import asyncio
        await asyncio.sleep(seconds)
