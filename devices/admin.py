from django.contrib import admin

from devices.models import (
    Device,
    ReplicaDevices,
    DeviceData,
    ReplicaDevicesData,
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
    
    def get_queryset(self, request):
        return super().get_queryset(request).using('default')

    def save_model(self, request, obj, form, change):
        obj.save(using='default')

    def delete_model(self, request, obj):
        obj.delete(using='default')
   
@admin.register(ReplicaDevices)     
class ReplicaDeviceAdmin(admin.ModelAdmin):
    fields = ['device_id', 'device_type', 'device_type_name', 'is_connected', 'is_active', 'last_seen']
    list_display = (
        'id', 'device_id', 'is_connected', 'is_active', 'last_seen'
    )
    list_filter = ('id', 'device_id', 'is_connected', 'is_active', 'last_seen')
    search_fields = ('id', 'device_id', 'is_connected', 'is_active', 'last_seen')
    readonly_fields = ('id', 'is_connected', 'is_active', 'last_seen')

    def get_queryset(self, request):
        return super().get_queryset(request).using('replica')

    def save_model(self, request, obj, form, change):
        obj.save(using='replica')

    def delete_model(self, request, obj):
        obj.delete(using='replica')

@admin.register(DeviceData)
class DeviceDataAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'device_id', 'latitude', 'longitude'
    )
    list_filter = ('id', 'device_id')
    search_fields = ('id', 'device_id')
    readonly_fields = ('id', 'device_id')
    
    def get_queryset(self, request):
        return super().get_queryset(request).using('default')

    def save_model(self, request, obj, form, change):
        obj.save(using='default')

    def delete_model(self, request, obj):
        obj.delete(using='default')

@admin.register(ReplicaDevicesData)
class ReplicaDeviceDataAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'device_id', 'latitude', 'longitude'
    )
    list_filter = ('id', 'device_id')
    search_fields = ('id', 'device_id')
    readonly_fields = ('id', 'device_id')
    
    def get_queryset(self, request):
        return super().get_queryset(request).using('replica')

    def save_model(self, request, obj, form, change):
        obj.save(using='replica')

    def delete_model(self, request, obj):
        obj.delete(using='replica')

@admin.register(ExtraDevice)
class ExtraDeviceAdmin(admin.ModelAdmin):
    list_display = (
        'id', 'device_id'
    )
    list_filter = ('id', 'device_id')
    search_fields = ('id', 'device_id')
    readonly_fields = ('id', 'device_id')