from rest_framework import serializers
from users.models import User, UserDeviceAssignment
from devices.models import Device, DeviceData

class UserProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'mobile']

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = ['id', 'device_id', 'device_type']

class DeviceDataSerializer(serializers.ModelSerializer):
    device = DeviceSerializer()

    class Meta:
        model = DeviceData
        fields = '__all__'

class AssignDeviceSerializer(serializers.Serializer):
    user_id = serializers.IntegerField()
    device_ids = serializers.ListField(child=serializers.IntegerField())
