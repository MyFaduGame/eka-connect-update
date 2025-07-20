from django.db import models
from django.utils.translation   import gettext_lazy as _

class Device(models.Model):
    device_id = models.CharField(_("DeviceId"),max_length=5000, unique=True, blank=True)
    device_type = models.CharField(_("DeviceType"),max_length=500,null=True,blank=True)
    device_type_name = models.CharField(_("DeviceSpecificType"),max_length=500,)
    is_connected = models.BooleanField(_("Connected"),default=False)
    is_active = models.BooleanField(_("Active"),default=True)
    last_seen = models.DateTimeField(_("Last_Login"), auto_now_add=True)

    def __str__(self):
        return self.device_id
    
    def save(self, *args, **kwargs):
        using = kwargs.pop('using', 'default')
        super().save(*args, using=using, **kwargs)

        if using == 'default':
            clone = self.__class__.objects.using('default').get(pk=self.pk)
            clone.pk = self.pk
            clone.save(using='replica')
            
class ReplicaDevices(Device):
    class Meta:
        proxy = True
        verbose_name = "Replica Device"
        verbose_name_plural = "Replica Devices"
    
class ExtraDevice(models.Model):
    device_id = models.CharField(_("DeviceId"),max_length=5000, unique=True)
    last_seen = models.DateTimeField(_("Last_Login"), auto_now_add=True)
    is_notified = models.BooleanField(_("Notified"),default=False)
    
    def __str__(self):
        return self.device_id
    
    def save(self, *args, **kwargs):
        using = kwargs.pop('using', 'default')
        super().save(*args, using=using, **kwargs)

        if using == 'default':
            clone = self.__class__.objects.using('default').get(pk=self.pk)
            clone.pk = self.pk
            clone.save(using='replica')
    
class DeviceData(models.Model):
    timestamp = models.DateTimeField(_("time_stamp"), auto_now_add=True)
    device_id = models.CharField(max_length=500, null=True, blank=True)
    NMR = models.CharField(max_length=500, null=True, blank=True)
    digital_input_status = models.CharField(max_length=500, null=True, blank=True)
    digital_output_status = models.CharField(max_length=500, null=True, blank=True)
    analog_input_1 = models.CharField(max_length=500, null=True, blank=True)
    analog_input_2 = models.CharField(max_length=500, null=True, blank=True)
    frame_number = models.CharField(max_length=500, null=True, blank=True)
    odometer = models.CharField(max_length=500, null=True, blank=True)
    debug_info = models.CharField(max_length=500, null=True, blank=True)
    header = models.CharField(max_length=500, null=True, blank=True)
    vendor_id = models.CharField(max_length=500, null=True, blank=True)
    version = models.CharField(max_length=500, null=True, blank=True)
    packet_type = models.CharField(max_length=500, null=True, blank=True)
    alert_id = models.CharField(max_length=500, null=True, blank=True)
    packet_status = models.CharField(max_length=500, null=True, blank=True)
    IMEI = models.CharField(max_length=500, null=True, blank=True)
    vehicle_reg_no = models.CharField(max_length=500, null=True, blank=True)
    gps_fix = models.CharField(max_length=500, null=True, blank=True)
    date = models.CharField(max_length=500, null=True, blank=True)
    time = models.CharField(max_length=500, null=True, blank=True)
    latitude = models.CharField(max_length=500, null=True, blank=True)
    latitude_dir = models.CharField(max_length=500, null=True, blank=True)
    longitude = models.CharField(max_length=500, null=True, blank=True)
    longitude_dir = models.CharField(max_length=500, null=True, blank=True)
    speed = models.CharField(max_length=500, null=True, blank=True)
    heading = models.CharField(max_length=500, null=True, blank=True)
    no_of_stattalites = models.CharField(max_length=500, null=True, blank=True)
    altitude = models.CharField(max_length=500, null=True, blank=True)
    pdop = models.CharField(max_length=500, null=True, blank=True)
    hdop = models.CharField(max_length=500, null=True, blank=True)
    operator = models.CharField(max_length=500, null=True, blank=True)
    ignition = models.CharField(max_length=500, null=True, blank=True)
    main_power_status = models.CharField(max_length=500, null=True, blank=True)
    main_input_voltage = models.CharField(max_length=500, null=True, blank=True)
    internal_battery_voltage = models.CharField(max_length=500, null=True, blank=True)
    emergency_status = models.CharField(max_length=500, null=True, blank=True)
    temper_alert = models.CharField(max_length=500, null=True, blank=True)
    gsm_strength = models.CharField(max_length=500, null=True, blank=True)
    MCC = models.CharField(max_length=500, null=True, blank=True)
    MNC = models.CharField(max_length=500, null=True, blank=True)
    LAC = models.CharField(max_length=500, null=True, blank=True)
    cell_id = models.CharField(max_length=500, null=True, blank=True)
    extra_data = models.JSONField()
    can_data = models.JSONField()

    def save(self, *args, **kwargs):
        using = kwargs.pop('using', 'default')
        super().save(*args, using=using, **kwargs)

        if using == 'default':
            clone = self.__class__.objects.using('default').get(pk=self.pk)
            clone.pk = self.pk
            clone.save(using='replica')
            
class ReplicaDevicesData(DeviceData):
    class Meta:
        proxy = True
        verbose_name = "Replica DeviceData"
        verbose_name_plural = "Replica DevicesData"
