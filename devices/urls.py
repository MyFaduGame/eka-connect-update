# urls.py
from django.urls import path
from .views import (
    DeviceAPIView,
    DeviceDataListView
)

urlpatterns = [
    path('', DeviceAPIView.as_view(), name='device-list-create'),
    path('<int:pk>', DeviceAPIView.as_view(), name='device-update-delete'),
    path('detail', DeviceDataListView.as_view(), name='device-data-list'),
]
