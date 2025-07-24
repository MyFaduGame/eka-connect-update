# serializers.py
from rest_framework import serializers
from devices.models import (
    Alert,
    Device,
    DeviceData,
    FaultAlert
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

class AlertDataSerializer(serializers.ModelSerializer):
    class Meta:
        model = Alert
        fields = '__all__'
        read_only_fields = ['device','timestamp']

class FaultAlertSerializer(serializers.ModelSerializer):
    fault_name = serializers.CharField(source='fault.name', read_only=True)
    device_id = serializers.CharField(source='device.device_id', read_only=True)

    class Meta:
        model = FaultAlert
        fields = ['id', 'device_id', 'fault_name', 'can_data_snapshot', 'timestamp']

class LiveDataSerializer(serializers.ModelSerializer):
    
    class Meta:
        model = DeviceData
        fields = ['timestamp','device_id','latitude','latitude_dir','longitude',
                  'longitude_dir','odometer','speed','heading']
