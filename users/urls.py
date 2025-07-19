from django.urls import path
from users.views import *

urlpatterns = [
    path('assign-devices/', AssignDevicesToUser.as_view(), name='assign-devices'),
    path('latest-device-data/', UserLatestDeviceDataView.as_view(), name='latest-device-data'),
    path('change-password/', FirstTimePasswordChangeView.as_view(), name='change-password'),
]
