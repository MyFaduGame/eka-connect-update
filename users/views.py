from rest_framework import generics, permissions, status
from rest_framework.views import APIView
from rest_framework.response import Response
from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.utils.timezone import now
from django.db.models import Max

from users.models import  UserDeviceAssignment
from devices.models import Device, DeviceData
from users.serializers import *

User = get_user_model()

class AssignDevicesToUser(APIView):
    permission_classes = [permissions.IsAdminUser]

    def post(self, request):
        serializer = AssignDeviceSerializer(data=request.data)
        if serializer.is_valid():
            user = User.objects.get(pk=serializer.validated_data['user_id'])
            for device_id in serializer.validated_data['device_ids']:
                device = Device.objects.get(pk=device_id)
                UserDeviceAssignment.objects.get_or_create(user=user, device=device)
            return Response({"message": "Devices assigned successfully."})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserLatestDeviceDataView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        assigned_devices = UserDeviceAssignment.objects.filter(user=request.user).values_list('device_id', flat=True)
        latest_entries = []

        for device_id in assigned_devices:
            latest_data = DeviceData.objects.filter(device_id=device_id).order_by('-timestamp').first()
            if latest_data:
                latest_entries.append(latest_data)

        page = self.paginate_queryset(latest_entries)
        if page is not None:
            serializer = DeviceDataSerializer(page, many=True)
            return self.get_paginated_response(serializer.data)

        serializer = DeviceDataSerializer(latest_entries, many=True)
        return Response(serializer.data)

    def paginate_queryset(self, queryset):
        page = int(self.request.query_params.get('page', 1))
        page_size = int(self.request.query_params.get('page_size', 10))
        start = (page - 1) * page_size
        end = start + page_size
        self.total_count = len(queryset)
        self.page_size = page_size
        self.page = page
        return queryset[start:end]

    def get_paginated_response(self, data):
        return Response({
            "count": self.total_count,
            "page": self.page,
            "page_size": self.page_size,
            "results": data
        })


class FirstTimePasswordChangeView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request):
        password = request.data.get("password")
        try:
            validate_password(password, request.user)
            request.user.set_password(password)
            request.user.save()
            return Response({"message": "Password updated successfully."})
        except Exception as e:
            return Response({"error": str(e)}, status=400)
