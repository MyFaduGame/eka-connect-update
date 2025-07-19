from django.db import models
from django.contrib.auth.models import AbstractUser,Group,Permission

from devices.models import Device

class User(AbstractUser):
    # Extend default Django user for profile
    full_name = models.CharField(max_length=255, blank=True, null=True)
    mobile = models.CharField(max_length=15, blank=True, null=True)
    groups = models.ManyToManyField(
        Group,
        related_name='EkaGroup',
        blank=True,
        help_text='The groups this user belongs to.',
        verbose_name='groups'
    )
    user_permissions = models.ManyToManyField(
        Permission,
        related_name='EkaPermissions',
        blank=True,
        help_text='Specific permissions for this user.',
        verbose_name='user permissions'
    )

class UserDeviceAssignment(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='devices')
    device = models.ForeignKey(Device, on_delete=models.CASCADE)
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('user', 'device')
