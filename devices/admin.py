from django.contrib import admin

from devices.models import (
    Device,
    DeviceData,
    ExtraDevice,
)

@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    fields = ['device_id', 'device_type', 'device_type_name', 'is_connected', 'is_active', 'last_seen']
    list_display = (
        'id', 'device_id', 'is_connected', 'is_active', 'last_seen'
    )
    list_filter = ('id', 'device_id', 'is_connected', 'is_active', 'last_seen')
    search_fields = ('id', 'device_id', 'is_connected', 'is_active', 'last_seen')
    readonly_fields = ('id', 'is_connected', 'is_active', 'last_seen')

@admin.register(DeviceData)
class MQTTDataAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'device_id', 'latitude', 'longitude'
    )
    list_filter = ('id', 'device_id')
    search_fields = ('id', 'device_id')
    readonly_fields = ('id', 'device_id')


@admin.register(ExtraDevice)
class MQTTDataAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'device_id'
    )
    list_filter = ('id', 'device_id')
    search_fields = ('id', 'device_id')
    readonly_fields = ('id', 'device_id')