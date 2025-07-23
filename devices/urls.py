# urls.py
from django.urls import path
from .views import (
    DeviceAPIView,
    DeviceDataListView,
    ReplicaDevicesAPIView,
    FirebaseNotificationAPIView  
)

urlpatterns = [
    path('', DeviceAPIView.as_view(), name='device-list-create'),
    path('<int:pk>', DeviceAPIView.as_view(), name='device-update-delete'),
    path('detail', DeviceDataListView.as_view(), name='device-data-list'),
    path('replica-devices/', ReplicaDevicesAPIView.as_view(), name='replica-devices-list'),
    path('send-firebase-notification/', FirebaseNotificationAPIView.as_view(), name='send-firebase-notification'),
   

]
