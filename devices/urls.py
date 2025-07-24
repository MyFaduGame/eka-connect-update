# urls.py
from django.urls import path
from .views import (
    AlertAPIView,
    DeviceAPIView,
    DeviceDataListView,
    FaultAlertAPIView
)

urlpatterns = [
    path('', DeviceAPIView.as_view(), name='device-list-create'),
    path('<int:pk>', DeviceAPIView.as_view(), name='device-update-delete'),
    path('detail', DeviceDataListView.as_view(), name='device-data-list'),
    path('alerts', AlertAPIView.as_view(), name='alert-list'),
    path('fault', FaultAlertAPIView.as_view(), name='fault-alerts-api'),
]
