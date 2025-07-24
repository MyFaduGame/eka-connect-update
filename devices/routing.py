# mqtt_processor/routing.py
from django.urls import re_path
from devices.consumers import LiveDataConsumer

websocket_urlpatterns = [
    re_path(r'ws/live-data/$', LiveDataConsumer.as_asgi()),
]
