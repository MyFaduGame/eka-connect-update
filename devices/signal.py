from django.db.models.signals import post_save
from django.dispatch import receiver
from .models import DeviceData, AlertRule, Alert
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
