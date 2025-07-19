# serializers.py
from rest_framework import serializers
from devices.models import (
    Device,
    DeviceData
)

class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = '__all__'
        read_only_fields = ['is_active', 'last_seen']


class DeviceDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = DeviceData
        fields = '__all__'
        read_only_fields = ['can_data', 'extra_data']
        