from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DeviceData, AlertRule, Alert, FaultAlert, Fault
from django.utils import timezone

@receiver(post_save, sender=DeviceData)
def check_alerts_on_device_data_save(sender, instance, created, **kwargs):
    alert_rules = AlertRule.objects.all()
    
    for rule in alert_rules:
        try:
            device = instance.device_id
            can_data = instance.can_data or {}
            # Evaluate the condition safely
            condition_result = eval(rule.condition, {}, {
                "can_data": can_data,
                "device": device,
                "timezone": timezone,
            })
            if condition_result:
                Alert.objects.create(
                    device=instance,
                    alert_type=rule.alert_type,
                    value=rule.description,
                )
                print(f'[Alert Created Success] {rule.name}')
        except Exception as e:
            print(f"[ALERT ERROR] {rule.name}: {str(e)}")

@receiver(post_save, sender=DeviceData)
def create_fault_alert(sender, instance, created, **kwargs):
    can_data = instance.can_data
    if not can_data:
        return

    all_faults = Fault.objects.all()

    for fault in all_faults:
        fault_key = fault.name.lower()

        # Check key match
        if any(fault_key in str(k).lower() for k in can_data.keys()) or \
           any(fault_key in str(v).lower() for v in can_data.values()):

            FaultAlert.objects.create(
                device=instance,
                fault=fault,
                can_data_snapshot=can_data
            )
